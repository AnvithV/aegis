"""JobStore: DuckDB-backed storage for async pipeline jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

_ALLOWED_UPDATE_COLUMNS = frozenset(
    {"status", "completed_at", "duration_ms", "source_count", "candidate_count"}
)

_ALL_COLUMNS = (
    "id, query_text, status, created_at, completed_at, "
    "duration_ms, source_count, candidate_count, created_by"
)


class JobStore:
    """Persistent store for pipeline jobs backed by DuckDB."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._run_migrations()

    def _run_migrations(self) -> None:
        migration_dir = Path(__file__).parent / "migrations"
        for sql_file in sorted(migration_dir.glob("*.sql")):
            sql = sql_file.read_text()
            self._conn.execute(sql)

    def create(self, *, job_id: str, query_text: str, created_by: str) -> None:
        """Insert a new job with status='in_progress'."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO jobs (id, query_text, status, created_at, created_by)
            VALUES (?, ?, 'in_progress', ?, ?)
            """,
            [job_id, query_text, now, created_by],
        )

    def update(self, job_id: str, **kwargs: Any) -> None:
        """Update allowed columns on a job row.

        Raises ValueError if any key is not in the allowed set.
        """
        if not kwargs:
            return
        bad_keys = set(kwargs.keys()) - _ALLOWED_UPDATE_COLUMNS
        if bad_keys:
            msg = f"Invalid column(s): {', '.join(sorted(bad_keys))}"
            raise ValueError(msg)

        set_clauses = [f"{col} = ?" for col in kwargs]
        values = list(kwargs.values()) + [job_id]
        self._conn.execute(
            f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = ?",  # noqa: S608
            values,
        )

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a job by ID, or None if not found."""
        result = self._conn.execute(
            f"SELECT {_ALL_COLUMNS} FROM jobs WHERE id = ?",  # noqa: S608
            [job_id],
        ).fetchone()
        if result is None:
            return None
        return self._row_to_dict(result)

    def list_all(
        self, *, created_by: str, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        """Paginated list filtered by created_by, ordered by created_at DESC."""
        offset = (page - 1) * per_page

        total_row = self._conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE created_by = ?",
            [created_by],
        ).fetchone()
        total = int(total_row[0]) if total_row else 0

        rows = self._conn.execute(
            f"SELECT {_ALL_COLUMNS} FROM jobs "  # noqa: S608
            "WHERE created_by = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [created_by, per_page, offset],
        ).fetchall()

        return [self._row_to_dict(r) for r in rows], total

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()

    @staticmethod
    def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
        """Convert a database row to a dictionary."""
        return {
            "id": row[0],
            "query_text": row[1],
            "status": row[2],
            "created_at": row[3],
            "completed_at": row[4],
            "duration_ms": row[5],
            "source_count": row[6],
            "candidate_count": row[7],
            "created_by": row[8],
        }
