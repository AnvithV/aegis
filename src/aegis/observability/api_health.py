"""Per-API call success/failure tracking with latency and rate-limit metrics."""

from __future__ import annotations

from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

_LATENCY_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

_VALID_STATUSES = frozenset(
    {"success", "http_4xx", "http_5xx", "timeout", "parse_error"}
)


class ApiHealthMetrics:
    """Track per-source API call success/failure, latency, and rate limits."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry or CollectorRegistry()

        self._requests_total = Counter(
            "aegis_api_requests_total",
            "Total API requests per source and status",
            ["source", "status"],
            registry=self._registry,
        )
        self._latency = Histogram(
            "aegis_api_latency_seconds",
            "API call latency in seconds",
            ["source"],
            buckets=_LATENCY_BUCKETS,
            registry=self._registry,
        )
        self._rate_limit_hits = Counter(
            "aegis_api_rate_limit_hits_total",
            "Total rate-limit hits per source",
            ["source"],
            registry=self._registry,
        )
        self._parse_errors = Counter(
            "aegis_api_parse_errors_total",
            "Total parse errors per source",
            ["source"],
            registry=self._registry,
        )
        # Internal tracking for summary
        self._request_counts: dict[str, dict[str, int]] = {}
        self._parse_error_details: dict[str, list[str]] = {}

    def record_request(
        self, source: str, status: str, latency_seconds: float
    ) -> None:
        """Record an API request with its outcome and latency."""
        self._requests_total.labels(source=source, status=status).inc()
        self._latency.labels(source=source).observe(latency_seconds)

        src_counts = self._request_counts.setdefault(source, {})
        src_counts[status] = src_counts.get(status, 0) + 1

    def record_rate_limit_hit(self, source: str) -> None:
        """Record a rate-limit hit for a source."""
        self._rate_limit_hits.labels(source=source).inc()

    def record_parse_error(
        self, source: str, error_detail: str
    ) -> None:
        """Record a parse/schema error for a source."""
        self._parse_errors.labels(source=source).inc()
        self._parse_error_details.setdefault(source, []).append(
            error_detail
        )

    def get_health_summary(self) -> dict[str, dict[str, Any]]:
        """Return a per-source health summary dict."""
        summary: dict[str, dict[str, Any]] = {}
        for source, counts in self._request_counts.items():
            total = sum(counts.values())
            errors = (
                counts.get("http_4xx", 0)
                + counts.get("http_5xx", 0)
                + counts.get("timeout", 0)
            )
            parse_errs = counts.get("parse_error", 0)
            error_rate = errors / total if total > 0 else 0.0
            summary[source] = {
                "total_requests": total,
                "success_count": counts.get("success", 0),
                "error_count": errors,
                "parse_error_count": parse_errs,
                "error_rate": error_rate,
            }
        return summary

    def expose_metrics(self) -> str:
        """Return metrics in Prometheus exposition format."""
        return generate_latest(self._registry).decode("utf-8")
