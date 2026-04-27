"""Candidate evidence trail API with access-controlled views.

GET /v1/candidates/{uuid}/evidence

Access tiers:
- Self-view (ORCID/NPI verified): full detail -- all artifacts, all scores,
  all integrity decisions, all linkage decisions
- Customer-view (JWT): scoped to artifacts and scores relevant to queries
  the customer has made
- Admin-view: full detail (same as self)

Every access request is audit-logged regardless of tier.
Implements program overview section 15 candidate-transparency promise.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class AccessTier(StrEnum):
    """Access tiers for the candidate evidence trail."""

    self_view = "self_view"
    customer_view = "customer_view"
    admin_view = "admin_view"


class VerificationMethod(StrEnum):
    """Methods of identity verification."""

    orcid_oauth = "orcid_oauth"
    npi_proof = "npi_proof"
    jwt_customer = "jwt_customer"
    jwt_admin = "jwt_admin"


class AccessRequest(BaseModel):
    """An access request for the candidate evidence trail."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    candidate_uuid: str
    requester_id: str
    access_tier: AccessTier
    verification_method: VerificationMethod
    timestamp: datetime
    granted: bool
    denial_reason: str | None


class ArtifactEvidence(BaseModel):
    """Evidence from a single artifact."""

    model_config = ConfigDict(frozen=True)

    artifact_type: str
    identifier: str
    title: str | None
    contribution_to_score: float | None
    source: str
    linked_at: datetime | None


class ScoreEvidence(BaseModel):
    """Evidence for a score component."""

    model_config = ConfigDict(frozen=True)

    component: str
    value: float
    detail: str
    factors: dict[str, float]


class IntegrityEvidence(BaseModel):
    """Evidence from integrity checks."""

    model_config = ConfigDict(frozen=True)

    gate_result: str
    checks_evaluated: int
    discounts: list[dict[str, Any]]
    overrides: list[dict[str, Any]]


class LinkageEvidence(BaseModel):
    """Evidence from identity linkage."""

    model_config = ConfigDict(frozen=True)

    confidence: float
    strong_keys: dict[str, str]
    linked_artifacts_count: int
    name_variants: list[str]


class CandidateEvidenceTrail(BaseModel):
    """Full evidence trail for a candidate (self-view / admin-view)."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    candidate_name: str
    access_tier: AccessTier
    artifacts: list[ArtifactEvidence]
    scores: list[ScoreEvidence]
    integrity: IntegrityEvidence
    linkage: LinkageEvidence
    affiliation_history: list[dict[str, Any]]
    opt_out_status: bool
    contestability_history: list[dict[str, Any]]
    generated_at: datetime


class ScopedEvidenceTrail(BaseModel):
    """Scoped evidence trail for a candidate (customer-view)."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    candidate_name: str
    access_tier: AccessTier
    artifacts: list[ArtifactEvidence]
    scores: list[ScoreEvidence]
    integrity_status: str
    linkage_confidence: float
    generated_at: datetime


