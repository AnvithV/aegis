"""NotesStore: DuckDB-backed storage for candidate notes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from aegis.config import get_db_path


class NotesStore:
    """Persistent store for candidate notes backed by DuckDB."""

    def __init__(self, db_path: str | None = None) -> None:
        self._conn = duckdb.connect(db_path or get_db_path())
        self._run_migrations()

    def _run_migrations(self) -> None:
        migration_dir = Path(__file__).parent / "migrations"
        for sql_file in sorted(migration_dir.glob("*.sql")):
            sql = sql_file.read_text()
            self._conn.execute(sql)

    def create(
        self, *, candidate_uuid: str, author: str, content: str
    ) -> str:
        """Create a new note and return its ID."""
        note_id = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO candidate_notes (id, candidate_uuid, author, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [note_id, candidate_uuid, author, content, now, now],
        )
        return note_id

    def get_for_candidate(self, candidate_uuid: str) -> list[dict]:
        """List all notes for a candidate, newest first."""
        rows = self._conn.execute(
            "SELECT id, candidate_uuid, author, content, created_at, updated_at "
            "FROM candidate_notes WHERE candidate_uuid = ? ORDER BY created_at DESC",
            [candidate_uuid],
        ).fetchall()
        return [
            {
                "id": r[0],
                "candidate_uuid": r[1],
                "author": r[2],
                "content": r[3],
                "created_at": r[4],
                "updated_at": r[5],
            }
            for r in rows
        ]

    def update(self, note_id: str, content: str) -> None:
        """Update a note's content."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "UPDATE candidate_notes SET content = ?, updated_at = ? WHERE id = ?",
            [content, now, note_id],
        )

    def delete(self, note_id: str) -> None:
        """Delete a note."""
        self._conn.execute(
            "DELETE FROM candidate_notes WHERE id = ?",
            [note_id],
        )

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()
