"""Pydantic models for ranked candidate results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ContributingArtifact(BaseModel):
    """A single artifact that contributed to a candidate's score."""

    model_config = ConfigDict(frozen=True)

    artifact_type: str
    identifier: str
    title: str
    contribution_score: float


class ComponentBreakdown(BaseModel):
    """Per-component breakdown of the final Rank(c,q) score."""

    model_config = ConfigDict(frozen=True)

    integrity_score: float
    quality_prior: float
    quality_prior_powered: float  # Q^alpha
    topical_fit: float
    topical_fit_powered: float  # T^beta
    recency: float
    recency_powered: float  # R^gamma
    final_score: float


class RankedCandidate(BaseModel):
    """A single candidate in the ranked output."""

    model_config = ConfigDict(frozen=True)

    rank: int
    candidate_uuid: str
    candidate_name: str
    linkage_confidence: float
    score: float
    breakdown: ComponentBreakdown
    top_artifacts: list[ContributingArtifact]
    evidence_trail: list[str]


class RankedList(BaseModel):
    """Full ranked result set for a query."""

    model_config = ConfigDict(frozen=True)

    query_mesh_terms: list[str]
    cohort_size: int
    result_count: int
    candidates: list[RankedCandidate]
    excluded_count: int
    weight_version: int
    exponents: dict[str, float]
    metadata: dict[str, str]
