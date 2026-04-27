"""New York OPMC (Office of Professional Medical Conduct) client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# NY OPMC action type to severity mapping
_NY_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "surrender": ActionSeverity.revocation,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "limitation": ActionSeverity.restriction,
    "restriction": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "censure and reprimand": ActionSeverity.public_reprimand,
    "censure": ActionSeverity.public_reprimand,
    "reprimand": ActionSeverity.public_reprimand,
}


class NewYorkOPMC(StateBoardClient):
    """New York OPMC client.

    Data source: NY OPMC public enforcement actions.
    """

    @property
    def state_code(self) -> str:
        return "NY"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up NY disciplinary actions by NPI or name.

        Stub: in production, queries the OPMC database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all NY disciplinary actions.

        Stub: in production, scrapes the OPMC public page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a New York action description to severity."""
        lower = action_text.lower()
        for key, severity in _NY_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
