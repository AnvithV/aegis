"""OFAC/SAM sanctions and debarment list in-memory store."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class OFACSAMRecord(BaseModel):
    """A record from OFAC SDN or SAM.gov exclusion lists."""

    model_config = ConfigDict(frozen=True)

    primary_name: str
    aliases: list[str]
    source: str  # "OFAC" or "SAM"
    record_type: str | None  # "Individual", "Entity"
    program: str | None
    remarks: str | None


class OFACSAMStore:
    """In-memory store for OFAC and SAM.gov exclusion records.

    Checks primary name and aliases (case-insensitive).
    """

    def __init__(self) -> None:
        self._records: list[OFACSAMRecord] = []

    def add_batch(self, records: list[OFACSAMRecord]) -> None:
        self._records.extend(records)

    def is_listed(self, name: str) -> bool:
        """Check if a name appears in OFAC or SAM lists.

        Checks primary name and all aliases (case-insensitive).
        """
        name_lower = name.lower()
        for record in self._records:
            if record.primary_name.lower() == name_lower:
                return True
            if any(alias.lower() == name_lower for alias in record.aliases):
                return True
        return False

    def count(self) -> int:
        return len(self._records)
