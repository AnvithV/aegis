"""Centralized retry policy with exponential back-off and per-API budget."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryBudgetExhausted(Exception):  # noqa: N818
    """Raised when the per-API retry budget is exhausted."""


class RetryConfig(BaseModel):
    """Configuration for the retry policy."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    budget_per_window: int = 100
    budget_window_seconds: float = 300.0
    retryable_status_codes: tuple[int, ...] = (429, 503)


class RetryBudget:
    """Tracks retry count within a sliding time window."""

    def __init__(self, config: RetryConfig) -> None:
        self._config = config
        self._timestamps: list[float] = []

    def _prune(self) -> None:
        """Remove timestamps outside the current window."""
        cutoff = time.monotonic() - self._config.budget_window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    def consume(self) -> bool:
        """Return True if a retry is allowed (budget not exhausted)."""
        self._prune()
        if len(self._timestamps) >= self._config.budget_per_window:
            return False
        self._timestamps.append(time.monotonic())
        return True

    def remaining(self) -> int:
        """Return how many retries remain in the current window."""
        self._prune()
        return max(0, self._config.budget_per_window - len(self._timestamps))


class RetryPolicy:
    """Retry wrapper with exponential back-off and budget enforcement."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        self._config = config or RetryConfig()
        self._budget = RetryBudget(self._config)

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Call *func* with retries on transient HTTP errors."""
        import asyncio

        last_exc: httpx.HTTPStatusError | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in self._config.retryable_status_codes:
                    raise

                last_exc = exc

                if attempt >= self._config.max_retries:
                    raise

                if not self._budget.consume():
                    logger.warning(
                        "Retry budget exhausted (%d/%d in %.0fs window)",
                        self._config.budget_per_window,
                        self._config.budget_per_window,
                        self._config.budget_window_seconds,
                    )
                    raise RetryBudgetExhausted(
                        f"Retry budget of {self._config.budget_per_window} "
                        f"exhausted within {self._config.budget_window_seconds}s window"
                    ) from exc

                delay = min(
                    self._config.base_delay_seconds * (2**attempt),
                    self._config.max_delay_seconds,
                )
                jitter = delay * 0.1 * (2 * random.random() - 1)  # noqa: S311
                delay += jitter

                logger.info(
                    "Retry attempt %d/%d after %.2fs (status %d)",
                    attempt + 1,
                    self._config.max_retries,
                    delay,
                    exc.response.status_code,
                )

                await asyncio.sleep(delay)

        # This should be unreachable, but satisfies the type checker.
        assert last_exc is not None  # noqa: S101
        raise last_exc
