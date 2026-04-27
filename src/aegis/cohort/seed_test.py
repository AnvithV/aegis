"""Tests for the NSCLC translational seed-cohort builder."""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from aegis.cohort.nsclc_translational import (
    CohortConfig,
    SeedSource,
    build_nsclc_translational_cohort,
)
from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import (
    AffiliationSpan,
    ArtifactRefBundle,
    Candidate,
    MeshDescriptor,
)

_NSCLC_MESH = MeshDescriptor(
    descriptor="Carcinoma, Non-Small-Cell Lung",
    qualifier=None,
    major_topic=True,
)

_OTHER_MESH = MeshDescriptor(
    descriptor="Diabetes Mellitus, Type 2",
    qualifier=None,
    major_topic=True,
)

_ACADEMIC_AFF = AffiliationSpan(
    ror_id="https://ror.org/03vek6s52",
    canonical_name="Harvard University",
    raw_string="Harvard Univ, Boston, MA",
    country="US",
    confidence=0.95,
    start_date=date(2020, 1, 1),
    end_date=None,
)

_INDUSTRY_AFF = AffiliationSpan(
    ror_id=None,
    canonical_name="Acme Therapeutics Inc",
    raw_string="Acme Therapeutics Inc, San Diego, CA",
    country="US",
    confidence=0.80,
    start_date=date(2020, 1, 1),
    end_date=None,
)


def _make_candidate(
    *,
    pmids: list[str] | None = None,
    grant_ids: list[str] | None = None,
    nct_ids: list[str] | None = None,
    mesh: list[MeshDescriptor] | None = None,
    affiliations: list[AffiliationSpan] | None = None,
    candidate_uuid: str | None = None,
) -> Candidate:
    return Candidate(
        uuid=candidate_uuid or str(_uuid.uuid4()),
        strong_keys={},
        name_variants=["Test Author"],
        affiliations=affiliations or [_ACADEMIC_AFF],
        artifact_refs=ArtifactRefBundle(
            pmids=pmids or [],
            nct_ids=nct_ids or [],
            grant_ids=grant_ids or [],
        ),
        linkage_confidence=0.9,
        evidence_trail=[],
        last_updated_per_source={
            "pubmed": datetime(2024, 1, 1, tzinfo=UTC),
        },
        mesh_descriptors=mesh or [_NSCLC_MESH],
    )


@pytest.fixture()
def store(tmp_path: Path) -> Generator[CandidateStore]:
    db_path = str(tmp_path / "test.duckdb")
    s = CandidateStore(db_path=db_path)
    yield s
    s.close()


def test_seed_phase_pubmed(store: CandidateStore) -> None:
    """Mock store with 10 PubMed last-authors matching NSCLC MeSH."""
    for i in range(10):
        c = _make_candidate(pmids=[f"PMID{i:04d}"])
        store.upsert(c)

    cohort = build_nsclc_translational_cohort(store)
    assert cohort.seed_count == 10
    for uid in cohort.candidates:
        assert SeedSource.pubmed_last_author in cohort.provenance[uid]


def test_seed_phase_nih(store: CandidateStore) -> None:
    """Mock store with 5 NIH contact PIs on NSCLC grants."""
    for i in range(5):
        c = _make_candidate(grant_ids=[f"R01CA{i:06d}"])
        store.upsert(c)

    cohort = build_nsclc_translational_cohort(store)
    assert cohort.seed_count == 5
    for uid in cohort.candidates:
        assert SeedSource.nih_contact_pi in cohort.provenance[uid]


