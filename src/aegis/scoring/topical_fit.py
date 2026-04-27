"""T(c,q) Topical-fit cosine similarity between candidate and query vectors."""

from __future__ import annotations

from aegis.scoring.candidate_vector import SparseVector


class TopicalFit:
    """Compute topical fit T(c,q) as cosine similarity of pre-normalized vectors."""

    def compute(
        self,
        candidate_vector: SparseVector,
        query_vector: SparseVector,
    ) -> float:
        """Return cosine similarity in [0, 1].

        Both vectors are expected to be L2-normalized, so cosine
        similarity reduces to the dot product.  The result is clamped
        to [0, 1] to guard against floating-point drift.
        """
        raw = candidate_vector.dot(query_vector)
        return max(0.0, min(1.0, raw))
