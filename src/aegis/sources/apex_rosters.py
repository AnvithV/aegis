"""Apex roster ingestion for elite recognition markers."""

from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ApexRosterType(StrEnum):
    """Types of apex recognition rosters."""

    hhmi_investigator = "hhmi_investigator"
    nas_member = "nas_member"
    nae_member = "nae_member"
    nam_member = "nam_member"
    nih_merit = "nih_merit"
    lasker_laureate = "lasker_laureate"
    hhmi_hanna_gray = "hhmi_hanna_gray"


class ApexMembership(BaseModel):
    """A single membership record on an apex roster."""

    model_config = ConfigDict(frozen=True)

    roster_type: ApexRosterType
    name: str
    year: int | None
    institution: str | None
    confidence: float  # identity match confidence


class ApexRosterStore:
    """In-memory store for apex roster memberships.

    Phase 1 uses a static in-memory store loaded from YAML/JSON.
    Phase 3 will add live scraping and DB persistence.
    """

    def __init__(self) -> None:
        self._memberships: list[ApexMembership] = []

    def add(self, membership: ApexMembership) -> None:
        """Add a membership record."""
        self._memberships.append(membership)

    def add_batch(self, memberships: list[ApexMembership]) -> None:
        """Add multiple membership records."""
        self._memberships.extend(memberships)

    def lookup_by_name(
        self,
        name: str,
        institution: str | None = None,
    ) -> list[ApexMembership]:
        """Find memberships matching a name (case-insensitive).

        If institution is provided, prefer matches with matching institution.
        """
        name_lower = name.lower()
        matches = [
            m for m in self._memberships if m.name.lower() == name_lower
        ]
        if institution and len(matches) > 1:
            inst_lower = institution.lower()
            inst_matches = [
                m
                for m in matches
                if m.institution and inst_lower in m.institution.lower()
            ]
            if inst_matches:
                return inst_matches
        return matches

    def list_by_roster(self, roster_type: ApexRosterType) -> list[ApexMembership]:
        """List all memberships for a roster type."""
        return [m for m in self._memberships if m.roster_type == roster_type]

    def count(self) -> int:
        """Total membership records loaded."""
        return len(self._memberships)
