"""Tests for candidate evidence trail API."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis.api.candidate_view import (
    AccessRequest,
    AccessTier,
    ArtifactEvidence,
    CandidateEvidenceTrail,
    CandidateViewService,
    IntegrityEvidence,
    LinkageEvidence,
    ScoreEvidence,
    VerificationMethod,
)


def test_self_access_orcid_match() -> None:
    svc = CandidateViewService()
    req = svc.verify_self_access(
        candidate_uuid="cand-1",
        orcid="0000-0001-2345-6789",
        candidate_strong_keys={"orcid": "0000-0001-2345-6789"},
    )
    assert req.granted is True
    assert req.access_tier == AccessTier.self_view
    assert req.verification_method == VerificationMethod.orcid_oauth


def test_self_access_npi_match() -> None:
    svc = CandidateViewService()
    req = svc.verify_self_access(
        candidate_uuid="cand-1",
        npi="1234567890",
        candidate_strong_keys={"npi": "1234567890"},
    )
    assert req.granted is True
    assert req.access_tier == AccessTier.self_view
    assert req.verification_method == VerificationMethod.npi_proof


def test_self_access_denied_no_match() -> None:
    svc = CandidateViewService()
    req = svc.verify_self_access(
        candidate_uuid="cand-1",
        orcid="0000-0001-9999-9999",
        candidate_strong_keys={"orcid": "0000-0001-2345-6789"},
    )
    assert req.granted is False
    assert req.denial_reason is not None


def test_self_access_denied_no_credentials() -> None:
    svc = CandidateViewService()
    req = svc.verify_self_access(
        candidate_uuid="cand-1",
        candidate_strong_keys={"orcid": "0000-0001-2345-6789"},
    )
    assert req.granted is False


def test_customer_access_always_granted() -> None:
    svc = CandidateViewService()
    req = svc.verify_customer_access(
        candidate_uuid="cand-1",
        customer_id="customer-abc",
    )
    assert req.granted is True
    assert req.access_tier == AccessTier.customer_view


def test_admin_access_always_granted() -> None:
    svc = CandidateViewService()
    req = svc.verify_admin_access(
        candidate_uuid="cand-1",
        admin_id="admin-1",
    )
    assert req.granted is True
    assert req.access_tier == AccessTier.admin_view


def test_build_full_trail() -> None:
    svc = CandidateViewService()
    artifact = ArtifactEvidence(
        artifact_type="pmid",
        identifier="12345678",
        title="Test Paper",
        contribution_to_score=0.5,
        source="pubmed",
        linked_at=datetime.now(tz=UTC),
    )
    score = ScoreEvidence(
        component="quality_prior",
        value=0.85,
        detail="High quality",
        factors={"F1": 0.9, "F2": 0.8},
    )
    integrity = IntegrityEvidence(
        gate_result="passed",
        checks_evaluated=5,
        discounts=[],
        overrides=[],
    )
    linkage = LinkageEvidence(
        confidence=0.95,
        strong_keys={"orcid": "0000-0001-2345-6789"},
        linked_artifacts_count=10,
        name_variants=["J Smith", "Jane Smith"],
    )
    trail = svc.build_full_trail(
        candidate_uuid="cand-1",
        candidate_name="Jane Smith",
        artifacts=[artifact],
        scores=[score],
        integrity=integrity,
        linkage=linkage,
        affiliation_history=[{"org": "MIT", "start": "2020"}],
        contestability_history=[],
    )
    assert trail.candidate_uuid == "cand-1"
    assert len(trail.artifacts) == 1
    assert len(trail.scores) == 1
    assert trail.integrity.gate_result == "passed"
    assert trail.linkage.confidence == 0.95


def test_build_scoped_trail() -> None:
    svc = CandidateViewService()
    trail = svc.build_scoped_trail(
        candidate_uuid="cand-1",
        candidate_name="Jane Smith",
        integrity_status="passed",
        linkage_confidence=0.95,
    )
    assert trail.access_tier == AccessTier.customer_view
    assert trail.integrity_status == "passed"
    assert trail.linkage_confidence == 0.95
    # Scoped trail should not have detailed integrity/linkage
    assert not hasattr(trail, "integrity")
    assert not hasattr(trail, "linkage")


def test_access_log_recorded() -> None:
    svc = CandidateViewService()
    svc.verify_self_access(
        candidate_uuid="cand-1",
        orcid="0000-0001-2345-6789",
        candidate_strong_keys={"orcid": "0000-0001-2345-6789"},
    )
    svc.verify_customer_access(candidate_uuid="cand-2", customer_id="cust-1")
    svc.verify_admin_access(candidate_uuid="cand-3", admin_id="admin-1")
    log = svc.get_access_log()
    assert len(log) == 3


def test_access_log_persisted(tmp_path: Path) -> None:
    audit_path = tmp_path / "access.jsonl"
    svc = CandidateViewService(audit_log_path=audit_path)
    svc.verify_self_access(
        candidate_uuid="cand-1",
        orcid="0000-0001-2345-6789",
        candidate_strong_keys={"orcid": "0000-0001-2345-6789"},
    )
    assert audit_path.exists()
    lines = audit_path.read_text().strip().split("\n")
    assert len(lines) == 1


def test_access_request_model() -> None:
    req = AccessRequest(
        request_id="abc123",
        candidate_uuid="cand-1",
        requester_id="orcid-123",
        access_tier=AccessTier.self_view,
        verification_method=VerificationMethod.orcid_oauth,
        timestamp=datetime.now(tz=UTC),
        granted=True,
        denial_reason=None,
    )
    with pytest.raises(Exception):  # noqa: B017
        req.granted = False


def test_full_trail_model() -> None:
    trail = CandidateEvidenceTrail(
        candidate_uuid="cand-1",
        candidate_name="Jane Smith",
        access_tier=AccessTier.self_view,
        artifacts=[],
        scores=[],
        integrity=IntegrityEvidence(
            gate_result="passed",
            checks_evaluated=0,
            discounts=[],
            overrides=[],
        ),
        linkage=LinkageEvidence(
            confidence=0.0,
            strong_keys={},
            linked_artifacts_count=0,
            name_variants=[],
        ),
        affiliation_history=[],
        opt_out_status=False,
        contestability_history=[],
        generated_at=datetime.now(tz=UTC),
    )
    with pytest.raises(Exception):  # noqa: B017
        trail.candidate_uuid = "cand-2"
