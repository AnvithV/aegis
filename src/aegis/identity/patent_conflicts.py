"""Patent inventor disambiguation conflict handler.

Surfaces split/merge conflicts for HITL review and tracks
excluded patents that should be removed from scoring.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class PatentConflict(BaseModel):
    """A single patent inventor disambiguation conflict."""

    model_config = ConfigDict(frozen=True)

    conflict_id: str
    patent_number: str
    inventor_name: str
    patentsview_inventor_id: str
    aegis_candidate_uuid: str | None
    conflict_type: Literal["split", "merge"]
    confidence_gap: float
    created_at: datetime
    status: Literal["pending", "resolved", "excluded"]


class PatentConflictHandler:
    """Track and manage patent inventor disambiguation conflicts."""

    def __init__(self) -> None:
        self._conflicts: list[PatentConflict] = []

    def report_conflict(
        self,
        patent_number: str,
        inventor_name: str,
        patentsview_id: str,
        aegis_uuid: str | None,
        conflict_type: Literal["split", "merge"],
        confidence_gap: float,
    ) -> PatentConflict:
        """Report a new patent disambiguation conflict."""
        conflict = PatentConflict(
            conflict_id=str(uuid.uuid4()),
            patent_number=patent_number,
            inventor_name=inventor_name,
            patentsview_inventor_id=patentsview_id,
            aegis_candidate_uuid=aegis_uuid,
            conflict_type=conflict_type,
            confidence_gap=confidence_gap,
            created_at=datetime.now(UTC),
            status="pending",
        )
        self._conflicts.append(conflict)
        logger.warning(
            "Patent conflict reported: %s %s for patent %s (gap=%.3f)",
            conflict_type,
            inventor_name,
            patent_number,
            confidence_gap,
        )
        return conflict

    def get_pending(self) -> list[PatentConflict]:
        """Return all pending (unresolved) conflicts."""
        return [c for c in self._conflicts if c.status == "pending"]

    def get_excluded_patents(self) -> set[str]:
        """Return patent numbers that should be excluded from scoring.

        Patents with pending or excluded status are excluded from v_c.
        """
        return {
            c.patent_number
            for c in self._conflicts
            if c.status in ("pending", "excluded")
        }

    @property
    def conflict_rate(self) -> int:
        """Return the total number of conflicts recorded."""
        return len(self._conflicts)
