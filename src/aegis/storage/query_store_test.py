"""Tests for QueryStore."""

from __future__ import annotations

import os
import tempfile

import pytest

from aegis.storage.query_store import QueryStore


@pytest.fixture
def store() -> QueryStore:
    """Create a QueryStore with a temporary database."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.duckdb")
    s = QueryStore(db_path=db_path)
    yield s  # type: ignore[misc]
    s.close()


def test_save_and_get(store: QueryStore) -> None:
    store.save(
        query_id="q1",
        task_description="KRAS inhibitor drug discovery",
        query_type="drug_discovery",
        weight_vector_name="drug_discovery_v2",
        mesh_terms=["KRAS", "Lung Cancer"],
        k=10,
        result_count=5,
        candidate_uuids=["u1", "u2"],
        candidate_scores=[{"uuid": "u1", "score": 0.95, "rank": 1}],
        pipeline_duration_ms=1234.5,
        created_by="alice",
    )
    result = store.get("q1")
    assert result is not None
    assert result["task_description"] == "KRAS inhibitor drug discovery"
    assert result["query_type"] == "drug_discovery"
    assert result["mesh_terms"] == ["KRAS", "Lung Cancer"]
    assert result["candidate_uuids"] == ["u1", "u2"]
    assert result["candidate_scores"][0]["score"] == 0.95
    assert result["pipeline_duration_ms"] == 1234.5


def test_list_all_with_pagination(store: QueryStore) -> None:
    for i in range(5):
        store.save(
            query_id=f"q{i}",
            task_description=f"Query {i}",
            k=10,
            result_count=i,
        )
    items, total = store.list_all(page=1, per_page=2)
    assert total == 5
    assert len(items) == 2

    items_p2, _ = store.list_all(page=2, per_page=2)
    assert len(items_p2) == 2

    items_p3, _ = store.list_all(page=3, per_page=2)
    assert len(items_p3) == 1


def test_rename_query(store: QueryStore) -> None:
    store.save(
        query_id="q1",
        task_description="Test query",
        k=10,
        result_count=3,
    )
    store.rename("q1", "My saved search")
    result = store.get("q1")
    assert result is not None
    assert result["custom_name"] == "My saved search"


def test_get_nonexistent_returns_none(store: QueryStore) -> None:
    result = store.get("nonexistent")
    assert result is None


def test_list_all_filter_by_creator(store: QueryStore) -> None:
    store.save(
        query_id="q1", task_description="A", k=10, result_count=1, created_by="alice"
    )
    store.save(
        query_id="q2", task_description="B", k=10, result_count=1, created_by="bob"
    )
    items, total = store.list_all(created_by="alice")
    assert total == 1
    assert items[0]["created_by"] == "alice"
