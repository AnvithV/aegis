"""Tests for the OpenAlex unified client (mocked, no live API calls)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from aegis.sources.openalex import (
    OpenAlexAuthor,
    OpenAlexClient,
    OpenAlexConcept,
    OpenAlexWork,
)

# ── Fixture data ──────────────────────────────────────────────────────────────

_WORK_ITEM = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.1234/test",
    "title": "KRAS G12C Inhibitors in Lung Cancer",
    "publication_date": "2024-03-15",
    "type": "journal-article",
    "cited_by_count": 42,
    "concepts": [
        {"id": "C123", "display_name": "Oncology", "score": 0.95},
        {"id": "C456", "display_name": "Drug Discovery", "score": 0.80},
    ],
    "authorships": [
        {
            "author": {
                "id": "https://openalex.org/A5023888391",
                "display_name": "Jane Smith",
                "orcid": "https://orcid.org/0000-0001-2345-6789",
            },
            "author_position": "first",
        },
        {
            "author": {
                "id": "https://openalex.org/A5023888392",
                "display_name": "John Doe",
                "orcid": None,
            },
            "author_position": "last",
        },
    ],
    "primary_location": {
        "source": {
            "id": "https://openalex.org/S12345",
            "display_name": "Nature Medicine",
        },
    },
    "mesh": [
        {"descriptor_name": "Lung Neoplasms"},
        {"descriptor_name": "Proto-Oncogene Proteins p21(ras)"},
    ],
    "grants": [
        {
            "funder": "https://openalex.org/F4320332161",
            "award_id": "ERC-2023-STG-101",
        },
    ],
}

_AUTHOR_ITEM = {
    "id": "https://openalex.org/A5023888391",
    "display_name": "Jane Smith",
    "orcid": "https://orcid.org/0000-0001-2345-6789",
    "works_count": 150,
    "cited_by_count": 5000,
    "last_known_institutions": [
        {
            "id": "https://openalex.org/I123",
            "display_name": "Harvard University",
            "country_code": "US",
        },
    ],
    "x_concepts": [
        {"id": "C123", "display_name": "Oncology", "score": 0.9},
    ],
}

_FUNDER_ITEM = {
    "id": "https://openalex.org/F4320332161",
    "display_name": "European Research Council",
    "country_code": "EU",
    "grants_count": 12000,
    "works_count": 350000,
}


def _works_response(
    results: list[dict[str, object]],
    next_cursor: str | None = None,
) -> dict[str, object]:
    return {
        "meta": {
            "count": len(results),
            "next_cursor": next_cursor,
        },
        "results": results,
    }


def _authors_response(results: list[dict[str, object]]) -> dict[str, object]:
    return {"meta": {"count": len(results)}, "results": results}


def _funders_response(results: list[dict[str, object]]) -> dict[str, object]:
    return {"meta": {"count": len(results)}, "results": results}


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def client() -> OpenAlexClient:
    return OpenAlexClient(mailto="test@example.com")


@respx.mock
@pytest.mark.anyio
async def test_search_works_returns_parsed_objects(client: OpenAlexClient) -> None:
    """search_works returns parsed OpenAlexWork objects."""
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(
            200, json=_works_response([_WORK_ITEM])
        )
    )

    works: list[OpenAlexWork] = []
    async for w in client.search_works("KRAS inhibitor"):
        works.append(w)

    assert len(works) == 1
    w = works[0]
    assert isinstance(w, OpenAlexWork)
    assert w.openalex_id == "https://openalex.org/W2741809807"
    assert w.doi == "https://doi.org/10.1234/test"
    assert "KRAS" in w.title
    assert w.cited_by_count == 42
    assert w.type == "journal-article"
    assert w.publication_date is not None
    assert w.publication_date.year == 2024
    assert len(w.concepts) == 2
    assert len(w.authorships) == 2
    assert w.authorships[0]["author_name"] == "Jane Smith"
    assert w.primary_location is not None
    assert w.primary_location["source_name"] == "Nature Medicine"
    assert len(w.mesh_terms) == 2
    assert "Lung Neoplasms" in w.mesh_terms


@respx.mock
@pytest.mark.anyio
async def test_search_authors_returns_parsed_objects(client: OpenAlexClient) -> None:
    """search_authors returns parsed OpenAlexAuthor objects."""
    respx.get("https://api.openalex.org/authors").mock(
        return_value=httpx.Response(
            200, json=_authors_response([_AUTHOR_ITEM])
        )
    )

    authors: list[OpenAlexAuthor] = []
    async for a in client.search_authors("Jane Smith"):
        authors.append(a)

    assert len(authors) == 1
    a = authors[0]
    assert isinstance(a, OpenAlexAuthor)
    assert a.display_name == "Jane Smith"
    assert a.orcid == "0000-0001-2345-6789"
    assert a.works_count == 150
    assert a.cited_by_count == 5000
    assert len(a.affiliations) == 1
    assert a.affiliations[0]["institution_name"] == "Harvard University"
    assert a.affiliations[0]["country"] == "US"


@respx.mock
@pytest.mark.anyio
async def test_pagination_with_cursor(client: OpenAlexClient) -> None:
    """Cursor-based pagination fetches multiple pages."""
    page1 = _works_response([_WORK_ITEM], next_cursor="abc123")
    page2_item = dict(_WORK_ITEM)
    page2_item["id"] = "https://openalex.org/W9999999999"
    page2_item["title"] = "Second Work"
    page2 = _works_response([page2_item], next_cursor=None)

    route = respx.get("https://api.openalex.org/works")
    route.side_effect = [
        httpx.Response(200, json=page1),
        httpx.Response(200, json=page2),
    ]

    works: list[OpenAlexWork] = []
    async for w in client.search_works("test"):
        works.append(w)

    assert len(works) == 2
    assert works[0].openalex_id == "https://openalex.org/W2741809807"
    assert works[1].openalex_id == "https://openalex.org/W9999999999"
    assert route.call_count == 2


@respx.mock
@pytest.mark.anyio
async def test_retry_on_429(client: OpenAlexClient) -> None:
    """Client retries on 429 Too Many Requests."""
    route = respx.get("https://api.openalex.org/works")
    route.side_effect = [
        httpx.Response(429, text="rate limited"),
        httpx.Response(200, json=_works_response([_WORK_ITEM])),
    ]

    works: list[OpenAlexWork] = []
    async for w in client.search_works("test"):
        works.append(w)

    assert len(works) == 1
    assert route.call_count == 2


@respx.mock
@pytest.mark.anyio
async def test_get_concepts_for_work(client: OpenAlexClient) -> None:
    """get_concepts_for_work returns OpenAlexConcept objects."""
    respx.get("https://api.openalex.org/works/W123").mock(
        return_value=httpx.Response(200, json=_WORK_ITEM)
    )

    concepts = await client.get_concepts_for_work("W123")

    assert len(concepts) == 2
    assert isinstance(concepts[0], OpenAlexConcept)
    assert concepts[0].display_name == "Oncology"
    assert concepts[0].score == 0.95
    assert concepts[1].display_name == "Drug Discovery"


@respx.mock
@pytest.mark.anyio
async def test_search_funders(client: OpenAlexClient) -> None:
    """search_funders returns OpenAlexFunder objects."""
    respx.get("https://api.openalex.org/funders").mock(
        return_value=httpx.Response(
            200, json=_funders_response([_FUNDER_ITEM])
        )
    )

    funders = []
    async for f in client.search_funders("ERC"):
        funders.append(f)

    assert len(funders) == 1
    assert funders[0].display_name == "European Research Council"
    assert funders[0].country_code == "EU"
    assert funders[0].grants_count == 12000
