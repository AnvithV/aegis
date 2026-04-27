"""Performance benchmark: end-to-end query latency on synthetic cohort."""

from __future__ import annotations

import random
import time
from datetime import date

from aegis.scoring.candidate_vector import (
    ArtifactWeight,
    CandidateVectorBuilder,
    QueryVectorBuilder,
    SparseVector,
)
from aegis.scoring.rank import CandidateScoreInput, Ranker
from aegis.scoring.recency import Recency, RecencyArtifact
from aegis.scoring.topical_fit import TopicalFit

# ── synthetic universe ──────────────────────────────────────────────────
_NUM_CANDIDATES = 100
_NUM_TRIALS = 100
_MESH_UNIVERSE_SIZE = 500
_TERMS_PER_CANDIDATE = 30
_TERMS_PER_QUERY = 10
_ARTIFACTS_PER_CANDIDATE = 8
_TOP_K = 50
_P95_LIMIT_MS = 500.0

_REFERENCE_DATE = date(2026, 1, 15)


def _build_mesh_universe(rng: random.Random) -> list[str]:
    """Generate a fixed MeSH term universe."""
    return [f"D{i:06d}" for i in range(_MESH_UNIVERSE_SIZE)]


def _build_synthetic_cohort(
    rng: random.Random,
    mesh_universe: list[str],
) -> tuple[
    list[SparseVector],
    list[list[RecencyArtifact]],
    list[CandidateScoreInput],
]:
    """Build synthetic candidate data for benchmarking."""
    cvb = CandidateVectorBuilder()
    candidate_vectors: list[SparseVector] = []
    candidate_recency_artifacts: list[list[RecencyArtifact]] = []
    candidate_inputs: list[CandidateScoreInput] = []

    for i in range(_NUM_CANDIDATES):
        # Pick random MeSH terms for this candidate
        terms = set(rng.sample(mesh_universe, _TERMS_PER_CANDIDATE))

        # Build artifact weights for vector construction
        artifacts: list[ArtifactWeight] = []
        recency_artifacts: list[RecencyArtifact] = []

        for j in range(_ARTIFACTS_PER_CANDIDATE):
            art_terms = set(rng.sample(list(terms), min(5, len(terms))))
            artifacts.append(
                ArtifactWeight(
                    pmid=f"PM{i:04d}_{j}",
                    role_weight=rng.uniform(0.3, 1.0),
                    venue_weight=rng.uniform(0.5, 1.0),
                    recency_weight=rng.uniform(0.4, 1.0),
                    evidence_type_weight=rng.uniform(0.5, 1.0),
                    mesh_descriptors=art_terms,
                )
            )
            recency_artifacts.append(
                RecencyArtifact(
                    publication_date=date(
                        2020 + rng.randint(0, 5),
                        rng.randint(1, 12),
                        rng.randint(1, 28),
                    ),
                    role_weight=rng.uniform(0.3, 1.0),
                    type_weight=rng.uniform(0.5, 1.0),
                    is_preprint=rng.random() < 0.15,
                    mesh_descriptors=art_terms,
                )
            )

        vec = cvb.build(artifacts)
        candidate_vectors.append(vec)
        candidate_recency_artifacts.append(recency_artifacts)

        candidate_inputs.append(
            CandidateScoreInput(
                candidate_uuid=f"C{i:04d}",
                candidate_name=f"Candidate {i}",
                linkage_confidence=rng.uniform(0.7, 1.0),
                integrity_score=rng.uniform(0.5, 1.0),
                quality_percentile=rng.uniform(0.1, 0.99),
                topical_fit=0.0,  # filled per-query
                recency=0.0,  # filled per-query
            )
        )

    return candidate_vectors, candidate_recency_artifacts, candidate_inputs


def test_query_latency_p95() -> None:
    """100 queries on 100-candidate cohort must complete under 500ms p95."""
    rng = random.Random(42)
    mesh_universe = _build_mesh_universe(rng)

    candidate_vectors, candidate_recency_arts, base_inputs = (
        _build_synthetic_cohort(rng, mesh_universe)
    )

    qvb = QueryVectorBuilder()
    tf = TopicalFit()
    rec = Recency()
    ranker = Ranker()

    latencies_ms: list[float] = []

    for trial in range(_NUM_TRIALS):
        # Build a random query
        query_terms = rng.sample(mesh_universe, _TERMS_PER_QUERY)
        query_vec = qvb.build(query_terms)
        query_mesh_set = set(query_terms)

        t0 = time.perf_counter()

        # Compute T(c,q) and R(c,q) for all candidates
        scored_inputs: list[CandidateScoreInput] = []
        for idx in range(_NUM_CANDIDATES):
            t_score = tf.compute(candidate_vectors[idx], query_vec)
            r_score = rec.compute(
                candidate_recency_arts[idx],
                query_mesh_set,
                _REFERENCE_DATE,
            )
            inp = base_inputs[idx]
            scored_inputs.append(
                CandidateScoreInput(
                    candidate_uuid=inp.candidate_uuid,
                    candidate_name=inp.candidate_name,
                    linkage_confidence=inp.linkage_confidence,
                    integrity_score=inp.integrity_score,
                    quality_percentile=inp.quality_percentile,
                    topical_fit=t_score,
                    recency=r_score,
                )
            )

        # Rank top-k
        result = ranker.rank(
            query_mesh_terms=query_terms,
            candidates=scored_inputs,
            k=_TOP_K,
        )

        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    p95_idx = int(len(latencies_ms) * 0.95) - 1
    p95_ms = latencies_ms[p95_idx]
    median_ms = latencies_ms[len(latencies_ms) // 2]

    print(f"\nLatency benchmark ({_NUM_TRIALS} trials, {_NUM_CANDIDATES} candidates):")
    print(f"  Median: {median_ms:.1f} ms")
    print(f"  p95:    {p95_ms:.1f} ms")
    print(f"  Max:    {latencies_ms[-1]:.1f} ms")

    assert p95_ms < _P95_LIMIT_MS, (
        f"p95 latency {p95_ms:.1f}ms exceeds budget {_P95_LIMIT_MS}ms"
    )
    # Verify results are well-formed
    assert result.result_count <= _TOP_K
    assert result.cohort_size == _NUM_CANDIDATES
