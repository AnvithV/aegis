"""ACS National Meeting proceedings ingestor."""

from __future__ import annotations

from collections.abc import Iterator

from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord


class AcsIngestor(ConferenceIngestor):
    """Ingestor for ACS National Meeting proceedings."""

    @property
    def conference_name(self) -> str:
        return "ACS National Meeting"

    @property
    def society_code(self) -> str:
        return "ACS"

    def ingest(self, year: int) -> Iterator[TalkRecord]:
        """Ingest ACS proceedings for a given year."""
        return iter([])
