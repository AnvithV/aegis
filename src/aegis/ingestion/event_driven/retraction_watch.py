"""Retraction Watch RSS feed watcher.

Monitors the Retraction Watch blog RSS feed for new retraction notices.
Publishes IntegrityEvent objects with severity based on retraction reason.
"""

from __future__ import annotations

import logging
import re
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

RETRACTION_WATCH_FEED_URL = "https://retractionwatch.com/feed/"

# Keywords indicating high-severity retractions
_FABRICATION_KEYWORDS = frozenset({
    "fabrication",
    "fabricated",
    "fake data",
    "manufactured data",
})
_FALSIFICATION_KEYWORDS = frozenset({
    "falsification",
    "falsified",
    "manipulated",
    "image manipulation",
    "data manipulation",
})


def _classify_severity(
    title: str, summary: str | None
) -> IntegritySeverity:
    """Classify retraction severity from title and summary text."""
    text = f"{title} {summary or ''}".lower()
    if any(kw in text for kw in _FABRICATION_KEYWORDS):
        return IntegritySeverity.critical
    if any(kw in text for kw in _FALSIFICATION_KEYWORDS):
        return IntegritySeverity.critical
    if "concern" in text and "expression" in text:
        return IntegritySeverity.medium
    return IntegritySeverity.high


def _extract_author_names(
    title: str, summary: str | None
) -> list[str]:
    """Best-effort extraction of author names from retraction notice text.

    Looks for patterns like "by Author Name" or "Author Name's paper".
    Returns empty list if no names found.
    """
    names: list[str] = []
    text = f"{title} {summary or ''}"
    # Pattern: "by FirstName LastName" (common in RW titles)
    pattern = r"\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
    matches = re.findall(pattern, text)
    names.extend(matches)
    return names


class RetractionWatchWatcher(FeedWatcher):
    """RSS feed watcher for Retraction Watch blog.

    Polls the RW RSS feed and classifies each retraction by severity:
    - critical: fabrication or falsification detected
    - high: standard retraction
    - medium: expression of concern
    """

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
        return RETRACTION_WATCH_FEED_URL

    @property
    def source_name(self) -> str:
        return "retraction_watch"

    async def parse_entry(
        self, entry: FeedEntry
    ) -> IntegrityEvent | None:
        """Convert a Retraction Watch RSS entry to an IntegrityEvent."""
        severity = _classify_severity(entry.title, entry.summary)
        author_names = _extract_author_names(entry.title, entry.summary)

        candidate_ids: dict[str, str] = {}
        if author_names:
            candidate_ids["name"] = author_names[0]
            if len(author_names) > 1:
                candidate_ids["additional_names"] = "; ".join(
                    author_names[1:]
                )

        # Extract PMID from entry link or summary if available
        pmid_match = re.search(
            r"pubmed/(\d+)",
            f"{entry.link or ''} {entry.summary or ''}",
        )
        if pmid_match:
            candidate_ids["pmid"] = pmid_match.group(1)

        return IntegrityEvent(
            event_id=str(uuid.uuid4()),
            source=IntegritySource.retraction_watch,
            action_type=IntegrityActionType.retraction_added,
            severity=severity,
            candidate_identifiers=candidate_ids,
            detail=entry.title,
            source_url=entry.link,
            detected_at=datetime.now(UTC),
            published_at=entry.published,
        )
