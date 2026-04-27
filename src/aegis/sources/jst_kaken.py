"""JST/KAKEN (Japan) grant client with Japanese name transliteration."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.non_us_grants import NonUsGrantRecord
from aegis.sources.retry import RetryPolicy

logger = logging.getLogger(__name__)

KAKEN_API_URL = "https://kaken.nii.ac.jp/api/v1"
CINII_API_URL = "https://cir.nii.ac.jp/api/v1"


class KakenResearcher(BaseModel):
    """Researcher profile from KAKEN with Japanese name variants."""

    model_config = ConfigDict(frozen=True)

    researcher_number: str
    name_ja: str | None = None
    name_en: str | None = None
    name_kana: str | None = None
    name_romaji: str | None = None
    affiliation_ja: str | None = None
    affiliation_en: str | None = None
    orcid: str | None = None


def transliterate_japanese_name(name_ja: str) -> str:
    """Transliterate a Japanese name to romaji using Hepburn romanization.

    Falls back to the original string if cutlet is unavailable or fails.
    """
    try:
        import cutlet  # type: ignore[import-untyped]

        katsu = cutlet.Cutlet()
        result: str = str(katsu.romaji(name_ja))
        return result
    except Exception:  # noqa: BLE001
        return name_ja


def build_name_variants(researcher: KakenResearcher) -> list[str]:
    """Collect all non-None name forms into a deduplicated list.

    Suitable for populating Candidate.name_variants.
    """
    variants: list[str] = []
    seen: set[str] = set()
    for name in [
        researcher.name_ja,
        researcher.name_en,
        researcher.name_kana,
        researcher.name_romaji,
    ]:
        if name and name not in seen:
            variants.append(name)
            seen.add(name)
    return variants


class KakenClient:
    """Typed client for JST/KAKEN grant data."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry = retry_policy or RetryPolicy()

    async def fetch_grants(
        self,
        keywords: list[str] | None = None,
        since_year: int | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Fetch KAKEN grants, paginated."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            offset = 0
            while True:
                params: dict[str, Any] = {
                    "offset": offset,
                    "limit": batch_size,
                    "format": "json",
                }
                if keywords:
                    params["q"] = " ".join(keywords)
                if since_year is not None:
                    params["from"] = since_year

                async def _do_get(
                    p: dict[str, Any] = params,
                ) -> httpx.Response:
                    resp = await client.get(
                        f"{KAKEN_API_URL}/grants",
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
                    parsed = self._parse_kaken_grant(item)
                    if parsed is not None:
                        yield parsed

                offset += len(results)
                total = body.get("total") or 0
                if offset >= total:
                    break

    async def fetch_grants_by_researcher(
        self,
        researcher_number: str,
    ) -> AsyncIterator[NonUsGrantRecord]:
        """Fetch grants by KAKEN researcher number."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {
                "researcher": researcher_number,
                "format": "json",
                "limit": 100,
            }

            async def _do_get(
                p: dict[str, Any] = params,
            ) -> httpx.Response:
                resp = await client.get(
                    f"{KAKEN_API_URL}/grants",
                    params=p,
                )
                resp.raise_for_status()
                return resp

            response = await self._retry.execute(_do_get)
            body = response.json()
            results = body.get("results") or []

            for item in results:
                parsed = self._parse_kaken_grant(item)
                if parsed is not None:
                    yield parsed

    async def fetch_researcher(
        self,
        researcher_number: str,
    ) -> KakenResearcher | None:
        """Fetch a researcher profile and auto-transliterate Japanese name."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params: dict[str, Any] = {
                "id": researcher_number,
                "format": "json",
            }

            async def _do_get(
                p: dict[str, Any] = params,
            ) -> httpx.Response:
                resp = await client.get(
                    f"{KAKEN_API_URL}/researchers",
                    params=p,
                )
                resp.raise_for_status()
                return resp

            response = await self._retry.execute(_do_get)
            body = response.json()
            data = body.get("result") or body
            return self._parse_researcher(data)

    @staticmethod
    def _parse_kaken_grant(data: dict[str, Any]) -> NonUsGrantRecord | None:
        """Parse a KAKEN API response into a NonUsGrantRecord."""
        grant_number = data.get("grantNumber") or data.get("id")
        if not grant_number:
            return None

        # Title: prefer English, fall back to Japanese
        title = data.get("title_en") or data.get("title_ja") or data.get("title") or ""

        # PI names (both ja and en)
        pi_names: list[str] = []
        pi_orcids: list[str | None] = []
        investigators = data.get("investigators") or data.get("pis") or []
        if isinstance(investigators, list):
            for inv in investigators:
                if isinstance(inv, dict):
                    name = (
                        inv.get("name_en")
                        or inv.get("name_ja")
                        or inv.get("name")
                        or ""
                    )
                    if name:
                        pi_names.append(name)
                        pi_orcids.append(inv.get("orcid"))
                elif isinstance(inv, str):
                    pi_names.append(inv)
                    pi_orcids.append(None)
        elif isinstance(investigators, str):
            pi_names.append(investigators)
            pi_orcids.append(None)

        # Institution
        institution = (
            data.get("institution_en")
            or data.get("institution_ja")
            or data.get("institution")
        )
        if isinstance(institution, dict):
            institution = (
                institution.get("name_en")
                or institution.get("name_ja")
                or institution.get("name")
            )

        # Amount (JPY)
        amount: float | None = None
        val = data.get("totalAmount") or data.get("amount")
        if val is not None:
            try:
                amount = float(val)
            except (ValueError, TypeError):
                pass

        # Dates from fiscal year
        start_date: date | None = None
        end_date: date | None = None
        sd_str = data.get("startDate") or data.get("startFiscalYear")
        ed_str = data.get("endDate") or data.get("endFiscalYear")
        if sd_str:
            try:
                if len(str(sd_str)) == 4:
                    start_date = date(int(sd_str), 4, 1)
                else:
                    start_date = date.fromisoformat(str(sd_str)[:10])
            except (ValueError, TypeError):
                pass
        if ed_str:
            try:
                if len(str(ed_str)) == 4:
                    end_date = date(int(ed_str), 3, 31)
                else:
                    end_date = date.fromisoformat(str(ed_str)[:10])
            except (ValueError, TypeError):
                pass

        # Research category as subject areas
        categories = data.get("researchCategory") or data.get("subjects") or []
        subject_areas: list[str] = []
        if isinstance(categories, list):
            for cat in categories:
                if isinstance(cat, dict):
                    name = (
                        cat.get("name_en")
                        or cat.get("name_ja")
                        or cat.get("name")
                        or ""
                    )
                    if name:
                        subject_areas.append(name)
                elif isinstance(cat, str):
                    subject_areas.append(cat)
        elif isinstance(categories, str):
            subject_areas.append(categories)

        return NonUsGrantRecord(
            grant_reference=str(grant_number),
            funder="KAKEN",
            funder_country="JP",
            title=title,
            abstract=(
                data.get("abstract_en")
                or data.get("abstract_ja")
                or data.get("abstract")
            ),
            pi_names=pi_names,
            pi_orcids=pi_orcids,
            institution=str(institution) if institution else None,
            institution_country="JP",
            amount_local=amount,
            currency="JPY",
            start_date=start_date,
            end_date=end_date,
            subject_areas=subject_areas,
            source="kaken",
            coverage_caveat=None,
            raw_json=json.dumps(data, ensure_ascii=False),
        )

    @staticmethod
    def _parse_researcher(data: dict[str, Any]) -> KakenResearcher | None:
        """Parse researcher profile data into a KakenResearcher model."""
        researcher_number = data.get("researcherNumber") or data.get("id")
        if not researcher_number:
            return None

        name_ja = data.get("name_ja") or data.get("nameJa")
        name_romaji: str | None = None
        if name_ja:
            name_romaji = transliterate_japanese_name(name_ja)

        return KakenResearcher(
            researcher_number=str(researcher_number),
            name_ja=name_ja,
            name_en=data.get("name_en") or data.get("nameEn"),
            name_kana=data.get("name_kana") or data.get("nameKana"),
            name_romaji=name_romaji,
            affiliation_ja=data.get("affiliation_ja") or data.get("affiliationJa"),
            affiliation_en=data.get("affiliation_en") or data.get("affiliationEn"),
            orcid=data.get("orcid"),
        )
