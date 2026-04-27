"""State medical board bulletin watcher.

Monitors state medical board RSS feeds and bulletin pages for
new disciplinary actions. Publishes IntegrityEvent objects.
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

# Known state board RSS/bulletin feed URLs
STATE_BOARD_FEEDS: dict[str, str] = {
    "CA": "https://mbc.ca.gov/rss/enforcement.xml",
    "NY": "https://health.ny.gov/professionals/doctors/conduct/rss.xml",
    "TX": "https://www.tmb.state.tx.us/rss/disciplinary.xml",
    "FL": "https://flboardofmedicine.gov/rss/actions.xml",
    "PA": "https://pals.pa.gov/rss/medicine-enforcement.xml",
}

_SEVERITY_MAP: dict[str, IntegritySeverity] = {
    "revocation": IntegritySeverity.critical,
    "revoked": IntegritySeverity.critical,
    "suspension": IntegritySeverity.critical,
    "suspended": IntegritySeverity.critical,
    "surrender": IntegritySeverity.critical,
    "restriction": IntegritySeverity.high,
    "probation": IntegritySeverity.high,
    "reprimand": IntegritySeverity.medium,
    "fine": IntegritySeverity.medium,
    "warning": IntegritySeverity.low,
}


def _classify_board_action_severity(
    title: str, summary: str | None
) -> IntegritySeverity:
    """Classify severity from board action text."""
    text = f"{title} {summary or ''}".lower()
    for keyword, severity in _SEVERITY_MAP.items():
        if keyword in text:
            return severity
    return IntegritySeverity.high  # Default to high for unknown action types


class StateBoardWatcher(FeedWatcher):
    """RSS/bulletin watcher for a single state medical board.

    Each instance monitors one state's feed.
    """

    def __init__(
        self,
        dispatcher: IntegrityEventDispatcher,
        state_code: str,
        feed_url_override: str | None = None,
        poll_interval_seconds: float = 900.0,
    ) -> None:
        self._state_code = state_code
        self._feed_url = feed_url_override or STATE_BOARD_FEEDS.get(
            state_code, ""
        )
        super().__init__(
            dispatcher=dispatcher,
            poll_interval_seconds=poll_interval_seconds,
        )

    @property
    def feed_url(self) -> str:
        return self._feed_url

    @property
    def source_name(self) -> str:
        return f"state_board_{self._state_code}"

    @property
    def state_code(self) -> str:
        return self._state_code

    async def parse_entry(
        self, entry: FeedEntry
    ) -> IntegrityEvent | None:
        severity = _classify_board_action_severity(
            entry.title, entry.summary
        )
        return IntegrityEvent(
            event_id=str(uuid.uuid4()),
            source=IntegritySource.state_medical_board,
            action_type=IntegrityActionType.board_action_added,
            severity=severity,
            candidate_identifiers={
                "name": entry.title,
                "state": self._state_code,
            },
            detail=f"[{self._state_code}] {entry.title}",
            source_url=entry.link,
            detected_at=datetime.now(UTC),
            published_at=entry.published,
        )


def create_all_state_watchers(
    dispatcher: IntegrityEventDispatcher,
    poll_interval_seconds: float = 900.0,
) -> list[StateBoardWatcher]:
    """Create watchers for all known state board feeds."""
    watchers: list[StateBoardWatcher] = []
    for state_code, url in STATE_BOARD_FEEDS.items():
        watchers.append(
            StateBoardWatcher(
                dispatcher=dispatcher,
                state_code=state_code,
                feed_url_override=url,
                poll_interval_seconds=poll_interval_seconds,
            )
        )
    return watchers
