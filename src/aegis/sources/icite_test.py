"""Tests for the iCite API client (fixture-based, no live API calls)."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from aegis.sources.icite import ICITE_API_URL, IciteClient, IciteRecord

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_RECORD: dict[str, object] = {
    "pmid": 12345678,
    "year": 2022,
    "relative_citation_ratio": 2.45,
    "citation_count": 30,
    "expected_citations_per_year": 6.1,
    "field_citation_rate": 12.3,
    "is_research_article": True,
    "doi": "10.1234/example.2022.001",
}

SAMPLE_RECORD_NULL_RCR: dict[str, object] = {
    "pmid": 99999999,
    "year": 2024,
    "relative_citation_ratio": None,
    "citation_count": 0,
    "expected_citations_per_year": None,
    "field_citation_rate": None,
    "is_research_article": False,
    "doi": None,
}


def _make_batch(n: int) -> list[dict[str, object]]:
    """Generate n distinct sample records."""
    return [
        {
            **SAMPLE_RECORD,
            "pmid": 10000000 + i,
            "citation_count": i * 5,
        }
        for i in range(n)
    ]


@pytest.fixture
def client() -> IciteClient:
    return IciteClient()


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_icite_parse_single_record() -> None:
    """IciteRecord correctly parses a sample response dict."""
    rec = IciteRecord(
        pmid=str(SAMPLE_RECORD["pmid"]),
        year=SAMPLE_RECORD["year"],  # type: ignore[arg-type]
        relative_citation_ratio=SAMPLE_RECORD["relative_citation_ratio"],  # type: ignore[arg-type]
        citation_count=SAMPLE_RECORD["citation_count"],  # type: ignore[arg-type]
        expected_citations_per_year=SAMPLE_RECORD["expected_citations_per_year"],  # type: ignore[arg-type]
        field_citation_rate=SAMPLE_RECORD["field_citation_rate"],  # type: ignore[arg-type]
        is_research_article=bool(SAMPLE_RECORD["is_research_article"]),
        doi=SAMPLE_RECORD["doi"],  # type: ignore[arg-type]
    )
    assert rec.pmid == "12345678"
    assert rec.year == 2022
    assert rec.relative_citation_ratio == 2.45
    assert rec.citation_count == 30
    assert rec.expected_citations_per_year == 6.1
    assert rec.field_citation_rate == 12.3
    assert rec.is_research_article is True
    assert rec.doi == "10.1234/example.2022.001"


@pytest.mark.asyncio
@respx.mock
async def test_icite_batch_fetch(client: IciteClient) -> None:
    """Mocked batch fetch returns all 5 records."""
    batch_data = _make_batch(5)
    respx.get(ICITE_API_URL).mock(
        return_value=Response(200, json={"data": batch_data}),
    )

    pmids = [str(r["pmid"]) for r in batch_data]
    results: list[IciteRecord] = []
    async for rec in client.fetch_by_pmids(pmids):
        results.append(rec)

    assert len(results) == 5
    assert results[0].pmid == "10000000"
    assert results[4].pmid == "10000004"
    assert results[2].citation_count == 10


@pytest.mark.asyncio
@respx.mock
async def test_icite_missing_rcr(client: IciteClient) -> None:
    """Record with null relative_citation_ratio parses as None."""
    respx.get(ICITE_API_URL).mock(
        return_value=Response(200, json={"data": [SAMPLE_RECORD_NULL_RCR]}),
    )

    results: list[IciteRecord] = []
    async for rec in client.fetch_by_pmids(["99999999"]):
        results.append(rec)

    assert len(results) == 1
    rec = results[0]
    assert rec.pmid == "99999999"
    assert rec.relative_citation_ratio is None
    assert rec.citation_count == 0
    assert rec.is_research_article is False
    assert rec.doi is None
