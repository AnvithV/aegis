"""Per-source ingestion freshness metrics in Prometheus exposition format."""

from __future__ import annotations

import time
from datetime import datetime

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Per-source SLO thresholds in seconds
SOURCE_SLOS: dict[str, float] = {
    "pubmed": 24 * 3600,      # 24 hours
    "reporter": 48 * 3600,    # 48 hours
    "ctgov": 24 * 3600,       # 24 hours
}


class FreshnessMetrics:
    """Emit per-source ingestion freshness metrics."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry or CollectorRegistry()

        self._last_success = Gauge(
            "aegis_ingestion_last_success_seconds",
            "Epoch seconds of last successful pull",
            ["source"],
            registry=self._registry,
        )
        self._lag = Histogram(
            "aegis_ingestion_lag_seconds",
            "Lag between artifact publication and ingestion",
            ["source"],
            registry=self._registry,
        )
        self._gap_count = Gauge(
            "aegis_ingestion_gap_count",
            "Number of detected gaps per source",
            ["source"],
            registry=self._registry,
        )
        self._records_total = Counter(
            "aegis_ingestion_records_total",
            "Total records ingested per source",
            ["source"],
            registry=self._registry,
        )
        # Internal tracking for summary
        self._last_success_times: dict[str, float] = {}
        self._lag_observations: dict[str, list[float]] = {}
        self._gap_counts: dict[str, int] = {}

    def record_success(self, source: str) -> None:
        """Record a successful ingestion pull for a source."""
        now = time.time()
        self._last_success.labels(source=source).set(now)
        self._last_success_times[source] = now

    def record_lag(
        self, source: str, publication_date: datetime, ingestion_date: datetime
    ) -> None:
        """Observe lag between publication and ingestion."""
        lag = (ingestion_date - publication_date).total_seconds()
        self._lag.labels(source=source).observe(lag)
        self._lag_observations.setdefault(source, []).append(lag)

    def record_gap(self, source: str, gap_count: int) -> None:
        """Set the current gap count for a source."""
        self._gap_count.labels(source=source).set(gap_count)
        self._gap_counts[source] = gap_count

    def record_ingested(self, source: str, count: int) -> None:
        """Increment total records ingested for a source."""
        self._records_total.labels(source=source).inc(count)

    def get_freshness_summary(self) -> dict[str, dict[str, float]]:
        """Return a summary dict keyed by source."""
        now = time.time()
        summary: dict[str, dict[str, float]] = {}
        for source, ts in self._last_success_times.items():
            age = now - ts
            slo = SOURCE_SLOS.get(source, 24 * 3600)
            lags = self._lag_observations.get(source, [])
            avg_lag = sum(lags) / len(lags) if lags else 0.0
            summary[source] = {
                "age_seconds": age,
                "slo_seconds": slo,
                "slo_met": 1.0 if age <= slo else 0.0,
                "avg_lag_seconds": avg_lag,
                "gap_count": float(self._gap_counts.get(source, 0)),
            }
        return summary

    def expose_metrics(self) -> str:
        """Return metrics in Prometheus exposition format."""
        return generate_latest(self._registry).decode("utf-8")
