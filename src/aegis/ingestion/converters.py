"""Source-record-to-Candidate converters for live ingestion."""

from __future__ import annotations

import hashlib
import json as json_mod
import re
import unicodedata
from datetime import UTC, datetime

from aegis.sources.ctgov import StudyRecord
from aegis.sources.openalex import OpenAlexWork
from aegis.sources.pubmed import PubMedRecord
from aegis.sources.reporter import GrantRecord
from aegis.storage.schema import AffiliationSpan, ArtifactRefBundle, Candidate, MeshDescriptor

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_orcid(raw: str) -> str:
    """Strip URL prefix from ORCID, keeping only digits and dashes."""
    return (
        raw.strip()
        .replace("https://orcid.org/", "")
        .replace("http://orcid.org/", "")
    )


def _normalize_name(name: str) -> str:
    """NFC-normalise and lowercase a personal name."""
    return unicodedata.normalize("NFC", name).lower().strip()


def _make_uuid(strong_keys: dict[str, str], name: str, affiliation: str = "") -> str:
    """Generate a deterministic 32-hex-char UUID.

    Priority: orcid > era_commons > sha256(normalized_name + affiliation).
    """
    if "orcid" in strong_keys:
        key = f"orcid:{_normalize_orcid(strong_keys['orcid'])}"
    elif "era_commons" in strong_keys:
        key = f"era:{strong_keys['era_commons'].upper()}"
    else:
        key = f"name:{_normalize_name(name)}:{affiliation[:80].lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# PubMed
# ---------------------------------------------------------------------------


def _extract_email(affiliations: list[str]) -> str | None:
    """Extract email address from PubMed affiliation strings (corresponding author)."""
    for aff in affiliations:
        match = _EMAIL_RE.search(aff)
        if match:
            return match.group()
    return None


def pubmed_record_to_candidates(record: PubMedRecord) -> list[Candidate]:
    """Extract last (senior) author only; fallback to first author if none marked."""
    authors = [a for a in record.authors if a.is_last_author]
    if not authors and record.authors:
        authors = [record.authors[0]]

    results: list[Candidate] = []
    for author in authors:
        name = author.full_name.strip()
        if not name:
            continue

        strong_keys: dict[str, str] = {}
        if author.orcid:
            strong_keys["orcid"] = _normalize_orcid(author.orcid)

        affiliation = author.affiliations[0] if author.affiliations else ""
        uuid = _make_uuid(strong_keys, name, affiliation)

        date_str = str(record.publication_date) if record.publication_date else "unknown date"
        title_short = record.title[:80] if record.title else "Untitled"

        results.append(
            Candidate(
                uuid=uuid,
                strong_keys=strong_keys,
                name_variants=[name],
                affiliations=[
                    AffiliationSpan(
                        ror_id=None,
                        canonical_name=affiliation[:200],
                        raw_string=affiliation[:500],
                        country=None,
                        confidence=0.70,
                        start_date=None,
                        end_date=None,
                    )
                ]
                if affiliation
                else [],
                artifact_refs=ArtifactRefBundle(
                    pmids=[record.pmid],
                    nct_ids=[],
                    grant_ids=[],
                    patent_ids=[],
                ),
                linkage_confidence=0.85 if strong_keys.get("orcid") else 0.70,
                evidence_trail=[
                    f"Principal Investigator: '{title_short}' (PMID:{record.pmid}, {date_str})"
                ],
                last_updated_per_source={"pubmed": datetime.now(UTC)},
                mesh_descriptors=list(record.mesh_descriptors[:30]),
                contact_email=_extract_email(author.affiliations),
            )
        )
    return results


# ---------------------------------------------------------------------------
# NIH Reporter
# ---------------------------------------------------------------------------


def grant_record_to_candidates(record: GrantRecord) -> list[Candidate]:
    """Convert a grant record to one Candidate per PI."""
    results: list[Candidate] = []
    for pi in record.pis:
        name = pi.full_name.strip()
        if not name:
            continue

        strong_keys: dict[str, str] = {}
        if pi.era_id:
            strong_keys["era_commons"] = pi.era_id.upper()
        if pi.orcid:
            strong_keys["orcid"] = _normalize_orcid(pi.orcid)

        affiliation = pi.organization or record.organization_name or ""
        uuid = _make_uuid(strong_keys, name, affiliation)

        cost_str = f"${record.total_cost:,}" if record.total_cost else "cost unknown"
        title_part = f": '{record.project_title[:80]}'" if record.project_title else ""
        mesh = [
            MeshDescriptor(descriptor=cat, qualifier=None, major_topic=False)
            for cat in record.rcdc_categories[:10]
        ]

        trail = [
            f"Principal Investigator on NIH {record.project_number}{title_part} ({record.fiscal_year}, {cost_str})"
        ]
        if record.abstract_text:
            trail.append(f"Grant scope: {record.abstract_text[:300]}")

        results.append(
            Candidate(
                uuid=uuid,
                strong_keys=strong_keys,
                name_variants=[name],
                affiliations=[
                    AffiliationSpan(
                        ror_id=record.organization_ror_candidate,
                        canonical_name=affiliation[:200],
                        raw_string=affiliation[:500],
                        country=None,
                        confidence=0.80 if record.organization_ror_candidate else 0.65,
                        start_date=None,
                        end_date=None,
                    )
                ]
                if affiliation
                else [],
                artifact_refs=ArtifactRefBundle(
                    pmids=[],
                    nct_ids=[],
                    grant_ids=[record.project_number],
                    patent_ids=[],
                ),
                linkage_confidence=0.93 if strong_keys.get("era_commons") else 0.78,
                evidence_trail=trail,
                last_updated_per_source={"reporter": datetime.now(UTC)},
                mesh_descriptors=mesh,
            )
        )
    return results


