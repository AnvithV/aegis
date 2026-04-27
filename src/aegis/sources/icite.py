"""NIH iCite API client for Relative Citation Ratio (RCR) data."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)

ICITE_API_URL = "https://icite.od.nih.gov/api/pubs"


class IciteRecord(BaseModel):
    """RCR and citation data for a single PubMed article."""

    model_config = ConfigDict(frozen=True)

    pmid: str
    year: int | None
    relative_citation_ratio: float | None
    citation_count: int
    expected_citations_per_year: float | None
    field_citation_rate: float | None
    is_research_article: bool
    doi: str | None


class IciteClient:
    """Client for the NIH iCite API (batch PMID lookups)."""

    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._retry = retry_policy or RetryPolicy(RetryConfig())

    async def fetch_by_pmids(
        self,
        pmids: list[str],
        batch_size: int = 200,
    ) -> AsyncIterator[IciteRecord]:
        """Fetch iCite records for a list of PMIDs in batches.

        The iCite API accepts up to 200 PMIDs per request.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(pmids), batch_size):
                batch = pmids[i : i + batch_size]
                pmid_str = ",".join(batch)

                async def _do_get(p: str = pmid_str) -> httpx.Response:
                    resp = await client.get(
                        ICITE_API_URL,
                        params={"pmids": p, "format": "json"},
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                records: list[dict[str, object]] = []
                if isinstance(body, dict) and "data" in body:
                    records = body["data"]
                elif isinstance(body, list):
                    records = body
                else:
                    records = [body]

                for item in records:
                    if not isinstance(item, dict):
                        continue
                    yield IciteRecord(
                        pmid=str(item.get("pmid", "")),
                        year=item.get("year"),  # type: ignore[arg-type]
                        relative_citation_ratio=item.get("relative_citation_ratio"),  # type: ignore[arg-type]
                        citation_count=item.get("citation_count", 0),  # type: ignore[arg-type]
                        expected_citations_per_year=item.get("expected_citations_per_year"),  # type: ignore[arg-type]
                        field_citation_rate=item.get("field_citation_rate"),  # type: ignore[arg-type]
                        is_research_article=bool(
                            item.get("is_research_article", False),
                        ),
                        doi=item.get("doi"),  # type: ignore[arg-type]
                    )
