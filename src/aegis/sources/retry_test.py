"""Tests for the centralized retry policy."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import httpx
import pytest

from aegis.sources.retry import (
    RetryBudgetExhausted,
    RetryConfig,
    RetryPolicy,
)


def _make_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Create an httpx.HTTPStatusError with the given status code."""
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"{status_code} error", request=request, response=response
    )


@pytest.mark.asyncio
async def test_retry_on_429() -> None:
    """Retry on 429 twice then succeed on third call."""
    config = RetryConfig(base_delay_seconds=0.01, max_delay_seconds=0.1)
    policy = RetryPolicy(config)

    mock_fn = AsyncMock(
        side_effect=[
            _make_status_error(429),
            _make_status_error(429),
            "success",
        ]
    )

    result = await policy.execute(mock_fn)
    assert result == "success"
    assert mock_fn.call_count == 3


@pytest.mark.asyncio
async def test_retry_on_503() -> None:
    """Retry on 503 twice then succeed on third call."""
    config = RetryConfig(base_delay_seconds=0.01, max_delay_seconds=0.1)
    policy = RetryPolicy(config)

    mock_fn = AsyncMock(
        side_effect=[
            _make_status_error(503),
            _make_status_error(503),
            "success",
        ]
    )

    result = await policy.execute(mock_fn)
    assert result == "success"
    assert mock_fn.call_count == 3


@pytest.mark.asyncio
async def test_max_retries_exceeded() -> None:
    """Raise HTTPStatusError after max retries are exhausted."""
    config = RetryConfig(max_retries=3, base_delay_seconds=0.01, max_delay_seconds=0.1)
    policy = RetryPolicy(config)

    mock_fn = AsyncMock(side_effect=_make_status_error(429))

    with pytest.raises(httpx.HTTPStatusError):
        await policy.execute(mock_fn)

    assert mock_fn.call_count == 4  # 1 initial + 3 retries


@pytest.mark.asyncio
async def test_budget_exhaustion() -> None:
    """Raise RetryBudgetExhausted when budget is spent."""
    config = RetryConfig(
        budget_per_window=2,
        base_delay_seconds=0.01,
        max_delay_seconds=0.1,
    )
    policy = RetryPolicy(config)

    mock_fn = AsyncMock(side_effect=_make_status_error(429))

    with pytest.raises(RetryBudgetExhausted):
        await policy.execute(mock_fn)


@pytest.mark.asyncio
async def test_no_retry_on_400() -> None:
    """Non-retryable status codes raise immediately."""
    config = RetryConfig(base_delay_seconds=0.01)
    policy = RetryPolicy(config)

    mock_fn = AsyncMock(side_effect=_make_status_error(400))

    with pytest.raises(httpx.HTTPStatusError):
        await policy.execute(mock_fn)

    assert mock_fn.call_count == 1


@pytest.mark.asyncio
async def test_exponential_backoff_timing() -> None:
    """Verify delays increase exponentially (within tolerance for jitter)."""
    config = RetryConfig(
        max_retries=3,
        base_delay_seconds=0.1,
        max_delay_seconds=10.0,
    )
    policy = RetryPolicy(config)

    timestamps: list[float] = []

    async def tracked_fn() -> str:
        timestamps.append(time.perf_counter())
        if len(timestamps) < 4:
            raise _make_status_error(429)
        return "done"

    result = await policy.execute(tracked_fn)
    assert result == "done"
    assert len(timestamps) == 4

    delays = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]

    # Expected delays: ~0.1s, ~0.2s, ~0.4s (with +/-10% jitter)
    # Use generous tolerance to avoid flaky tests
    assert delays[0] >= 0.05, f"First delay too short: {delays[0]}"
    assert delays[1] >= 0.10, f"Second delay too short: {delays[1]}"
    assert delays[2] >= 0.20, f"Third delay too short: {delays[2]}"

    # Verify exponential growth: each delay should be roughly 2x the previous
    assert delays[1] > delays[0] * 1.3, f"Not exponential: {delays}"
    assert delays[2] > delays[1] * 1.3, f"Not exponential: {delays}"
