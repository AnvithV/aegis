"""Tests for the Candidate schema and CandidateStore."""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

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
    orcid: str = "0000-0001-2345-6789",
) -> Candidate:
    """Create a fully-populated Candidate for testing."""
    return Candidate(
        uuid=candidate_uuid or str(_uuid.uuid4()),
        strong_keys={"orcid": orcid},
        name_variants=["Jane Smith", "J Smith", "J. A. Smith"],
        affiliations=[
            AffiliationSpan(
                ror_id="https://ror.org/03yrm5c26",
                canonical_name="Harvard University",
                raw_string="Harvard Univ, Boston, MA",
                country="US",
                confidence=0.95,
                start_date=date(2015, 9, 1),
                end_date=date(2020, 6, 30),
            ),
            AffiliationSpan(
                ror_id="https://ror.org/05a0ya142",
                canonical_name="MIT",
                raw_string="Massachusetts Institute of Technology",
                country="US",
                confidence=0.98,
                start_date=date(2020, 7, 1),
                end_date=None,
            ),
        ],
        artifact_refs=ArtifactRefBundle(
            pmids=["12345678", "87654321"],
            nct_ids=["NCT00000001"],
            grant_ids=["R01CA123456"],
        ),
        linkage_confidence=0.92,
        evidence_trail=["pubmed_match:12345678", "orcid_verified"],
        last_updated_per_source={
            "pubmed": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "orcid": datetime(2024, 2, 1, 8, 0, 0, tzinfo=UTC),
        },
        mesh_descriptors=[
            MeshDescriptor(
                descriptor="Carcinoma, Non-Small-Cell Lung",
                qualifier="drug therapy",
                major_topic=True,
            ),
            MeshDescriptor(
                descriptor="Immunotherapy",
                qualifier=None,
                major_topic=False,
            ),
        ],
    )


@pytest.fixture()
def store(tmp_path: Path) -> Generator[CandidateStore]:
    """Create a CandidateStore backed by a temporary DuckDB file."""
    db_path = str(tmp_path / "test.duckdb")
    s = CandidateStore(db_path=db_path)
    yield s
    s.close()


def test_candidate_round_trip(store: CandidateStore) -> None:
    """Upsert a fully-populated Candidate, retrieve by UUID, and verify all fields."""
    candidate = _make_candidate()
    store.upsert(candidate)
    retrieved = store.get_by_uuid(candidate.uuid)

    assert retrieved is not None
    assert retrieved.uuid == candidate.uuid
    assert retrieved.strong_keys == candidate.strong_keys
    assert retrieved.name_variants == candidate.name_variants
    assert retrieved.affiliations == candidate.affiliations
    assert retrieved.artifact_refs == candidate.artifact_refs
    assert retrieved.linkage_confidence == candidate.linkage_confidence
    assert retrieved.evidence_trail == candidate.evidence_trail
    assert retrieved.last_updated_per_source == candidate.last_updated_per_source
    assert retrieved.mesh_descriptors == candidate.mesh_descriptors


def test_strong_key_lookup(store: CandidateStore) -> None:
    """Upsert a candidate with ORCID, retrieve via get_by_strong_key."""
    orcid = "0000-0002-9999-0001"
    candidate = _make_candidate(orcid=orcid)
    store.upsert(candidate)

    retrieved = store.get_by_strong_key("orcid", orcid)
    assert retrieved is not None
    assert retrieved.uuid == candidate.uuid
    assert retrieved.strong_keys["orcid"] == orcid


def test_upsert_idempotent(store: CandidateStore) -> None:
    """Upserting the same candidate twice should not create duplicates."""
    candidate = _make_candidate()
    store.upsert(candidate)
    store.upsert(candidate)
    assert store.count() == 1


def test_list_by_cohort(store: CandidateStore) -> None:
    """Insert 3 candidates, list all, assert count is 3."""
    for _ in range(3):
        store.upsert(_make_candidate())
    candidates = store.list_by_cohort()
    assert len(candidates) == 3


def test_bulk_round_trip(store: CandidateStore) -> None:
    """Create 100 candidates, upsert all, retrieve all, assert no field truncation."""
    originals: list[Candidate] = []
    for i in range(100):
        c = _make_candidate(orcid=f"0000-0001-0000-{i:04d}")
        originals.append(c)
        store.upsert(c)

    assert store.count() == 100

    for orig in originals:
        retrieved = store.get_by_uuid(orig.uuid)
        assert retrieved is not None
        assert retrieved.name_variants == orig.name_variants
        assert len(retrieved.affiliations) == len(orig.affiliations)
        assert retrieved.artifact_refs == orig.artifact_refs
        assert retrieved.mesh_descriptors == orig.mesh_descriptors
