"""Tests for the Phase 0 archetype validation harness."""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import (
    ArtifactRefBundle,
    Candidate,
    MeshDescriptor,
)
from aegis.validation.archetypes import (
    ArchetypeFixture,
    load_archetypes,
    load_phase0_archetypes,
)
from aegis.validation.phase0_harness import Phase0Harness, ValidationResult


def _make_candidate_with_artifacts(
    *,
    pmids: list[str] | None = None,
    nct_ids: list[str] | None = None,
    grant_ids: list[str] | None = None,
) -> Candidate:
    return Candidate(
        uuid=str(_uuid.uuid4()),
        strong_keys={},
        name_variants=["Test PI"],
        affiliations=[],
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
        mesh_descriptors=[
            MeshDescriptor(
                descriptor="Carcinoma, Non-Small-Cell Lung",
                qualifier=None,
                major_topic=True,
            )
        ],
    )


@pytest.fixture()
def store(tmp_path: Path) -> Generator[CandidateStore]:
    db_path = str(tmp_path / "test.duckdb")
    s = CandidateStore(db_path=db_path)
    yield s
    s.close()


@pytest.fixture()
def populated_store(store: CandidateStore) -> CandidateStore:
    """Store populated with artifacts matching Dr. A and Dr. B fixtures."""
    dr_a_fixtures = load_phase0_archetypes()
    for fixture in dr_a_fixtures:
        arts = fixture.expected_artifacts
        c = _make_candidate_with_artifacts(
            pmids=arts.pmids,
            nct_ids=arts.nct_ids,
            grant_ids=arts.grant_ids,
        )
        store.upsert(c)
    return store


def test_dr_a_artifacts_present(populated_store: CandidateStore) -> None:
    """Validate Dr. A fixture against populated store."""
    harness = Phase0Harness(populated_store)
    fixtures = load_phase0_archetypes()
    dr_a = next(f for f in fixtures if f.archetype_id == "dr_a")
    result = harness.validate_archetype(dr_a)
    assert result.coverage_pct >= 0.95
    assert result.passed is True


def test_dr_b_artifacts_present(populated_store: CandidateStore) -> None:
    """Validate Dr. B fixture against populated store."""
    harness = Phase0Harness(populated_store)
    fixtures = load_phase0_archetypes()
    dr_b = next(f for f in fixtures if f.archetype_id == "dr_b")
    result = harness.validate_archetype(dr_b)
    assert result.coverage_pct >= 0.95
    assert result.passed is True


def test_dr_c_stubbed() -> None:
    """Dr. C fixture has in_scope_phase0=False."""
    all_fixtures = load_archetypes()
    dr_c = next(f for f in all_fixtures if f.archetype_id == "dr_c")
    assert dr_c.in_scope_phase0 is False


def test_dr_d_stubbed() -> None:
    """Dr. D fixture has in_scope_phase0=False."""
    all_fixtures = load_archetypes()
    dr_d = next(f for f in all_fixtures if f.archetype_id == "dr_d")
    assert dr_d.in_scope_phase0 is False


def test_harness_report_generated(
    populated_store: CandidateStore,
) -> None:
    """Run validate_all(), assert report is non-empty markdown."""
    harness = Phase0Harness(populated_store)
    results = harness.validate_all()
    report = harness.generate_report(results)
    assert len(report) > 0
    assert "# Phase 0 Validation Report" in report
    assert "PASS" in report


def test_harness_fails_on_missing_artifacts(
    store: CandidateStore,
) -> None:
    """Fixture with artifacts not in store should fail validation."""
    fixture = ArchetypeFixture(
        name="Missing PI",
        archetype_id="missing",
        description="Artifacts not in store",
        expected_artifacts=ArtifactRefBundle(
            pmids=["99999999"],
            nct_ids=["NCT99999999"],
            grant_ids=["R01CA999999"],
        ),
        assertions=["Should fail"],
        in_scope_phase0=True,
    )
    harness = Phase0Harness(store)
    result = harness.validate_archetype(fixture)
    assert result.passed is False
    assert result.coverage_pct == 0.0
    assert len(result.missing_artifacts) == 3


def test_all_archetypes_loaded() -> None:
    """load_archetypes() returns exactly 4 fixtures."""
    fixtures = load_archetypes()
    assert len(fixtures) == 4
    ids = {f.archetype_id for f in fixtures}
    assert ids == {"dr_a", "dr_b", "dr_c", "dr_d"}
