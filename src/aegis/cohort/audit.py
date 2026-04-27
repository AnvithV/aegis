"""Append-only cohort-membership audit log backed by DuckDB."""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, date, datetime
from enum import StrEnum

import duckdb
from pydantic import BaseModel, ConfigDict


class AuditAction(StrEnum):
    """Possible audit log actions."""

    add = "add"
    remove = "remove"


class AuditEntry(BaseModel):
    """A single audit log entry."""

    model_config = ConfigDict(frozen=True)

    entry_id: str
    cohort_id: str
    candidate_uuid: str
    action: AuditAction
    reason: str
    source: str
    timestamp: datetime


_AUDIT_DDL = """\
CREATE TABLE IF NOT EXISTS cohort_audit_log (
    entry_id TEXT PRIMARY KEY,
    cohort_id TEXT NOT NULL,
    candidate_uuid TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT current_timestamp
);
"""

_AUDIT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_cohort "
    "ON cohort_audit_log(cohort_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_candidate "
    "ON cohort_audit_log(candidate_uuid);",
    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp "
    "ON cohort_audit_log(timestamp);",
]


class CohortAuditLog:
    """Append-only audit log for cohort membership changes."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute(_AUDIT_DDL)
        for idx_stmt in _AUDIT_INDEXES:
            self._conn.execute(idx_stmt)

    def _log(
        self,
        cohort_id: str,
        candidate_uuid: str,
        action: AuditAction,
        reason: str,
        source: str,
    ) -> AuditEntry:
        now = datetime.now(UTC)
        entry = AuditEntry(
            entry_id=str(_uuid.uuid4()),
            cohort_id=cohort_id,
            candidate_uuid=candidate_uuid,
            action=action,
            reason=reason,
            source=source,
            timestamp=now,
        )
        self._conn.execute(
            "INSERT INTO cohort_audit_log "
            "(entry_id, cohort_id, candidate_uuid, action, "
            "reason, source, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                entry.entry_id,
                entry.cohort_id,
                entry.candidate_uuid,
                entry.action,
                entry.reason,
                entry.source,
                entry.timestamp,
            ],
        )
        return entry

    def log_add(
        self,
        cohort_id: str,
        candidate_uuid: str,
        reason: str,
        source: str,
    ) -> AuditEntry:
        """Record that a candidate was added to a cohort."""
        return self._log(
            cohort_id, candidate_uuid, AuditAction.add, reason, source
        )

    def log_remove(
        self,
        cohort_id: str,
        candidate_uuid: str,
        reason: str,
        source: str,
    ) -> AuditEntry:
        """Record that a candidate was removed from a cohort."""
        return self._log(
            cohort_id, candidate_uuid, AuditAction.remove, reason, source
        )

    @staticmethod
    def _coerce_ts(value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _rows_to_entries(
        self, rows: list[tuple[object, ...]]
    ) -> list[AuditEntry]:
        return [
            AuditEntry(
                entry_id=str(r[0]),
                cohort_id=str(r[1]),
                candidate_uuid=str(r[2]),
                action=AuditAction(str(r[3])),
                reason=str(r[4]),
                source=str(r[5]),
                timestamp=self._coerce_ts(r[6]),
            )
            for r in rows
        ]

    def get_log(
        self,
        cohort_id: str,
        since: datetime | None = None,
    ) -> list[AuditEntry]:
        """Return audit entries for a cohort, optionally filtered by time."""
        if since is not None:
            rows = self._conn.execute(
                "SELECT entry_id, cohort_id, candidate_uuid, action, "
                "reason, source, timestamp "
                "FROM cohort_audit_log "
                "WHERE cohort_id = ? AND timestamp >= ? "
                "ORDER BY timestamp ASC",
                [cohort_id, since],
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT entry_id, cohort_id, candidate_uuid, action, "
                "reason, source, timestamp "
                "FROM cohort_audit_log "
                "WHERE cohort_id = ? "
                "ORDER BY timestamp ASC",
                [cohort_id],
            ).fetchall()
        return self._rows_to_entries(rows)

    def get_by_candidate(
        self, candidate_uuid: str
    ) -> list[AuditEntry]:
        """Return all audit entries for a given candidate."""
        rows = self._conn.execute(
            "SELECT entry_id, cohort_id, candidate_uuid, action, "
            "reason, source, timestamp "
            "FROM cohort_audit_log "
            "WHERE candidate_uuid = ? "
            "ORDER BY timestamp ASC",
            [candidate_uuid],
        ).fetchall()
        return self._rows_to_entries(rows)

    def get_by_reason(self, reason: str) -> list[AuditEntry]:
        """Return all audit entries with a specific reason."""
        rows = self._conn.execute(
            "SELECT entry_id, cohort_id, candidate_uuid, action, "
            "reason, source, timestamp "
            "FROM cohort_audit_log "
            "WHERE reason = ? "
            "ORDER BY timestamp ASC",
            [reason],
        ).fetchall()
        return self._rows_to_entries(rows)

    def daily_summary(
        self, cohort_id: str, day: date
    ) -> dict[str, int]:
        """Return ``{"added": N, "removed": M}`` for a given date."""
        rows = self._conn.execute(
            "SELECT action, COUNT(*) "
            "FROM cohort_audit_log "
            "WHERE cohort_id = ? "
            "AND CAST(timestamp AS DATE) = ? "
            "GROUP BY action",
            [cohort_id, day],
        ).fetchall()
        summary: dict[str, int] = {"added": 0, "removed": 0}
        for action, count in rows:
            if action == AuditAction.add:
                summary["added"] = int(count)
            elif action == AuditAction.remove:
                summary["removed"] = int(count)
        return summary

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()
