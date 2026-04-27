"""Tests for end-to-end Rank(c,q) wiring and result formatting."""

from __future__ import annotations

import pytest

from aegis.scoring.rank import (
    CandidateScoreInput,
    Ranker,
)
from aegis.scoring.result_format import ContributingArtifact


def _candidate(
    uuid: str = "u1",
    name: str = "Alice",
    integrity: float = 1.0,
    quality: float = 0.8,
    topical: float = 0.7,
    recency: float = 0.6,
    is_hard_zero: bool = False,
    artifacts: list[ContributingArtifact] | None = None,
    evidence: list[str] | None = None,
) -> CandidateScoreInput:
    return CandidateScoreInput(
        candidate_uuid=uuid,
        candidate_name=name,
        linkage_confidence=0.95,
        integrity_score=integrity,
        quality_percentile=quality,
        topical_fit=topical,
        recency=recency,
        is_hard_zero=is_hard_zero,
        top_artifacts=artifacts or [],
        evidence_trail=evidence or [],
    )


MESH = ["D001158", "D006333"]


class TestRanker:
    """Suite for Ranker.rank."""

    ranker = Ranker()

    def test_ranking_order(self) -> None:
        """Higher-scored candidates appear first."""
        c1 = _candidate(uuid="high", quality=0.95, topical=0.9, recency=0.8)
        c2 = _candidate(uuid="low", quality=0.3, topical=0.2, recency=0.1)
        result = self.ranker.rank(MESH, [c2, c1])
        assert result.candidates[0].candidate_uuid == "high"
        assert result.candidates[1].candidate_uuid == "low"

    def test_hard_zero_exclusion(self) -> None:
        """Hard-zero candidates should be excluded."""
        c1 = _candidate(uuid="ok")
        c2 = _candidate(uuid="bad", is_hard_zero=True)
        result = self.ranker.rank(MESH, [c1, c2])
        assert result.result_count == 1
        assert result.excluded_count == 1
        uuids = [c.candidate_uuid for c in result.candidates]
        assert "bad" not in uuids

    def test_integrity_zero_excluded(self) -> None:
        """Candidates with integrity_score=0 should be excluded."""
        c1 = _candidate(uuid="ok")
        c2 = _candidate(uuid="zero_int", integrity=0.0)
        result = self.ranker.rank(MESH, [c1, c2])
        assert result.excluded_count == 1
        assert result.result_count == 1

    def test_top_k_limit(self) -> None:
        """Only top-k candidates should be returned."""
        candidates = [
            _candidate(uuid=f"c{i}", quality=0.5 + i * 0.01)
            for i in range(10)
        ]
        result = self.ranker.rank(MESH, candidates, k=3)
        assert result.result_count == 3
        assert result.cohort_size == 10

    def test_component_breakdown(self) -> None:
        """Breakdown should contain raw and powered values."""
        c = _candidate(quality=0.8, topical=0.7, recency=0.6)
        result = self.ranker.rank(MESH, [c])
        bd = result.candidates[0].breakdown
        assert bd.quality_prior == pytest.approx(0.8)
        assert bd.topical_fit == pytest.approx(0.7)
        assert bd.recency == pytest.approx(0.6)
        # Powered values
        assert bd.quality_prior_powered == pytest.approx(0.8**0.7, abs=1e-6)
        assert bd.topical_fit_powered == pytest.approx(0.7**1.0, abs=1e-6)
        assert bd.recency_powered == pytest.approx(0.6**0.4, abs=1e-6)

    def test_final_score_formula(self) -> None:
        """Final score = I * Q^alpha * T^beta * R^gamma."""
        c = _candidate(
            integrity=0.9, quality=0.8, topical=0.7, recency=0.6
        )
        result = self.ranker.rank(MESH, [c])
        bd = result.candidates[0].breakdown
        expected = 0.9 * (0.8**0.7) * (0.7**1.0) * (0.6**0.4)
        assert bd.final_score == pytest.approx(expected, abs=1e-6)

    def test_custom_exponents(self) -> None:
        """Custom exponents should be reflected in output and scoring."""
        ranker = Ranker(alpha=1.0, beta=1.0, gamma=1.0)
        c = _candidate(
            integrity=1.0, quality=0.5, topical=0.4, recency=0.3
        )
        result = ranker.rank(MESH, [c])
        assert result.exponents == {
            "alpha": 1.0,
            "beta": 1.0,
            "gamma": 1.0,
        }
        bd = result.candidates[0].breakdown
        expected = 1.0 * 0.5 * 0.4 * 0.3
        assert bd.final_score == pytest.approx(expected, abs=1e-6)

    def test_artifact_limiting(self) -> None:
        """Top artifacts should be limited to 3."""
        arts = [
            ContributingArtifact(
                artifact_type="paper",
                identifier=f"pmid{i}",
                title=f"Paper {i}",
                contribution_score=float(i),
            )
            for i in range(5)
        ]
        c = _candidate(artifacts=arts)
        result = self.ranker.rank(MESH, [c])
        assert len(result.candidates[0].top_artifacts) == 3

    def test_evidence_trail_preserved(self) -> None:
        """Evidence trail should be passed through."""
        trail = ["PubMed:12345", "iCite:67890"]
        c = _candidate(evidence=trail)
        result = self.ranker.rank(MESH, [c])
        assert result.candidates[0].evidence_trail == trail

    def test_empty_candidates(self) -> None:
        """Empty candidate list should return empty result."""
        result = self.ranker.rank(MESH, [])
        assert result.result_count == 0
        assert result.excluded_count == 0
        assert result.candidates == []

    def test_weight_version_in_output(self) -> None:
        """Weight version should appear in the output."""
        ranker = Ranker(weight_version=42)
        result = ranker.rank(MESH, [_candidate()])
        assert result.weight_version == 42

    def test_metadata_passthrough(self) -> None:
        """Metadata dict should be preserved in output."""
        meta = {"query_id": "q123", "source": "test"}
        result = self.ranker.rank(MESH, [_candidate()], metadata=meta)
        assert result.metadata == meta
