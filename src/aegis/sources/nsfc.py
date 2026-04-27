"""National Natural Science Foundation of China (NSFC) grant client — best-effort."""

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

NSFC_API_URL = "https://kd.nsfc.cn/api/v1"

NSFC_COVERAGE_CAVEAT = (
    "NSFC data is best-effort from public records only. Coverage is partial "
    "-- not all funded projects are publicly accessible. Grant amounts and "
    "detailed project information may be incomplete."
)


class NsfcClient:
    """Typed client for NSFC public grant data (best-effort coverage)."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry = retry_policy or RetryPolicy()

    async def fetch_grants(
        self,
        keywords: list[str] | None = None,
        since_year: int | None = None,
        batch_size: int = 50,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Fetch NSFC grants from public API.

        Lower default batch_size (50) due to rate constraints.
        Every record gets the NSFC_COVERAGE_CAVEAT.
        """
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
                    params["year"] = f">={since_year}"

                async def _do_get(
                    p: dict[str, Any] = params,
                ) -> httpx.Response:
                    resp = await client.get(
                        f"{NSFC_API_URL}/projects",
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
                    parsed = self._parse_nsfc_grant(item)
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
        """Search NSFC grants by PI name (supports Chinese and English)."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {
                "pi": pi_name,
                "limit": 50,
            }

            async def _do_get(
                p: dict[str, Any] = params,
            ) -> httpx.Response:
                resp = await client.get(
                    f"{NSFC_API_URL}/projects",
                    params=p,
                )
                resp.raise_for_status()
                return resp

            response = await self._retry.execute(_do_get)
            body = response.json()
            results = body.get("results") or []

            for item in results:
                parsed = self._parse_nsfc_grant(item)
                if parsed is not None:
                    yield parsed

    @staticmethod
    def _parse_nsfc_grant(data: dict[str, Any]) -> NonUsGrantRecord | None:
        """Parse an NSFC response into a NonUsGrantRecord.

        Always sets coverage_caveat=NSFC_COVERAGE_CAVEAT.
        """
        grant_code = data.get("grantCode") or data.get("projectCode") or data.get("id")
        if not grant_code:
            return None

        # Title: Chinese with English if available
        title_cn = data.get("title_cn") or data.get("title") or ""
        title_en = data.get("title_en") or ""
        title = f"{title_cn} / {title_en}".strip(" /") if title_en else title_cn

        # PI names
        pi_names: list[str] = []
        pi_orcids: list[str | None] = []
        pi_data = data.get("principalInvestigators") or data.get("pis") or []
        if isinstance(pi_data, list):
            for pi in pi_data:
                if isinstance(pi, dict):
                    name = (
                        pi.get("name")
                        or pi.get("name_cn")
                        or pi.get("name_en")
                        or ""
                    )
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
            institution = institution.get("name") or institution.get("name_cn")

        # Amount (CNY)
        amount: float | None = None
        val = data.get("amount") or data.get("fundingAmount")
        if val is not None:
            try:
                amount = float(val)
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

        # Discipline code as subject areas
        disciplines = data.get("disciplineCode") or data.get("subjects") or []
        subject_areas: list[str] = []
        if isinstance(disciplines, list):
            for d in disciplines:
                if isinstance(d, str):
                    subject_areas.append(d)
                elif isinstance(d, dict):
                    name = d.get("name") or d.get("code") or ""
                    if name:
                        subject_areas.append(name)
        elif isinstance(disciplines, str):
            subject_areas.append(disciplines)

        return NonUsGrantRecord(
            grant_reference=str(grant_code),
            funder="NSFC",
            funder_country="CN",
            title=title,
            abstract=data.get("abstract"),
            pi_names=pi_names,
            pi_orcids=pi_orcids,
            institution=str(institution) if institution else None,
            institution_country="CN",
            amount_local=amount,
            currency="CNY",
            start_date=start_date,
            end_date=end_date,
            subject_areas=subject_areas,
            source="nsfc",
            coverage_caveat=NSFC_COVERAGE_CAVEAT,
            raw_json=json.dumps(data, ensure_ascii=False),
        )
