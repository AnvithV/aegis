"""Tests for bioRxiv and medRxiv preprint clients."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.biorxiv import (
    BIORXIV_API_URL,
    PREPRINT_WEIGHT,
    BioRxivClient,
    PreprintAuthor,
    PreprintRecord,
    match_preprint_to_publication,
)
from aegis.sources.medrxiv import MEDRXIV_API_URL, MedRxivClient


def _make_biorxiv_response(
    records: list[dict[str, Any]], total: int | None = None
) -> dict[str, Any]:
    """Build a mock bioRxiv API response."""
    if total is None:
        total = len(records)
    return {
        "messages": [{"status": "ok", "total": str(total)}],
        "collection": records,
    }


def _make_preprint_item(
    doi: str = "10.1101/2024.01.01.000001",
    title: str = "Test Preprint",
    authors: str = "Smith, J; Doe, A",
    abstract: str = "Test abstract",
    category: str = "neuroscience",
    date_str: str = "2024-01-15",
    version: str = "1",
    published: str = "",
) -> dict[str, Any]:
    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "category": category,
        "date": date_str,
        "version": version,
        "published": published,
    }


def test_preprint_record_model() -> None:
    """Create a PreprintRecord with all fields, verify serialization."""
    author = PreprintAuthor(
        full_name="Smith, J",
        institution="MIT",
        orcid="0000-0001-2345-6789",
        is_corresponding=True,
    )
    record = PreprintRecord(
        doi="10.1101/2024.01.01.000001",
        title="Test Preprint",
        abstract="Test abstract",
        authors=[author],
        category="neuroscience",
        posted_date=date(2024, 1, 15),
        version=1,
        server="biorxiv",
        published_doi=None,
        mesh_descriptors=[],
    )
    assert record.doi == "10.1101/2024.01.01.000001"
    assert record.title == "Test Preprint"
    assert record.server == "biorxiv"
    assert record.weight == PREPRINT_WEIGHT
    assert len(record.authors) == 1
    data = record.model_dump()
    assert data["doi"] == "10.1101/2024.01.01.000001"


def test_preprint_author_model() -> None:
    """Create a PreprintAuthor with all fields, verify serialization."""
    author = PreprintAuthor(
        full_name="Smith, J",
        institution="MIT",
        orcid="0000-0001-2345-6789",
        is_corresponding=True,
    )
    assert author.full_name == "Smith, J"
    assert author.institution == "MIT"
    assert author.orcid == "0000-0001-2345-6789"
    assert author.is_corresponding is True
    data = author.model_dump()
    assert data["full_name"] == "Smith, J"


def test_preprint_weight() -> None:
    """Assert PREPRINT_WEIGHT == 0.6."""
    assert PREPRINT_WEIGHT == 0.6


def test_biorxiv_parse_record() -> None:
    """Call BioRxivClient._parse_record with a mock item dict."""
    item = _make_preprint_item(
        doi="10.1101/2024.01.01.000001",
        title="Test Preprint",
        authors="Smith, J; Doe, A",
        abstract="Test abstract",
        category="neuroscience",
        date_str="2024-01-15",
        version="2",
        published="10.1000/journal.001",
    )
    record = BioRxivClient._parse_record(item)
    assert record is not None
    assert record.doi == "10.1101/2024.01.01.000001"
    assert record.title == "Test Preprint"
    assert record.abstract == "Test abstract"
    assert record.category == "neuroscience"
    assert record.posted_date == date(2024, 1, 15)
    assert record.version == 2
    assert record.server == "biorxiv"
    assert record.published_doi == "10.1000/journal.001"
    assert len(record.authors) == 2


def test_biorxiv_parse_record_missing_fields() -> None:
    """Call with minimal dict (only doi), verify parsing succeeds."""
    item = {"doi": "10.1101/min"}
    record = BioRxivClient._parse_record(item)
    assert record is not None
    assert record.doi == "10.1101/min"
    assert record.title == ""
    assert record.abstract is None
    assert record.posted_date is None
    assert record.authors == []
    assert record.published_doi is None


def test_biorxiv_author_parsing() -> None:
    """Verify semicolon-separated author string is split correctly."""
    item = _make_preprint_item(authors="Smith, J; Doe, A; Lee, B")
    record = BioRxivClient._parse_record(item)
    assert record is not None
    assert len(record.authors) == 3
    assert record.authors[0].full_name == "Smith, J"
    assert record.authors[1].full_name == "Doe, A"
    assert record.authors[2].full_name == "Lee, B"
    for author in record.authors:
        assert author.institution is None
        assert author.orcid is None
        assert author.is_corresponding is False


@pytest.mark.asyncio
@respx.mock
async def test_biorxiv_fetch_daily() -> None:
    """Mock GET to BIORXIV_API_URL returning 2 preprints."""
    items = [
        _make_preprint_item(doi="10.1101/001"),
        _make_preprint_item(doi="10.1101/002"),
    ]
    respx.get(f"{BIORXIV_API_URL}/2024-01-15/2024-01-15/0").mock(
        return_value=Response(200, json=_make_biorxiv_response(items))
    )
    client = BioRxivClient()
    records = [r async for r in client.fetch_daily(date(2024, 1, 15))]
    assert len(records) == 2
    assert records[0].doi == "10.1101/001"
    assert records[1].doi == "10.1101/002"


@pytest.mark.asyncio
@respx.mock
async def test_biorxiv_fetch_daily_pagination() -> None:
    """Mock two pages: first returns 2 records with total=3, second returns 1."""
    page1_items = [
        _make_preprint_item(doi="10.1101/001"),
        _make_preprint_item(doi="10.1101/002"),
    ]
    page2_items = [
        _make_preprint_item(doi="10.1101/003"),
    ]
    respx.get(f"{BIORXIV_API_URL}/2024-01-15/2024-01-15/0").mock(
        return_value=Response(200, json=_make_biorxiv_response(page1_items, total=3))
    )
    respx.get(f"{BIORXIV_API_URL}/2024-01-15/2024-01-15/2").mock(
        return_value=Response(200, json=_make_biorxiv_response(page2_items, total=3))
    )
    client = BioRxivClient()
    records = [r async for r in client.fetch_daily(date(2024, 1, 15))]
    assert len(records) == 3


@pytest.mark.asyncio
@respx.mock
async def test_biorxiv_fetch_daily_empty() -> None:
    """Mock response with empty collection, verify 0 records."""
    respx.get(f"{BIORXIV_API_URL}/2024-01-15/2024-01-15/0").mock(
        return_value=Response(200, json=_make_biorxiv_response([]))
    )
    client = BioRxivClient()
    records = [r async for r in client.fetch_daily(date(2024, 1, 15))]
    assert len(records) == 0


def test_medrxiv_parse_record() -> None:
    """Call MedRxivClient._parse_record, verify server == medrxiv."""
    item = _make_preprint_item(doi="10.1101/med001")
    record = MedRxivClient._parse_record(item)
    assert record is not None
    assert record.server == "medrxiv"
    assert record.doi == "10.1101/med001"


@pytest.mark.asyncio
@respx.mock
async def test_medrxiv_fetch_daily() -> None:
    """Mock GET to MEDRXIV_API_URL, verify fetch_daily works."""
    items = [
        _make_preprint_item(doi="10.1101/med001"),
    ]
    respx.get(f"{MEDRXIV_API_URL}/2024-01-15/2024-01-15/0").mock(
        return_value=Response(200, json=_make_biorxiv_response(items))
    )
    client = MedRxivClient()
    records = [r async for r in client.fetch_daily(date(2024, 1, 15))]
    assert len(records) == 1
    assert records[0].server == "medrxiv"


def test_preprint_to_publication_collapse() -> None:
    """Create a preprint, collapse it, verify published_doi and weight."""
    preprint = PreprintRecord(
        doi="10.1101/2024.01.01.000001",
        title="Test",
        abstract=None,
        authors=[],
        category=None,
        posted_date=date(2024, 1, 15),
        version=1,
        server="biorxiv",
        published_doi=None,
        mesh_descriptors=[],
    )
    collapsed = match_preprint_to_publication(preprint, "10.1000/journal.001")
    assert collapsed.published_doi == "10.1000/journal.001"
    assert collapsed.weight == 0.0


def test_preprint_to_publication_preserves_fields() -> None:
    """Verify all other fields are preserved after collapse."""
    author = PreprintAuthor(
        full_name="Smith, J",
        institution="MIT",
        orcid="0000-0001",
        is_corresponding=True,
    )
    preprint = PreprintRecord(
        doi="10.1101/2024.01.01.000001",
        title="My Preprint",
        abstract="Abstract text",
        authors=[author],
        category="neuroscience",
        posted_date=date(2024, 1, 15),
        version=2,
        server="biorxiv",
        published_doi=None,
        mesh_descriptors=[],
    )
    collapsed = match_preprint_to_publication(preprint, "10.1000/pub.001")
    assert collapsed.doi == preprint.doi
    assert collapsed.title == preprint.title
    assert collapsed.abstract == preprint.abstract
    assert collapsed.authors == preprint.authors
    assert collapsed.category == preprint.category
    assert collapsed.posted_date == preprint.posted_date
    assert collapsed.version == preprint.version
    assert collapsed.server == preprint.server
    assert collapsed.mesh_descriptors == preprint.mesh_descriptors
    assert collapsed.published_doi == "10.1000/pub.001"
    assert collapsed.weight == 0.0


def test_preprint_default_weight() -> None:
    """Verify a fresh PreprintRecord has weight == PREPRINT_WEIGHT."""
    record = PreprintRecord(
        doi="10.1101/test",
        title="Test",
        abstract=None,
        authors=[],
        category=None,
        posted_date=None,
        version=1,
        server="biorxiv",
        published_doi=None,
        mesh_descriptors=[],
    )
    assert record.weight == PREPRINT_WEIGHT
    assert record.weight == 0.6
