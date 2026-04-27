"""Tests for per-customer task-quality tracker."""

from __future__ import annotations

from datetime import date, timedelta

from aegis.observability.customer_quality import (
    CustomerQualitySnapshot,
    CustomerQualityTracker,
)


def _make_tracker(tmp_path: object) -> CustomerQualityTracker:
    return CustomerQualityTracker(db_path=str(tmp_path) + "/test.duckdb")


def test_record_and_retrieve_snapshot(tmp_path: object) -> None:
    """Record a snapshot, retrieve it, verify all fields match."""
    tracker = _make_tracker(tmp_path)
    snap = CustomerQualitySnapshot(
        customer_id="cust-1",
        snapshot_date=date(2026, 4, 1),
        fleiss_kappa=0.75,
        accept_rate=0.85,
        task_count=50,
        total_candidates_evaluated=500,
    )
    tracker.record_snapshot(snap)

    result = tracker.get_snapshots("cust-1")
    assert len(result) == 1
    assert result[0].customer_id == "cust-1"
    assert result[0].fleiss_kappa == 0.75
    assert result[0].accept_rate == 0.85
    assert result[0].task_count == 50
    assert result[0].total_candidates_evaluated == 500


def test_upsert_snapshot(tmp_path: object) -> None:
    """Record same customer+date twice, verify second write wins."""
    tracker = _make_tracker(tmp_path)
    snap1 = CustomerQualitySnapshot(
        customer_id="cust-1",
        snapshot_date=date(2026, 4, 1),
        fleiss_kappa=0.75,
        accept_rate=0.85,
        task_count=50,
        total_candidates_evaluated=500,
    )
    snap2 = CustomerQualitySnapshot(
        customer_id="cust-1",
        snapshot_date=date(2026, 4, 1),
        fleiss_kappa=0.80,
        accept_rate=0.90,
        task_count=60,
        total_candidates_evaluated=600,
    )
    tracker.record_snapshot(snap1)
    tracker.record_snapshot(snap2)

    result = tracker.get_snapshots("cust-1")
    assert len(result) == 1
    assert result[0].fleiss_kappa == 0.80
    assert result[0].accept_rate == 0.90


def test_trend_computation_positive(tmp_path: object) -> None:
    """Record 5 snapshots with increasing kappa, verify positive slope."""
    tracker = _make_tracker(tmp_path)
    base_date = date(2026, 1, 1)
    for i in range(5):
        tracker.record_snapshot(
            CustomerQualitySnapshot(
                customer_id="cust-1",
                snapshot_date=base_date + timedelta(weeks=i),
                fleiss_kappa=0.50 + i * 0.05,
                accept_rate=0.80,
                task_count=50,
                total_candidates_evaluated=500,
            )
        )

    trend = tracker.compute_trend("cust-1")
    assert trend is not None
    assert trend.kappa_slope > 0
    assert trend.kappa_improving is True


def test_trend_computation_negative(tmp_path: object) -> None:
    """Record 5 snapshots with decreasing accept_rate, verify negative slope."""
    tracker = _make_tracker(tmp_path)
    base_date = date(2026, 1, 1)
    for i in range(5):
        tracker.record_snapshot(
            CustomerQualitySnapshot(
                customer_id="cust-1",
                snapshot_date=base_date + timedelta(weeks=i),
                fleiss_kappa=0.75,
                accept_rate=0.90 - i * 0.05,
                task_count=50,
                total_candidates_evaluated=500,
            )
        )

    trend = tracker.compute_trend("cust-1")
    assert trend is not None
    assert trend.accept_rate_slope < 0
    assert trend.accept_rate_improving is False


def test_trend_insufficient_data(tmp_path: object) -> None:
    """Record 2 snapshots, verify compute_trend returns None (min_points=4)."""
    tracker = _make_tracker(tmp_path)
    for i in range(2):
        tracker.record_snapshot(
            CustomerQualitySnapshot(
                customer_id="cust-1",
                snapshot_date=date(2026, 1, 1) + timedelta(weeks=i),
                fleiss_kappa=0.75,
                accept_rate=0.85,
                task_count=50,
                total_candidates_evaluated=500,
            )
        )

    trend = tracker.compute_trend("cust-1")
    assert trend is None


