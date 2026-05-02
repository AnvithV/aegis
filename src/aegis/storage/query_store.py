"""QueryStore: DuckDB-backed storage for persistent query history."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from aegis.config import get_db_path


class QueryStore:
    """Persistent store for query history backed by DuckDB."""

    def __init__(self, db_path: str | None = None) -> None:
        self._conn = duckdb.connect(db_path or get_db_path())
        self._run_migrations()

    def _run_migrations(self) -> None:
        migration_dir = Path(__file__).parent / "migrations"
        for sql_file in sorted(migration_dir.glob("*.sql")):
            sql = sql_file.read_text()
            self._conn.execute(sql)

    def save(
        self,
        *,
        query_id: str,
        task_description: str,
        query_type: str | None = None,
        weight_vector_name: str | None = None,
        mesh_terms: list[str] | None = None,
        k: int,
        result_count: int,
        candidate_uuids: list[str] | None = None,
        candidate_scores: list[dict] | None = None,
        pipeline_duration_ms: float | None = None,
        created_by: str | None = None,
    ) -> None:
        """Save a query execution to history."""
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO query_history
                (id, task_description, query_type, weight_vector_name,
                 mesh_terms, k, result_count, candidate_uuids,
                 candidate_scores, pipeline_duration_ms, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                result_count = excluded.result_count,
                candidate_uuids = excluded.candidate_uuids,
                candidate_scores = excluded.candidate_scores,
                pipeline_duration_ms = excluded.pipeline_duration_ms
            """,
            [
                query_id,
                task_description,
                query_type,
                weight_vector_name,
                json.dumps(mesh_terms) if mesh_terms else None,
                k,
                result_count,
                json.dumps(candidate_uuids) if candidate_uuids else None,
                json.dumps(candidate_scores) if candidate_scores else None,
                pipeline_duration_ms,
                now,
                created_by,
            ],
        )

    def get(self, query_id: str) -> dict | None:
        """Retrieve a query by ID."""
        result = self._conn.execute(
            "SELECT id, task_description, query_type, weight_vector_name, "
            "mesh_terms, k, result_count, candidate_uuids, candidate_scores, "
            "pipeline_duration_ms, created_at, created_by, custom_name "
            "FROM query_history WHERE id = ?",
            [query_id],
        ).fetchone()
        if result is None:
            return None
        return self._row_to_dict(result)

    def list_all(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        created_by: str | None = None,
    ) -> tuple[list[dict], int]:
        """List queries with pagination. Returns (items, total_count)."""
        offset = (page - 1) * per_page

        if created_by is not None:
            total_row = self._conn.execute(
                "SELECT COUNT(*) FROM query_history WHERE created_by = ?",
                [created_by],
            ).fetchone()
            rows = self._conn.execute(
                "SELECT id, task_description, query_type, weight_vector_name, "
                "mesh_terms, k, result_count, candidate_uuids, candidate_scores, "
                "pipeline_duration_ms, created_at, created_by, custom_name "
                "FROM query_history WHERE created_by = ? "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [created_by, per_page, offset],
            ).fetchall()
        else:
            total_row = self._conn.execute(
                "SELECT COUNT(*) FROM query_history"
            ).fetchone()
            rows = self._conn.execute(
                "SELECT id, task_description, query_type, weight_vector_name, "
                "mesh_terms, k, result_count, candidate_uuids, candidate_scores, "
                "pipeline_duration_ms, created_at, created_by, custom_name "
                "FROM query_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [per_page, offset],
            ).fetchall()

        total = int(total_row[0]) if total_row else 0
        return [self._row_to_dict(r) for r in rows], total

    def rename(self, query_id: str, custom_name: str) -> None:
        """Set a custom name for a saved query."""
        self._conn.execute(
            "UPDATE query_history SET custom_name = ? WHERE id = ?",
            [custom_name, query_id],
        )

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:  # type: ignore[type-arg]
        """Convert a database row to a dictionary."""
        mesh_terms = json.loads(row[4]) if row[4] else None
        candidate_uuids = json.loads(row[7]) if row[7] else None
        candidate_scores = json.loads(row[8]) if row[8] else None
        return {
            "id": row[0],
            "task_description": row[1],
            "query_type": row[2],
            "weight_vector_name": row[3],
            "mesh_terms": mesh_terms,
            "k": row[5],
            "result_count": row[6],
            "candidate_uuids": candidate_uuids,
            "candidate_scores": candidate_scores,
            "pipeline_duration_ms": row[9],
            "created_at": row[10],
            "created_by": row[11],
            "custom_name": row[12],
        }