def test_expansion_two_hops(store: CandidateStore) -> None:
    """3 seed PIs, each with 5 co-authors who each have 3 co-authors.

    Seed PIs share PMIDs with hop-1 co-authors, and hop-1 co-authors
    share PMIDs with hop-2 co-authors.
    """
    seeds: list[Candidate] = []
    hop1: list[Candidate] = []
    hop2: list[Candidate] = []

    # 3 seeds — each has a unique PMID and NSCLC MeSH
    for i in range(3):
        shared_pmid = f"SEED_PMID_{i}"
        c = _make_candidate(pmids=[shared_pmid])
        seeds.append(c)
        store.upsert(c)

        # 5 hop-1 co-authors per seed (share the seed's PMID)
        for j in range(5):
            hop1_pmid = f"HOP1_PMID_{i}_{j}"
            co = _make_candidate(
                pmids=[shared_pmid, hop1_pmid],
                mesh=[_OTHER_MESH],  # not NSCLC → not a seed themselves
            )
            hop1.append(co)
            store.upsert(co)

            # 3 hop-2 co-authors per hop-1 (share hop-1's unique PMID)
            for k in range(3):
                co2 = _make_candidate(
                    pmids=[hop1_pmid],
                    mesh=[_OTHER_MESH],
                )
                hop2.append(co2)
                store.upsert(co2)

    cohort = build_nsclc_translational_cohort(store)
    assert cohort.seed_count == 3
    # Expect: 3 seeds + 15 hop-1 + 45 hop-2 = 63
    assert cohort.expanded_count == 3 + 15 + 45


def test_fanout_cap(store: CandidateStore) -> None:
    """Seed PI with 100 co-authors; only max_coauthor_fanout included."""
    shared_pmid = "POPULAR_PMID"
    seed = _make_candidate(pmids=[shared_pmid])
    store.upsert(seed)

    for i in range(100):
        co = _make_candidate(
            pmids=[shared_pmid],
            mesh=[_OTHER_MESH],
        )
        store.upsert(co)

    config = CohortConfig(
        max_coauthor_fanout=50,
        expansion_hops=1,
    )
    cohort = build_nsclc_translational_cohort(store, config)
    # 1 seed + at most 50 co-authors
    assert cohort.expanded_count <= 1 + 50


def test_provenance_tracked(store: CandidateStore) -> None:
    """Every candidate in the cohort has at least one provenance entry."""
    # Seed with both PubMed and NIH provenance
    seed = _make_candidate(
        pmids=["PMID_PROV"],
        grant_ids=["R01CA999999"],
    )
    store.upsert(seed)

    # A co-author (shares PMID) — will inherit provenance via expansion
    co = _make_candidate(
        pmids=["PMID_PROV"],
        mesh=[_OTHER_MESH],
    )
    store.upsert(co)

    config = CohortConfig(expansion_hops=1)
    cohort = build_nsclc_translational_cohort(store, config)

    for uid in cohort.candidates:
        assert uid in cohort.provenance
        assert len(cohort.provenance[uid]) >= 1


def test_cohort_size_bounds(store: CandidateStore) -> None:
    """On bounded fixture data the cohort size is within bounds."""
    # Create exactly 100 NSCLC seeds
    for i in range(100):
        c = _make_candidate(pmids=[f"PMID_BOUND_{i}"])
        store.upsert(c)

    config = CohortConfig(
        target_min=0,
        target_max=10000,
        expansion_hops=0,  # no expansion — just seeds
    )
    cohort = build_nsclc_translational_cohort(store, config)
    assert config.target_min <= cohort.expanded_count <= config.target_max


def test_dedup_across_sources(store: CandidateStore) -> None:
    """Same PI in PubMed and NIH yields single candidate with both sources."""
    c = _make_candidate(
        pmids=["PMID_DEDUP_1"],
        grant_ids=["R01CA111111"],
    )
    store.upsert(c)

    cohort = build_nsclc_translational_cohort(store)
    # Only one candidate, not duplicated
    assert cohort.seed_count == 1
    assert len(cohort.candidates) == 1
    prov = cohort.provenance[c.uuid]
    assert SeedSource.pubmed_last_author in prov
    assert SeedSource.nih_contact_pi in prov
