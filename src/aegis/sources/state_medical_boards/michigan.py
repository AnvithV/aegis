"""Michigan LARA (Licensing and Regulatory Affairs) medical board client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# MI LARA action type to severity mapping
_MI_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "summary suspension": ActionSeverity.suspension,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "limitation": ActionSeverity.restriction,
    "restricted": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "reprimand": ActionSeverity.public_reprimand,
    "formal complaint": ActionSeverity.public_reprimand,
}


class MichiganLARA(StateBoardClient):
    """Michigan LARA Medical Board client.

    Data source: MI LARA public disciplinary actions.
    """

    @property
    def state_code(self) -> str:
        return "MI"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up MI disciplinary actions by NPI or name.

        Stub: in production, queries the MI LARA database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all MI disciplinary actions.

        Stub: in production, downloads from MI LARA enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a Michigan action description to severity."""
        lower = action_text.lower()
        for key, severity in _MI_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
