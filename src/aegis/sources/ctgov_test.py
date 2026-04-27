"""Tests for the ClinicalTrials.gov v2 client — fixture-based, no live API calls."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from aegis.sources.ctgov import (
    CTGOV_API_URL,
    CtgovClient,
    StudyRecord,
    _parse_study,
)
from aegis.sources.retry import RetryPolicy

# ---------------------------------------------------------------------------
# Fixture data — mirrors CT.gov v2 API response structure
# ---------------------------------------------------------------------------

FIXTURE_STUDY_1: dict[str, Any] = {
    "protocolSection": {
        "identificationModule": {
            "nctId": "NCT01234567",
            "briefTitle": "A Phase 3 Study of Drug X in Cancer",
        },
        "statusModule": {
            "overallStatus": "Recruiting",
            "statusVerifiedDate": "2024-03-01",
            "startDateStruct": {"date": "2023-01-15"},
            "lastUpdatePostDateStruct": {"date": "2024-03-05"},
        },
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE3"],
            "designInfo": {
                "allocation": "RANDOMIZED",
                "maskingInfo": {"masking": "DOUBLE"},
            },
        },
        "sponsorCollaboratorsModule": {
            "leadSponsor": {"name": "Pharma Corp"},
        },
        "conditionsModule": {
            "conditions": ["Lung Cancer", "Non-Small Cell Lung Cancer"],
        },
        "armsInterventionsModule": {
            "interventions": [
                {"name": "Drug X", "type": "DRUG"},
                {"name": "Placebo", "type": "DRUG"},
            ],
        },
        "contactsLocationsModule": {
            "overallOfficials": [
                {
                    "name": "Dr. Jane Smith",
                    "role": "PRINCIPAL_INVESTIGATOR",
                    "affiliation": "MIT Cancer Center",
                },
                {
                    "name": "Dr. Bob Chair",
                    "role": "STUDY_CHAIR",
                    "affiliation": "NIH",
                },
            ],
            "locations": [
                {
                    "facility": "MIT Cancer Center",
                    "contacts": [
                        {
                            "name": "Dr. Sub Inv",
                            "role": "SUB_INVESTIGATOR",
                        },
                    ],
                },
                {
                    "facility": "Stanford Hospital",
                    "contacts": [
                        {
                            "name": "Dr. Site PI",
                            "role": "PRINCIPAL_INVESTIGATOR",
                        },
                    ],
                },
            ],
        },
    },
    "derivedSection": {
        "conditionBrowseModule": {
            "meshes": [
                {"term": "Lung Neoplasms"},
                {"term": "Carcinoma, Non-Small-Cell Lung"},
            ],
        },
    },
}

FIXTURE_STUDY_2: dict[str, Any] = {
    "protocolSection": {
        "identificationModule": {
            "nctId": "NCT09876543",
            "briefTitle": "Phase 2 Trial of Antibody Y",
        },
        "statusModule": {
            "overallStatus": "Completed",
            "statusVerifiedDate": "2023-12-01",
            "startDateStruct": {"date": "2021-06-01"},
            "lastUpdatePostDateStruct": {"date": "2023-12-15"},
        },
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE2"],
            "designInfo": {
                "allocation": "NON_RANDOMIZED",
                "maskingInfo": {"masking": "NONE"},
            },
        },
        "sponsorCollaboratorsModule": {
            "leadSponsor": {"name": "Biotech Inc"},
        },
        "conditionsModule": {
            "conditions": ["Breast Cancer"],
        },
        "armsInterventionsModule": {
            "interventions": [
                {"name": "Antibody Y", "type": "BIOLOGICAL"},
            ],
        },
        "contactsLocationsModule": {
            "overallOfficials": [
                {
                    "name": "Dr. Alice Jones",
                    "role": "PRINCIPAL_INVESTIGATOR",
                    "affiliation": "Harvard Medical School",
                },
            ],
            "locations": [],
        },
    },
    "derivedSection": {
        "conditionBrowseModule": {
            "meshes": [
                {"term": "Breast Neoplasms"},
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_parse_study_record() -> None:
    """Parse fixture JSON, assert all fields populated."""
    record = _parse_study(FIXTURE_STUDY_1)
    assert record.nct_id == "NCT01234567"
    assert record.title == "A Phase 3 Study of Drug X in Cancer"
    assert record.status == "Recruiting"
    assert record.phase == "PHASE3"
    assert record.study_type == "INTERVENTIONAL"
    assert record.sponsor == "Pharma Corp"
    assert record.randomization == "RANDOMIZED"
    assert record.masking == "DOUBLE"
    assert record.last_update_post_date is not None
    assert record.last_update_post_date.year == 2024
    assert len(record.interventions) == 2
    assert "Drug X" in record.interventions


def test_investigator_roles_preserved() -> None:
    """Assert PI, Sub-I, Study Chair roles are preserved."""
    record = _parse_study(FIXTURE_STUDY_1)
    roles = {inv.role for inv in record.investigators}
    assert "PI" in roles
    assert "Sub-I" in roles
    assert "Study Chair" in roles


def test_multi_site_investigators() -> None:
    """Assert investigators across multiple sites are all captured."""
    record = _parse_study(FIXTURE_STUDY_1)
    # 2 overall officials + 1 site contact at MIT + 1 site contact at Stanford
    assert len(record.investigators) == 4
    sites = {inv.site for inv in record.investigators if inv.site}
    assert "MIT Cancer Center" in sites
    assert "Stanford Hospital" in sites


def test_conditions_mesh_and_freetext() -> None:
    """Assert both MeSH and free-text conditions are captured."""
    record = _parse_study(FIXTURE_STUDY_1)
    assert "Lung Neoplasms" in record.conditions_mesh
    assert "Carcinoma, Non-Small-Cell Lung" in record.conditions_mesh
    assert "Lung Cancer" in record.conditions_freetext
    assert "Non-Small Cell Lung Cancer" in record.conditions_freetext


def test_status_history() -> None:
    """Assert status history is chronologically ordered."""
    record = _parse_study(FIXTURE_STUDY_1)
    assert len(record.status_history) >= 1
    # Start date should come first if present
    if len(record.status_history) >= 2:
        dates = [entry["date"] for entry in record.status_history]
        assert dates == sorted(dates)


def test_raw_json_preserved() -> None:
    """Assert raw_json contains original response data."""
    record = _parse_study(FIXTURE_STUDY_1)
    raw = json.loads(record.raw_json)
    proto = raw["protocolSection"]["identificationModule"]
    assert proto["nctId"] == "NCT01234567"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_studies_by_condition_pagination() -> None:
    """Assert paginated fetch returns all records."""
    page1_response = {
        "studies": [FIXTURE_STUDY_1],
        "nextPageToken": "token123",
    }
    page2_response = {
        "studies": [FIXTURE_STUDY_2],
    }

    route = respx.get(CTGOV_API_URL)
    route.side_effect = [
        httpx.Response(200, json=page1_response),
        httpx.Response(200, json=page2_response),
    ]

    client = CtgovClient(retry_policy=RetryPolicy())
    records: list[StudyRecord] = []
    async for record in client.fetch_studies_by_condition(
        ["Lung Neoplasms"], page_size=1
    ):
        records.append(record)

    assert len(records) == 2
    assert records[0].nct_id == "NCT01234567"
    assert records[1].nct_id == "NCT09876543"
