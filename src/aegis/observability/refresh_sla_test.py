"""Tests for refresh-cadence SLA tracker."""

from __future__ import annotations

import time

from prometheus_client import CollectorRegistry

from aegis.observability.refresh_sla import (
    HARD_GATE_SOURCES,
    RefreshSlaTracker,
)


def _make_tracker() -> RefreshSlaTracker:
    return RefreshSlaTracker(registry=CollectorRegistry())


def test_compliant_source() -> None:
    """Record success for pubmed within its SLA, verify compliant."""
    tracker = _make_tracker()
    tracker.record_success("pubmed")

    status = tracker.check_source("pubmed")
    assert status.is_compliant is True
    assert status.breach_severity is None


def test_hard_gate_breach() -> None:
    """Set retraction_watch last success to 8 hours ago (SLA is 6h)."""
    tracker = _make_tracker()
    stuck_epoch = time.time() - (8 * 3600)
    tracker.record_success_at("retraction_watch", stuck_epoch)

    status = tracker.check_source("retraction_watch")
    assert status.is_compliant is False
    assert status.is_hard_gate is True
    assert status.breach_severity == "critical"


def test_non_hard_gate_breach() -> None:
    """Set pubmed last success to 30 hours ago (SLA is 24h)."""
    tracker = _make_tracker()
    stuck_epoch = time.time() - (30 * 3600)
    tracker.record_success_at("pubmed", stuck_epoch)

    status = tracker.check_source("pubmed")
    assert status.is_compliant is False
    assert status.is_hard_gate is False
    assert status.breach_severity == "warning"


def test_never_reported_source() -> None:
    """Do NOT record success for a source in SOURCE_SLOS, verify non-compliant."""
    tracker = _make_tracker()

    status = tracker.check_source("pubmed")
    assert status.is_compliant is False
    assert status.last_success_epoch is None
    assert status.age_seconds is None


def test_check_all_sources() -> None:
    """Record success for some sources, verify check_all_sources returns all."""
    tracker = _make_tracker()
    tracker.record_success("pubmed")
    tracker.record_success("retraction_watch")

    statuses = tracker.check_all_sources()
    # Should have an entry for every source in SOURCE_SLOS
    from aegis.observability.freshness import SOURCE_SLOS

    assert len(statuses) == len(SOURCE_SLOS)

    source_names = {s.source for s in statuses}
    for source in SOURCE_SLOS:
        assert source in source_names


def test_breach_alerts_hard_gate_pages() -> None:
    """Create a hard-gate breach, verify page_oncall == True in the alert."""
    tracker = _make_tracker()
    stuck_epoch = time.time() - (8 * 3600)
    tracker.record_success_at("retraction_watch", stuck_epoch)

    # Make all other sources compliant to isolate the test
    from aegis.observability.freshness import SOURCE_SLOS

    for source in SOURCE_SLOS:
        if source != "retraction_watch":
            tracker.record_success(source)

    alerts = tracker.get_breach_alerts()
    rw_alerts = [a for a in alerts if a.source == "retraction_watch"]
    assert len(rw_alerts) == 1
    assert rw_alerts[0].page_oncall is True
    assert rw_alerts[0].severity == "critical"
    assert rw_alerts[0].is_hard_gate is True


def test_weekly_summary() -> None:
    """Create a mix of compliant and breached sources, verify summary."""
    tracker = _make_tracker()

    # Make pubmed compliant
    tracker.record_success("pubmed")

    # retraction_watch is breached (old success)
    stuck_epoch = time.time() - (8 * 3600)
    tracker.record_success_at("retraction_watch", stuck_epoch)

    # All other sources get fresh success
    from aegis.observability.freshness import SOURCE_SLOS

    for source in SOURCE_SLOS:
        if source not in ("pubmed", "retraction_watch"):
            tracker.record_success(source)

    summary = tracker.get_weekly_summary()
    assert summary.total_sources == len(SOURCE_SLOS)
    assert summary.breached_count >= 1
    assert summary.compliant_count == summary.total_sources - summary.breached_count
    assert 0.0 <= summary.compliance_rate <= 1.0


def test_prometheus_metrics() -> None:
    """Record success and check sources, verify Prometheus text."""
    tracker = _make_tracker()
    tracker.record_success("pubmed")
    tracker.check_source("pubmed")

    text = tracker.expose_metrics()
    assert "aegis_refresh_sla_compliant" in text
    assert "aegis_refresh_sla_overage_seconds" in text


def test_synthetic_stuck_source() -> None:
    """Synthetic stuck-source test: verify alerting fires for a source
    that has not reported success within its SLA."""
    tracker = RefreshSlaTracker(registry=CollectorRegistry())

    # Simulate "retraction_watch" stuck: last success was 12 hours ago
    # SLA is 6 hours
    stuck_epoch = time.time() - (12 * 3600)
    tracker.record_success_at("retraction_watch", stuck_epoch)

    # All other hard-gate sources are fresh
    for source in HARD_GATE_SOURCES:
        if source != "retraction_watch":
            tracker.record_success(source)

    alerts = tracker.get_breach_alerts()
    hard_gate_alerts = [
        a for a in alerts if a.is_hard_gate and a.source == "retraction_watch"
    ]
    assert len(hard_gate_alerts) == 1
    assert hard_gate_alerts[0].page_oncall is True
    assert hard_gate_alerts[0].severity == "critical"
    assert hard_gate_alerts[0].overage_seconds > 0
