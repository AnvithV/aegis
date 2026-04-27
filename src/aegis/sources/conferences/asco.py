"""ASCO Annual Meeting proceedings ingestor."""

from __future__ import annotations

from collections.abc import Iterator

from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord


class AscoIngestor(ConferenceIngestor):
    """Ingestor for ASCO Annual Meeting proceedings."""

    @property
    def conference_name(self) -> str:
        return "ASCO Annual Meeting"

    @property
    def society_code(self) -> str:
        return "ASCO"

    def ingest(self, year: int) -> Iterator[TalkRecord]:
        """Ingest ASCO proceedings for a given year."""
        return iter([])
