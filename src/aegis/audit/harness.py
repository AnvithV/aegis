"""Audit harness: pair sampling, session management, and review facade."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from aegis.audit.storage import JudgmentStore, PairwiseJudgment

logger = logging.getLogger(__name__)


class PairwisePrompt(BaseModel):
    """A prompt presented to a reviewer for pairwise comparison."""

    model_config = ConfigDict(frozen=True)

    prompt_id: str
    query_mesh_terms: list[str]
    candidate_a_uuid: str
    candidate_a_name: str
    candidate_a_evidence: dict[str, str]
    candidate_b_uuid: str
    candidate_b_name: str
    candidate_b_evidence: dict[str, str]


@dataclass
class ScoredCandidate:
    """A candidate with a score, used as input to pair sampling."""

    uuid: str
    name: str
    score: float
    evidence: dict[str, str]


class PairSampler:
    """Sample informative candidate pairs with active-learning bias."""

    def __init__(self, *, rng_seed: int | None = None) -> None:
        self._rng = random.Random(rng_seed)

    def sample_pairs(
        self,
        *,
        candidates: list[ScoredCandidate],
        query_mesh: list[str],
        n_pairs: int,
        existing_judgments: list[PairwiseJudgment] | None = None,
    ) -> list[PairwisePrompt]:
        """Sample up to n_pairs informative candidate pairs.

        Uses active-learning bias: pairs with closer scores are preferred
        since they are more informative for learning-to-rank.
        """
        if len(candidates) < 2:
            return []

        # Build set of already-judged pairs for exclusion
        judged: set[frozenset[str]] = set()
        if existing_judgments:
            for jdg in existing_judgments:
                judged.add(
                    frozenset({jdg.candidate_a_uuid, jdg.candidate_b_uuid})
                )

        # Sort candidates by score
        sorted_cands = sorted(
            candidates, key=lambda c: c.score, reverse=True
        )

        # Build all possible pairs with weights
        weighted_pairs: list[tuple[int, int, float]] = []
        for idx_a in range(len(sorted_cands)):
            for idx_b in range(idx_a + 1, len(sorted_cands)):
                pair_key = frozenset({
                    sorted_cands[idx_a].uuid,
                    sorted_cands[idx_b].uuid,
                })
                if pair_key in judged:
                    continue
                score_diff = abs(
                    sorted_cands[idx_a].score - sorted_cands[idx_b].score
                )
                weight = 1.0 / (1.0 + score_diff)
                weighted_pairs.append((idx_a, idx_b, weight))

        if not weighted_pairs:
            return []

        # Normalize weights and sample without replacement
        total_weight = sum(w for _, _, w in weighted_pairs)
        normalized: list[tuple[int, int, float]] = [
            (pa, pb, w / total_weight)
            for pa, pb, w in weighted_pairs
        ]

        selected: list[tuple[int, int]] = []
        remaining = list(normalized)
        for _ in range(min(n_pairs, len(remaining))):
            if not remaining:
                break
            weights = [w for _, _, w in remaining]
            chosen_indices = self._rng.choices(
                range(len(remaining)), weights=weights, k=1
            )
            chosen_idx = chosen_indices[0]
            pa, pb, _ = remaining.pop(chosen_idx)
            selected.append((pa, pb))

        # Build prompts
        prompts: list[PairwisePrompt] = []
        for idx_a, idx_b in selected:
            a = sorted_cands[idx_a]
            b = sorted_cands[idx_b]
            prompts.append(
                PairwisePrompt(
                    prompt_id=uuid4().hex,
                    query_mesh_terms=query_mesh,
                    candidate_a_uuid=a.uuid,
                    candidate_a_name=a.name,
                    candidate_a_evidence=a.evidence,
                    candidate_b_uuid=b.uuid,
                    candidate_b_name=b.name,
                    candidate_b_evidence=b.evidence,
                )
            )

        return prompts


class SessionManager:
    """Manage reviewer sessions with pair limits and cooldowns."""

    def __init__(
        self,
        *,
        max_pairs_per_session: int = 20,
        cooldown_minutes: int = 60,
    ) -> None:
        self._max_pairs = max_pairs_per_session
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._last_session_end: dict[str, datetime] = {}

    def can_continue(
        self,
        *,
        reviewer_id: str,
        session_judgments: int,
        session_start: datetime,
    ) -> bool:
        """Check whether a reviewer can continue their session."""
        if session_judgments >= self._max_pairs:
            return False

        last_end = self._last_session_end.get(reviewer_id)
        if last_end is not None and session_start < last_end + self._cooldown:
            return False

        return True

    def record_session_end(
        self,
        *,
        reviewer_id: str,
        timestamp: datetime,
    ) -> None:
        """Record when a reviewer's session ended."""
        self._last_session_end[reviewer_id] = timestamp


class AuditHarness:
    """Facade for the audit review workflow."""

    def __init__(
        self,
        *,
        store: JudgmentStore,
        sampler: PairSampler,
        session_mgr: SessionManager,
    ) -> None:
        self._store = store
        self._sampler = sampler
        self._session_mgr = session_mgr

    def next_pair(
        self,
        *,
        reviewer_id: str,
        candidates: list[ScoredCandidate],
        query_mesh: list[str],
    ) -> PairwisePrompt | None:
        """Get the next pair for a reviewer to judge."""
        existing = self._store.load_all()
        prompts = self._sampler.sample_pairs(
            candidates=candidates,
            query_mesh=query_mesh,
            n_pairs=1,
            existing_judgments=existing,
        )
        if not prompts:
            return None
        return prompts[0]

    def submit_judgment(self, *, judgment: PairwiseJudgment) -> None:
        """Submit a completed judgment to the store."""
        self._store.append(judgment=judgment)

    def inter_reviewer_kappa(self) -> float | None:
        """Compute Cohen's kappa on overlapping pairs across reviewers.

        Returns None if there are fewer than 2 reviewers or no
        overlapping pair judgments.
        """
        all_judgments = self._store.load_all()

        # Group by (candidate_a, candidate_b) pair — normalize order
        pair_reviews: dict[
            frozenset[str], dict[str, str]
        ] = {}
        for j in all_judgments:
            pair_key = frozenset({
                j.candidate_a_uuid, j.candidate_b_uuid
            })
            if pair_key not in pair_reviews:
                pair_reviews[pair_key] = {}
            pair_reviews[pair_key][j.reviewer_id] = j.winner_uuid

        # Find overlapping pairs (judged by 2+ reviewers)
        agreements = 0
        total = 0
        all_winners: list[str] = []

        for _pair_key, reviews in pair_reviews.items():
            reviewers = list(reviews.keys())
            if len(reviewers) < 2:
                continue
            # Compare all reviewer pairs
            for i in range(len(reviewers)):
                for k in range(i + 1, len(reviewers)):
                    total += 1
                    if reviews[reviewers[i]] == reviews[reviewers[k]]:
                        agreements += 1
                    all_winners.append(reviews[reviewers[i]])
                    all_winners.append(reviews[reviewers[k]])

        if total == 0:
            return None

        # Cohen's kappa: (p_o - p_e) / (1 - p_e)
        p_observed = agreements / total

        # Expected agreement by chance
        winner_counts: dict[str, int] = {}
        for w in all_winners:
            winner_counts[w] = winner_counts.get(w, 0) + 1
        n_ratings = len(all_winners)
        p_expected = sum(
            (c / n_ratings) ** 2 for c in winner_counts.values()
        )

        if p_expected >= 1.0:
            return None

        return (p_observed - p_expected) / (1.0 - p_expected)
