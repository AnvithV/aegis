"""California Medical Board (MBC) disciplinary action client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# MBC action type to severity mapping
_CA_ACTION_MAP: dict[str, ActionSeverity] = {
    "revoked": ActionSeverity.revocation,
    "revocation": ActionSeverity.revocation,
    "suspended": ActionSeverity.suspension,
    "suspension": ActionSeverity.suspension,
    "restricted": ActionSeverity.restriction,
    "restriction": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "public reprimand": ActionSeverity.public_reprimand,
    "public reproval": ActionSeverity.public_reprimand,
}


class CaliforniaMBC(StateBoardClient):
    """California Medical Board client.

    Data source: CA DCA License Lookup / MBC enforcement actions.
    """

    @property
    def state_code(self) -> str:
        return "CA"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up CA disciplinary actions by NPI or name.

        Stub: in production, queries the MBC public database.
        """
        # Production: HTTP query to MBC enforcement API
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all CA disciplinary actions.

        Stub: in production, scrapes the MBC enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a California action description to severity."""
        lower = action_text.lower()
        for key, severity in _CA_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
