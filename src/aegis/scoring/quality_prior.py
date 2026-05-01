"""Quality prior Q(c): geometric-mean composition of F1-F6 sub-scores."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

_DEFAULT_CONFIG_PATH = Path("config/aegis/weights/translational_v1.yaml")


class WeightVector(BaseModel):
    """Versioned weight configuration for quality prior composition."""

    model_config = ConfigDict(frozen=True)

    version: int
    specialty: str
    weights: dict[str, float]  # f1_rcr -> 0.35, etc.
    exponents: dict[str, float]  # alpha, beta, gamma
    exponent_bounds: dict[str, list[float]]  # alpha -> [0.3, 1.2]


class QualityScore(BaseModel):
    """Result of Q(c) computation for a single candidate."""

    model_config = ConfigDict(frozen=True)

    raw_score: float  # raw geometric mean (internal)
    percentile: float  # percentile within cohort [0, 1]
    component_percentiles: dict[str, float]  # f1_rcr -> 0.85, etc.
    weight_version: int


def load_weight_vector(
    config_path: Path | None = None,
) -> WeightVector:
    """Load weight vector from YAML config file."""
    path = config_path or _DEFAULT_CONFIG_PATH
    with open(path) as f:  # noqa: PTH123
        data: dict[str, Any] = yaml.safe_load(f)
    return WeightVector(
        version=data["version"],
        specialty=data["specialty"],
        weights=data["weights"],
        exponents=data["exponents"],
        exponent_bounds=data.get("exponent_bounds", {}),
    )


class QualityPrior:
    """Compute Q(c) = prod(F_i(c)^{w_i}) with percentile calibration."""

    def __init__(self, weight_vector: WeightVector) -> None:
        self._weights = weight_vector

    @property
    def weight_vector(self) -> WeightVector:
        """Return the weight vector used for this prior."""
        return self._weights

    def compute_raw(
        self,
        component_percentiles: dict[str, float],
    ) -> float:
        """Compute raw Q(c) from component percentiles.

        Q(c) = prod(F_i(c)^{w_i}) where F_i(c) is the percentile [0,1].
        Uses geometric mean in log space to avoid numerical issues.
        """
        log_sum = 0.0
        total_weight = 0.0

        for family, weight in self._weights.weights.items():
            percentile = component_percentiles.get(family, 0.0)
            # Clamp to avoid log(0). Floor of 0.01 prevents catastrophic
            # penalties from missing data — a researcher who has no patents
            # should not be treated identically to a proven fraud.
            if weight == 0.0:
                continue
            percentile = max(percentile, 0.01)
            log_sum += weight * math.log(percentile)
            total_weight += weight

        if total_weight == 0:
            return 0.0

        # Geometric mean: exp(sum(w_i * log(p_i)))
        return math.exp(log_sum)

    def compute_percentiles(
        self,
        candidates: list[tuple[str, dict[str, float]]],
    ) -> dict[str, QualityScore]:
        """Compute Q(c) percentile for a set of candidates.

        Input: list of (candidate_uuid, {family: percentile})
        Output: dict mapping uuid -> QualityScore
        """
        if not candidates:
            return {}

        # Compute raw Q(c) for each candidate
        raw_scores: list[
            tuple[str, float, dict[str, float]]
        ] = []
        for uuid, components in candidates:
            raw = self.compute_raw(components)
            raw_scores.append((uuid, raw, components))

        # Sort by raw score for percentile assignment
        raw_scores.sort(key=lambda x: x[1])

        n = len(raw_scores)
        results: dict[str, QualityScore] = {}
        for rank_idx, (uuid, raw, components) in enumerate(
            raw_scores
        ):
            percentile = (rank_idx + 0.5) / n
            results[uuid] = QualityScore(
                raw_score=round(raw, 8),
                percentile=round(percentile, 6),
                component_percentiles=components,
                weight_version=self._weights.version,
            )

        return results
