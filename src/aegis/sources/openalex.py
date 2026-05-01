"""OpenAlex unified client for scholarly works, authors, funders, and concepts."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openalex.org"


class OpenAlexWork(BaseModel):
    """A scholarly work (publication) from OpenAlex."""

    model_config = ConfigDict(frozen=True)

    openalex_id: str
    doi: str | None
    pmid: str | None
    title: str
    publication_date: date | None
    type: str | None
    cited_by_count: int
    concepts: list[dict[str, str | float]]
    authorships: list[dict[str, str | None]]
    primary_location: dict[str, str | None] | None
    mesh_terms: list[str]
    raw_json: str


class OpenAlexAuthor(BaseModel):
    """An author profile from OpenAlex."""

    model_config = ConfigDict(frozen=True)

    openalex_id: str
    display_name: str
    orcid: str | None
    works_count: int
    cited_by_count: int
    affiliations: list[dict[str, str | None]]
    concepts: list[dict[str, str | float]]
    raw_json: str


class OpenAlexFunder(BaseModel):
    """A funder record from OpenAlex."""

    model_config = ConfigDict(frozen=True)

    openalex_id: str
    display_name: str
    country_code: str | None
    grants_count: int
    works_count: int
    raw_json: str


class OpenAlexConcept(BaseModel):
    """A concept tag from OpenAlex."""

    model_config = ConfigDict(frozen=True)

    openalex_id: str
    display_name: str
    level: int
    score: float
    raw_json: str


class OpenAlexClient:
    """Async client for the OpenAlex API.

    Provides access to works, authors, funders, and concepts with
    cursor-based pagination, rate limiting, and retry support.
    """

    def __init__(
        self,
        mailto: str = "aegis@example.com",
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._mailto = mailto
        self._retry = retry_policy or RetryPolicy(RetryConfig())
        # OpenAlex polite pool: 10 req/s with mailto, ~100k/day
        self._min_interval = 0.1
        self._last_request_time: float = 0.0

    async def _throttle(self) -> None:
        """Enforce per-second rate limits for the polite pool."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Make a rate-limited GET request with retry, returning parsed JSON."""
        params["mailto"] = self._mailto

        async def _do_request() -> dict[str, Any]:
            await self._throttle()
            resp = await client.get(f"{_BASE_URL}{path}", params=params)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

        return await self._retry.execute(_do_request)

    # ── Works ─────────────────────────────────────────────────────────────

    async def search_works(
        self,
        query: str,
        since_date: date | None = None,
        batch_size: int = 200,
    ) -> AsyncIterator[OpenAlexWork]:
        """Search works by topic string with optional date filter."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            cursor = "*"
            while cursor:
                params: dict[str, Any] = {
                    "search": query,
                    "per_page": batch_size,
                    "cursor": cursor,
                }
                if since_date is not None:
                    params["filter"] = f"from_publication_date:{since_date.isoformat()}"

                data = await self._get_json(client, "/works", params)
                results = data.get("results") or []
                if not results:
                    break

                for item in results:
                    yield self._parse_work(item)

                meta = data.get("meta") or {}
                cursor = meta.get("next_cursor")
                if cursor is None:
                    break

    async def get_works_by_author(
        self,
        author_id: str,
        since_date: date | None = None,
    ) -> AsyncIterator[OpenAlexWork]:
        """Get all works for a given author OpenAlex ID."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            cursor = "*"
            while cursor:
                filter_parts = [f"author.id:{author_id}"]
                if since_date is not None:
                    filter_parts.append(
                        f"from_publication_date:{since_date.isoformat()}"
                    )
                params: dict[str, Any] = {
                    "filter": ",".join(filter_parts),
                    "per_page": 200,
                    "cursor": cursor,
                }
                data = await self._get_json(client, "/works", params)
                results = data.get("results") or []
                if not results:
                    break

                for item in results:
                    yield self._parse_work(item)

                meta = data.get("meta") or {}
                cursor = meta.get("next_cursor")
                if cursor is None:
                    break

    @staticmethod
    def _parse_work(data: dict[str, Any]) -> OpenAlexWork:
        """Parse an OpenAlex work JSON object into a typed model."""
        # Extract concepts
        concepts: list[dict[str, str | float]] = []
        for c in data.get("concepts") or []:
            concepts.append({
                "id": c.get("id", ""),
                "display_name": c.get("display_name", ""),
                "score": float(c.get("score", 0.0)),
            })

        # Extract authorships
        authorships: list[dict[str, str | None]] = []
        for a in data.get("authorships") or []:
            author_info = a.get("author") or {}
            authorships.append({
                "author_id": author_info.get("id"),
                "author_name": author_info.get("display_name"),
                "position": a.get("author_position"),
            })

        # Primary location
        primary_loc = data.get("primary_location")
        primary_location: dict[str, str | None] | None = None
        if primary_loc:
            source = primary_loc.get("source") or {}
            primary_location = {
                "source_id": source.get("id"),
                "source_name": source.get("display_name"),
            }

        # PMID from ids field (many OpenAlex works have a PubMed ID)
        ids = data.get("ids") or {}
        raw_pmid = ids.get("pmid")  # e.g. "https://pubmed.ncbi.nlm.nih.gov/33521700"
        pmid: str | None = None
        if raw_pmid:
            pmid = str(raw_pmid).rstrip("/").rsplit("/", 1)[-1]

        # MeSH terms from concepts (OpenAlex concepts with wikidata mapped)
        mesh_terms: list[str] = []
        for c in data.get("mesh") or []:
            name = c.get("descriptor_name")
            if name:
                mesh_terms.append(name)

        # Publication date
        pub_date: date | None = None
        pub_date_str = data.get("publication_date")
        if pub_date_str:
            try:
                pub_date = date.fromisoformat(str(pub_date_str)[:10])
            except (ValueError, TypeError):
                pass

        return OpenAlexWork(
            openalex_id=data.get("id", ""),
            doi=data.get("doi"),
            pmid=pmid,
            title=data.get("title") or "",
            publication_date=pub_date,
            type=data.get("type"),
            cited_by_count=data.get("cited_by_count", 0),
            concepts=concepts,
            authorships=authorships,
            primary_location=primary_location,
            mesh_terms=mesh_terms,
            raw_json=json.dumps(data),
        )

    # ── Authors ───────────────────────────────────────────────────────────

    async def search_authors(
        self,
        query: str,
        affiliation_hint: str | None = None,
    ) -> AsyncIterator[OpenAlexAuthor]:
        """Search for author profiles by name, optionally filtering by affiliation."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {"search": query, "per_page": 25}
            if affiliation_hint:
                params["filter"] = (
                    f"last_known_institutions.display_name.search:{affiliation_hint}"
                )
            data = await self._get_json(client, "/authors", params)
            for item in data.get("results") or []:
                yield self._parse_author(item)

    async def get_author(self, author_id: str) -> OpenAlexAuthor:
        """Get a single author by OpenAlex ID (e.g. 'A5023888391')."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            data = await self._get_json(client, f"/authors/{author_id}", {})
            return self._parse_author(data)

    @staticmethod
    def _parse_author(data: dict[str, Any]) -> OpenAlexAuthor:
        """Parse an OpenAlex author JSON object into a typed model."""
        affiliations: list[dict[str, str | None]] = []
        for inst in data.get("last_known_institutions") or data.get("affiliations") or []:
            if isinstance(inst, dict):
                affiliations.append({
                    "institution_id": inst.get("id"),
                    "institution_name": inst.get("display_name"),
                    "country": inst.get("country_code"),
                })

        concepts: list[dict[str, str | float]] = []
        for c in data.get("x_concepts") or data.get("concepts") or []:
            concepts.append({
                "id": c.get("id", ""),
                "display_name": c.get("display_name", ""),
                "score": float(c.get("score", 0.0)),
            })

        orcid_raw = data.get("orcid")
        orcid: str | None = None
        if orcid_raw:
            orcid = str(orcid_raw).rsplit("/", 1)[-1] if "/" in str(orcid_raw) else str(orcid_raw)

        return OpenAlexAuthor(
            openalex_id=data.get("id", ""),
            display_name=data.get("display_name", ""),
            orcid=orcid,
            works_count=data.get("works_count", 0),
            cited_by_count=data.get("cited_by_count", 0),
            affiliations=affiliations,
            concepts=concepts,
            raw_json=json.dumps(data),
        )

    # ── Funders ───────────────────────────────────────────────────────────

    async def search_funders(self, query: str) -> AsyncIterator[OpenAlexFunder]:
        """Search funders by name."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {"search": query, "per_page": 25}
            data = await self._get_json(client, "/funders", params)
            for item in data.get("results") or []:
                yield self._parse_funder(item)

    @staticmethod
    def _parse_funder(data: dict[str, Any]) -> OpenAlexFunder:
        return OpenAlexFunder(
            openalex_id=data.get("id", ""),
            display_name=data.get("display_name", ""),
            country_code=data.get("country_code"),
            grants_count=data.get("grants_count", 0),
            works_count=data.get("works_count", 0),
            raw_json=json.dumps(data),
        )

    # ── Concepts ──────────────────────────────────────────────────────────

    async def get_concepts_for_work(
        self, work_id: str
    ) -> list[OpenAlexConcept]:
        """Get concept tags for a specific work."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            data = await self._get_json(client, f"/works/{work_id}", {})
            concepts: list[OpenAlexConcept] = []
            for c in data.get("concepts") or []:
                concepts.append(
                    OpenAlexConcept(
                        openalex_id=c.get("id", ""),
                        display_name=c.get("display_name", ""),
                        level=c.get("level", 0),
                        score=float(c.get("score", 0.0)),
                        raw_json=json.dumps(c),
                    )
                )
            return concepts
