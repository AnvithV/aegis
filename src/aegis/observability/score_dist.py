"""Per-component score-distribution monitoring with KS anomaly detection."""

from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path

import duckdb
import numpy as np
from pydantic import BaseModel, ConfigDict

COMPONENTS: list[str] = [
    "f1_rcr",
    "f2_funding",
    "f3_leadership",
    "f4_apex",
    "f5_translational",
    "f6_lineage",
    "quality_prior",
    "topical_fit",
    "recency",
    "rank",
]

_NUM_BUCKETS = 50

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS score_distribution_snapshots (
    component TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    bucket_edges TEXT NOT NULL,
    counts TEXT NOT NULL,
    total_candidates INTEGER NOT NULL,
    mean DOUBLE NOT NULL,
    median DOUBLE NOT NULL,
    stddev DOUBLE NOT NULL,
    PRIMARY KEY (component, snapshot_date)
);
"""


class DistributionSnapshot(BaseModel):
    """Frozen snapshot of a score distribution for a single component."""

    model_config = ConfigDict(frozen=True)

    component: str
    snapshot_date: datetime.date
    bucket_edges: list[float]
    counts: list[int]
    total_candidates: int
    mean: float
    median: float
    stddev: float


class KSAlert(BaseModel):
    """Alert raised when KS statistic exceeds threshold between snapshots."""

    model_config = ConfigDict(frozen=True)

    alert_id: str
    component: str
    date: datetime.date
    ks_statistic: float
    threshold: float
    previous_date: datetime.date
    severity: str
    message: str


class ScoreDistributionMonitor:
    """Monitor per-component score distributions with KS anomaly detection."""

    def __init__(
        self,
        db_path: str = "aegis.duckdb",
        ks_threshold: float = 0.1,
    ) -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)
        self._ks_threshold = ks_threshold

    def record_snapshot(
        self,
        component: str,
        snapshot_date: datetime.date,
        scores: list[float],
    ) -> DistributionSnapshot:
        """Compute a 50-bucket histogram from raw scores and persist it."""
        arr = np.array(scores, dtype=np.float64)
        total_candidates = len(scores)
        mean = float(np.mean(arr))
        median = float(np.median(arr))
        stddev = float(np.std(arr, ddof=1)) if len(scores) > 1 else 0.0

        counts_arr, edges_arr = np.histogram(arr, bins=_NUM_BUCKETS)
        bucket_edges = [float(e) for e in edges_arr]
        counts = [int(c) for c in counts_arr]

        edges_json = json.dumps(bucket_edges)
        counts_json = json.dumps(counts)

        self._conn.execute(
            "INSERT INTO score_distribution_snapshots "
            "(component, snapshot_date, bucket_edges, counts, "
            "total_candidates, mean, median, stddev) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (component, snapshot_date) DO UPDATE SET "
            "bucket_edges = excluded.bucket_edges, "
            "counts = excluded.counts, "
            "total_candidates = excluded.total_candidates, "
            "mean = excluded.mean, "
            "median = excluded.median, "
            "stddev = excluded.stddev",
            [
                component,
                snapshot_date,
                edges_json,
                counts_json,
                total_candidates,
                mean,
                median,
                stddev,
            ],
        )

        return DistributionSnapshot(
            component=component,
            snapshot_date=snapshot_date,
            bucket_edges=bucket_edges,
            counts=counts,
            total_candidates=total_candidates,
            mean=mean,
            median=median,
            stddev=stddev,
        )

    def get_snapshot(
        self, component: str, snapshot_date: datetime.date
    ) -> DistributionSnapshot | None:
        """Retrieve a persisted snapshot for a component and date."""
        row = self._conn.execute(
            "SELECT component, snapshot_date, bucket_edges, counts, "
            "total_candidates, mean, median, stddev "
            "FROM score_distribution_snapshots "
            "WHERE component = ? AND snapshot_date = ?",
            [component, snapshot_date],
        ).fetchone()

        if row is None:
            return None

        return DistributionSnapshot(
            component=row[0],
            snapshot_date=row[1],
            bucket_edges=json.loads(row[2]),
            counts=json.loads(row[3]),
            total_candidates=row[4],
            mean=float(row[5]),
            median=float(row[6]),
            stddev=float(row[7]),
        )

    def check_ks_anomaly(
        self,
        component: str,
        current_date: datetime.date,
        previous_date: datetime.date,
    ) -> KSAlert | None:
        """Compare two snapshots using the KS test; alert if KS > threshold."""
        current = self.get_snapshot(component, current_date)
        previous = self.get_snapshot(component, previous_date)

        if current is None or previous is None:
            return None

        from scipy.stats import ks_2samp  # type: ignore[import-untyped]

        current_samples = _expand_histogram(
            current.bucket_edges, current.counts
        )
        previous_samples = _expand_histogram(
            previous.bucket_edges, previous.counts
        )

        if len(current_samples) == 0 or len(previous_samples) == 0:
            return None

        stat, _ = ks_2samp(current_samples, previous_samples)
        ks_statistic = float(stat)

        if ks_statistic <= self._ks_threshold:
            return None

        severity = "critical" if ks_statistic > 0.3 else "warning"
        message = (
            f"{component}: KS statistic {ks_statistic:.4f} exceeds "
            f"threshold {self._ks_threshold} between "
            f"{previous_date} and {current_date}"
        )

        return KSAlert(
            alert_id=str(uuid.uuid4()),
            component=component,
            date=current_date,
            ks_statistic=ks_statistic,
            threshold=self._ks_threshold,
            previous_date=previous_date,
            severity=severity,
            message=message,
        )

    def check_all_components(
        self,
        current_date: datetime.date,
        previous_date: datetime.date,
    ) -> list[KSAlert]:
        """Run KS anomaly check across all known components."""
        alerts: list[KSAlert] = []
        for component in COMPONENTS:
            alert = self.check_ks_anomaly(
                component, current_date, previous_date
            )
            if alert is not None:
                alerts.append(alert)
        return alerts

    def generate_html_report(
        self,
        snapshot_date: datetime.date,
        alerts: list[KSAlert] | None = None,
    ) -> str:
        """Generate an HTML dashboard with distribution bars for each component."""
        component_sections = ""
        for component in COMPONENTS:
            snap = self.get_snapshot(component, snapshot_date)
            if snap is None:
                continue

            max_count = max(snap.counts) if snap.counts else 1
            bars = ""
            for i, count in enumerate(snap.counts):
                width = int(200 * count / max_count) if max_count > 0 else 0
                bars += (
                    f'<div style="margin:1px 0;">'
                    f'<span style="display:inline-block;width:{width}px;'
                    f'height:12px;background:#4682b4;"></span>'
                    f" {count}</div>"
                )

            component_sections += f"""
