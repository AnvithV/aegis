"""Illinois IDFPR (Dept. of Financial and Professional Regulation) medical client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# IL IDFPR action type to severity mapping
_IL_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "surrender": ActionSeverity.revocation,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "indefinite suspension": ActionSeverity.suspension,
    "restriction": ActionSeverity.restriction,
    "restricted": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "reprimand": ActionSeverity.public_reprimand,
    "formal complaint": ActionSeverity.public_reprimand,
}


class IllinoisIDFPR(StateBoardClient):
    """Illinois IDFPR Medical Disciplinary Board client.

    Data source: IL IDFPR public disciplinary actions.
    """

    @property
    def state_code(self) -> str:
        return "IL"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up IL disciplinary actions by NPI or name.

        Stub: in production, queries the IL IDFPR database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all IL disciplinary actions.

        Stub: in production, downloads from IL IDFPR enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map an Illinois action description to severity."""
        lower = action_text.lower()
        for key, severity in _IL_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
