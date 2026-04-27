"""Tests for the ERC CORDIS client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.erc import CORDIS_API_URL, ErcClient
from aegis.sources.non_us_grants import NonUsGrantRecord

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_CORDIS_RESPONSE: dict[str, Any] = {
    "total": 1,
    "results": [
        {
            "id": "101075123",
            "acronym": "StG",
            "title": "Novel mechanisms of immune evasion in cancer",
            "objective": "This project investigates novel immune evasion mechanisms.",
            "participants": [
                {
                    "name": "Dr. Marie Curie",
                    "orcid": "0000-0001-2345-6789",
                }
            ],
            "hostInstitution": {"name": "Karolinska Institutet"},
            "totalCost": 1500000.0,
            "startDate": "2023-09-01",
            "endDate": "2028-08-31",
            "euroSciVoc": ["Life Sciences", "Oncology"],
        }
    ],
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_cordis_project() -> None:
    """CORDIS project parses correctly into NonUsGrantRecord."""
    data = SAMPLE_CORDIS_RESPONSE["results"][0]
    result = ErcClient._parse_cordis_project(data)
    assert result is not None
    assert isinstance(result, NonUsGrantRecord)
    assert result.grant_reference == "ERC-StG-101075123"
    assert result.title == "Novel mechanisms of immune evasion in cancer"
    assert result.abstract is not None
    assert "Dr. Marie Curie" in result.pi_names
    assert result.institution == "Karolinska Institutet"
    assert result.amount_local == 1500000.0
    assert result.start_date == date(2023, 9, 1)
    assert result.end_date == date(2028, 8, 31)
    assert "Life Sciences" in result.subject_areas


def test_erc_grant_has_correct_funder() -> None:
    """ERC grants have funder='ERC' and source='erc'."""
    data = SAMPLE_CORDIS_RESPONSE["results"][0]
    result = ErcClient._parse_cordis_project(data)
    assert result is not None
    assert result.funder == "ERC"
    assert result.funder_country == "EU"
    assert result.source == "erc"
    assert result.currency == "EUR"
    assert result.coverage_caveat is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination() -> None:
    """Pagination: fetch_grants pages through CORDIS results."""
    client = ErcClient()

    page1 = {
        "total": 2,
        "results": [SAMPLE_CORDIS_RESPONSE["results"][0]],
    }
    page2 = {
        "total": 2,
        "results": [
            {
                "id": "101099999",
                "acronym": "CoG",
                "title": "Second ERC Grant",
                "participants": [{"name": "Dr. Test PI"}],
                "totalCost": 2000000.0,
                "euroSciVoc": ["Chemistry"],
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
    assert results[0].grant_reference == "ERC-StG-101075123"
    assert results[1].grant_reference == "ERC-CoG-101099999"


def test_parse_cordis_missing_id() -> None:
    """Parse returns None when project ID is missing."""
    result = ErcClient._parse_cordis_project({"title": "No ID"})
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_grants_by_pi() -> None:
    """fetch_grants_by_pi returns ERC grants for a PI."""
    client = ErcClient()

    respx.get(f"{CORDIS_API_URL}/projects").mock(
        return_value=Response(200, json=SAMPLE_CORDIS_RESPONSE),
    )

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants_by_pi("Marie Curie"):
        results.append(grant)

    assert len(results) == 1
    assert "Marie Curie" in results[0].pi_names[0]
