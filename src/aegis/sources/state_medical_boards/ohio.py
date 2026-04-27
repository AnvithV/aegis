"""State Medical Board of Ohio (SMBO) disciplinary action client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# Ohio SMBO action type to severity mapping
_OH_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "permanent revocation": ActionSeverity.revocation,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "restriction": ActionSeverity.restriction,
    "restricted": ActionSeverity.restriction,
    "probationary": ActionSeverity.probation,
    "probation": ActionSeverity.probation,
    "reprimand": ActionSeverity.public_reprimand,
    "public reprimand": ActionSeverity.public_reprimand,
}


class OhioSMBO(StateBoardClient):
    """State Medical Board of Ohio client.

    Data source: Ohio SMBO public enforcement actions.
    """

    @property
    def state_code(self) -> str:
        return "OH"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up OH disciplinary actions by NPI or name.

        Stub: in production, queries the Ohio SMBO database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all OH disciplinary actions.

        Stub: in production, downloads from Ohio SMBO enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map an Ohio action description to severity."""
        lower = action_text.lower()
        for key, severity in _OH_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
