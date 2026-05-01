"""ClinicalTrials.gov v2 REST/JSON API client."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import date
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict

from aegis.sources.retry import RetryPolicy

logger = logging.getLogger(__name__)

CTGOV_API_URL = "https://clinicaltrials.gov/api/v2/studies"


class InvestigatorRole(BaseModel):
    """An investigator on a clinical trial."""

    model_config = ConfigDict(frozen=True)

    full_name: str
    role: Literal["PI", "Sub-I", "Study Chair"]
    affiliation: str | None = None
    site: str | None = None


class StudyRecord(BaseModel):
    """A single study record from ClinicalTrials.gov."""

    model_config = ConfigDict(frozen=True)

    nct_id: str
    title: str
    conditions_mesh: list[str]
    conditions_freetext: list[str]
    interventions: list[str]
    phase: str | None = None
    study_type: str | None = None
    sponsor: str | None = None
    investigators: list[InvestigatorRole]
    status: str
    status_history: list[dict[str, str]]
    randomization: str | None = None
    masking: str | None = None
    last_update_post_date: date | None = None
    raw_json: str


_ROLE_MAP: dict[str, Literal["PI", "Sub-I", "Study Chair"]] = {
    "PRINCIPAL_INVESTIGATOR": "PI",
    "SUB_INVESTIGATOR": "Sub-I",
    "STUDY_CHAIR": "Study Chair",
    "STUDY_DIRECTOR": "Study Chair",
    "PI": "PI",
    "Sub-I": "Sub-I",
    "Study Chair": "Study Chair",
}


def _parse_study(data: dict[str, Any]) -> StudyRecord:
    """Parse a single study from the CT.gov v2 API response."""
    protocol = data.get("protocolSection") or {}
    id_module = protocol.get("identificationModule") or {}
    status_module = protocol.get("statusModule") or {}
    design_module = protocol.get("designModule") or {}
    sponsor_module = protocol.get("sponsorCollaboratorsModule") or {}
    conditions_module = protocol.get("conditionsModule") or {}
    interventions_module = protocol.get("armsInterventionsModule") or {}
    contacts_module = protocol.get("contactsLocationsModule") or {}

    # Derived annotations (e.g., MeSH terms)
    derived = data.get("derivedSection") or {}
    condition_browse = derived.get("conditionBrowseModule") or {}

    nct_id = id_module.get("nctId") or ""
    title = id_module.get("briefTitle") or ""

    # Conditions: MeSH from derived section, freetext from conditions module
    mesh_list = condition_browse.get("meshes") or []
    conditions_mesh = [m.get("term", "") for m in mesh_list if m.get("term")]

    conditions_freetext = conditions_module.get("conditions") or []

    # Interventions
    intervention_list = interventions_module.get("interventions") or []
    interventions = [
        i.get("name", "") for i in intervention_list if i.get("name")
    ]

    # Phase
    phases = design_module.get("phases") or []
    phase = phases[0] if phases else None

    study_type = design_module.get("studyType") or None

    # Sponsor
    lead_sponsor = sponsor_module.get("leadSponsor") or {}
    sponsor = lead_sponsor.get("name") or None

    # Investigators
    investigators: list[InvestigatorRole] = []

    # From overall officials
    officials = contacts_module.get("overallOfficials") or []
    for official in officials:
        name = official.get("name") or ""
        raw_role = official.get("role") or ""
        mapped = _ROLE_MAP.get(raw_role, "PI")
        affiliation = official.get("affiliation") or None
        investigators.append(
            InvestigatorRole(
                full_name=name,
                role=mapped,
                affiliation=affiliation,
                site=None,
            )
        )

    # From locations (site-level investigators)
    locations = contacts_module.get("locations") or []
    for loc in locations:
        site_name = loc.get("facility") or None
        site_contacts = loc.get("contacts") or []
        for contact in site_contacts:
            name = contact.get("name") or ""
            raw_role = contact.get("role") or ""
            if raw_role not in _ROLE_MAP:
                continue
            mapped = _ROLE_MAP[raw_role]
            investigators.append(
                InvestigatorRole(
                    full_name=name,
                    role=mapped,
                    affiliation=None,
                    site=site_name,
                )
            )

    # Status
    overall_status = status_module.get("overallStatus") or ""

    # Status history
    status_history: list[dict[str, str]] = []
    status_changes = status_module.get("statusVerifiedDate")
    if status_changes:
        status_history.append(
            {"status": overall_status, "date": status_changes}
        )
    start_date_struct = status_module.get("startDateStruct") or {}
    start_date_str = start_date_struct.get("date")
    if start_date_str:
        status_history.insert(
            0, {"status": "Started", "date": start_date_str}
        )

    # Design info
    design_info = design_module.get("designInfo") or {}
    randomization = design_info.get("allocation") or None
    masking_info = design_info.get("maskingInfo") or {}
    masking = masking_info.get("masking") or None

    # Last update
    last_update_struct = status_module.get(
        "lastUpdatePostDateStruct"
    ) or {}
    last_update_str = last_update_struct.get("date")
    last_update_date: date | None = None
    if last_update_str:
        try:
            last_update_date = date.fromisoformat(last_update_str[:10])
        except (ValueError, TypeError):
            pass

    return StudyRecord(
        nct_id=nct_id,
        title=title,
        conditions_mesh=conditions_mesh,
        conditions_freetext=conditions_freetext,
        interventions=interventions,
        phase=phase,
        study_type=study_type,
        sponsor=sponsor,
        investigators=investigators,
        status=overall_status,
        status_history=status_history,
        randomization=randomization,
        masking=masking,
        last_update_post_date=last_update_date,
        raw_json=json.dumps(data),
    )


class CtgovClient:
    """Typed client for the ClinicalTrials.gov v2 API."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self._retry = retry_policy or RetryPolicy()

    async def _paginate(
        self,
        params: dict[str, str | int],
        page_size: int = 100,
    ) -> AsyncIterator[StudyRecord]:
        """Shared pagination loop for CT.gov API calls."""
        params = {**params, "pageSize": page_size, "format": "json"}
        page_token: str | None = None
        seen: set[str] = set()

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                if page_token:
                    params["pageToken"] = page_token

                async def _do_get(
                    p: dict[str, str | int] = params,
                ) -> httpx.Response:
                    resp = await client.get(CTGOV_API_URL, params=p)
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_get)
                body = response.json()
                studies = body.get("studies") or []

                if not studies:
                    break

                for study_data in studies:
                    record = _parse_study(study_data)
                    if record.nct_id not in seen:
                        seen.add(record.nct_id)
                        yield record

                page_token = body.get("nextPageToken")
                if not page_token:
                    break

    async def fetch_studies_by_text(
        self,
        query_text: str,
        page_size: int = 100,
    ) -> AsyncIterator[StudyRecord]:
        """Full-text search across all CT.gov fields (title, conditions,
        interventions, description).  Use this for free-form queries such as
        'KRAS inhibitor lung cancer' — it finds trials that mention the topic
        in *any* field, not just the condition name."""
        async for record in self._paginate(
            {"query.term": query_text}, page_size=page_size
        ):
            yield record

    async def fetch_studies_by_condition(
        self,
        mesh_terms: list[str],
        page_size: int = 100,
    ) -> AsyncIterator[StudyRecord]:
        """Fetch studies matching MeSH condition terms (query.cond field).
        Kept for backwards compatibility; prefer fetch_studies_by_text for
        free-form topic queries."""
        async for record in self._paginate(
            {"query.cond": " OR ".join(mesh_terms)}, page_size=page_size
        ):
            yield record
