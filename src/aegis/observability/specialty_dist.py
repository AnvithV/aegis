"""Specialty distribution dashboard for multi-population candidate analysis."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class SpecialtyDistMetrics(BaseModel):
    """Frozen snapshot of specialty distribution statistics."""

    model_config = ConfigDict(frozen=True)

    total_candidates: int
    per_specialty_count: dict[str, int]
    per_specialty_pct: dict[str, float]
    multi_specialty_count: int
    multi_specialty_pct: float
    multi_specialty_distribution: dict[str, int]


class SpecialtyDistDashboard:
    """Compute specialty distribution metrics from candidate classification data."""

    def compute(
        self, candidates: list[dict[str, dict[str, float]]]
    ) -> SpecialtyDistMetrics:
        """Compute specialty distribution for a list of candidates.

        Each candidate is a dict mapping uuid to specialty_distribution,
        where specialty_distribution is {specialty: probability}.
        """
        total = len(candidates)
        if total == 0:
            return SpecialtyDistMetrics(
                total_candidates=0,
                per_specialty_count={},
                per_specialty_pct={},
                multi_specialty_count=0,
                multi_specialty_pct=0.0,
                multi_specialty_distribution={},
            )

        per_specialty_count: dict[str, int] = {}
        multi_specialty_count = 0
        multi_specialty_distribution: dict[str, int] = {}

        for candidate in candidates:
            for _uuid, spec_dist in candidate.items():
                if not spec_dist:
                    continue

                # Primary specialty = max probability
                primary = max(spec_dist, key=lambda s: spec_dist[s])
                per_specialty_count[primary] = (
                    per_specialty_count.get(primary, 0) + 1
                )

                # Multi-specialty = more than one specialty above 0.2
                above_threshold = [
                    s for s, p in spec_dist.items() if p > 0.2
                ]
                if len(above_threshold) > 1:
                    multi_specialty_count += 1
                    count_key = str(len(above_threshold))
                    multi_specialty_distribution[count_key] = (
                        multi_specialty_distribution.get(count_key, 0) + 1
                    )

        per_specialty_pct = {
            spec: round(100.0 * count / total, 2)
            for spec, count in per_specialty_count.items()
        }
        multi_specialty_pct = round(100.0 * multi_specialty_count / total, 2)

        logger.info(
            "Specialty distribution computed: %d candidates, %d multi-specialty",
            total,
            multi_specialty_count,
        )

        return SpecialtyDistMetrics(
            total_candidates=total,
            per_specialty_count=per_specialty_count,
            per_specialty_pct=per_specialty_pct,
            multi_specialty_count=multi_specialty_count,
            multi_specialty_pct=multi_specialty_pct,
            multi_specialty_distribution=multi_specialty_distribution,
        )
