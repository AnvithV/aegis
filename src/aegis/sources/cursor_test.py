"""Tests for cursor-based incremental ingestion."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from aegis.sources.cursor import CursorManager, CursorState, IncrementalIngester
from aegis.sources.pubmed import PubMedRecord
from aegis.storage.schema import MeshDescriptor


@pytest.fixture
def cursor_db(tmp_path: object) -> CursorManager:
    """Create a CursorManager backed by a temp DuckDB file."""
    db_path = f"{tmp_path}/test_cursors.duckdb"
    return CursorManager(db_path=db_path)


def _make_cursor(
    source: str = "pubmed",
    value: str = "2024-01-01",
    batch: int = 100,
    total: int = 500,
) -> CursorState:
    return CursorState(
        source_name=source,
        cursor_value=value,
        last_batch_size=batch,
        last_run_at=datetime(2024, 1, 15, tzinfo=UTC),
        total_records_ingested=total,
    )


def test_cursor_round_trip(cursor_db: CursorManager) -> None:
    """Save cursor, retrieve it, assert fields match."""
    state = _make_cursor()
    cursor_db.save_cursor(state)

    loaded = cursor_db.get_cursor("pubmed")
    assert loaded is not None
    assert loaded.source_name == "pubmed"
    assert loaded.cursor_value == "2024-01-01"
    assert loaded.last_batch_size == 100
    assert loaded.total_records_ingested == 500


def test_cursor_upsert(cursor_db: CursorManager) -> None:
    """Save cursor twice with different values, latest wins."""
    cursor_db.save_cursor(_make_cursor(value="2024-01-01"))
    cursor_db.save_cursor(_make_cursor(value="2024-06-15", total=1000))

    loaded = cursor_db.get_cursor("pubmed")
    assert loaded is not None
    assert loaded.cursor_value == "2024-06-15"
    assert loaded.total_records_ingested == 1000


def test_cursor_reset(cursor_db: CursorManager) -> None:
    """Save cursor, reset it, assert None returned."""
    cursor_db.save_cursor(_make_cursor())
    cursor_db.reset_cursor("pubmed")

    assert cursor_db.get_cursor("pubmed") is None


def test_list_cursors(cursor_db: CursorManager) -> None:
    """Save 3 cursors for different sources, list all."""
    cursor_db.save_cursor(_make_cursor(source="pubmed"))
    cursor_db.save_cursor(_make_cursor(source="reporter"))
    cursor_db.save_cursor(_make_cursor(source="ctgov"))

    cursors = cursor_db.list_cursors()
    assert len(cursors) == 3
    names = {c.source_name for c in cursors}
    assert names == {"pubmed", "reporter", "ctgov"}


def _make_pubmed_record(
    pmid: str, pub_date: date | None = None
) -> PubMedRecord:
    return PubMedRecord(
        pmid=pmid,
        title=f"Article {pmid}",
        abstract=None,
        mesh_descriptors=[
            MeshDescriptor(
                descriptor="Test",
                qualifier=None,
                major_topic=False,
            )
        ],
        authors=[],
        journal_nlm_id=None,
        medline_indexed=True,
        publication_date=pub_date,
        article_type="Journal Article",
        raw_xml=f"<xml>{pmid}</xml>",
    )


@pytest.mark.asyncio
async def test_incremental_pubmed_uses_cursor(
    cursor_db: CursorManager,
) -> None:
    """Mock PubMedClient, verify since= uses cursor date."""
    # Pre-seed cursor
    cursor_db.save_cursor(
        _make_cursor(source="pubmed", value="2024-03-01", total=100)
    )

    records = [
        _make_pubmed_record("111", date(2024, 3, 15)),
        _make_pubmed_record("222", date(2024, 4, 1)),
    ]

    async def mock_search(
        query: str,
        since: date | None = None,
        batch_size: int = 200,
    ) -> AsyncIterator[PubMedRecord]:
        # Verify the cursor date is passed
        assert since == date(2024, 3, 1)
        for r in records:
            yield r

    client = MagicMock()
    client.search_and_fetch = mock_search

    ingester = IncrementalIngester(cursor_db)
    count = await ingester.ingest_pubmed(client, "cancer")

    assert count == 2

    # Cursor should be updated
    cursor = cursor_db.get_cursor("pubmed")
    assert cursor is not None
    assert cursor.cursor_value == "2024-04-01"
    assert cursor.total_records_ingested == 102  # 100 prev + 2 new


@pytest.mark.asyncio
async def test_cursor_persisted_on_crash(
    cursor_db: CursorManager,
) -> None:
    """Simulate crash mid-batch, verify cursor saved at last batch."""
    batch_size = 2

    call_count = 0

    async def mock_search(
        query: str,
        since: date | None = None,
        batch_size: int = 200,
    ) -> AsyncIterator[PubMedRecord]:
        nonlocal call_count
        # Yield a full batch, then crash on third record
        yield _make_pubmed_record("r1", date(2024, 1, 10))
        yield _make_pubmed_record("r2", date(2024, 1, 20))
        # At this point batch checkpoint should happen
        yield _make_pubmed_record("r3", date(2024, 2, 1))
        msg = "Simulated crash"
        raise RuntimeError(msg)

    client = MagicMock()
    client.search_and_fetch = mock_search

    ingester = IncrementalIngester(cursor_db)

    with pytest.raises(RuntimeError, match="Simulated crash"):
        await ingester.ingest_pubmed(
            client, "cancer", batch_size=batch_size
        )

    # Cursor should have been saved at the batch checkpoint
    cursor = cursor_db.get_cursor("pubmed")
    assert cursor is not None
    # The batch of 2 should have been checkpointed
    assert cursor.total_records_ingested == 2
    assert cursor.cursor_value == "2024-01-20"
