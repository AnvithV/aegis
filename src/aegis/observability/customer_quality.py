"""Per-customer task-quality tracking with DuckDB persistence and trend analysis."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import duckdb
from pydantic import BaseModel, ConfigDict

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS customer_quality_snapshots (
    customer_id TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    fleiss_kappa DOUBLE NOT NULL,
    accept_rate DOUBLE NOT NULL,
    task_count INTEGER NOT NULL,
    total_candidates_evaluated INTEGER NOT NULL,
    PRIMARY KEY (customer_id, snapshot_date)
);
"""


class CustomerQualitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: str
    snapshot_date: date
    fleiss_kappa: float  # Inter-rater agreement
    accept_rate: float  # Customer accept rate [0, 1]
    task_count: int  # Number of tasks in this snapshot period
    total_candidates_evaluated: int


class QualityTrend(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: str
    kappa_slope: float  # Linear trend slope for kappa over time
    accept_rate_slope: float  # Linear trend slope for accept rate
    data_points: int  # Number of snapshots used
    latest_kappa: float
    latest_accept_rate: float
    kappa_improving: bool  # True if slope > 0
    accept_rate_improving: bool


class QualityAlert(BaseModel):
    model_config = ConfigDict(frozen=True)

    alert_id: str
    customer_id: str
    alert_type: str  # "kappa_decline" or "accept_rate_decline"
    current_value: float
    previous_value: float
    threshold: float
    severity: str  # "warning" or "critical"
    message: str


class CustomerQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: str
    generated_at: datetime
    snapshots: list[CustomerQualitySnapshot]
    trend: QualityTrend | None
    alerts: list[QualityAlert]


class CustomerQualityTracker:
    """Track per-customer task quality over time with DuckDB persistence."""

    def __init__(
        self,
        db_path: str = "aegis.duckdb",
        kappa_decline_threshold: float = 0.1,
        accept_rate_decline_threshold: float = 0.05,
    ) -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)
        self._kappa_decline_threshold = kappa_decline_threshold
        self._accept_rate_decline_threshold = accept_rate_decline_threshold

    def record_snapshot(self, snapshot: CustomerQualitySnapshot) -> None:
        """Upsert a customer quality snapshot into DuckDB."""
        self._conn.execute(
            "INSERT INTO customer_quality_snapshots "
            "(customer_id, snapshot_date, fleiss_kappa, accept_rate, "
            "task_count, total_candidates_evaluated) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (customer_id, snapshot_date) DO UPDATE SET "
            "fleiss_kappa = excluded.fleiss_kappa, "
            "accept_rate = excluded.accept_rate, "
            "task_count = excluded.task_count, "
            "total_candidates_evaluated = excluded.total_candidates_evaluated",
            [
                snapshot.customer_id,
                snapshot.snapshot_date,
                snapshot.fleiss_kappa,
                snapshot.accept_rate,
                snapshot.task_count,
                snapshot.total_candidates_evaluated,
            ],
        )

    def get_snapshots(
        self, customer_id: str, limit: int = 52
    ) -> list[CustomerQualitySnapshot]:
        """Fetch the most recent snapshots for a customer."""
        rows = self._conn.execute(
            "SELECT customer_id, snapshot_date, fleiss_kappa, accept_rate, "
            "task_count, total_candidates_evaluated "
            "FROM customer_quality_snapshots "
            "WHERE customer_id = ? "
            "ORDER BY snapshot_date DESC "
            "LIMIT ?",
            [customer_id, limit],
        ).fetchall()

        return [
            CustomerQualitySnapshot(
                customer_id=r[0],
                snapshot_date=r[1],
                fleiss_kappa=r[2],
                accept_rate=r[3],
                task_count=r[4],
                total_candidates_evaluated=r[5],
            )
            for r in rows
        ]

    def compute_trend(
        self, customer_id: str, min_points: int = 4
    ) -> QualityTrend | None:
        """Compute linear regression trend for kappa and accept rate."""
        snapshots = self.get_snapshots(customer_id, limit=1000)
        if len(snapshots) < min_points:
            return None

        # Sort by date ascending for regression
        snapshots_asc = sorted(snapshots, key=lambda s: s.snapshot_date)

        # Convert dates to ordinals for regression
        x_values = [s.snapshot_date.toordinal() for s in snapshots_asc]
        kappa_values = [s.fleiss_kappa for s in snapshots_asc]
        accept_values = [s.accept_rate for s in snapshots_asc]

        kappa_slope = self._compute_slope(x_values, kappa_values)
        accept_slope = self._compute_slope(x_values, accept_values)

        latest = snapshots_asc[-1]

        return QualityTrend(
            customer_id=customer_id,
            kappa_slope=kappa_slope,
            accept_rate_slope=accept_slope,
            data_points=len(snapshots_asc),
            latest_kappa=latest.fleiss_kappa,
            latest_accept_rate=latest.accept_rate,
            kappa_improving=kappa_slope > 0,
            accept_rate_improving=accept_slope > 0,
        )

    @staticmethod
    def _compute_slope(x: list[int], y: list[float]) -> float:
        """Simple least-squares slope computation."""
        n = len(x)
        if n < 2:
            return 0.0
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return 0.0
        return (n * sum_xy - sum_x * sum_y) / denom

    def check_alerts(self, customer_id: str) -> list[QualityAlert]:
        """Check for quality decline alerts between the two most recent snapshots."""
        snapshots = self.get_snapshots(customer_id, limit=2)
        if len(snapshots) < 2:
            return []

        # snapshots are DESC order, so [0] is latest, [1] is previous
        current = snapshots[0]
        previous = snapshots[1]

        alerts: list[QualityAlert] = []

        kappa_drop = previous.fleiss_kappa - current.fleiss_kappa
        if kappa_drop > self._kappa_decline_threshold:
            severity = (
                "critical"
                if kappa_drop > 2 * self._kappa_decline_threshold
                else "warning"
            )
            alerts.append(
                QualityAlert(
                    alert_id=str(uuid.uuid4()),
                    customer_id=customer_id,
                    alert_type="kappa_decline",
                    current_value=current.fleiss_kappa,
                    previous_value=previous.fleiss_kappa,
                    threshold=self._kappa_decline_threshold,
                    severity=severity,
                    message=(
                        f"Fleiss kappa for {customer_id} dropped from "
                        f"{previous.fleiss_kappa:.3f} to {current.fleiss_kappa:.3f} "
                        f"(decline: {kappa_drop:.3f}, threshold: "
                        f"{self._kappa_decline_threshold})"
                    ),
                )
            )

        accept_drop = previous.accept_rate - current.accept_rate
        if accept_drop > self._accept_rate_decline_threshold:
            severity = (
                "critical"
                if accept_drop > 2 * self._accept_rate_decline_threshold
                else "warning"
            )
            alerts.append(
                QualityAlert(
                    alert_id=str(uuid.uuid4()),
                    customer_id=customer_id,
                    alert_type="accept_rate_decline",
                    current_value=current.accept_rate,
                    previous_value=previous.accept_rate,
                    threshold=self._accept_rate_decline_threshold,
                    severity=severity,
                    message=(
                        f"Accept rate for {customer_id} dropped from "
                        f"{previous.accept_rate:.3f} to {current.accept_rate:.3f} "
                        f"(decline: {accept_drop:.3f}, threshold: "
                        f"{self._accept_rate_decline_threshold})"
                    ),
                )
            )

        return alerts

    def generate_report(self, customer_id: str) -> CustomerQualityReport:
        """Generate a full quality report for a customer."""
        snapshots = self.get_snapshots(customer_id)
        trend = self.compute_trend(customer_id)
        alerts = self.check_alerts(customer_id)

        return CustomerQualityReport(
            customer_id=customer_id,
            generated_at=datetime.now(),
            snapshots=snapshots,
            trend=trend,
            alerts=alerts,
        )

    def get_all_customer_ids(self) -> list[str]:
        """Return all distinct customer IDs."""
        rows = self._conn.execute(
            "SELECT DISTINCT customer_id "
            "FROM customer_quality_snapshots "
            "ORDER BY customer_id"
        ).fetchall()
        return [r[0] for r in rows]

    def get_cross_customer_summary(self) -> list[CustomerQualityReport]:
        """Generate reports for all customers."""
        customer_ids = self.get_all_customer_ids()
        return [self.generate_report(cid) for cid in customer_ids]
