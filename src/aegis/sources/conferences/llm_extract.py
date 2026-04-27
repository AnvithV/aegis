"""LLM-constrained extraction protocol for conference proceedings."""

from __future__ import annotations

import logging
from typing import Protocol

from aegis.sources.conferences.base import TalkRecord, TalkType

logger = logging.getLogger(__name__)


class LLMExtractor(Protocol):
    """Protocol for LLM-based talk extraction from raw text."""

    def extract_talks(
        self, text: str, conference_name: str, year: int
    ) -> list[dict[str, str]]: ...


class DefaultLLMExtractor:
    """Stub extractor that returns empty results with logging."""

    def extract_talks(
        self, text: str, conference_name: str, year: int
    ) -> list[dict[str, str]]:
        """Return empty results — placeholder for real LLM integration."""
        logger.info(
            "DefaultLLMExtractor stub called for %s %d (%d chars)",
            conference_name,
            year,
            len(text),
        )
        return []


_TALK_TYPE_KEYWORDS: dict[str, str] = {
    "named_lectureship": "is_named_lectureship",
    "lectureship": "is_named_lectureship",
    "invited": "is_invited_talk",
    "oral": "is_oral_presentation",
    "poster": "is_poster",
}


def talks_from_extraction(
    raw_talks: list[dict[str, str]],
    conference_name: str,
    year: int,
) -> list[TalkRecord]:
    """Convert raw dicts from LLM extraction to TalkRecords."""
    records: list[TalkRecord] = []
    for raw in raw_talks:
        talk_type_str = raw.get("talk_type", "").lower()
        type_flags: dict[str, bool] = {
            "is_named_lectureship": False,
            "is_invited_talk": False,
            "is_oral_presentation": False,
            "is_poster": False,
        }
        for keyword, flag in _TALK_TYPE_KEYWORDS.items():
            if keyword in talk_type_str:
                type_flags[flag] = True

        coauthors_raw = raw.get("coauthors", "")
        coauthors = (
            [c.strip() for c in coauthors_raw.split(",") if c.strip()]
            if coauthors_raw
            else []
        )

        records.append(
            TalkRecord(
                presenter_name=raw.get("presenter_name", ""),
                talk_type=TalkType(**type_flags),
                session_title=raw.get("session_title", ""),
                conference_name=conference_name,
                year=year,
                abstract_title=raw.get("abstract_title"),
                coauthors=coauthors,
                source_url=raw.get("source_url"),
            )
        )
    return records
