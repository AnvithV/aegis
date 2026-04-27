"""F4 sub-score: apex-tier recognition flag."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Lookup table: membership count -> score (monotonic, diminishing returns)
_SCORE_TABLE: dict[int, float] = {
    0: 0.0,
    1: 0.4,
    2: 0.65,
    3: 0.8,
    4: 0.9,
}
_MAX_TABLE_COUNT = max(_SCORE_TABLE)
_MAX_SCORE = 1.0


def _membership_score(count: int) -> float:
    """Monotonic mapping from membership count to [0, 1]."""
    if count <= 0:
        return 0.0
    if count in _SCORE_TABLE:
        return _SCORE_TABLE[count]
    return _MAX_SCORE


class F4Score(BaseModel):
    """F4 apex-tier sub-score for a single candidate."""

    model_config = ConfigDict(frozen=True)

    memberships: list[str]
    membership_count: int
    score: float
    percentile: float


class F4Computer:
    """Compute F4 apex-tier scores and cohort percentiles."""

    def score_from_memberships(
        self, memberships: list[str]
    ) -> tuple[float, int]:
        """Compute raw apex score from membership list.

        Returns (raw_score, count).
        """
        count = len(memberships)
        return _membership_score(count), count

    def compute_percentiles(
        self,
        raw_scores: list[tuple[str, float, int]],
    ) -> dict[str, F4Score]:
        """Compute percentile-ranked F4 scores for a cohort.

        Each entry is (candidate_id, raw_score, membership_count).
        Memberships list is not available here; stored as empty.
        """
        if not raw_scores:
            return {}

        # Rank-order percentile by raw score
        sorted_scores = sorted(raw_scores, key=lambda x: x[1])
        n = len(sorted_scores)
        rank_map: dict[str, float] = {}
        for rank_idx, (cid, _, _) in enumerate(sorted_scores):
            rank_map[cid] = rank_idx / max(n - 1, 1)

        result: dict[str, F4Score] = {}
        for cid, raw_score, count in raw_scores:
            result[cid] = F4Score(
                memberships=[],
                membership_count=count,
                score=raw_score,
                percentile=rank_map[cid],
            )

        return result