<h2>{component}</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total Candidates</td><td>{snap.total_candidates}</td></tr>
<tr><td>Mean</td><td>{snap.mean:.4f}</td></tr>
<tr><td>Median</td><td>{snap.median:.4f}</td></tr>
<tr><td>Std Dev</td><td>{snap.stddev:.4f}</td></tr>
</table>
<h3>Distribution</h3>
{bars}
"""

        alert_rows = ""
        if alerts:
            for a in alerts:
                alert_rows += (
                    f"<tr><td>{a.component}</td>"
                    f"<td>{a.ks_statistic:.4f}</td>"
                    f"<td>{a.threshold}</td>"
                    f"<td>{a.severity}</td>"
                    f"<td>{a.message}</td></tr>"
                )

        alert_section = ""
        if alert_rows:
            alert_section = (
                "\n<h2>KS Anomaly Alerts</h2>\n<table>\n"
                "<tr><th>Component</th><th>KS Statistic</th>"
                "<th>Threshold</th><th>Severity</th>"
                "<th>Message</th></tr>\n"
                f"{alert_rows}\n</table>\n"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Score Distribution Dashboard</title>
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
<h1>Score Distribution Dashboard &mdash; {snapshot_date}</h1>
{alert_section}
{component_sections}
</body>
</html>"""

    def save_report(
        self,
        snapshot_date: datetime.date,
        alerts: list[KSAlert] | None = None,
        path: str = "src/aegis/observability/score_dist_dashboard.html",
    ) -> None:
        """Write the HTML report to disk."""
        html = self.generate_html_report(snapshot_date, alerts)
        Path(path).write_text(html)


def _expand_histogram(
    edges: list[float], counts: list[int]
) -> list[float]:
    """Expand histogram bins into representative sample points for KS test."""
    samples: list[float] = []
    for i, count in enumerate(counts):
        midpoint = (edges[i] + edges[i + 1]) / 2.0
        samples.extend([midpoint] * count)
    return samples