def test_kappa_decline_alert(tmp_path: object) -> None:
    """Record 2 snapshots with kappa drop > 0.1, verify alert fires."""
    tracker = _make_tracker(tmp_path)
    tracker.record_snapshot(
        CustomerQualitySnapshot(
            customer_id="cust-1",
            snapshot_date=date(2026, 4, 1),
            fleiss_kappa=0.80,
            accept_rate=0.85,
            task_count=50,
            total_candidates_evaluated=500,
        )
    )
    tracker.record_snapshot(
        CustomerQualitySnapshot(
            customer_id="cust-1",
            snapshot_date=date(2026, 4, 8),
            fleiss_kappa=0.65,
            accept_rate=0.85,
            task_count=50,
            total_candidates_evaluated=500,
        )
    )

    alerts = tracker.check_alerts("cust-1")
    assert len(alerts) == 1
    assert alerts[0].alert_type == "kappa_decline"
    assert alerts[0].severity == "warning"


def test_no_alert_stable(tmp_path: object) -> None:
    """Record 2 snapshots with similar kappa, verify no alert."""
    tracker = _make_tracker(tmp_path)
    tracker.record_snapshot(
        CustomerQualitySnapshot(
            customer_id="cust-1",
            snapshot_date=date(2026, 4, 1),
            fleiss_kappa=0.75,
            accept_rate=0.85,
            task_count=50,
            total_candidates_evaluated=500,
        )
    )
    tracker.record_snapshot(
        CustomerQualitySnapshot(
            customer_id="cust-1",
            snapshot_date=date(2026, 4, 8),
            fleiss_kappa=0.74,
            accept_rate=0.84,
            task_count=50,
            total_candidates_evaluated=500,
        )
    )

    alerts = tracker.check_alerts("cust-1")
    assert len(alerts) == 0


def test_critical_severity(tmp_path: object) -> None:
    """Record a kappa drop > 0.2 (2x threshold), verify severity is critical."""
    tracker = _make_tracker(tmp_path)
    tracker.record_snapshot(
        CustomerQualitySnapshot(
            customer_id="cust-1",
            snapshot_date=date(2026, 4, 1),
            fleiss_kappa=0.80,
            accept_rate=0.85,
            task_count=50,
            total_candidates_evaluated=500,
        )
    )
    tracker.record_snapshot(
        CustomerQualitySnapshot(
            customer_id="cust-1",
            snapshot_date=date(2026, 4, 8),
            fleiss_kappa=0.55,
            accept_rate=0.85,
            task_count=50,
            total_candidates_evaluated=500,
        )
    )

    alerts = tracker.check_alerts("cust-1")
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"


def test_generate_report(tmp_path: object) -> None:
    """Record 5 snapshots, call generate_report, verify all fields populated."""
    tracker = _make_tracker(tmp_path)
    base_date = date(2026, 1, 1)
    for i in range(5):
        tracker.record_snapshot(
            CustomerQualitySnapshot(
                customer_id="cust-1",
                snapshot_date=base_date + timedelta(weeks=i),
                fleiss_kappa=0.50 + i * 0.05,
                accept_rate=0.80 + i * 0.02,
                task_count=50,
                total_candidates_evaluated=500,
            )
        )

    report = tracker.generate_report("cust-1")
    assert report.customer_id == "cust-1"
    assert len(report.snapshots) == 5
    assert report.trend is not None
    assert report.generated_at is not None
    # Verify JSON serializable
    json_str = report.model_dump_json()
    assert "cust-1" in json_str


def test_cross_customer_summary(tmp_path: object) -> None:
    """Record snapshots for 2 customers, verify summary returns 2 reports."""
    tracker = _make_tracker(tmp_path)
    for cid in ["cust-1", "cust-2"]:
        tracker.record_snapshot(
            CustomerQualitySnapshot(
                customer_id=cid,
                snapshot_date=date(2026, 4, 1),
                fleiss_kappa=0.75,
                accept_rate=0.85,
                task_count=50,
                total_candidates_evaluated=500,
            )
        )

    summary = tracker.get_cross_customer_summary()
    assert len(summary) == 2
    customer_ids = {r.customer_id for r in summary}
    assert customer_ids == {"cust-1", "cust-2"}
