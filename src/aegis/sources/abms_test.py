"""Tests for ABMS board certification client."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from aegis.sources.abms import (
    AbmsCertification,
    AbmsClient,
    CertificationStatus,
    MOCStatus,
)

_API_URL = "https://api.certificationmatters.org/v1/physicians"

_MOCK_API_RESPONSE: dict[str, object] = {
    "certifications": [
        {
            "board": "American Board of Internal Medicine",
            "specialty": "Internal Medicine",
            "subspecialty": "Medical Oncology",
            "status": "Certified",
            "cert_date": "2015-06-15",
            "expiration_date": "2025-06-15",
            "moc_status": "Participating",
        },
        {
            "board": "American Board of Internal Medicine",
            "specialty": "Medical Oncology",
            "subspecialty": None,
            "status": "Certified",
            "cert_date": "2018-01-01",
            "expiration_date": "2028-01-01",
            "moc_status": "Not Participating",
        },
    ]
}


def test_certification_status_enum() -> None:
    """Verify all CertificationStatus values."""
    assert CertificationStatus.certified == "certified"
    assert CertificationStatus.expired == "expired"
    assert CertificationStatus.revoked == "revoked"
    assert CertificationStatus.not_certified == "not_certified"
    assert len(CertificationStatus) == 4


def test_moc_status_enum() -> None:
    """Verify all MOCStatus values."""
    assert MOCStatus.participating == "participating"
    assert MOCStatus.not_participating == "not_participating"
    assert MOCStatus.unknown == "unknown"
    assert len(MOCStatus) == 3


def test_parse_api_response() -> None:
    """Mock API response with 2 certifications, verify parsing."""
    certs = AbmsClient._parse_api_response(
        "1234567890", _MOCK_API_RESPONSE
    )
    assert len(certs) == 2
    assert certs[0].board_name == "American Board of Internal Medicine"
    assert certs[0].specialty == "Internal Medicine"
    assert certs[0].subspecialty == "Medical Oncology"
    assert certs[0].certification_status == CertificationStatus.certified
    assert certs[0].moc_status == MOCStatus.participating
    assert certs[1].specialty == "Medical Oncology"
    assert certs[1].moc_status == MOCStatus.not_participating


@pytest.mark.asyncio
@respx.mock
async def test_fetch_caching() -> None:
    """Second call uses cache, not a second HTTP request."""
    respx.get(_API_URL).mock(
        return_value=Response(200, json=_MOCK_API_RESPONSE),
    )
    client = AbmsClient(api_key="test-key")

    first = await client.fetch_certification("1234567890")
    assert len(first) == 2

    # Second call should use cache (no additional HTTP call)
    second = await client.fetch_certification("1234567890")
    assert len(second) == 2
    assert first is second  # Same list object from cache

    # Only one HTTP call was made
    assert respx.calls.call_count == 1


@pytest.mark.asyncio
async def test_fetch_fallback_no_api_key() -> None:
    """Without API key, verify fallback is used (returns empty)."""
    client = AbmsClient(api_key=None)
    certs = await client.fetch_certification("9876543210")
    assert certs == []


def test_abms_certification_model() -> None:
    """Create AbmsCertification, verify fields."""
    cert = AbmsCertification(
        npi="5555555555",
        board_name="American Board of Surgery",
        specialty="General Surgery",
        subspecialty="Surgical Critical Care",
        certification_status=CertificationStatus.certified,
        certification_date="2020-03-01",
        expiration_date="2030-03-01",
        moc_status=MOCStatus.participating,
    )
    assert cert.npi == "5555555555"
    assert cert.board_name == "American Board of Surgery"
    assert cert.specialty == "General Surgery"
    assert cert.subspecialty == "Surgical Critical Care"
    assert cert.certification_status == CertificationStatus.certified
    assert cert.certification_date == "2020-03-01"
    assert cert.expiration_date == "2030-03-01"
    assert cert.moc_status == MOCStatus.participating
