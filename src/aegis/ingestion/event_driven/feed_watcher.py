"""Base FeedWatcher ABC for RSS/Atom feed monitoring.

Provides common feed-parsing, schedule management, deduplication,
and integration with the IntegrityEventDispatcher.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import feedparser  # type: ignore[import-untyped]
import httpx

from aegis.ingestion.event_dispatcher import (
    IntegrityEvent,
    IntegrityEventDispatcher,
)

logger = logging.getLogger(__name__)


class FeedEntry:
    """Parsed feed entry with normalized fields."""

    def __init__(
        self,
        entry_id: str,
        title: str,
        link: str | None,
        summary: str | None,
        published: datetime | None,
        updated: datetime | None,
        raw: dict,  # type: ignore[type-arg]
    ) -> None:
        self.entry_id = entry_id
        self.title = title
        self.link = link
        self.summary = summary
        self.published = published
        self.updated = updated
        self.raw = raw


def _parse_datetime(time_struct: object) -> datetime | None:
    """Convert feedparser time struct to datetime."""
    if time_struct is None:
        return None
    try:
        import time as _time

        ts = _time.mktime(time_struct)  # type: ignore[arg-type]
        return datetime.fromtimestamp(ts, tz=UTC)
    except (TypeError, ValueError, OverflowError):
        return None


def _entry_fingerprint(entry: dict) -> str:  # type: ignore[type-arg]
    """Generate a stable fingerprint for deduplication."""
    raw = (
        f"{entry.get('id', '')}"
        f"{entry.get('title', '')}"
        f"{entry.get('link', '')}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class FeedWatcher(ABC):
    """Abstract base class for RSS/Atom feed watchers.

    Subclasses implement:
      - feed_url: property returning the feed URL
      - source_name: property returning the source name for logging
      - parse_entry(entry: FeedEntry) -> IntegrityEvent | None:
          convert a feed entry to an IntegrityEvent, or None to skip

    The base class handles:
      - Periodic polling via asyncio
      - Feed fetching and parsing with feedparser
      - Entry deduplication via fingerprints
      - Publishing events to the IntegrityEventDispatcher
    """

    def __init__(
        self,
        dispatcher: IntegrityEventDispatcher,
        poll_interval_seconds: float = 900.0,  # 15 minutes default
        http_timeout: float = 30.0,
    ) -> None:
        self._dispatcher = dispatcher
        self._poll_interval = poll_interval_seconds
        self._http_timeout = http_timeout
        self._seen_fingerprints: set[str] = set()
        self._running = False
        self._poll_task: asyncio.Task[None] | None = None
        self._polls_completed = 0
        self._entries_processed = 0

    @property
    @abstractmethod
    def feed_url(self) -> str:
        """URL of the RSS/Atom feed to monitor."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source name for logging."""
        ...

    @abstractmethod
    async def parse_entry(
        self, entry: FeedEntry
    ) -> IntegrityEvent | None:
        """Convert a feed entry to an IntegrityEvent.

        Return None to skip entries that are not relevant.
        """
        ...

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(
            "FeedWatcher started: source=%s url=%s interval=%ds",
            self.source_name,
            self.feed_url,
            self._poll_interval,
        )

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info(
            "FeedWatcher stopped: source=%s polls=%d entries=%d",
            self.source_name,
            self._polls_completed,
            self._entries_processed,
        )

    async def poll_once(self) -> list[IntegrityEvent]:
        """Fetch the feed once and return new events.

        Public for testing. Called internally by _poll_loop.
        """
        events: list[IntegrityEvent] = []
        try:
            async with httpx.AsyncClient(
                timeout=self._http_timeout
            ) as client:
                resp = await client.get(self.feed_url)
                resp.raise_for_status()
                content = resp.text

            feed = feedparser.parse(content)

            for raw_entry in feed.entries:
                fp = _entry_fingerprint(raw_entry)
                if fp in self._seen_fingerprints:
                    continue
                self._seen_fingerprints.add(fp)

                entry = FeedEntry(
                    entry_id=raw_entry.get("id", fp),
                    title=raw_entry.get("title", ""),
                    link=raw_entry.get("link"),
                    summary=raw_entry.get("summary"),
                    published=_parse_datetime(
                        raw_entry.get("published_parsed")
                    ),
                    updated=_parse_datetime(
                        raw_entry.get("updated_parsed")
                    ),
                    raw=dict(raw_entry),
                )

                event = await self.parse_entry(entry)
                if event is not None:
                    events.append(event)
                    await self._dispatcher.publish(event)
                    self._entries_processed += 1

            self._polls_completed += 1
            logger.info(
                "Feed poll complete: source=%s new_events=%d",
                self.source_name,
                len(events),
            )

        except httpx.HTTPError:
            logger.exception(
                "Feed fetch failed: source=%s url=%s",
                self.source_name,
                self.feed_url,
            )
        except Exception:
            logger.exception(
                "Feed processing failed: source=%s",
                self.source_name,
            )

        return events

    async def _poll_loop(self) -> None:
        """Periodically poll the feed."""
        while self._running:
            await self.poll_once()
            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

    @property
    def stats(self) -> dict[str, int]:
        """Return watcher statistics."""
        return {
            "polls_completed": self._polls_completed,
            "entries_processed": self._entries_processed,
            "seen_fingerprints": len(self._seen_fingerprints),
        }
