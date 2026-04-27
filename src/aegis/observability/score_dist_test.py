"""Tests for per-component score-distribution monitoring."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from aegis.observability.score_dist import (
    DistributionSnapshot,
    KSAlert,
    ScoreDistributionMonitor,
)


@pytest.fixture()
def monitor(tmp_path: Path) -> ScoreDistributionMonitor:
    """Create a ScoreDistributionMonitor backed by a temp DuckDB file."""
    db_path = str(tmp_path / "test_score_dist.duckdb")
    return ScoreDistributionMonitor(db_path=db_path)


def test_record_and_retrieve_snapshot(
    monitor: ScoreDistributionMonitor,
) -> None:
    """Recording scores produces a retrievable snapshot with correct stats."""
    rng = np.random.default_rng(42)
    scores = rng.normal(0.5, 0.1, size=200).tolist()
    snap = monitor.record_snapshot("f1_rcr", date(2024, 6, 15), scores)

    assert isinstance(snap, DistributionSnapshot)
    assert snap.component == "f1_rcr"
    assert snap.total_candidates == 200
    assert len(snap.bucket_edges) == 51  # 50 bins => 51 edges
    assert len(snap.counts) == 50
    assert sum(snap.counts) == 200
    assert abs(snap.mean - np.mean(scores)) < 1e-6

    # Retrieve from DB
    retrieved = monitor.get_snapshot("f1_rcr", date(2024, 6, 15))
    assert retrieved is not None
    assert retrieved.component == "f1_rcr"
    assert retrieved.total_candidates == 200
    assert retrieved.bucket_edges == snap.bucket_edges
    assert retrieved.counts == snap.counts


def test_uniform_distribution_no_alert(
    monitor: ScoreDistributionMonitor,
) -> None:
    """Two similar distributions should not trigger a KS alert."""
    rng = np.random.default_rng(42)
    scores_day1 = rng.normal(0.5, 0.1, size=500).tolist()
    scores_day2 = rng.normal(0.5, 0.1, size=500).tolist()

    monitor.record_snapshot("f1_rcr", date(2024, 6, 14), scores_day1)
    monitor.record_snapshot("f1_rcr", date(2024, 6, 15), scores_day2)

    alert = monitor.check_ks_anomaly(
        "f1_rcr", date(2024, 6, 15), date(2024, 6, 14)
    )
    assert alert is None


def test_shifted_distribution_triggers_alert(
    monitor: ScoreDistributionMonitor,
) -> None:
    """A significantly shifted distribution triggers a KS alert."""
    rng = np.random.default_rng(42)
    scores_day1 = rng.normal(0.5, 0.1, size=500).tolist()
    # Large shift in mean
    scores_day2 = rng.normal(0.9, 0.1, size=500).tolist()

    monitor.record_snapshot("f2_funding", date(2024, 6, 14), scores_day1)
    monitor.record_snapshot("f2_funding", date(2024, 6, 15), scores_day2)

    alert = monitor.check_ks_anomaly(
        "f2_funding", date(2024, 6, 15), date(2024, 6, 14)
    )
    assert alert is not None
    assert isinstance(alert, KSAlert)
    assert alert.ks_statistic > 0.1
    assert alert.component == "f2_funding"
    assert alert.severity in ("warning", "critical")


def test_html_report_generation(
    monitor: ScoreDistributionMonitor, tmp_path: Path
) -> None:
    """HTML report contains component names and distribution data."""
    rng = np.random.default_rng(42)
    scores = rng.normal(0.5, 0.1, size=100).tolist()
    monitor.record_snapshot("f1_rcr", date(2024, 6, 15), scores)

    html = monitor.generate_html_report(date(2024, 6, 15))
    assert "Score Distribution Dashboard" in html
    assert "f1_rcr" in html
    assert "Total Candidates" in html
    assert "100" in html

    # Test save_report
    report_path = str(tmp_path / "report.html")
    monitor.save_report(date(2024, 6, 15), path=report_path)
    assert Path(report_path).exists()
    content = Path(report_path).read_text()
    assert "f1_rcr" in content


def test_idempotent_upsert(
    monitor: ScoreDistributionMonitor,
) -> None:
    """Recording the same component+date twice updates rather than duplicating."""
    rng = np.random.default_rng(42)
    scores_v1 = rng.normal(0.5, 0.1, size=100).tolist()
    scores_v2 = rng.normal(0.7, 0.1, size=150).tolist()

    monitor.record_snapshot("f1_rcr", date(2024, 6, 15), scores_v1)
    monitor.record_snapshot("f1_rcr", date(2024, 6, 15), scores_v2)

    snap = monitor.get_snapshot("f1_rcr", date(2024, 6, 15))
    assert snap is not None
    assert snap.total_candidates == 150
    assert abs(snap.mean - float(np.mean(scores_v2))) < 1e-6
