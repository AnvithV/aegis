"""Cursor-based incremental ingestion manager for all source clients."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

import duckdb
from pydantic import BaseModel, ConfigDict

from aegis.sources.ctgov import CtgovClient, StudyRecord
from aegis.sources.pubmed import PubMedClient, PubMedRecord
from aegis.sources.reporter import GrantRecord, ReporterClient

logger = logging.getLogger(__name__)

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS ingestion_cursors (
    source_name TEXT PRIMARY KEY,
    cursor_value TEXT NOT NULL,
    last_batch_size INTEGER NOT NULL,
    last_run_at TIMESTAMP NOT NULL,
    total_records_ingested INTEGER NOT NULL DEFAULT 0
);
"""


class CursorState(BaseModel):
    """Persisted cursor state for a single source."""

    model_config = ConfigDict(frozen=True)

    source_name: str
    cursor_value: str
    last_batch_size: int
    last_run_at: datetime
    total_records_ingested: int


class CursorManager:
    """Manages per-source ingestion cursors in DuckDB."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)

    def get_cursor(self, source_name: str) -> CursorState | None:
        """Retrieve last cursor for a source."""
        row = self._conn.execute(
            "SELECT source_name, cursor_value, last_batch_size, "
            "last_run_at, total_records_ingested "
            "FROM ingestion_cursors WHERE source_name = ?",
            [source_name],
        ).fetchone()
        if row is None:
            return None
        return CursorState(
            source_name=row[0],
            cursor_value=row[1],
            last_batch_size=row[2],
            last_run_at=row[3],
            total_records_ingested=row[4],
        )

    def save_cursor(self, state: CursorState) -> None:
        """Persist cursor (upsert)."""
        self._conn.execute(
            "INSERT INTO ingestion_cursors "
            "(source_name, cursor_value, last_batch_size, "
            "last_run_at, total_records_ingested) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (source_name) DO UPDATE SET "
            "cursor_value = excluded.cursor_value, "
            "last_batch_size = excluded.last_batch_size, "
            "last_run_at = excluded.last_run_at, "
            "total_records_ingested = "
            "excluded.total_records_ingested",
            [
                state.source_name,
                state.cursor_value,
                state.last_batch_size,
                state.last_run_at,
                state.total_records_ingested,
            ],
        )

    def reset_cursor(self, source_name: str) -> None:
        """Delete cursor for full re-pull."""
        self._conn.execute(
            "DELETE FROM ingestion_cursors WHERE source_name = ?",
            [source_name],
        )

    def list_cursors(self) -> list[CursorState]:
        """List all active cursors."""
        rows = self._conn.execute(
            "SELECT source_name, cursor_value, last_batch_size, "
            "last_run_at, total_records_ingested "
            "FROM ingestion_cursors ORDER BY source_name"
        ).fetchall()
        return [
            CursorState(
                source_name=r[0],
                cursor_value=r[1],
                last_batch_size=r[2],
                last_run_at=r[3],
                total_records_ingested=r[4],
            )
            for r in rows
        ]

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()


class IncrementalIngester:
    """Runs incremental ingestion for each source using cursors."""

    def __init__(self, cursor_manager: CursorManager) -> None:
        self._cm = cursor_manager

    async def ingest_pubmed(
        self,
        client: PubMedClient,
        query: str,
        batch_size: int = 200,
    ) -> int:
        """Run incremental PubMed pull using cursor. Returns count."""
        source = "pubmed"
        cursor = self._cm.get_cursor(source)
        since: date | None = None
        total_prev = 0
        if cursor is not None:
            since = date.fromisoformat(cursor.cursor_value)
            total_prev = cursor.total_records_ingested

        count = 0
        latest_date: str | None = None
        batch: list[PubMedRecord] = []

        async for record in client.search_and_fetch(
            query, since=since, batch_size=batch_size
        ):
            batch.append(record)
            count += 1

            # Track latest publication date for cursor
            if record.publication_date is not None:
                d = record.publication_date.isoformat()
                if latest_date is None or d > latest_date:
                    latest_date = d

            # Checkpoint at end of each batch
            if len(batch) >= batch_size:
                self._save_pubmed_cursor(
                    source, latest_date, len(batch),
                    total_prev + count,
                )
                batch = []

        # Final checkpoint
        if batch or count > 0:
            self._save_pubmed_cursor(
                source, latest_date, len(batch),
                total_prev + count,
            )

        logger.info(
            "PubMed ingestion complete: %d new records", count
        )
        return count

    def _save_pubmed_cursor(
        self,
        source: str,
        latest_date: str | None,
        batch_size: int,
        total: int,
    ) -> None:
        cursor_val = latest_date or date.today().isoformat()
        self._cm.save_cursor(
            CursorState(
                source_name=source,
                cursor_value=cursor_val,
                last_batch_size=batch_size,
                last_run_at=datetime.now(UTC),
                total_records_ingested=total,
            )
        )

    async def ingest_reporter(
        self,
        client: ReporterClient,
        rcdc_terms: list[str],
        page_size: int = 500,
    ) -> int:
        """Run incremental RePORTER pull using cursor. Returns count."""
        source = "reporter"
        cursor = self._cm.get_cursor(source)
        since_fy: int | None = None
        total_prev = 0
        if cursor is not None:
            since_fy = int(cursor.cursor_value)
            total_prev = cursor.total_records_ingested

        count = 0
        latest_fy: int = since_fy or 0
        batch: list[GrantRecord] = []

        async for record in client.fetch_grants_by_topic(
            rcdc_terms, since_fy=since_fy, page_size=page_size
        ):
            batch.append(record)
            count += 1
            if record.fiscal_year > latest_fy:
                latest_fy = record.fiscal_year

            if len(batch) >= page_size:
                self._cm.save_cursor(
                    CursorState(
                        source_name=source,
                        cursor_value=str(latest_fy),
                        last_batch_size=len(batch),
                        last_run_at=datetime.now(UTC),
                        total_records_ingested=total_prev + count,
                    )
                )
                batch = []

        # Final checkpoint
        if batch or count > 0:
            self._cm.save_cursor(
                CursorState(
                    source_name=source,
                    cursor_value=str(latest_fy or date.today().year),
                    last_batch_size=len(batch),
                    last_run_at=datetime.now(UTC),
                    total_records_ingested=total_prev + count,
                )
            )

        logger.info(
            "RePORTER ingestion complete: %d new records", count
        )
        return count

    async def ingest_ctgov(
        self,
        client: CtgovClient,
        mesh_terms: list[str],
        page_size: int = 100,
    ) -> int:
        """Run incremental CT.gov pull using cursor. Returns count."""
        source = "ctgov"
        cursor = self._cm.get_cursor(source)
        total_prev = 0
        if cursor is not None:
            total_prev = cursor.total_records_ingested

        count = 0
        latest_date: str | None = None
        if cursor is not None:
            latest_date = cursor.cursor_value
        batch: list[StudyRecord] = []

        async for record in client.fetch_studies_by_condition(
            mesh_terms, page_size=page_size
        ):
            batch.append(record)
            count += 1

            if record.last_update_post_date is not None:
                d = record.last_update_post_date.isoformat()
                if latest_date is None or d > latest_date:
                    latest_date = d

            if len(batch) >= page_size:
                self._cm.save_cursor(
                    CursorState(
                        source_name=source,
                        cursor_value=(
                            latest_date or date.today().isoformat()
                        ),
                        last_batch_size=len(batch),
                        last_run_at=datetime.now(UTC),
                        total_records_ingested=total_prev + count,
                    )
                )
                batch = []

        # Final checkpoint
        if batch or count > 0:
            self._cm.save_cursor(
                CursorState(
                    source_name=source,
                    cursor_value=(
                        latest_date or date.today().isoformat()
                    ),
                    last_batch_size=len(batch),
                    last_run_at=datetime.now(UTC),
                    total_records_ingested=total_prev + count,
                )
            )

        logger.info(
            "CT.gov ingestion complete: %d new records", count
        )
        return count
