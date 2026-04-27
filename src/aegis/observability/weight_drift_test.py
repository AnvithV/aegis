"""Tests for weight-drift time-series tracker."""

from __future__ import annotations

from datetime import date

from aegis.observability.weight_drift import (
    DriftAnnotation,
    JumpAlert,  # noqa: F401
    ParameterTimeSeries,  # noqa: F401
    WeightDriftReport,
    WeightDriftTracker,
    WeightSnapshot,
)
from aegis.scoring.quality_prior import WeightVector


def _make_tracker(tmp_path: object) -> WeightDriftTracker:
    """Create a tracker with a temporary DuckDB."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    return WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))


def test_record_and_retrieve_snapshot(tmp_path: object) -> None:
    """Record a single WeightSnapshot, query it back via get_time_series."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    snap = WeightSnapshot(
        specialty="translational",
        version=1,
        parameter_name="weight.f1_rcr",
        parameter_value=0.35,
        refit_date=date(2026, 4, 25),
    )
    tracker.record_snapshot(snap)
    ts = tracker.get_time_series("translational", "weight.f1_rcr")
    assert ts is not None
    assert ts.specialty == "translational"
    assert ts.parameter_name == "weight.f1_rcr"
    assert ts.versions == [1]
    assert ts.values == [0.35]
    assert ts.dates == [date(2026, 4, 25)]


def test_record_weight_vector(tmp_path: object) -> None:
    """Record a WeightVector and verify all 9 parameters are stored."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    wv = WeightVector(
        version=1,
        specialty="translational",
        weights={
            "f1_rcr": 0.35,
            "f2_funding": 0.25,
            "f3_leadership": 0.20,
            "f4_apex": 0.05,
            "f5_translational": 0.10,
            "f6_lineage": 0.05,
        },
        exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
        exponent_bounds={
            "alpha": [0.3, 1.2],
            "beta": [0.5, 1.5],
            "gamma": [0.1, 0.8],
        },
    )
    tracker.record_weight_vector(wv, date(2026, 4, 25))
    all_ts = tracker.get_all_time_series("translational")
    assert len(all_ts) == 9  # 6 weights + 3 exponents


def test_time_series_ordering(tmp_path: object) -> None:
    """Record 3 versions, verify time series has versions in ascending order."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    for v in [3, 1, 2]:
        tracker.record_snapshot(
            WeightSnapshot(
                specialty="translational",
                version=v,
                parameter_name="exponent.alpha",
                parameter_value=0.7 + v * 0.01,
                refit_date=date(2026, 4, 20 + v),
            )
        )
    ts = tracker.get_time_series("translational", "exponent.alpha")
    assert ts is not None
    assert ts.versions == [1, 2, 3]


def test_detect_jump(tmp_path: object) -> None:
    """Detect a jump when alpha changes from 0.7 to 1.0 (42.8% change)."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=1,
            parameter_name="exponent.alpha",
            parameter_value=0.7,
            refit_date=date(2026, 4, 25),
        )
    )
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=2,
            parameter_name="exponent.alpha",
            parameter_value=1.0,
            refit_date=date(2026, 4, 26),
        )
    )
    alerts = tracker.detect_jumps("translational")
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.specialty == "translational"
    assert alert.parameter_name == "exponent.alpha"
    assert alert.old_version == 1
    assert alert.new_version == 2
    assert alert.old_value == 0.7
    assert alert.new_value == 1.0
    assert alert.relative_change_pct > 42.0
    assert alert.severity == "warning"


def test_no_jump_stable(tmp_path: object) -> None:
    """No jump when alpha changes from 0.7 to 0.75 (7.1% change)."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=1,
            parameter_name="exponent.alpha",
            parameter_value=0.7,
            refit_date=date(2026, 4, 25),
        )
    )
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=2,
            parameter_name="exponent.alpha",
            parameter_value=0.75,
            refit_date=date(2026, 4, 26),
        )
    )
    alerts = tracker.detect_jumps("translational")
    assert len(alerts) == 0


def test_annotation(tmp_path: object) -> None:
    """Record an annotation, retrieve it, verify fields."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    annotation = tracker.record_annotation(
        annotation_date=date(2026, 4, 25),
        event_description="EPO patent source ingested",
    )
    assert isinstance(annotation, DriftAnnotation)
    assert annotation.event_description == "EPO patent source ingested"
    assert annotation.annotation_date == date(2026, 4, 25)
    assert len(annotation.annotation_id) > 0

    retrieved = tracker.get_annotations()
    assert len(retrieved) == 1
    assert retrieved[0].annotation_id == annotation.annotation_id
    assert retrieved[0].event_description == "EPO patent source ingested"


def test_generate_report(tmp_path: object) -> None:
    """Record 3 versions with one jump, add annotation, verify report."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    # Version 1
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=1,
            parameter_name="exponent.alpha",
            parameter_value=0.7,
            refit_date=date(2026, 4, 23),
        )
    )
    # Version 2 -- stable
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=2,
            parameter_name="exponent.alpha",
            parameter_value=0.72,
            refit_date=date(2026, 4, 24),
        )
    )
    # Version 3 -- jump
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=3,
            parameter_name="exponent.alpha",
            parameter_value=1.0,
            refit_date=date(2026, 4, 25),
        )
    )
    tracker.record_annotation(
        annotation_date=date(2026, 4, 24),
        event_description="EPO patent source ingested",
    )

    report = tracker.generate_report()
    assert isinstance(report, WeightDriftReport)
    assert "translational" in report.specialties
    assert len(report.time_series) >= 1
    assert len(report.jump_alerts) >= 1
    assert len(report.annotations) == 1
    # Verify JSON-serializable
    report.model_dump_json()


