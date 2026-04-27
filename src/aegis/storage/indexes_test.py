"""Tests for IndexManager: MeSH index, yearly counts, and performance."""

from __future__ import annotations

import time
import uuid as _uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from aegis.storage.candidate_store import CandidateStore
from aegis.storage.indexes import IndexManager
from aegis.storage.schema import (
    AffiliationSpan,
    ArtifactRefBundle,
    Candidate,
    MeshDescriptor,
)


def _make_candidate(
    *,
    candidate_uuid: str | None = None,
    orcid: str | None = None,
    mesh_terms: list[MeshDescriptor] | None = None,
    sources: dict[str, datetime] | None = None,
) -> Candidate:
    """Create a Candidate with configurable MeSH and sources."""
    return Candidate(
        uuid=candidate_uuid or str(_uuid.uuid4()),
        strong_keys={"orcid": orcid or f"0000-{_uuid.uuid4().hex[:14]}"},
        name_variants=["Test Person"],
        affiliations=[
            AffiliationSpan(
                ror_id=None,
                canonical_name="Test University",
                raw_string="Test Univ",
                country="US",
                confidence=0.9,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
        ],
        artifact_refs=ArtifactRefBundle(
            pmids=["11111111"],
            nct_ids=[],
            grant_ids=[],
        ),
        linkage_confidence=0.8,
        evidence_trail=["test"],
        last_updated_per_source=sources
        or {
            "pubmed": datetime(2024, 1, 1, tzinfo=UTC),
        },
        mesh_descriptors=mesh_terms or [],
    )


@pytest.fixture()
def store(tmp_path: Path) -> Generator[CandidateStore]:
    """Create a CandidateStore backed by a temporary DuckDB file."""
    db_path = str(tmp_path / "test.duckdb")
    s = CandidateStore(db_path=db_path)
    yield s
    s.close()


def test_mesh_index_lookup(store: CandidateStore) -> None:
    """Insert 3 candidates, 2 with NSCLC MeSH, lookup returns 2."""
    nsclc = MeshDescriptor(
        descriptor="Carcinoma, Non-Small-Cell Lung",
        qualifier="drug therapy",
        major_topic=True,
    )
    other = MeshDescriptor(
        descriptor="Diabetes Mellitus",
        qualifier=None,
        major_topic=False,
    )

    store.upsert(_make_candidate(mesh_terms=[nsclc]))
    store.upsert(_make_candidate(mesh_terms=[nsclc, other]))
    store.upsert(_make_candidate(mesh_terms=[other]))

    mgr = IndexManager(store)
    mgr.rebuild_mesh_index()

    results = mgr.lookup_by_mesh(
        "Carcinoma, Non-Small-Cell Lung", "drug therapy"
    )
    assert len(results) == 2

    results_all = mgr.lookup_by_mesh(
        "Carcinoma, Non-Small-Cell Lung"
    )
    assert len(results_all) == 2

    diabetes = mgr.lookup_by_mesh("Diabetes Mellitus")
    assert len(diabetes) == 2


def test_mesh_index_rebuild_idempotent(
    store: CandidateStore,
) -> None:
    """Rebuilding twice yields same count."""
    nsclc = MeshDescriptor(
        descriptor="NSCLC",
        qualifier=None,
        major_topic=True,
    )
    store.upsert(_make_candidate(mesh_terms=[nsclc]))
    store.upsert(_make_candidate(mesh_terms=[nsclc]))

    mgr = IndexManager(store)
    count1 = mgr.rebuild_mesh_index()
    count2 = mgr.rebuild_mesh_index()
    assert count1 == count2 == 2


def test_yearly_counts(store: CandidateStore) -> None:
    """Verify yearly aggregation from last_updated_per_source."""
    sources = {
        "pubmed": datetime(2023, 6, 1, tzinfo=UTC),
        "nih_reporter": datetime(2024, 3, 1, tzinfo=UTC),
    }
    c = _make_candidate(sources=sources)
    store.upsert(c)

    mgr = IndexManager(store)
    mgr.rebuild_yearly_counts()

    counts = mgr.get_yearly_counts(c.uuid)
    assert 2023 in counts
    assert counts[2023]["publication"] == 1
    assert 2024 in counts
    assert counts[2024]["grant"] == 1


def test_lookup_performance(store: CandidateStore) -> None:
    """MeSH lookup on 5000 candidates completes in < 100ms."""
    nsclc = MeshDescriptor(
        descriptor="NSCLC-Perf",
        qualifier=None,
        major_topic=True,
    )
    for i in range(5000):
        store.upsert(
            _make_candidate(
                orcid=f"0000-perf-{i:06d}",
                mesh_terms=[nsclc],
            )
        )

    mgr = IndexManager(store)
    mgr.rebuild_mesh_index()

    start = time.perf_counter()
    results = mgr.lookup_by_mesh("NSCLC-Perf")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(results) == 5000
    assert elapsed_ms < 100, f"Lookup took {elapsed_ms:.1f}ms"


def test_candidate_fetch_performance(
    store: CandidateStore,
) -> None:
    """get_by_uuid on 5000 candidates completes in < 50ms."""
    uuids: list[str] = []
    for i in range(5000):
        uid = str(_uuid.uuid4())
        uuids.append(uid)
        store.upsert(
            _make_candidate(
                candidate_uuid=uid,
                orcid=f"0000-fetch-{i:06d}",
            )
        )

    target_uuid = uuids[2500]

    start = time.perf_counter()
    result = store.get_by_uuid(target_uuid)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result is not None
    assert result.uuid == target_uuid
    assert elapsed_ms < 50, f"Fetch took {elapsed_ms:.1f}ms"
