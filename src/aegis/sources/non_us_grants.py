"""Shared data model for non-US grant records and region-mapping utilities."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from aegis.storage.schema import AffiliationSpan


class Region(StrEnum):
    """Geographic region classification."""

    US = "US"
    EU = "EU"
    UK = "UK"
    CANADA = "CANADA"
    JAPAN = "JAPAN"
    CHINA = "CHINA"
    REST_OF_WORLD = "REST_OF_WORLD"


# EU member states (ISO 3166-1 alpha-2)
_EU_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})

COUNTRY_TO_REGION: dict[str, Region] = {
    "US": Region.US,
    "GB": Region.UK,
    "CA": Region.CANADA,
    "JP": Region.JAPAN,
    "CN": Region.CHINA,
    **{code: Region.EU for code in _EU_COUNTRIES},
}


def country_to_region(country_code: str | None) -> Region:
    """Map an ISO alpha-2 country code to a Region.

    Returns Region.REST_OF_WORLD for None or unknown codes.
    """
    if country_code is None:
        return Region.REST_OF_WORLD
    return COUNTRY_TO_REGION.get(country_code, Region.REST_OF_WORLD)


def candidate_region(affiliations: list[AffiliationSpan]) -> Region:
    """Derive region from a candidate's affiliation history.

    Uses the most recent affiliation's country field (by end_date, or latest
    in list if no dates are set).
    """
    if not affiliations:
        return Region.REST_OF_WORLD

    # Sort by end_date descending; None end_date treated as most recent
    dated = [(a, a.end_date) for a in affiliations]
    dated.sort(key=lambda x: (x[1] is not None, x[1] if x[1] is not None else date.min))

    # The last entry after sorting is the most recent
    most_recent = dated[-1][0]
    return country_to_region(most_recent.country)


class NonUsGrantRecord(BaseModel):
    """A non-US grant record shared across all non-US grant source clients."""

    model_config = ConfigDict(frozen=True)

    grant_reference: str
    funder: str
    funder_country: str
    title: str
    abstract: str | None = None
    pi_names: list[str]
    pi_orcids: list[str | None]
    institution: str | None = None
    institution_country: str | None = None
    amount_local: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    subject_areas: list[str]
    source: str
    coverage_caveat: str | None = None
    raw_json: str
