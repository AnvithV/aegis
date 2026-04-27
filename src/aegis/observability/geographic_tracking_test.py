"""Tests for geographic-coverage tracking over time."""

from __future__ import annotations

from pathlib import Path

from aegis.observability.geographic_tracking import (
    GeographicSnapshot,
    GeographicTracker,
)
from aegis.observability.regional_coverage import RegionalCoverageMetrics
from aegis.sources.non_us_grants import Region


def _make_metrics(non_us_ratio: float, total: int = 100) -> RegionalCoverageMetrics:
    """Build a minimal RegionalCoverageMetrics for testing."""
    us_count = int(total * (1 - non_us_ratio))
    non_us_count = total - us_count
    return RegionalCoverageMetrics(
        total_candidates=total,
        per_region_count={
            Region.US.value: us_count,
            Region.EU.value: non_us_count,
            Region.UK.value: 0,
            Region.CANADA.value: 0,
            Region.JAPAN.value: 0,
            Region.CHINA.value: 0,
            Region.REST_OF_WORLD.value: 0,
        },
        per_region_pct={
            Region.US.value: round(100.0 * us_count / total, 2),
            Region.EU.value: round(100.0 * non_us_count / total, 2),
            Region.UK.value: 0.0,
            Region.CANADA.value: 0.0,
            Region.JAPAN.value: 0.0,
            Region.CHINA.value: 0.0,
            Region.REST_OF_WORLD.value: 0.0,
        },
        non_us_ratio=non_us_ratio,
        dominant_region=Region.US.value,
        dominant_region_pct=round(100.0 * us_count / total, 2),
        is_geographically_biased=False,
        per_region_linkage_confidence={},
        per_region_source_coverage={},
        coverage_caveats=[],
        regional_caveat=None,
    )


def test_record_snapshot(tmp_path: Path) -> None:
    """Snapshot creation and JSONL persistence."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    metrics = _make_metrics(non_us_ratio=0.35)
    snapshot = tracker.record_snapshot(metrics, active_sources=["erc", "mrc"])

    assert isinstance(snapshot, GeographicSnapshot)
    assert snapshot.non_us_ratio == 0.35
    assert "erc" in snapshot.new_sources_active
    assert (tmp_path / "tracking.jsonl").exists()


def test_load_history(tmp_path: Path) -> None:
    """Reading back from JSONL works correctly."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    tracker.record_snapshot(_make_metrics(0.30), ["erc"])
    tracker.record_snapshot(_make_metrics(0.35), ["erc", "mrc"])
    tracker.record_snapshot(_make_metrics(0.40), ["erc", "mrc", "cihr"])

    history = tracker.load_history()
    assert len(history) == 3
    assert history[0].non_us_ratio == 0.30
    assert history[2].non_us_ratio == 0.40


def test_compute_trend_improving(tmp_path: Path) -> None:
    """4 snapshots with increasing ratio produce 'improving' trend."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    for ratio in [0.20, 0.25, 0.30, 0.35]:
        tracker.record_snapshot(_make_metrics(ratio), ["erc"])

    trend = tracker.compute_trend()
    assert trend.ratio_trend == "improving"


def test_compute_trend_regressing(tmp_path: Path) -> None:
    """4 snapshots with decreasing ratio produce 'regressing' trend."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    for ratio in [0.40, 0.35, 0.30, 0.25]:
        tracker.record_snapshot(_make_metrics(ratio), ["erc"])

    trend = tracker.compute_trend()
    assert trend.ratio_trend == "regressing"


def test_regression_alert(tmp_path: Path) -> None:
    """>5% drop from previous snapshot triggers regression alert."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    tracker.record_snapshot(_make_metrics(0.45), ["erc"])
    tracker.record_snapshot(_make_metrics(0.38), ["erc"])  # drop of 0.07

    trend = tracker.compute_trend()
    assert trend.regression_alert is True


def test_target_met(tmp_path: Path) -> None:
    """non_us_ratio >= 0.40 means target_met=True."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    tracker.record_snapshot(_make_metrics(0.42), ["erc", "mrc"])

    trend = tracker.compute_trend()
    assert trend.target_met is True
    assert trend.current_non_us_ratio == 0.42


def test_target_not_met(tmp_path: Path) -> None:
    """non_us_ratio < 0.40 means target_met=False."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    tracker.record_snapshot(_make_metrics(0.35), ["erc"])

    trend = tracker.compute_trend()
    assert trend.target_met is False
    assert trend.current_non_us_ratio == 0.35


def test_empty_history(tmp_path: Path) -> None:
    """Empty history returns stable trend with no alert."""
    tracker = GeographicTracker(store_path=str(tmp_path / "nonexistent.jsonl"))
    trend = tracker.compute_trend()

    assert trend.ratio_trend == "stable"
    assert trend.regression_alert is False
    assert trend.target_met is False
    assert len(trend.snapshots) == 0


def test_prometheus_metrics(tmp_path: Path) -> None:
    """Prometheus metrics are generated as text."""
    tracker = GeographicTracker(store_path=str(tmp_path / "tracking.jsonl"))
    tracker.record_snapshot(_make_metrics(0.42), ["erc"])

    output = tracker.generate_prometheus_metrics()
    assert "aegis_geographic_non_us_ratio" in output
    assert "aegis_geographic_target_met" in output
