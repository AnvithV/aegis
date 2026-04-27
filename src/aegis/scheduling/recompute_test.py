"""Tests for nightly score recomputation."""

from __future__ import annotations

from aegis.scheduling.recompute import ScoreRecomputer
from aegis.scoring.candidate_vector import ArtifactWeight
from aegis.scoring.quality_prior import QualityPrior, WeightVector

_WEIGHTS = WeightVector(
    version=1,
    specialty="test",
    weights={"f1_rcr": 0.5, "f2_funding": 0.5},
    exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
    exponent_bounds={},
)


def _make_artifacts(n: int = 3) -> list[ArtifactWeight]:
    return [
        ArtifactWeight(
            pmid=f"PM{i:04d}",
            role_weight=0.8,
            venue_weight=0.9,
            recency_weight=0.7,
            evidence_type_weight=0.6,
            mesh_descriptors={f"D{i:06d}", f"D{i + 100:06d}"},
        )
        for i in range(n)
    ]


def _make_components() -> dict[str, float]:
    return {"f1_rcr": 0.8, "f2_funding": 0.6}


def test_artifact_set_hash_deterministic() -> None:
    """Same artifact IDs in any order produce the same hash."""
    recomp = ScoreRecomputer()

    hash_a = recomp.compute_artifact_set_hash(["PM0002", "PM0001", "PM0000"])
    hash_b = recomp.compute_artifact_set_hash(["PM0000", "PM0001", "PM0002"])
    hash_c = recomp.compute_artifact_set_hash(["PM0001", "PM0000", "PM0002"])

    assert hash_a == hash_b == hash_c
    assert len(hash_a) == 64  # SHA-256 hex digest


def test_is_up_to_date_miss() -> None:
    """A candidate with no record is not up-to-date."""
    recomp = ScoreRecomputer()

    assert not recomp.is_up_to_date("C001", "abc123", 1)


def test_is_up_to_date_hit() -> None:
    """A candidate with a matching record is up-to-date."""
    recomp = ScoreRecomputer()
    qp = QualityPrior(_WEIGHTS)
    arts = _make_artifacts()
    comp = _make_components()

    record = recomp.recompute_candidate("C001", arts, qp, comp)
    recomp.record_recompute(record)

    assert recomp.is_up_to_date(
        "C001", record.artifact_set_hash, record.weight_version
    )


def test_recompute_candidate() -> None:
    """Recompute produces a valid record with correct dimensions."""
    recomp = ScoreRecomputer()
    qp = QualityPrior(_WEIGHTS)
    arts = _make_artifacts(3)
    comp = _make_components()

    record = recomp.recompute_candidate("C001", arts, qp, comp)

    assert record.candidate_uuid == "C001"
    assert record.quality_score_raw > 0.0
    assert record.vector_nonzero_dims > 0
    assert record.weight_version == 1
    assert len(record.artifact_set_hash) == 64


def test_recompute_batch_idempotent() -> None:
    """Running the same batch twice skips all on the second run."""
    recomp = ScoreRecomputer()
    qp = QualityPrior(_WEIGHTS)
    arts = _make_artifacts()
    comp = _make_components()

    candidates = [("C001", arts, comp), ("C002", arts, comp)]

    result1 = recomp.recompute_batch("cohort-1", candidates, qp)
    assert result1.recomputed_count == 2
    assert result1.skipped_count == 0

    result2 = recomp.recompute_batch("cohort-1", candidates, qp)
    assert result2.recomputed_count == 0
    assert result2.skipped_count == 2
    assert result2.idempotent is True


def test_recompute_batch_counts() -> None:
    """Batch result counts are accurate."""
    recomp = ScoreRecomputer()
    qp = QualityPrior(_WEIGHTS)
    arts = _make_artifacts()
    comp = _make_components()

    candidates = [
        ("C001", arts, comp),
        ("C002", arts, comp),
        ("C003", arts, comp),
    ]

    result = recomp.recompute_batch("cohort-1", candidates, qp)

    assert result.total_candidates == 3
    assert result.recomputed_count == 3
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert result.weight_version == 1
    assert result.elapsed_seconds >= 0.0

    records = recomp.get_latest_records(weight_version=1)
    assert len(records) == 3
