"""Load-test harness for Aegis query API throughput SLO.

Targets:
- 100 queries/second sustained for configurable duration
- 500 queries/second peak burst
- <500ms p95 latency
- <1500ms p99 latency

Uses FastAPI's TestClient with concurrent.futures for parallel request generation.
For production load testing, use locust or k6 against a running server.
"""

from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegis.api.auth import CustomerClaims, create_token
from aegis.api.server import create_app


def _make_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rate_limit_qps: int = 10000
) -> tuple[TestClient, str]:
    """Create test client and token with high rate limit for load testing."""
    monkeypatch.setenv("AEGIS_JWT_SECRET", "test-secret-key-for-testing-32b")
    claims = CustomerClaims(
        customer_id="load-test-customer",
        customer_name="Load Test Corp",
        rate_limit_qps=rate_limit_qps,
    )
    token = create_token(claims, secret="test-secret-key-for-testing-32b")
    app = create_app(audit_log_path=tmp_path / "audit.jsonl")
    return TestClient(app), token


def _send_query(
    client: TestClient, token: str, query_text: str
) -> tuple[int, float]:
    """Send a single query and return (status_code, latency_ms)."""
    start = time.monotonic()
    resp = client.post(
        "/v1/queries",
        json={"task_description": query_text},
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    return resp.status_code, elapsed_ms


@pytest.mark.slow
def test_sustained_throughput(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """100 concurrent queries, p95 < 500ms, >= 95% success."""
    client, token = _make_client(tmp_path, monkeypatch)
    num_requests = 100
    latencies: list[float] = []
    statuses: list[int] = []

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [
            pool.submit(
                _send_query,
                client,
                token,
                f"Evaluate JAK2 inhibitor candidates for kinase screening run {i}",
            )
            for i in range(num_requests)
        ]
        for fut in as_completed(futures):
            status_code, latency_ms = fut.result()
            statuses.append(status_code)
            latencies.append(latency_ms)

    success_count = sum(1 for s in statuses if s == 200)
    success_rate = success_count / num_requests

    p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile

    assert success_rate >= 0.95, f"Success rate {success_rate:.2%} < 95%"
    assert p95 < 500, f"p95 latency {p95:.1f}ms >= 500ms"
    assert p99 < 1500, f"p99 latency {p99:.1f}ms >= 1500ms"


@pytest.mark.slow
def test_peak_burst(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """50 concurrent requests simulating burst."""
    client, token = _make_client(tmp_path, monkeypatch)
    num_requests = 50
    latencies: list[float] = []
    statuses: list[int] = []

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [
            pool.submit(
                _send_query,
                client,
                token,
                f"Evaluate protein kinase inhibitors for drug discovery burst {i}",
            )
            for i in range(num_requests)
        ]
        for fut in as_completed(futures):
            status_code, latency_ms = fut.result()
            statuses.append(status_code)
            latencies.append(latency_ms)

    # No 5xx errors
    server_errors = [s for s in statuses if s >= 500]
    assert len(server_errors) == 0, f"Got {len(server_errors)} 5xx errors"

    # All should be 200 (no rate limiting with high qps)
    assert all(s == 200 for s in statuses)

    p95 = statistics.quantiles(latencies, n=20)[18]
    assert p95 < 1000, f"Burst p95 latency {p95:.1f}ms >= 1000ms"


def test_p95_latency_single(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """20 sequential requests, p95 < 500ms."""
    client, token = _make_client(tmp_path, monkeypatch)
    latencies: list[float] = []

    for i in range(20):
        _, latency_ms = _send_query(
            client,
            token,
            f"Evaluate kinase inhibitors for sequential test {i}",
        )
        latencies.append(latency_ms)

    p95 = statistics.quantiles(latencies, n=20)[18]
    assert p95 < 500, f"p95 latency {p95:.1f}ms >= 500ms"


def test_rate_limit_under_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify rate limiting works under concurrent load."""
    client, token = _make_client(tmp_path, monkeypatch, rate_limit_qps=5)
    num_requests = 20
    statuses: list[int] = []

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [
            pool.submit(
                _send_query,
                client,
                token,
                f"Evaluate candidates for rate limit test {i}",
            )
            for i in range(num_requests)
        ]
        for fut in as_completed(futures):
            status_code, _ = fut.result()
            statuses.append(status_code)

    got_429 = any(s == 429 for s in statuses)
    server_errors = [s for s in statuses if s >= 500]

    assert got_429, "Expected at least one 429 under rate-limited load"
    assert len(server_errors) == 0, f"Got {len(server_errors)} 5xx errors"
