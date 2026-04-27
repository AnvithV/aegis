"""medRxiv API client for daily preprint ingestion.

Uses the bioRxiv content API (shared infrastructure) to fetch
medRxiv preprints by date range. Preprints contribute to R(c,q)
recency at 0.6x peer-reviewed weight.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx

from aegis.sources.biorxiv import (
    PreprintAuthor,
    PreprintRecord,
)
from aegis.sources.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)

MEDRXIV_API_URL = "https://api.biorxiv.org/details/medrxiv"


class MedRxivClient:
    """Typed client for the medRxiv content API.

    medRxiv shares infrastructure with bioRxiv; the API is identical
    except for the server name in the URL path.
    """

    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._retry = retry_policy or RetryPolicy(RetryConfig())

    async def fetch_daily(
        self,
        target_date: date,
        batch_size: int = 100,
    ) -> AsyncIterator[PreprintRecord]:
        """Fetch all medRxiv preprints posted on a specific date.

        Args:
            target_date: The date to fetch preprints for.
            batch_size: Number of records per API page.

        Yields:
            PreprintRecord objects with server="medrxiv".
        """
        date_str = target_date.isoformat()
        cursor = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                url = f"{MEDRXIV_API_URL}/{date_str}/{date_str}/{cursor}"

                async def _do_get(u: str = url) -> httpx.Response:
                    resp = await client.get(u)
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()

                messages = body.get("messages", [{}])
                total = int(messages[0].get("total", 0)) if messages else 0
                records = body.get("collection", [])

                if not records:
                    break

                for item in records:
                    record = self._parse_record(item)
                    if record is not None:
                        yield record

                cursor += len(records)
                if cursor >= total:
                    break

    async def fetch_date_range(
        self,
        start_date: date,
        end_date: date,
        batch_size: int = 100,
    ) -> AsyncIterator[PreprintRecord]:
        """Fetch medRxiv preprints within a date range."""
        cursor = 0
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                url = f"{MEDRXIV_API_URL}/{start_str}/{end_str}/{cursor}"

                async def _do_get(u: str = url) -> httpx.Response:
                    resp = await client.get(u)
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()

                messages = body.get("messages", [{}])
                total = int(messages[0].get("total", 0)) if messages else 0
                records = body.get("collection", [])

                if not records:
                    break

                for item in records:
                    record = self._parse_record(item)
                    if record is not None:
                        yield record

                cursor += len(records)
                if cursor >= total:
                    break

    @staticmethod
    def _parse_record(data: dict[str, Any]) -> PreprintRecord | None:
        """Parse a medRxiv API response item into a PreprintRecord."""
        try:
            authors: list[PreprintAuthor] = []
            author_str = data.get("authors", "")
            if author_str:
                for name in author_str.split(";"):
                    name = name.strip()
                    if name:
                        authors.append(PreprintAuthor(
                            full_name=name,
                            institution=None,
                            orcid=None,
                            is_corresponding=False,
                        ))

            posted_date = None
            date_str = data.get("date")
            if date_str:
                posted_date = date.fromisoformat(date_str)

            version = int(data.get("version", "1"))

            return PreprintRecord(
                doi=data.get("doi", ""),
                title=data.get("title", ""),
                abstract=data.get("abstract"),
                authors=authors,
                category=data.get("category"),
                posted_date=posted_date,
                version=version,
                server="medrxiv",
                published_doi=data.get("published") or None,
                mesh_descriptors=[],
            )
        except (KeyError, ValueError, TypeError):
            logger.warning("Failed to parse medRxiv record: %s", data.get("doi", "?"))
            return None
