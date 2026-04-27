"""Tests for candidate opt-out enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.privacy.opt_out import (
    OptOutAction,
    OptOutRecord,
    OptOutStore,
)


def test_opt_out(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    store.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    assert store.is_opted_out("cand-1") is True


def test_opt_in_reversal(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    store.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    store.opt_in(candidate_uuid="cand-1", verified_via="orcid")
    assert store.is_opted_out("cand-1") is False


def test_default_not_opted_out(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    assert store.is_opted_out("cand-1") is False


def test_get_all_opted_out(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    store.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    store.opt_out(candidate_uuid="cand-2", verified_via="npi")
    store.opt_out(candidate_uuid="cand-3", verified_via="admin")
    store.opt_in(candidate_uuid="cand-2", verified_via="npi")
    opted_out = store.get_all_opted_out()
    assert len(opted_out) == 2
    assert "cand-1" in opted_out
    assert "cand-3" in opted_out


def test_filter_candidates(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    store.opt_out(candidate_uuid="cand-2", verified_via="orcid")
    result = store.filter_candidates(["cand-1", "cand-2", "cand-3"])
    assert result == ["cand-1", "cand-3"]


def test_get_status(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    store.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    store.opt_in(candidate_uuid="cand-1", verified_via="orcid")
    status = store.get_status("cand-1")
    assert status.is_opted_out is False
    assert status.history_count == 2


def test_get_history(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    store.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    store.opt_in(candidate_uuid="cand-1", verified_via="orcid")
    store.opt_out(candidate_uuid="cand-1", verified_via="admin")
    history = store.get_history("cand-1")
    assert len(history) == 3
    assert history[0].action == OptOutAction.opt_out
    assert history[1].action == OptOutAction.opt_in
    assert history[2].action == OptOutAction.opt_out


def test_append_only_persistence(tmp_path: Path) -> None:
    path = tmp_path / "opt_out.jsonl"
    store1 = OptOutStore(storage_path=path)
    store1.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    store2 = OptOutStore(storage_path=path)
    assert store2.is_opted_out("cand-1") is True


def test_opt_out_record_model() -> None:
    from datetime import UTC, datetime

    record = OptOutRecord(
        record_id="abc123",
        candidate_uuid="cand-1",
        action=OptOutAction.opt_out,
        reason="personal request",
        verified_via="orcid",
        timestamp=datetime.now(tz=UTC),
    )
    with pytest.raises(Exception):  # noqa: B017
        record.candidate_uuid = "cand-2"


def test_stats(tmp_path: Path) -> None:
    store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    store.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    store.opt_out(candidate_uuid="cand-2", verified_via="npi")
    store.opt_out(candidate_uuid="cand-3", verified_via="admin")
    store.opt_in(candidate_uuid="cand-2", verified_via="npi")
    stats = store.get_stats()
    assert stats.current_opted_out_count == 2
    assert stats.total_opt_in_reversals == 1
