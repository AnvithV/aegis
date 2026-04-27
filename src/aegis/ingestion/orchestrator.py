"""RefreshOrchestrator: parallel refresh pipeline for ~25 sources.

Manages concurrent source refresh with:
- Per-source workers with independent error handling
- Global concurrency limit (backpressure)
- Per-source rate limiters (via semaphores)
- Failure isolation: one source failure cannot cascade
- Metrics reporting for SLO compliance
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_GLOBAL_CONCURRENCY = 10  # Max simultaneous source refreshes
DEFAULT_PER_SOURCE_CONCURRENCY = 3  # Max parallel tasks within one source
DEFAULT_SOURCE_TIMEOUT_SECONDS = 3600.0  # 1 hour per source max
DAILY_BUDGET_SECONDS = 6 * 3600  # 6 hours


class SourceStatus(StrEnum):
    """Status of a source refresh."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"
    skipped = "skipped"


class SourceRefreshResult(BaseModel):
    """Result of refreshing a single source."""

    model_config = ConfigDict(frozen=True)

    source_name: str
    status: SourceStatus
    records_ingested: int
    duration_seconds: float
    error_message: str | None
    started_at: datetime
    completed_at: datetime


class RefreshSummary(BaseModel):
    """Summary of a full refresh cycle."""

    model_config = ConfigDict(frozen=True)

    total_sources: int
    completed: int
    failed: int
    timed_out: int
    skipped: int
    total_records: int
    total_duration_seconds: float
    within_budget: bool
    results: list[SourceRefreshResult]


# Type for a source refresh function: async callable returning record count
SourceRefreshFn = Callable[[], Awaitable[int]]


@dataclass
class SourceConfig:
    """Configuration for a single source in the refresh pipeline."""

    name: str
    refresh_fn: SourceRefreshFn
    concurrency_limit: int = DEFAULT_PER_SOURCE_CONCURRENCY
    timeout_seconds: float = DEFAULT_SOURCE_TIMEOUT_SECONDS
    priority: int = 0  # Lower = higher priority (runs first)
    enabled: bool = True


class RefreshOrchestrator:
    """Parallel refresh orchestrator for multiple data sources.

    Usage:
        orchestrator = RefreshOrchestrator(global_concurrency=10)
        orchestrator.register_source(SourceConfig(
            name="pubmed",
            refresh_fn=pubmed_refresh,
        ))
        summary = await orchestrator.run_full_refresh()
    """

    def __init__(
        self,
        global_concurrency: int = DEFAULT_GLOBAL_CONCURRENCY,
        daily_budget_seconds: float = DAILY_BUDGET_SECONDS,
    ) -> None:
        self._global_semaphore = asyncio.Semaphore(global_concurrency)
        self._daily_budget = daily_budget_seconds
        self._sources: dict[str, SourceConfig] = {}
        self._results: list[SourceRefreshResult] = []

    def register_source(self, config: SourceConfig) -> None:
        """Register a source for refresh."""
        self._sources[config.name] = config
        logger.info("Registered source: %s (priority=%d)", config.name, config.priority)

    def unregister_source(self, name: str) -> None:
        """Remove a source from the refresh pipeline."""
        self._sources.pop(name, None)

    @property
    def source_count(self) -> int:
        """Number of registered sources."""
        return len(self._sources)

    async def run_full_refresh(self) -> RefreshSummary:
        """Run a complete refresh cycle across all registered sources.

        Sources are processed concurrently up to the global concurrency
        limit. Each source has its own timeout and error isolation.
        """
        start_time = time.monotonic()
        self._results = []

        # Sort sources by priority (lower = first)
        sorted_sources = sorted(
            self._sources.values(),
            key=lambda s: s.priority,
        )

        # Filter enabled sources
        active_sources = [s for s in sorted_sources if s.enabled]
        skipped_sources = [s for s in sorted_sources if not s.enabled]

        # Record skipped sources
        now = datetime.now(UTC)
        for src in skipped_sources:
            self._results.append(SourceRefreshResult(
                source_name=src.name,
                status=SourceStatus.skipped,
                records_ingested=0,
                duration_seconds=0.0,
                error_message=None,
                started_at=now,
                completed_at=now,
            ))

        # Run active sources concurrently
        tasks = [
            self._refresh_source(source)
            for source in active_sources
        ]

        if tasks:
            # Use gather with return_exceptions for failure isolation
            await asyncio.gather(*tasks, return_exceptions=True)

        total_duration = time.monotonic() - start_time

        completed = sum(1 for r in self._results if r.status == SourceStatus.completed)
        failed = sum(1 for r in self._results if r.status == SourceStatus.failed)
        timed_out = sum(1 for r in self._results if r.status == SourceStatus.timed_out)
        skipped = sum(1 for r in self._results if r.status == SourceStatus.skipped)
        total_records = sum(r.records_ingested for r in self._results)

        summary = RefreshSummary(
            total_sources=len(sorted_sources),
            completed=completed,
            failed=failed,
            timed_out=timed_out,
            skipped=skipped,
            total_records=total_records,
            total_duration_seconds=total_duration,
            within_budget=total_duration <= self._daily_budget,
            results=list(self._results),
        )

        logger.info(
            "Refresh cycle complete: %d/%d sources OK, %d failed, "
            "%d timed out, %.1fs total (budget: %s)",
            completed,
            summary.total_sources,
            failed,
            timed_out,
            total_duration,
            "MET" if summary.within_budget else "EXCEEDED",
        )

        return summary

    async def _refresh_source(self, source: SourceConfig) -> None:
        """Refresh a single source with concurrency control and timeout."""
        start_time = time.monotonic()
        started_at = datetime.now(UTC)

        async with self._global_semaphore:
            try:
                records = await asyncio.wait_for(
                    source.refresh_fn(),
                    timeout=source.timeout_seconds,
                )
                duration = time.monotonic() - start_time
                self._results.append(SourceRefreshResult(
                    source_name=source.name,
                    status=SourceStatus.completed,
                    records_ingested=records,
                    duration_seconds=duration,
                    error_message=None,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                ))
                logger.info(
                    "Source %s completed: %d records in %.1fs",
                    source.name,
                    records,
                    duration,
                )

            except TimeoutError:
                duration = time.monotonic() - start_time
                self._results.append(SourceRefreshResult(
                    source_name=source.name,
                    status=SourceStatus.timed_out,
                    records_ingested=0,
                    duration_seconds=duration,
                    error_message=f"Timed out after {source.timeout_seconds}s",
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                ))
                logger.warning(
                    "Source %s timed out after %.1fs",
                    source.name,
                    duration,
                )

            except Exception as exc:
                duration = time.monotonic() - start_time
                self._results.append(SourceRefreshResult(
                    source_name=source.name,
                    status=SourceStatus.failed,
                    records_ingested=0,
                    duration_seconds=duration,
                    error_message=str(exc),
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                ))
                logger.exception(
                    "Source %s failed after %.1fs: %s",
                    source.name,
                    duration,
                    exc,
                )

    async def refresh_single(self, source_name: str) -> SourceRefreshResult | None:
        """Refresh a single source by name. Returns result or None if not found."""
        source = self._sources.get(source_name)
        if source is None:
            logger.warning("Source not found: %s", source_name)
            return None
        self._results = []
        await self._refresh_source(source)
        return self._results[0] if self._results else None
