"""Multi-specialty router for selecting weight vectors per query."""

from __future__ import annotations

import logging
from pathlib import Path

from aegis.scoring.quality_prior import QualityPrior, WeightVector, load_weight_vector

logger = logging.getLogger(__name__)

_WEIGHT_PATHS: dict[str, str] = {
    "translational": "config/aegis/weights/translational_v1.yaml",
    "drug_discovery": "config/aegis/weights/drug_discovery_v1.yaml",
    "clinician": "config/aegis/weights/clinician_v1.yaml",
}


class MultiSpecialtyRouter:
    """Route queries to the appropriate specialty weight vector."""

    def __init__(self) -> None:
        self._priors: dict[str, QualityPrior] = {}
        self._vectors: dict[str, WeightVector] = {}

    def load_all(self) -> None:
        """Load all specialty weight vectors from config files."""
        for specialty, path_str in _WEIGHT_PATHS.items():
            path = Path(path_str)
            if path.exists():
                wv = load_weight_vector(path)
                self._vectors[specialty] = wv
                self._priors[specialty] = QualityPrior(wv)
                logger.info("Loaded weight vector for %s", specialty)
            else:
                logger.warning(
                    "Weight config not found for %s: %s", specialty, path
                )

    def get_prior(self, specialty: str) -> QualityPrior | None:
        """Return the QualityPrior for a specialty, or None."""
        return self._priors.get(specialty)

    def get_weight_vector(self, specialty: str) -> WeightVector | None:
        """Return the WeightVector for a specialty, or None."""
        return self._vectors.get(specialty)

    def select_specialty(
        self,
        specialty_distribution: dict[str, float],
        query_specialty: str | None = None,
    ) -> str:
        """Select the best specialty for a query.

        If query_specialty is provided and available, use it.
        Otherwise, pick the specialty with the highest probability.
        Default to 'translational' if nothing matches.
        """
        if query_specialty is not None and query_specialty in self._vectors:
            return query_specialty

        if specialty_distribution:
            best = max(
                specialty_distribution, key=lambda k: specialty_distribution[k]
            )
            if best in self._vectors:
                return best

        return "translational"

    @property
    def available_specialties(self) -> list[str]:
        """Return list of loaded specialty names."""
        return list(self._vectors.keys())
