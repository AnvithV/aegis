"""ABMS board certification client."""

from __future__ import annotations

import logging
from enum import StrEnum

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)


class CertificationStatus(StrEnum):
    """Board certification status."""

    certified = "certified"
    expired = "expired"
    revoked = "revoked"
    not_certified = "not_certified"


class MOCStatus(StrEnum):
    """Maintenance of Certification status."""

    participating = "participating"
    not_participating = "not_participating"
    unknown = "unknown"


class AbmsCertification(BaseModel):
    """Board certification record for a physician."""

    model_config = ConfigDict(frozen=True)

    npi: str
    board_name: str
    specialty: str
    subspecialty: str | None
    certification_status: CertificationStatus
    certification_date: str | None
    expiration_date: str | None
    moc_status: MOCStatus


class AbmsClient:
    """Client for ABMS Certification Matters API.

    Falls back to CMS-published certification data if ABMS API
    credentials are not configured.
    """

    def __init__(
        self,
        api_key: str | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._api_key = api_key
        self._retry = retry_policy or RetryPolicy(RetryConfig())
        self._cache: dict[str, list[AbmsCertification]] = {}

    async def fetch_certification(
        self,
        npi: str,
    ) -> list[AbmsCertification]:
        """Fetch board certifications for a physician by NPI.

        Returns list because a physician may hold multiple
        board certifications.
        """
        if npi in self._cache:
            return self._cache[npi]

        if self._api_key:
            certs = await self._fetch_from_api(npi)
        else:
            certs = self._fetch_from_fallback(npi)

        self._cache[npi] = certs
        return certs

    async def _fetch_from_api(
        self, npi: str
    ) -> list[AbmsCertification]:
        """Fetch from ABMS Certification Matters API (paid)."""
        async with httpx.AsyncClient(timeout=30.0) as client:

            async def _do_get() -> httpx.Response:
                resp = await client.get(
                    "https://api.certificationmatters.org/v1/physicians",
                    params={"npi": npi},
                    headers={
                        "Authorization": f"Bearer {self._api_key}"
                    },
                )
                resp.raise_for_status()
                return resp

            response = await self._retry.execute(_do_get)
            return self._parse_api_response(npi, response.json())

    @staticmethod
    def _fetch_from_fallback(npi: str) -> list[AbmsCertification]:
        """Fallback: return empty (CMS cross-reference not yet implemented)."""
        logger.info("ABMS fallback for NPI %s (stub)", npi)
        return []

    @staticmethod
    def _parse_api_response(
        npi: str, data: dict[str, object]
    ) -> list[AbmsCertification]:
        """Parse ABMS API response into certification records."""
        certs: list[AbmsCertification] = []
        raw_certs = data.get("certifications", [])
        if not isinstance(raw_certs, list):
            return certs
        for item in raw_certs:
            if not isinstance(item, dict):
                continue
            status_str = str(
                item.get("status", "not_certified")
            ).lower()
            cert_status = CertificationStatus.not_certified
            if "certified" in status_str and "not" not in status_str:
                cert_status = CertificationStatus.certified
            elif "expired" in status_str:
                cert_status = CertificationStatus.expired
            elif "revoked" in status_str:
                cert_status = CertificationStatus.revoked

            moc_str = str(
                item.get("moc_status", "unknown")
            ).lower()
            moc = MOCStatus.unknown
            if "participating" in moc_str and "not" not in moc_str:
                moc = MOCStatus.participating
            elif "not" in moc_str:
                moc = MOCStatus.not_participating

            certs.append(
                AbmsCertification(
                    npi=npi,
                    board_name=str(item.get("board", "Unknown")),
                    specialty=str(item.get("specialty", "Unknown")),
                    subspecialty=item.get("subspecialty"),
                    certification_status=cert_status,
                    certification_date=item.get("cert_date"),
                    expiration_date=item.get("expiration_date"),
                    moc_status=moc,
                )
            )
        return certs
