"""Tests for request/response Pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aegis.api.schemas import (
    ArtifactLink,
    CandidateResult,
    CutoffStrategy,
    ExpansionInfo,
    IntegrityDisclosure,
    QueryRequest,
    QueryResponse,
    StalenessWarning,
    VarianceBand,
)


def test_query_request_defaults() -> None:
    req = QueryRequest(
        task_description=(
            "Evaluate JAK2 inhibitor candidates"
            " for kinase selectivity screening"
        )
    )
    assert req.k == 50
    assert req.cutoff_strategy == CutoffStrategy.top_k
    assert req.include_variance_bands is True
    assert req.mesh_override is None
    assert req.cohort_filter is None
    assert req.score_threshold is None


def test_query_request_short_description() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(task_description="short")


def test_query_request_empty_description() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(task_description="")


def test_query_request_custom_k() -> None:
    req = QueryRequest(
        task_description="Evaluate JAK2 inhibitor candidates for screening",
        k=100,
    )
    assert req.k == 100

    with pytest.raises(ValidationError):
        QueryRequest(
            task_description="Evaluate JAK2 inhibitor candidates for screening",
            k=0,
        )

    with pytest.raises(ValidationError):
        QueryRequest(
            task_description="Evaluate JAK2 inhibitor candidates for screening",
            k=501,
        )


def test_candidate_result_model() -> None:
    result = CandidateResult(
        rank=1,
        candidate_uuid="abc-123",
        candidate_name="Dr. Jane Smith",
        affiliation="MIT",
        affiliation_country="US",
        score=0.85,
        component_scores={
            "quality_prior": 0.9,
            "topical_fit": 0.8,
            "recency": 0.7,
            "integrity": 1.0,
        },
        top_artifacts=[
            ArtifactLink(
                artifact_type="pmid",
                identifier="12345678",
                title="Test Paper",
                url="https://pubmed.ncbi.nlm.nih.gov/12345678",
                contribution_score=0.3,
            )
        ],
        linkage_confidence=0.95,
        variance_band=VarianceBand(low=0.75, high=0.95, median=0.85),
        integrity_disclosures=[
            IntegrityDisclosure(
                discount_type="predatory_load",
                factor=0.9,
                detail="predatory load 0.05",
            )
        ],
        specialty="Oncology",
        evidence_trail=["PubMed: 12345678"],
    )
    assert result.rank == 1
    # Verify frozen
    with pytest.raises(ValidationError):
        result.rank = 2


def test_query_response_model() -> None:
    now = datetime.now(UTC)
    candidates = [
        CandidateResult(
            rank=i,
            candidate_uuid=f"uuid-{i}",
            candidate_name=f"Dr. Test {i}",
            affiliation="Test Uni",
            affiliation_country="US",
            score=0.9 - i * 0.1,
            component_scores={
                "quality_prior": 0.8,
                "topical_fit": 0.7,
                "recency": 0.6,
                "integrity": 1.0,
            },
            top_artifacts=[],
            linkage_confidence=0.9,
            variance_band=None,
            integrity_disclosures=[],
            specialty=None,
            evidence_trail=[],
        )
        for i in range(3)
    ]
    response = QueryResponse(
        query_id="q-001",
        timestamp=now,
        candidates=candidates,
        total_candidates_evaluated=100,
        excluded_count=5,
        expansion_info=ExpansionInfo(
            original_query="JAK2 inhibitors",
            expanded_mesh_terms=["Protein Kinases", "Neoplasms"],
            expansion_method="llm",
        ),
        staleness_warnings=[
            StalenessWarning(
                source="retraction_watch",
                last_updated=now,
                sla_hours=6.0,
                message="Data may be stale",
            )
        ],
        weight_version=1,
        integrity_rule_version="1.0.0",
        metadata={"run_id": "test"},
    )
    json_str = response.model_dump_json()
    assert "q-001" in json_str
    assert len(response.candidates) == 3


def test_artifact_link_model() -> None:
    link = ArtifactLink(
        artifact_type="pmid",
        identifier="12345678",
        title="A Study on JAK2",
        url="https://pubmed.ncbi.nlm.nih.gov/12345678",
        contribution_score=0.25,
    )
    assert link.artifact_type == "pmid"
    assert link.identifier == "12345678"
    assert link.url == "https://pubmed.ncbi.nlm.nih.gov/12345678"
    assert link.contribution_score == 0.25


def test_staleness_warning_model() -> None:
    now = datetime.now(UTC)
    warning = StalenessWarning(
        source="ori",
        last_updated=now,
        sla_hours=24.0,
        message="ORI data is stale beyond SLA",
    )
    assert warning.source == "ori"
    assert warning.sla_hours == 24.0
    assert warning.last_updated == now
    assert "stale" in warning.message
