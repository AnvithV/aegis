"""Tests for per-source artifact count drift detection."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from aegis.observability.drift import DriftAlert, DriftDetector


@pytest.fixture()
def detector(tmp_path: Path) -> DriftDetector:
    """Create a DriftDetector backed by a temp DuckDB file."""
    db_path = str(tmp_path / "test_drift.duckdb")
    return DriftDetector(db_path=db_path)


def _seed_baseline(
    detector: DriftDetector,
    source: str,
    end_date: date,
    count: int,
    days: int = 14,
) -> None:
    """Seed stable daily counts for the baseline window."""
    for i in range(days, 0, -1):
        d = end_date - timedelta(days=i)
        detector.record_daily_count(source, d, count)


def test_baseline_computation(detector: DriftDetector) -> None:
    """Baseline mean and stddev computed from prior days."""
    check = date(2024, 6, 15)
    _seed_baseline(detector, "pubmed", check, 100)

    mean, stddev = detector.get_baseline("pubmed", check)
    assert abs(mean - 100.0) < 0.01
    assert stddev == 0.0  # all same value


def test_no_drift_normal_variation(detector: DriftDetector) -> None:
    """Small variation should not trigger an alert."""
    check = date(2024, 6, 15)
    _seed_baseline(detector, "pubmed", check, 100)
    detector.record_daily_count("pubmed", check, 95)

    alert = detector.check_drift("pubmed", check)
    assert alert is None


def test_drift_30pct_drop(detector: DriftDetector) -> None:
    """A 30%+ drop triggers a critical alert."""
    check = date(2024, 6, 15)
    _seed_baseline(detector, "pubmed", check, 100)
    detector.record_daily_count("pubmed", check, 60)

    alert = detector.check_drift("pubmed", check)
    assert alert is not None
    assert isinstance(alert, DriftAlert)
    assert alert.severity == "critical"
    assert alert.drop_pct >= 0.3
    assert alert.source == "pubmed"


def test_drift_z_score_alert(detector: DriftDetector) -> None:
    """A z-score above threshold triggers a warning alert."""
    check = date(2024, 6, 15)
    # Seed varying counts so stddev > 0
    base = date(2024, 6, 15)
    counts = [100, 105, 98, 102, 97, 103, 101, 99, 104, 96, 100, 98, 102, 101]
    for i, c in enumerate(counts):
        d = base - timedelta(days=14 - i)
        detector.record_daily_count("ctgov", d, c)

    # Record a count that is a big deviation but < 30% drop
    detector.record_daily_count("ctgov", check, 80)

    alert = detector.check_drift("ctgov", check)
    assert alert is not None
    assert alert.z_score >= 2.0


def test_no_data_no_alert(detector: DriftDetector) -> None:
    """No data for a source returns None."""
    alert = detector.check_drift("unknown", date(2024, 6, 15))
    assert alert is None


def test_multiple_sources(detector: DriftDetector) -> None:
    """check_all_sources checks each source independently."""
    check = date(2024, 6, 15)
    _seed_baseline(detector, "pubmed", check, 100)
    _seed_baseline(detector, "ctgov", check, 200)

    detector.record_daily_count("pubmed", check, 50)  # big drop
    detector.record_daily_count("ctgov", check, 195)  # normal

    alerts = detector.check_all_sources(check)
    sources = {a.source for a in alerts}
    assert "pubmed" in sources
    assert "ctgov" not in sources


def test_idempotent_daily_record(detector: DriftDetector) -> None:
    """Recording the same date twice updates rather than duplicating."""
    d1 = date(2024, 6, 9)
    d2 = date(2024, 6, 10)
    detector.record_daily_count("pubmed", d1, 100)
    detector.record_daily_count("pubmed", d2, 100)
    # Upsert same date with new value
    detector.record_daily_count("pubmed", d2, 150)

    mean, _ = detector.get_baseline("pubmed", date(2024, 6, 11))
    # mean of [100, 150] = 125
    assert abs(mean - 125.0) < 0.01
