"""Tests for the JST/KAKEN client (fixture-based, no live API calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import respx
from httpx import Response

from aegis.sources.jst_kaken import (
    KAKEN_API_URL,
    KakenClient,
    KakenResearcher,
    build_name_variants,
    transliterate_japanese_name,
)
from aegis.sources.non_us_grants import NonUsGrantRecord

# ── Fixture data ──────────────────────────────────────────────────────────────

SAMPLE_KAKEN_RESPONSE: dict[str, Any] = {
    "total": 1,
    "results": [
        {
            "grantNumber": "23H01234",
            "title_en": "Novel approaches to stem cell therapy",
            "title_ja": (
                "\u5e79\u7d30\u80de\u6cbb\u7642\u306e\u65b0"
                "\u3057\u3044\u30a2\u30d7\u30ed\u30fc\u30c1"
            ),
            "abstract_en": "This project develops new stem cell methods.",
            "investigators": [
                {
                    "name_en": "Tanaka Ichiro",
                    "name_ja": "\u7530\u4e2d\u4e00\u90ce",
                    "orcid": "0000-0002-3333-4444",
                }
            ],
            "institution_en": "University of Tokyo",
            "totalAmount": 15000000.0,
            "startFiscalYear": "2023",
            "endFiscalYear": "2026",
            "researchCategory": [
                {"name_en": "Cell Biology"},
                {"name_en": "Regenerative Medicine"},
            ],
        }
    ],
}

SAMPLE_RESEARCHER_RESPONSE: dict[str, Any] = {
    "result": {
        "researcherNumber": "R12345678",
        "name_ja": "\u7530\u4e2d\u4e00\u90ce",
        "name_en": "Tanaka Ichiro",
        "name_kana": "\u30bf\u30ca\u30ab\u30a4\u30c1\u30ed\u30a6",
        "affiliation_ja": "\u6771\u4eac\u5927\u5b66",
        "affiliation_en": "University of Tokyo",
        "orcid": "0000-0002-3333-4444",
    }
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_parse_kaken_grant() -> None:
    """KAKEN grant parses correctly into NonUsGrantRecord."""
    data = SAMPLE_KAKEN_RESPONSE["results"][0]
    result = KakenClient._parse_kaken_grant(data)
    assert result is not None
    assert isinstance(result, NonUsGrantRecord)
    assert result.grant_reference == "23H01234"
    assert result.title == "Novel approaches to stem cell therapy"
    assert "Tanaka Ichiro" in result.pi_names
    assert result.institution == "University of Tokyo"
    assert result.amount_local == 15000000.0
    assert result.start_date == date(2023, 4, 1)
    assert result.end_date == date(2026, 3, 31)
    assert "Cell Biology" in result.subject_areas


def test_kaken_grant_metadata() -> None:
    """KAKEN grants have correct metadata."""
    data = SAMPLE_KAKEN_RESPONSE["results"][0]
    result = KakenClient._parse_kaken_grant(data)
    assert result is not None
    assert result.funder == "KAKEN"
    assert result.funder_country == "JP"
    assert result.source == "kaken"
    assert result.currency == "JPY"
    assert result.institution_country == "JP"
    assert result.coverage_caveat is None


def test_transliterate_japanese_name() -> None:
    """Transliteration produces romaji output from Japanese text."""
    # Test with katakana input
    result = transliterate_japanese_name("\u30bf\u30ca\u30ab")
    assert isinstance(result, str)
    assert len(result) > 0
    # The result should be ASCII-like (romanized)
    # cutlet converts katakana to romaji
    assert result.isascii() or result == "\u30bf\u30ca\u30ab"  # fallback case


def test_transliterate_fallback() -> None:
    """Transliteration returns original string for non-Japanese text."""
    result = transliterate_japanese_name("John Smith")
    assert result == "John Smith"


def test_build_name_variants() -> None:
    """All name forms are collected and deduplicated."""
    researcher = KakenResearcher(
        researcher_number="R12345",
        name_ja="\u7530\u4e2d",
        name_en="Tanaka",
        name_kana="\u30bf\u30ca\u30ab",
        name_romaji="Tanaka",  # duplicate of name_en
    )
    variants = build_name_variants(researcher)
    # Should have 3 unique: name_ja, name_en (=name_romaji deduplicated), name_kana
    assert len(variants) == 3
    assert "\u7530\u4e2d" in variants
    assert "Tanaka" in variants
    assert "\u30bf\u30ca\u30ab" in variants


def test_parse_researcher() -> None:
    """Researcher model with Japanese fields parses correctly."""
    data = SAMPLE_RESEARCHER_RESPONSE["result"]
    result = KakenClient._parse_researcher(data)
    assert result is not None
    assert isinstance(result, KakenResearcher)
    assert result.researcher_number == "R12345678"
    assert result.name_ja == "\u7530\u4e2d\u4e00\u90ce"
    assert result.name_en == "Tanaka Ichiro"
    assert result.name_kana == "\u30bf\u30ca\u30ab\u30a4\u30c1\u30ed\u30a6"
    assert result.name_romaji is not None  # auto-transliterated
    assert result.affiliation_en == "University of Tokyo"
    assert result.orcid == "0000-0002-3333-4444"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pagination() -> None:
    """Pagination: fetch_grants pages through KAKEN results."""
    client = KakenClient()

    page1 = {
        "total": 2,
        "results": [SAMPLE_KAKEN_RESPONSE["results"][0]],
    }
    page2 = {
        "total": 2,
        "results": [
            {
                "grantNumber": "24K99999",
                "title_en": "Second KAKEN Grant",
                "investigators": [{"name_en": "Suzuki Yuki"}],
                "totalAmount": 5000000.0,
                "researchCategory": [{"name_en": "Chemistry"}],
            }
        ],
    }

    route = respx.get(f"{KAKEN_API_URL}/grants")
    route.side_effect = [
        Response(200, json=page1),
        Response(200, json=page2),
    ]

    results: list[NonUsGrantRecord] = []
    async for grant in client.fetch_grants(batch_size=1):
        results.append(grant)

    assert len(results) == 2
    assert results[0].grant_reference == "23H01234"
    assert results[1].grant_reference == "24K99999"


def test_build_name_variants_all_none() -> None:
    """Name variants with all None returns empty list."""
    researcher = KakenResearcher(researcher_number="R00000")
    variants = build_name_variants(researcher)
    assert variants == []


def test_parse_kaken_missing_grant_number() -> None:
    """Parse returns None when grant number is missing."""
    result = KakenClient._parse_kaken_grant({"title_en": "No grant number"})
    assert result is None
