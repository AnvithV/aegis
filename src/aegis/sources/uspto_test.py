"""Tests for the USPTO PatentsView API client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.uspto import (
    PATENTSVIEW_API_URL,
    PatentRecord,
    UsptoClient,
)

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_PATENT: dict[str, Any] = {
    "patent_number": "US10123456B2",
    "patent_date": "2023-06-15",
    "patent_title": "Kinase Inhibitor Compound",
    "patent_abstract": "A novel kinase inhibitor for treating cancer.",
    "patent_firstnamed_inventor_id": "inv-001",
    "patent_num_cited_by_us_patents": 42,
    "inventors": [
        {
            "inventor_id": "inv-001",
            "inventor_first_name": "Alice",
            "inventor_last_name": "Smith",
            "inventor_sequence": 0,
        },
        {
            "inventor_id": "inv-002",
            "inventor_first_name": "Bob",
            "inventor_last_name": "Jones",
            "inventor_sequence": 1,
        },
    ],
    "assignees": [
        {
            "assignee_id": "asg-001",
            "assignee_organization": "Pharma Corp",
            "assignee_type": 2,
        },
    ],
    "cpcs": [
        {"cpc_subgroup_id": "A61K31/00"},
        {"cpc_subgroup_id": "C07D401/12"},
    ],
}

SAMPLE_PATENT_MINIMAL: dict[str, Any] = {
    "patent_number": "US9999999B1",
    "patent_date": "2022-01-10",
    "patent_title": "Minimal Patent",
    "patent_abstract": None,
    "patent_firstnamed_inventor_id": None,
    "patent_num_cited_by_us_patents": 0,
    "inventors": [],
    "assignees": [],
    "cpcs": [],
}


@pytest.fixture
def client() -> UsptoClient:
    return UsptoClient()


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_patent_record_parse() -> None:
    """PatentRecord correctly parses a mock PatentsView response."""
    record = UsptoClient._parse_patent(SAMPLE_PATENT)
    assert record is not None
    assert record.patent_number == "US10123456B2"
    assert record.grant_date == date(2023, 6, 15)
    assert record.title == "Kinase Inhibitor Compound"
    assert record.abstract == "A novel kinase inhibitor for treating cancer."
    assert record.forward_citation_count == 42
    assert len(record.inventors) == 2
    assert record.inventors[0].inventor_id == "inv-001"
    assert record.inventors[0].full_name == "Alice Smith"
    assert len(record.assignees) == 1
    assert record.assignees[0].organization == "Pharma Corp"
    assert record.assignees[0].assignee_type == "organization"
    assert record.cpc_codes == ["A61K31/00", "C07D401/12"]


def test_inventor_lead_detection() -> None:
    """Lead inventor detection: is_lead_inventor is True only for sequence=0."""
    data = {
        **SAMPLE_PATENT,
        "inventors": [
            {
                "inventor_id": "inv-A",
                "inventor_first_name": "First",
                "inventor_last_name": "Author",
                "inventor_sequence": 0,
            },
            {
                "inventor_id": "inv-B",
                "inventor_first_name": "Second",
                "inventor_last_name": "Author",
                "inventor_sequence": 1,
            },
            {
                "inventor_id": "inv-C",
                "inventor_first_name": "Third",
                "inventor_last_name": "Author",
                "inventor_sequence": 2,
            },
        ],
    }
    record = UsptoClient._parse_patent(data)
    assert record is not None
    assert len(record.inventors) == 3
    assert record.inventors[0].is_lead_inventor is True
    assert record.inventors[1].is_lead_inventor is False
    assert record.inventors[2].is_lead_inventor is False


@pytest.mark.asyncio
@respx.mock
async def test_fetch_patents_pagination(client: UsptoClient) -> None:
    """Pagination: two pages of results yield all patents."""
    page1_response = {
        "patents": [SAMPLE_PATENT],
        "total_patent_count": 2,
    }
    page2_response = {
        "patents": [SAMPLE_PATENT_MINIMAL],
        "total_patent_count": 2,
    }

    route = respx.post(PATENTSVIEW_API_URL)
    route.side_effect = [
        Response(200, json=page1_response),
        Response(200, json=page2_response),
    ]

    results: list[PatentRecord] = []
    async for rec in client.fetch_patents(
        cpc_codes=["A61K31/00"], since=date(2020, 1, 1), batch_size=1
    ):
        results.append(rec)

    assert len(results) == 2
    assert results[0].patent_number == "US10123456B2"
    assert results[1].patent_number == "US9999999B1"


def test_parse_patent_missing_fields() -> None:
    """Missing optional fields parse to None."""
    record = UsptoClient._parse_patent(SAMPLE_PATENT_MINIMAL)
    assert record is not None
    assert record.patent_number == "US9999999B1"
    assert record.abstract is None
    assert record.claims_text is None
    assert record.family_id is None
    assert record.maintenance_status is None
    assert record.application_date is None
    assert record.inventors == []
    assert record.assignees == []
    assert record.cpc_codes == []


def test_cpc_code_extraction() -> None:
    """CPC codes are correctly extracted from the cpcs array."""
    data = {
        **SAMPLE_PATENT,
        "cpcs": [
            {"cpc_subgroup_id": "A61K31/00"},
            {"cpc_subgroup_id": "C07D401/12"},
            {"cpc_subgroup_id": "A61P35/00"},
            {"cpc_subgroup_id": "C07K14/435"},
        ],
    }
    record = UsptoClient._parse_patent(data)
    assert record is not None
    assert len(record.cpc_codes) == 4
    assert record.cpc_codes == [
        "A61K31/00",
        "C07D401/12",
        "A61P35/00",
        "C07K14/435",
    ]
