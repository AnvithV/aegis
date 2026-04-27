"""Tests for the NSFC client (fixture-based, no live API calls)."""

from __future__ import annotations

import inspect
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.non_us_grants import NonUsGrantRecord
from aegis.sources.nsfc import NSFC_API_URL, NSFC_COVERAGE_CAVEAT, NsfcClient

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_NSFC_RESPONSE: dict[str, Any] = {
    "total": 1,
    "results": [
        {
            "grantCode": "82170001",
            "title_cn": (
                "\u80bf\u7624\u514d\u75ab\u9003\u9038"
                "\u7684\u65b0\u673a\u5236\u7814\u7a76"
            ),
            "title_en": "Novel mechanisms of tumor immune evasion",
            "abstract": "This project investigates immune evasion in solid tumors.",
            "principalInvestigators": [
                {
                    "name": "\u738b\u5c0f\u660e",
                    "name_en": "Wang Xiaoming",
                    "orcid": "0000-0003-7777-8888",
                }
            ],
            "institution": {"name": "Peking University"},
            "amount": 550000.0,
            "startDate": "2022-01-01",
            "endDate": "2025-12-31",
            "disciplineCode": ["C0601", "C0602"],
        }
    ],
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_nsfc_grant() -> None:
    """NSFC grant parses correctly into NonUsGrantRecord."""
    data = SAMPLE_NSFC_RESPONSE["results"][0]
    result = NsfcClient._parse_nsfc_grant(data)
    assert result is not None
    assert isinstance(result, NonUsGrantRecord)
    assert result.grant_reference == "82170001"
    assert "tumor immune evasion" in result.title
    assert "\u738b\u5c0f\u660e" in result.pi_names
    assert result.institution == "Peking University"
    assert result.amount_local == 550000.0


def test_nsfc_coverage_caveat() -> None:
    """Every NSFC record has the coverage caveat string."""
    data = SAMPLE_NSFC_RESPONSE["results"][0]
    result = NsfcClient._parse_nsfc_grant(data)
    assert result is not None
    assert result.coverage_caveat is not None
    assert result.coverage_caveat == NSFC_COVERAGE_CAVEAT
    assert "best-effort" in result.coverage_caveat.lower()


def test_nsfc_grant_metadata() -> None:
    """NSFC grants have correct metadata."""
    data = SAMPLE_NSFC_RESPONSE["results"][0]
    result = NsfcClient._parse_nsfc_grant(data)
    assert result is not None
    assert result.funder == "NSFC"
    assert result.funder_country == "CN"
    assert result.source == "nsfc"
    assert result.currency == "CNY"
    assert result.institution_country == "CN"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination() -> None:
    """Pagination: fetch_grants pages through NSFC results."""
    client = NsfcClient()

    page1 = {
        "total": 2,
        "results": [SAMPLE_NSFC_RESPONSE["results"][0]],
    }
    page2 = {
        "total": 2,
        "results": [
            {
                "grantCode": "99990001",
                "title_cn": "\u7b2c\u4e8c\u4e2a\u9879\u76ee",
                "principalInvestigators": [{"name": "\u674e\u56db"}],
                "amount": 300000.0,
                "disciplineCode": ["A0101"],
            }
        ],
    }

    route = respx.get(f"{NSFC_API_URL}/projects")
    route.side_effect = [
        Response(200, json=page1),
        Response(200, json=page2),
    ]

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants(batch_size=1):
        results.append(grant)

    assert len(results) == 2
    assert results[0].grant_reference == "82170001"
    assert results[1].grant_reference == "99990001"
    # Both records must have the coverage caveat
    for r in results:
        assert r.coverage_caveat == NSFC_COVERAGE_CAVEAT


def test_nsfc_lower_batch_size() -> None:
    """Default batch_size for NSFC is 50 (not 100)."""
    sig = inspect.signature(NsfcClient.fetch_grants)
    batch_param = sig.parameters["batch_size"]
    assert batch_param.default == 50


def test_parse_nsfc_missing_grant_code() -> None:
    """Parse returns None when grant code is missing."""
    result = NsfcClient._parse_nsfc_grant({"title_cn": "No code"})
    assert result is None