def test_load_history_from_dir(tmp_path: object) -> None:
    """Write 2 weight YAML files, load them, verify 2 vectors loaded."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))

    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()

    yaml_content_v1 = """\
version: 1
specialty: translational
created: "2026-04-25"
weights:
  f1_rcr: 0.35
  f2_funding: 0.25
  f3_leadership: 0.20
  f4_apex: 0.05
  f5_translational: 0.10
  f6_lineage: 0.05
exponents:
  alpha: 0.7
  beta: 1.0
  gamma: 0.4
exponent_bounds:
  alpha: [0.3, 1.2]
  beta: [0.5, 1.5]
  gamma: [0.1, 0.8]
"""
    yaml_content_v2 = """\
version: 2
specialty: translational
created: "2026-04-26"
weights:
  f1_rcr: 0.30
  f2_funding: 0.25
  f3_leadership: 0.20
  f4_apex: 0.10
  f5_translational: 0.10
  f6_lineage: 0.05
exponents:
  alpha: 0.75
  beta: 1.0
  gamma: 0.4
exponent_bounds:
  alpha: [0.3, 1.2]
  beta: [0.5, 1.5]
  gamma: [0.1, 0.8]
"""
    (weights_dir / "translational_v1.yaml").write_text(yaml_content_v1)
    (weights_dir / "translational_v2.yaml").write_text(yaml_content_v2)

    loaded = tracker.load_history_from_dir(str(weights_dir))
    assert loaded == 2

    all_ts = tracker.get_all_time_series("translational")
    assert len(all_ts) == 9  # 6 weights + 3 exponents
    # Check that we have 2 versions for at least one parameter
    alpha_ts = tracker.get_time_series("translational", "exponent.alpha")
    assert alpha_ts is not None
    assert len(alpha_ts.versions) == 2


def test_multi_specialty_time_series(tmp_path: object) -> None:
    """Record vectors for two specialties, verify both returned."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    wv1 = WeightVector(
        version=1,
        specialty="translational",
        weights={
            "f1_rcr": 0.35,
            "f2_funding": 0.25,
            "f3_leadership": 0.20,
            "f4_apex": 0.05,
            "f5_translational": 0.10,
            "f6_lineage": 0.05,
        },
        exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
        exponent_bounds={
            "alpha": [0.3, 1.2],
            "beta": [0.5, 1.5],
            "gamma": [0.1, 0.8],
        },
    )
    wv2 = WeightVector(
        version=1,
        specialty="drug_discovery",
        weights={
            "f1_rcr": 0.30,
            "f2_funding": 0.20,
            "f3_leadership": 0.15,
            "f4_apex": 0.10,
            "f5_translational": 0.15,
            "f6_lineage": 0.10,
        },
        exponents={"alpha": 0.8, "beta": 0.9, "gamma": 0.5},
        exponent_bounds={
            "alpha": [0.3, 1.2],
            "beta": [0.5, 1.5],
            "gamma": [0.1, 0.8],
        },
    )
    tracker.record_weight_vector(wv1, date(2026, 4, 25))
    tracker.record_weight_vector(wv2, date(2026, 4, 25))

    all_ts = tracker.get_all_time_series()
    specialties_found = {ts.specialty for ts in all_ts}
    assert "translational" in specialties_found
    assert "drug_discovery" in specialties_found
    assert len(all_ts) == 18  # 9 params x 2 specialties


def test_critical_jump_severity(tmp_path: object) -> None:
    """A 60% change (>2x threshold of 25%) should be 'critical'."""
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    tracker = WeightDriftTracker(db_path=str(tmp_path / "test.duckdb"))
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=1,
            parameter_name="exponent.alpha",
            parameter_value=0.5,
            refit_date=date(2026, 4, 25),
        )
    )
    tracker.record_snapshot(
        WeightSnapshot(
            specialty="translational",
            version=2,
            parameter_name="exponent.alpha",
            parameter_value=0.8,
            refit_date=date(2026, 4, 26),
        )
    )
    alerts = tracker.detect_jumps("translational")
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"
    assert alerts[0].relative_change_pct == 60.0
