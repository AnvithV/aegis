"""Tests for the WIPO PATENTSCOPE client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.wipo import (
    PATENTSCOPE_API_URL,
    PctApplication,
    WipoClient,
    WipoCredentials,
)

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_PATENTSCOPE_RESPONSE: dict[str, Any] = {
    "total": 2,
    "results": [
        {
            "applicationNumber": "PCT/US2023/012345",
            "publicationNumber": "WO2023/123456",
            "filingDate": "2023-03-15",
            "publicationDate": "2023-09-21",
            "title": "Novel CRISPR-Cas9 Delivery System",
            "abstract": "A method for targeted delivery of CRISPR components.",
            "applicants": ["MIT", "Broad Institute"],
            "inventors": ["Dr. Alice Smith", "Dr. Bob Jones"],
            "ipcCodes": ["C12N15/11", "A61K48/00"],
            "designatedStates": ["US", "EP", "JP", "CN"],
            "originCountry": "US",
            "familyId": "FAM-PCT-001",
        },
        {
            "applicationNumber": "PCT/EP2023/067890",
            "publicationNumber": "WO2023/789012",
            "filingDate": "2023-06-28",
            "publicationDate": "2024-01-04",
            "title": "Antibody-Drug Conjugate for Oncology",
            "abstract": None,
            "applicants": ["Roche AG"],
            "inventors": ["Dr. Maria Mueller"],
            "ipcCodes": ["A61K47/68"],
            "designatedStates": ["US", "EP"],
            "originCountry": "EP",
            "familyId": "FAM-PCT-002",
        },
    ],
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_patentscope_result() -> None:
    """A PATENTSCOPE result parses into PctApplication correctly."""
    data = SAMPLE_PATENTSCOPE_RESPONSE["results"][0]
    result = WipoClient._parse_patentscope_result(data)
    assert result is not None
    assert result.application_number == "PCT/US2023/012345"
    assert result.publication_number == "WO2023/123456"
    assert result.title == "Novel CRISPR-Cas9 Delivery System"
    assert result.filing_date == date(2023, 3, 15)
    assert result.publication_date == date(2023, 9, 21)
    assert "MIT" in result.applicants
    assert len(result.ipc_codes) == 2
    assert result.origin_country == "US"
    assert result.family_id == "FAM-PCT-001"


def test_pct_application_model() -> None:
    """PctApplication model creates with all fields."""
    app = PctApplication(
        application_number="PCT/JP2024/001234",
        publication_number=None,
        filing_date=date(2024, 1, 10),
        publication_date=None,
        title="Test Application",
        abstract=None,
        applicants=["Test Corp"],
        inventors=["Inventor A"],
        ipc_codes=["A61K31/00"],
        designated_states=["JP", "US"],
        origin_country="JP",
        family_id=None,
    )
    assert app.application_number == "PCT/JP2024/001234"
    assert app.origin_country == "JP"
    assert len(app.designated_states) == 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination() -> None:
    """Pagination: fetch_pct_applications pages through results correctly."""
    creds = WipoCredentials(access_token="test-token")
    client = WipoClient(credentials=creds)

    page1 = {
        "total": 2,
        "results": [SAMPLE_PATENTSCOPE_RESPONSE["results"][0]],
    }
    page2 = {
        "total": 2,
        "results": [SAMPLE_PATENTSCOPE_RESPONSE["results"][1]],
    }

    search_url = f"{PATENTSCOPE_API_URL}/search"
    route = respx.get(search_url)
    route.side_effect = [
        Response(200, json=page1),
        Response(200, json=page2),
    ]

    results: list[PctApplication] = []
    async for app in client.fetch_pct_applications(
        ipc_codes=["C12N15/11"], since=date(2023, 1, 1), batch_size=1
    ):
        results.append(app)

    assert len(results) == 2
    assert results[0].application_number == "PCT/US2023/012345"
    assert results[1].application_number == "PCT/EP2023/067890"


def test_wipo_credentials_model() -> None:
    """WipoCredentials model creates correctly."""
    creds = WipoCredentials(access_token="abc123")
    assert creds.access_token == "abc123"


def test_parse_missing_application_number() -> None:
    """Parse returns None when applicationNumber is missing."""
    result = WipoClient._parse_patentscope_result({"title": "No app number"})
    assert result is None
