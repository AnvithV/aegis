"""Tests for JWT authentication module."""

from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from aegis.api.auth import (
    CustomerClaims,
    create_token,
    decode_token,
    require_cohort_access,
)


def test_create_and_decode_token() -> None:
    claims = CustomerClaims(customer_id="cust-1", customer_name="Test Corp")
    token = create_token(claims, secret="test-secret")
    payload = decode_token(token, secret="test-secret")
    assert payload.sub == "cust-1"
    assert payload.customer_name == "Test Corp"


def test_expired_token() -> None:
    claims = CustomerClaims(customer_id="cust-1", customer_name="Test Corp")
    token = create_token(claims, secret="test-secret", expiry_hours=0)
    # Token with 0-hour expiry is effectively expired immediately or very soon.
    # Sleep briefly to ensure expiry.
    time.sleep(0.1)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, secret="test-secret")
    assert exc_info.value.status_code == 401


def test_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        decode_token("this-is-garbage", secret="test-secret")
    assert exc_info.value.status_code == 401


def test_wrong_secret() -> None:
    claims = CustomerClaims(customer_id="cust-1", customer_name="Test Corp")
    token = create_token(claims, secret="secret-a")
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, secret="secret-b")
    assert exc_info.value.status_code == 401


def test_cohort_restriction_allowed() -> None:
    claims = CustomerClaims(
        customer_id="cust-1",
        customer_name="Test Corp",
        allowed_cohorts=["translational"],
    )
    token = create_token(claims, secret="test-secret")
    payload = decode_token(token, secret="test-secret")
    # Should not raise
    require_cohort_access(payload, "translational")


def test_cohort_restriction_denied() -> None:
    claims = CustomerClaims(
        customer_id="cust-1",
        customer_name="Test Corp",
        allowed_cohorts=["translational"],
    )
    token = create_token(claims, secret="test-secret")
    payload = decode_token(token, secret="test-secret")
    with pytest.raises(HTTPException) as exc_info:
        require_cohort_access(payload, "drug_discovery")
    assert exc_info.value.status_code == 403


def test_cohort_restriction_none_allows_all() -> None:
    claims = CustomerClaims(
        customer_id="cust-1",
        customer_name="Test Corp",
        allowed_cohorts=None,
    )
    token = create_token(claims, secret="test-secret")
    payload = decode_token(token, secret="test-secret")
    # Should not raise for any cohort
    require_cohort_access(payload, "anything")


def test_customer_claims_defaults() -> None:
    claims = CustomerClaims(customer_id="cust-1", customer_name="Test Corp")
    assert claims.rate_limit_qps == 10
    assert claims.llm_budget_cents == 1000
    assert claims.allowed_cohorts is None


def test_token_contains_all_claims() -> None:
    claims = CustomerClaims(
        customer_id="cust-2",
        customer_name="Pharma Inc",
        allowed_cohorts=["translational", "drug_discovery"],
        rate_limit_qps=50,
        llm_budget_cents=5000,
    )
    token = create_token(claims, secret="test-secret")
    payload = decode_token(token, secret="test-secret")
    assert payload.sub == "cust-2"
    assert payload.customer_name == "Pharma Inc"
    assert payload.allowed_cohorts == ["translational", "drug_discovery"]
    assert payload.rate_limit_qps == 50
    assert payload.llm_budget_cents == 5000
