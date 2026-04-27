"""Tests for integrity contestability override store."""

from __future__ import annotations

from pathlib import Path

from aegis.integrity.contestability import (
    ContestabilityStore,
    OverrideAction,
    OverrideRecord,
)


def test_add_override_persists(tmp_path: Path) -> None:
    store = ContestabilityStore(storage_path=tmp_path / "overrides.jsonl")
    record = store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev1",
        action=OverrideAction.override,
        justification="false positive",
        original_reason="retraction flag",
    )
    assert isinstance(record, OverrideRecord)

    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].record_id == record.record_id
    assert loaded[0].candidate_uuid == "c1"


def test_is_overridden_after_override(tmp_path: Path) -> None:
    store = ContestabilityStore(storage_path=tmp_path / "overrides.jsonl")
    store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev1",
        action=OverrideAction.override,
        justification="false positive",
        original_reason="retraction flag",
    )
    assert store.is_overridden("c1") is True


def test_is_overridden_after_revoke(tmp_path: Path) -> None:
    store = ContestabilityStore(storage_path=tmp_path / "overrides.jsonl")
    store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev1",
        action=OverrideAction.override,
        justification="false positive",
        original_reason="retraction flag",
    )
    store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev1",
        action=OverrideAction.revoke,
        justification="new evidence found",
        original_reason="retraction flag",
    )
    assert store.is_overridden("c1") is False


def test_append_only(tmp_path: Path) -> None:
    store = ContestabilityStore(storage_path=tmp_path / "overrides.jsonl")
    store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev1",
        action=OverrideAction.override,
        justification="false positive",
        original_reason="retraction flag",
    )
    store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev1",
        action=OverrideAction.revoke,
        justification="new evidence",
        original_reason="retraction flag",
    )
    store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev2",
        action=OverrideAction.override,
        justification="confirmed false positive",
        original_reason="retraction flag",
    )
    history = store.get_history("c1")
    assert len(history) == 3


def test_nonexistent_candidate(tmp_path: Path) -> None:
    store = ContestabilityStore(storage_path=tmp_path / "overrides.jsonl")
    assert store.is_overridden("unknown") is False


def test_get_history_chronological(tmp_path: Path) -> None:
    store = ContestabilityStore(storage_path=tmp_path / "overrides.jsonl")
    r1 = store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev1",
        action=OverrideAction.override,
        justification="first",
        original_reason="retraction flag",
    )
    r2 = store.add_override(
        candidate_uuid="c1",
        reviewer_id="rev2",
        action=OverrideAction.revoke,
        justification="second",
        original_reason="retraction flag",
    )
    history = store.get_history("c1")
    assert len(history) == 2
    assert history[0].record_id == r1.record_id
    assert history[1].record_id == r2.record_id
    assert history[0].timestamp <= history[1].timestamp
