"""NIH RePORTER v2 API client for grant record retrieval."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryPolicy

logger = logging.getLogger(__name__)

REPORTER_API_URL = "https://api.reporter.nih.gov/v2/projects/search"


class GrantPI(BaseModel):
    """Principal investigator on a grant."""

    model_config = ConfigDict(frozen=True)

    full_name: str
    era_id: str
    orcid: str | None = None
    role: str
    organization: str | None = None


class GrantRecord(BaseModel):
    """A single NIH grant record from RePORTER."""

    model_config = ConfigDict(frozen=True)

    project_number: str
    activity_code: str
    pis: list[GrantPI]
    total_cost: int | None = None
    fiscal_year: int
    project_terms: list[str]
    rcdc_categories: list[str]
    organization_name: str | None = None
    organization_ror_candidate: str | None = None
    award_notice_date: date | None = None
    is_active: bool
    raw_json: str


def _parse_grant(data: dict[str, Any]) -> GrantRecord:
    """Parse a single grant record from RePORTER API response."""
    pis: list[GrantPI] = []
    for pi_data in data.get("principal_investigators") or []:
        full_name = pi_data.get("full_name") or ""
        era_id = str(pi_data.get("profile_id") or "")
        if not era_id:
            era_id = str(pi_data.get("era_commons_id", ""))
        orcid = pi_data.get("orcid") or None
        role = pi_data.get("is_contact_pi")
        role_str = "Contact PI" if role else "Co-PI"
        org = pi_data.get("org_name") or None
        pis.append(
            GrantPI(
                full_name=full_name,
                era_id=era_id,
                orcid=orcid,
                role=role_str,
                organization=org,
            )
        )

    org_data = data.get("organization") or {}
    org_name = org_data.get("org_name") if isinstance(org_data, dict) else None

    project_terms_raw = data.get("phr_text") or ""
    project_terms: list[str] = (
        [t.strip() for t in project_terms_raw.split(";") if t.strip()]
        if project_terms_raw
        else []
    )

    rcdc_raw = data.get("spending_categories_desc") or data.get("rcdc_categories") or ""
    if isinstance(rcdc_raw, list):
        rcdc_categories = rcdc_raw
    elif isinstance(rcdc_raw, str) and rcdc_raw:
        rcdc_categories = [c.strip() for c in rcdc_raw.split(";") if c.strip()]
    else:
        rcdc_categories = []

    award_date_str = data.get("award_notice_date")
    award_date: date | None = None
    if award_date_str:
        try:
            award_date = date.fromisoformat(award_date_str[:10])
        except (ValueError, TypeError):
            pass

    project_num = data.get("project_num") or data.get("project_number") or ""
    activity = data.get("activity_code") or ""
    if not activity and project_num:
        parts = project_num.split("-")
        if parts:
            code_part = parts[0].lstrip("0123456789")
            if len(code_part) >= 3:
                activity = code_part[:3]

    return GrantRecord(
        project_number=project_num,
        activity_code=activity,
        pis=pis,
        total_cost=data.get("award_amount"),
        fiscal_year=data.get("fiscal_year") or 0,
        project_terms=project_terms,
        rcdc_categories=rcdc_categories,
        organization_name=org_name,
        organization_ror_candidate=org_name,
        award_notice_date=award_date,
        is_active=data.get("is_active", False),
        raw_json=json.dumps(data),
    )


class ReporterClient:
    """Typed client for the NIH RePORTER v2 API."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry = retry_policy or RetryPolicy()

    async def fetch_grants_by_topic(
        self,
        rcdc_terms: list[str],
        since_fy: int | None = None,
        page_size: int = 500,
    ) -> AsyncIterator[GrantRecord]:
        """Fetch grants matching RCDC terms, paginated."""
        criteria: dict[str, Any] = {
            "spending_categories_desc": rcdc_terms,
        }
        if since_fy is not None:
            criteria["fiscal_years"] = list(range(since_fy, since_fy + 20))

        offset = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                payload: dict[str, Any] = {
                    "criteria": criteria,
                    "offset": offset,
                    "limit": page_size,
                }

                async def _do_post(p: dict[str, Any] = payload) -> httpx.Response:
                    resp = await client.post(REPORTER_API_URL, json=p)
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_post)
                body = response.json()
                results = body.get("results") or []

                if not results:
                    break

                for item in results:
                    yield _parse_grant(item)

                offset += len(results)
                meta = body.get("meta") or {}
                total = meta.get("total") or 0
                if offset >= total:
                    break

    async def fetch_grants_by_pi(
        self,
        era_id: str,
    ) -> AsyncIterator[GrantRecord]:
        """Fetch all grants for a given PI by eRA Commons ID."""
        criteria: dict[str, Any] = {
            "pi_profile_ids": [era_id],
        }

        offset = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                payload: dict[str, Any] = {
                    "criteria": criteria,
                    "offset": offset,
                    "limit": 500,
                }

                async def _do_post(p: dict[str, Any] = payload) -> httpx.Response:
                    resp = await client.post(REPORTER_API_URL, json=p)
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_post)
                body = response.json()
                results = body.get("results") or []

                if not results:
                    break

                for item in results:
                    yield _parse_grant(item)

                offset += len(results)
                meta = body.get("meta") or {}
                total = meta.get("total") or 0
                if offset >= total:
                    break
