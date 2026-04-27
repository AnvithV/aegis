"""Tests for the feedback API endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import aegis.api.feedback as feedback_mod


@pytest.fixture()
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(feedback_mod.router)
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _valid_payload(
    *,
    n_candidates: int = 3,
    fleiss_kappa: float | None = 0.7,
    accept_rate: float | None = 0.85,
    consensus_rate: float | None = 0.9,
    metadata: dict[str, str] | None = None,
) -> dict[str, object]:
    candidates = [
        {
            "candidate_uuid": f"cand-{i}",
            "candidate_rank": i + 1,
            "quality_prior_score": 0.9 - i * 0.2,
            "topical_fit_score": 0.8 - i * 0.1,
            "recency_score": 0.7 - i * 0.1,
        }
        for i in range(n_candidates)
    ]
    return {
        "query_specialty": "translational",
        "query_mesh_terms": ["Neoplasms", "Drug Therapy"],
        "candidates": candidates,
        "fleiss_kappa": fleiss_kappa,
        "accept_rate": accept_rate,
        "consensus_rate": consensus_rate,
        "metadata": metadata or {},
    }


def test_submit_outcome_success(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST a valid outcome with 3 candidates returns 201."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    resp = client.post(
        "/v1/feedback/tasks/task-001/outcomes",
        json=_valid_payload(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["task_id"] == "task-001"
    assert data["status"] == "accepted"
    assert data["derived_judgments_count"] == 2
    assert data["outcome_count"] == 1


def test_submit_outcome_phi_rejection(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST with PHI metadata key 'ssn' returns 422."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    payload = _valid_payload(metadata={"ssn": "123-45-6789"})
    resp = client.post(
        "/v1/feedback/tasks/task-002/outcomes",
        json=payload,
    )
    assert resp.status_code == 422


def test_submit_outcome_phi_case_insensitive(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST with PHI metadata key 'Patient_Name' (mixed case) returns 422."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    payload = _valid_payload(metadata={"Patient_Name": "test"})
    resp = client.post(
        "/v1/feedback/tasks/task-003/outcomes",
        json=payload,
    )
    assert resp.status_code == 422


def test_submit_outcome_kappa_out_of_range(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST with fleiss_kappa=2.0 returns 422."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    payload = _valid_payload(fleiss_kappa=2.0)
    resp = client.post(
        "/v1/feedback/tasks/task-004/outcomes",
        json=payload,
    )
    assert resp.status_code == 422


def test_submit_outcome_accept_rate_out_of_range(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST with accept_rate=-0.1 returns 422."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    payload = _valid_payload(accept_rate=-0.1)
    resp = client.post(
        "/v1/feedback/tasks/task-005/outcomes",
        json=payload,
    )
    assert resp.status_code == 422


def test_submit_outcome_none_metrics(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST with all metrics as None returns 201."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    payload = _valid_payload(
        fleiss_kappa=None, accept_rate=None, consensus_rate=None
    )
    resp = client.post(
        "/v1/feedback/tasks/task-006/outcomes",
        json=payload,
    )
    assert resp.status_code == 201


def test_submit_outcome_single_candidate(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST with 1 candidate returns 201 with derived_judgments_count=0."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    payload = _valid_payload(n_candidates=1)
    resp = client.post(
        "/v1/feedback/tasks/task-007/outcomes",
        json=payload,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["derived_judgments_count"] == 0


def test_submit_multiple_outcomes(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST two outcomes; second response has outcome_count=2."""
    monkeypatch.setattr(
        feedback_mod,
        "_default_store_path",
        tmp_path / "test_outcomes.jsonl",
    )
    resp1 = client.post(
        "/v1/feedback/tasks/task-008a/outcomes",
        json=_valid_payload(),
    )
    assert resp1.status_code == 201
    assert resp1.json()["outcome_count"] == 1

    resp2 = client.post(
        "/v1/feedback/tasks/task-008b/outcomes",
        json=_valid_payload(),
    )
    assert resp2.status_code == 201
    assert resp2.json()["outcome_count"] == 2
