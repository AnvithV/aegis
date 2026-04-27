"""Tests for state medical board action ingestion."""

from __future__ import annotations

from aegis.sources.state_medical_boards.base import (
    ActionSeverity,
    BoardAction,
    StateBoardClient,
)
from aegis.sources.state_medical_boards.california import CaliforniaMBC
from aegis.sources.state_medical_boards.florida import FloridaDOH
from aegis.sources.state_medical_boards.illinois import IllinoisIDFPR
from aegis.sources.state_medical_boards.massachusetts import MassachusettsBORM
from aegis.sources.state_medical_boards.michigan import MichiganLARA
from aegis.sources.state_medical_boards.new_jersey import NewJerseyDCA
from aegis.sources.state_medical_boards.new_york import NewYorkOPMC
from aegis.sources.state_medical_boards.ohio import OhioSMBO
from aegis.sources.state_medical_boards.pennsylvania import PennsylvaniaPSMB
from aegis.sources.state_medical_boards.registry import (
    StateMedicalBoardRegistry,
)
from aegis.sources.state_medical_boards.texas import TexasTMB


class _MockStateBoardClient(StateBoardClient):
    """Mock state board client for testing."""

    def __init__(
        self,
        code: str,
        actions: list[BoardAction] | None = None,
    ) -> None:
        self._code = code
        self._actions = actions or []

    @property
    def state_code(self) -> str:
        return self._code

    def lookup(
        self, npi: str | None = None, name: str | None = None
    ) -> list[BoardAction]:
        return self._actions

    def fetch_all_actions(self) -> list[BoardAction]:
        return self._actions


def test_action_severity_ordering() -> None:
    """Verify ActionSeverity enum values exist in order."""
    values = list(ActionSeverity)
    assert values == [
        ActionSeverity.revocation,
        ActionSeverity.suspension,
        ActionSeverity.restriction,
        ActionSeverity.probation,
        ActionSeverity.public_reprimand,
    ]
    assert ActionSeverity.revocation.value == "revocation"
    assert ActionSeverity.suspension.value == "suspension"
    assert ActionSeverity.restriction.value == "restriction"
    assert ActionSeverity.probation.value == "probation"
    assert ActionSeverity.public_reprimand.value == "public_reprimand"


def test_california_classify_action() -> None:
    """Verify CA action text maps to correct severity."""
    assert CaliforniaMBC.classify_action("Revoked") == ActionSeverity.revocation
    assert CaliforniaMBC.classify_action("License Suspended") == ActionSeverity.suspension
    assert CaliforniaMBC.classify_action("Probation ordered") == ActionSeverity.probation
    assert (
        CaliforniaMBC.classify_action("Public Reprimand issued")
        == ActionSeverity.public_reprimand
    )
    assert (
        CaliforniaMBC.classify_action("Public Reproval")
        == ActionSeverity.public_reprimand
    )
    # Unknown action defaults to public_reprimand
    assert (
        CaliforniaMBC.classify_action("something else")
        == ActionSeverity.public_reprimand
    )


def test_registry_register() -> None:
    """Register 3 state clients, verify registered_states returns sorted list."""
    registry = StateMedicalBoardRegistry()
    registry.register(_MockStateBoardClient("TX"))
    registry.register(_MockStateBoardClient("CA"))
    registry.register(_MockStateBoardClient("NY"))
    assert registry.registered_states == ["CA", "NY", "TX"]


def test_registry_lookup_delegates() -> None:
    """Mock state client that returns a BoardAction, verify registry returns it."""
    action = BoardAction(
        state="CA",
        npi="1234567890",
        physician_name="Dr. Test",
        license_number="A12345",
        action_type=ActionSeverity.probation,
        action_date="2024-01-15",
        description="Probation for prescribing violations",
        source_url=None,
    )
    client = _MockStateBoardClient("CA", actions=[action])
    registry = StateMedicalBoardRegistry(clients=[client])

    results = registry.lookup(npi="1234567890")
    assert len(results) == 1
    assert results[0].npi == "1234567890"
    assert results[0].action_type == ActionSeverity.probation
    assert results[0].state == "CA"


def test_registry_has_severe_action() -> None:
    """Mock client with revocation, verify has_severe_action returns True."""
    action = BoardAction(
        state="NY",
        npi="9876543210",
        physician_name="Dr. Severe",
        license_number="NY99999",
        action_type=ActionSeverity.revocation,
        action_date="2023-06-01",
        description="License revoked",
        source_url=None,
    )
    client = _MockStateBoardClient("NY", actions=[action])
    registry = StateMedicalBoardRegistry(clients=[client])

    assert registry.has_severe_action(npi="9876543210") is True


