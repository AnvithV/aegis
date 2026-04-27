"""Tests for pairwise judgment storage and audit harness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from aegis.audit.harness import (
    AuditHarness,
    PairSampler,
    PairwisePrompt,
    ScoredCandidate,
    SessionManager,
)
from aegis.audit.storage import JudgmentStore, PairwiseJudgment


def _make_judgment(
    *,
    reviewer_id: str = "reviewer-1",
    session_id: str = "session-1",
) -> PairwiseJudgment:
    """Create a sample judgment for testing."""
    return PairwiseJudgment(
        judgment_id=str(uuid4()),
        reviewer_id=reviewer_id,
        query_mesh_terms=["D009369", "D001943"],
        candidate_a_uuid=str(uuid4()),
        candidate_b_uuid=str(uuid4()),
        winner_uuid=str(uuid4()),
        timestamp=datetime.now(tz=UTC),
        evidence_shown={"summary": "test evidence"},
        session_id=session_id,
    )


class TestJudgmentStore:
    """Tests for JudgmentStore append-only JSONL storage."""

    def test_append_and_load(self, tmp_path: Path) -> None:
        """Append 3 judgments, load all, verify count and content."""
        store = JudgmentStore(storage_path=tmp_path / "judgments.jsonl")
        judgments = [_make_judgment() for _ in range(3)]

        for j in judgments:
            store.append(judgment=j)

        loaded = store.load_all()
        assert len(loaded) == 3
        assert store.count() == 3

        for original, restored in zip(judgments, loaded, strict=True):
            assert original.judgment_id == restored.judgment_id
            assert original.reviewer_id == restored.reviewer_id
            assert original.query_mesh_terms == restored.query_mesh_terms

    def test_empty_file(self, tmp_path: Path) -> None:
        """Load from nonexistent path returns empty list."""
        store = JudgmentStore(
            storage_path=tmp_path / "nonexistent.jsonl"
        )
        assert store.load_all() == []
        assert store.count() == 0

    def test_by_reviewer(self, tmp_path: Path) -> None:
        """Filter judgments by reviewer_id."""
        store = JudgmentStore(storage_path=tmp_path / "judgments.jsonl")

        store.append(judgment=_make_judgment(reviewer_id="alice"))
        store.append(judgment=_make_judgment(reviewer_id="bob"))
        store.append(judgment=_make_judgment(reviewer_id="alice"))

        alice_judgments = store.by_reviewer(reviewer_id="alice")
        assert len(alice_judgments) == 2
        assert all(j.reviewer_id == "alice" for j in alice_judgments)

        bob_judgments = store.by_reviewer(reviewer_id="bob")
        assert len(bob_judgments) == 1
        assert bob_judgments[0].reviewer_id == "bob"


# ---------------------------------------------------------------------------
# Helpers for harness tests
# ---------------------------------------------------------------------------


def _make_candidates(n: int) -> list[ScoredCandidate]:
    """Create n scored candidates with linearly spaced scores."""
    return [
        ScoredCandidate(
            uuid=str(uuid4()),
            name=f"candidate-{i}",
            score=float(i) / max(n - 1, 1),
            evidence={"pub_count": str(i * 10)},
        )
        for i in range(n)
    ]


def _make_judgment_for_pair(
    *,
    candidate_a_uuid: str,
    candidate_b_uuid: str,
    reviewer_id: str = "reviewer-1",
) -> PairwiseJudgment:
    """Create a judgment for a specific pair."""
    return PairwiseJudgment(
        judgment_id=str(uuid4()),
        reviewer_id=reviewer_id,
        query_mesh_terms=["D009369"],
        candidate_a_uuid=candidate_a_uuid,
        candidate_b_uuid=candidate_b_uuid,
        winner_uuid=candidate_a_uuid,
        timestamp=datetime.now(tz=UTC),
        evidence_shown={"summary": "test"},
        session_id="session-1",
    )


# ---------------------------------------------------------------------------
# PairSampler tests
# ---------------------------------------------------------------------------


class TestPairSampler:
    """Tests for PairSampler active-learning pair selection."""

    def test_pair_sampler_returns_prompts(self) -> None:
        """5 candidates, sample 3 pairs, verify 3 PairwisePrompt objects."""
        sampler = PairSampler(rng_seed=42)
        candidates = _make_candidates(5)

        prompts = sampler.sample_pairs(
            candidates=candidates,
            query_mesh=["D009369"],
            n_pairs=3,
        )

        assert len(prompts) == 3
        assert all(isinstance(p, PairwisePrompt) for p in prompts)
        # Each prompt should have unique prompt_id
        ids = [p.prompt_id for p in prompts]
        assert len(set(ids)) == 3

    def test_pair_sampler_active_learning_bias(self) -> None:
        """Sampled pairs tend to have closer scores than random baseline.

        Run multiple rounds with different seeds and check the average
        across all rounds to smooth out random noise.
        """
        n_rounds = 20
        total_sampled_gap = 0.0
        total_random_gap = 0.0

        for seed in range(n_rounds):
            sampler = PairSampler(rng_seed=seed)
            candidates = _make_candidates(20)

            prompts = sampler.sample_pairs(
                candidates=candidates,
                query_mesh=["D009369"],
                n_pairs=10,
            )

            score_by_uuid = {c.uuid: c.score for c in candidates}
            gaps = [
                abs(
                    score_by_uuid[p.candidate_a_uuid]
                    - score_by_uuid[p.candidate_b_uuid]
                )
                for p in prompts
            ]
            total_sampled_gap += sum(gaps) / len(gaps)

            all_gaps = [
                abs(candidates[i].score - candidates[j].score)
                for i in range(len(candidates))
                for j in range(i + 1, len(candidates))
            ]
            total_random_gap += sum(all_gaps) / len(all_gaps)

        avg_sampled = total_sampled_gap / n_rounds
        avg_random = total_random_gap / n_rounds

        # Active-learning bias should produce smaller average gap
        assert avg_sampled < avg_random

    def test_pair_sampler_excludes_existing(self) -> None:
        """Existing judgments are not re-sampled."""
        sampler = PairSampler(rng_seed=42)
        candidates = _make_candidates(3)
        # 3 candidates -> 3 possible pairs

        # Judge all 3 pairs
        existing = [
            _make_judgment_for_pair(
                candidate_a_uuid=candidates[i].uuid,
                candidate_b_uuid=candidates[j].uuid,
            )
            for i in range(3)
            for j in range(i + 1, 3)
        ]

        prompts = sampler.sample_pairs(
            candidates=candidates,
            query_mesh=["D009369"],
            n_pairs=5,
            existing_judgments=existing,
        )

        assert len(prompts) == 0


# ---------------------------------------------------------------------------
# SessionManager tests
# ---------------------------------------------------------------------------


class TestSessionManager:
    """Tests for session limits and cooldowns."""

    def test_session_manager_limit(self) -> None:
        """can_continue returns False after max_pairs."""
        mgr = SessionManager(max_pairs_per_session=5, cooldown_minutes=0)
        now = datetime.now(tz=UTC)

        assert mgr.can_continue(
            reviewer_id="r1",
            session_judgments=4,
            session_start=now,
        )
        assert not mgr.can_continue(
            reviewer_id="r1",
            session_judgments=5,
            session_start=now,
        )

    def test_session_manager_cooldown(self) -> None:
        """Cooldown enforcement between sessions."""
        mgr = SessionManager(
            max_pairs_per_session=20, cooldown_minutes=60
        )
        now = datetime.now(tz=UTC)

        # Record a session end
        mgr.record_session_end(reviewer_id="r1", timestamp=now)

        # Trying to start a new session immediately should fail
        assert not mgr.can_continue(
            reviewer_id="r1",
            session_judgments=0,
            session_start=now + timedelta(minutes=30),
        )

        # After cooldown passes, should succeed
        assert mgr.can_continue(
            reviewer_id="r1",
            session_judgments=0,
            session_start=now + timedelta(minutes=61),
        )


# ---------------------------------------------------------------------------
# AuditHarness tests
# ---------------------------------------------------------------------------


class TestAuditHarness:
    """Tests for the AuditHarness facade."""

    def test_audit_harness_next_pair(self, tmp_path: Path) -> None:
        """End-to-end: next_pair returns a prompt."""
        store = JudgmentStore(storage_path=tmp_path / "j.jsonl")
        sampler = PairSampler(rng_seed=42)
        mgr = SessionManager()
        harness = AuditHarness(
            store=store, sampler=sampler, session_mgr=mgr
        )

        candidates = _make_candidates(5)
        prompt = harness.next_pair(
            reviewer_id="r1",
            candidates=candidates,
            query_mesh=["D009369"],
        )

        assert prompt is not None
        assert isinstance(prompt, PairwisePrompt)
        assert prompt.candidate_a_uuid != prompt.candidate_b_uuid

    def test_inter_reviewer_kappa(self, tmp_path: Path) -> None:
        """2 reviewers, 5 overlapping pairs, 80% agreement -> kappa > 0."""
        store = JudgmentStore(storage_path=tmp_path / "j.jsonl")
        sampler = PairSampler(rng_seed=42)
        mgr = SessionManager()
        harness = AuditHarness(
            store=store, sampler=sampler, session_mgr=mgr
        )

        # Create 5 pairs with 2 reviewers each
        candidates = _make_candidates(6)
        pairs = [
            (candidates[i].uuid, candidates[i + 1].uuid)
            for i in range(5)
        ]

        for idx, (a, b) in enumerate(pairs):
            # Reviewer 1 always picks a
            harness.submit_judgment(
                judgment=PairwiseJudgment(
                    judgment_id=str(uuid4()),
                    reviewer_id="r1",
                    query_mesh_terms=["D009369"],
                    candidate_a_uuid=a,
                    candidate_b_uuid=b,
                    winner_uuid=a,
                    timestamp=datetime.now(tz=UTC),
                    evidence_shown={"summary": "test"},
                    session_id="s1",
                )
            )
            # Reviewer 2 agrees 80% of the time (disagrees on last pair)
            winner = a if idx < 4 else b
            harness.submit_judgment(
                judgment=PairwiseJudgment(
                    judgment_id=str(uuid4()),
                    reviewer_id="r2",
                    query_mesh_terms=["D009369"],
                    candidate_a_uuid=a,
                    candidate_b_uuid=b,
                    winner_uuid=winner,
                    timestamp=datetime.now(tz=UTC),
                    evidence_shown={"summary": "test"},
                    session_id="s2",
                )
            )

        kappa = harness.inter_reviewer_kappa()
        assert kappa is not None
        assert kappa > 0.0
