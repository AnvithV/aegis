"""Lens.org patent API client — replacement for defunct PatentsView."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)

LENS_API_URL = "https://api.lens.org/patent/search"


class LensInventor(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    residence: str | None = None


class LensPatentRecord(BaseModel):
    """Structured patent from Lens.org."""

    model_config = ConfigDict(frozen=True)

    lens_id: str
    doc_number: str | None
    title: str
    abstract: str | None
    date_published: date | None
    inventors: list[LensInventor]
    assignees: list[str]          # applicant names
    cpc_symbols: list[str]
    cited_by_count: int


class LensClient:
    """Client wrapping the Lens.org patent search API.

    Free academic token at https://www.lens.org/lens/user/subscriptions.
    Set LENS_API_TOKEN in the environment.
    """

    def __init__(
        self,
        api_token: str | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._token = api_token or os.environ.get("LENS_API_TOKEN", "")
        self._retry = retry_policy or RetryPolicy(RetryConfig())
        if not self._token:
            logger.warning("LENS_API_TOKEN not set — patent search will be skipped")

    async def search_by_text(
        self,
        query_text: str,
        since: date | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[LensPatentRecord]:
        """Full-text patent search on title + abstract via Lens.org.

        Yields LensPatentRecord objects with pagination.
        """
        if not self._token:
            return

        must: list[dict[str, Any]] = [
            {
                "multi_match": {
                    "query": query_text,
                    "fields": ["title", "abstract"],
                    "type": "best_fields",
                }
            }
        ]
        if since is not None:
            must.append({"range": {"date_published": {"gte": since.isoformat()}}})

        body: dict[str, Any] = {
            "query": {"bool": {"must": must}},
            "include": [
                "lens_id",
                "doc_number",
                "title",
                "abstract",
                "date_published",
                "inventor",
                "applicant",
                "class_cpc",
                "cited_by",
            ],
            "size": batch_size,
            "from": 0,
        }

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        offset = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                body["from"] = offset

                async def _do_post(
                    b: dict[str, Any] = body,
                    h: dict[str, str] = headers,
                ) -> httpx.Response:
                    resp = await client.post(LENS_API_URL, json=b, headers=h)
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_post)
                data = response.json()
                results = data.get("results") or []

                if not results:
                    break

                for item in results:
                    record = self._parse(item)
                    if record is not None:
                        yield record

                total = data.get("total", 0)
                offset += batch_size
                if offset >= total:
                    break

    @staticmethod
    def _parse(data: dict[str, Any]) -> LensPatentRecord | None:
        try:
            inventors = []
            for inv in data.get("inventor") or []:
                name = inv.get("name", "").strip()
                if name:
                    inventors.append(
                        LensInventor(
                            name=name,
                            residence=inv.get("residence"),
                        )
                    )

            assignees = [
                a.get("name", "").strip()
                for a in (data.get("applicant") or [])
                if a.get("name")
            ]

            cpc_symbols = []
            for cpc_group in data.get("class_cpc") or []:
                sym = cpc_group.get("symbol")
                if sym:
                    cpc_symbols.append(sym)

            grant_date: date | None = None
            dp = data.get("date_published")
            if dp:
                try:
                    grant_date = date.fromisoformat(str(dp)[:10])
                except (ValueError, TypeError):
                    pass

            cited_by = data.get("cited_by") or {}
            cited_count = cited_by.get("patent_count", 0) if isinstance(cited_by, dict) else 0

            return LensPatentRecord(
                lens_id=data.get("lens_id", ""),
                doc_number=data.get("doc_number"),
                title=data.get("title", ""),
                abstract=data.get("abstract"),
                date_published=grant_date,
                inventors=inventors,
                assignees=assignees,
                cpc_symbols=cpc_symbols,
                cited_by_count=cited_count,
            )
        except (KeyError, ValueError, TypeError):
            logger.warning("Failed to parse Lens patent: %s", data.get("lens_id", "?"))
            return None
