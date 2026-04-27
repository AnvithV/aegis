"""Tests for candidate vector construction and topical-fit scoring."""

from __future__ import annotations

import math

import pytest

from aegis.scoring.candidate_vector import (
    ArtifactWeight,
    CandidateVectorBuilder,
    QueryVectorBuilder,
    SparseVector,
)
from aegis.scoring.topical_fit import TopicalFit


# ── SparseVector tests ──────────────────────────────────────────────────


class TestSparseVector:
    """Core sparse-vector operations."""

    def test_add_and_get(self) -> None:
        v = SparseVector()
        v.add("a", 1.0)
        v.add("a", 2.0)
        assert v.get("a") == pytest.approx(3.0)
        assert v.get("missing") == 0.0

    def test_keys(self) -> None:
        v = SparseVector()
        v.add("x", 1.0)
        v.add("y", 2.0)
        assert v.keys() == {"x", "y"}

    def test_l2_norm(self) -> None:
        v = SparseVector()
        v.add("a", 3.0)
        v.add("b", 4.0)
        assert v.l2_norm() == pytest.approx(5.0)

    def test_normalize(self) -> None:
        v = SparseVector()
        v.add("a", 3.0)
        v.add("b", 4.0)
        v.normalize()
        assert v.l2_norm() == pytest.approx(1.0)
        assert v.get("a") == pytest.approx(3.0 / 5.0)
        assert v.get("b") == pytest.approx(4.0 / 5.0)

    def test_normalize_zero_vector(self) -> None:
        v = SparseVector()
        v.normalize()  # should not raise
        assert v.l2_norm() == 0.0

    def test_dot_product(self) -> None:
        a = SparseVector()
        a.add("x", 1.0)
        a.add("y", 2.0)
        b = SparseVector()
        b.add("x", 3.0)
        b.add("z", 5.0)
        # Only "x" overlaps: 1*3 = 3
        assert a.dot(b) == pytest.approx(3.0)

    def test_nonzero_count(self) -> None:
        v = SparseVector()
        v.add("a", 1.0)
        v.add("b", 0.0)
        v.add("c", -1.0)
        assert v.nonzero_count() == 2  # "a" and "c"

    def test_to_dict(self) -> None:
        v = SparseVector()
        v.add("a", 1.5)
        d = v.to_dict()
        assert d == {"a": 1.5}
        # Mutating the dict should not affect the vector
        d["a"] = 999.0
        assert v.get("a") == pytest.approx(1.5)


# ── CandidateVectorBuilder tests ────────────────────────────────────────


class TestCandidateVectorBuilder:
    """Vector builder for candidate artifacts."""

    builder = CandidateVectorBuilder()

    def test_build_single_artifact(self) -> None:
        art = ArtifactWeight(
            pmid="1",
            role_weight=1.0,
            venue_weight=1.0,
            recency_weight=1.0,
            evidence_type_weight=1.0,
            mesh_descriptors={"D001", "D002"},
        )
        vec = self.builder.build([art])
        assert vec.l2_norm() == pytest.approx(1.0)
        # Both terms should have equal weight
        assert vec.get("D001") == pytest.approx(vec.get("D002"))

    def test_build_multiple_artifacts_accumulates(self) -> None:
        arts = [
            ArtifactWeight(
                pmid="1",
                role_weight=1.0,
                venue_weight=1.0,
                recency_weight=1.0,
                evidence_type_weight=1.0,
                mesh_descriptors={"D001"},
            ),
            ArtifactWeight(
                pmid="2",
                role_weight=0.5,
                venue_weight=1.0,
                recency_weight=1.0,
                evidence_type_weight=1.0,
                mesh_descriptors={"D001"},
            ),
        ]
        vec = self.builder.build(arts)
        # D001 gets 1.0 + 0.5 = 1.5 pre-normalization
        assert vec.l2_norm() == pytest.approx(1.0)

    def test_build_empty_returns_zero_vector(self) -> None:
        vec = self.builder.build([])
        assert vec.nonzero_count() == 0


# ── TopicalFit tests ────────────────────────────────────────────────────


class TestTopicalFit:
    """T(c,q) cosine similarity."""

    tf = TopicalFit()
    qb = QueryVectorBuilder()
    cb = CandidateVectorBuilder()

    def test_identical_vectors(self) -> None:
        """Identical candidate and query should produce ~1.0."""
        art = ArtifactWeight(
            pmid="1",
            role_weight=1.0,
            venue_weight=1.0,
            recency_weight=1.0,
            evidence_type_weight=1.0,
            mesh_descriptors={"D001", "D002"},
        )
        cv = self.cb.build([art])
        qv = self.qb.build(["D001", "D002"])
        score = self.tf.compute(cv, qv)
        assert score == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self) -> None:
        """Completely non-overlapping MeSH sets should produce 0.0."""
        art = ArtifactWeight(
            pmid="1",
            role_weight=1.0,
            venue_weight=1.0,
            recency_weight=1.0,
            evidence_type_weight=1.0,
            mesh_descriptors={"D001"},
        )
        cv = self.cb.build([art])
        qv = self.qb.build(["D999"])
        score = self.tf.compute(cv, qv)
        assert score == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        """Partial MeSH overlap should produce 0 < score < 1."""
        art = ArtifactWeight(
            pmid="1",
            role_weight=1.0,
            venue_weight=1.0,
            recency_weight=1.0,
            evidence_type_weight=1.0,
            mesh_descriptors={"D001", "D002", "D003"},
        )
        cv = self.cb.build([art])
        qv = self.qb.build(["D001", "D004", "D005"])
        score = self.tf.compute(cv, qv)
        assert 0.0 < score < 1.0
