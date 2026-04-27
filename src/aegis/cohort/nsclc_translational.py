"""NSCLC translational seed-cohort builder with co-author expansion."""

from __future__ import annotations

import uuid as _uuid
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import Candidate


class SeedSource(StrEnum):
    """How a candidate was introduced into the seed pool."""

    pubmed_last_author = "pubmed_last_author"
    nih_contact_pi = "nih_contact_pi"
    ctgov_pi = "ctgov_pi"


_NSCLC_MESH = "Carcinoma, Non-Small-Cell Lung"

# Organisation keywords that indicate industry affiliation.
_INDUSTRY_KEYWORDS = frozenset(
    {
        "pharma",
        "inc",
        "inc.",
        "corp",
        "corp.",
        "ltd",
        "ltd.",
        "gmbh",
        "therapeutics",
        "biosciences",
        "biotech",
        "oncology inc",
        "laboratories",
    }
)


class CohortConfig(BaseModel):
    """Configuration for the NSCLC translational cohort builder."""

    model_config = ConfigDict(frozen=True)

    mesh_terms: list[str] = Field(
        default_factory=lambda: [_NSCLC_MESH]
    )
    lookback_years: int = 10
    max_coauthor_fanout: int = 50
    expansion_hops: int = 2
    target_min: int = 3500
    target_max: int = 6000


class Cohort(BaseModel):
    """Result of a cohort build run."""

    model_config = ConfigDict(frozen=True)

    cohort_id: str
    name: str
    candidates: list[str]
    provenance: dict[str, list[str]]
    seed_count: int
    expanded_count: int
    created_at: datetime
    industry_flagged: list[str] = Field(default_factory=list)


def _has_nsclc_mesh(candidate: Candidate, mesh_terms: list[str]) -> bool:
    """Check if candidate has any matching MeSH descriptor."""
    mesh_lower = {m.lower() for m in mesh_terms}
    return any(
        d.descriptor.lower() in mesh_lower
        for d in candidate.mesh_descriptors
    )


def _is_last_author_on_pmid(candidate: Candidate) -> bool:
    """Return True if candidate has PubMed artifact refs (proxy for authorship)."""
    return len(candidate.artifact_refs.pmids) > 0


def _is_nih_contact_pi(candidate: Candidate) -> bool:
    """Return True if candidate has NIH grant artifact refs."""
    return len(candidate.artifact_refs.grant_ids) > 0


def _is_ctgov_pi(candidate: Candidate) -> bool:
    """Return True if candidate has CT.gov trial artifact refs."""
    return len(candidate.artifact_refs.nct_ids) > 0


def _is_industry(candidate: Candidate) -> bool:
    """Flag candidates whose primary affiliation looks non-academic."""
    if not candidate.affiliations:
        return False
    primary = candidate.affiliations[-1]
    raw_lower = primary.raw_string.lower()
    canonical_lower = primary.canonical_name.lower()
    for kw in _INDUSTRY_KEYWORDS:
        if kw in raw_lower or kw in canonical_lower:
            return True
    return False


def _get_coauthor_uuids(
    candidate: Candidate,
    all_candidates: list[Candidate],
    max_fanout: int,
) -> list[str]:
    """Find co-authors by shared PubMed artifact refs (PMID overlap)."""
    if not candidate.artifact_refs.pmids:
        return []
    candidate_pmids = set(candidate.artifact_refs.pmids)
    coauthors: list[str] = []
    for other in all_candidates:
        if other.uuid == candidate.uuid:
            continue
        if set(other.artifact_refs.pmids) & candidate_pmids:
            coauthors.append(other.uuid)
            if len(coauthors) >= max_fanout:
                break
    return coauthors


def build_nsclc_translational_cohort(
    store: CandidateStore,
    config: CohortConfig | None = None,
) -> Cohort:
    """Build an NSCLC translational seed cohort from a CandidateStore.

    1. **Seed phase** — identify PIs matching NSCLC criteria from three
       sources (PubMed last-author, NIH contact PI, CT.gov PI).
    2. **Expansion phase** — BFS over the co-author graph for
       ``config.expansion_hops`` hops, capping per-PI fan-out.
    3. **Industry flagging** — flag non-academic affiliations.
    """
    if config is None:
        config = CohortConfig()

    all_candidates = store.list_by_cohort()
    uuid_to_candidate: dict[str, Candidate] = {
        c.uuid: c for c in all_candidates
    }

    # --- Seed phase ---
    provenance: dict[str, list[str]] = defaultdict(list)
    seed_uuids: set[str] = set()

    for c in all_candidates:
        if not _has_nsclc_mesh(c, config.mesh_terms):
            continue

        if _is_last_author_on_pmid(c):
            seed_uuids.add(c.uuid)
            provenance[c.uuid].append(SeedSource.pubmed_last_author)

        if _is_nih_contact_pi(c):
            seed_uuids.add(c.uuid)
            provenance[c.uuid].append(SeedSource.nih_contact_pi)

        if _is_ctgov_pi(c):
            seed_uuids.add(c.uuid)
            provenance[c.uuid].append(SeedSource.ctgov_pi)

    seed_count = len(seed_uuids)

    # --- Expansion phase (BFS) ---
    visited: set[str] = set(seed_uuids)
    frontier = list(seed_uuids)

    for _hop in range(config.expansion_hops):
        next_frontier: list[str] = []
        for uid in frontier:
            candidate = uuid_to_candidate.get(uid)
            if candidate is None:
                continue
            coauthor_uuids = _get_coauthor_uuids(
                candidate,
                all_candidates,
                config.max_coauthor_fanout,
            )
            for co_uid in coauthor_uuids:
                if co_uid not in visited:
                    visited.add(co_uid)
                    next_frontier.append(co_uid)
                    # Inherit provenance from the seed that introduced them
                    if co_uid not in provenance:
                        provenance[co_uid] = list(
                            provenance.get(uid, [])
                        )
        frontier = next_frontier

    # Ensure every visited candidate has a provenance entry
    for uid in visited:
        if uid not in provenance:
            provenance[uid] = []

    # --- Industry flagging ---
    industry_flagged: list[str] = []
    for uid in visited:
        candidate = uuid_to_candidate.get(uid)
        if candidate is not None and _is_industry(candidate):
            industry_flagged.append(uid)

    sorted_candidates = sorted(visited)

    return Cohort(
        cohort_id=str(_uuid.uuid4()),
        name="nsclc_translational_v1",
        candidates=sorted_candidates,
        provenance=dict(provenance),
        seed_count=seed_count,
        expanded_count=len(sorted_candidates),
        created_at=datetime.now(UTC),
        industry_flagged=industry_flagged,
    )
