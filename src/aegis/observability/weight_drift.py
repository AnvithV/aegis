"""Per-refit weight-drift time-series tracking with jump detection."""

from __future__ import annotations

import glob as globmod
import uuid
from datetime import date, datetime
from pathlib import Path

import duckdb
import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from aegis.scoring.quality_prior import WeightVector, load_weight_vector

_CREATE_SNAPSHOTS_TABLE = """\
CREATE TABLE IF NOT EXISTS weight_drift_snapshots (
    specialty TEXT NOT NULL,
    version INTEGER NOT NULL,
    parameter_name TEXT NOT NULL,
    parameter_value DOUBLE NOT NULL,
    refit_date DATE NOT NULL,
    PRIMARY KEY (specialty, version, parameter_name)
);
"""

_CREATE_ANNOTATIONS_TABLE = """\
CREATE TABLE IF NOT EXISTS weight_drift_annotations (
    annotation_id TEXT NOT NULL PRIMARY KEY,
    annotation_date DATE NOT NULL,
    event_description TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class WeightSnapshot(BaseModel):
    """A single parameter snapshot from a weight refit."""

    model_config = ConfigDict(frozen=True)

    specialty: str
    version: int
    parameter_name: str  # e.g., "weight.f1_rcr", "exponent.alpha"
    parameter_value: float
    refit_date: date


class DriftAnnotation(BaseModel):
    """An event annotation for the weight drift timeline."""

    model_config = ConfigDict(frozen=True)

    annotation_id: str
    annotation_date: date
    event_description: str  # e.g., "EPO patent source ingested"


class JumpAlert(BaseModel):
    """Alert emitted when a parameter changes by more than the threshold."""

    model_config = ConfigDict(frozen=True)

    alert_id: str
    specialty: str
    parameter_name: str
    old_version: int
    new_version: int
    old_value: float
    new_value: float
    relative_change_pct: float
    severity: str  # "warning" or "critical"
    message: str


class ParameterTimeSeries(BaseModel):
    """Time series of a single parameter across versions."""

    model_config = ConfigDict(frozen=True)

    specialty: str
    parameter_name: str
    versions: list[int]
    values: list[float]
    dates: list[date]


class WeightDriftReport(BaseModel):
    """Full drift report across specialties."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    specialties: list[str]
    time_series: list[ParameterTimeSeries]
    jump_alerts: list[JumpAlert]
    annotations: list[DriftAnnotation]


