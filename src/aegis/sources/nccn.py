"""NCCN guideline panel roster ingestion (Phase 1: NSCLC panel only)."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class NCCNPanelMember(BaseModel):
    """A member of an NCCN guideline panel."""

    model_config = ConfigDict(frozen=True)

    name: str
    institution: str | None
    panel_name: str
    role: str | None  # "Chair", "Vice Chair", "Member"
    guideline_version: str | None


class NCCNPanelStore:
    """In-memory store for NCCN guideline panel rosters.

    Phase 1: manually curated NSCLC panel only.
    Phase 3: automated PDF extraction across all panels.
    """

    def __init__(self) -> None:
        self._members: list[NCCNPanelMember] = []

    def add_batch(self, members: list[NCCNPanelMember]) -> None:
        self._members.extend(members)

    def is_panel_member(self, name: str, panel_name: str | None = None) -> bool:
        """Check if a name appears on any (or a specific) panel."""
        name_lower = name.lower()
        for m in self._members:
            if m.name.lower() == name_lower:
                if panel_name is None or m.panel_name.lower() == panel_name.lower():
                    return True
        return False

    def lookup_by_name(self, name: str) -> list[NCCNPanelMember]:
        name_lower = name.lower()
        return [m for m in self._members if m.name.lower() == name_lower]

    def list_panel(self, panel_name: str) -> list[NCCNPanelMember]:
        panel_lower = panel_name.lower()
        return [m for m in self._members if m.panel_name.lower() == panel_lower]

    def count(self) -> int:
        return len(self._members)
