"""ORI (Office of Research Integrity) findings in-memory store."""

from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ORIFinding(BaseModel):
    """A research misconduct finding from ORI."""

    model_config = ConfigDict(frozen=True)

    name: str
    institution: str | None
    finding_date: date
    misconduct_type: str | None  # "Fabrication", "Falsification", "Plagiarism"
    settlement_type: str | None  # "Voluntary exclusion", "Debarment"
    debarment_end_date: date | None


class ORIStore:
    """In-memory store for ORI research misconduct findings.

    Supports lookup by name and recency-based filtering.
    """

    def __init__(self) -> None:
        self._findings: list[ORIFinding] = []

    def add_batch(self, findings: list[ORIFinding]) -> None:
        self._findings.extend(findings)

    def lookup_by_name(self, name: str) -> list[ORIFinding]:
        """Find findings by name (case-insensitive)."""
        name_lower = name.lower()
        return [f for f in self._findings if f.name.lower() == name_lower]

    def has_recent_finding(
        self, name: str, *, years: int = 10, as_of: date | None = None
    ) -> bool:
        """Check if a person has an ORI finding within the last N years.

        Args:
            name: Person name to check (case-insensitive).
            years: Window size in years (default 10).
            as_of: Reference date (default today).
        """
        ref = as_of or date.today()
        cutoff = ref.replace(year=ref.year - years)
        name_lower = name.lower()
        return any(
            f.name.lower() == name_lower and f.finding_date >= cutoff
            for f in self._findings
        )

    def count(self) -> int:
        return len(self._findings)
