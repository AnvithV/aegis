"""Tests for JobStore."""

from __future__ import annotations

import os
import tempfile

import pytest

from aegis.storage.job_store import JobStore


@pytest.fixture
def store() -> JobStore:
    """Create a JobStore with a temporary database."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.duckdb")
    s = JobStore(db_path=db_path)
    yield s  # type: ignore[misc]
    s.close()


def test_create_and_get(store: JobStore) -> None:
    store.create(job_id="job-1", query_text="KRAS inhibitors", created_by="alice")
    result = store.get("job-1")
    assert result is not None
    assert result["id"] == "job-1"
    assert result["query_text"] == "KRAS inhibitors"
    assert result["status"] == "in_progress"
    assert result["created_by"] == "alice"
    assert result["created_at"] is not None
    assert result["completed_at"] is None
    assert result["duration_ms"] is None
    assert result["source_count"] is None
    assert result["candidate_count"] is None


def test_get_returns_none_for_unknown(store: JobStore) -> None:
    result = store.get("nonexistent")
    assert result is None


def test_update_status(store: JobStore) -> None:
    store.create(job_id="job-2", query_text="PD-L1 research", created_by="bob")
    store.update("job-2", status="complete", candidate_count=42)
    result = store.get("job-2")
    assert result is not None
    assert result["status"] == "complete"
    assert result["candidate_count"] == 42


def test_update_rejects_invalid_column(store: JobStore) -> None:
    store.create(job_id="job-3", query_text="test", created_by="alice")
    with pytest.raises(ValueError, match="Invalid column"):
        store.update("job-3", status="complete", query_text="hacked")


def test_list_all_paginated(store: JobStore) -> None:
    for i in range(3):
        store.create(job_id=f"job-{i}", query_text=f"query {i}", created_by="alice")
    items, total = store.list_all(created_by="alice", per_page=2)
    assert len(items) == 2
    assert total == 3


def test_list_all_filters_by_creator(store: JobStore) -> None:
    store.create(job_id="job-a", query_text="alice query", created_by="alice")
    store.create(job_id="job-b", query_text="bob query", created_by="bob")

    alice_items, alice_total = store.list_all(created_by="alice")
    assert len(alice_items) == 1
    assert alice_total == 1
    assert alice_items[0]["created_by"] == "alice"

    bob_items, bob_total = store.list_all(created_by="bob")
    assert len(bob_items) == 1
    assert bob_total == 1
    assert bob_items[0]["created_by"] == "bob"
