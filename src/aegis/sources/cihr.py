"""Canadian Institutes of Health Research (CIHR) grant client."""

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

CIHR_API_URL = "https://webapps.cihr-irsc.gc.ca/decisions/api/v1"


class CihrClient:
    """Typed client for CIHR Funding Decisions Database."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry = retry_policy or RetryPolicy()

    async def fetch_grants(
        self,
        keywords: list[str] | None = None,
        since_year: int | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Fetch CIHR grants, paginated."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            offset = 0
            while True:
                params: dict[str, Any] = {
                    "offset": offset,
                    "limit": batch_size,
                }
                if keywords:
                    params["keywords"] = ",".join(keywords)
                if since_year is not None:
                    params["fiscalYear"] = f">={since_year}"

                async def _do_get(
                    p: dict[str, Any] = params,
                ) -> httpx.Response:
                    resp = await client.get(
                        f"{CIHR_API_URL}/grants",
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
                    parsed = self._parse_cihr_grant(item)
                    if parsed is not None:
                        yield parsed

                offset += len(results)
                total = body.get("total") or 0
                if offset >= total:
                    break

    async def fetch_grants_by_pi(
        self,
        pi_name: str,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Search CIHR grants by PI name."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {
                "pi": pi_name,
                "limit": 100,
            }

            async def _do_get(
                p: dict[str, Any] = params,
            ) -> httpx.Response:
                resp = await client.get(
                    f"{CIHR_API_URL}/grants",
                    params=p,
                )
                resp.raise_for_status()
                return resp

            response = await self._retry.execute(_do_get)
            body = response.json()
            results = body.get("results") or []

            for item in results:
                parsed = self._parse_cihr_grant(item)
                if parsed is not None:
                    yield parsed

    @staticmethod
    def _parse_cihr_grant(data: dict[str, Any]) -> NonUsGrantRecord | None:
        """Parse a CIHR grant response into a NonUsGrantRecord."""
        app_id = data.get("applicationId") or data.get("id")
        if not app_id:
            return None

        grant_ref = f"CIHR-{app_id}"
        title = data.get("title") or data.get("projectTitle") or ""

        # PI names
        pi_names: list[str] = []
        pi_orcids: list[str | None] = []
        pi_data = data.get("principalInvestigators") or data.get("pis") or []
        if isinstance(pi_data, list):
            for pi in pi_data:
                if isinstance(pi, dict):
                    name = pi.get("name") or pi.get("fullName") or ""
                    if name:
                        pi_names.append(name)
                        pi_orcids.append(pi.get("orcid"))
                elif isinstance(pi, str):
                    pi_names.append(pi)
                    pi_orcids.append(None)
        elif isinstance(pi_data, str):
            pi_names.append(pi_data)
            pi_orcids.append(None)

        # Institution
        institution = data.get("institution") or data.get("organizationName")
        if isinstance(institution, dict):
            institution = institution.get("name")

        # Amount (CAD)
        amount: float | None = None
        val = data.get("amount") or data.get("fundingAmount")
        if val is not None:
            try:
                amount = float(val)
            except (ValueError, TypeError):
                pass

        # Dates from fiscal year
        start_date: date | None = None
        end_date: date | None = None
        fy = data.get("fiscalYear") or data.get("fiscal_year")
        sd_str = data.get("startDate")
        ed_str = data.get("endDate")
        if sd_str:
            try:
                start_date = date.fromisoformat(str(sd_str)[:10])
            except (ValueError, TypeError):
                pass
        elif fy:
            try:
                start_date = date(int(fy), 4, 1)
            except (ValueError, TypeError):
                pass
        if ed_str:
            try:
                end_date = date.fromisoformat(str(ed_str)[:10])
            except (ValueError, TypeError):
                pass

        # Subject areas
        areas_raw = data.get("researchAreas") or data.get("subjects") or []
        subject_areas: list[str] = []
        if isinstance(areas_raw, list):
            for area in areas_raw:
                if isinstance(area, dict):
                    name = area.get("name") or area.get("text") or ""
                    if name:
                        subject_areas.append(name)
                elif isinstance(area, str):
                    subject_areas.append(area)

        return NonUsGrantRecord(
            grant_reference=str(grant_ref),
            funder="CIHR",
            funder_country="CA",
            title=title,
            abstract=data.get("abstract"),
            pi_names=pi_names,
            pi_orcids=pi_orcids,
            institution=str(institution) if institution else None,
            institution_country="CA",
            amount_local=amount,
            currency="CAD",
            start_date=start_date,
            end_date=end_date,
            subject_areas=subject_areas,
            source="cihr",
            coverage_caveat=None,
            raw_json=json.dumps(data),
        )