# ---------------------------------------------------------------------------
# ClinicalTrials.gov
# ---------------------------------------------------------------------------


def study_record_to_candidates(record: StudyRecord) -> list[Candidate]:
    """Extract PI-role investigators only."""
    pis = [i for i in record.investigators if i.role == "PI"]
    if not pis:
        return []

    results: list[Candidate] = []
    for pi in pis:
        name = pi.full_name.strip()
        if not name:
            continue

        affiliation = pi.affiliation or ""
        uuid = _make_uuid({}, name, affiliation)
        title_short = record.title[:80] if record.title else record.nct_id
        # conditionBrowseModule is absent from CT.gov API default response,
        # so conditions_mesh is usually empty. Fall back to freetext conditions.
        mesh_sources = record.conditions_mesh or record.conditions_freetext
        mesh = [
            MeshDescriptor(descriptor=t, qualifier=None, major_topic=True)
            for t in mesh_sources[:10]
        ]

        results.append(
            Candidate(
                uuid=uuid,
                strong_keys={},
                name_variants=[name],
                affiliations=[
                    AffiliationSpan(
                        ror_id=None,
                        canonical_name=affiliation[:200],
                        raw_string=affiliation[:500],
                        country=None,
                        confidence=0.60,
                        start_date=None,
                        end_date=None,
                    )
                ]
                if affiliation
                else [],
                artifact_refs=ArtifactRefBundle(
                    pmids=[],
                    nct_ids=[record.nct_id],
                    grant_ids=[],
                    patent_ids=[],
                ),
                linkage_confidence=0.72,
                evidence_trail=[
                    f"PI on {record.nct_id}: '{title_short}' ({record.phase or 'phase?'}, {record.status})"
                ],
                last_updated_per_source={"ctgov": datetime.now(UTC)},
                mesh_descriptors=mesh,
            )
        )
    return results


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------


def openalex_work_to_candidates(record: OpenAlexWork) -> list[Candidate]:
    """Extract last-position author only; fallback to final element."""
    last = [a for a in record.authorships if a.get("position") == "last"]
    if not last and record.authorships:
        last = [record.authorships[-1]]

    results: list[Candidate] = []
    for authorship in last:
        name = (authorship.get("author_name") or "").strip()
        if not name:
            continue

        strong_keys: dict[str, str] = {}
        raw_orcid = authorship.get("orcid") or authorship.get("author_orcid")
        if raw_orcid:
            strong_keys["orcid"] = _normalize_orcid(raw_orcid)

        uuid = _make_uuid(strong_keys, name)
        title_short = record.title[:80] if record.title else record.openalex_id
        mesh = [
            MeshDescriptor(descriptor=t, qualifier=None, major_topic=False)
            for t in record.mesh_terms[:10]
        ]

        grant_ids: list[str] = []
        try:
            raw_data = json_mod.loads(record.raw_json)
            for grant in raw_data.get("grants") or []:
                award_id = grant.get("award_id")
                funder_name = grant.get("funder_display_name", "")
                if award_id:
                    grant_ids.append(
                        f"{funder_name}-{award_id}" if funder_name else award_id
                    )
        except (json_mod.JSONDecodeError, TypeError):
            pass

        results.append(
            Candidate(
                uuid=uuid,
                strong_keys=strong_keys,
                name_variants=[name],
                affiliations=[],
                artifact_refs=ArtifactRefBundle(
                    pmids=[record.pmid] if record.pmid else [],
                    nct_ids=[],
                    grant_ids=grant_ids,
                    patent_ids=[],
                ),
                linkage_confidence=0.85 if strong_keys.get("orcid") else 0.65,
                evidence_trail=[
                    f"OpenAlex {record.openalex_id}: '{title_short}' ({record.cited_by_count} citations)"
                ],
                last_updated_per_source={"openalex": datetime.now(UTC)},
                mesh_descriptors=mesh,
            )
        )
    return results


