"""Pairwise audit consistency tracking with Cohen's kappa."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict


class JudgmentRecord(BaseModel):
    """A single pairwise judgment from a reviewer."""

    model_config = ConfigDict(frozen=True)

    judgment_id: str
    reviewer_id: str
    candidate_a_uuid: str
    candidate_b_uuid: str
    winner_uuid: str
    is_reshow: bool = False


class ConsistencyReport(BaseModel):
    """Report on inter- and intra-reviewer agreement."""

    model_config = ConfigDict(frozen=True)

    inter_reviewer_kappa: float | None
    intra_reviewer_kappa: float | None
    overlapping_pair_count: int
    reshow_pair_count: int
    per_reviewer_agreement: dict[str, float]
    low_agreement_reviewers: list[str]


class AuditConsistencyTracker:
    """Track pairwise audit consistency and compute agreement metrics."""

    def __init__(
        self,
        reshow_rate: float = 0.05,
        low_agreement_threshold: float = 0.6,
    ) -> None:
        self._reshow_rate = reshow_rate
        self._low_agreement_threshold = low_agreement_threshold

    def should_reshow(self, pair_count: int) -> bool:
        """Determine if the next pair should be a reshow."""
        if self._reshow_rate <= 0:
            return False
        interval = round(1.0 / self._reshow_rate)
        if interval == 0:
            return True
        return pair_count % interval == 0

    def find_overlapping_pairs(
        self, judgments: list[JudgmentRecord]
    ) -> dict[tuple[str, str], list[JudgmentRecord]]:
        """Find pairs judged by different reviewers.

        Keys are sorted (candidate_a, candidate_b) tuples.
        """
        by_pair: dict[
            tuple[str, str], list[JudgmentRecord]
        ] = defaultdict(list)
        for j in judgments:
            if not j.is_reshow:
                key = tuple(
                    sorted([j.candidate_a_uuid, j.candidate_b_uuid])
                )
                by_pair[(key[0], key[1])].append(j)

        return {
            k: v
            for k, v in by_pair.items()
            if len({j.reviewer_id for j in v}) > 1
        }

    def find_reshow_pairs(
        self, judgments: list[JudgmentRecord]
    ) -> dict[
        tuple[str, str, str], list[JudgmentRecord]
    ]:
        """Find reshow pairs by the same reviewer.

        Keys are (reviewer_id, candidate_a, candidate_b) tuples.
        """
        by_key: dict[
            tuple[str, str, str], list[JudgmentRecord]
        ] = defaultdict(list)
        for j in judgments:
            pair = tuple(
                sorted([j.candidate_a_uuid, j.candidate_b_uuid])
            )
            key = (j.reviewer_id, pair[0], pair[1])
            by_key[key].append(j)

        return {
            k: v for k, v in by_key.items() if len(v) > 1
        }

    def compute_kappa(
        self,
        pairs: list[tuple[str, str]],
    ) -> float | None:
        """Compute Cohen's kappa for a list of (rater1_choice, rater2_choice).

        Each tuple is (winner_from_rater1, winner_from_rater2).
        Returns None if fewer than 2 pairs.
        """
        if len(pairs) < 2:
            return None

        n = len(pairs)
        agree = sum(1 for a, b in pairs if a == b)
        p_o = agree / n

        all_choices = [c for pair in pairs for c in pair]
        unique = set(all_choices)
        total = len(all_choices)

        p_e = sum(
            (all_choices.count(c) / total) ** 2 for c in unique
        )

        if abs(1.0 - p_e) < 1e-10:
            return 1.0 if p_o == 1.0 else 0.0

        return (p_o - p_e) / (1.0 - p_e)

    def compute_report(
        self, judgments: list[JudgmentRecord]
    ) -> ConsistencyReport:
        """Compute a full consistency report from judgments."""
        overlapping = self.find_overlapping_pairs(judgments)
        reshow = self.find_reshow_pairs(judgments)

        # Inter-reviewer kappa from overlapping pairs
        inter_pairs: list[tuple[str, str]] = []
        for pair_judgments in overlapping.values():
            reviewers = sorted(
                {j.reviewer_id for j in pair_judgments}
            )
            if len(reviewers) >= 2:
                r1_js = [
                    j
                    for j in pair_judgments
                    if j.reviewer_id == reviewers[0]
                ]
                r2_js = [
                    j
                    for j in pair_judgments
                    if j.reviewer_id == reviewers[1]
                ]
                if r1_js and r2_js:
                    inter_pairs.append(
                        (r1_js[0].winner_uuid, r2_js[0].winner_uuid)
                    )

        inter_kappa = self.compute_kappa(inter_pairs)

        # Intra-reviewer kappa from reshow pairs
        intra_pairs: list[tuple[str, str]] = []
        for reshow_judgments in reshow.values():
            if len(reshow_judgments) >= 2:
                intra_pairs.append(
                    (
                        reshow_judgments[0].winner_uuid,
                        reshow_judgments[1].winner_uuid,
                    )
                )

        intra_kappa = self.compute_kappa(intra_pairs)

        # Per-reviewer agreement from reshows
        reviewer_reshows: dict[
            str, list[tuple[str, str]]
        ] = defaultdict(list)
        for (reviewer_id, _, _), rjs in reshow.items():
            if len(rjs) >= 2:
                reviewer_reshows[reviewer_id].append(
                    (rjs[0].winner_uuid, rjs[1].winner_uuid)
                )

        per_reviewer: dict[str, float] = {}
        for reviewer_id, rpairs in reviewer_reshows.items():
            if rpairs:
                agree = sum(1 for a, b in rpairs if a == b)
                per_reviewer[reviewer_id] = agree / len(rpairs)

        low_agreement = sorted(
            r
            for r, a in per_reviewer.items()
            if a < self._low_agreement_threshold
        )

        return ConsistencyReport(
            inter_reviewer_kappa=inter_kappa,
            intra_reviewer_kappa=intra_kappa,
            overlapping_pair_count=len(overlapping),
            reshow_pair_count=sum(
                len(v) for v in reshow.values()
            ),
            per_reviewer_agreement=per_reviewer,
            low_agreement_reviewers=low_agreement,
        )
