"""USPTO PatentSearch API client for patent ingestion."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)

# New PatentSearch API (api.patentsview.org shut down May 2025)
PATENTSVIEW_API_URL = "https://search.patentsview.org/api/v1/patent/"


class InventorAttribution(BaseModel):
    """An inventor listed on a patent."""

    model_config = ConfigDict(frozen=True)

    inventor_id: str
    full_name: str
    first_name: str | None
    last_name: str | None
    is_lead_inventor: bool


class PatentAssignee(BaseModel):
    """Assignee (organization or individual) on a patent."""

    model_config = ConfigDict(frozen=True)

    assignee_id: str | None
    organization: str | None
    assignee_type: str


class PatentRecord(BaseModel):
    """Structured representation of a granted US patent."""

    model_config = ConfigDict(frozen=True)

    patent_number: str
    grant_date: date | None
    application_date: date | None
    title: str
    abstract: str | None
    claims_text: str | None
    inventors: list[InventorAttribution]
    assignees: list[PatentAssignee]
    cpc_codes: list[str]
    ipc_codes: list[str]
    forward_citation_count: int
    family_id: str | None
    maintenance_status: str | None


class UsptoClient:
    """Typed client wrapping the PatentSearch API (search.patentsview.org)."""

    def __init__(
        self,
        api_key: str | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("PATENTSVIEW_API_KEY", "")
        self._retry = retry_policy or RetryPolicy(RetryConfig())

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            h["X-Api-Key"] = self._api_key
        return h

    async def fetch_patents(
        self,
        cpc_codes: list[str],
        since: date,
        batch_size: int = 100,
    ) -> AsyncIterator[PatentRecord]:
        """Fetch patents matching CPC codes granted since a given date."""
        cpc_filter = [{"cpc_subgroup_id": cpc} for cpc in cpc_codes]
        query: dict[str, Any] = {
            "_and": [
                {"_or": cpc_filter},
                {"_gte": {"patent_date": since.isoformat()}},
            ]
        }
        fields = [
            "patent_id",
            "patent_date",
            "patent_title",
            "patent_abstract",
            "patent_num_us_patent_citations",
            "inventors",
            "assignees",
            "cpcs",
        ]

        offset = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                params = {
                    "q": json.dumps(query),
                    "f": json.dumps(fields),
                    "o": json.dumps({"size": batch_size, "offset": offset}),
                    "s": json.dumps([{"patent_date": "desc"}]),
                }

                async def _do_get(p: dict[str, str] = params) -> httpx.Response:
                    resp = await client.get(
                        PATENTSVIEW_API_URL,
                        params=p,
                        headers=self._headers(),
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                patents = body.get("patents") or []

                if not patents:
                    break

                for pat in patents:
                    record = self._parse_patent(pat)
                    if record is not None:
                        yield record

                total = body.get("total_patent_count", 0)
                offset += batch_size
                if offset >= total:
                    break

    async def search_by_text(
        self,
        query_text: str,
        since: date | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[PatentRecord]:
        """Fetch patents matching free-text search on title and abstract."""
        text_filter: dict[str, Any] = {
            "_text_any": {"patent_title": query_text, "patent_abstract": query_text}
        }
        if since is not None:
            query: dict[str, Any] = {
                "_and": [
                    text_filter,
                    {"_gte": {"patent_date": since.isoformat()}},
                ]
            }
        else:
            query = text_filter

        fields = [
            "patent_id",
            "patent_date",
            "patent_title",
            "patent_abstract",
            "patent_num_us_patent_citations",
            "inventors",
            "assignees",
            "cpcs",
        ]

        offset = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                params = {
                    "q": json.dumps(query),
                    "f": json.dumps(fields),
                    "o": json.dumps({"size": batch_size, "offset": offset}),
                    "s": json.dumps([{"patent_date": "desc"}]),
                }

                async def _do_get(p: dict[str, str] = params) -> httpx.Response:
                    resp = await client.get(
                        PATENTSVIEW_API_URL,
                        params=p,
                        headers=self._headers(),
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                patents = body.get("patents") or []

                if not patents:
                    break

                for pat in patents:
                    record = self._parse_patent(pat)
                    if record is not None:
                        yield record

                total = body.get("total_patent_count", 0)
                offset += batch_size
                if offset >= total:
                    break

    @staticmethod
    def _parse_patent(data: dict[str, Any]) -> PatentRecord | None:
        """Parse a PatentSearch API response into a PatentRecord.

        Handles both old field names (patent_number, inventor_first_name) and
        new field names (patent_id, inventor_name_first) for forward compatibility.
        """
        try:
            inventors = []
            for inv in data.get("inventors") or []:
                # New API uses inventor_name_first/last; old used inventor_first_name/last_name
                first = (
                    inv.get("inventor_name_first")
                    or inv.get("inventor_first_name")
                    or ""
                )
                last = (
                    inv.get("inventor_name_last")
                    or inv.get("inventor_last_name")
                    or ""
                )
                full = f"{first} {last}".strip()
                inv_id = (
                    inv.get("inventor_id")
                    or inv.get("inventor_key_id")
                    or ""
                )
                inventors.append(
                    InventorAttribution(
                        inventor_id=inv_id,
                        full_name=full,
                        first_name=first or None,
                        last_name=last or None,
                        is_lead_inventor=inv.get("inventor_sequence", 1) == 0,
                    )
                )

            assignees = []
            for asg in data.get("assignees") or []:
                assignees.append(
                    PatentAssignee(
                        assignee_id=asg.get("assignee_id"),
                        organization=asg.get("assignee_organization"),
                        assignee_type=(
                            "organization"
                            if asg.get("assignee_type", 0) in (2, 3)
                            else "individual"
                        ),
                    )
                )

            cpc_codes = [
                c.get("cpc_subgroup_id", "")
                for c in (data.get("cpcs") or [])
                if c.get("cpc_subgroup_id")
            ]

            grant_date = None
            if data.get("patent_date"):
                grant_date = date.fromisoformat(data["patent_date"])

            # New API uses patent_id; old used patent_number
            patent_num = data.get("patent_id") or data.get("patent_number", "")

            # New API uses patent_num_us_patent_citations; old used patent_num_cited_by_us_patents
            citations = (
                data.get("patent_num_us_patent_citations")
                or data.get("patent_num_cited_by_us_patents")
                or 0
            )

            return PatentRecord(
                patent_number=patent_num,
                grant_date=grant_date,
                application_date=None,
                title=data.get("patent_title", ""),
                abstract=data.get("patent_abstract"),
                claims_text=None,
                inventors=inventors,
                assignees=assignees,
                cpc_codes=cpc_codes,
                ipc_codes=[],
                forward_citation_count=citations,
                family_id=None,
                maintenance_status=None,
            )
        except (KeyError, ValueError, TypeError):
            logger.warning(
                "Failed to parse patent: %s",
                data.get("patent_id") or data.get("patent_number", "?"),
            )
            return None
