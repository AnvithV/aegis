"""Tests for IntegrityEventDispatcher message bus."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest

from aegis.ingestion.event_dispatcher import (
    IntegrityActionType,
    IntegrityEvent,
    IntegrityEventDispatcher,
    IntegritySeverity,
    IntegritySource,
)


def _make_event(**overrides: object) -> IntegrityEvent:
    """Create a test IntegrityEvent with sensible defaults."""
    defaults: dict[str, object] = {
        "event_id": str(uuid.uuid4()),
        "source": IntegritySource.retraction_watch,
        "action_type": IntegrityActionType.retraction_added,
        "severity": IntegritySeverity.critical,
        "candidate_identifiers": {"name": "Test Author", "pmid": "12345678"},
        "detail": "Test retraction event",
        "source_url": "https://retractionwatch.com/test",
        "detected_at": datetime.now(UTC),
        "published_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return IntegrityEvent(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_publish_and_consume() -> None:
    """Publish 3 events; verify all 3 are received by the handler."""
    received: list[IntegrityEvent] = []

    async def handler(event: IntegrityEvent) -> None:
        received.append(event)

    dispatcher = IntegrityEventDispatcher()
    dispatcher.subscribe(handler)
    await dispatcher.start()

    events = [_make_event() for _ in range(3)]
    for event in events:
        await dispatcher.publish(event)

    # Give consumer loop time to process
    await asyncio.sleep(0.1)
    await dispatcher.stop()

    assert len(received) == 3
    assert {e.event_id for e in received} == {e.event_id for e in events}


@pytest.mark.asyncio
async def test_multiple_handlers() -> None:
    """Subscribe 2 handlers, publish 1 event, verify both receive it."""
    received_a: list[IntegrityEvent] = []
    received_b: list[IntegrityEvent] = []

    async def handler_a(event: IntegrityEvent) -> None:
        received_a.append(event)

    async def handler_b(event: IntegrityEvent) -> None:
        received_b.append(event)

    dispatcher = IntegrityEventDispatcher()
    dispatcher.subscribe(handler_a)
    dispatcher.subscribe(handler_b)
    await dispatcher.start()

    event = _make_event()
    await dispatcher.publish(event)

    await asyncio.sleep(0.1)
    await dispatcher.stop()

    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0].event_id == event.event_id
    assert received_b[0].event_id == event.event_id


@pytest.mark.asyncio
async def test_handler_failure_isolation() -> None:
    """A failing handler does not prevent other handlers from receiving events."""
    received: list[IntegrityEvent] = []

    async def failing_handler(event: IntegrityEvent) -> None:
        raise RuntimeError("boom")

    async def good_handler(event: IntegrityEvent) -> None:
        received.append(event)

    dispatcher = IntegrityEventDispatcher()
    dispatcher.subscribe(failing_handler)
    dispatcher.subscribe(good_handler)
    await dispatcher.start()

    await dispatcher.publish(_make_event())

    await asyncio.sleep(0.1)
    await dispatcher.stop()

    assert len(received) == 1
    assert dispatcher.stats["failed"] == 1


@pytest.mark.asyncio
async def test_stats_tracking() -> None:
    """Publish events and verify stats dict has correct counts."""
    received: list[IntegrityEvent] = []

    async def handler(event: IntegrityEvent) -> None:
        received.append(event)

    dispatcher = IntegrityEventDispatcher()
    dispatcher.subscribe(handler)
    await dispatcher.start()

    for _ in range(5):
        await dispatcher.publish(_make_event())

    await asyncio.sleep(0.1)
    await dispatcher.stop()

    stats = dispatcher.stats
    assert stats["published"] == 5
    assert stats["processed"] == 5
    assert stats["failed"] == 0
    assert stats["queue_size"] == 0


@pytest.mark.asyncio
async def test_stop_drains() -> None:
    """Publish events, stop dispatcher, verify events were processed."""
    received: list[IntegrityEvent] = []

    async def handler(event: IntegrityEvent) -> None:
        received.append(event)

    dispatcher = IntegrityEventDispatcher()
    dispatcher.subscribe(handler)
    await dispatcher.start()

    for _ in range(3):
        await dispatcher.publish(_make_event())

    # Wait for processing then stop
    await asyncio.sleep(0.1)
    await dispatcher.stop()

    assert len(received) == 3
    assert dispatcher.stats["processed"] == 3


@pytest.mark.asyncio
async def test_integrity_event_model() -> None:
    """Create IntegrityEvent with all fields, verify serialization."""
    now = datetime.now(UTC)
    event = IntegrityEvent(
        event_id="test-uuid-1234",
        source=IntegritySource.retraction_watch,
        action_type=IntegrityActionType.retraction_added,
        severity=IntegritySeverity.critical,
        candidate_identifiers={"name": "Test Author", "pmid": "12345678"},
        detail="Test retraction event",
        source_url="https://retractionwatch.com/test",
        detected_at=now,
        published_at=now,
    )

    data = event.model_dump()
    assert data["event_id"] == "test-uuid-1234"
    assert data["source"] == "retraction_watch"
    assert data["action_type"] == "retraction_added"
    assert data["severity"] == "critical"
    assert data["candidate_identifiers"] == {"name": "Test Author", "pmid": "12345678"}
    assert data["detail"] == "Test retraction event"
    assert data["source_url"] == "https://retractionwatch.com/test"
    assert data["detected_at"] == now
    assert data["published_at"] == now

    # Frozen model: cannot mutate
    with pytest.raises(Exception):
        event.detail = "modified"


@pytest.mark.asyncio
async def test_integrity_source_enum() -> None:
    """Verify all expected source values exist."""
    expected = {
        "retraction_watch",
        "ori",
        "ofac",
        "sam",
        "leie",
        "state_medical_board",
    }
    actual = {member.value for member in IntegritySource}
    assert actual == expected


@pytest.mark.asyncio
async def test_backpressure() -> None:
    """A dispatcher with max_queue_size=2 blocks on the third publish."""
    dispatcher = IntegrityEventDispatcher(max_queue_size=2)
    # Don't start consumer — queue won't drain

    await dispatcher.publish(_make_event())
    await dispatcher.publish(_make_event())

    # Third publish should block because queue is full
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(dispatcher.publish(_make_event()), timeout=0.2)
