"""Tests for the CIHR client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.cihr import CIHR_API_URL, CihrClient
from aegis.sources.non_us_grants import NonUsGrantRecord

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_CIHR_RESPONSE: dict[str, Any] = {
    "total": 1,
    "results": [
        {
            "applicationId": "PJT-173456",
            "title": "Epigenomic regulation of immune cell differentiation",
            "abstract": "This project investigates epigenetic mechanisms.",
            "principalInvestigators": [
                {
                    "name": "Dr. Sarah Chen",
                    "orcid": "0000-0001-5555-6666",
                }
            ],
            "institution": {"name": "University of Toronto"},
            "amount": 850000.0,
            "fiscalYear": 2023,
            "startDate": "2023-04-01",
            "endDate": "2028-03-31",
            "researchAreas": [
                {"name": "Epigenetics"},
                {"name": "Immunology"},
            ],
        }
    ],
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_cihr_grant() -> None:
    """CIHR grant parses correctly into NonUsGrantRecord."""
    data = SAMPLE_CIHR_RESPONSE["results"][0]
    result = CihrClient._parse_cihr_grant(data)
    assert result is not None
    assert isinstance(result, NonUsGrantRecord)
    assert result.grant_reference == "CIHR-PJT-173456"
    assert result.title == "Epigenomic regulation of immune cell differentiation"
    assert "Dr. Sarah Chen" in result.pi_names
    assert result.institution == "University of Toronto"
    assert result.amount_local == 850000.0
    assert result.start_date == date(2023, 4, 1)
    assert "Epigenetics" in result.subject_areas


def test_cihr_grant_metadata() -> None:
    """CIHR grants have correct metadata."""
    data = SAMPLE_CIHR_RESPONSE["results"][0]
    result = CihrClient._parse_cihr_grant(data)
    assert result is not None
    assert result.funder == "CIHR"
    assert result.funder_country == "CA"
    assert result.source == "cihr"
    assert result.currency == "CAD"
    assert result.institution_country == "CA"
    assert result.coverage_caveat is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination() -> None:
    """Pagination: fetch_grants pages through CIHR results."""
    client = CihrClient()

    page1 = {
        "total": 2,
        "results": [SAMPLE_CIHR_RESPONSE["results"][0]],
    }
    page2 = {
        "total": 2,
        "results": [
            {
                "applicationId": "PJT-999999",
                "title": "Second CIHR Grant",
                "principalInvestigators": [{"name": "Dr. Test PI"}],
                "amount": 500000.0,
                "researchAreas": [{"name": "Neuroscience"}],
            }
        ],
    }

    route = respx.get(f"{CIHR_API_URL}/grants")
    route.side_effect = [
        Response(200, json=page1),
        Response(200, json=page2),
    ]

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants(batch_size=1):
        results.append(grant)

    assert len(results) == 2
    assert results[0].grant_reference == "CIHR-PJT-173456"
    assert results[1].grant_reference == "CIHR-PJT-999999"


def test_parse_cihr_missing_id() -> None:
    """Parse returns None when application ID is missing."""
    result = CihrClient._parse_cihr_grant({"title": "No ID"})
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_grants_by_pi() -> None:
    """fetch_grants_by_pi returns CIHR grants for a PI."""
    client = CihrClient()

    respx.get(f"{CIHR_API_URL}/grants").mock(
        return_value=Response(200, json=SAMPLE_CIHR_RESPONSE),
    )

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants_by_pi("Sarah Chen"):
        results.append(grant)

    assert len(results) == 1
