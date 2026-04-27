"""USPTO PatentsView API client for patent ingestion."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)

PATENTSVIEW_API_URL = "https://api.patentsview.org/patents/query"


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
    """Typed client wrapping the PatentsView API."""

    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._retry = retry_policy or RetryPolicy(RetryConfig())

    async def fetch_patents(
        self,
        cpc_codes: list[str],
        since: date,
        batch_size: int = 100,
    ) -> AsyncIterator[PatentRecord]:
        """Fetch patents matching CPC codes granted since a given date.

        Uses PatentsView query API with pagination.
        Yields PatentRecord objects.
        """
        cpc_filter = [{"cpc_subgroup_id": cpc} for cpc in cpc_codes]
        query = {
            "_and": [
                {"_or": cpc_filter},
                {"_gte": {"patent_date": since.isoformat()}},
            ]
        }
        fields = [
            "patent_number",
            "patent_date",
            "patent_title",
            "patent_abstract",
            "patent_firstnamed_inventor_id",
            "patent_num_cited_by_us_patents",
        ]

        page = 1
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                payload = {
                    "q": query,
                    "f": fields,
                    "o": {"page": page, "per_page": batch_size},
                    "s": [{"patent_date": "desc"}],
                }

                async def _do_post(p: dict[str, Any] = payload) -> httpx.Response:
                    resp = await client.post(
                        PATENTSVIEW_API_URL,
                        json=p,
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_post)
                body = response.json()
                patents = body.get("patents") or []

                if not patents:
                    break

                for pat in patents:
                    record = self._parse_patent(pat)
                    if record is not None:
                        yield record

                total = body.get("total_patent_count", 0)
                if page * batch_size >= total:
                    break
                page += 1

    @staticmethod
    def _parse_patent(data: dict[str, Any]) -> PatentRecord | None:
        """Parse a PatentsView API response into a PatentRecord."""
        try:
            inventors = []
            for inv in data.get("inventors") or []:
                first = inv.get("inventor_first_name") or ""
                last = inv.get("inventor_last_name") or ""
                full = f"{first} {last}".strip()
                inventors.append(
                    InventorAttribution(
                        inventor_id=inv.get("inventor_id", ""),
                        full_name=full,
                        first_name=inv.get("inventor_first_name"),
                        last_name=inv.get("inventor_last_name"),
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

            return PatentRecord(
                patent_number=data.get("patent_number", ""),
                grant_date=grant_date,
                application_date=None,
                title=data.get("patent_title", ""),
                abstract=data.get("patent_abstract"),
                claims_text=None,
                inventors=inventors,
                assignees=assignees,
                cpc_codes=cpc_codes,
                ipc_codes=[],
                forward_citation_count=data.get(
                    "patent_num_cited_by_us_patents", 0
                ),
                family_id=None,
                maintenance_status=None,
            )
        except (KeyError, ValueError, TypeError):
            logger.warning(
                "Failed to parse patent: %s", data.get("patent_number", "?")
            )
            return None
