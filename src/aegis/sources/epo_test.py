"""Tests for the EPO Espacenet OPS API client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.epo import (
    EP_MEMBER_STATES,
    OPS_API_URL,
    OPS_AUTH_URL,
    EpoClient,
    EpoCredentials,
    PatentFamily,
)
from aegis.sources.uspto import PatentRecord

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_OPS_RESPONSE: dict[str, Any] = {
    "ops:world-patent-data": {
        "ops:biblio-search": {
            "ops:search-result": {
                "ops:publication-reference": [
                    {
                        "document-id": {
                            "doc-number": "3456789",
                            "kind": "A1",
                        }
                    },
                    {
                        "document-id": {
                            "doc-number": "3456790",
                            "kind": "B1",
                        }
                    },
                    {
                        "document-id": {
                            "doc-number": "3456791",
                            "kind": "A2",
                        }
                    },
                ]
            }
        }
    }
}

SAMPLE_FAMILY_RESPONSE: dict[str, Any] = {
    "ops:world-patent-data": {
        "ops:patent-family": {
            "@family-id": "FAM-12345",
            "ops:family-member": [
                {
                    "publication-reference": {
                        "document-id": {
                            "doc-number": "3456789",
                            "country": "EP",
                        }
                    }
                },
                {
                    "publication-reference": {
                        "document-id": {
                            "doc-number": "10123456",
                            "country": "US",
                        }
                    }
                },
                {
                    "publication-reference": {
                        "document-id": {
                            "doc-number": "2022100001",
                            "country": "CN",
                        }
                    }
                },
            ],
        }
    }
}

AUTH_RESPONSE: dict[str, Any] = {
    "access_token": "test-token-123",
    "token_type": "Bearer",
}


@pytest.fixture
def credentials() -> EpoCredentials:
    return EpoCredentials(consumer_key="test-key", consumer_secret="test-secret")


@pytest.fixture
def client(credentials: EpoCredentials) -> EpoClient:
    return EpoClient(credentials=credentials)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_ops_response() -> None:
    """OPS response with 3 EP patents parses correctly."""
    records = EpoClient._parse_ops_response(SAMPLE_OPS_RESPONSE)
    assert len(records) == 3
    assert records[0].patent_number == "EP3456789A1"
    assert records[1].patent_number == "EP3456790B1"
    assert records[2].patent_number == "EP3456791A2"
    for rec in records:
        assert rec.forward_citation_count == 0
        assert rec.inventors == []
        assert rec.cpc_codes == []


def test_patent_family_extraction() -> None:
    """Family member extraction returns all members with country prefixes."""
    members = EpoClient._extract_family_members(SAMPLE_FAMILY_RESPONSE)
    assert len(members) == 3
    assert "EP3456789" in members
    assert "US10123456" in members
    assert "CN2022100001" in members


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination(client: EpoClient) -> None:
    """Pagination: two pages of OPS results yield all patents."""
    # Mock OAuth2 token
    respx.post(OPS_AUTH_URL).mock(
        return_value=Response(200, json=AUTH_RESPONSE),
    )

    page1_data = {
        "ops:world-patent-data": {
            "ops:biblio-search": {
                "ops:search-result": {
                    "ops:publication-reference": [
                        {
                            "document-id": {
                                "doc-number": "1000001",
                                "kind": "A1",
                            }
                        },
                    ]
                }
            }
        }
    }
    page2_data = {
        "ops:world-patent-data": {
            "ops:biblio-search": {
                "ops:search-result": {
                    "ops:publication-reference": [
                        {
                            "document-id": {
                                "doc-number": "1000002",
                                "kind": "B1",
                            }
                        },
                    ]
                }
            }
        }
    }
    empty_data: dict[str, Any] = {
        "ops:world-patent-data": {
            "ops:biblio-search": {
                "ops:search-result": {
                    "ops:publication-reference": []
                }
            }
        }
    }

    search_url = f"{OPS_API_URL}/published-data/search"
    route = respx.get(search_url)
    route.side_effect = [
        Response(200, json=page1_data),
        Response(200, json=page2_data),
        Response(200, json=empty_data),
    ]

    results: list[PatentRecord] = []
    async for rec in client.fetch_patents(
        cpc_codes=["A61K31/00"], since=date(2020, 1, 1), batch_size=1
    ):
        results.append(rec)

    assert len(results) == 2
    assert results[0].patent_number == "EP1000001A1"
    assert results[1].patent_number == "EP1000002B1"


def test_epo_credentials_model() -> None:
    """EpoCredentials model creates correctly."""
    creds = EpoCredentials(consumer_key="key123", consumer_secret="secret456")
    assert creds.consumer_key == "key123"
    assert creds.consumer_secret == "secret456"


@pytest.mark.asyncio
@respx.mock
async def test_get_patent_family(client: EpoClient) -> None:
    """Patent family lookup returns family with members."""
    respx.post(OPS_AUTH_URL).mock(
        return_value=Response(200, json=AUTH_RESPONSE),
    )
    family_url = f"{OPS_API_URL}/family/publication/docdb/EP3456789A1"
    respx.get(family_url).mock(
        return_value=Response(200, json=SAMPLE_FAMILY_RESPONSE),
    )

    family = await client.get_patent_family("EP3456789A1")
    assert family is not None
    assert isinstance(family, PatentFamily)
    assert family.family_id == "FAM-12345"
    assert len(family.members) == 3


def test_ep_member_states_count() -> None:
    """EP_MEMBER_STATES has exactly 39 entries."""
    assert len(EP_MEMBER_STATES) == 39
    # Spot-check a few expected countries
    assert "DE" in EP_MEMBER_STATES
    assert "FR" in EP_MEMBER_STATES
    assert "GB" in EP_MEMBER_STATES


@pytest.mark.asyncio
@respx.mock
async def test_fetch_patents_by_country(client: EpoClient) -> None:
    """fetch_patents_by_country yields PatentRecord objects for a country."""
    respx.post(OPS_AUTH_URL).mock(
        return_value=Response(200, json=AUTH_RESPONSE),
    )

    country_data = {
        "ops:world-patent-data": {
            "ops:biblio-search": {
                "ops:search-result": {
                    "ops:publication-reference": [
                        {
                            "document-id": {
                                "doc-number": "9000001",
                                "kind": "A1",
                            }
                        },
                    ]
                }
            }
        }
    }
    empty_data: dict[str, Any] = {
        "ops:world-patent-data": {
            "ops:biblio-search": {
                "ops:search-result": {
                    "ops:publication-reference": []
                }
            }
        }
    }

    search_url = f"{OPS_API_URL}/published-data/search"
    route = respx.get(search_url)
    route.side_effect = [
        Response(200, json=country_data),
        Response(200, json=empty_data),
    ]

    results: list[PatentRecord] = []
    async for rec in client.fetch_patents_by_country(
        country="DE", since=date(2023, 1, 1), batch_size=1
    ):
        results.append(rec)

    assert len(results) == 1
    assert results[0].patent_number == "EP9000001A1"
