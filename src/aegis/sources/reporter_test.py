"""Tests for the NIH RePORTER client — fixture-based, no live API calls."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from aegis.sources.reporter import (
    REPORTER_API_URL,
    GrantRecord,
    ReporterClient,
    _parse_grant,
)
from aegis.sources.retry import RetryPolicy

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

FIXTURE_GRANT_1: dict[str, object] = {
    "project_num": "5R01CA123456-03",
    "activity_code": "R01",
    "principal_investigators": [
        {
            "full_name": "Jane Smith",
            "profile_id": "JSMITH01",
            "orcid": "0000-0001-2345-6789",
            "is_contact_pi": True,
            "org_name": "MIT",
        },
        {
            "full_name": "John Doe",
            "profile_id": "JDOE02",
            "orcid": None,
            "is_contact_pi": False,
            "org_name": "Harvard",
        },
    ],
    "award_amount": 500000,
    "fiscal_year": 2024,
    "phr_text": "cancer; genomics; precision medicine",
    "spending_categories_desc": "Cancer;Genomics",
    "organization": {"org_name": "Massachusetts Institute of Technology"},
    "award_notice_date": "2024-01-15T00:00:00",
    "is_active": True,
}

FIXTURE_GRANT_2: dict[str, object] = {
    "project_num": "1U01AI987654-01",
    "activity_code": "U01",
    "principal_investigators": [
        {
            "full_name": "Alice Johnson",
            "profile_id": "AJOHN03",
            "orcid": "0000-0002-9876-5432",
            "is_contact_pi": True,
            "org_name": "Stanford University",
        },
    ],
    "award_amount": 750000,
    "fiscal_year": 2023,
    "phr_text": "immunology; vaccines",
    "spending_categories_desc": "Immunology;Vaccines",
    "organization": {"org_name": "Stanford University"},
    "award_notice_date": "2023-06-01T00:00:00",
    "is_active": False,
}

FIXTURE_GRANT_3: dict[str, object] = {
    "project_num": "3P01HL654321-02",
    "activity_code": "P01",
    "principal_investigators": [
        {
            "full_name": "Bob Williams",
            "profile_id": "BWILL04",
            "orcid": None,
            "is_contact_pi": True,
            "org_name": "Johns Hopkins",
        },
        {
            "full_name": "Carol Davis",
            "profile_id": "CDAV05",
            "orcid": "0000-0003-1111-2222",
            "is_contact_pi": False,
            "org_name": "Johns Hopkins",
        },
        {
            "full_name": "David Lee",
            "profile_id": "DLEE06",
            "orcid": None,
            "is_contact_pi": False,
            "org_name": "NIH",
        },
    ],
    "award_amount": None,
    "fiscal_year": 2024,
    "phr_text": "cardiology; heart failure; clinical trials",
    "spending_categories_desc": "Heart Disease;Clinical Trials",
    "organization": {"org_name": "Johns Hopkins University"},
    "award_notice_date": None,
    "is_active": True,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_parse_grant_record() -> None:
    """Parse fixture JSON, assert fields populated correctly."""
    record = _parse_grant(FIXTURE_GRANT_1)
    assert record.project_number == "5R01CA123456-03"
    assert record.activity_code == "R01"
    assert record.fiscal_year == 2024
    assert record.total_cost == 500000
    assert record.is_active is True
    assert record.organization_name == "Massachusetts Institute of Technology"
    assert len(record.pis) == 2
    assert record.award_notice_date is not None
    assert record.award_notice_date.year == 2024


def test_multi_pi_preserved() -> None:
    """Assert grants with multiple PIs have all PIs in the list."""
    record = _parse_grant(FIXTURE_GRANT_3)
    assert len(record.pis) == 3
    names = {pi.full_name for pi in record.pis}
    assert names == {"Bob Williams", "Carol Davis", "David Lee"}
    roles = {pi.role for pi in record.pis}
    assert "Contact PI" in roles
    assert "Co-PI" in roles


def test_era_commons_populated() -> None:
    """Assert eRA Commons IDs present on all fixture records."""
    fixtures = [FIXTURE_GRANT_1, FIXTURE_GRANT_2, FIXTURE_GRANT_3]
    for fix in fixtures:
        record = _parse_grant(fix)
        for pi in record.pis:
            assert pi.era_id, f"Missing eRA ID for {pi.full_name}"
            assert len(pi.era_id) > 0


def test_rcdc_categories_preserved() -> None:
    """Assert RCDC categories match fixture data verbatim."""
    record = _parse_grant(FIXTURE_GRANT_1)
    assert "Cancer" in record.rcdc_categories
    assert "Genomics" in record.rcdc_categories

    record2 = _parse_grant(FIXTURE_GRANT_2)
    assert "Immunology" in record2.rcdc_categories
    assert "Vaccines" in record2.rcdc_categories


def test_raw_json_preserved() -> None:
    """Assert raw_json contains original response data."""
    record = _parse_grant(FIXTURE_GRANT_1)
    raw = json.loads(record.raw_json)
    assert raw["project_num"] == "5R01CA123456-03"
    assert raw["fiscal_year"] == 2024


@pytest.mark.asyncio
@respx.mock
async def test_fetch_grants_by_topic_pagination() -> None:
    """Assert that paginated fetch returns all records."""
    page1_response = {
        "results": [FIXTURE_GRANT_1, FIXTURE_GRANT_2],
        "meta": {"total": 3},
    }
    page2_response = {
        "results": [FIXTURE_GRANT_3],
        "meta": {"total": 3},
    }

    route = respx.post(REPORTER_API_URL)
    route.side_effect = [
        httpx.Response(200, json=page1_response),
        httpx.Response(200, json=page2_response),
    ]

    client = ReporterClient(retry_policy=RetryPolicy())
    records: list[GrantRecord] = []
    async for record in client.fetch_grants_by_topic(["Cancer"], page_size=2):
        records.append(record)

    assert len(records) == 3
    assert records[0].project_number == "5R01CA123456-03"
    assert records[2].project_number == "3P01HL654321-02"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_grants_by_pi() -> None:
    """Assert fetch_grants_by_pi returns records for the given eRA ID."""
    api_response = {
        "results": [FIXTURE_GRANT_1],
        "meta": {"total": 1},
    }

    respx.post(REPORTER_API_URL).mock(
        return_value=httpx.Response(200, json=api_response)
    )

    client = ReporterClient(retry_policy=RetryPolicy())
    records: list[GrantRecord] = []
    async for record in client.fetch_grants_by_pi("JSMITH01"):
        records.append(record)

    assert len(records) == 1
    assert records[0].pis[0].era_id == "JSMITH01"
