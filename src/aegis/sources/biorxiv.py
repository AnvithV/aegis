"""bioRxiv API client for daily preprint ingestion.

Uses the bioRxiv content API to fetch preprints by date range.
Preprints contribute to R(c,q) recency at 0.6x peer-reviewed weight.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy
from aegis.storage.schema import MeshDescriptor

logger = logging.getLogger(__name__)

BIORXIV_API_URL = "https://api.biorxiv.org/details/biorxiv"

# Preprint weight relative to peer-reviewed publication
PREPRINT_WEIGHT = 0.6


class PreprintAuthor(BaseModel):
    """Author on a preprint."""

    model_config = ConfigDict(frozen=True)

    full_name: str
    institution: str | None
    orcid: str | None
    is_corresponding: bool


class PreprintRecord(BaseModel):
    """Structured representation of a bioRxiv or medRxiv preprint."""

    model_config = ConfigDict(frozen=True)

    doi: str
    title: str
    abstract: str | None
    authors: list[PreprintAuthor]
    category: str | None            # bioRxiv subject category
    posted_date: date | None
    version: int
    server: str                      # "biorxiv" or "medrxiv"
    published_doi: str | None        # DOI of peer-reviewed version (if known)
    mesh_descriptors: list[MeshDescriptor]  # LLM-assigned MeSH (initially empty)
    weight: float = PREPRINT_WEIGHT  # Scoring weight relative to peer-reviewed


class BioRxivClient:
    """Typed client for the bioRxiv content API."""

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
        """Fetch all preprints posted on a specific date.

        Args:
            target_date: The date to fetch preprints for.
            batch_size: Number of records per API page (max 100).

        Yields:
            PreprintRecord objects for each preprint posted on target_date.
        """
        date_str = target_date.isoformat()
        cursor = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                url = f"{BIORXIV_API_URL}/{date_str}/{date_str}/{cursor}"

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
        """Fetch preprints posted within a date range.

        Args:
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).
            batch_size: Number of records per API page.

        Yields:
            PreprintRecord objects.
        """
        cursor = 0
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                url = f"{BIORXIV_API_URL}/{start_str}/{end_str}/{cursor}"

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
        """Parse a bioRxiv API response item into a PreprintRecord."""
        try:
            # Parse authors from the semicolon-separated author string
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
                server="biorxiv",
                published_doi=data.get("published") or None,
                mesh_descriptors=[],
            )
        except (KeyError, ValueError, TypeError):
            logger.warning("Failed to parse bioRxiv record: %s", data.get("doi", "?"))
            return None


def match_preprint_to_publication(
    preprint: PreprintRecord,
    published_doi: str,
) -> PreprintRecord:
    """Collapse a preprint with its peer-reviewed publication.

    Sets the published_doi field, marking this preprint as the
    'older version' of the peer-reviewed publication. Downstream
    scoring uses only the published version at full weight.

    Args:
        preprint: The original preprint record.
        published_doi: DOI of the peer-reviewed publication.

    Returns:
        Updated PreprintRecord with published_doi set.
    """
    return PreprintRecord(
        doi=preprint.doi,
        title=preprint.title,
        abstract=preprint.abstract,
        authors=preprint.authors,
        category=preprint.category,
        posted_date=preprint.posted_date,
        version=preprint.version,
        server=preprint.server,
        published_doi=published_doi,
        mesh_descriptors=preprint.mesh_descriptors,
        weight=0.0,  # Collapsed: no longer contributes independently
    )
