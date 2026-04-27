"""Base class for state medical board clients."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ActionSeverity(StrEnum):
    """Severity classification for disciplinary actions.

    Ordered from most to least severe.
    """

    revocation = "revocation"
    suspension = "suspension"
    restriction = "restriction"
    probation = "probation"
    public_reprimand = "public_reprimand"


class BoardAction(BaseModel):
    """A single disciplinary action from a state medical board."""

    model_config = ConfigDict(frozen=True)

    state: str                     # Two-letter state code
    npi: str | None                # NPI if available
    physician_name: str
    license_number: str | None
    action_type: ActionSeverity
    action_date: str | None        # ISO date string
    description: str | None
    source_url: str | None


class StateBoardClient(ABC):
    """Abstract base for per-state medical board clients."""

    @property
    @abstractmethod
    def state_code(self) -> str:
        """Two-letter state code (e.g., 'CA')."""
        ...

    @abstractmethod
    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        """Look up disciplinary actions by NPI or name.

        At least one of npi or name must be provided.
        """
        ...

    @abstractmethod
    def fetch_all_actions(self) -> list[BoardAction]:
        """Fetch all known disciplinary actions for this state.

        Used for bulk loading; may be expensive.
        """
        ...
