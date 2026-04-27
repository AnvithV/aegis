"""Drugs@FDA bulk data client for FDA submission cross-referencing."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class FDASubmission(BaseModel):
    """A drug submission record from Drugs@FDA."""

    model_config = ConfigDict(frozen=True)

    application_number: str
    sponsor_name: str
    drug_name: str
    active_ingredient: str | None
    submission_type: str | None
    approval_date: str | None  # ISO date string
    application_type: str | None  # NDA, BLA, ANDA


class DrugsFDAStore:
    """In-memory store for FDA submission records.

    Phase 1 uses bulk download data loaded into memory.
    Phase 3 will add the openFDA API integration.
    """

    def __init__(self) -> None:
        self._submissions: list[FDASubmission] = []

    def add_batch(self, submissions: list[FDASubmission]) -> None:
        self._submissions.extend(submissions)

    def lookup_by_sponsor(self, sponsor_name: str) -> list[FDASubmission]:
        """Find submissions by sponsor name (case-insensitive substring)."""
        sponsor_lower = sponsor_name.lower()
        return [
            s for s in self._submissions
            if sponsor_lower in s.sponsor_name.lower()
        ]

    def count(self) -> int:
        return len(self._submissions)