class WeightDriftTracker:
    """Track per-refit weight snapshots and detect drift jumps."""

    def __init__(
        self,
        db_path: str = "aegis.duckdb",
        jump_threshold_pct: float = 25.0,
    ) -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_SNAPSHOTS_TABLE)
        self._conn.execute(_CREATE_ANNOTATIONS_TABLE)
        self._jump_threshold_pct = jump_threshold_pct

    def record_snapshot(self, snapshot: WeightSnapshot) -> None:
        """Upsert a single parameter snapshot."""
        self._conn.execute(
            "INSERT INTO weight_drift_snapshots "
            "(specialty, version, parameter_name, parameter_value, refit_date) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (specialty, version, parameter_name) DO UPDATE SET "
            "parameter_value = excluded.parameter_value, "
            "refit_date = excluded.refit_date",
            [
                snapshot.specialty,
                snapshot.version,
                snapshot.parameter_name,
                snapshot.parameter_value,
                snapshot.refit_date,
            ],
        )

    def record_weight_vector(
        self, wv: WeightVector, refit_date: date
    ) -> None:
        """Decompose a WeightVector into individual parameter snapshots."""
        for key, value in wv.weights.items():
            self.record_snapshot(
                WeightSnapshot(
                    specialty=wv.specialty,
                    version=wv.version,
                    parameter_name=f"weight.{key}",
                    parameter_value=value,
                    refit_date=refit_date,
                )
            )
        for key, value in wv.exponents.items():
            self.record_snapshot(
                WeightSnapshot(
                    specialty=wv.specialty,
                    version=wv.version,
                    parameter_name=f"exponent.{key}",
                    parameter_value=value,
                    refit_date=refit_date,
                )
            )

    def load_history_from_dir(
        self, weights_dir: str = "config/aegis/weights"
    ) -> int:
        """Load all weight YAML files from a directory and record them.

        Returns the number of weight vectors loaded.
        """
        pattern = str(Path(weights_dir) / "*_v*.yaml")
        files = sorted(globmod.glob(pattern))
        count = 0
        for filepath in files:
            wv = load_weight_vector(Path(filepath))
            # Extract refit_date from the YAML created field
            with open(filepath) as f:  # noqa: PTH123
                data = yaml.safe_load(f)
            created = data.get("created")
            if created is not None:
                if isinstance(created, str):
                    refit_date = date.fromisoformat(created)
                elif isinstance(created, date):
                    refit_date = created
                else:
                    refit_date = date.today()
            else:
                refit_date = date.today()
            self.record_weight_vector(wv, refit_date)
            count += 1
        return count

    def record_annotation(
        self, annotation_date: date, event_description: str
    ) -> DriftAnnotation:
        """Record an event annotation on the drift timeline."""
        annotation = DriftAnnotation(
            annotation_id=str(uuid.uuid4()),
            annotation_date=annotation_date,
            event_description=event_description,
        )
        self._conn.execute(
            "INSERT INTO weight_drift_annotations "
            "(annotation_id, annotation_date, event_description, created_at) "
            "VALUES (?, ?, ?, ?)",
            [
                annotation.annotation_id,
                annotation.annotation_date,
                annotation.event_description,
                datetime.now().isoformat(),
            ],
        )
        return annotation

    def get_annotations(self) -> list[DriftAnnotation]:
        """Fetch all annotations ordered by date."""
        rows = self._conn.execute(
            "SELECT annotation_id, annotation_date, event_description "
            "FROM weight_drift_annotations "
            "ORDER BY annotation_date"
        ).fetchall()
        return [
            DriftAnnotation(
                annotation_id=row[0],
                annotation_date=row[1],
                event_description=row[2],
            )
            for row in rows
        ]

    def get_time_series(
        self, specialty: str, parameter_name: str
    ) -> ParameterTimeSeries | None:
        """Get the time series for a single parameter in a specialty."""
        rows = self._conn.execute(
            "SELECT version, parameter_value, refit_date "
            "FROM weight_drift_snapshots "
            "WHERE specialty = ? AND parameter_name = ? "
            "ORDER BY version",
            [specialty, parameter_name],
        ).fetchall()
        if not rows:
            return None
        return ParameterTimeSeries(
            specialty=specialty,
            parameter_name=parameter_name,
            versions=[r[0] for r in rows],
            values=[r[1] for r in rows],
            dates=[r[2] for r in rows],
        )

    def get_all_time_series(
        self, specialty: str | None = None
    ) -> list[ParameterTimeSeries]:
        """Get all time series, optionally filtered by specialty."""
        if specialty is None:
            spec_rows = self._conn.execute(
                "SELECT DISTINCT specialty FROM weight_drift_snapshots "
                "ORDER BY specialty"
            ).fetchall()
            specialties = [r[0] for r in spec_rows]
        else:
            specialties = [specialty]

        result: list[ParameterTimeSeries] = []
        for spec in specialties:
            param_rows = self._conn.execute(
                "SELECT DISTINCT parameter_name "
                "FROM weight_drift_snapshots "
                "WHERE specialty = ? "
                "ORDER BY parameter_name",
                [spec],
            ).fetchall()
            for (param_name,) in param_rows:
                ts = self.get_time_series(spec, param_name)
                if ts is not None:
                    result.append(ts)
        return result

    def detect_jumps(
        self, specialty: str | None = None
    ) -> list[JumpAlert]:
        """Detect parameter jumps exceeding the threshold."""
        all_ts = self.get_all_time_series(specialty)
        alerts: list[JumpAlert] = []
        for ts in all_ts:
            if len(ts.versions) < 2:
                continue
            for i in range(1, len(ts.versions)):
                old_val = ts.values[i - 1]
                new_val = ts.values[i]
                if abs(old_val) < 1e-10:
                    # Handle zero old_value
                    if abs(new_val) > 0.01:
                        rel_change = 100.0
                    else:
                        continue
                else:
                    rel_change = abs(new_val - old_val) / abs(old_val) * 100.0

                if rel_change > self._jump_threshold_pct:
                    if rel_change > 2 * self._jump_threshold_pct:
                        severity = "critical"
                    else:
                        severity = "warning"
                    alerts.append(
                        JumpAlert(
                            alert_id=str(uuid.uuid4()),
                            specialty=ts.specialty,
                            parameter_name=ts.parameter_name,
                            old_version=ts.versions[i - 1],
                            new_version=ts.versions[i],
                            old_value=old_val,
                            new_value=new_val,
                            relative_change_pct=round(rel_change, 2),
                            severity=severity,
                            message=(
                                f"{ts.specialty}/{ts.parameter_name}: "
                                f"{rel_change:.1f}% change from v{ts.versions[i - 1]} "
                                f"to v{ts.versions[i]} "
                                f"({old_val} -> {new_val})"
                            ),
                        )
                    )
        return alerts

    def generate_report(
        self, specialty: str | None = None
    ) -> WeightDriftReport:
        """Generate a full drift report."""
        all_ts = self.get_all_time_series(specialty)
        jump_alerts = self.detect_jumps(specialty)
        annotations = self.get_annotations()

        spec_rows = self._conn.execute(
            "SELECT DISTINCT specialty FROM weight_drift_snapshots "
            "ORDER BY specialty"
        ).fetchall()
        specialties = [r[0] for r in spec_rows]

        return WeightDriftReport(
            generated_at=datetime.now(),
            specialties=specialties,
            time_series=all_ts,
            jump_alerts=jump_alerts,
            annotations=annotations,
        )
