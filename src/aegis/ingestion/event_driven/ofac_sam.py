"""OFAC/SAM change-data feed watcher.

Monitors OFAC SDN and SAM.gov exclusion list changes via their
published update feeds. Publishes IntegrityEvent objects for
new sanctions/exclusions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from aegis.ingestion.event_dispatcher import (
    IntegrityActionType,
    IntegrityEvent,
    IntegrityEventDispatcher,
    IntegritySeverity,
    IntegritySource,
)
from aegis.ingestion.event_driven.feed_watcher import FeedEntry, FeedWatcher

logger = logging.getLogger(__name__)

# OFAC publishes change notices via RSS
OFAC_FEED_URL = "https://sanctionssearch.ofac.treas.gov/feed"
# SAM.gov entity exclusions RSS
SAM_FEED_URL = "https://sam.gov/api/prod/feeds/v1/exclusions/rss"


def _classify_ofac_action(
    title: str, summary: str | None
) -> tuple[IntegrityActionType, IntegritySeverity]:
    """Classify an OFAC/SAM feed entry action and severity."""
    text = f"{title} {summary or ''}".lower()
    if "remov" in text or "delist" in text:
        return (
            IntegrityActionType.sanctions_removed,
            IntegritySeverity.low,
        )
    return (
        IntegrityActionType.sanctions_added,
        IntegritySeverity.critical,
    )


class OFACWatcher(FeedWatcher):
    """OFAC SDN list change feed watcher."""

    def __init__(
        self,
        dispatcher: IntegrityEventDispatcher,
        poll_interval_seconds: float = 900.0,
    ) -> None:
        super().__init__(
            dispatcher=dispatcher,
            poll_interval_seconds=poll_interval_seconds,
        )

    @property
    def feed_url(self) -> str:
        return OFAC_FEED_URL

    @property
    def source_name(self) -> str:
        return "ofac"

    async def parse_entry(
        self, entry: FeedEntry
    ) -> IntegrityEvent | None:
        action_type, severity = _classify_ofac_action(
            entry.title, entry.summary
        )
        return IntegrityEvent(
            event_id=str(uuid.uuid4()),
            source=IntegritySource.ofac,
            action_type=action_type,
            severity=severity,
            candidate_identifiers={"name": entry.title},
            detail=entry.title,
            source_url=entry.link,
            detected_at=datetime.now(UTC),
            published_at=entry.published,
        )


class SAMWatcher(FeedWatcher):
    """SAM.gov exclusion list change feed watcher."""

    def __init__(
        self,
        dispatcher: IntegrityEventDispatcher,
        poll_interval_seconds: float = 900.0,
    ) -> None:
        super().__init__(
            dispatcher=dispatcher,
            poll_interval_seconds=poll_interval_seconds,
        )

    @property
    def feed_url(self) -> str:
        return SAM_FEED_URL

    @property
    def source_name(self) -> str:
        return "sam"

    async def parse_entry(
        self, entry: FeedEntry
    ) -> IntegrityEvent | None:
        action_type, severity = _classify_ofac_action(
            entry.title, entry.summary
        )
        return IntegrityEvent(
            event_id=str(uuid.uuid4()),
            source=IntegritySource.sam,
            action_type=action_type,
            severity=severity,
            candidate_identifiers={"name": entry.title},
            detail=entry.title,
            source_url=entry.link,
            detected_at=datetime.now(UTC),
            published_at=entry.published,
        )
