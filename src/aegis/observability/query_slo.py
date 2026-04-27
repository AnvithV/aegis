"""Query latency SLO monitoring with Prometheus metrics and error-budget tracking."""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, ConfigDict


class SloTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    p95_ms: float = 500.0  # <500ms p95
    p99_ms: float = 1500.0  # <1500ms p99
    success_rate: float = 0.999  # >=99.9%
    budget_window_days: int = 30  # Rolling 30-day window


class SloStatusReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    total_requests: int
    success_count: int
    failure_count: int
    p95_latency_ms: float
    p99_latency_ms: float
    success_rate: float
    p95_slo_met: bool
    p99_slo_met: bool
    success_rate_slo_met: bool
    error_budget_consumed_pct: float  # 0.0-100.0
    error_budget_remaining_pct: float


class CustomerCohortBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: str
    cohort: str | None
    total_requests: int
    p95_latency_ms: float
    p99_latency_ms: float
    success_rate: float


class QuerySloMonitor:
    """Monitor query latency SLO compliance with per-customer/cohort breakdown."""

    def __init__(
        self,
        target: SloTarget | None = None,
        registry: CollectorRegistry | None = None,
        max_window_size: int = 100_000,
    ) -> None:
        self._target = target or SloTarget()
        self._registry = registry or CollectorRegistry()

        self._latency_histogram = Histogram(
            "aegis_query_latency_seconds",
            "Query latency in seconds",
            ["customer", "cohort"],
            buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 5.0),
            registry=self._registry,
        )
        self._requests_total = Counter(
            "aegis_query_requests_total",
            "Total query requests",
            ["customer", "cohort", "status"],
            registry=self._registry,
        )
        self._p95_gauge = Gauge(
            "aegis_query_p95_latency_ms",
            "Current p95 query latency in milliseconds",
            registry=self._registry,
        )
        self._p99_gauge = Gauge(
            "aegis_query_p99_latency_ms",
            "Current p99 query latency in milliseconds",
            registry=self._registry,
        )
        self._success_rate_gauge = Gauge(
            "aegis_query_success_rate",
            "Current query success rate",
            registry=self._registry,
        )
        self._error_budget_gauge = Gauge(
            "aegis_query_error_budget_consumed_pct",
            "Percentage of error budget consumed in rolling window",
            registry=self._registry,
        )

        # Internal tracking: (timestamp_epoch, latency_ms, customer_id, cohort, success)
        self._latencies: deque[tuple[float, float, str, str | None, bool]] = deque(
            maxlen=max_window_size
        )

    def record_request(
        self,
        customer_id: str,
        cohort: str | None,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record a single query request."""
        cohort_label = cohort or ""
        self._latency_histogram.labels(
            customer=customer_id, cohort=cohort_label
        ).observe(latency_ms / 1000.0)
        status = "success" if success else "failure"
        self._requests_total.labels(
            customer=customer_id, cohort=cohort_label, status=status
        ).inc()
        self._latencies.append(
            (time.time(), latency_ms, customer_id, cohort, success)
        )
        self._update_gauges()

    def _update_gauges(self) -> None:
        """Recompute and set Prometheus gauge values from rolling window."""
        latencies_sorted = sorted(entry[1] for entry in self._latencies)
        n = len(latencies_sorted)
        if n == 0:
            return
        p95_idx = int(0.95 * (n - 1))
        p99_idx = int(0.99 * (n - 1))
        p95 = latencies_sorted[p95_idx]
        p99 = latencies_sorted[p99_idx]

        success_count = sum(1 for entry in self._latencies if entry[4])
        success_rate = success_count / n

        self._p95_gauge.set(p95)
        self._p99_gauge.set(p99)
        self._success_rate_gauge.set(success_rate)

        # Error budget
        allowed_failures = (1 - self._target.success_rate) * n
        actual_failures = n - success_count
        if allowed_failures == 0:
            consumed = 100.0 if actual_failures > 0 else 0.0
        else:
            consumed = actual_failures / allowed_failures * 100
        self._error_budget_gauge.set(consumed)

    def get_status_report(self) -> SloStatusReport:
        """Generate a snapshot SLO status report from the rolling window."""
        n = len(self._latencies)
        if n == 0:
            return SloStatusReport(
                timestamp=datetime.now(),
                total_requests=0,
                success_count=0,
                failure_count=0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                success_rate=1.0,
                p95_slo_met=True,
                p99_slo_met=True,
                success_rate_slo_met=True,
                error_budget_consumed_pct=0.0,
                error_budget_remaining_pct=100.0,
            )

        latencies_sorted = sorted(entry[1] for entry in self._latencies)
        p95_idx = int(0.95 * (n - 1))
        p99_idx = int(0.99 * (n - 1))
        p95 = latencies_sorted[p95_idx]
        p99 = latencies_sorted[p99_idx]

        success_count = sum(1 for entry in self._latencies if entry[4])
        failure_count = n - success_count
        success_rate = success_count / n

        allowed_failures = (1 - self._target.success_rate) * n
        actual_failures = failure_count
        if allowed_failures == 0:
            consumed = 100.0 if actual_failures > 0 else 0.0
        else:
            consumed = actual_failures / allowed_failures * 100

        return SloStatusReport(
            timestamp=datetime.now(),
            total_requests=n,
            success_count=success_count,
            failure_count=failure_count,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            success_rate=success_rate,
            p95_slo_met=p95 <= self._target.p95_ms,
            p99_slo_met=p99 <= self._target.p99_ms,
            success_rate_slo_met=success_rate >= self._target.success_rate,
            error_budget_consumed_pct=consumed,
            error_budget_remaining_pct=max(0.0, 100.0 - consumed),
        )

    def get_customer_breakdown(self) -> list[CustomerCohortBreakdown]:
        """Compute per-customer/cohort latency and success breakdown."""
        groups: dict[
            tuple[str, str | None], list[tuple[float, bool]]
        ] = {}
        for _ts, latency_ms, customer_id, cohort, success in self._latencies:
            key = (customer_id, cohort)
            groups.setdefault(key, []).append((latency_ms, success))

        result: list[CustomerCohortBreakdown] = []
        for (customer_id, cohort), entries in sorted(groups.items()):
            latencies_sorted = sorted(e[0] for e in entries)
            n = len(latencies_sorted)
            p95_idx = int(0.95 * (n - 1))
            p99_idx = int(0.99 * (n - 1))
            success_count = sum(1 for e in entries if e[1])
            result.append(
                CustomerCohortBreakdown(
                    customer_id=customer_id,
                    cohort=cohort,
                    total_requests=n,
                    p95_latency_ms=latencies_sorted[p95_idx],
                    p99_latency_ms=latencies_sorted[p99_idx],
                    success_rate=success_count / n,
                )
            )
        return result

    def is_budget_breached(self) -> bool:
        """Return True if the error budget is fully consumed."""
        report = self.get_status_report()
        return report.error_budget_consumed_pct >= 100.0 - 1e-9

    def expose_metrics(self) -> str:
        """Return metrics in Prometheus exposition format."""
        return generate_latest(self._registry).decode("utf-8")
