"""Tests for ingestion freshness metrics."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from prometheus_client import CollectorRegistry

from aegis.observability.freshness import FreshnessMetrics


def _make_metrics() -> FreshnessMetrics:
    return FreshnessMetrics(registry=CollectorRegistry())


def test_record_success_updates_gauge() -> None:
    """record_success sets the last-success gauge to current time."""
    m = _make_metrics()
    before = time.time()
    m.record_success("pubmed")
    after = time.time()

    val = m._last_success.labels(source="pubmed")._value.get()
    assert before <= val <= after


def test_record_lag_observes_histogram() -> None:
    """record_lag observes the difference in seconds."""
    m = _make_metrics()
    pub = datetime(2024, 6, 1, tzinfo=UTC)
    ing = datetime(2024, 6, 2, tzinfo=UTC)
    m.record_lag("pubmed", pub, ing)

    # Histogram sum should equal 86400 seconds (1 day)
    assert m._lag.labels(source="pubmed")._sum.get() == 86400.0


def test_record_gap_updates_gauge() -> None:
    """record_gap sets the gap-count gauge."""
    m = _make_metrics()
    m.record_gap("ctgov", 5)
    assert m._gap_count.labels(source="ctgov")._value.get() == 5.0

    m.record_gap("ctgov", 3)
    assert m._gap_count.labels(source="ctgov")._value.get() == 3.0


def test_expose_metrics_prometheus_format() -> None:
    """expose_metrics returns valid Prometheus text."""
    m = _make_metrics()
    m.record_success("pubmed")
    m.record_ingested("pubmed", 100)
    m.record_gap("pubmed", 2)

    text = m.expose_metrics()
    assert "aegis_ingestion_last_success_seconds" in text
    assert "aegis_ingestion_records_total" in text
    assert "aegis_ingestion_gap_count" in text
    assert 'source="pubmed"' in text


def test_freshness_summary() -> None:
    """get_freshness_summary returns per-source dict with SLO info."""
    m = _make_metrics()
    m.record_success("pubmed")
    m.record_gap("pubmed", 1)

    pub = datetime(2024, 6, 1, tzinfo=UTC)
    ing = datetime(2024, 6, 1, 12, tzinfo=UTC)
    m.record_lag("pubmed", pub, ing)

    summary = m.get_freshness_summary()
    assert "pubmed" in summary
    assert summary["pubmed"]["slo_seconds"] == 86400.0
    assert summary["pubmed"]["avg_lag_seconds"] == 43200.0
    assert summary["pubmed"]["gap_count"] == 1.0
    # Just recorded, so should meet SLO
    assert summary["pubmed"]["slo_met"] == 1.0


def test_freshness_lag_increases_on_pause() -> None:
    """After recording success, age grows, eventually breaching SLO."""
    m = _make_metrics()
    # Simulate a success that happened a long time ago
    m._last_success.labels(source="pubmed").set(time.time() - 100_000)
    m._last_success_times["pubmed"] = time.time() - 100_000

    summary = m.get_freshness_summary()
    assert summary["pubmed"]["slo_met"] == 0.0
    assert summary["pubmed"]["age_seconds"] >= 100_000
