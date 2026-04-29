"""Tests for ingestion converters."""

from __future__ import annotations

from datetime import date

import pytest

from aegis.ingestion.converters import (
    _make_uuid,
    _normalize_orcid,
    grant_record_to_candidates,
    openalex_work_to_candidates,
    pubmed_record_to_candidates,
    study_record_to_candidates,
)
from aegis.sources.ctgov import InvestigatorRole, StudyRecord
from aegis.sources.openalex import OpenAlexWork
from aegis.sources.pubmed import AuthorAffiliation, PubMedRecord
from aegis.sources.reporter import GrantPI, GrantRecord
from aegis.storage.schema import MeshDescriptor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pubmed(
    pmid: str = "12345",
    authors: list[AuthorAffiliation] | None = None,
    mesh: list[MeshDescriptor] | None = None,
) -> PubMedRecord:
    return PubMedRecord(
        pmid=pmid,
        title="A test paper",
        abstract=None,
        mesh_descriptors=mesh or [],
        authors=authors or [],
        journal_nlm_id=None,
        medline_indexed=True,
        publication_date=date(2023, 1, 1),
        article_type=None,
        raw_xml="<xml/>",
    )


def _make_author(
    full_name: str,
    is_last: bool = False,
    orcid: str | None = None,
    affiliations: list[str] | None = None,
) -> AuthorAffiliation:
    return AuthorAffiliation(
        full_name=full_name,
        last_name=full_name.split()[-1] if full_name.strip() else "",
        initials="X",
        orcid=orcid,
        affiliations=affiliations or [],
        is_last_author=is_last,
    )


def _make_grant(
    project_number: str = "R01CA123456",
    pis: list[GrantPI] | None = None,
    rcdc: list[str] | None = None,
) -> GrantRecord:
    return GrantRecord(
        project_number=project_number,
        activity_code="R01",
        pis=pis or [],
        total_cost=500_000,
        fiscal_year=2023,
        project_terms=[],
        rcdc_categories=rcdc or [],
        organization_name="Test University",
        organization_ror_candidate=None,
        award_notice_date=None,
        is_active=True,
        raw_json="{}",
    )


def _make_study(
    nct_id: str = "NCT00000001",
    investigators: list[InvestigatorRole] | None = None,
    conditions_mesh: list[str] | None = None,
) -> StudyRecord:
    return StudyRecord(
        nct_id=nct_id,
        title="A test trial",
        conditions_mesh=conditions_mesh or [],
        conditions_freetext=[],
        interventions=[],
        phase="PHASE2",
        study_type="INTERVENTIONAL",
        sponsor=None,
        investigators=investigators or [],
        status="RECRUITING",
        status_history=[],
        randomization=None,
        masking=None,
        last_update_post_date=None,
        raw_json="{}",
    )


def _make_openalex_work(
    authorships: list[dict] | None = None,
    mesh_terms: list[str] | None = None,
) -> OpenAlexWork:
    return OpenAlexWork(
        openalex_id="W1234567890",
        doi=None,
        title="An OpenAlex paper",
        publication_date=date(2023, 6, 1),
        type="article",
        cited_by_count=42,
        concepts=[],
        authorships=authorships or [],
        primary_location=None,
        mesh_terms=mesh_terms or [],
        raw_json="{}",
    )


# ---------------------------------------------------------------------------
# PubMed converter tests
# ---------------------------------------------------------------------------


def test_pubmed_last_author_only() -> None:
    """Paper with last-author marked → only that author extracted."""
    authors = [
        _make_author("First Author", is_last=False),
        _make_author("Last Author", is_last=True),
    ]
    record = _make_pubmed(authors=authors)
    candidates = pubmed_record_to_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].name_variants == ["Last Author"]


def test_pubmed_fallback_to_first() -> None:
    """No last-author marked → fallback to first author."""
    authors = [
        _make_author("Only Author", is_last=False),
    ]
    record = _make_pubmed(authors=authors)
    candidates = pubmed_record_to_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].name_variants == ["Only Author"]


def test_pubmed_skips_empty_name() -> None:
    """Author with empty full_name → 0 candidates."""
    authors = [_make_author("", is_last=True)]
    record = _make_pubmed(authors=authors)
    candidates = pubmed_record_to_candidates(record)
    assert candidates == []


def test_pubmed_orcid_normalization() -> None:
    """ORCID with URL prefix → stripped in strong_keys."""
    authors = [
        _make_author(
            "Jane Doe",
            is_last=True,
            orcid="https://orcid.org/0000-0001-2345-6789",
        )
    ]
    record = _make_pubmed(authors=authors)
    candidates = pubmed_record_to_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].strong_keys["orcid"] == "0000-0001-2345-6789"
    assert candidates[0].linkage_confidence == 0.85


def test_pubmed_no_orcid_lower_confidence() -> None:
    """No ORCID → linkage_confidence is 0.70."""
    authors = [_make_author("Jane Doe", is_last=True)]
    record = _make_pubmed(authors=authors)
    candidates = pubmed_record_to_candidates(record)
    assert candidates[0].linkage_confidence == 0.70
    assert "orcid" not in candidates[0].strong_keys


