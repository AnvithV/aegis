"""EPO Espacenet OPS API client for European patent ingestion."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy
from aegis.sources.uspto import PatentRecord

logger = logging.getLogger(__name__)

OPS_API_URL = "https://ops.epo.org/3.2/rest-services"
OPS_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"


class EpoCredentials(BaseModel):
    """OAuth2 credentials for EPO OPS API."""

    model_config = ConfigDict(frozen=True)

    consumer_key: str
    consumer_secret: str


class PatentFamily(BaseModel):
    """Patent family grouping (DOCDB family)."""

    model_config = ConfigDict(frozen=True)

    family_id: str
    members: list[str]


class EpoClient:
    """Typed client wrapping EPO Open Patent Services API."""

    def __init__(
        self,
        credentials: EpoCredentials | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._credentials = credentials
        self._retry = retry_policy or RetryPolicy(RetryConfig())
        self._access_token: str | None = None

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        """Obtain or refresh OAuth2 access token."""
        if self._access_token is not None:
            return self._access_token
        if self._credentials is None:
            raise ValueError("EPO credentials required for API access")
        resp = await client.post(
            OPS_AUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=(
                self._credentials.consumer_key,
                self._credentials.consumer_secret,
            ),
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        return self._access_token

    async def fetch_patents(
        self,
        cpc_codes: list[str],
        since: date,
        batch_size: int = 100,
    ) -> AsyncIterator[PatentRecord]:
        """Fetch EP patents matching CPC codes published since a given date.

        Reuses PatentRecord from the USPTO module for uniform downstream handling.
        Yields PatentRecord objects with source-specific fields.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            token = await self._ensure_token(client)
            headers = {"Authorization": f"Bearer {token}"}

            for cpc in cpc_codes:
                query = f'cpc={cpc} and pd>={since.strftime("%Y%m%d")}'
                start = 1
                while True:
                    end = start + batch_size - 1
                    url = f"{OPS_API_URL}/published-data/search"

                    async def _do_get(
                        q: str = query, s: int = start, e: int = end
                    ) -> httpx.Response:
                        resp = await client.get(
                            url,
                            params={"q": q, "Range": f"{s}-{e}"},
                            headers=headers,
                        )
                        resp.raise_for_status()
                        return resp

                    try:
                        response = await self._retry.execute(_do_get)
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 404:
                            break
                        raise

                    records = self._parse_ops_response(response.json())
                    if not records:
                        break

                    for record in records:
                        yield record

                    if len(records) < batch_size:
                        break
                    start += batch_size

    async def get_patent_family(
        self,
        patent_number: str,
        client: httpx.AsyncClient | None = None,
    ) -> PatentFamily | None:
        """Look up the DOCDB family for a patent number."""
        should_close = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=30.0)
        try:
            token = await self._ensure_token(client)
            url = f"{OPS_API_URL}/family/publication/docdb/{patent_number}"
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            body = resp.json()
            members = self._extract_family_members(body)
            family_id = (
                body.get("ops:world-patent-data", {})
                .get("ops:patent-family", {})
                .get("@family-id", patent_number)
            )
            return PatentFamily(family_id=str(family_id), members=members)
        finally:
            if should_close:
                await client.aclose()

    @staticmethod
    def _parse_ops_response(data: dict[str, Any]) -> list[PatentRecord]:
        """Parse OPS search response into PatentRecord objects."""
        records: list[PatentRecord] = []
        search_result = (
            data.get("ops:world-patent-data", {})
            .get("ops:biblio-search", {})
            .get("ops:search-result", {})
            .get("ops:publication-reference", [])
        )

        if isinstance(search_result, dict):
            search_result = [search_result]

        for pub_ref in search_result:
            doc_id = pub_ref.get("document-id", {})
            patent_number = (
                f"EP{doc_id.get('doc-number', '')}{doc_id.get('kind', '')}"
            )

            records.append(
                PatentRecord(
                    patent_number=patent_number,
                    grant_date=None,
                    application_date=None,
                    title="",
                    abstract=None,
                    claims_text=None,
                    inventors=[],
                    assignees=[],
                    cpc_codes=[],
                    ipc_codes=[],
                    forward_citation_count=0,
                    family_id=None,
                    maintenance_status=None,
                )
            )

        return records

    @staticmethod
    def _extract_family_members(data: dict[str, Any]) -> list[str]:
        """Extract member patent numbers from family lookup response."""
        members: list[str] = []
        family = (
            data.get("ops:world-patent-data", {})
            .get("ops:patent-family", {})
            .get("ops:family-member", [])
        )
        if isinstance(family, dict):
            family = [family]
        for member in family:
            doc_id = member.get("publication-reference", {}).get(
                "document-id", {}
            )
            num = doc_id.get("doc-number", "")
            country = doc_id.get("country", "")
            if num:
                members.append(f"{country}{num}")
        return members
