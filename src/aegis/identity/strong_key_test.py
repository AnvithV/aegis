"""Tests for strong-key identity resolution."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from aegis.identity.strong_key import (
    CandidateRegistry,
    StrongKeyResolver,
)
from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import ArtifactRefBundle, Candidate


def _make_candidate(
    candidate_uuid: str,
    *,
    strong_keys: dict[str, str] | None = None,
    name: str = "Jane Smith",
) -> Candidate:
    return Candidate(
        uuid=candidate_uuid,
        strong_keys=strong_keys or {},
        name_variants=[name],
        affiliations=[],
        artifact_refs=ArtifactRefBundle(
            pmids=[], nct_ids=[], grant_ids=[]
        ),
        linkage_confidence=1.0,
        evidence_trail=[],
        last_updated_per_source={},
        mesh_descriptors=[],
    )


@pytest.fixture()
def store(tmp_path: Path) -> Generator[CandidateStore]:
    db_path = str(tmp_path / "test.duckdb")
    s = CandidateStore(db_path=db_path)
    yield s
    s.close()


def test_resolve_by_orcid(store: CandidateStore) -> None:
    """Register a candidate with ORCID, resolve an artifact with matching ORCID."""
    cand = _make_candidate(
        "uuid-001", strong_keys={"orcid": "0000-0001-2345-6789"}
    )
    store.upsert(cand)

    resolver = StrongKeyResolver(store)
    ref = resolver.resolve({
        "orcid": "0000-0001-2345-6789",
        "era_id": None,
        "name": "Jane Smith",
    })

    assert ref is not None
    assert ref.candidate_uuid == "uuid-001"
    assert ref.matched_via == "orcid"
    assert ref.confidence == 1.0


def test_resolve_by_era_commons(store: CandidateStore) -> None:
    """Register a candidate with eRA Commons, resolve via eRA."""
    cand = _make_candidate(
        "uuid-002", strong_keys={"era_commons": "JSMITH01"}
    )
    store.upsert(cand)

    resolver = StrongKeyResolver(store)
    ref = resolver.resolve({
        "orcid": None,
        "era_id": "JSMITH01",
        "name": "Jane Smith",
    })

    assert ref is not None
    assert ref.candidate_uuid == "uuid-002"
    assert ref.matched_via == "era_commons"
    assert ref.confidence == 1.0


def test_resolve_no_match(store: CandidateStore) -> None:
    """Artifact with unknown keys returns None."""
    resolver = StrongKeyResolver(store)
    ref = resolver.resolve({
        "orcid": "0000-0000-0000-0000",
        "era_id": None,
        "name": "Nobody",
    })
    assert ref is None


def test_resolve_orcid_priority(store: CandidateStore) -> None:
    """When artifact has both ORCID and eRA, ORCID is tried first."""
    cand_orcid = _make_candidate(
        "uuid-orcid", strong_keys={"orcid": "0000-0001-1111-1111"}
    )
    cand_era = _make_candidate(
        "uuid-era", strong_keys={"era_commons": "ERA001"}
    )
    store.upsert(cand_orcid)
    store.upsert(cand_era)

    resolver = StrongKeyResolver(store)
    ref = resolver.resolve({
        "orcid": "0000-0001-1111-1111",
        "era_id": "ERA001",
        "name": "Jane Smith",
    })

    assert ref is not None
    assert ref.candidate_uuid == "uuid-orcid"
    assert ref.matched_via == "orcid"


def test_register_idempotent(store: CandidateStore) -> None:
    """Register same key-value twice, no error, count is 1."""
    cand = _make_candidate(
        "uuid-003", strong_keys={"orcid": "0000-0001-0000-0001"}
    )
    store.upsert(cand)

    resolver = StrongKeyResolver(store)
    resolver.register("orcid", "0000-0001-0000-0001", "uuid-003")
    # Should not raise, key already exists for same candidate
    resolver.register("orcid", "0000-0001-0000-0001", "uuid-003")

    count = resolver.bulk_register([
        ("orcid", "0000-0001-0000-0001", "uuid-003"),
    ])
    # Already registered, so count should be 0
    assert count == 0


def test_get_or_create_existing(store: CandidateStore) -> None:
    """get_or_create with existing ORCID returns same UUID."""
    cand = _make_candidate(
        "uuid-004", strong_keys={"orcid": "0000-0001-9999-0001"}
    )
    store.upsert(cand)

    registry = CandidateRegistry(store)
    result_uuid = registry.get_or_create(
        {"orcid": "0000-0001-9999-0001"}, "Jane Smith"
    )
    assert result_uuid == "uuid-004"


def test_get_or_create_new(store: CandidateStore) -> None:
    """Call get_or_create with unknown keys, assert new UUID created."""
    registry = CandidateRegistry(store)
    result_uuid = registry.get_or_create(
        {"orcid": "0000-0002-0000-0001"}, "New Person"
    )
    assert result_uuid is not None
    assert len(result_uuid) > 0

    # Verify the candidate was persisted
    cand = store.get_by_uuid(result_uuid)
    assert cand is not None
    assert cand.strong_keys["orcid"] == "0000-0002-0000-0001"
    assert "New Person" in cand.name_variants


def test_cross_source_linking(store: CandidateStore) -> None:
    """ORCID from PubMed + eRA from RePORTER resolve to same candidate."""
    registry = CandidateRegistry(store)

    # First encounter: PubMed provides ORCID
    uuid1 = registry.get_or_create(
        {"orcid": "0000-0001-5555-5555"}, "Dr. Cross Source"
    )

    # Second encounter: RePORTER provides eRA Commons for same person
    # We know it's the same person because they share the ORCID
    uuid2 = registry.get_or_create(
        {"orcid": "0000-0001-5555-5555", "era_commons": "CROSSSRC"},
        "Dr. Cross Source",
    )

    assert uuid1 == uuid2

    # Now resolve by eRA Commons alone
    resolver = StrongKeyResolver(store)
    ref = resolver.resolve({
        "orcid": None,
        "era_id": "CROSSSRC",
        "name": "Dr. Cross Source",
    })
    assert ref is not None
    assert ref.candidate_uuid == uuid1
    assert ref.matched_via == "era_commons"
