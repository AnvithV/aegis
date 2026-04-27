"""CLI-driven integrity false-positive override with append-only audit trail."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class OverrideAction(StrEnum):
    """Actions that can be taken on a candidate override."""

    override = "override"
    revoke = "revoke"


class OverrideRecord(BaseModel):
    """A single override or revocation record."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    candidate_uuid: str
    reviewer_id: str
    action: OverrideAction
    justification: str
    timestamp: datetime
    original_reason: str


class ContestabilityStore:
    """Append-only JSONL store for integrity override records."""

    def __init__(self, *, storage_path: Path) -> None:
        self._path = storage_path

    def add_override(
        self,
        *,
        candidate_uuid: str,
        reviewer_id: str,
        action: OverrideAction,
        justification: str,
        original_reason: str,
    ) -> OverrideRecord:
        """Create and persist a new override record."""
        record = OverrideRecord(
            record_id=uuid.uuid4().hex,
            candidate_uuid=candidate_uuid,
            reviewer_id=reviewer_id,
            action=action,
            justification=justification,
            timestamp=datetime.now(tz=UTC),
            original_reason=original_reason,
        )
        with open(self._path, "a") as f:
            f.write(record.model_dump_json() + "\n")
            f.flush()
        return record

    def is_overridden(self, candidate_uuid: str) -> bool:
        """Return True if the most recent action for this candidate is override."""
        history = self.get_history(candidate_uuid)
        if not history:
            return False
        return history[-1].action == OverrideAction.override

    def get_history(self, candidate_uuid: str) -> list[OverrideRecord]:
        """Return all records for a candidate in chronological order."""
        return [
            r for r in self.load_all() if r.candidate_uuid == candidate_uuid
        ]

    def load_all(self) -> list[OverrideRecord]:
        """Load all records from the JSONL file."""
        if not self._path.exists():
            return []
        records: list[OverrideRecord] = []
        with open(self._path) as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(
                        OverrideRecord.model_validate(json.loads(stripped))
                    )
        return records
