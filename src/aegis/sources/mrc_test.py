"""Tests for the MRC GtR client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.mrc import GTR_API_URL, MrcClient
from aegis.sources.non_us_grants import NonUsGrantRecord

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_GTR_RESPONSE: dict[str, Any] = {
    "totalPages": 1,
    "project": [
        {
            "grantReference": "MR/T012345/1",
            "title": "Novel biomarkers for neurodegenerative diseases",
            "abstractText": "This project aims to identify blood-based biomarkers.",
            "principalInvestigator": {
                "firstName": "John",
                "surname": "Watson",
                "orcid": "0000-0003-1111-2222",
            },
            "leadOrganisation": {"name": "University of Oxford"},
            "fund": {
                "valuePounds": 750000.0,
                "start": "2022-04-01",
                "end": "2025-03-31",
            },
            "startDate": "2022-04-01",
            "endDate": "2025-03-31",
            "researchTopics": [
                {"text": "Neuroscience"},
                {"text": "Biomarkers"},
            ],
        }
    ],
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_gtr_project() -> None:
    """GtR project parses correctly into NonUsGrantRecord."""
    data = SAMPLE_GTR_RESPONSE["project"][0]
    result = MrcClient._parse_gtr_project(data)
    assert result is not None
    assert isinstance(result, NonUsGrantRecord)
    assert result.grant_reference == "MR/T012345/1"
    assert result.title == "Novel biomarkers for neurodegenerative diseases"
    assert "John Watson" in result.pi_names
    assert result.institution == "University of Oxford"
    assert result.amount_local == 750000.0
    assert result.start_date == date(2022, 4, 1)
    assert result.end_date == date(2025, 3, 31)
    assert "Neuroscience" in result.subject_areas


def test_mrc_grant_metadata() -> None:
    """MRC grants have correct funder metadata."""
    data = SAMPLE_GTR_RESPONSE["project"][0]
    result = MrcClient._parse_gtr_project(data)
    assert result is not None
    assert result.funder == "MRC"
    assert result.funder_country == "GB"
    assert result.source == "mrc"
    assert result.currency == "GBP"
    assert result.institution_country == "GB"
    assert result.coverage_caveat is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination() -> None:
    """Pagination: fetch_grants pages through GtR results."""
    client = MrcClient()

    page1 = {
        "totalPages": 2,
        "project": [SAMPLE_GTR_RESPONSE["project"][0]],
    }
    page2 = {
        "totalPages": 2,
        "project": [
            {
                "grantReference": "MR/V099999/1",
                "title": "Second MRC Grant",
                "principalInvestigator": {
                    "firstName": "Jane",
                    "surname": "Smith",
                },
                "fund": {"valuePounds": 500000.0},
                "researchTopics": [{"text": "Immunology"}],
            }
        ],
    }

    route = respx.get(f"{GTR_API_URL}/projects")
    route.side_effect = [
        Response(200, json=page1),
        Response(200, json=page2),
    ]

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants(batch_size=1):
        results.append(grant)

    assert len(results) == 2
    assert results[0].grant_reference == "MR/T012345/1"
    assert results[1].grant_reference == "MR/V099999/1"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_grants_by_pi() -> None:
    """fetch_grants_by_pi returns MRC grants for a PI."""
    client = MrcClient()

    respx.get(f"{GTR_API_URL}/projects").mock(
        return_value=Response(200, json=SAMPLE_GTR_RESPONSE),
    )

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants_by_pi("John Watson"):
        results.append(grant)

    assert len(results) == 1
    assert "John Watson" in results[0].pi_names[0]


def test_parse_gtr_missing_reference() -> None:
    """Parse returns None when grant reference is missing."""
    result = MrcClient._parse_gtr_project({"title": "No ref"})
    assert result is None
