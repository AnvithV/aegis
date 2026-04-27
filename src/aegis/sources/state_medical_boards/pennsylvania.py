"""Pennsylvania State Medical Board (PSMB) disciplinary action client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# PA State Medical Board action type to severity mapping
_PA_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "surrender": ActionSeverity.revocation,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "restriction": ActionSeverity.restriction,
    "restricted": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "reprimand": ActionSeverity.public_reprimand,
    "public reprimand": ActionSeverity.public_reprimand,
}


class PennsylvaniaPSMB(StateBoardClient):
    """Pennsylvania State Medical Board client.

    Data source: PA State Medical Board public enforcement actions.
    """

    @property
    def state_code(self) -> str:
        return "PA"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up PA disciplinary actions by NPI or name.

        Stub: in production, queries the PA PSMB database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all PA disciplinary actions.

        Stub: in production, downloads from PA PSMB enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a Pennsylvania action description to severity."""
        lower = action_text.lower()
        for key, severity in _PA_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
