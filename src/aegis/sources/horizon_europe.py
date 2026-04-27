"""Horizon Europe framework programme grant client via CORDIS API."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx

from aegis.sources.non_us_grants import NonUsGrantRecord
from aegis.sources.retry import RetryPolicy

logger = logging.getLogger(__name__)

CORDIS_API_URL = "https://cordis.europa.eu/api/v1"


class HorizonEuropeClient:
    """Typed client for Horizon Europe grants from the CORDIS API."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry = retry_policy or RetryPolicy()

    async def fetch_grants(
        self,
        programme_part: str | None = None,
        since_year: int | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Fetch Horizon Europe projects from CORDIS.

        Filters by frameworkProgramme=HORIZON to distinguish from FP7/H2020.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            offset = 0
            while True:
                params: dict[str, Any] = {
                    "q": "frameworkProgramme=HORIZON",
                    "type": "project",
                    "offset": offset,
                    "limit": batch_size,
                }
                if programme_part:
                    params["programmePart"] = programme_part
                if since_year is not None:
                    params["startYear"] = since_year

                async def _do_get(
                    p: dict[str, Any] = params,
                ) -> httpx.Response:
                    resp = await client.get(
                        f"{CORDIS_API_URL}/projects",
                        params=p,
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                results = body.get("results") or []

                if not results:
                    break

                for item in results:
                    parsed = self._parse_horizon_project(item)
                    if parsed is not None:
                        yield parsed

                offset += len(results)
                total = body.get("total") or 0
                if offset >= total:
                    break

    async def fetch_grants_by_institution(
        self,
        institution: str,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Search Horizon Europe grants by host institution."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {
                "q": f"frameworkProgramme=HORIZON AND {institution}",
                "type": "project",
                "limit": 100,
            }

            async def _do_get(
                p: dict[str, Any] = params,
            ) -> httpx.Response:
                resp = await client.get(
                    f"{CORDIS_API_URL}/projects",
                    params=p,
                )
                resp.raise_for_status()
                return resp

            response = await self._retry.execute(_do_get)
            body = response.json()
            results = body.get("results") or []

            for item in results:
                parsed = self._parse_horizon_project(item)
                if parsed is not None:
                    yield parsed

    @staticmethod
    def _parse_horizon_project(data: dict[str, Any]) -> NonUsGrantRecord | None:
        """Parse a CORDIS Horizon Europe project into a NonUsGrantRecord."""
        project_id = data.get("id") or data.get("projectId")
        acronym = data.get("acronym") or ""
        if not project_id:
            return None

        grant_ref = (
            f"HORIZON-{acronym}-{project_id}"
            if acronym
            else f"HORIZON-{project_id}"
        )
        title = data.get("title") or ""
        abstract = data.get("objective") or data.get("abstract")

        # Extract PI names from participants
        pi_names: list[str] = []
        pi_orcids: list[str | None] = []
        participants = data.get("participants") or data.get("coordinator") or []
        if isinstance(participants, list):
            for p in participants:
                name = p.get("name") or p.get("fullName") or ""
                if name:
                    pi_names.append(name)
                    pi_orcids.append(p.get("orcid"))
        elif isinstance(participants, dict):
            name = participants.get("name") or participants.get("fullName") or ""
            if name:
                pi_names.append(name)
                pi_orcids.append(participants.get("orcid"))

        # Institution
        institution = data.get("coordinatorName") or data.get("hostInstitution")
        if isinstance(institution, dict):
            institution = institution.get("name") or institution.get("legalName")

        # Amount
        amount: float | None = None
        cost = data.get("totalCost") or data.get("ecMaxContribution")
        if cost is not None:
            try:
                amount = float(cost)
            except (ValueError, TypeError):
                pass

        # Dates
        start_date: date | None = None
        end_date: date | None = None
        sd_str = data.get("startDate")
        ed_str = data.get("endDate")
        if sd_str:
            try:
                start_date = date.fromisoformat(str(sd_str)[:10])
            except (ValueError, TypeError):
                pass
        if ed_str:
            try:
                end_date = date.fromisoformat(str(ed_str)[:10])
            except (ValueError, TypeError):
                pass

        # Subject areas
        subjects_raw = (
            data.get("euroSciVoc")
            or data.get("subjects")
            or data.get("topics")
            or []
        )
        subject_areas: list[str] = (
            subjects_raw if isinstance(subjects_raw, list) else [str(subjects_raw)]
        )

        return NonUsGrantRecord(
            grant_reference=grant_ref,
            funder="Horizon Europe",
            funder_country="EU",
            title=title,
            abstract=abstract,
            pi_names=pi_names,
            pi_orcids=pi_orcids,
            institution=str(institution) if institution else None,
            institution_country=None,
            amount_local=amount,
            currency="EUR",
            start_date=start_date,
            end_date=end_date,
            subject_areas=subject_areas,
            source="horizon_europe",
            coverage_caveat=None,
            raw_json=json.dumps(data),
        )
