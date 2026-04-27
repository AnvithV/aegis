"""Tests for probabilistic record linkage."""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from aegis.identity.probabilistic import ProbabilisticLinker
from aegis.identity.probabilistic_train import ThresholdTrainer
from aegis.identity.ror import RorResolver
from aegis.identity.strong_key import CandidateRegistry
from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import (
    AffiliationSpan,
    ArtifactRefBundle,
    Candidate,
    MeshDescriptor,
)


def _make_candidate(
    *,
    candidate_uuid: str | None = None,
    name: str = "Jane Smith",
    name_variants: list[str] | None = None,
    orcid: str = "0000-0001-2345-6789",
    ror_id: str | None = "https://ror.org/002pd6e78",
    canonical_affiliation: str = "Massachusetts General Hospital",
    country: str = "US",
    mesh_terms: list[str] | None = None,
) -> Candidate:
    """Create a test candidate."""
    mesh_descriptors = [
        MeshDescriptor(
            descriptor=term,
            qualifier=None,
            major_topic=True,
        )
        for term in (mesh_terms or [])
    ]
    return Candidate(
        uuid=candidate_uuid or str(_uuid.uuid4()),
        strong_keys={"orcid": orcid},
        name_variants=name_variants or [name],
        affiliations=[
            AffiliationSpan(
                ror_id=ror_id,
                canonical_name=canonical_affiliation,
                raw_string=canonical_affiliation,
                country=country,
                confidence=0.95,
                start_date=date(2018, 1, 1),
                end_date=date(2024, 12, 31),
            ),
        ],
        artifact_refs=ArtifactRefBundle(
            pmids=[], nct_ids=[], grant_ids=[]
        ),
        linkage_confidence=1.0,
        evidence_trail=[],
        last_updated_per_source={
            "pubmed": datetime(2024, 1, 1, tzinfo=UTC),
        },
        mesh_descriptors=mesh_descriptors,
    )


@pytest.fixture()
def store(tmp_path: Path) -> Generator[CandidateStore]:
    """Create a CandidateStore backed by a temporary DuckDB file."""
    db_path = str(tmp_path / "test.duckdb")
    s = CandidateStore(db_path=db_path)
    yield s
    s.close()


@pytest.fixture()
def ror_resolver() -> RorResolver:
    """Create a ROR resolver."""
    return RorResolver()


@pytest.fixture()
def registry(store: CandidateStore) -> CandidateRegistry:
    """Create a candidate registry."""
    return CandidateRegistry(store)


@pytest.fixture()
def linker(
    store: CandidateStore, ror_resolver: RorResolver
) -> ProbabilisticLinker:
    """Create a probabilistic linker."""
    return ProbabilisticLinker(store, ror_resolver)


def test_exact_name_match_auto_links(
    store: CandidateStore,
    linker: ProbabilisticLinker,
    registry: CandidateRegistry,
) -> None:
    """Two records with identical names and same affiliation -> auto-link."""
    candidate = _make_candidate(
        name="Jane Smith",
        name_variants=["Jane Smith", "J Smith"],
        mesh_terms=["Oncology", "Immunotherapy"],
    )
    store.upsert(candidate)

    artifact = {
        "name": "Jane Smith",
        "name_variants": ["Jane Smith", "J Smith"],
        "affiliation": "Massachusetts General Hospital",
        "coauthors": [],
        "mesh_terms": ["Oncology", "Immunotherapy"],
        "year": 2022,
    }

    result = linker.link(artifact, registry)
    assert result.confidence >= 0.95
    assert result.action == "auto-link"
    assert result.candidate_uuid == candidate.uuid


def test_different_names_reject(
    store: CandidateStore,
    linker: ProbabilisticLinker,
    registry: CandidateRegistry,
) -> None:
    """Completely different names -> reject."""
    candidate = _make_candidate(name="Jane Smith")
    store.upsert(candidate)

    artifact = {
        "name": "Robert Williams",
        "name_variants": ["Robert Williams", "R Williams"],
        "affiliation": "University of Oxford",
        "coauthors": [],
        "mesh_terms": [],
        "year": 2010,
    }

    result = linker.link(artifact, registry)
    assert result.confidence <= 0.5
    assert result.action == "reject"


def test_borderline_goes_to_review(
    store: CandidateStore,
    linker: ProbabilisticLinker,
    registry: CandidateRegistry,
) -> None:
    """Similar but not identical name + different affiliation -> review."""
    candidate = _make_candidate(
        name="Jane A Smith",
        name_variants=["Jane A Smith", "J A Smith"],
    )
    store.upsert(candidate)

    artifact = {
        "name": "Jane Smith",
        "name_variants": ["Jane Smith"],
        "affiliation": "Stanford University",
        "coauthors": [],
        "mesh_terms": [],
        "year": 2022,
    }

    result = linker.link(artifact, registry)
    assert result.action == "review"
    assert 0.5 <= result.confidence < 0.95


def test_feature_scores_populated(
    store: CandidateStore,
    linker: ProbabilisticLinker,
    registry: CandidateRegistry,
) -> None:
    """Assert feature_scores dict has all 5 features."""
    candidate = _make_candidate(name="Test Person")
    store.upsert(candidate)

    artifact: dict[str, Any] = {
        "name": "Test Person",
        "name_variants": [],
        "affiliation": "",
        "coauthors": [],
        "mesh_terms": [],
        "year": None,
    }

    result = linker.link(artifact, registry)
    expected_keys = {
        "name_similarity",
        "affiliation_similarity",
        "coauthor_overlap",
        "mesh_overlap",
        "time_continuity",
    }
    assert set(result.feature_scores.keys()) == expected_keys


