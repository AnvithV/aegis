"""Tests for token-bucket rate limiting and abuse detection."""

from __future__ import annotations

import time

from aegis.api.rate_limit import (
    AbuseDetector,
    RateLimiterRegistry,
    TokenBucket,
)


def test_token_bucket_allows_within_rate() -> None:
    bucket = TokenBucket(rate=10.0, capacity=10.0)
    for _ in range(10):
        result = bucket.consume(customer_id="test")
        assert result.allowed is True


def test_token_bucket_denies_over_capacity() -> None:
    bucket = TokenBucket(rate=1.0, capacity=2.0)
    r1 = bucket.consume(customer_id="test")
    assert r1.allowed is True
    r2 = bucket.consume(customer_id="test")
    assert r2.allowed is True
    r3 = bucket.consume(customer_id="test")
    assert r3.allowed is False
    assert r3.retry_after_seconds is not None
    assert r3.retry_after_seconds > 0


def test_token_bucket_refills() -> None:
    bucket = TokenBucket(rate=100.0, capacity=1.0)
    r1 = bucket.consume(customer_id="test")
    assert r1.allowed is True
    time.sleep(0.02)
    r2 = bucket.consume(customer_id="test")
    assert r2.allowed is True


def test_abuse_detector_burst() -> None:
    detector = AbuseDetector(burst_threshold=5, window_seconds=10.0)
    alert = None
    for i in range(6):
        alert = detector.record_request(
            customer_id="cust-1", query_hash=f"hash-{i}"
        )
    assert alert is not None
    assert alert.pattern == "high_frequency_burst"


def test_abuse_detector_identical_queries() -> None:
    detector = AbuseDetector(identical_threshold=3)
    alert = None
    for _ in range(4):
        alert = detector.record_request(
            customer_id="cust-1", query_hash="same-hash"
        )
    assert alert is not None
    assert alert.pattern == "repeated_identical"


def test_abuse_detector_no_abuse() -> None:
    detector = AbuseDetector(burst_threshold=100, identical_threshold=10)
    for i in range(3):
        alert = detector.record_request(
            customer_id="cust-1", query_hash=f"hash-{i}"
        )
        assert alert is None


def test_rate_limiter_registry_creates_bucket() -> None:
    registry = RateLimiterRegistry()
    r1 = registry.check(customer_id="cust-1", rate=10.0, capacity=10.0, query_hash="h1")
    r2 = registry.check(customer_id="cust-1", rate=10.0, capacity=10.0, query_hash="h2")
    assert r1.customer_id == "cust-1"
    assert r2.customer_id == "cust-1"


def test_rate_limiter_registry_429_scenario() -> None:
    registry = RateLimiterRegistry()
    r1 = registry.check(customer_id="cust-1", rate=1.0, capacity=1.0, query_hash="h1")
    assert r1.allowed is True
    r2 = registry.check(customer_id="cust-1", rate=1.0, capacity=1.0, query_hash="h2")
    assert r2.allowed is False
    assert r2.retry_after_seconds is not None


def test_rate_limiter_alerts_collected() -> None:
    registry = RateLimiterRegistry()
    registry._detector = AbuseDetector(burst_threshold=2, window_seconds=60.0)
    for i in range(3):
        registry.check(
            customer_id="cust-1", rate=100.0, capacity=100.0, query_hash=f"h-{i}"
        )
    alerts = registry.get_alerts()
    assert len(alerts) == 1
    # Calling again returns empty
    assert registry.get_alerts() == []
