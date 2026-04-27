"""FastAPI router for privacy, contestability, and dispute endpoints.

Mounts:
- GET /v1/candidates/{uuid}/evidence -- Candidate evidence trail
- POST /v1/candidates/{uuid}/contests -- Contestability submissions
- GET /v1/candidates/{uuid}/contests -- List candidate's contests
- POST /v1/disputes -- Customer dispute submissions
- GET /v1/disputes -- List customer's disputes
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator

from aegis.api.auth import TokenPayload, get_current_customer
from aegis.api.candidate_view import (
    AccessTier,
    CandidateEvidenceTrail,
    CandidateViewService,
    ScopedEvidenceTrail,
)
from aegis.api.contestability import (
    ContestabilityQueue,
    ContestCategory,
    ContestSubmission,
    ContestSummary,
)
from aegis.api.customer_disputes import (
    DisputeCategory,
    DisputeQueue,
    DisputeSubmission,
)

logger = logging.getLogger(__name__)


class EvidenceRequest(BaseModel):
    """Request model for evidence trail query params."""

    model_config = ConfigDict(frozen=True)

    orcid: str | None = None
    npi: str | None = None


class ContestRequest(BaseModel):
    """Request model for contest submissions."""

    category: str
    description: str
    evidence: dict[str, Any]
    orcid: str | None = None
    npi: str | None = None

    @field_validator("description")
    @classmethod
    def _check_description_length(cls, v: str) -> str:
        if len(v) < 20:
            msg = "Description must be at least 20 characters"
            raise ValueError(msg)
        return v


class DisputeRequest(BaseModel):
    """Request model for dispute submissions."""

    candidate_uuid: str
    query_id: str | None = None
    category: str
    description: str
    evidence: dict[str, Any]

    @field_validator("description")
    @classmethod
    def _check_description_length(cls, v: str) -> str:
        if len(v) < 20:
            msg = "Description must be at least 20 characters"
            raise ValueError(msg)
        return v


def create_privacy_contestability_router(
    *,
    candidate_view_service: CandidateViewService | None = None,
    contest_queue: ContestabilityQueue | None = None,
    dispute_queue: DisputeQueue | None = None,
) -> APIRouter:
    """Create the privacy/contestability/dispute router."""
    router = APIRouter()
    _view_service = candidate_view_service or CandidateViewService()
    _contest_queue = contest_queue or ContestabilityQueue()
    _dispute_queue = dispute_queue or DisputeQueue()

    @router.get("/v1/candidates/{uuid}/evidence")
    def get_evidence(
        uuid: str,
        orcid: str | None = None,
        npi: str | None = None,
        customer: TokenPayload = Depends(get_current_customer),
    ) -> CandidateEvidenceTrail | ScopedEvidenceTrail:
        """Get candidate evidence trail with access control."""
        # Try self-view if ORCID or NPI provided
        if orcid or npi:
            access_req = _view_service.verify_self_access(
                candidate_uuid=uuid,
                orcid=orcid,
                npi=npi,
                candidate_strong_keys=None,  # No store connected in initial impl
            )
            if access_req.granted:
                return _view_service.build_full_trail(
                    candidate_uuid=uuid,
                    candidate_name="",
                    access_tier=AccessTier.self_view,
                )

        # Fall back to customer-view (scoped)
        _view_service.verify_customer_access(
            candidate_uuid=uuid,
            customer_id=customer.sub,
        )
        return _view_service.build_scoped_trail(
            candidate_uuid=uuid,
            candidate_name="",
        )

    @router.post("/v1/candidates/{uuid}/contests")
    def submit_contest(
        uuid: str,
        body: ContestRequest,
    ) -> ContestSubmission:
        """Submit a contestability request."""
        if not body.orcid and not body.npi:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ORCID or NPI required for verification",
            )

        try:
            category = ContestCategory(body.category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {body.category}",
            )

        verified_via = "orcid" if body.orcid else "npi"
        requester_id = body.orcid or body.npi or ""

        return _contest_queue.submit(
            candidate_uuid=uuid,
            category=category,
            description=body.description,
            evidence=body.evidence,
            verified_via=verified_via,
            requester_id=requester_id,
        )

    @router.get("/v1/candidates/{uuid}/contests")
    def list_contests(
        uuid: str,
        customer: TokenPayload = Depends(get_current_customer),
    ) -> list[ContestSummary]:
        """List contests for a candidate."""
        return _contest_queue.get_by_candidate(uuid)

    @router.post("/v1/disputes")
    def submit_dispute(
        body: DisputeRequest,
        customer: TokenPayload = Depends(get_current_customer),
    ) -> DisputeSubmission:
        """Submit a customer dispute."""
        try:
            category = DisputeCategory(body.category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {body.category}",
            )

        return _dispute_queue.submit(
            customer_id=customer.sub,
            candidate_uuid=body.candidate_uuid,
            category=category,
            description=body.description,
            evidence=body.evidence,
            query_id=body.query_id,
        )

    @router.get("/v1/disputes")
    def list_disputes(
        customer: TokenPayload = Depends(get_current_customer),
    ) -> list[DisputeSubmission]:
        """List disputes for the current customer."""
        return _dispute_queue.get_by_customer(customer.sub)

    return router
