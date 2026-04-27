"""Refresh-cadence SLA tracking with hard-gate/non-hard-gate classification."""

from __future__ import annotations

import time
import uuid
from datetime import date

from prometheus_client import CollectorRegistry, Gauge, generate_latest
from pydantic import BaseModel, ConfigDict

from aegis.observability.freshness import SOURCE_SLOS

# Hard-gate sources: integrity-critical, page on-call immediately on breach.
# Derived from IntegritySource enum in src/aegis/ingestion/event_dispatcher.py.
HARD_GATE_SOURCES: frozenset[str] = frozenset(
    {
        "retraction_watch",
        "ori",
        "ofac",
        "sam",
        "leie",
        "state_board_CA",
        "state_board_FL",
        "state_board_NY",
        "state_board_PA",
        "state_board_TX",
    }
)

_DEFAULT_SLA_SECONDS = 24 * 3600  # 24 hours


class SourceSlaStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    sla_seconds: float
    last_success_epoch: float | None  # None if never succeeded
    age_seconds: float | None  # None if never succeeded
    is_compliant: bool
    is_hard_gate: bool
    breach_severity: str | None  # "critical" / "warning" / None


class SlaBreachAlert(BaseModel):
    model_config = ConfigDict(frozen=True)

    alert_id: str
    source: str
    is_hard_gate: bool
    sla_seconds: float
    age_seconds: float
    overage_seconds: float  # How far past the SLA
    severity: str  # "critical" or "warning"
    page_oncall: bool  # True for hard-gate sources
    message: str


class WeeklySlaSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary_date: date
    total_sources: int
    compliant_count: int
    breached_count: int
    hard_gate_breaches: list[SlaBreachAlert]
    non_hard_gate_breaches: list[SlaBreachAlert]
    compliance_rate: float  # compliant / total


class RefreshSlaTracker:
    """Track per-source refresh SLA compliance with alerting."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry or CollectorRegistry()
        self._sla_compliant = Gauge(
            "aegis_refresh_sla_compliant",
            "Whether the source is within its refresh SLA (1=yes, 0=no)",
            ["source", "is_hard_gate"],
            registry=self._registry,
        )
        self._sla_overage_seconds = Gauge(
            "aegis_refresh_sla_overage_seconds",
            "Seconds past the SLA threshold (0 if compliant)",
            ["source"],
            registry=self._registry,
        )
        self._hard_gate_breach = Gauge(
            "aegis_refresh_hard_gate_breach",
            "1 if a hard-gate source has breached its SLA",
            ["source"],
            registry=self._registry,
        )

        self._last_success_times: dict[str, float] = {}

    def record_success(self, source: str) -> None:
        """Record a successful ingestion for a source at current time."""
        self._last_success_times[source] = time.time()

    def record_success_at(self, source: str, epoch: float) -> None:
        """Record a successful ingestion at a specific epoch (for testing)."""
        self._last_success_times[source] = epoch

    def check_source(self, source: str) -> SourceSlaStatus:
        """Check SLA compliance for a single source."""
        sla_seconds = SOURCE_SLOS.get(source, _DEFAULT_SLA_SECONDS)
        is_hard_gate = source in HARD_GATE_SOURCES

        last_success_epoch = self._last_success_times.get(source)
        if last_success_epoch is None:
            age_seconds = None
            is_compliant = False
        else:
            age_seconds = time.time() - last_success_epoch
            is_compliant = age_seconds <= sla_seconds

        if not is_compliant and is_hard_gate:
            breach_severity: str | None = "critical"
        elif not is_compliant:
            breach_severity = "warning"
        else:
            breach_severity = None

        # Update Prometheus gauges
        hg_label = "true" if is_hard_gate else "false"
        self._sla_compliant.labels(source=source, is_hard_gate=hg_label).set(
            1.0 if is_compliant else 0.0
        )

        overage = 0.0
        if age_seconds is not None and not is_compliant:
            overage = age_seconds - sla_seconds
        self._sla_overage_seconds.labels(source=source).set(overage)

        if is_hard_gate:
            self._hard_gate_breach.labels(source=source).set(
                0.0 if is_compliant else 1.0
            )

        return SourceSlaStatus(
            source=source,
            sla_seconds=sla_seconds,
            last_success_epoch=last_success_epoch,
            age_seconds=age_seconds,
            is_compliant=is_compliant,
            is_hard_gate=is_hard_gate,
            breach_severity=breach_severity,
        )

    def check_all_sources(self) -> list[SourceSlaStatus]:
        """Check SLA compliance for all sources in SOURCE_SLOS."""
        return [self.check_source(source) for source in sorted(SOURCE_SLOS)]

    def get_breach_alerts(self) -> list[SlaBreachAlert]:
        """Get alerts for all non-compliant sources."""
        statuses = self.check_all_sources()
        alerts: list[SlaBreachAlert] = []
        for status in statuses:
            if status.is_compliant:
                continue

            age = status.age_seconds
            if age is None:
                # Never reported -- use SLA as the overage estimate
                age = status.sla_seconds * 2
                overage = status.sla_seconds
            else:
                overage = age - status.sla_seconds

            alerts.append(
                SlaBreachAlert(
                    alert_id=str(uuid.uuid4()),
                    source=status.source,
                    is_hard_gate=status.is_hard_gate,
                    sla_seconds=status.sla_seconds,
                    age_seconds=age,
                    overage_seconds=overage,
                    severity="critical" if status.is_hard_gate else "warning",
                    page_oncall=status.is_hard_gate,
                    message=(
                        f"Source {status.source} has breached its refresh SLA "
                        f"({status.sla_seconds / 3600:.0f}h). "
                        f"Age: {age / 3600:.1f}h, overage: {overage / 3600:.1f}h."
                    ),
                )
            )

        return alerts

    def get_weekly_summary(
        self, summary_date: date | None = None
    ) -> WeeklySlaSummary:
        """Generate a weekly SLA compliance summary."""
        actual_date = summary_date or date.today()
        alerts = self.get_breach_alerts()

        hard_gate_breaches = [a for a in alerts if a.is_hard_gate]
        non_hard_gate_breaches = [a for a in alerts if not a.is_hard_gate]

        total = len(SOURCE_SLOS)
        breached = len(alerts)
        compliant = total - breached

        return WeeklySlaSummary(
            summary_date=actual_date,
            total_sources=total,
            compliant_count=compliant,
            breached_count=breached,
            hard_gate_breaches=hard_gate_breaches,
            non_hard_gate_breaches=non_hard_gate_breaches,
            compliance_rate=compliant / total if total > 0 else 1.0,
        )

    def expose_metrics(self) -> str:
        """Return metrics in Prometheus exposition format."""
        return generate_latest(self._registry).decode("utf-8")
