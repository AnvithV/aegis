"""Integrity-gate hit-rate dashboard with spike detection."""

from __future__ import annotations

import datetime
import uuid
from pathlib import Path

import duckdb
from pydantic import BaseModel, ConfigDict

HARD_ZERO_REASONS: list[str] = [
    "LEIE",
    "OFAC/SAM",
    "ORI",
    "retraction_fabrication",
    "retraction_falsification",
    "medical_board",
]

SOFT_DISCOUNT_REASONS: list[str] = [
    "predatory_load",
    "out_of_subdomain_retraction",
    "authorship_inconsistency",
    "papermill_pending",
]

_SPIKE_WINDOW_DAYS = 14
_SPIKE_MULTIPLIER = 3.0

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS integrity_events (
    event_date DATE NOT NULL,
    candidate_uuid TEXT NOT NULL,
    event_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


class IntegrityEvent(BaseModel):
    """A single integrity gate event."""

    model_config = ConfigDict(frozen=True)

    event_date: datetime.date
    candidate_uuid: str
    event_type: str
    reason: str
    detail: str


class DailySummary(BaseModel):
    """Daily summary of integrity events."""

    model_config = ConfigDict(frozen=True)

    summary_date: datetime.date
    hard_zero_count: int
    soft_discount_count: int
    by_reason: dict[str, int]


class SpikeAlert(BaseModel):
    """Alert raised when event counts spike above baseline."""

    model_config = ConfigDict(frozen=True)

    alert_id: str
    event_type: str
    reason: str
    date: datetime.date
    current_count: int
    baseline_mean: float
    severity: str
    message: str


class IntegrityDashboard:
    """Track integrity gate events and detect spikes."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)

    def record_event(self, event: IntegrityEvent) -> None:
        """Record a single integrity event."""
        self._conn.execute(
            "INSERT INTO integrity_events "
            "(event_date, candidate_uuid, event_type, reason, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                event.event_date,
                event.candidate_uuid,
                event.event_type,
                event.reason,
                event.detail,
            ],
        )

    def record_hard_zero(
        self,
        event_date: datetime.date,
        candidate_uuid: str,
        reason: str,
        detail: str = "",
    ) -> None:
        """Record a hard-zero integrity event."""
        self.record_event(
            IntegrityEvent(
                event_date=event_date,
                candidate_uuid=candidate_uuid,
                event_type="hard_zero",
                reason=reason,
                detail=detail,
            )
        )

    def record_soft_discount(
        self,
        event_date: datetime.date,
        candidate_uuid: str,
        reason: str,
        detail: str = "",
    ) -> None:
        """Record a soft-discount integrity event."""
        self.record_event(
            IntegrityEvent(
                event_date=event_date,
                candidate_uuid=candidate_uuid,
                event_type="soft_discount",
                reason=reason,
                detail=detail,
            )
        )

    def get_daily_summary(
        self, summary_date: datetime.date
    ) -> DailySummary:
        """Compute a daily summary of integrity events."""
        hard_row = self._conn.execute(
            "SELECT COUNT(*) FROM integrity_events "
            "WHERE event_date = ? AND event_type = 'hard_zero'",
            [summary_date],
        ).fetchone()
        hard_zero_count = hard_row[0] if hard_row else 0

        soft_row = self._conn.execute(
            "SELECT COUNT(*) FROM integrity_events "
            "WHERE event_date = ? AND event_type = 'soft_discount'",
            [summary_date],
        ).fetchone()
        soft_discount_count = soft_row[0] if soft_row else 0

        reason_rows = self._conn.execute(
            "SELECT reason, COUNT(*) FROM integrity_events "
            "WHERE event_date = ? GROUP BY reason",
            [summary_date],
        ).fetchall()
        by_reason = {row[0]: row[1] for row in reason_rows}

        return DailySummary(
            summary_date=summary_date,
            hard_zero_count=hard_zero_count,
            soft_discount_count=soft_discount_count,
            by_reason=by_reason,
        )

    def check_spike(
        self,
        event_type: str,
        reason: str,
        check_date: datetime.date,
    ) -> SpikeAlert | None:
        """Check if today's count for a reason spikes above 3x baseline."""
        current_row = self._conn.execute(
            "SELECT COUNT(*) FROM integrity_events "
            "WHERE event_date = ? AND event_type = ? AND reason = ?",
            [check_date, event_type, reason],
        ).fetchone()
        current_count = current_row[0] if current_row else 0

        if current_count == 0:
            return None

        baseline_rows = self._conn.execute(
            "SELECT event_date, COUNT(*) as cnt "
            "FROM integrity_events "
            "WHERE event_type = ? AND reason = ? "
            "AND event_date < ? "
            "AND event_date >= ? "
            "GROUP BY event_date",
            [
                event_type,
                reason,
                check_date,
                check_date - datetime.timedelta(days=_SPIKE_WINDOW_DAYS),
            ],
        ).fetchall()

        if len(baseline_rows) == 0:
            return None

        baseline_mean = sum(r[1] for r in baseline_rows) / len(
            baseline_rows
        )

        if current_count <= _SPIKE_MULTIPLIER * baseline_mean:
            return None

        severity = "critical" if current_count > 5 * baseline_mean else "warning"
        message = (
            f"{event_type}/{reason}: {current_count} events on "
            f"{check_date}, {_SPIKE_MULTIPLIER}x baseline "
            f"mean={baseline_mean:.1f}"
        )

        return SpikeAlert(
            alert_id=str(uuid.uuid4()),
            event_type=event_type,
            reason=reason,
            date=check_date,
            current_count=current_count,
            baseline_mean=baseline_mean,
            severity=severity,
            message=message,
        )

    def get_weekly_summary(
        self, end_date: datetime.date
    ) -> list[DailySummary]:
        """Get daily summaries for the 7 days ending on end_date."""
        summaries: list[DailySummary] = []
        for i in range(6, -1, -1):
            d = end_date - datetime.timedelta(days=i)
            summaries.append(self.get_daily_summary(d))
        return summaries

    def generate_html_report(
        self,
        end_date: datetime.date,
        alerts: list[SpikeAlert] | None = None,
    ) -> str:
        """Generate an HTML dashboard for the week ending on end_date."""
        summaries = self.get_weekly_summary(end_date)

        summary_rows = ""
        for s in summaries:
            reasons_str = ", ".join(
                f"{k}: {v}" for k, v in sorted(s.by_reason.items())
            )
            summary_rows += (
                f"<tr><td>{s.summary_date}</td>"
                f"<td>{s.hard_zero_count}</td>"
                f"<td>{s.soft_discount_count}</td>"
                f"<td>{reasons_str}</td></tr>"
            )

        alert_rows = ""
        if alerts:
            for a in alerts:
                alert_rows += (
                    f"<tr><td>{a.event_type}</td>"
                    f"<td>{a.reason}</td>"
                    f"<td>{a.current_count}</td>"
                    f"<td>{a.baseline_mean:.1f}</td>"
                    f"<td>{a.severity}</td>"
                    f"<td>{a.message}</td></tr>"
                )

        alert_section = ""
        if alert_rows:
            alert_section = (
                "\n<h2>Spike Alerts</h2>\n<table>\n"
                "<tr><th>Type</th><th>Reason</th>"
                "<th>Count</th><th>Baseline</th>"
                "<th>Severity</th><th>Message</th></tr>\n"
                f"{alert_rows}\n</table>\n"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<title>Integrity Gate Dashboard</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: left; }}
th {{ background: #f0f0f0; }}
h1 {{ color: #333; }}
h2 {{ color: #555; margin-top: 2em; }}
</style>
</head>
<body>
<h1>Integrity Gate Dashboard &mdash; week ending {end_date}</h1>
{alert_section}
<h2>Daily Summary</h2>
<table>
<tr><th>Date</th><th>Hard Zero</th>
<th>Soft Discount</th><th>By Reason</th></tr>
{summary_rows}
</table>
</body>
</html>"""

    def save_report(
        self,
        end_date: datetime.date,
        alerts: list[SpikeAlert] | None = None,
        path: str = "src/aegis/observability/integrity_dashboard.html",
    ) -> None:
        """Write the HTML report to disk."""
        html = self.generate_html_report(end_date, alerts)
        Path(path).write_text(html)
