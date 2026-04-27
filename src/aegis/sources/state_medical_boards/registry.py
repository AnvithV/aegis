"""Federated state medical board registry."""

from __future__ import annotations

import logging

from aegis.sources.state_medical_boards.base import (
    BoardAction,
    StateBoardClient,
)

logger = logging.getLogger(__name__)


class StateMedicalBoardRegistry:
    """Federation layer across multiple state medical board clients.

    Lookup queries all registered states and aggregates results.
    """

    def __init__(
        self, clients: list[StateBoardClient] | None = None
    ) -> None:
        self._clients: dict[str, StateBoardClient] = {}
        if clients:
            for client in clients:
                self.register(client)

    def register(self, client: StateBoardClient) -> None:
        """Register a state board client."""
        self._clients[client.state_code] = client
        logger.info("Registered state board: %s", client.state_code)

    @property
    def registered_states(self) -> list[str]:
        """List of registered state codes."""
        return sorted(self._clients.keys())

    def lookup(
        self,
        npi: str | None = None,
        name: str | None = None,
        states: list[str] | None = None,
    ) -> list[BoardAction]:
        """Look up disciplinary actions across registered states.

        Args:
            npi: NPI number to search
            name: Physician name to search
            states: Limit to specific states (default: all registered)
        """
        if npi is None and name is None:
            raise ValueError("At least one of npi or name required")

        results: list[BoardAction] = []
        target_clients = (
            [
                self._clients[s]
                for s in states
                if s in self._clients
            ]
            if states
            else list(self._clients.values())
        )

        for client in target_clients:
            try:
                actions = client.lookup(npi=npi, name=name)
                results.extend(actions)
            except Exception:
                logger.exception(
                    "Error querying %s board", client.state_code
                )

        return results

    def has_severe_action(
        self,
        npi: str | None = None,
        name: str | None = None,
    ) -> bool:
        """Check if a physician has any revocation or suspension."""
        actions = self.lookup(npi=npi, name=name)
        severe = {"revocation", "suspension"}
        return any(a.action_type.value in severe for a in actions)
