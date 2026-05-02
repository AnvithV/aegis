"""Request and response Pydantic models for the Aegis query API."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class CutoffStrategy(StrEnum):
    """Strategy for cutting off result sets."""

    top_k = "top_k"
    score_threshold = "score_threshold"


class QueryRequest(BaseModel):
    """Customer query request for expert discovery."""

    model_config = ConfigDict(frozen=True)

    task_description: str
    mesh_override: list[str] | None = None
    cohort_filter: str | None = None
    k: int = Field(default=50, ge=1, le=500)
    cutoff_strategy: CutoffStrategy = CutoffStrategy.top_k
    score_threshold: float | None = None
    include_variance_bands: bool = True
    query_type_override: str | None = None

    @field_validator("task_description")
    @classmethod
    def _check_task_description(cls, v: str) -> str:
        if len(v) < 10:
            msg = "Task description must be at least 10 characters"
            raise ValueError(msg)
        return v


class ArtifactLink(BaseModel):
    """A hyperlinked artifact contributing to a candidate's score."""

    model_config = ConfigDict(frozen=True)

    artifact_type: str
    identifier: str
    title: str
    url: str
    contribution_score: float


class IntegrityDisclosure(BaseModel):
    """Disclosure of an integrity soft-discount applied to a candidate."""

    model_config = ConfigDict(frozen=True)

    discount_type: str
    factor: float
    detail: str


class VarianceBand(BaseModel):
    """Bootstrap score confidence interval for a candidate."""

    model_config = ConfigDict(frozen=True)

    low: float
    high: float
    median: float


class CandidateResult(BaseModel):
    """A single candidate in the customer-facing ranked output."""

    model_config = ConfigDict(frozen=True)

    rank: int
    candidate_uuid: str
    candidate_name: str
    affiliation: str
    affiliation_country: str | None
    score: float
    component_scores: dict[str, float]
    top_artifacts: list[ArtifactLink]
    linkage_confidence: float
    variance_band: VarianceBand | None
    integrity_disclosures: list[IntegrityDisclosure]
    specialty: str | None
    evidence_trail: list[str]
    contact_email: str | None = None


class ExpansionInfo(BaseModel):
    """Metadata about the query expansion process."""

    model_config = ConfigDict(frozen=True)

    original_query: str
    expanded_mesh_terms: list[str]
    expansion_method: str
    low_confidence: bool = False
    cached: bool = False


class StalenessWarning(BaseModel):
    """Warning about stale integrity data sources."""

    model_config = ConfigDict(frozen=True)

    source: str
    last_updated: datetime
    sla_hours: float
    message: str


class QueryResponse(BaseModel):
    """Full response to a customer query."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    timestamp: datetime
    candidates: list[CandidateResult]
    total_candidates_evaluated: int
    excluded_count: int
    expansion_info: ExpansionInfo
    staleness_warnings: list[StalenessWarning]
    weight_version: int
    integrity_rule_version: str
    metadata: dict[str, str]


class ErrorResponse(BaseModel):
    """Error response for API errors."""

    model_config = ConfigDict(frozen=True)

    error: str
    detail: str
    retry_after: int | None = None


class ClassifyRequest(BaseModel):
    """Request to classify a query and return detected type + weight vector."""

    model_config = ConfigDict(frozen=True)

    task_description: str


class ClassifyResponse(BaseModel):
    """Response with query classification and associated weight vector."""

    model_config = ConfigDict(frozen=True)

    query_type: str
    confidence: float
    keyword_matches: list[str]
    weights: dict[str, float]
    exponents: dict[str, float]
