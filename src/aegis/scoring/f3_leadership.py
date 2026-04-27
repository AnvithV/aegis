"""F3 sub-score: PI / leadership signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Composite weights for percentile ranking
_W_LAST_AUTHOR = 0.35
_W_TRIAL_PI = 0.30
_W_CORRESPONDING = 0.25
_W_EDITORIAL = 0.10

# Study Chair weight (vs full PI = 1.0)
_STUDY_CHAIR_WEIGHT = 0.7

# Normalization cap for trial PI count
_TRIAL_PI_CAP = 5.0


class F3Score(BaseModel):
    """F3 leadership sub-score for a single candidate."""

    model_config = ConfigDict(frozen=True)

    last_author_rate: float
    trial_pi_count: float
    corresponding_author_rate: float
    editorial_role_flag: bool
    percentile: float


@dataclass(frozen=True)
class LeadershipInput:
    """Raw inputs for computing F3 leadership score."""

    total_papers: int
    last_author_papers: int
    corresponding_author_papers: int
    trial_pi_roles: int
    trial_chair_roles: int
    has_editorial_role: bool


class F3Computer:
    """Compute F3 leadership sub-scores and cohort percentiles."""

    def score_raw(
        self, inp: LeadershipInput
    ) -> tuple[float, float, float, bool]:
        """Compute raw leadership metrics.

        Returns (last_author_rate, trial_pi_count,
        corresponding_author_rate, editorial_role_flag).
        """
        if inp.total_papers == 0:
            last_author_rate = 0.0
            corresponding_author_rate = 0.0
        else:
            last_author_rate = inp.last_author_papers / inp.total_papers
            corresponding_author_rate = (
                inp.corresponding_author_papers / inp.total_papers
            )

        trial_pi_count = (
            inp.trial_pi_roles * 1.0 + inp.trial_chair_roles * _STUDY_CHAIR_WEIGHT
        )

        return (
            last_author_rate,
            trial_pi_count,
            corresponding_author_rate,
            inp.has_editorial_role,
        )

    def compute_percentiles(
        self,
        raw_scores: list[tuple[str, float, float, float, bool]],
    ) -> dict[str, F3Score]:
        """Compute percentile-ranked F3 scores for a cohort.

        Each entry in raw_scores is (candidate_id, last_author_rate,
        trial_pi_count, corresponding_author_rate, editorial_role_flag).
        """
        if not raw_scores:
            return {}

        # Compute composite for each candidate
        composites: list[tuple[str, float]] = []
        for cid, lar, tpi, car, erf in raw_scores:
            normalized_tpi = min(tpi / _TRIAL_PI_CAP, 1.0)
            editorial_val = 1.0 if erf else 0.0
            composite = (
                _W_LAST_AUTHOR * lar
                + _W_TRIAL_PI * normalized_tpi
                + _W_CORRESPONDING * car
                + _W_EDITORIAL * editorial_val
            )
            composites.append((cid, composite))

        # Rank-order percentile
        sorted_composites = sorted(composites, key=lambda x: x[1])
        n = len(sorted_composites)
        rank_map: dict[str, float] = {}
        for rank_idx, (cid, _) in enumerate(sorted_composites):
            rank_map[cid] = rank_idx / max(n - 1, 1)

        # Build result
        result: dict[str, F3Score] = {}
        for cid, lar, tpi, car, erf in raw_scores:
            result[cid] = F3Score(
                last_author_rate=lar,
                trial_pi_count=tpi,
                corresponding_author_rate=car,
                editorial_role_flag=erf,
                percentile=rank_map[cid],
            )

        return result
