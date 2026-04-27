"""Tests for the refit scheduler."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from aegis.learning.plackett_luce import (
    JudgmentRecord,
    PlackettLuceFitter,
)
from aegis.learning.refit_scheduler import (
    RefitCadence,
    RefitScheduler,
)
from aegis.scoring.quality_prior import WeightVector


def _make_weight_vector(*, version: int = 1) -> WeightVector:
    """Create a test weight vector."""
    return WeightVector(
        version=version,
        specialty="translational",
        weights={"f1_rcr": 0.5, "f2_funding": 0.5},
        exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
        exponent_bounds={
            "alpha": [0.3, 1.2],
            "beta": [0.5, 1.5],
            "gamma": [0.1, 0.8],
        },
    )


def _make_judgments(n: int = 50) -> list[JudgmentRecord]:
    """Create minimal synthetic judgments."""
    import random

    rng = random.Random(42)
    judgments: list[JudgmentRecord] = []
    for _ in range(n):
        judgments.append(
            JudgmentRecord(
                winner_scores={
                    "quality_prior": rng.uniform(0.1, 1.0),
                    "topical_fit": rng.uniform(0.1, 1.0),
                    "recency": rng.uniform(0.1, 1.0),
                },
                loser_scores={
                    "quality_prior": rng.uniform(0.1, 1.0),
                    "topical_fit": rng.uniform(0.1, 1.0),
                    "recency": rng.uniform(0.1, 1.0),
                },
            )
        )
    return judgments


class TestRefitScheduler:
    """Tests for RefitScheduler."""

    def test_should_refit_cold_start(self) -> None:
        """7+ days in cold_start returns True."""
        scheduler = RefitScheduler(
            weights_dir=Path("/tmp"),
            cadence=RefitCadence.cold_start,
        )
        now = datetime.now(tz=UTC)
        last = now - timedelta(days=8)
        assert scheduler.should_refit(last_refit=last, now=now) is True

    def test_should_refit_too_soon(self) -> None:
        """3 days in cold_start returns False."""
        scheduler = RefitScheduler(
            weights_dir=Path("/tmp"),
            cadence=RefitCadence.cold_start,
        )
        now = datetime.now(tz=UTC)
        last = now - timedelta(days=3)
        assert scheduler.should_refit(last_refit=last, now=now) is False

    def test_should_refit_steady_state(self) -> None:
        """30+ days in steady_state returns True."""
        scheduler = RefitScheduler(
            weights_dir=Path("/tmp"),
            cadence=RefitCadence.steady_state,
        )
        now = datetime.now(tz=UTC)
        last = now - timedelta(days=31)
        assert scheduler.should_refit(last_refit=last, now=now) is True

    def test_execute_refit_writes_yaml(self, tmp_path: Path) -> None:
        """Verify YAML created with bumped version."""
        weights = _make_weight_vector(version=1)
        scheduler = RefitScheduler(
            weights_dir=tmp_path,
            current_version=1,
        )
        fitter = PlackettLuceFitter()
        judgments = _make_judgments(50)

        result = scheduler.execute_refit(
            fitter=fitter,
            judgments=judgments,
            current_weights=weights,
        )

        assert result.new_version == 2
        output = Path(result.output_path)
        assert output.exists()

        with open(output) as f:
            data = yaml.safe_load(f)
        assert data["version"] == 2
        assert data["specialty"] == "translational"
        assert "alpha" in data["exponents"]
        assert "beta" in data["exponents"]
        assert "gamma" in data["exponents"]

    def test_rollback_loads_version(self, tmp_path: Path) -> None:
        """Write YAML, rollback, verify WeightVector."""
        # Write a v1 YAML file
        data = {
            "version": 1,
            "specialty": "translational",
            "created": "2026-04-25",
            "weights": {"f1_rcr": 0.5, "f2_funding": 0.5},
            "exponents": {"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
            "exponent_bounds": {
                "alpha": [0.3, 1.2],
                "beta": [0.5, 1.5],
                "gamma": [0.1, 0.8],
            },
        }
        yaml_path = tmp_path / "translational_v1.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(data, f)

        scheduler = RefitScheduler(weights_dir=tmp_path)
        loaded = scheduler.rollback(
            weights_dir=tmp_path, target_version=1
        )

        assert isinstance(loaded, WeightVector)
        assert loaded.version == 1
        assert loaded.specialty == "translational"
        assert loaded.exponents["alpha"] == 0.7
