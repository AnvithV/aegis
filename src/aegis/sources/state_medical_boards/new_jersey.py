"""New Jersey Division of Consumer Affairs (DCA) medical board client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# NJ DCA action type to severity mapping
_NJ_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "surrender": ActionSeverity.revocation,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "restriction": ActionSeverity.restriction,
    "restricted": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "reprimand": ActionSeverity.public_reprimand,
    "censure": ActionSeverity.public_reprimand,
}


class NewJerseyDCA(StateBoardClient):
    """New Jersey Division of Consumer Affairs Medical Board client.

    Data source: NJ DCA public disciplinary actions.
    """

    @property
    def state_code(self) -> str:
        return "NJ"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up NJ disciplinary actions by NPI or name.

        Stub: in production, queries the NJ DCA database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all NJ disciplinary actions.

        Stub: in production, downloads from NJ DCA enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a New Jersey action description to severity."""
        lower = action_text.lower()
        for key, severity in _NJ_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
