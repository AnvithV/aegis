"""Archetype fixture definitions for Phase 0 validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aegis.storage.schema import ArtifactRefBundle


class ArchetypeFixture(BaseModel):
    """A named archetype used as a validation fixture."""

    model_config = ConfigDict(frozen=True)

    name: str
    archetype_id: str
    description: str
    expected_artifacts: ArtifactRefBundle
    assertions: list[str]
    in_scope_phase0: bool


def _dr_a() -> ArchetypeFixture:
    """Dr. A -- Established PI.

    >=40 last-author NSCLC papers in last 10y (MEDLINE-indexed),
    >=1 active R01, PI on >=1 Phase 2/3 trial.
    """
    return ArchetypeFixture(
        name="Dr. A \u2014 Established PI",
        archetype_id="dr_a",
        description=(
            "High-volume translational PI with >=40 last-author "
            "NSCLC papers in last 10 years, at least one active "
            "R01 grant, and PI on at least one Phase 2/3 trial."
        ),
        expected_artifacts=ArtifactRefBundle(
            pmids=[
                "31003550",
                "31658955",
                "33872481",
                "34725503",
                "35091380",
            ],
            nct_ids=["NCT02409342"],
            grant_ids=["R01CA236871"],
        ),
        assertions=[
            ">=40 last-author NSCLC papers in MEDLINE within 10y",
            ">=1 active R01 grant",
            "PI on >=1 Phase 2/3 trial",
            "MeSH includes Carcinoma, Non-Small-Cell Lung",
        ],
        in_scope_phase0=True,
    )


def _dr_b() -> ArchetypeFixture:
    """Dr. B -- Industry Pivot.

    15-25 papers in last 10y, previously held R01 (now expired),
    advisor on industry-sponsored trials.
    """
    return ArchetypeFixture(
        name="Dr. B \u2014 Industry Pivot",
        archetype_id="dr_b",
        description=(
            "Mid-career PI with 15-25 papers in last 10 years, "
            "previously held R01 (now expired), currently listed "
            "as advisor on industry-sponsored trials."
        ),
        expected_artifacts=ArtifactRefBundle(
            pmids=[
                "29596029",
                "30715168",
                "32822576",
            ],
            nct_ids=["NCT03515837"],
            grant_ids=["R01CA198533"],
        ),
        assertions=[
            "15-25 papers in last 10y",
            "Previously held R01 (expired)",
            "Listed as advisor on industry-sponsored trial",
        ],
        in_scope_phase0=True,
    )


def _dr_c() -> ArchetypeFixture:
    """Dr. C -- Industry-Only.

    No PubMed presence, no NIH grants. Stubbed for Phase 2.
    """
    return ArchetypeFixture(
        name="Dr. C \u2014 Industry-Only",
        archetype_id="dr_c",
        description=(
            "Industry-only researcher with no PubMed presence "
            "and no NIH grants. Stubbed for Phase 2 expansion."
        ),
        expected_artifacts=ArtifactRefBundle(
            pmids=[],
            nct_ids=[],
            grant_ids=[],
        ),
        assertions=[
            "No PubMed papers expected",
            "No NIH grants expected",
            "Phase 2 stub only",
        ],
        in_scope_phase0=False,
    )


def _dr_d() -> ArchetypeFixture:
    """Dr. D -- Integrity Outlier.

    Papers with retractions or high self-citation.
    Stubbed for Phase 1 integrity gate.
    """
    return ArchetypeFixture(
        name="Dr. D \u2014 Integrity Outlier",
        archetype_id="dr_d",
        description=(
            "Researcher with retractions or anomalously high "
            "self-citation rate. Stubbed for Phase 1 integrity "
            "gate."
        ),
        expected_artifacts=ArtifactRefBundle(
            pmids=[],
            nct_ids=[],
            grant_ids=[],
        ),
        assertions=[
            "Has retracted papers (Phase 1 check)",
            "High self-citation ratio (Phase 1 check)",
            "Phase 1 stub only",
        ],
        in_scope_phase0=False,
    )


def load_archetypes() -> list[ArchetypeFixture]:
    """Return all 4 archetype fixture definitions."""
    return [_dr_a(), _dr_b(), _dr_c(), _dr_d()]


def load_phase0_archetypes() -> list[ArchetypeFixture]:
    """Return only the Phase 0 in-scope archetypes (Dr. A and Dr. B)."""
    return [a for a in load_archetypes() if a.in_scope_phase0]
