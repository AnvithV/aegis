"""Texas Medical Board (TMB) disciplinary action client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# TMB action type to severity mapping
_TX_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "restriction": ActionSeverity.restriction,
    "restricted": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "public reprimand": ActionSeverity.public_reprimand,
    "reprimand": ActionSeverity.public_reprimand,
    "warning": ActionSeverity.public_reprimand,
}


class TexasTMB(StateBoardClient):
    """Texas Medical Board client.

    Data source: TMB enforcement actions database.
    """

    @property
    def state_code(self) -> str:
        return "TX"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up TX disciplinary actions by NPI or name.

        Stub: in production, queries the TMB database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all TX disciplinary actions.

        Stub: in production, scrapes the TMB public page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a Texas action description to severity."""
        lower = action_text.lower()
        for key, severity in _TX_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
