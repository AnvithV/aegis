"""IntegrityEventDispatcher: internal message bus for integrity-source events.

Provides a lightweight publish/subscribe bus backed by asyncio queues.
All integrity-source feed watchers publish IntegrityEvent objects to a common
topic. Consumers (I(c) recomputation, audit logging) subscribe to the bus.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class IntegritySource(StrEnum):
    """Enumeration of integrity-event source types."""

    retraction_watch = "retraction_watch"
    ori = "ori"
    ofac = "ofac"
    sam = "sam"
    leie = "leie"
    state_medical_board = "state_medical_board"


class IntegrityActionType(StrEnum):
    """Type of integrity action detected."""

    retraction_added = "retraction_added"
    retraction_updated = "retraction_updated"
    misconduct_finding = "misconduct_finding"
    sanctions_added = "sanctions_added"
    sanctions_removed = "sanctions_removed"
    exclusion_added = "exclusion_added"
    exclusion_removed = "exclusion_removed"
    board_action_added = "board_action_added"
    board_action_updated = "board_action_updated"


class IntegritySeverity(StrEnum):
    """Severity level of the integrity event."""

    critical = "critical"     # Hard gate: I(c) = 0
    high = "high"             # Significant soft discount
    medium = "medium"         # Moderate soft discount
    low = "low"               # Minor or informational


class IntegrityEvent(BaseModel):
    """A single integrity-source event for the message bus.

    Published by feed watchers, consumed by I(c) recomputation
    and audit logging.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str                          # Unique event identifier (UUID)
    source: IntegritySource
    action_type: IntegrityActionType
    severity: IntegritySeverity
    candidate_identifiers: dict[str, str]  # e.g. {"name": "...", "pmid": "..."}
    detail: str                            # Human-readable description
    source_url: str | None                 # URL to the source record
    detected_at: datetime                  # When the event was detected
    published_at: datetime | None          # When the source published it


# Type alias for event handler callbacks
EventHandler = Callable[[IntegrityEvent], Awaitable[None]]


class IntegrityEventDispatcher:
    """Async publish/subscribe bus for integrity events.

    Usage:
        dispatcher = IntegrityEventDispatcher()
        dispatcher.subscribe(my_handler)
        await dispatcher.start()
        await dispatcher.publish(event)
        ...
        await dispatcher.stop()
    """

    def __init__(self, max_queue_size: int = 10_000) -> None:
        self._queue: asyncio.Queue[IntegrityEvent] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self._handlers: list[EventHandler] = []
        self._running = False
        self._consumer_task: asyncio.Task[None] | None = None
        self._events_published = 0
        self._events_processed = 0
        self._events_failed = 0

    def subscribe(self, handler: EventHandler) -> None:
        """Register a handler to be called for every event."""
        self._handlers.append(handler)

    async def publish(self, event: IntegrityEvent) -> None:
        """Publish an integrity event to the bus.

        Blocks if the queue is full (backpressure).
        """
        await self._queue.put(event)
        self._events_published += 1
        logger.info(
            "Published integrity event: source=%s action=%s severity=%s",
            event.source,
            event.action_type,
            event.severity,
        )

    async def start(self) -> None:
        """Start the consumer loop."""
        if self._running:
            return
        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_loop())
        logger.info("IntegrityEventDispatcher started")

    async def stop(self) -> None:
        """Stop the consumer loop and drain remaining events."""
        self._running = False
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info(
            "IntegrityEventDispatcher stopped: published=%d processed=%d failed=%d",
            self._events_published,
            self._events_processed,
            self._events_failed,
        )

    async def _consume_loop(self) -> None:
        """Main consumer loop: dequeue events and fan out to handlers."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            for handler in self._handlers:
                try:
                    await handler(event)
                except Exception:
                    self._events_failed += 1
                    logger.exception(
                        "Handler %s failed for event %s",
                        handler.__name__,
                        event.event_id,
                    )
            self._events_processed += 1
            self._queue.task_done()

    @property
    def stats(self) -> dict[str, int]:
        """Return dispatcher statistics."""
        return {
            "published": self._events_published,
            "processed": self._events_processed,
            "failed": self._events_failed,
            "queue_size": self._queue.qsize(),
        }
