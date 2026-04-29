"""Tests for NotesStore."""

from __future__ import annotations

import os
import tempfile

import pytest

from aegis.storage.notes_store import NotesStore


@pytest.fixture
def store() -> NotesStore:
    """Create a NotesStore with a temporary database."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.duckdb")
    s = NotesStore(db_path=db_path)
    yield s  # type: ignore[misc]
    s.close()


def test_create_and_get(store: NotesStore) -> None:
    note_id = store.create(
        candidate_uuid="cand-001", author="alice", content="Great researcher"
    )
    notes = store.get_for_candidate("cand-001")
    assert len(notes) == 1
    assert notes[0]["id"] == note_id
    assert notes[0]["content"] == "Great researcher"
    assert notes[0]["author"] == "alice"


def test_update_note(store: NotesStore) -> None:
    note_id = store.create(
        candidate_uuid="cand-001", author="alice", content="Initial"
    )
    store.update(note_id, "Updated content")
    notes = store.get_for_candidate("cand-001")
    assert notes[0]["content"] == "Updated content"


def test_delete_note(store: NotesStore) -> None:
    note_id = store.create(
        candidate_uuid="cand-001", author="alice", content="To delete"
    )
    store.delete(note_id)
    notes = store.get_for_candidate("cand-001")
    assert len(notes) == 0


def test_multiple_notes_for_candidate(store: NotesStore) -> None:
    store.create(candidate_uuid="cand-001", author="alice", content="Note 1")
    store.create(candidate_uuid="cand-001", author="bob", content="Note 2")
    store.create(candidate_uuid="cand-002", author="alice", content="Note 3")

    notes_1 = store.get_for_candidate("cand-001")
    assert len(notes_1) == 2

    notes_2 = store.get_for_candidate("cand-002")
    assert len(notes_2) == 1
