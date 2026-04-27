"""Tests for LEIE exclusion list source client."""

from __future__ import annotations

from datetime import date

from aegis.sources.leie import LEIERecord, LEIEStore


def _make_record(
    first: str = "John",
    last: str = "Doe",
    npi: str | None = "1234567890",
    reinstate: date | None = None,
) -> LEIERecord:
    return LEIERecord(
        first_name=first,
        last_name=last,
        npi=npi,
        exclusion_type="1128(a)(1)",
        exclusion_date=date(2020, 1, 15),
        reinstate_date=reinstate,
        state="NY",
        specialty="General Practice",
    )


def test_is_excluded_by_npi() -> None:
    store = LEIEStore()
    store.add_batch([_make_record(npi="1111111111")])

    assert store.is_excluded(npi="1111111111") is True
    assert store.is_excluded(npi="9999999999") is False


def test_is_excluded_by_name() -> None:
    store = LEIEStore()
    store.add_batch([_make_record(first="Jane", last="Smith", npi=None)])

    assert store.is_excluded(name="Jane Smith") is True
    assert store.is_excluded(name="jane smith") is True
    assert store.is_excluded(name="Smith, Jane") is True
    assert store.is_excluded(name="Unknown Person") is False


def test_is_excluded_npi_takes_priority() -> None:
    store = LEIEStore()
    store.add_batch([_make_record(first="Jane", last="Smith", npi="5555555555")])

    # NPI match found, returns True
    assert store.is_excluded(npi="5555555555", name="Wrong Name") is True


def test_is_excluded_reinstated_returns_none() -> None:
    store = LEIEStore()
    store.add_batch([
        _make_record(npi="2222222222", reinstate=date(2023, 6, 1)),
    ])

    assert store.is_excluded(npi="2222222222") is None


def test_lookup_by_name() -> None:
    store = LEIEStore()
    store.add_batch([
        _make_record(first="Alice", last="Wong"),
        _make_record(first="Bob", last="Chen"),
    ])

    results = store.lookup_by_name("Alice Wong")
    assert len(results) == 1
    assert results[0].first_name == "Alice"

    assert store.lookup_by_name("Nobody Here") == []


def test_count() -> None:
    store = LEIEStore()
    assert store.count() == 0

    store.add_batch([_make_record(), _make_record(first="Jane")])
    assert store.count() == 2
