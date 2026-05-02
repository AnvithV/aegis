"""Candidate schema models for the Aegis storage layer."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class StrongKeyType(StrEnum):
    """Enumeration of strong identity key types."""

    orcid = "orcid"
    era_commons = "era_commons"
    npi = "npi"


class AffiliationSpan(BaseModel):
    """Time-stamped affiliation record with ROR resolution metadata."""

    model_config = ConfigDict(frozen=True)

    ror_id: str | None
    canonical_name: str
    raw_string: str
    country: str | None
    confidence: float
    start_date: date | None
    end_date: date | None


class MeshDescriptor(BaseModel):
    """MeSH descriptor with optional qualifier and major-topic flag."""

    model_config = ConfigDict(frozen=True)

    descriptor: str
    qualifier: str | None
    major_topic: bool


class ArtifactRefBundle(BaseModel):
    """Bundle of cross-source artifact references."""

    model_config = ConfigDict(frozen=True)

    pmids: list[str]
    nct_ids: list[str]
    grant_ids: list[str]
    patent_ids: list[str] = []


class Candidate(BaseModel):
    """Unified candidate record aggregating identity, affiliations, and artifacts."""

    model_config = ConfigDict(frozen=True)

    uuid: str
    strong_keys: dict[str, str]
    name_variants: list[str]
    affiliations: list[AffiliationSpan]
    artifact_refs: ArtifactRefBundle
    linkage_confidence: float
    evidence_trail: list[str]
    last_updated_per_source: dict[str, datetime]
    mesh_descriptors: list[MeshDescriptor]
    contact_email: str | None = None
