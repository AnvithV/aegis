"""Tests for query latency SLO monitor."""

from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry

from aegis.observability.query_slo import (
    QuerySloMonitor,
)


def _make_monitor() -> QuerySloMonitor:
    return QuerySloMonitor(registry=CollectorRegistry())


def test_record_and_report_basic() -> None:
    """Record 100 requests with 200ms latency, all success."""
    m = _make_monitor()
    for _ in range(100):
        m.record_request("cust-1", "cohort-a", 200.0, success=True)

    report = m.get_status_report()
    assert report.total_requests == 100
    assert report.success_count == 100
    assert report.failure_count == 0
    assert report.p95_latency_ms < 500
    assert report.p99_latency_ms < 1500
    assert report.success_rate == 1.0
    assert report.p95_slo_met is True
    assert report.p99_slo_met is True
    assert report.success_rate_slo_met is True
    assert report.error_budget_consumed_pct == 0.0


def test_p95_breach() -> None:
    """Record 100 requests, 6 with 600ms latency. p95 should breach."""
    m = _make_monitor()
    for _ in range(94):
        m.record_request("cust-1", None, 200.0, success=True)
    for _ in range(6):
        m.record_request("cust-1", None, 600.0, success=True)

    report = m.get_status_report()
    assert report.p95_slo_met is False


def test_p99_breach() -> None:
    """Record 100 requests, 2 with 2000ms latency. p99 should breach."""
    m = _make_monitor()
    for _ in range(98):
        m.record_request("cust-1", None, 200.0, success=True)
    for _ in range(2):
        m.record_request("cust-1", None, 2000.0, success=True)

    report = m.get_status_report()
    assert report.p99_slo_met is False


def test_success_rate_breach() -> None:
    """Record 1000 requests, 2 failures. Success rate should breach 99.9%."""
    m = _make_monitor()
    for _ in range(998):
        m.record_request("cust-1", None, 200.0, success=True)
    for _ in range(2):
        m.record_request("cust-1", None, 200.0, success=False)

    report = m.get_status_report()
    assert report.success_rate < 0.999
    assert report.success_rate_slo_met is False


def test_error_budget_tracking() -> None:
    """Record requests with known failure rate, verify budget consumption."""
    m = _make_monitor()
    # With 1000 requests and 0.1% allowed failure rate,
    # allowed failures = 1.0
    # If we have 1 failure, budget consumed = 100%
    for _ in range(999):
        m.record_request("cust-1", None, 200.0, success=True)
    m.record_request("cust-1", None, 200.0, success=False)

    report = m.get_status_report()
    assert report.error_budget_consumed_pct == pytest.approx(100.0)
    assert m.is_budget_breached() is True


def test_customer_cohort_breakdown() -> None:
    """Record requests from 2 customers with different cohorts."""
    m = _make_monitor()
    for _ in range(50):
        m.record_request("cust-1", "cohort-a", 200.0, success=True)
    for _ in range(50):
        m.record_request("cust-2", "cohort-b", 400.0, success=True)

    breakdown = m.get_customer_breakdown()
    assert len(breakdown) == 2

    cust1 = [b for b in breakdown if b.customer_id == "cust-1"][0]
    cust2 = [b for b in breakdown if b.customer_id == "cust-2"][0]

    assert cust1.total_requests == 50
    assert cust1.cohort == "cohort-a"
    assert cust1.p95_latency_ms == 200.0
    assert cust1.success_rate == 1.0

    assert cust2.total_requests == 50
    assert cust2.cohort == "cohort-b"
    assert cust2.p95_latency_ms == 400.0
    assert cust2.success_rate == 1.0


def test_prometheus_metrics_exposed() -> None:
    """Record requests, verify Prometheus text contains expected metric names."""
    m = _make_monitor()
    m.record_request("cust-1", "cohort-a", 200.0, success=True)

    text = m.expose_metrics()
    assert "aegis_query_latency_seconds" in text
    assert "aegis_query_requests_total" in text
    assert "aegis_query_p95_latency_ms" in text
    assert "aegis_query_p99_latency_ms" in text
    assert "aegis_query_success_rate" in text
    assert "aegis_query_error_budget_consumed_pct" in text


def test_empty_window() -> None:
    """Call get_status_report with no requests, verify defaults."""
    m = _make_monitor()
    report = m.get_status_report()
    assert report.total_requests == 0
    assert report.success_rate == 1.0
    assert report.p95_slo_met is True
    assert report.p99_slo_met is True
    assert report.success_rate_slo_met is True
    assert report.error_budget_consumed_pct == 0.0
    assert m.is_budget_breached() is False
