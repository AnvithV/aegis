"""Integration tests for the Aegis query API server."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegis.api.auth import CustomerClaims, create_token
from aegis.api.server import create_app
from aegis.api.staleness import StalenessCircuitBreaker


def _make_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kwargs: object
) -> tuple[TestClient, str]:
    """Create a test client and JWT token."""
    monkeypatch.setenv("AEGIS_JWT_SECRET", "test-secret-key-for-testing-32b")
    claims = CustomerClaims(
        customer_id="test-customer",
        customer_name="Test Corp",
        **kwargs,  # type: ignore[arg-type]
    )
    token = create_token(claims, secret="test-secret-key-for-testing-32b")
    app = create_app(audit_log_path=tmp_path / "audit.jsonl")
    return TestClient(app), token


def test_health_check() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_query_requires_auth() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/v1/queries",
        json={"task_description": "Evaluate JAK2 inhibitor candidates for screening"},
    )
    assert resp.status_code in (401, 403)


def test_query_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_JWT_SECRET", "test-secret-key-for-testing-32b")
    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/v1/queries",
        json={"task_description": "Evaluate JAK2 inhibitor candidates for screening"},
        headers={"Authorization": "Bearer garbage-token-value"},
    )
    assert resp.status_code == 401


def test_query_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = _make_client(tmp_path, monkeypatch)
    resp = client.post(
        "/v1/queries",
        json={
            "task_description": (
                "Evaluate JAK2 inhibitor candidates"
                " for kinase screening"
            ),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "query_id" in data
    assert "candidates" in data
    assert "expansion_info" in data
    assert "weight_version" in data


def test_query_with_mesh_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = _make_client(tmp_path, monkeypatch)
    resp = client.post(
        "/v1/queries",
        json={
            "task_description": "Evaluate JAK2 inhibitor candidates for screening",
            "mesh_override": ["Neoplasms"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expansion_info"]["expansion_method"] == "override"


def test_query_rate_limited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = _make_client(
        tmp_path, monkeypatch, rate_limit_qps=1
    )
    got_429 = False
    for _ in range(5):
        resp = client.post(
            "/v1/queries",
            json={
                "task_description": (
                    "Evaluate JAK2 inhibitor candidates"
                    " for screening"
                ),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 429:
            got_429 = True
            assert "Retry-After" in resp.headers
            break
    assert got_429, "Expected at least one 429 response"


def test_query_cohort_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = _make_client(
        tmp_path, monkeypatch, allowed_cohorts=["translational"]
    )
    resp = client.post(
        "/v1/queries",
        json={
            "task_description": "Evaluate JAK2 inhibitor candidates for screening",
            "cohort_filter": "drug_discovery",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_query_short_description(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = _make_client(tmp_path, monkeypatch)
    resp = client.post(
        "/v1/queries",
        json={"task_description": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_staleness_warnings_included(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AEGIS_JWT_SECRET", "test-secret-key-for-testing-32b")
    # Circuit breaker with no refreshes -> all stale
    breaker = StalenessCircuitBreaker()
    app = create_app(
        audit_log_path=tmp_path / "audit.jsonl",
        circuit_breaker=breaker,
    )
    client = TestClient(app)
    claims = CustomerClaims(
        customer_id="test-customer", customer_name="Test Corp"
    )
    token = create_token(claims, secret="test-secret-key-for-testing-32b")
    resp = client.post(
        "/v1/queries",
        json={"task_description": "Evaluate JAK2 inhibitor candidates for screening"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["staleness_warnings"]) > 0


def test_audit_log_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, token = _make_client(tmp_path, monkeypatch)
    resp = client.post(
        "/v1/queries",
        json={"task_description": "Evaluate JAK2 inhibitor candidates for screening"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    audit_path = tmp_path / "audit.jsonl"
    assert audit_path.exists()
    lines = audit_path.read_text().strip().split("\n")
    assert len(lines) >= 1
    entry = json.loads(lines[0])
    assert entry["customer_id"] == "test-customer"
    assert "JAK2" in entry["query_text"]
