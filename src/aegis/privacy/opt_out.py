"""Candidate opt-out enforcement.

Opted-out candidates are excluded from the active cohort and from
all query results. Opt-out is reversible by the candidate.
Defaults to permanent until explicitly reversed.
Bypassing opt-out is an alertable event.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class OptOutAction(StrEnum):
    """Actions for candidate opt-out."""

    opt_out = "opt_out"
    opt_in = "opt_in"


class OptOutRecord(BaseModel):
    """A single opt-out or opt-in record."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    candidate_uuid: str
    action: OptOutAction
    reason: str | None
    verified_via: str
    timestamp: datetime


class OptOutStatus(BaseModel):
    """Current opt-out status for a candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    is_opted_out: bool
    last_action: OptOutAction | None
    last_action_at: datetime | None
    history_count: int


class OptOutStats(BaseModel):
    """Aggregate opt-out statistics."""

    model_config = ConfigDict(frozen=True)

    total_opted_out: int
    total_opt_in_reversals: int
    current_opted_out_count: int


class OptOutStore:
    """Append-only JSONL store for candidate opt-out records.

    Follows the ContestabilityStore pattern: append-only writes,
    latest action determines current state.
    """

    def __init__(
        self,
        *,
        storage_path: Path,
        alert_callback: Any | None = None,
    ) -> None:
        self._path = storage_path
        self._alert_callback = alert_callback

    def opt_out(
        self,
        *,
        candidate_uuid: str,
        verified_via: str,
        reason: str | None = None,
    ) -> OptOutRecord:
        """Record a candidate opt-out."""
        record = OptOutRecord(
            record_id=_uuid.uuid4().hex,
            candidate_uuid=candidate_uuid,
            action=OptOutAction.opt_out,
            reason=reason,
            verified_via=verified_via,
            timestamp=datetime.now(tz=UTC),
        )
        self._append(record)
        return record

    def opt_in(
        self,
        *,
        candidate_uuid: str,
        verified_via: str,
        reason: str | None = None,
    ) -> OptOutRecord:
        """Record a candidate opt-in (reversal)."""
        record = OptOutRecord(
            record_id=_uuid.uuid4().hex,
            candidate_uuid=candidate_uuid,
            action=OptOutAction.opt_in,
            reason=reason,
            verified_via=verified_via,
            timestamp=datetime.now(tz=UTC),
        )
        self._append(record)
        return record

    def is_opted_out(self, candidate_uuid: str) -> bool:
        """Check if a candidate is currently opted out."""
        history = self.get_history(candidate_uuid)
        if not history:
            return False
        return history[-1].action == OptOutAction.opt_out

    def get_status(self, candidate_uuid: str) -> OptOutStatus:
        """Return full opt-out status for a candidate."""
        history = self.get_history(candidate_uuid)
        if not history:
            return OptOutStatus(
                candidate_uuid=candidate_uuid,
                is_opted_out=False,
                last_action=None,
                last_action_at=None,
                history_count=0,
            )
        latest = history[-1]
        return OptOutStatus(
            candidate_uuid=candidate_uuid,
            is_opted_out=latest.action == OptOutAction.opt_out,
            last_action=latest.action,
            last_action_at=latest.timestamp,
            history_count=len(history),
        )

    def get_all_opted_out(self) -> set[str]:
        """Return set of all candidate UUIDs currently opted out."""
        all_records = self.load_all()
        latest_by_candidate: dict[str, OptOutAction] = {}
        for record in all_records:
            latest_by_candidate[record.candidate_uuid] = record.action
        return {
            uuid
            for uuid, action in latest_by_candidate.items()
            if action == OptOutAction.opt_out
        }

    def filter_candidates(self, candidate_uuids: list[str]) -> list[str]:
        """Filter a list of candidate UUIDs, removing opted-out ones."""
        opted_out = self.get_all_opted_out()
        return [uuid for uuid in candidate_uuids if uuid not in opted_out]

    def get_history(self, candidate_uuid: str) -> list[OptOutRecord]:
        """Return all records for a candidate in chronological order."""
        all_records = self.load_all()
        return [r for r in all_records if r.candidate_uuid == candidate_uuid]

    def load_all(self) -> list[OptOutRecord]:
        """Load all records from JSONL."""
        if not self._path.exists():
            return []
        records: list[OptOutRecord] = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(OptOutRecord.model_validate_json(line))
        return records

    def get_stats(self) -> OptOutStats:
        """Return aggregate opt-out statistics."""
        all_records = self.load_all()
        total_opted_out = sum(
            1 for r in all_records if r.action == OptOutAction.opt_out
        )
        total_opt_in_reversals = sum(
            1 for r in all_records if r.action == OptOutAction.opt_in
        )
        current_opted_out_count = len(self.get_all_opted_out())
        return OptOutStats(
            total_opted_out=total_opted_out,
            total_opt_in_reversals=total_opt_in_reversals,
            current_opted_out_count=current_opted_out_count,
        )

    def _append(self, record: OptOutRecord) -> None:
        """Append a record to the JSONL file."""
        with open(self._path, "a") as f:
            f.write(record.model_dump_json() + "\n")
