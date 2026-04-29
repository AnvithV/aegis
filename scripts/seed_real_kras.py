"""Real data seed: KRAS-targeted cancer therapy researchers.

Pulls from every implemented free connector.  No API keys required.

Usage:
    uv run python scripts/seed_real_kras.py
    uv run python scripts/seed_real_kras.py --sources nih_reporter,pubmed,icite,ctgov
    uv run python scripts/seed_real_kras.py --list-sources

Available sources (all enabled by default):
    nih_reporter    NIH grants, US PIs
    erc             European Research Council grants
    mrc             UK Medical Research Council grants
    cihr            Canadian Institutes of Health Research grants
    kaken           Japan KAKEN grants
    pubmed          PubMed publications per researcher
    icite           iCite citation metrics (RCR per paper)
    ctgov           ClinicalTrials.gov investigator lookup
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
from collections import defaultdict
from datetime import UTC, date, datetime
from statistics import median

import httpx

from aegis.sources.cihr import CihrClient
from aegis.sources.ctgov import CTGOV_API_URL
from aegis.sources.erc import ErcClient
from aegis.sources.icite import IciteClient
from aegis.sources.jst_kaken import KakenClient
from aegis.sources.mrc import MrcClient
from aegis.sources.pubmed import PubMedClient
from aegis.storage.candidate_store import CandidateStore
from aegis.storage.schema import AffiliationSpan, ArtifactRefBundle, Candidate, MeshDescriptor

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPORTER_API = "https://api.reporter.nih.gov/v2/projects/search"
MAX_RESEARCHERS = 25
MAX_PMIDS_PER_RESEARCHER = 20

ALL_SOURCES = [
    "nih_reporter",
    "erc",
    "mrc",
    "cihr",
    "kaken",
    "pubmed",
    "icite",
    "ctgov",
]


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--sources",
        default=",".join(ALL_SOURCES),
        help="Comma-separated list of sources to enable (default: all)",
    )
    p.add_argument("--list-sources", action="store_true", help="Print available sources and exit")
    return p.parse_args()


# ── Grant source fetchers → unified PI dicts ─────────────────────────────────

async def fetch_nih_pis(http: httpx.AsyncClient) -> list[dict]:
    payload = {
        "criteria": {
            "advanced_text_search": {
                "operator": "and",
                "search_field": "all",
                "search_text": "KRAS mutation cancer therapy",
            },
            "fiscal_years": [2022, 2023, 2024],
            "is_active": True,
        },
        "offset": 0,
        "limit": 100,
        "sort_field": "award_amount",
        "sort_order": "desc",
    }
    log.info("[nih_reporter] Querying NIH Reporter…")
    try:
        resp = await http.post(REPORTER_API, json=payload, timeout=30.0)
        resp.raise_for_status()
        grants = resp.json().get("results") or []
    except Exception as exc:
        log.warning("[nih_reporter] Failed: %s", exc)
        return []

    seen: dict[str, dict] = {}
    for g in grants:
        org = (g.get("organization") or {}).get("org_name") or ""
        project_num = g.get("project_num") or ""
        award = g.get("award_amount") or 0
        for pi in (g.get("principal_investigators") or []):
            name = (pi.get("full_name") or "").strip()
            era_id = str(pi.get("profile_id") or pi.get("era_commons_id") or "")
            if not name:
                continue
            key = era_id or name
            if key not in seen or award > seen[key].get("award", 0):
                seen[key] = {
                    "full_name": name,
                    "era_id": era_id,
                    "orcid": pi.get("orcid") or None,
                    "organization": org,
                    "grant_ids": [project_num] if project_num else [],
                    "grant_sources": ["nih_reporter"],
                    "country": "US",
                    "award": award,
                }
            else:
                if project_num and project_num not in seen[key]["grant_ids"]:
                    seen[key]["grant_ids"].append(project_num)

    pis = sorted(seen.values(), key=lambda p: p["award"], reverse=True)
    log.info("[nih_reporter] %d unique PIs", len(pis))
    return pis


async def _fetch_intl_pis(
    source_name: str,
    grants_iter,
    country: str,
    limit: int = 30,
) -> list[dict]:
    """Convert any NonUsGrantRecord stream to unified PI dicts."""
    seen: dict[str, dict] = {}
    count = 0
    try:
        async for grant in grants_iter:
            for name in grant.pi_names:
                name = name.strip()
                if not name or len(name) < 4:
                    continue
                key = name.lower()
                if key not in seen:
                    orcid = None
                    if grant.pi_orcids:
                        idx = grant.pi_names.index(name) if name in grant.pi_names else -1
                        if 0 <= idx < len(grant.pi_orcids):
                            orcid = grant.pi_orcids[idx]
                    seen[key] = {
                        "full_name": name,
                        "era_id": "",
                        "orcid": orcid,
                        "organization": grant.institution or "Unknown",
                        "grant_ids": [grant.grant_reference],
                        "grant_sources": [source_name],
                        "country": country,
                        "award": grant.amount_local or 0,
                    }
                else:
                    if grant.grant_reference not in seen[key]["grant_ids"]:
                        seen[key]["grant_ids"].append(grant.grant_reference)
            count += 1
            if count >= limit:
                break
    except Exception as exc:
        log.warning("[%s] Failed: %s", source_name, exc)
    log.info("[%s] %d unique PIs", source_name, len(seen))
    return list(seen.values())


async def fetch_erc_pis() -> list[dict]:
    client = ErcClient()
    return await _fetch_intl_pis(
        "erc",
        client.fetch_grants(subject_areas=["Life Sciences"], since_year=2020),
        country="EU",
    )


async def fetch_mrc_pis() -> list[dict]:
    client = MrcClient()
    return await _fetch_intl_pis(
        "mrc",
        client.fetch_grants(search_term="KRAS cancer", since_year=2020),
        country="GB",
    )


async def fetch_cihr_pis() -> list[dict]:
    client = CihrClient()
    return await _fetch_intl_pis(
        "cihr",
        client.fetch_grants(keywords=["KRAS", "cancer"], since_year=2020),
        country="CA",
    )


async def fetch_kaken_pis() -> list[dict]:
    client = KakenClient()
    return await _fetch_intl_pis(
        "kaken",
        client.fetch_grants(keywords=["KRAS", "cancer"], since_year=2020),
        country="JP",
    )


# ── PubMed ────────────────────────────────────────────────────────────────────

def _author_query(full_name: str) -> str:
    parts = full_name.strip().split()
    if len(parts) >= 2:
        last = parts[-1]
        initials = "".join(p[0] for p in parts[:-1])
        return f'"{last} {initials}"[Author]'
    return f'"{full_name}"[Author]'


async def fetch_pmids_for_pi(
    pubmed: PubMedClient, full_name: str
) -> tuple[list[str], list[MeshDescriptor]]:
    query = f"{_author_query(full_name)} AND KRAS[Title/Abstract]"
    pmids: list[str] = []
    all_mesh: list[MeshDescriptor] = []
    try:
        async for record in pubmed.search_and_fetch(query, batch_size=MAX_PMIDS_PER_RESEARCHER):
            pmids.append(record.pmid)
            all_mesh.extend(record.mesh_descriptors)
            if len(pmids) >= MAX_PMIDS_PER_RESEARCHER:
                break
    except Exception as exc:
        log.warning("[pubmed] Error for %s: %s", full_name, exc)
    return pmids, all_mesh


# ── iCite ─────────────────────────────────────────────────────────────────────

async def fetch_rcr_scores(all_pmids: list[str]) -> dict[str, float]:
    icite = IciteClient()
    scores: dict[str, float] = {}
    try:
        async for rec in icite.fetch_by_pmids(all_pmids):
            if rec.relative_citation_ratio is not None:
                scores[rec.pmid] = rec.relative_citation_ratio
    except Exception as exc:
        log.warning("[icite] Failed: %s", exc)
    return scores


# ── ClinicalTrials.gov ────────────────────────────────────────────────────────

async def fetch_trials_for_pi(
    http: httpx.AsyncClient, last_name: str, max_trials: int = 5
) -> list[str]:
    """Search CT.gov for trials where this person appears as investigator."""
    params = {
        "query.term": f"{last_name} KRAS",
        "pageSize": max_trials,
        "format": "json",
        "fields": "NCTId,BriefTitle,OverallStatus,OverallOfficialName",
    }
    try:
        resp = await http.get(CTGOV_API_URL, params=params, timeout=15.0)
        resp.raise_for_status()
        studies = resp.json().get("studies") or []
        nct_ids = []
        for s in studies:
            protocol = s.get("protocolSection") or {}
            nct = (protocol.get("identificationModule") or {}).get("nctId")
            if nct:
                nct_ids.append(nct)
        return nct_ids
    except Exception as exc:
        log.warning("[ctgov] Error for %s: %s", last_name, exc)
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def deduplicate_pis(pis: list[dict]) -> list[dict]:
    """Merge PI dicts by lower-cased last name."""
    seen: dict[str, dict] = {}
    for pi in pis:
        parts = pi["full_name"].strip().split()
        last = parts[-1].lower() if parts else pi["full_name"].lower()
        if last not in seen:
            seen[last] = pi
        else:
            # Merge grant IDs from both records
            existing = seen[last]
            for gid in pi.get("grant_ids", []):
                if gid not in existing["grant_ids"]:
                    existing["grant_ids"].append(gid)
    return list(seen.values())


def _median_rcr(pmids: list[str], rcr_map: dict[str, float]) -> float:
    scores = [rcr_map[p] for p in pmids if p in rcr_map]
    return median(scores) if scores else 0.0


def quality_percentile(med: float, all_medians: list[float]) -> float:
    if not all_medians:
        return 0.5
    below = sum(1 for m in all_medians if m < med)
    return round(below / len(all_medians), 4)


def dedupe_mesh(descriptors: list[MeshDescriptor]) -> list[MeshDescriptor]:
    seen: dict[str, bool] = {}
    result: list[MeshDescriptor] = []
    for d in descriptors:
        key = d.descriptor.lower()
        if key not in seen:
            seen[key] = d.major_topic
            result.append(d)
        elif d.major_topic and not seen[key]:
            seen[key] = True
            result = [r if r.descriptor.lower() != key else d for r in result]
    return result[:10]


def make_uuid(pi: dict) -> str:
    raw = f"kras-{pi['era_id'] or pi['full_name']}"
    return "kras-" + hashlib.md5(raw.encode()).hexdigest()[:12]  # noqa: S324


def last_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[-1] if parts else full_name


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(sources: set[str]) -> None:
    now = datetime.now(UTC)

    # ── Phase 1: Collect PIs from all grant sources ──────────────────────────
    all_pis: list[dict] = []

    async with httpx.AsyncClient() as http:
        if "nih_reporter" in sources:
            all_pis += await fetch_nih_pis(http)

    tasks = []
    if "erc" in sources:
        tasks.append(fetch_erc_pis())
    if "mrc" in sources:
        tasks.append(fetch_mrc_pis())
    if "cihr" in sources:
        tasks.append(fetch_cihr_pis())
    if "kaken" in sources:
        tasks.append(fetch_kaken_pis())

    if tasks:
        intl_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in intl_results:
            if isinstance(r, list):
                all_pis += r
            elif isinstance(r, Exception):
                log.warning("International source failed: %s", r)

    pis = deduplicate_pis(all_pis)
    # Sort: US PIs first (by award), then international; cap total
    pis.sort(key=lambda p: (p["country"] != "US", -p["award"]))
    pis = pis[:MAX_RESEARCHERS]
    log.info("Total unique PIs after deduplication: %d", len(pis))

    # ── Phase 2: PubMed publications ─────────────────────────────────────────
    pi_pmids: dict[str, list[str]] = {}
    pi_mesh: dict[str, list[MeshDescriptor]] = {}

    if "pubmed" in sources:
        pubmed = PubMedClient()
        log.info("[pubmed] Fetching publications for %d PIs…", len(pis))
        for pi in pis:
            name = pi["full_name"]
            pmids, mesh = await fetch_pmids_for_pi(pubmed, name)
            pi_pmids[name] = pmids
            pi_mesh[name] = mesh
            log.info("  %s → %d PMIDs", name, len(pmids))
    else:
        for pi in pis:
            pi_pmids[pi["full_name"]] = []
            pi_mesh[pi["full_name"]] = []

    # ── Phase 3: iCite RCR scores ─────────────────────────────────────────────
    rcr_map: dict[str, float] = {}
    if "icite" in sources:
        all_pmids = list({p for pmids in pi_pmids.values() for p in pmids})
        log.info("[icite] Fetching RCR for %d PMIDs…", len(all_pmids))
        rcr_map = await fetch_rcr_scores(all_pmids)
        log.info("[icite] %d RCR scores retrieved", len(rcr_map))

    # ── Phase 4: ClinicalTrials.gov ───────────────────────────────────────────
    pi_nct_ids: dict[str, list[str]] = {}
    if "ctgov" in sources:
        log.info("[ctgov] Fetching trials for %d PIs…", len(pis))
        async with httpx.AsyncClient() as http:
            for pi in pis:
                nct_ids = await fetch_trials_for_pi(http, last_name(pi["full_name"]))
                pi_nct_ids[pi["full_name"]] = nct_ids
                if nct_ids:
                    log.info("  %s → %s", pi["full_name"], ", ".join(nct_ids))
    else:
        for pi in pis:
            pi_nct_ids[pi["full_name"]] = []

    # ── Phase 5: Compute quality percentiles ──────────────────────────────────
    medians = {pi["full_name"]: _median_rcr(pi_pmids[pi["full_name"]], rcr_map) for pi in pis}
    all_medians = list(medians.values())

    # ── Phase 6: Clear DB and seed ────────────────────────────────────────────
    store = CandidateStore("aegis.duckdb")
    store._conn.execute("DELETE FROM strong_keys")
    store._conn.execute("DELETE FROM artifact_refs")
    store._conn.execute("DELETE FROM affiliation_history")
    store._conn.execute("DELETE FROM candidates")
    log.info("Cleared existing candidates")

    print(f"\n{'Name':<32} {'Org':<35} {'Pubs':>4} {'RCR':>5} {'Trials':>6} {'Src'}")
    print("-" * 90)

    for pi in pis:
        name = pi["full_name"]
        pmids = pi_pmids[name]
        nct_ids = pi_nct_ids[name]
        mesh_raw = pi_mesh[name]
        med = medians[name]
        q_pct = quality_percentile(med, all_medians)

        uuid = make_uuid(pi)
        strong_keys: dict[str, str] = {}
        if pi.get("era_id"):
            strong_keys["era_commons"] = pi["era_id"]
        if pi.get("orcid"):
            strong_keys["orcid"] = pi["orcid"]

        org = pi["organization"] or "Unknown Institution"
        n_grants = len(pi["grant_ids"])
        rcr_top = sum(1 for p in pmids if rcr_map.get(p, 0.0) > 2.0)
        grant_src = ", ".join(set(pi.get("grant_sources", ["unknown"])))

        # Evidence trail — tagged with source
        evidence_trail = []
        if pmids:
            evidence_trail.append(
                f"{len(pmids)} KRAS publications in PubMed"
                + (f" (median RCR {med:.2f}, {rcr_top} papers >2× field avg)" if med > 0 else "")
            )
        if pi["grant_ids"]:
            evidence_trail.append(
                f"{n_grants} grant{'s' if n_grants > 1 else ''} [{grant_src}]: "
                + ", ".join(pi["grant_ids"][:3])
            )
        if nct_ids:
            evidence_trail.append(
                f"Investigator on {len(nct_ids)} KRAS-related clinical trial{'s' if len(nct_ids) > 1 else ''}: "
                + ", ".join(nct_ids[:3])
            )
        if not evidence_trail:
            evidence_trail = [f"NIH-funded researcher at {org}"]

        candidate = Candidate(
            uuid=uuid,
            strong_keys=strong_keys,
            name_variants=[name],
            affiliations=[
                AffiliationSpan(
                    ror_id=None,
                    canonical_name=org,
                    raw_string=org,
                    country=pi["country"],
                    confidence=0.90,
                    start_date=date(2020, 1, 1),
                    end_date=None,
                )
            ],
            artifact_refs=ArtifactRefBundle(
                pmids=pmids,
                nct_ids=nct_ids,
                grant_ids=pi["grant_ids"],
                patent_ids=[],
            ),
            linkage_confidence=0.93 if pi.get("era_id") else 0.78,
            evidence_trail=evidence_trail,
            last_updated_per_source={
                "pubmed": now,
                "reporter": now,
                **({"ctgov": now} if nct_ids else {}),
            },
            mesh_descriptors=dedupe_mesh(mesh_raw),
        )
        store.upsert(candidate)

        # Store per-pmid RCR as extended artifact metadata (best-effort)
        for pmid in pmids[:5]:
            rcr = rcr_map.get(pmid)
            if rcr is not None:
                try:
                    store._conn.execute(
                        """
                        INSERT OR REPLACE INTO artifact_refs
                            (artifact_type, artifact_id, candidate_uuid)
                        VALUES ('pmid_rcr', ?, ?)
                        """,
                        [f"{pmid}:rcr={rcr:.3f}", uuid],
                    )
                except Exception:
                    pass  # Non-critical; table schema may not have this column

        print(
            f"  {name:<30} {org[:33]:<35} {len(pmids):>4} {med:>5.2f} "
            f"{len(nct_ids):>6}   {grant_src}"
        )

    total = store.count()
    store.close()

    print(f"\nDone. {total} researchers seeded from: {', '.join(sorted(sources))}")
    print("\nSuggested demo queries:")
    print("  • 'KRAS inhibitor drug discovery for lung cancer'")
    print("  • 'RAS oncogene translational research pancreatic cancer'")
    print("  • 'KRAS G12C mutation clinical trials investigator'")


def run() -> None:
    args = parse_args()
    if args.list_sources:
        print("Available sources:")
        for s in ALL_SOURCES:
            print(f"  {s}")
        return
    requested = {s.strip() for s in args.sources.split(",") if s.strip()}
    unknown = requested - set(ALL_SOURCES)
    if unknown:
        print(f"Unknown sources: {unknown}. Use --list-sources to see available options.")
        raise SystemExit(1)
    asyncio.run(main(requested))


if __name__ == "__main__":
    run()
