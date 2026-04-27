"""F5 sub-score: translational impact (Phase 1 subset)."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

_COVERAGE_CAVEAT = (
    "Phase 1: patents excluded; Phase 2 will include patent linkage"
)


class F5Score(BaseModel):
    """Result of F5 computation for a single candidate."""

    model_config = ConfigDict(frozen=True)

    fda_submissions: int
    phase2plus_drugs: int
    nccn_panel_member: bool
    coverage_caveat: str
    percentile: float  # percentile within cohort [0, 1]


@dataclass
class TranslationalInput:
    """Raw inputs for F5 scoring."""

    fda_submission_count: int
    phase2plus_trial_count: int
    is_nccn_panel_member: bool


class F5Computer:
    """Compute F5 sub-score (translational impact) for candidates."""

    def score_raw(
        self,
        inp: TranslationalInput,
    ) -> tuple[float, int, int, bool, str]:
        """Compute raw F5 values (before percentile).

        Returns (composite, fda_count, phase2_count, nccn_flag, coverage_caveat).
        """
        fda_component = min(inp.fda_submission_count / 3.0, 1.0)
        trial_component = min(inp.phase2plus_trial_count / 5.0, 1.0)
        nccn_component = 1.0 if inp.is_nccn_panel_member else 0.0

        composite = (
            0.35 * fda_component
            + 0.40 * trial_component
            + 0.25 * nccn_component
        )

        return (
            composite,
            inp.fda_submission_count,
            inp.phase2plus_trial_count,
            inp.is_nccn_panel_member,
            _COVERAGE_CAVEAT,
        )

    def compute_percentiles(
        self,
        raw_scores: list[tuple[str, float, int, int, bool, str]],
    ) -> dict[str, F5Score]:
        """Compute percentile rank for each candidate.

        Takes list of (uuid, composite, fda_count, phase2_count, nccn_flag, caveat).
        """
        if not raw_scores:
            return {}

        # Sort by composite to assign percentiles
        sorted_scores = sorted(raw_scores, key=lambda x: x[1])

        n = len(sorted_scores)
        results: dict[str, F5Score] = {}
        for rank_idx, (
            uuid,
            _composite,
            fda_count,
            phase2_count,
            nccn_flag,
            caveat,
        ) in enumerate(sorted_scores):
            percentile = (rank_idx + 0.5) / n  # midpoint percentile
            results[uuid] = F5Score(
                fda_submissions=fda_count,
                phase2plus_drugs=phase2_count,
                nccn_panel_member=nccn_flag,
                coverage_caveat=caveat,
                percentile=round(percentile, 6),
            )

        return results
