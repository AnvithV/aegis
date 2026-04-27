"""Tests for OFAC/SAM sanctions list source client."""

from __future__ import annotations

from aegis.sources.ofac_sam import OFACSAMRecord, OFACSAMStore


def _make_record(
    name: str = "John Doe",
    aliases: list[str] | None = None,
    source: str = "OFAC",
) -> OFACSAMRecord:
    return OFACSAMRecord(
        primary_name=name,
        aliases=aliases or [],
        source=source,
        record_type="Individual",
        program=None,
        remarks=None,
    )


def test_is_listed_by_primary_name() -> None:
    store = OFACSAMStore()
    store.add_batch([_make_record("Evil Corp")])

    assert store.is_listed("Evil Corp") is True
    assert store.is_listed("evil corp") is True
    assert store.is_listed("Good Corp") is False


def test_is_listed_by_alias() -> None:
    store = OFACSAMStore()
    store.add_batch([_make_record("Primary Name", aliases=["Alias One", "Alias Two"])])

    assert store.is_listed("Alias One") is True
    assert store.is_listed("alias two") is True
    assert store.is_listed("Alias Three") is False


def test_is_listed_case_insensitive() -> None:
    store = OFACSAMStore()
    store.add_batch([_make_record("JOHN DOE", aliases=["J. DOE"])])

    assert store.is_listed("john doe") is True
    assert store.is_listed("John Doe") is True
    assert store.is_listed("j. doe") is True


def test_count() -> None:
    store = OFACSAMStore()
    assert store.count() == 0

    store.add_batch([_make_record("A"), _make_record("B")])
    assert store.count() == 2


def test_mixed_sources() -> None:
    store = OFACSAMStore()
    store.add_batch([
        _make_record("OFAC Person", source="OFAC"),
        _make_record("SAM Person", source="SAM"),
    ])

    assert store.is_listed("OFAC Person") is True
    assert store.is_listed("SAM Person") is True
    assert store.count() == 2
