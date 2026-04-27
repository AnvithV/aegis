"""Refit scheduler: manages weight version bumping and cadence control."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from aegis.learning.plackett_luce import (
    FittedWeights,
    JudgmentRecord,
    PlackettLuceFitter,
)
from aegis.scoring.quality_prior import WeightVector, load_weight_vector

logger = logging.getLogger(__name__)


class RefitCadence(StrEnum):
    """Refit cadence levels."""

    cold_start = "cold_start"
    steady_state = "steady_state"


_CADENCE_DAYS: dict[RefitCadence, int] = {
    RefitCadence.cold_start: 7,
    RefitCadence.steady_state: 30,
}


class RefitResult(BaseModel):
    """Result of a refit operation."""

    model_config = ConfigDict(frozen=True)

    new_version: int
    output_path: str
    fitted_weights: FittedWeights
    cadence: RefitCadence
    timestamp: datetime


class RefitScheduler:
    """Manage weight refit cadence and version bumping."""

    def __init__(
        self,
        *,
        weights_dir: Path,
        current_version: int = 1,
        cadence: RefitCadence = RefitCadence.cold_start,
    ) -> None:
        self._weights_dir = weights_dir
        self._current_version = current_version
        self._cadence = cadence

    def should_refit(
        self,
        *,
        last_refit: datetime | None,
        now: datetime,
    ) -> bool:
        """Check whether a refit is due based on cadence."""
        if last_refit is None:
            return True
        min_days = _CADENCE_DAYS[self._cadence]
        return (now - last_refit) >= timedelta(days=min_days)

    def execute_refit(
        self,
        *,
        fitter: PlackettLuceFitter,
        judgments: list[JudgmentRecord],
        current_weights: WeightVector,
    ) -> RefitResult:
        """Run the fitter and write a new weight version YAML."""
        fitted = fitter.fit(
            judgments=judgments, initial_weights=current_weights
        )

        new_version = self._current_version + 1
        filename = f"{current_weights.specialty}_v{new_version}.yaml"
        output_path = self._weights_dir / filename

        # Build YAML data matching the config format
        data = {
            "version": new_version,
            "specialty": current_weights.specialty,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "weights": dict(current_weights.weights),
            "exponents": {
                "alpha": round(fitted.alpha, 4),
                "beta": round(fitted.beta, 4),
                "gamma": round(fitted.gamma, 4),
            },
            "exponent_bounds": {
                k: list(v)
                for k, v in current_weights.exponent_bounds.items()
            },
        }

        self._weights_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False)

        self._current_version = new_version
        now = datetime.now()

        return RefitResult(
            new_version=new_version,
            output_path=str(output_path),
            fitted_weights=fitted,
            cadence=self._cadence,
            timestamp=now,
        )

    def rollback(
        self,
        *,
        weights_dir: Path,
        target_version: int,
    ) -> WeightVector:
        """Load a prior weight version."""
        # Search for YAML files matching the version
        for path in weights_dir.glob(f"*_v{target_version}.yaml"):
            return load_weight_vector(config_path=path)
        msg = f"No weight file found for version {target_version}"
        raise FileNotFoundError(msg)
