"""ORI Federal Register feed watcher.

Monitors the Federal Register RSS feed filtered for ORI/HHS research
misconduct findings. Publishes IntegrityEvent objects for new findings.
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

# Federal Register RSS filtered for ORI findings
ORI_FEDERAL_REGISTER_FEED_URL = (
    "https://www.federalregister.gov/documents/search.atom"
    "?conditions%5Bagencies%5D%5B%5D=office-of-research-integrity"
    "&conditions%5Btype%5D%5B%5D=NOTICE"
)

_MISCONDUCT_KEYWORDS = frozenset({
    "research misconduct",
    "scientific misconduct",
    "fabrication",
    "falsification",
    "debarment",
    "voluntary exclusion",
})


def _is_misconduct_finding(title: str, summary: str | None) -> bool:
    """Determine if a Federal Register entry is a misconduct finding."""
    text = f"{title} {summary or ''}".lower()
    return any(kw in text for kw in _MISCONDUCT_KEYWORDS)


def _extract_researcher_name(
    title: str, summary: str | None  # noqa: ARG001
) -> str | None:
    """Extract researcher name from ORI notice title.

    ORI notices typically have titles like:
    "Findings of Research Misconduct; John Q. Smith"
    """
    text = f"{title}"
    # Pattern: after semicolon or dash
    for sep in [";", "\u2014", "-"]:
        if sep in text:
            name_part = text.split(sep, 1)[1].strip()
            # Remove trailing punctuation
            name_part = re.sub(r"[.,;:]+$", "", name_part).strip()
            if name_part and len(name_part) > 3:
                return name_part
    return None


class ORIRegisterWatcher(FeedWatcher):
    """Federal Register feed watcher for ORI misconduct findings.

    Polls the Federal Register Atom feed filtered for ORI notices
    and publishes critical-severity events for misconduct findings.
    """

    def __init__(
        self,
        dispatcher: IntegrityEventDispatcher,
        poll_interval_seconds: float = 3600.0,
    ) -> None:
        super().__init__(
            dispatcher=dispatcher,
            poll_interval_seconds=poll_interval_seconds,
        )

    @property
    def feed_url(self) -> str:
        return ORI_FEDERAL_REGISTER_FEED_URL

    @property
    def source_name(self) -> str:
        return "ori_federal_register"

    async def parse_entry(
        self, entry: FeedEntry
    ) -> IntegrityEvent | None:
        """Convert a Federal Register entry to IntegrityEvent if misconduct-related."""
        if not _is_misconduct_finding(entry.title, entry.summary):
            return None

        researcher_name = _extract_researcher_name(
            entry.title, entry.summary
        )
        candidate_ids: dict[str, str] = {}
        if researcher_name:
            candidate_ids["name"] = researcher_name

        return IntegrityEvent(
            event_id=str(uuid.uuid4()),
            source=IntegritySource.ori,
            action_type=IntegrityActionType.misconduct_finding,
            severity=IntegritySeverity.critical,
            candidate_identifiers=candidate_ids,
            detail=entry.title,
            source_url=entry.link,
            detected_at=datetime.now(UTC),
            published_at=entry.published,
        )
