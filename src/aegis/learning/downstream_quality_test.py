"""Tests for downstream quality store and pairwise derivation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from aegis.learning.downstream_quality import (
    DownstreamQualityStore,
    TaskOutcome,
    TaskOutcomeCandidate,
)
from aegis.learning.plackett_luce import JudgmentRecord


def _make_candidate(
    uuid: str,
    rank: int,
    qp: float = 0.5,
    tf: float = 0.5,
    rc: float = 0.5,
) -> TaskOutcomeCandidate:
    return TaskOutcomeCandidate(
        candidate_uuid=uuid,
        candidate_rank=rank,
        quality_prior_score=qp,
        topical_fit_score=tf,
        recency_score=rc,
    )


def _make_outcome(
    task_id: str = "task-1",
    specialty: str = "translational",
    candidates: list[TaskOutcomeCandidate] | None = None,
    fleiss_kappa: float | None = 0.7,
    accept_rate: float | None = 0.85,
    consensus_rate: float | None = 0.9,
) -> TaskOutcome:
    if candidates is None:
        candidates = [
            _make_candidate("c1", 1, qp=0.9, tf=0.8, rc=0.7),
            _make_candidate("c2", 2, qp=0.6, tf=0.5, rc=0.4),
            _make_candidate("c3", 3, qp=0.3, tf=0.2, rc=0.1),
        ]
    return TaskOutcome(
        task_id=task_id,
        query_specialty=specialty,
        query_mesh_terms=["Neoplasms", "Drug Therapy"],
        candidates=candidates,
        fleiss_kappa=fleiss_kappa,
        accept_rate=accept_rate,
        consensus_rate=consensus_rate,
        submitted_at=datetime(2026, 4, 26),
        metadata={},
    )


def test_task_outcome_model_creation() -> None:
    """Create a TaskOutcome with 3 candidates and verify all fields."""
    candidates = [
        _make_candidate("c1", 1, qp=0.9, tf=0.8, rc=0.7),
        _make_candidate("c2", 2, qp=0.6, tf=0.5, rc=0.4),
        _make_candidate("c3", 3, qp=0.3, tf=0.2, rc=0.1),
    ]
    outcome = TaskOutcome(
        task_id="task-100",
        query_specialty="translational",
        query_mesh_terms=["Neoplasms"],
        candidates=candidates,
        fleiss_kappa=0.7,
        accept_rate=0.85,
        consensus_rate=0.9,
        submitted_at=datetime(2026, 4, 26),
        metadata={"source": "test"},
    )
    assert outcome.task_id == "task-100"
    assert outcome.query_specialty == "translational"
    assert outcome.query_mesh_terms == ["Neoplasms"]
    assert len(outcome.candidates) == 3
    assert outcome.candidates[0].candidate_uuid == "c1"
    assert outcome.candidates[0].candidate_rank == 1
    assert outcome.candidates[0].quality_prior_score == 0.9
    assert outcome.candidates[0].topical_fit_score == 0.8
    assert outcome.candidates[0].recency_score == 0.7
    assert outcome.fleiss_kappa == 0.7
    assert outcome.accept_rate == 0.85
    assert outcome.consensus_rate == 0.9
    assert outcome.metadata == {"source": "test"}


def test_store_append_and_load(tmp_path: Path) -> None:
    """Append 5 outcomes, load_all returns 5, count returns 5."""
    store = DownstreamQualityStore(storage_path=tmp_path / "outcomes.jsonl")
    for i in range(5):
        store.append(outcome=_make_outcome(task_id=f"task-{i}"))
    assert len(store.load_all()) == 5
    assert store.count() == 5


def test_store_empty_file(tmp_path: Path) -> None:
    """Store with non-existent file returns empty list."""
    store = DownstreamQualityStore(
        storage_path=tmp_path / "nonexistent.jsonl"
    )
    assert store.load_all() == []


def test_by_specialty_filter(tmp_path: Path) -> None:
    """Filter by specialty returns correct subset."""
    store = DownstreamQualityStore(storage_path=tmp_path / "outcomes.jsonl")
    store.append(outcome=_make_outcome(task_id="t1", specialty="translational"))
    store.append(outcome=_make_outcome(task_id="t2", specialty="translational"))
    store.append(outcome=_make_outcome(task_id="t3", specialty="drug_discovery"))
    result = store.by_specialty(specialty="translational")
    assert len(result) == 2


def test_derive_pairwise_basic(tmp_path: Path) -> None:
    """1 outcome with 3 candidates produces 2 adjacent-pair judgments."""
    store = DownstreamQualityStore(storage_path=tmp_path / "outcomes.jsonl")
    candidates = [
        _make_candidate("c1", 1, qp=0.9, tf=0.8, rc=0.7),
        _make_candidate("c2", 2, qp=0.6, tf=0.5, rc=0.4),
        _make_candidate("c3", 3, qp=0.3, tf=0.2, rc=0.1),
    ]
    store.append(
        outcome=_make_outcome(
            candidates=candidates,
            fleiss_kappa=0.7,
            accept_rate=0.85,
            consensus_rate=0.9,
        )
    )
    judgments = store.derive_pairwise_judgments()
    assert len(judgments) == 2
    # All candidates have the same quality_signal (same outcome metrics),
    # so sorted order depends on stable sort; verify structure
    for j in judgments:
        assert isinstance(j, JudgmentRecord)
        assert "quality_prior" in j.winner_scores
        assert "topical_fit" in j.winner_scores
        assert "recency" in j.winner_scores
        assert "quality_prior" in j.loser_scores
        assert "topical_fit" in j.loser_scores
        assert "recency" in j.loser_scores


def test_derive_pairwise_single_candidate(tmp_path: Path) -> None:
    """Outcome with 1 candidate produces 0 judgments."""
    store = DownstreamQualityStore(storage_path=tmp_path / "outcomes.jsonl")
    store.append(
        outcome=_make_outcome(
            candidates=[_make_candidate("c1", 1)],
        )
    )
    judgments = store.derive_pairwise_judgments()
    assert len(judgments) == 0


def test_derive_pairwise_multiple_outcomes(tmp_path: Path) -> None:
    """3 outcomes with 3 candidates each produces 6 judgments total."""
    store = DownstreamQualityStore(storage_path=tmp_path / "outcomes.jsonl")
    for i in range(3):
        store.append(outcome=_make_outcome(task_id=f"task-{i}"))
    judgments = store.derive_pairwise_judgments()
    assert len(judgments) == 6


def test_derive_pairwise_specialty_filter(tmp_path: Path) -> None:
    """Derive with specialty filter only uses matching outcomes."""
    store = DownstreamQualityStore(storage_path=tmp_path / "outcomes.jsonl")
    store.append(
        outcome=_make_outcome(task_id="t1", specialty="translational")
    )
    store.append(
        outcome=_make_outcome(task_id="t2", specialty="translational")
    )
    store.append(
        outcome=_make_outcome(task_id="t3", specialty="drug_discovery")
    )
    trans_judgments = store.derive_pairwise_judgments(specialty="translational")
    # 2 translational outcomes * 2 adjacent pairs each = 4
    assert len(trans_judgments) == 4
    all_judgments = store.derive_pairwise_judgments()
    # 3 outcomes * 2 adjacent pairs each = 6
    assert len(all_judgments) == 6


def test_derive_pairwise_none_metrics(tmp_path: Path) -> None:
    """Outcome with some None metrics produces valid judgments."""
    store = DownstreamQualityStore(storage_path=tmp_path / "outcomes.jsonl")
    candidates = [
        _make_candidate("c1", 1, qp=0.9, tf=0.8, rc=0.7),
        _make_candidate("c2", 2, qp=0.6, tf=0.5, rc=0.4),
        _make_candidate("c3", 3, qp=0.3, tf=0.2, rc=0.1),
    ]
    store.append(
        outcome=_make_outcome(
            candidates=candidates,
            fleiss_kappa=None,
            accept_rate=0.8,
            consensus_rate=None,
        )
    )
    judgments = store.derive_pairwise_judgments()
    assert len(judgments) == 2
    for j in judgments:
        assert isinstance(j, JudgmentRecord)
