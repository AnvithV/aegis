"""Tests for Retraction Watch database source client."""

from __future__ import annotations

from datetime import date

from aegis.sources.retraction_watch import RetractionRecord, RetractionWatchStore


def _make_record(
    title: str = "Retracted Paper",
    authors: list[str] | None = None,
    pmid: str | None = "12345678",
) -> RetractionRecord:
    return RetractionRecord(
        title=title,
        authors=authors or ["John Smith", "Jane Doe"],
        pmid=pmid,
        doi="10.1000/test",
        journal="Test Journal",
        retraction_date=date(2023, 1, 1),
        reason="Data fabrication",
        original_paper_date=date(2020, 6, 15),
    )


def test_lookup_by_author_substring() -> None:
    store = RetractionWatchStore()
    store.add_batch([_make_record(authors=["John Smith", "Alice Wong"])])

    # Substring match
    results = store.lookup_by_author("Smith")
    assert len(results) == 1

    results = store.lookup_by_author("John")
    assert len(results) == 1


def test_lookup_by_author_case_insensitive() -> None:
    store = RetractionWatchStore()
    store.add_batch([_make_record(authors=["John Smith"])])

    assert len(store.lookup_by_author("john smith")) == 1
    assert len(store.lookup_by_author("JOHN SMITH")) == 1
    assert len(store.lookup_by_author("john")) == 1


def test_lookup_by_author_no_match() -> None:
    store = RetractionWatchStore()
    store.add_batch([_make_record(authors=["John Smith"])])

    assert store.lookup_by_author("Nobody") == []


def test_lookup_by_pmid() -> None:
    store = RetractionWatchStore()
    store.add_batch([
        _make_record(pmid="11111111"),
        _make_record(pmid="22222222"),
    ])

    results = store.lookup_by_pmid("11111111")
    assert len(results) == 1

    assert store.lookup_by_pmid("99999999") == []


def test_lookup_by_pmid_none() -> None:
    store = RetractionWatchStore()
    store.add_batch([_make_record(pmid=None)])

    assert store.lookup_by_pmid("12345678") == []


def test_count() -> None:
    store = RetractionWatchStore()
    assert store.count() == 0

    store.add_batch([_make_record(), _make_record(title="Another")])
    assert store.count() == 2


def test_multiple_retractions_same_author() -> None:
    store = RetractionWatchStore()
    store.add_batch([
        _make_record(title="Paper 1", authors=["John Smith"]),
        _make_record(title="Paper 2", authors=["John Smith", "Bob Chen"]),
        _make_record(title="Paper 3", authors=["Alice Wong"]),
    ])

    results = store.lookup_by_author("John Smith")
    assert len(results) == 2
    assert {r.title for r in results} == {"Paper 1", "Paper 2"}