def test_coauthor_overlap_boosts_confidence(
    store: CandidateStore,
    ror_resolver: RorResolver,
    registry: CandidateRegistry,
) -> None:
    """Same name + shared co-authors -> higher coauthor_overlap feature score."""
    candidate = _make_candidate(
        name="Jane Smith",
        name_variants=["Jane Smith", "Alice Wong", "Bob Lee"],
    )
    store.upsert(candidate)

    linker = ProbabilisticLinker(store, ror_resolver)

    artifact_without = {
        "name": "Jane Smith",
        "name_variants": ["Jane Smith"],
        "affiliation": "",
        "coauthors": [],
        "mesh_terms": [],
        "year": None,
    }
    result_without = linker.link(artifact_without, registry)

    artifact_with = {
        "name": "Jane Smith",
        "name_variants": ["Jane Smith"],
        "affiliation": "",
        "coauthors": ["Alice Wong", "Bob Lee"],
        "mesh_terms": [],
        "year": None,
    }
    result_with = linker.link(artifact_with, registry)

    score_with = result_with.feature_scores["coauthor_overlap"]
    score_without = result_without.feature_scores["coauthor_overlap"]
    assert score_with > score_without


def test_mesh_overlap_boosts_confidence(
    store: CandidateStore,
    ror_resolver: RorResolver,
    registry: CandidateRegistry,
) -> None:
    """Same name + shared MeSH terms -> higher confidence."""
    candidate = _make_candidate(
        name="Jane Smith",
        mesh_terms=["Oncology", "Immunotherapy", "Carcinoma"],
    )
    store.upsert(candidate)

    base_artifact = {
        "name": "Jane Smith",
        "name_variants": ["Jane Smith"],
        "affiliation": "",
        "coauthors": [],
        "mesh_terms": [],
        "year": None,
    }

    linker = ProbabilisticLinker(store, ror_resolver)
    result_without = linker.link(base_artifact, registry)

    artifact_with_mesh = dict(base_artifact)
    artifact_with_mesh["mesh_terms"] = ["Oncology", "Immunotherapy"]

    result_with = linker.link(artifact_with_mesh, registry)

    assert result_with.confidence > result_without.confidence


def test_link_batch(
    store: CandidateStore,
    linker: ProbabilisticLinker,
    registry: CandidateRegistry,
) -> None:
    """Batch of 5 artifacts, assert results match individual link() calls."""
    candidate = _make_candidate(name="Jane Smith")
    store.upsert(candidate)

    artifacts = [
        {
            "name": f"Person {i}",
            "name_variants": [f"Person {i}"],
            "affiliation": "",
            "coauthors": [],
            "mesh_terms": [],
            "year": 2020 + i,
        }
        for i in range(5)
    ]

    batch_results = linker.link_batch(artifacts, registry)
    individual_results = [
        linker.link(a, registry) for a in artifacts
    ]

    assert len(batch_results) == 5
    for batch_r, indiv_r in zip(batch_results, individual_results):
        assert batch_r.confidence == indiv_r.confidence
        assert batch_r.action == indiv_r.action


def test_threshold_training(
    store: CandidateStore,
) -> None:
    """Generate synthetic strong-key pairs, train thresholds, assert valid."""
    # Create candidates with known names
    for i in range(20):
        candidate = _make_candidate(
            name=f"Researcher {i}",
            name_variants=[f"Researcher {i}", f"R {i}"],
            orcid=f"0000-0001-0000-{i:04d}",
        )
        store.upsert(candidate)

    candidates = store.list_by_cohort()

    # Create pairs with a mix of exact and approximate name matches
    # to ensure thresholds are distinct (not all 1.0)
    pairs: list[tuple[str, str]] = []
    for i, c in enumerate(candidates):
        if i % 3 == 0:
            # Exact match
            pairs.append((c.name_variants[0], c.uuid))
        elif i % 3 == 1:
            # Use short variant (lower similarity)
            pairs.append((c.name_variants[1], c.uuid))
        else:
            # Slight misspelling
            pairs.append((c.name_variants[0] + " Jr", c.uuid))

    trainer = ThresholdTrainer(store)
    thresholds = trainer.train(pairs)

    assert "auto_link" in thresholds
    assert "review" in thresholds
    assert thresholds["auto_link"] > thresholds["review"]
    assert 0.0 <= thresholds["review"] <= 1.0
    assert 0.0 <= thresholds["auto_link"] <= 1.0


def test_empty_registry(
    store: CandidateStore,
    linker: ProbabilisticLinker,
    registry: CandidateRegistry,
) -> None:
    """No candidates in registry -> reject."""
    artifact: dict[str, Any] = {
        "name": "Nobody",
        "name_variants": [],
        "affiliation": "",
        "coauthors": [],
        "mesh_terms": [],
        "year": None,
    }

    result = linker.link(artifact, registry)
    assert result.action == "reject"
    assert result.candidate_uuid is None
    assert result.confidence == 0.0
