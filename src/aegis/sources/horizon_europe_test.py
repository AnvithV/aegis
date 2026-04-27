"""Tests for the Horizon Europe CORDIS client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.horizon_europe import CORDIS_API_URL, HorizonEuropeClient
from aegis.sources.non_us_grants import NonUsGrantRecord

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_HORIZON_RESPONSE: dict[str, Any] = {
    "total": 1,
    "results": [
        {
            "id": "202012345",
            "acronym": "BIODEV",
            "title": "Biodevelopment for Rare Disease Therapeutics",
            "objective": "Developing novel gene therapy approaches for rare diseases.",
            "participants": [
                {
                    "name": "Prof. Hans Mueller",
                    "orcid": "0000-0002-9876-5432",
                }
            ],
            "coordinatorName": "Charite Berlin",
            "totalCost": 3500000.0,
            "startDate": "2024-01-01",
            "endDate": "2028-12-31",
            "euroSciVoc": ["Health", "Gene Therapy", "Rare Diseases"],
        }
    ],
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_horizon_project() -> None:
    """Horizon project parses correctly into NonUsGrantRecord."""
    data = SAMPLE_HORIZON_RESPONSE["results"][0]
    result = HorizonEuropeClient._parse_horizon_project(data)
    assert result is not None
    assert isinstance(result, NonUsGrantRecord)
    assert result.grant_reference == "HORIZON-BIODEV-202012345"
    assert result.title == "Biodevelopment for Rare Disease Therapeutics"
    assert "Prof. Hans Mueller" in result.pi_names
    assert result.institution == "Charite Berlin"
    assert result.amount_local == 3500000.0
    assert result.start_date == date(2024, 1, 1)


def test_horizon_grant_funder() -> None:
    """Horizon Europe grants have correct funder metadata."""
    data = SAMPLE_HORIZON_RESPONSE["results"][0]
    result = HorizonEuropeClient._parse_horizon_project(data)
    assert result is not None
    assert result.funder == "Horizon Europe"
    assert result.funder_country == "EU"
    assert result.source == "horizon_europe"
    assert result.currency == "EUR"
    assert result.coverage_caveat is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination() -> None:
    """Pagination: fetch_grants pages through Horizon results."""
    client = HorizonEuropeClient()

    page1 = {
        "total": 2,
        "results": [SAMPLE_HORIZON_RESPONSE["results"][0]],
    }
    page2 = {
        "total": 2,
        "results": [
            {
                "id": "202099999",
                "acronym": "GENOMIX",
                "title": "Genomic Analysis Platform",
                "participants": [{"name": "Dr. Test Scientist"}],
                "totalCost": 1000000.0,
                "euroSciVoc": ["Genomics"],
            }
        ],
    }

    route = respx.get(f"{CORDIS_API_URL}/projects")
    route.side_effect = [
        Response(200, json=page1),
        Response(200, json=page2),
    ]

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants(batch_size=1):
        results.append(grant)

    assert len(results) == 2
    assert results[0].grant_reference == "HORIZON-BIODEV-202012345"
    assert results[1].grant_reference == "HORIZON-GENOMIX-202099999"


def test_parse_horizon_missing_id() -> None:
    """Parse returns None when project ID is missing."""
    result = HorizonEuropeClient._parse_horizon_project({"title": "No ID"})
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_grants_by_institution() -> None:
    """fetch_grants_by_institution returns matching Horizon grants."""
    client = HorizonEuropeClient()

    respx.get(f"{CORDIS_API_URL}/projects").mock(
        return_value=Response(200, json=SAMPLE_HORIZON_RESPONSE),
    )

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants_by_institution("Charite Berlin"):
        results.append(grant)

    assert len(results) == 1
    assert results[0].institution == "Charite Berlin"
