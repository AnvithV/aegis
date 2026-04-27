"""Tests for the RefreshOrchestrator."""

from __future__ import annotations

import asyncio

import pytest

from aegis.ingestion.orchestrator import (
    RefreshOrchestrator,
    SourceConfig,
    SourceStatus,
)


def test_register_source() -> None:
    """Register 3 sources, verify source_count == 3."""
    orch = RefreshOrchestrator()

    async def fake() -> int:
        return 0

    orch.register_source(SourceConfig(name="a", refresh_fn=fake))
    orch.register_source(SourceConfig(name="b", refresh_fn=fake))
    orch.register_source(SourceConfig(name="c", refresh_fn=fake))
    assert orch.source_count == 3


def test_unregister_source() -> None:
    """Register then unregister, verify source_count decrements."""
    orch = RefreshOrchestrator()

    async def fake() -> int:
        return 0

    orch.register_source(SourceConfig(name="a", refresh_fn=fake))
    orch.register_source(SourceConfig(name="b", refresh_fn=fake))
    assert orch.source_count == 2
    orch.unregister_source("a")
    assert orch.source_count == 1


@pytest.mark.asyncio
async def test_run_full_refresh_all_succeed() -> None:
    """Register 3 sources returning 100 each. Verify completed=3, total_records=300."""
    orch = RefreshOrchestrator()

    async def fake() -> int:
        return 100

    orch.register_source(SourceConfig(name="a", refresh_fn=fake))
    orch.register_source(SourceConfig(name="b", refresh_fn=fake))
    orch.register_source(SourceConfig(name="c", refresh_fn=fake))

    summary = await orch.run_full_refresh()
    assert summary.completed == 3
    assert summary.failed == 0
    assert summary.total_records == 300
    assert summary.total_sources == 3


@pytest.mark.asyncio
async def test_failure_isolation() -> None:
    """One source raises, others complete. Verify completed=2, failed=1."""
    orch = RefreshOrchestrator()

    async def fail() -> int:
        msg = "source error"
        raise RuntimeError(msg)

    async def succeed() -> int:
        return 50

    orch.register_source(SourceConfig(name="bad", refresh_fn=fail))
    orch.register_source(SourceConfig(name="good1", refresh_fn=succeed))
    orch.register_source(SourceConfig(name="good2", refresh_fn=succeed))

    summary = await orch.run_full_refresh()
    assert summary.completed == 2
    assert summary.failed == 1
    assert summary.total_records == 100


@pytest.mark.asyncio
async def test_timeout_isolation() -> None:
    """One source times out, other completes. Verify timed_out=1, completed=1."""
    orch = RefreshOrchestrator()

    async def slow() -> int:
        await asyncio.sleep(10)
        return 0

    async def fast() -> int:
        return 25

    orch.register_source(SourceConfig(
        name="slow", refresh_fn=slow, timeout_seconds=0.1,
    ))
    orch.register_source(SourceConfig(name="fast", refresh_fn=fast))

    summary = await orch.run_full_refresh()
    assert summary.timed_out == 1
    assert summary.completed == 1


@pytest.mark.asyncio
async def test_skipped_sources() -> None:
    """Register a source with enabled=False. Verify skipped=1."""
    orch = RefreshOrchestrator()

    async def fake() -> int:
        return 10

    orch.register_source(SourceConfig(name="active", refresh_fn=fake, enabled=True))
    orch.register_source(SourceConfig(name="disabled", refresh_fn=fake, enabled=False))

    summary = await orch.run_full_refresh()
    assert summary.skipped == 1
    assert summary.completed == 1
    assert summary.total_sources == 2


@pytest.mark.asyncio
async def test_priority_ordering() -> None:
    """Register sources with priorities 2, 0, 1. Track call order."""
    call_order: list[str] = []

    async def make_fn(name: str) -> int:
        call_order.append(name)
        return 1

    orch = RefreshOrchestrator(global_concurrency=1)
    orch.register_source(SourceConfig(
        name="low", refresh_fn=lambda: make_fn("low"), priority=2,
    ))
    orch.register_source(SourceConfig(
        name="high", refresh_fn=lambda: make_fn("high"), priority=0,
    ))
    orch.register_source(SourceConfig(
        name="mid", refresh_fn=lambda: make_fn("mid"), priority=1,
    ))

    await orch.run_full_refresh()
    # With concurrency=1, sources run sequentially in priority order
    assert call_order == ["high", "mid", "low"]


@pytest.mark.asyncio
async def test_global_concurrency_limit() -> None:
    """Register 5 sources with global_concurrency=2. Verify max concurrent <= 2."""
    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def tracked() -> int:
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            if current_concurrent > max_concurrent:
                max_concurrent = current_concurrent
        await asyncio.sleep(0.05)
        async with lock:
            current_concurrent -= 1
        return 10

    orch = RefreshOrchestrator(global_concurrency=2)
    for i in range(5):
        orch.register_source(SourceConfig(name=f"src-{i}", refresh_fn=tracked))

    await orch.run_full_refresh()
    assert max_concurrent <= 2


@pytest.mark.asyncio
async def test_within_budget() -> None:
    """Register sources that complete quickly. Verify within_budget=True."""
    orch = RefreshOrchestrator()

    async def fast() -> int:
        return 1

    orch.register_source(SourceConfig(name="quick", refresh_fn=fast))
    summary = await orch.run_full_refresh()
    assert summary.within_budget is True


@pytest.mark.asyncio
async def test_refresh_single() -> None:
    """Register a source, call refresh_single, verify result."""
    orch = RefreshOrchestrator()

    async def fake() -> int:
        return 42

    orch.register_source(SourceConfig(name="test", refresh_fn=fake))
    result = await orch.refresh_single("test")
    assert result is not None
    assert result.source_name == "test"
    assert result.status == SourceStatus.completed
    assert result.records_ingested == 42


@pytest.mark.asyncio
async def test_refresh_single_not_found() -> None:
    """Call refresh_single with nonexistent name, verify None."""
    orch = RefreshOrchestrator()
    result = await orch.refresh_single("nonexistent")
    assert result is None


def test_source_status_enum() -> None:
    """Verify all expected SourceStatus values exist."""
    assert SourceStatus.pending == "pending"
    assert SourceStatus.running == "running"
    assert SourceStatus.completed == "completed"
    assert SourceStatus.failed == "failed"
    assert SourceStatus.timed_out == "timed_out"
    assert SourceStatus.skipped == "skipped"


def test_source_config_defaults() -> None:
    """Create SourceConfig with minimal args, verify defaults."""
    async def fake() -> int:
        return 0

    config = SourceConfig(name="test", refresh_fn=fake)
    assert config.name == "test"
    assert config.concurrency_limit == 3
    assert config.timeout_seconds == 3600.0
    assert config.priority == 0
    assert config.enabled is True
