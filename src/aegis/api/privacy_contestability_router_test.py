"""Integration tests for privacy, contestability, and dispute endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aegis.api.auth import CustomerClaims, create_token
from aegis.api.candidate_view import CandidateViewService
from aegis.api.contestability import ContestabilityQueue
from aegis.api.customer_disputes import DisputeQueue
from aegis.api.privacy_contestability_router import (
    create_privacy_contestability_router,
)


@pytest.fixture()
def app_and_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[FastAPI, str]:
    monkeypatch.setenv("AEGIS_JWT_SECRET", "test-secret")

    view_service = CandidateViewService(audit_log_path=tmp_path / "access.jsonl")
    contest_queue = ContestabilityQueue(db_path=str(tmp_path / "contest.duckdb"))
    dispute_queue = DisputeQueue(db_path=str(tmp_path / "dispute.duckdb"))

    app = FastAPI()
    router = create_privacy_contestability_router(
        candidate_view_service=view_service,
        contest_queue=contest_queue,
        dispute_queue=dispute_queue,
    )
    app.include_router(router)

    token = create_token(
        CustomerClaims(customer_id="test-customer", customer_name="Test Corp"),
        secret="test-secret",
    )

    return app, token


def test_evidence_customer_view(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.get(
        "/v1/candidates/cand-1/evidence",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_tier"] == "customer_view"


def test_evidence_self_view_orcid(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.get(
        "/v1/candidates/cand-1/evidence?orcid=0000-0001-2345-6789",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Self-view verification fails (no candidate store connected), falls back
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_tier"] == "customer_view"


def test_submit_contest(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.post(
        "/v1/candidates/cand-1/contests",
        json={
            "category": "affiliation_error",
            "description": "My affiliation history is incorrect and needs updating.",
            "evidence": {"correct_affiliation": "MIT"},
            "orcid": "0000-0001-2345-6789",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == "elevated"
    assert data["status"] == "submitted"


def test_contest_requires_orcid_or_npi(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.post(
        "/v1/candidates/cand-1/contests",
        json={
            "category": "affiliation_error",
            "description": "My affiliation history is incorrect and needs updating.",
            "evidence": {},
        },
    )
    assert resp.status_code == 400


def test_contest_short_description(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.post(
        "/v1/candidates/cand-1/contests",
        json={
            "category": "affiliation_error",
            "description": "Too short",
            "evidence": {},
            "orcid": "0000-0001-2345-6789",
        },
    )
    assert resp.status_code == 422


def test_list_contests(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    # Submit a contest first
    client.post(
        "/v1/candidates/cand-1/contests",
        json={
            "category": "affiliation_error",
            "description": "My affiliation history is incorrect and needs updating.",
            "evidence": {},
            "orcid": "0000-0001-2345-6789",
        },
    )
    resp = client.get(
        "/v1/candidates/cand-1/contests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


def test_submit_dispute(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.post(
        "/v1/disputes",
        json={
            "candidate_uuid": "cand-1",
            "category": "low_quality_output",
            "description": "Candidate produced low-quality labels on our task.",
            "evidence": {"quality_score": 0.3},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "submitted"


def test_dispute_requires_auth(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.post(
        "/v1/disputes",
        json={
            "candidate_uuid": "cand-1",
            "category": "low_quality_output",
            "description": "Candidate produced low-quality labels on our task.",
            "evidence": {},
        },
    )
    assert resp.status_code in (401, 403)


def test_list_disputes(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    # Submit a dispute first
    client.post(
        "/v1/disputes",
        json={
            "candidate_uuid": "cand-1",
            "category": "low_quality_output",
            "description": "Candidate produced low-quality labels on our task.",
            "evidence": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.get(
        "/v1/disputes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


def test_dispute_short_description(app_and_token: tuple[FastAPI, str]) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.post(
        "/v1/disputes",
        json={
            "candidate_uuid": "cand-1",
            "category": "low_quality_output",
            "description": "Too short",
            "evidence": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