# ---------------------------------------------------------------------------
# NIH Reporter converter tests
# ---------------------------------------------------------------------------


def test_grant_pi_strong_keys() -> None:
    """PI with era_id → era_commons in strong_keys."""
    pi = GrantPI(
        full_name="Dr Researcher",
        era_id="RESEARCHER1",
        orcid=None,
        role="Contact PI",
        organization="Harvard",
    )
    record = _make_grant(pis=[pi])
    candidates = grant_record_to_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].strong_keys["era_commons"] == "RESEARCHER1"
    assert candidates[0].linkage_confidence == 0.93


def test_grant_skips_empty_pi_name() -> None:
    """PI with empty name → skipped."""
    pi = GrantPI(
        full_name="   ",
        era_id="ABC123",
        orcid=None,
        role="Contact PI",
        organization=None,
    )
    record = _make_grant(pis=[pi])
    candidates = grant_record_to_candidates(record)
    assert candidates == []


def test_grant_artifact_refs() -> None:
    """Grant ID appears in artifact_refs.grant_ids."""
    pi = GrantPI(
        full_name="PI Name",
        era_id="PI1",
        orcid=None,
        role="Contact PI",
        organization=None,
    )
    record = _make_grant(project_number="R01CA999999", pis=[pi])
    candidates = grant_record_to_candidates(record)
    assert "R01CA999999" in candidates[0].artifact_refs.grant_ids


# ---------------------------------------------------------------------------
# CT.gov converter tests
# ---------------------------------------------------------------------------


def test_study_pi_role_only() -> None:
    """Study with PI and Sub-I → only PI extracted."""
    investigators = [
        InvestigatorRole(full_name="Dr PI", role="PI", affiliation="Mayo Clinic"),
        InvestigatorRole(full_name="Dr SubI", role="Sub-I", affiliation=None),
    ]
    record = _make_study(investigators=investigators)
    candidates = study_record_to_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].name_variants == ["Dr PI"]
    assert record.nct_id in candidates[0].artifact_refs.nct_ids


def test_study_no_pi_returns_empty() -> None:
    """Study with no PI-role investigator → empty list."""
    investigators = [
        InvestigatorRole(full_name="Dr SubI", role="Sub-I", affiliation=None),
    ]
    record = _make_study(investigators=investigators)
    candidates = study_record_to_candidates(record)
    assert candidates == []


# ---------------------------------------------------------------------------
# OpenAlex converter tests
# ---------------------------------------------------------------------------


def test_openalex_last_position() -> None:
    """Authorship with position='last' → extracted."""
    authorships = [
        {"position": "first", "author_name": "First Author", "orcid": None},
        {"position": "last", "author_name": "Last Author", "orcid": None},
    ]
    record = _make_openalex_work(authorships=authorships)
    candidates = openalex_work_to_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].name_variants == ["Last Author"]


def test_openalex_fallback_to_last_element() -> None:
    """No 'last' position → fallback to final authorship entry."""
    authorships = [
        {"position": "first", "author_name": "A", "orcid": None},
        {"position": "middle", "author_name": "B", "orcid": None},
    ]
    record = _make_openalex_work(authorships=authorships)
    candidates = openalex_work_to_candidates(record)
    assert len(candidates) == 1
    assert candidates[0].name_variants == ["B"]


def test_openalex_orcid_extracted() -> None:
    """ORCID in authorship → normalised and stored."""
    authorships = [
        {
            "position": "last",
            "author_name": "Jane Smith",
            "orcid": "https://orcid.org/0000-0002-9999-0000",
        }
    ]
    record = _make_openalex_work(authorships=authorships)
    candidates = openalex_work_to_candidates(record)
    assert candidates[0].strong_keys["orcid"] == "0000-0002-9999-0000"


# ---------------------------------------------------------------------------
# UUID determinism test
# ---------------------------------------------------------------------------


def test_deterministic_uuid() -> None:
    """Same inputs produce the same UUID across two calls."""
    strong_keys = {"orcid": "0000-0001-0000-0001"}
    uuid1 = _make_uuid(strong_keys, "Jane Doe", "MIT")
    uuid2 = _make_uuid(strong_keys, "Jane Doe", "MIT")
    assert uuid1 == uuid2
    assert len(uuid1) == 32


def test_uuid_differs_by_key() -> None:
    """Different ORCID → different UUID."""
    uuid1 = _make_uuid({"orcid": "0000-0001-0000-0001"}, "Jane Doe")
    uuid2 = _make_uuid({"orcid": "0000-0001-0000-0002"}, "Jane Doe")
    assert uuid1 != uuid2


def test_normalize_orcid_strips_url() -> None:
    assert _normalize_orcid("https://orcid.org/0000-0001-2345-6789") == "0000-0001-2345-6789"
    assert _normalize_orcid("http://orcid.org/0000-0001-2345-6789") == "0000-0001-2345-6789"
    assert _normalize_orcid("0000-0001-2345-6789") == "0000-0001-2345-6789"
