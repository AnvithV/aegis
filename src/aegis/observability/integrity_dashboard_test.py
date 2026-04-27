"""Tests for integrity-gate hit-rate dashboard."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from aegis.observability.integrity_dashboard import (
    DailySummary,
    IntegrityDashboard,
    SpikeAlert,
)


@pytest.fixture()
def dashboard(tmp_path: Path) -> IntegrityDashboard:
    """Create an IntegrityDashboard backed by a temp DuckDB file."""
    db_path = str(tmp_path / "test_integrity.duckdb")
    return IntegrityDashboard(db_path=db_path)


def test_record_and_summarize(dashboard: IntegrityDashboard) -> None:
    """Recording events produces correct daily summary."""
    d = datetime.date(2024, 6, 15)
    dashboard.record_hard_zero(d, "uuid-1", "LEIE", "excluded")
    dashboard.record_hard_zero(d, "uuid-2", "ORI", "misconduct")
    dashboard.record_soft_discount(
        d, "uuid-3", "predatory_load", "high load"
    )

    summary = dashboard.get_daily_summary(d)
    assert isinstance(summary, DailySummary)
    assert summary.hard_zero_count == 2
    assert summary.soft_discount_count == 1
    assert summary.by_reason["LEIE"] == 1
    assert summary.by_reason["ORI"] == 1
    assert summary.by_reason["predatory_load"] == 1


def test_spike_detection(dashboard: IntegrityDashboard) -> None:
    """A spike above 3x baseline triggers an alert."""
    # Seed 14 days of baseline with 2 events per day
    base = datetime.date(2024, 6, 15)
    for i in range(14, 0, -1):
        d = base - datetime.timedelta(days=i)
        dashboard.record_hard_zero(d, f"uuid-a{i}", "LEIE")
        dashboard.record_hard_zero(d, f"uuid-b{i}", "LEIE")

    # Record a spike on the check date: 10 events (5x baseline mean of 2)
    for j in range(10):
        dashboard.record_hard_zero(base, f"uuid-spike-{j}", "LEIE")

    alert = dashboard.check_spike("hard_zero", "LEIE", base)
    assert alert is not None
    assert isinstance(alert, SpikeAlert)
    assert alert.current_count == 10
    assert alert.baseline_mean == 2.0
    assert alert.event_type == "hard_zero"
    assert alert.reason == "LEIE"


def test_no_spike_normal(dashboard: IntegrityDashboard) -> None:
    """Normal counts should not trigger a spike alert."""
    base = datetime.date(2024, 6, 15)
    for i in range(14, 0, -1):
        d = base - datetime.timedelta(days=i)
        dashboard.record_hard_zero(d, f"uuid-{i}", "LEIE")
        dashboard.record_hard_zero(d, f"uuid-{i}b", "LEIE")

    # Record normal count on check date
    dashboard.record_hard_zero(base, "uuid-today-1", "LEIE")
    dashboard.record_hard_zero(base, "uuid-today-2", "LEIE")

    alert = dashboard.check_spike("hard_zero", "LEIE", base)
    assert alert is None


def test_weekly_summary(dashboard: IntegrityDashboard) -> None:
    """Weekly summary returns 7 daily summaries."""
    base = datetime.date(2024, 6, 15)
    for i in range(7):
        d = base - datetime.timedelta(days=i)
        dashboard.record_hard_zero(d, f"uuid-{i}", "LEIE")

    summaries = dashboard.get_weekly_summary(base)
    assert len(summaries) == 7
    assert all(isinstance(s, DailySummary) for s in summaries)
    # Each day should have 1 hard_zero
    for s in summaries:
        assert s.hard_zero_count == 1


def test_html_report(
    dashboard: IntegrityDashboard, tmp_path: Path
) -> None:
    """HTML report contains expected sections."""
    d = datetime.date(2024, 6, 15)
    dashboard.record_hard_zero(d, "uuid-1", "LEIE", "excluded")
    dashboard.record_soft_discount(
        d, "uuid-2", "predatory_load", "high"
    )

    html = dashboard.generate_html_report(d)
    assert "Integrity Gate Dashboard" in html
    assert "Hard Zero" in html
    assert "Soft Discount" in html
    assert "LEIE" in html

    report_path = str(tmp_path / "report.html")
    dashboard.save_report(d, path=report_path)
    assert Path(report_path).exists()
    content = Path(report_path).read_text()
    assert "Integrity Gate Dashboard" in content
