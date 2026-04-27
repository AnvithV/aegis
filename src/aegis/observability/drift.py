"""Per-source artifact-count drift detection with anomaly alerting."""

from __future__ import annotations

import statistics
import uuid
from datetime import date

import duckdb
from pydantic import BaseModel, ConfigDict

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS daily_artifact_counts (
    source TEXT NOT NULL,
    count_date DATE NOT NULL,
    artifact_count INTEGER NOT NULL,
    PRIMARY KEY (source, count_date)
);
"""


class DriftConfig(BaseModel):
    """Configuration for drift detection thresholds."""

    model_config = ConfigDict(frozen=True)

    window_days: int = 14
    z_score_threshold: float = 2.0
    min_drop_pct: float = 0.3


class DailyCount(BaseModel):
    """A single day's artifact count for a source."""

    model_config = ConfigDict(frozen=True)

    source: str
    date: date
    artifact_count: int


class DriftAlert(BaseModel):
    """Alert emitted when drift is detected."""

    model_config = ConfigDict(frozen=True)

    alert_id: str
    source: str
    date: date
    current_count: int
    baseline_mean: float
    baseline_stddev: float
    z_score: float
    drop_pct: float
    severity: str
    message: str


class DriftDetector:
    """Detect per-source artifact count drift using rolling baselines."""

    def __init__(
        self,
        db_path: str = "aegis.duckdb",
        config: DriftConfig | None = None,
    ) -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)
        self._config = config or DriftConfig()

    def record_daily_count(
        self, source: str, count_date: date, count: int
    ) -> None:
        """Record or upsert a daily artifact count."""
        self._conn.execute(
            "INSERT INTO daily_artifact_counts "
            "(source, count_date, artifact_count) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT (source, count_date) DO UPDATE SET "
            "artifact_count = excluded.artifact_count",
            [source, count_date, count],
        )

    def get_baseline(
        self, source: str, end_date: date
    ) -> tuple[float, float]:
        """Compute mean and stddev over the rolling window ending before end_date."""
        rows = self._conn.execute(
            "SELECT artifact_count FROM daily_artifact_counts "
            "WHERE source = ? AND count_date < ? "
            "ORDER BY count_date DESC "
            f"LIMIT {self._config.window_days}",
            [source, end_date],
        ).fetchall()

        if len(rows) < 2:
            return 0.0, 0.0

        counts = [r[0] for r in rows]
        mean = statistics.mean(counts)
        stddev = statistics.stdev(counts)
        return mean, stddev

    def check_drift(
        self, source: str, check_date: date
    ) -> DriftAlert | None:
        """Check if today's count is anomalous vs. baseline."""
        row = self._conn.execute(
            "SELECT artifact_count FROM daily_artifact_counts "
            "WHERE source = ? AND count_date = ?",
            [source, check_date],
        ).fetchone()

        if row is None:
            return None

        current_count = row[0]
        mean, stddev = self.get_baseline(source, check_date)

        if mean == 0.0:
            return None

        drop_pct = (mean - current_count) / mean if mean > 0 else 0.0
        z_score = (
            (mean - current_count) / stddev if stddev > 0 else 0.0
        )

        is_drop = drop_pct >= self._config.min_drop_pct
        is_z_anomaly = (
            z_score >= self._config.z_score_threshold and stddev > 0
        )

        if not is_drop and not is_z_anomaly:
            return None

        if is_drop:
            severity = "critical"
            msg = (
                f"{source}: {drop_pct:.0%} drop from baseline "
                f"(current={current_count}, mean={mean:.1f})"
            )
        else:
            severity = "warning"
            msg = (
                f"{source}: z-score {z_score:.2f} exceeds threshold "
                f"(current={current_count}, mean={mean:.1f}, "
                f"stddev={stddev:.1f})"
            )

        return DriftAlert(
            alert_id=str(uuid.uuid4()),
            source=source,
            date=check_date,
            current_count=current_count,
            baseline_mean=mean,
            baseline_stddev=stddev,
            z_score=z_score,
            drop_pct=drop_pct,
            severity=severity,
            message=msg,
        )

    def check_all_sources(
        self, check_date: date
    ) -> list[DriftAlert]:
        """Check drift for all sources with data on the given date."""
        rows = self._conn.execute(
            "SELECT DISTINCT source FROM daily_artifact_counts "
            "WHERE count_date = ?",
            [check_date],
        ).fetchall()

        alerts: list[DriftAlert] = []
        for (source,) in rows:
            alert = self.check_drift(source, check_date)
            if alert is not None:
                alerts.append(alert)
        return alerts