def test_registry_no_actions() -> None:
    """Empty lookup returns empty list."""
    client = _MockStateBoardClient("TX")
    registry = StateMedicalBoardRegistry(clients=[client])

    results = registry.lookup(npi="0000000000")
    assert results == []
    assert registry.has_severe_action(npi="0000000000") is False


def test_registry_all_10_states() -> None:
    """All 10 state clients register correctly."""
    clients = [
        CaliforniaMBC(),
        FloridaDOH(),
        IllinoisIDFPR(),
        MassachusettsBORM(),
        MichiganLARA(),
        NewJerseyDCA(),
        NewYorkOPMC(),
        OhioSMBO(),
        PennsylvaniaPSMB(),
        TexasTMB(),
    ]
    registry = StateMedicalBoardRegistry(clients=clients)
    assert len(registry.registered_states) == 10
    assert registry.registered_states == sorted(
        ["CA", "FL", "IL", "MA", "MI", "NJ", "NY", "OH", "PA", "TX"]
    )


def test_florida_classify_action() -> None:
    """FL action text maps to correct severity."""
    assert FloridaDOH.classify_action("License Revoked") == ActionSeverity.revocation
    assert FloridaDOH.classify_action("Voluntary Relinquishment") == ActionSeverity.revocation
    assert FloridaDOH.classify_action("Suspended for 1 year") == ActionSeverity.suspension
    assert FloridaDOH.classify_action("Letter of Concern issued") == ActionSeverity.public_reprimand
    assert FloridaDOH.classify_action("unknown action") == ActionSeverity.public_reprimand


def test_pennsylvania_classify_action() -> None:
    """PA action text maps to correct severity."""
    assert PennsylvaniaPSMB.classify_action("Revocation") == ActionSeverity.revocation
    assert PennsylvaniaPSMB.classify_action("Suspended") == ActionSeverity.suspension
    assert PennsylvaniaPSMB.classify_action("Probation ordered") == ActionSeverity.probation
    assert PennsylvaniaPSMB.classify_action("Public Reprimand") == ActionSeverity.public_reprimand


def test_illinois_classify_action() -> None:
    """IL action text maps to correct severity."""
    assert IllinoisIDFPR.classify_action("License Revoked") == ActionSeverity.revocation
    assert IllinoisIDFPR.classify_action("Indefinite Suspension") == ActionSeverity.suspension
    assert IllinoisIDFPR.classify_action("Formal Complaint") == ActionSeverity.public_reprimand


def test_ohio_classify_action() -> None:
    """OH action text maps to correct severity."""
    assert OhioSMBO.classify_action("Permanent Revocation") == ActionSeverity.revocation
    assert OhioSMBO.classify_action("Probationary license") == ActionSeverity.probation
    assert OhioSMBO.classify_action("Public Reprimand") == ActionSeverity.public_reprimand


def test_michigan_classify_action() -> None:
    """MI action text maps to correct severity."""
    assert MichiganLARA.classify_action("Revocation") == ActionSeverity.revocation
    assert MichiganLARA.classify_action("Summary Suspension") == ActionSeverity.suspension
    assert MichiganLARA.classify_action("Limitation on license") == ActionSeverity.restriction


def test_new_jersey_classify_action() -> None:
    """NJ action text maps to correct severity."""
    assert NewJerseyDCA.classify_action("License Revoked") == ActionSeverity.revocation
    assert NewJerseyDCA.classify_action("Surrender of license") == ActionSeverity.revocation
    assert NewJerseyDCA.classify_action("Censure") == ActionSeverity.public_reprimand


def test_massachusetts_classify_action() -> None:
    """MA action text maps to correct severity."""
    assert MassachusettsBORM.classify_action("Revocation") == ActionSeverity.revocation
    assert MassachusettsBORM.classify_action("Suspended") == ActionSeverity.suspension
    assert MassachusettsBORM.classify_action("Letter of Reprimand") == ActionSeverity.public_reprimand


def test_board_action_model() -> None:
    """Create BoardAction, verify all fields."""
    action = BoardAction(
        state="TX",
        npi="5555555555",
        physician_name="Dr. Model",
        license_number="TX12345",
        action_type=ActionSeverity.suspension,
        action_date="2024-03-01",
        description="Suspended for 6 months",
        source_url="https://example.com/action/123",
    )
    assert action.state == "TX"
    assert action.npi == "5555555555"
    assert action.physician_name == "Dr. Model"
    assert action.license_number == "TX12345"
    assert action.action_type == ActionSeverity.suspension
    assert action.action_date == "2024-03-01"
    assert action.description == "Suspended for 6 months"
    assert action.source_url == "https://example.com/action/123"
