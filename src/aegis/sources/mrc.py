"""UK Medical Research Council (MRC) grant client via Gateway to Research (GtR) API."""

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

GTR_API_URL = "https://gtr.ukri.org/gtr/api"


class MrcClient:
    """Typed client for MRC grant data from the GtR API."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry = retry_policy or RetryPolicy()

    async def fetch_grants(
        self,
        search_term: str | None = None,
        since_year: int | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Fetch MRC grants from GtR API, filtering by funder 'MRC'."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            page = 1
            while True:
                params: dict[str, Any] = {
                    "q": search_term or "MRC",
                    "f": "fu.org.n",
                    "fv": "Medical Research Council",
                    "page": page,
                    "fetchSize": batch_size,
                }
                if since_year is not None:
                    params["sf"] = f"startDate,gt,{since_year}-01-01"

                async def _do_get(
                    p: dict[str, Any] = params,
                ) -> httpx.Response:
                    resp = await client.get(
                        f"{GTR_API_URL}/projects",
                        params=p,
                        headers={"Accept": "application/json"},
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                results = body.get("project") or body.get("results") or []

                if not results:
                    break

                for item in results:
                    parsed = self._parse_gtr_project(item)
                    if parsed is not None:
                        yield parsed

                total_pages = body.get("totalPages") or 1
                if page >= total_pages:
                    break
                page += 1

    async def fetch_grants_by_pi(
        self,
        pi_name: str,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Search GtR by PI name."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {
                "q": pi_name,
                "f": "per.fn",
                "page": 1,
                "fetchSize": 100,
            }

            async def _do_get(
                p: dict[str, Any] = params,
            ) -> httpx.Response:
                resp = await client.get(
                    f"{GTR_API_URL}/projects",
                    params=p,
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                return resp

            response = await self._retry.execute(_do_get)
            body = response.json()
            results = body.get("project") or body.get("results") or []

            for item in results:
                parsed = self._parse_gtr_project(item)
                if parsed is not None:
                    yield parsed

    @staticmethod
    def _parse_gtr_project(data: dict[str, Any]) -> NonUsGrantRecord | None:
        """Parse a GtR project response into a NonUsGrantRecord."""
        grant_ref = data.get("grantReference") or data.get("id")
        if not grant_ref:
            return None

        title = data.get("title") or ""
        abstract = data.get("abstractText") or data.get("abstract")

        # PI names
        pi_names: list[str] = []
        pi_orcids: list[str | None] = []
        pi_data = data.get("principalInvestigator") or data.get("investigator")
        if isinstance(pi_data, dict):
            fname = pi_data.get("firstName") or ""
            lname = pi_data.get("surname") or pi_data.get("lastName") or ""
            full_name = f"{fname} {lname}".strip()
            if full_name:
                pi_names.append(full_name)
                pi_orcids.append(pi_data.get("orcid"))
        elif isinstance(pi_data, list):
            for pi in pi_data:
                fname = pi.get("firstName") or ""
                lname = pi.get("surname") or pi.get("lastName") or ""
                full_name = f"{fname} {lname}".strip()
                if full_name:
                    pi_names.append(full_name)
                    pi_orcids.append(pi.get("orcid"))

        # Institution from lead organisation
        institution: str | None = None
        org = data.get("leadOrganisation") or data.get("organisation")
        if isinstance(org, dict):
            institution = org.get("name") or org.get("legalName")
        elif isinstance(org, str):
            institution = org

        # Amount (GBP)
        amount: float | None = None
        fund = data.get("fund") or data.get("valuePounds")
        if isinstance(fund, dict):
            val = fund.get("valuePounds") or fund.get("amount")
            if val is not None:
                try:
                    amount = float(val)
                except (ValueError, TypeError):
                    pass
        elif fund is not None:
            try:
                amount = float(fund)
            except (ValueError, TypeError):
                pass

        # Dates
        start_date: date | None = None
        end_date: date | None = None
        sd_str = data.get("startDate") or (
            fund.get("start") if isinstance(fund, dict) else None
        )
        ed_str = data.get("endDate") or (
            fund.get("end") if isinstance(fund, dict) else None
        )
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

        # Subject areas from research topics
        topics_raw = data.get("researchTopics") or data.get("subjects") or []
        subject_areas: list[str] = []
        if isinstance(topics_raw, list):
            for topic in topics_raw:
                if isinstance(topic, dict):
                    name = topic.get("text") or topic.get("name") or ""
                    if name:
                        subject_areas.append(name)
                elif isinstance(topic, str):
                    subject_areas.append(topic)

        return NonUsGrantRecord(
            grant_reference=str(grant_ref),
            funder="MRC",
            funder_country="GB",
            title=title,
            abstract=abstract,
            pi_names=pi_names,
            pi_orcids=pi_orcids,
            institution=institution,
            institution_country="GB",
            amount_local=amount,
            currency="GBP",
            start_date=start_date,
            end_date=end_date,
            subject_areas=subject_areas,
            source="mrc",
            coverage_caveat=None,
            raw_json=json.dumps(data),
        )