class CandidateViewService:
    """Service for generating candidate evidence trails with access control.

    Generates full or scoped evidence trails based on the requester's
    access tier. All access requests are audit-logged.
    """

    def __init__(
        self,
        *,
        audit_log_path: Path | None = None,
    ) -> None:
        self._access_log: list[AccessRequest] = []
        self._audit_log_path = audit_log_path

    def verify_self_access(
        self,
        *,
        candidate_uuid: str,
        orcid: str | None = None,
        npi: str | None = None,
        candidate_strong_keys: dict[str, str] | None = None,
    ) -> AccessRequest:
        """Verify that the requester is the candidate themselves."""
        strong_keys = candidate_strong_keys or {}

        if orcid and strong_keys.get("orcid") == orcid:
            request = AccessRequest(
                request_id=_uuid.uuid4().hex,
                candidate_uuid=candidate_uuid,
                requester_id=orcid,
                access_tier=AccessTier.self_view,
                verification_method=VerificationMethod.orcid_oauth,
                timestamp=datetime.now(tz=UTC),
                granted=True,
                denial_reason=None,
            )
            self._log_access(request)
            return request

        if npi and strong_keys.get("npi") == npi:
            request = AccessRequest(
                request_id=_uuid.uuid4().hex,
                candidate_uuid=candidate_uuid,
                requester_id=npi,
                access_tier=AccessTier.self_view,
                verification_method=VerificationMethod.npi_proof,
                timestamp=datetime.now(tz=UTC),
                granted=True,
                denial_reason=None,
            )
            self._log_access(request)
            return request

        # Denied
        requester_id = orcid or npi or "unknown"
        request = AccessRequest(
            request_id=_uuid.uuid4().hex,
            candidate_uuid=candidate_uuid,
            requester_id=requester_id,
            access_tier=AccessTier.self_view,
            verification_method=(
                VerificationMethod.orcid_oauth
                if orcid
                else VerificationMethod.npi_proof
            ),
            timestamp=datetime.now(tz=UTC),
            granted=False,
            denial_reason=(
                "Verification failed: ORCID/NPI does not match candidate record"
            ),
        )
        self._log_access(request)
        return request

    def verify_customer_access(
        self,
        *,
        candidate_uuid: str,
        customer_id: str,
    ) -> AccessRequest:
        """Verify customer access. Always granted (scoped)."""
        request = AccessRequest(
            request_id=_uuid.uuid4().hex,
            candidate_uuid=candidate_uuid,
            requester_id=customer_id,
            access_tier=AccessTier.customer_view,
            verification_method=VerificationMethod.jwt_customer,
            timestamp=datetime.now(tz=UTC),
            granted=True,
            denial_reason=None,
        )
        self._log_access(request)
        return request

    def verify_admin_access(
        self,
        *,
        candidate_uuid: str,
        admin_id: str,
    ) -> AccessRequest:
        """Verify admin access. Always granted (full)."""
        request = AccessRequest(
            request_id=_uuid.uuid4().hex,
            candidate_uuid=candidate_uuid,
            requester_id=admin_id,
            access_tier=AccessTier.admin_view,
            verification_method=VerificationMethod.jwt_admin,
            timestamp=datetime.now(tz=UTC),
            granted=True,
            denial_reason=None,
        )
        self._log_access(request)
        return request

    def build_full_trail(
        self,
        *,
        candidate_uuid: str,
        candidate_name: str,
        artifacts: list[ArtifactEvidence] | None = None,
        scores: list[ScoreEvidence] | None = None,
        integrity: IntegrityEvidence | None = None,
        linkage: LinkageEvidence | None = None,
        affiliation_history: list[dict[str, Any]] | None = None,
        opt_out_status: bool = False,
        contestability_history: list[dict[str, Any]] | None = None,
        access_tier: AccessTier = AccessTier.self_view,
    ) -> CandidateEvidenceTrail:
        """Build full evidence trail with all details."""
        return CandidateEvidenceTrail(
            candidate_uuid=candidate_uuid,
            candidate_name=candidate_name,
            access_tier=access_tier,
            artifacts=artifacts or [],
            scores=scores or [],
            integrity=integrity
            or IntegrityEvidence(
                gate_result="passed",
                checks_evaluated=0,
                discounts=[],
                overrides=[],
            ),
            linkage=linkage
            or LinkageEvidence(
                confidence=0.0,
                strong_keys={},
                linked_artifacts_count=0,
                name_variants=[],
            ),
            affiliation_history=affiliation_history or [],
            opt_out_status=opt_out_status,
            contestability_history=contestability_history or [],
            generated_at=datetime.now(tz=UTC),
        )

    def build_scoped_trail(
        self,
        *,
        candidate_uuid: str,
        candidate_name: str,
        artifacts: list[ArtifactEvidence] | None = None,
        scores: list[ScoreEvidence] | None = None,
        integrity_status: str = "passed",
        linkage_confidence: float = 0.0,
    ) -> ScopedEvidenceTrail:
        """Build scoped (customer-view) evidence trail with limited details."""
        return ScopedEvidenceTrail(
            candidate_uuid=candidate_uuid,
            candidate_name=candidate_name,
            access_tier=AccessTier.customer_view,
            artifacts=artifacts or [],
            scores=scores or [],
            integrity_status=integrity_status,
            linkage_confidence=linkage_confidence,
            generated_at=datetime.now(tz=UTC),
        )

    def get_access_log(self) -> list[AccessRequest]:
        """Return all access requests logged."""
        return list(self._access_log)

    def _log_access(self, request: AccessRequest) -> None:
        """Log an access request."""
        self._access_log.append(request)
        if self._audit_log_path:
            with open(self._audit_log_path, "a") as f:
                f.write(request.model_dump_json() + "\n")
        logger.info(
            "Evidence access: %s for %s by %s - %s",
            request.access_tier,
            request.candidate_uuid,
            request.requester_id,
            request.granted,
        )
