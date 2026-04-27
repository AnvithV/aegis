"""Retraction Watch database in-memory store."""

from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class RetractionRecord(BaseModel):
    """A retraction record from the Retraction Watch database."""

    model_config = ConfigDict(frozen=True)

    title: str
    authors: list[str]
    pmid: str | None
    doi: str | None
    journal: str | None
    retraction_date: date | None
    reason: str | None
    original_paper_date: date | None


class RetractionWatchStore:
    """In-memory store for Retraction Watch database records.

    Supports lookup by author (case-insensitive substring) and by PMID.
    """

    def __init__(self) -> None:
        self._records: list[RetractionRecord] = []
        self._by_pmid: dict[str, list[RetractionRecord]] = {}

    def add_batch(self, records: list[RetractionRecord]) -> None:
        for record in records:
            self._records.append(record)
            if record.pmid:
                self._by_pmid.setdefault(record.pmid, []).append(record)

    def lookup_by_author(self, author: str) -> list[RetractionRecord]:
        """Find retraction records by author name (case-insensitive substring)."""
        author_lower = author.lower()
        return [
            r for r in self._records
            if any(author_lower in a.lower() for a in r.authors)
        ]

    def lookup_by_pmid(self, pmid: str) -> list[RetractionRecord]:
        """Find retraction records by PMID (exact match)."""
        return self._by_pmid.get(pmid, [])

    def count(self) -> int:
        return len(self._records)
