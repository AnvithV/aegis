"""LEIE (List of Excluded Individuals/Entities) in-memory store."""

from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class LEIERecord(BaseModel):
    """A record from the HHS-OIG LEIE exclusion list."""

    model_config = ConfigDict(frozen=True)

    last_name: str
    first_name: str
    npi: str | None
    exclusion_type: str | None
    exclusion_date: date | None
    reinstate_date: date | None
    state: str | None
    specialty: str | None


class LEIEStore:
    """In-memory store for LEIE exclusion records.

    Supports lookup by NPI (exact) or name (case-insensitive).
    Returns None for reinstated individuals.
    """

    def __init__(self) -> None:
        self._records: list[LEIERecord] = []
        self._by_npi: dict[str, list[LEIERecord]] = {}

    def add_batch(self, records: list[LEIERecord]) -> None:
        for record in records:
            self._records.append(record)
            if record.npi:
                self._by_npi.setdefault(record.npi, []).append(record)

    def is_excluded(
        self, *, npi: str | None = None, name: str | None = None
    ) -> bool | None:
        """Check if an individual is excluded.

        Matches by NPI first (exact), then by name (case-insensitive).
        Returns None if the matching record has been reinstated,
        True if excluded, False if no match found.
        """
        matches: list[LEIERecord] = []

        if npi:
            matches = self._by_npi.get(npi, [])

        if not matches and name:
            name_lower = name.lower()
            matches = [
                r for r in self._records
                if f"{r.first_name} {r.last_name}".lower() == name_lower
                or f"{r.last_name}, {r.first_name}".lower() == name_lower
            ]

        if not matches:
            return False

        # If any matching record has been reinstated, return None
        for record in matches:
            if record.reinstate_date is not None:
                return None

        return True

    def lookup_by_name(self, name: str) -> list[LEIERecord]:
        """Find records by name (case-insensitive)."""
        name_lower = name.lower()
        return [
            r for r in self._records
            if f"{r.first_name} {r.last_name}".lower() == name_lower
            or f"{r.last_name}, {r.first_name}".lower() == name_lower
        ]

    def count(self) -> int:
        return len(self._records)
