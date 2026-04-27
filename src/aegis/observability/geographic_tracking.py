"""Geographic-coverage tracking over time with trend analysis."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from prometheus_client import CollectorRegistry, Gauge, generate_latest
from pydantic import BaseModel, ConfigDict

from aegis.observability.regional_coverage import RegionalCoverageMetrics

logger = logging.getLogger(__name__)

NON_US_TARGET_RATIO = 0.40


class GeographicSnapshot(BaseModel):
    """Point-in-time record of geographic coverage."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    total_candidates: int
    per_region_count: dict[str, int]
    per_region_pct: dict[str, float]
    non_us_ratio: float
    new_sources_active: list[str]


class GeographicTrend(BaseModel):
    """Trend analysis over multiple geographic snapshots."""

    model_config = ConfigDict(frozen=True)

    snapshots: list[GeographicSnapshot]
    current_non_us_ratio: float
    target_non_us_ratio: float
    target_met: bool
    ratio_trend: str  # "improving", "stable", or "regressing"
    regression_alert: bool


class GeographicTracker:
    """Track geographic coverage ratios over time via JSONL persistence."""

    def __init__(self, store_path: str = "geographic_tracking.jsonl") -> None:
        self._store_path = Path(store_path)

    def record_snapshot(
        self,
        metrics: RegionalCoverageMetrics,
        active_sources: list[str],
    ) -> GeographicSnapshot:
        """Create snapshot from RegionalCoverageMetrics, append to JSONL."""
        snapshot = GeographicSnapshot(
            timestamp=datetime.now(UTC),
            total_candidates=metrics.total_candidates,
            per_region_count=dict(metrics.per_region_count),
            per_region_pct=dict(metrics.per_region_pct),
            non_us_ratio=metrics.non_us_ratio,
            new_sources_active=active_sources,
        )
        with self._store_path.open("a") as f:
            f.write(snapshot.model_dump_json() + "\n")
        return snapshot

    def load_history(self) -> list[GeographicSnapshot]:
        """Read all snapshots from the JSONL file."""
        if not self._store_path.exists():
            return []
        snapshots: list[GeographicSnapshot] = []
        with self._store_path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    snapshots.append(GeographicSnapshot.model_validate_json(line))
        return snapshots

    def compute_trend(self) -> GeographicTrend:
        """Load history and compute trend direction and regression alert."""
        snapshots = self.load_history()
        if not snapshots:
            return GeographicTrend(
                snapshots=[],
                current_non_us_ratio=0.0,
                target_non_us_ratio=NON_US_TARGET_RATIO,
                target_met=False,
                ratio_trend="stable",
                regression_alert=False,
            )

        current_ratio = snapshots[-1].non_us_ratio
        target_met = current_ratio >= NON_US_TARGET_RATIO

        # Compute trend from last 4 snapshots
        ratio_trend = "stable"
        if len(snapshots) >= 4:
            recent = [s.non_us_ratio for s in snapshots[-4:]]
            diffs = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
            if all(d > 0 for d in diffs):
                ratio_trend = "improving"
            elif all(d < 0 for d in diffs):
                ratio_trend = "regressing"

        # Regression alert: >5% drop from previous snapshot
        regression_alert = False
        if len(snapshots) >= 2:
            prev_ratio = snapshots[-2].non_us_ratio
            if prev_ratio - current_ratio > 0.05:
                regression_alert = True

        return GeographicTrend(
            snapshots=snapshots,
            current_non_us_ratio=current_ratio,
            target_non_us_ratio=NON_US_TARGET_RATIO,
            target_met=target_met,
            ratio_trend=ratio_trend,
            regression_alert=regression_alert,
        )

    def generate_prometheus_metrics(self) -> str:
        """Emit Prometheus metrics for geographic coverage."""
        registry = CollectorRegistry()

        non_us_gauge = Gauge(
            "aegis_geographic_non_us_ratio",
            "Current non-US candidate ratio",
            registry=registry,
        )
        target_gauge = Gauge(
            "aegis_geographic_target_met",
            "Whether non-US ratio target is met (0/1)",
            registry=registry,
        )
        region_gauge = Gauge(
            "aegis_geographic_region_count",
            "Candidate count per region",
            ["region"],
            registry=registry,
        )

        trend = self.compute_trend()
        non_us_gauge.set(trend.current_non_us_ratio)
        target_gauge.set(1.0 if trend.target_met else 0.0)

        if trend.snapshots:
            latest = trend.snapshots[-1]
            for region, count in latest.per_region_count.items():
                region_gauge.labels(region=region).set(count)

        return generate_latest(registry).decode("utf-8")
