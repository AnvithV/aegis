"""Massachusetts Board of Registration in Medicine (BORM) client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# MA BORM action type to severity mapping
_MA_ACTION_MAP: dict[str, ActionSeverity] = {
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
    "letter of reprimand": ActionSeverity.public_reprimand,
}


class MassachusettsBORM(StateBoardClient):
    """Massachusetts Board of Registration in Medicine client.

    Data source: MA BORM public disciplinary actions.
    """

    @property
    def state_code(self) -> str:
        return "MA"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up MA disciplinary actions by NPI or name.

        Stub: in production, queries the MA BORM database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all MA disciplinary actions.

        Stub: in production, downloads from MA BORM enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a Massachusetts action description to severity."""
        lower = action_text.lower()
        for key, severity in _MA_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
