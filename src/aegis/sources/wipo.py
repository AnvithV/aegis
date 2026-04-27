"""WIPO PATENTSCOPE API client for PCT international patent applications."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryPolicy

logger = logging.getLogger(__name__)

PATENTSCOPE_API_URL = "https://patentscope.wipo.int/search/api/v1"


class WipoCredentials(BaseModel):
    """Credentials for WIPO PATENTSCOPE API access."""

    model_config = ConfigDict(frozen=True)

    access_token: str


class PctApplication(BaseModel):
    """A PCT international patent application record."""

    model_config = ConfigDict(frozen=True)

    application_number: str
    publication_number: str | None = None
    filing_date: date | None = None
    publication_date: date | None = None
    title: str
    abstract: str | None = None
    applicants: list[str]
    inventors: list[str]
    ipc_codes: list[str]
    designated_states: list[str]
    origin_country: str | None = None
    family_id: str | None = None


class WipoClient:
    """Typed client for the WIPO PATENTSCOPE API."""

    def __init__(
        self,
        credentials: WipoCredentials | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._credentials = credentials
        self._retry = retry_policy or RetryPolicy()

    async def fetch_pct_applications(
        self,
        ipc_codes: list[str],
        since: date,
        batch_size: int = 100,
    ) -> AsyncIterator[PctApplication]:
        """Search PATENTSCOPE for PCT applications by IPC codes since a date.

        Paginates with offset/limit.
        """
        headers: dict[str, str] = {}
        if self._credentials:
            headers["Authorization"] = f"Bearer {self._credentials.access_token}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            offset = 0
            while True:
                params: dict[str, Any] = {
                    "ipc": ",".join(ipc_codes),
                    "dpd": f">={since.isoformat()}",
                    "offset": offset,
                    "limit": batch_size,
                }

                async def _do_get(
                    p: dict[str, Any] = params,
                ) -> httpx.Response:
                    resp = await client.get(
                        f"{PATENTSCOPE_API_URL}/search",
                        params=p,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                results = body.get("results") or []

                if not results:
                    break

                for item in results:
                    parsed = self._parse_patentscope_result(item)
                    if parsed is not None:
                        yield parsed

                offset += len(results)
                total = body.get("total") or 0
                if offset >= total:
                    break

    async def fetch_pct_by_applicant(
        self,
        applicant_name: str,
        since: date,
    ) -> AsyncIterator[PctApplication]:
        """Search PATENTSCOPE by applicant name."""
        headers: dict[str, str] = {}
        if self._credentials:
            headers["Authorization"] = f"Bearer {self._credentials.access_token}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            offset = 0
            while True:
                params: dict[str, Any] = {
                    "applicant": applicant_name,
                    "dpd": f">={since.isoformat()}",
                    "offset": offset,
                    "limit": 100,
                }

                async def _do_get(
                    p: dict[str, Any] = params,
                ) -> httpx.Response:
                    resp = await client.get(
                        f"{PATENTSCOPE_API_URL}/search",
                        params=p,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                results = body.get("results") or []

                if not results:
                    break

                for item in results:
                    parsed = self._parse_patentscope_result(item)
                    if parsed is not None:
                        yield parsed

                offset += len(results)
                total = body.get("total") or 0
                if offset >= total:
                    break

    @staticmethod
    def _parse_patentscope_result(data: dict[str, Any]) -> PctApplication | None:
        """Parse a single result from the PATENTSCOPE API response."""
        app_number = data.get("applicationNumber") or data.get("application_number")
        if not app_number:
            return None

        title = data.get("title") or data.get("inventionTitle") or ""

        filing_date: date | None = None
        fd_str = data.get("filingDate") or data.get("filing_date")
        if fd_str:
            try:
                filing_date = date.fromisoformat(str(fd_str)[:10])
            except (ValueError, TypeError):
                pass

        pub_date: date | None = None
        pd_str = data.get("publicationDate") or data.get("publication_date")
        if pd_str:
            try:
                pub_date = date.fromisoformat(str(pd_str)[:10])
            except (ValueError, TypeError):
                pass

        applicants_raw = data.get("applicants") or []
        applicants = (
            applicants_raw
            if isinstance(applicants_raw, list)
            else [str(applicants_raw)]
        )

        inventors_raw = data.get("inventors") or []
        inventors = (
            inventors_raw
            if isinstance(inventors_raw, list)
            else [str(inventors_raw)]
        )

        ipc_raw = data.get("ipcCodes") or data.get("ipc_codes") or []
        ipc_codes = ipc_raw if isinstance(ipc_raw, list) else [str(ipc_raw)]

        designated = data.get("designatedStates") or data.get("designated_states") or []
        designated_states = (
            designated if isinstance(designated, list) else [str(designated)]
        )

        return PctApplication(
            application_number=str(app_number),
            publication_number=data.get("publicationNumber")
            or data.get("publication_number"),
            filing_date=filing_date,
            publication_date=pub_date,
            title=title,
            abstract=data.get("abstract"),
            applicants=applicants,
            inventors=inventors,
            ipc_codes=ipc_codes,
            designated_states=designated_states,
            origin_country=data.get("originCountry") or data.get("origin_country"),
            family_id=data.get("familyId") or data.get("family_id"),
        )
