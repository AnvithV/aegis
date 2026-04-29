"""Tests for ShortlistStore."""

from __future__ import annotations

import os
import tempfile

import pytest

from aegis.storage.shortlist_store import ShortlistStore


@pytest.fixture
def store() -> ShortlistStore:
    """Create a ShortlistStore with a temporary database."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.duckdb")
    s = ShortlistStore(db_path=db_path)
    yield s  # type: ignore[misc]
    s.close()


def test_create_and_get(store: ShortlistStore) -> None:
    sid = store.create(
        name="Top picks", description="Best candidates", created_by="alice"
    )
    result = store.get(sid)
    assert result is not None
    assert result["name"] == "Top picks"
    assert result["description"] == "Best candidates"
    assert result["created_by"] == "alice"


def test_list_all_filters_by_creator(store: ShortlistStore) -> None:
    store.create(name="A", description=None, created_by="alice")
    store.create(name="B", description=None, created_by="bob")

    alice_lists = store.list_all(created_by="alice")
    assert len(alice_lists) == 1
    assert alice_lists[0]["name"] == "A"

    all_lists = store.list_all()
    assert len(all_lists) == 2


def test_add_and_remove_candidate(store: ShortlistStore) -> None:
    sid = store.create(name="S1", description=None, created_by="alice")
    store.add_candidate(sid, "cand-001", added_by="alice")
    store.add_candidate(sid, "cand-002", added_by="alice")

    members = store.get_members(sid)
    assert len(members) == 2
    uuids = {m["candidate_uuid"] for m in members}
    assert uuids == {"cand-001", "cand-002"}

    store.remove_candidate(sid, "cand-001")
    members = store.get_members(sid)
    assert len(members) == 1
    assert members[0]["candidate_uuid"] == "cand-002"


def test_delete_shortlist(store: ShortlistStore) -> None:
    sid = store.create(name="To delete", description=None, created_by="alice")
    store.add_candidate(sid, "cand-001", added_by="alice")

    store.delete(sid)
    assert store.get(sid) is None
    assert store.get_members(sid) == []


def test_add_duplicate_candidate_no_error(store: ShortlistStore) -> None:
    sid = store.create(name="Dupes", description=None, created_by="alice")
    store.add_candidate(sid, "cand-001", added_by="alice")
    store.add_candidate(sid, "cand-001", added_by="alice")

    members = store.get_members(sid)
    assert len(members) == 1
