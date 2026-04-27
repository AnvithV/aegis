"""Tests for apex roster store."""

from __future__ import annotations

from aegis.sources.apex_rosters import ApexMembership, ApexRosterStore, ApexRosterType


def _make_membership(
    name: str,
    roster_type: ApexRosterType = ApexRosterType.hhmi_investigator,
    year: int | None = 2020,
    institution: str | None = "MIT",
    confidence: float = 0.95,
) -> ApexMembership:
    return ApexMembership(
        roster_type=roster_type,
        name=name,
        year=year,
        institution=institution,
        confidence=confidence,
    )


def test_add_and_lookup() -> None:
    store = ApexRosterStore()
    store.add(_make_membership("Alice Smith"))
    store.add(_make_membership("Bob Jones", roster_type=ApexRosterType.nas_member))
    store.add(_make_membership("Carol Lee", roster_type=ApexRosterType.lasker_laureate))

    results = store.lookup_by_name("Alice Smith")
    assert len(results) == 1
    assert results[0].name == "Alice Smith"
    assert results[0].roster_type == ApexRosterType.hhmi_investigator


def test_lookup_case_insensitive() -> None:
    store = ApexRosterStore()
    store.add(_make_membership("Alice Smith"))

    results = store.lookup_by_name("alice smith")
    assert len(results) == 1
    assert results[0].name == "Alice Smith"

    results = store.lookup_by_name("ALICE SMITH")
    assert len(results) == 1
    assert results[0].name == "Alice Smith"


def test_lookup_with_institution_disambiguation() -> None:
    store = ApexRosterStore()
    store.add(_make_membership("John Doe", institution="MIT"))
    store.add(_make_membership("John Doe", institution="Stanford University"))

    # Without institution, returns both
    results = store.lookup_by_name("John Doe")
    assert len(results) == 2

    # With institution, narrows to one
    results = store.lookup_by_name("John Doe", institution="Stanford")
    assert len(results) == 1
    assert results[0].institution == "Stanford University"


def test_list_by_roster() -> None:
    store = ApexRosterStore()
    store.add(
        _make_membership("Alice Smith", roster_type=ApexRosterType.hhmi_investigator)
    )
    store.add(_make_membership("Bob Jones", roster_type=ApexRosterType.nas_member))
    store.add(
        _make_membership("Carol Lee", roster_type=ApexRosterType.hhmi_investigator)
    )

    hhmi = store.list_by_roster(ApexRosterType.hhmi_investigator)
    assert len(hhmi) == 2
    assert {m.name for m in hhmi} == {"Alice Smith", "Carol Lee"}

    nas = store.list_by_roster(ApexRosterType.nas_member)
    assert len(nas) == 1
    assert nas[0].name == "Bob Jones"


def test_count() -> None:
    store = ApexRosterStore()
    members = [
        _make_membership("Alice Smith"),
        _make_membership("Bob Jones"),
        _make_membership("Carol Lee"),
        _make_membership("David Kim"),
        _make_membership("Eve Chen"),
    ]
    store.add_batch(members)
    assert store.count() == 5
