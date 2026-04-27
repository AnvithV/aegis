"""AACR Annual Meeting proceedings ingestor."""

from __future__ import annotations

from collections.abc import Iterator

from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord


class AacrIngestor(ConferenceIngestor):
    """Ingestor for AACR Annual Meeting proceedings."""

    @property
    def conference_name(self) -> str:
        return "AACR Annual Meeting"

    @property
    def society_code(self) -> str:
        return "AACR"

    def ingest(self, year: int) -> Iterator[TalkRecord]:
        """Ingest AACR proceedings for a given year."""
        return iter([])
