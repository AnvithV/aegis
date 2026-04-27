"""Demographic feature blocklist: strips prohibited fields at ingestion.

Per program overview section 15, these demographic features must never
enter the scoring pipeline:
- Gender / sex
- Race / ethnicity
- Citizenship / nationality / immigration status
- Age / date of birth (as a standalone field; publication dates are allowed)

Fields are stripped at ingestion. Any attempt to bypass triggers an alert.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Blocklisted field name substrings (case-insensitive matching).
# If a field name contains any of these substrings, it is stripped.
_BLOCKED_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "gender",
        "sex",
        "race",
        "ethnicity",
        "ethnic",
        "citizenship",
        "nationality",
        "immigration",
        "visa",
        "age",
        "date_of_birth",
        "dob",
        "birth_date",
        "birthdate",
    }
)

# Exact field names that are blocked (case-insensitive).
# These catch short names that substring matching might miss.
_BLOCKED_EXACT: frozenset[str] = frozenset(
    {
        "sex",
        "age",
        "dob",
        "race",
    }
)

# Field names that are ALLOWED even if they contain a blocked substring.
# Example: "dosage" contains "age", "page" contains "age".
_ALLOWLIST_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "dosage",
        "page",
        "passage",
        "stage",
        "storage",
        "usage",
        "average",
        "coverage",
        "leverage",
        "lineage",
        "percentage",
        "voltage",
        "shortage",
        "manage",
        "message",
        "package",
        "image",
        "language",
        "damage",
        "garbage",
        "baggage",
        "sextet",
    }
)


class BlocklistResult(BaseModel):
    """Result of applying the demographic blocklist to a data record."""

    model_config = ConfigDict(frozen=True)

    original_field_count: int
    stripped_field_count: int
    stripped_fields: list[str]
    remaining_fields: list[str]
    cleaned_data: dict[str, str]
    timestamp: datetime


class BlocklistStats(BaseModel):
    """Aggregate blocklist statistics."""

    model_config = ConfigDict(frozen=True)

    total_records_processed: int
    total_fields_stripped: int
    stripped_by_field: dict[str, int]


class DemographicBlocklist:
    """Strip prohibited demographic fields from ingestion data.

    Matching is case-insensitive. A field is blocked if:
    1. Its lowercased name exactly matches a blocked name, OR
    2. Its lowercased name contains a blocked substring AND is NOT
       in the allowlist (to avoid false positives like "dosage").
    """

    def __init__(
        self,
        *,
        extra_blocked: frozenset[str] | None = None,
        alert_callback: Any | None = None,
    ) -> None:
        self._blocked_substrings = _BLOCKED_SUBSTRINGS | (extra_blocked or frozenset())
        self._alert_callback = alert_callback
        self._total_records = 0
        self._total_stripped = 0
        self._stripped_by_field: dict[str, int] = {}

    def is_blocked(self, field_name: str) -> bool:
        """Check if a field name is blocked by the demographic blocklist."""
        lowered = field_name.lower()

        # Exact match check
        if lowered in _BLOCKED_EXACT:
            return True

        # Allowlist check -- if the lowered name matches an allowlist entry, allow it
        if lowered in _ALLOWLIST_SUBSTRINGS:
            return False

        # Substring match check
        if any(sub in lowered for sub in self._blocked_substrings):
            return True

        return False

    def strip(self, data: dict[str, str]) -> BlocklistResult:
        """Strip prohibited demographic fields from data."""
        stripped_fields: list[str] = []
        remaining_fields: list[str] = []
        cleaned_data: dict[str, str] = {}

        for field_name, value in data.items():
            if self.is_blocked(field_name):
                stripped_fields.append(field_name)
            else:
                remaining_fields.append(field_name)
                cleaned_data[field_name] = value

        if stripped_fields and self._alert_callback:
            self._alert_callback(stripped_fields)

        # Update stats
        self._total_records += 1
        self._total_stripped += len(stripped_fields)
        for field in stripped_fields:
            self._stripped_by_field[field] = self._stripped_by_field.get(field, 0) + 1

        return BlocklistResult(
            original_field_count=len(data),
            stripped_field_count=len(stripped_fields),
            stripped_fields=stripped_fields,
            remaining_fields=remaining_fields,
            cleaned_data=cleaned_data,
            timestamp=datetime.now(tz=UTC),
        )

    def get_stats(self) -> BlocklistStats:
        """Return current blocklist statistics."""
        return BlocklistStats(
            total_records_processed=self._total_records,
            total_fields_stripped=self._total_stripped,
            stripped_by_field=dict(self._stripped_by_field),
        )
