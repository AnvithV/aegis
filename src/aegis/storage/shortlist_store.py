"""ShortlistStore: DuckDB-backed storage for candidate shortlists."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import duckdb


class ShortlistStore:
    """Persistent store for shortlists backed by DuckDB."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._run_migrations()

    def _run_migrations(self) -> None:
        migration_dir = Path(__file__).parent / "migrations"
        for sql_file in sorted(migration_dir.glob("*.sql")):
            sql = sql_file.read_text()
            self._conn.execute(sql)

    def create(
        self, *, name: str, description: str | None, created_by: str
    ) -> str:
        """Create a new shortlist and return its ID."""
        shortlist_id = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO shortlists (id, name, description, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [shortlist_id, name, description, created_by, now, now],
        )
        return shortlist_id

    def get(self, shortlist_id: str) -> dict | None:
        """Retrieve a shortlist by ID."""
        result = self._conn.execute(
            "SELECT id, name, description, created_by, created_at, updated_at "
            "FROM shortlists WHERE id = ?",
            [shortlist_id],
        ).fetchone()
        if result is None:
            return None
        return {
            "id": result[0],
            "name": result[1],
            "description": result[2],
            "created_by": result[3],
            "created_at": result[4],
            "updated_at": result[5],
        }

    def list_all(self, created_by: str | None = None) -> list[dict]:
        """List all shortlists, optionally filtered by creator."""
        if created_by is not None:
            rows = self._conn.execute(
                "SELECT id, name, description, created_by, created_at, updated_at "
                "FROM shortlists WHERE created_by = ? ORDER BY created_at DESC",
                [created_by],
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, name, description, created_by, created_at, updated_at "
                "FROM shortlists ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "id": r[0],
                "name": r[1],
                "description": r[2],
                "created_by": r[3],
                "created_at": r[4],
                "updated_at": r[5],
            }
            for r in rows
        ]

    def add_candidate(
        self, shortlist_id: str, candidate_uuid: str, added_by: str
    ) -> None:
        """Add a candidate to a shortlist."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO shortlist_members (shortlist_id, candidate_uuid, added_at, added_by)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (shortlist_id, candidate_uuid) DO NOTHING
            """,
            [shortlist_id, candidate_uuid, now, added_by],
        )

    def remove_candidate(
        self, shortlist_id: str, candidate_uuid: str
    ) -> None:
        """Remove a candidate from a shortlist."""
        self._conn.execute(
            "DELETE FROM shortlist_members "
            "WHERE shortlist_id = ? AND candidate_uuid = ?",
            [shortlist_id, candidate_uuid],
        )

    def get_members(self, shortlist_id: str) -> list[dict]:
        """List all members of a shortlist."""
        rows = self._conn.execute(
            "SELECT shortlist_id, candidate_uuid, added_at, added_by "
            "FROM shortlist_members WHERE shortlist_id = ? ORDER BY added_at",
            [shortlist_id],
        ).fetchall()
        return [
            {
                "shortlist_id": r[0],
                "candidate_uuid": r[1],
                "added_at": r[2],
                "added_by": r[3],
            }
            for r in rows
        ]

    def delete(self, shortlist_id: str) -> None:
        """Delete a shortlist and its members."""
        self._conn.execute(
            "DELETE FROM shortlist_members WHERE shortlist_id = ?",
            [shortlist_id],
        )
        self._conn.execute(
            "DELETE FROM shortlists WHERE id = ?",
            [shortlist_id],
        )

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()
