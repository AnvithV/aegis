"""Candidate topic-vector construction for topical-fit scoring."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class ArtifactWeight:
    """Weights and MeSH descriptors for a single artifact."""

    pmid: str
    role_weight: float
    venue_weight: float
    recency_weight: float
    evidence_type_weight: float
    mesh_descriptors: set[str] = field(default_factory=set)


class SparseVector:
    """Dict-based sparse vector with L2 operations."""

    def __init__(self) -> None:
        self._data: dict[str, float] = {}

    def add(self, key: str, value: float) -> None:
        """Accumulate *value* into dimension *key*."""
        self._data[key] = self._data.get(key, 0.0) + value

    def get(self, key: str) -> float:
        """Return value for *key*, defaulting to 0.0."""
        return self._data.get(key, 0.0)

    def keys(self) -> set[str]:
        """Return the set of non-zero dimension keys."""
        return set(self._data.keys())

    def l2_norm(self) -> float:
        """Return the L2 (Euclidean) norm of the vector."""
        return math.sqrt(sum(v * v for v in self._data.values()))

    def normalize(self) -> None:
        """L2-normalize the vector in place."""
        norm = self.l2_norm()
        if norm > 0.0:
            for k in self._data:
                self._data[k] /= norm

    def dot(self, other: SparseVector) -> float:
        """Compute the dot product with *other*."""
        # Iterate over the smaller set for efficiency
        if len(self._data) > len(other._data):
            return other.dot(self)
        total = 0.0
        for k, v in self._data.items():
            ov = other._data.get(k)
            if ov is not None:
                total += v * ov
        return total

    def nonzero_count(self) -> int:
        """Return the number of non-zero dimensions."""
        return sum(1 for v in self._data.values() if v != 0.0)

    def to_dict(self) -> dict[str, float]:
        """Return a copy of the underlying data."""
        return dict(self._data)


class CandidateVectorBuilder:
    """Build a candidate topic vector from weighted artifacts."""

    def build(self, artifacts: list[ArtifactWeight]) -> SparseVector:
        """Aggregate MeSH weights and return an L2-normalized vector.

        For each artifact and each MeSH term, the contribution is
        ``w_role * w_venue * w_recency * w_evidence_type``.
        """
        vec = SparseVector()
        for art in artifacts:
            w = (
                art.role_weight
                * art.venue_weight
                * art.recency_weight
                * art.evidence_type_weight
            )
            for term in art.mesh_descriptors:
                vec.add(term, w)
        vec.normalize()
        return vec


class QueryVectorBuilder:
    """Build a query topic vector from MeSH terms."""

    def build(
        self,
        mesh_terms: list[str],
        weights: list[float] | None = None,
    ) -> SparseVector:
        """Return an L2-normalized query vector.

        If *weights* is ``None``, all terms are weighted equally (1.0).
        """
        vec = SparseVector()
        if weights is None:
            weights = [1.0] * len(mesh_terms)
        for term, w in zip(mesh_terms, weights):
            vec.add(term, w)
        vec.normalize()
        return vec
