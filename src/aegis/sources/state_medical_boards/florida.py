"""Florida Department of Health (DOH) Medical Quality Assurance client."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)

# FL DOH MQA action type to severity mapping
_FL_ACTION_MAP: dict[str, ActionSeverity] = {
    "revocation": ActionSeverity.revocation,
    "revoked": ActionSeverity.revocation,
    "voluntary relinquishment": ActionSeverity.revocation,
    "suspension": ActionSeverity.suspension,
    "suspended": ActionSeverity.suspension,
    "restriction": ActionSeverity.restriction,
    "restricted": ActionSeverity.restriction,
    "limitation": ActionSeverity.restriction,
    "probation": ActionSeverity.probation,
    "reprimand": ActionSeverity.public_reprimand,
    "letter of concern": ActionSeverity.public_reprimand,
}


class FloridaDOH(StateBoardClient):
    """Florida Department of Health Medical Quality Assurance client.

    Data source: FL DOH MQA public disciplinary actions.
    """

    @property
    def state_code(self) -> str:
        return "FL"

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up FL disciplinary actions by NPI or name.

        Stub: in production, queries the FL DOH MQA database.
        """
        return []

    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all FL disciplinary actions.

        Stub: in production, downloads from FL DOH MQA enforcement page.
        """
        return []

    @staticmethod
    def classify_action(action_text: str) -> ActionSeverity:
        """Map a Florida action description to severity."""
        lower = action_text.lower()
        for key, severity in _FL_ACTION_MAP.items():
            if key in lower:
                return severity
        return ActionSeverity.public_reprimand
