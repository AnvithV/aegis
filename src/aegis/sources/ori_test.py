"""Tests for ORI research misconduct findings source client."""

from __future__ import annotations

from datetime import date

from aegis.sources.ori import ORIFinding, ORIStore


def _make_finding(
    name: str = "John Doe",
    finding_date: date = date(2020, 3, 15),
) -> ORIFinding:
    return ORIFinding(
        name=name,
        institution="MIT",
        finding_date=finding_date,
        misconduct_type="Fabrication",
        settlement_type="Debarment",
        debarment_end_date=None,
    )


def test_lookup_by_name() -> None:
    store = ORIStore()
    store.add_batch([
        _make_finding("Alice Smith"),
        _make_finding("Bob Jones"),
    ])

    results = store.lookup_by_name("Alice Smith")
    assert len(results) == 1
    assert results[0].name == "Alice Smith"

    assert store.lookup_by_name("alice smith") == [results[0]]
    assert store.lookup_by_name("Nobody") == []


def test_has_recent_finding_within_window() -> None:
    store = ORIStore()
    store.add_batch([_make_finding("Jane Doe", finding_date=date(2022, 6, 1))])

    assert store.has_recent_finding("Jane Doe", as_of=date(2026, 1, 1)) is True


def test_has_recent_finding_outside_window() -> None:
    store = ORIStore()
    store.add_batch([_make_finding("Jane Doe", finding_date=date(2010, 1, 1))])

    assert (
        store.has_recent_finding("Jane Doe", years=10, as_of=date(2026, 1, 1)) is False
    )


def test_has_recent_finding_custom_window() -> None:
    store = ORIStore()
    store.add_batch([_make_finding("Jane Doe", finding_date=date(2022, 1, 1))])

    # 3-year window from 2026 -> cutoff 2023, finding in 2022 is outside
    assert (
        store.has_recent_finding("Jane Doe", years=3, as_of=date(2026, 1, 1)) is False
    )
    # 5-year window from 2026 -> cutoff 2021, finding in 2022 is inside
    assert store.has_recent_finding("Jane Doe", years=5, as_of=date(2026, 1, 1)) is True


def test_has_recent_finding_case_insensitive() -> None:
    store = ORIStore()
    store.add_batch([_make_finding("Jane Doe", finding_date=date(2024, 1, 1))])

    assert store.has_recent_finding("jane doe", as_of=date(2026, 1, 1)) is True
    assert store.has_recent_finding("JANE DOE", as_of=date(2026, 1, 1)) is True


def test_count() -> None:
    store = ORIStore()
    assert store.count() == 0

    store.add_batch([_make_finding(), _make_finding("Jane")])
    assert store.count() == 2
