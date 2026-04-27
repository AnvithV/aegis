"""Tests for API health metrics."""

from __future__ import annotations

from prometheus_client import CollectorRegistry

from aegis.observability.api_health import ApiHealthMetrics


def _make_metrics() -> ApiHealthMetrics:
    return ApiHealthMetrics(registry=CollectorRegistry())


def test_record_success() -> None:
    """Recording a success request increments the counter."""
    m = _make_metrics()
    m.record_request("pubmed", "success", 0.5)

    val = m._requests_total.labels(source="pubmed", status="success")._value.get()
    assert val == 1.0


def test_record_http_error() -> None:
    """Recording HTTP errors increments error counters."""
    m = _make_metrics()
    m.record_request("pubmed", "http_5xx", 1.2)
    m.record_request("pubmed", "http_4xx", 0.3)

    val_5xx = m._requests_total.labels(source="pubmed", status="http_5xx")._value.get()
    val_4xx = m._requests_total.labels(source="pubmed", status="http_4xx")._value.get()
    assert val_5xx == 1.0
    assert val_4xx == 1.0


def test_record_parse_error() -> None:
    """record_parse_error increments the parse-error counter."""
    m = _make_metrics()
    m.record_parse_error("ctgov", "missing field: nct_id")
    m.record_parse_error("ctgov", "invalid date format")

    val = m._parse_errors.labels(source="ctgov")._value.get()
    assert val == 2.0


def test_record_rate_limit() -> None:
    """record_rate_limit_hit increments the rate-limit counter."""
    m = _make_metrics()
    m.record_rate_limit_hit("reporter")
    m.record_rate_limit_hit("reporter")
    m.record_rate_limit_hit("reporter")

    val = m._rate_limit_hits.labels(source="reporter")._value.get()
    assert val == 3.0


def test_latency_histogram() -> None:
    """Latency observations are recorded in the histogram."""
    m = _make_metrics()
    m.record_request("pubmed", "success", 0.15)
    m.record_request("pubmed", "success", 2.5)

    hist_sum = m._latency.labels(source="pubmed")._sum.get()
    assert abs(hist_sum - 2.65) < 0.01


def test_health_summary() -> None:
    """get_health_summary computes error rates correctly."""
    m = _make_metrics()
    for _ in range(8):
        m.record_request("pubmed", "success", 0.1)
    m.record_request("pubmed", "http_5xx", 1.0)
    m.record_request("pubmed", "timeout", 5.0)

    summary = m.get_health_summary()
    assert "pubmed" in summary
    assert summary["pubmed"]["total_requests"] == 10
    assert summary["pubmed"]["success_count"] == 8
    assert summary["pubmed"]["error_count"] == 2
    assert abs(summary["pubmed"]["error_rate"] - 0.2) < 0.01


def test_prometheus_format() -> None:
    """expose_metrics returns valid Prometheus text."""
    m = _make_metrics()
    m.record_request("pubmed", "success", 0.2)
    m.record_rate_limit_hit("pubmed")

    text = m.expose_metrics()
    assert "aegis_api_requests_total" in text
    assert "aegis_api_latency_seconds" in text
    assert "aegis_api_rate_limit_hits_total" in text
    assert 'source="pubmed"' in text


def test_http_vs_parse_distinction() -> None:
    """HTTP errors and parse errors are tracked independently."""
    m = _make_metrics()
    m.record_request("ctgov", "http_5xx", 1.0)
    m.record_request("ctgov", "parse_error", 0.5)
    m.record_parse_error("ctgov", "bad json")

    summary = m.get_health_summary()
    # http_5xx counted as error, parse_error counted separately
    assert summary["ctgov"]["error_count"] == 1  # only http_5xx
    assert summary["ctgov"]["parse_error_count"] == 1
    # parse_errors counter has 1 from record_parse_error
    val = m._parse_errors.labels(source="ctgov")._value.get()
    assert val == 1.0
