"""Feedback API: POST /v1/feedback/tasks/{task_id}/outcomes."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, field_validator

from aegis.learning.downstream_quality import (
    DownstreamQualityStore,
    TaskOutcome,
    TaskOutcomeCandidate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])

# Disallowed PHI key substrings (case-insensitive)
_PHI_KEYS = frozenset({
    "ssn",
    "social_security",
    "dob",
    "date_of_birth",
    "mrn",
    "medical_record",
    "patient_name",
    "patient_id",
    "phi",
})


class CandidateOutcomeRequest(BaseModel):
    """Request model for a single candidate's outcome data."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    candidate_rank: int
    quality_prior_score: float
    topical_fit_score: float
    recency_score: float


class TaskOutcomeRequest(BaseModel):
    """Request model for submitting downstream task quality outcomes."""

    model_config = ConfigDict(frozen=True)

    query_specialty: str
    query_mesh_terms: list[str]
    candidates: list[CandidateOutcomeRequest]
    fleiss_kappa: float | None = None
    accept_rate: float | None = None
    consensus_rate: float | None = None
    metadata: dict[str, str] = {}  # noqa: RUF012

    @field_validator("metadata")
    @classmethod
    def reject_phi_keys(cls, v: dict[str, str]) -> dict[str, str]:
        """Reject metadata keys containing PHI-related strings."""
        for key in v:
            key_lower = key.lower()
            for phi_key in _PHI_KEYS:
                if phi_key in key_lower:
                    msg = "PHI fields are not accepted"
                    raise ValueError(msg)
        return v

    @field_validator("fleiss_kappa")
    @classmethod
    def validate_fleiss_kappa(cls, v: float | None) -> float | None:
        """Ensure fleiss_kappa is between -1.0 and 1.0 if not None."""
        if v is not None and (v < -1.0 or v > 1.0):
            msg = "fleiss_kappa must be between -1.0 and 1.0"
            raise ValueError(msg)
        return v

    @field_validator("accept_rate")
    @classmethod
    def validate_accept_rate(cls, v: float | None) -> float | None:
        """Ensure accept_rate is between 0.0 and 1.0 if not None."""
        if v is not None and (v < 0.0 or v > 1.0):
            msg = "accept_rate must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v

    @field_validator("consensus_rate")
    @classmethod
    def validate_consensus_rate(cls, v: float | None) -> float | None:
        """Ensure consensus_rate is between 0.0 and 1.0 if not None."""
        if v is not None and (v < 0.0 or v > 1.0):
            msg = "consensus_rate must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class TaskOutcomeResponse(BaseModel):
    """Response model for a submitted task outcome."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    status: str
    outcome_count: int
    derived_judgments_count: int


# Module-level store path (will be overridden in tests via monkeypatch)
_default_store_path = Path("data/aegis/downstream_quality.jsonl")


def _get_store(store_path: Path | None = None) -> DownstreamQualityStore:
    """Factory for the downstream quality store."""
    return DownstreamQualityStore(storage_path=store_path or _default_store_path)


@router.post(
    "/tasks/{task_id}/outcomes",
    response_model=TaskOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_task_outcome(
    task_id: str,
    body: TaskOutcomeRequest,
) -> TaskOutcomeResponse:
    """Submit downstream task quality outcomes for a completed task.

    Maps task outcomes to (query, candidate) pairs and persists
    them for weight relearning.
    """
    store = _get_store()

    # Build internal TaskOutcome from request
    candidates = [
        TaskOutcomeCandidate(
            candidate_uuid=c.candidate_uuid,
            candidate_rank=c.candidate_rank,
            quality_prior_score=c.quality_prior_score,
            topical_fit_score=c.topical_fit_score,
            recency_score=c.recency_score,
        )
        for c in body.candidates
    ]

    outcome = TaskOutcome(
        task_id=task_id,
        query_specialty=body.query_specialty,
        query_mesh_terms=body.query_mesh_terms,
        candidates=candidates,
        fleiss_kappa=body.fleiss_kappa,
        accept_rate=body.accept_rate,
        consensus_rate=body.consensus_rate,
        submitted_at=datetime.now(),
        metadata=body.metadata,
    )

    store.append(outcome=outcome)

    # Derive pairwise judgments to report count
    # (only from this single outcome, not the full store)
    n_candidates = len(candidates)
    derived_count = max(0, n_candidates - 1)  # adjacent pairs

    return TaskOutcomeResponse(
        task_id=task_id,
        status="accepted",
        outcome_count=store.count(),
        derived_judgments_count=derived_count,
    )
