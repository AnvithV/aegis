"""Feedback API: task outcomes and per-candidate judgments."""

from __future__ import annotations

import json as json_mod
import logging
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, field_validator

from aegis.learning.downstream_quality import (
    DownstreamQualityStore,
    TaskOutcome,
    TaskOutcomeCandidate,
)
from aegis.learning.plackett_luce import JudgmentRecord

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


# Module-level store paths
_default_store_path = Path("data/aegis/downstream_quality.jsonl")
_default_judgments_path = Path("data/aegis/candidate_judgments.jsonl")


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


# ---------------------------------------------------------------------------
# Per-candidate judgments (thumbs up / X mark)
# ---------------------------------------------------------------------------


class CandidateJudgment(StrEnum):
    """Judgment type for a single candidate."""

    relevant = "relevant"
    irrelevant = "irrelevant"


class CandidateJudgmentRequest(BaseModel):
    """Request to judge a single candidate within a query."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    candidate_uuid: str
    judgment: CandidateJudgment
    score_components: dict[str, float]


class CandidateJudgmentResponse(BaseModel):
    """Response after recording a candidate judgment."""

    model_config = ConfigDict(frozen=True)

    status: str
    derived_pairs: int


def _load_judgments(path: Path) -> list[dict]:  # type: ignore[type-arg]
    """Load all candidate judgments from JSONL."""
    if not path.exists():
        return []
    results = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                results.append(json_mod.loads(stripped))
    return results


def _judgments_for_query(path: Path, query_id: str) -> list[dict]:  # type: ignore[type-arg]
    """Get all judgments for a specific query."""
    return [j for j in _load_judgments(path) if j.get("query_id") == query_id]


def derive_pairwise_from_judgments(
    judgments: list[dict],  # type: ignore[type-arg]
) -> list[JudgmentRecord]:
    """Derive pairwise JudgmentRecords from per-candidate judgments.

    Every irrelevant candidate generates a pair against every relevant candidate.
    """
    relevant = [j for j in judgments if j["judgment"] == "relevant"]
    irrelevant = [j for j in judgments if j["judgment"] == "irrelevant"]

    pairs: list[JudgmentRecord] = []
    for winner in relevant:
        ws = winner["score_components"]
        for loser in irrelevant:
            ls = loser["score_components"]
            pairs.append(
                JudgmentRecord(
                    winner_scores={
                        "quality_prior": ws.get("Q", ws.get("quality_prior", 0.5)),
                        "topical_fit": ws.get("C", ws.get("topical_fit", 0.5)),
                        "recency": ws.get("R", ws.get("recency", 0.5)),
                    },
                    loser_scores={
                        "quality_prior": ls.get("Q", ls.get("quality_prior", 0.5)),
                        "topical_fit": ls.get("C", ls.get("topical_fit", 0.5)),
                        "recency": ls.get("R", ls.get("recency", 0.5)),
                    },
                )
            )
    return pairs


@router.post(
    "/candidates/judge",
    response_model=CandidateJudgmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def judge_candidate(body: CandidateJudgmentRequest) -> CandidateJudgmentResponse:
    """Record a thumbs-up (relevant) or X (irrelevant) judgment for a candidate."""
    path = _default_judgments_path
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "query_id": body.query_id,
        "candidate_uuid": body.candidate_uuid,
        "judgment": body.judgment.value,
        "score_components": body.score_components,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with open(path, mode="a", encoding="utf-8") as fh:
        fh.write(json_mod.dumps(record) + "\n")

    # Derive pairs from all judgments for this query
    query_judgments = _judgments_for_query(path, body.query_id)
    pairs = derive_pairwise_from_judgments(query_judgments)

    return CandidateJudgmentResponse(
        status="accepted",
        derived_pairs=len(pairs),
    )


@router.get("/candidates/judgments/{query_id}")
def get_candidate_judgments(query_id: str) -> dict:
    """Get all candidate judgments for a query."""
    judgments = _judgments_for_query(_default_judgments_path, query_id)
    return {
        "query_id": query_id,
        "judgments": {j["candidate_uuid"]: j["judgment"] for j in judgments},
    }
