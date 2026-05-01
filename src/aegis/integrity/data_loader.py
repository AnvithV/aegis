"""Auto-download and cache integrity data at startup."""

from __future__ import annotations

import csv
import io
import json
import logging
import time
from datetime import date
from pathlib import Path

import httpx

from aegis.sources.leie import LEIERecord, LEIEStore
from aegis.sources.ofac_sam import OFACSAMRecord, OFACSAMStore
from aegis.sources.ori import ORIStore
from aegis.sources.retraction_watch import RetractionRecord, RetractionWatchStore

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("data/integrity")
_CACHE_MAX_AGE_DAYS = 30


def _cache_is_fresh(path: Path) -> bool:
    """Return True if cache file exists and is less than 30 days old."""
    if not path.exists():
        return False
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds < _CACHE_MAX_AGE_DAYS * 86400


def _download_leie(cache_dir: Path) -> list[LEIERecord]:
    """Download and parse the LEIE exclusion CSV."""
    cache_path = cache_dir / "leie.csv"
    try:
        if not _cache_is_fresh(cache_path):
            logger.info("Downloading LEIE exclusion list...")
            resp = httpx.get(
                "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv",
                timeout=60.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            cache_path.write_bytes(resp.content)
            logger.info("LEIE data cached to %s", cache_path)
        else:
            logger.info("Using cached LEIE data from %s", cache_path)

        text = cache_path.read_text(encoding="utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        records: list[LEIERecord] = []
        for row in reader:
            excl_date: date | None = None
            rein_date: date | None = None
            try:
                if row.get("EXCLDATE"):
                    excl_date = date.fromisoformat(row["EXCLDATE"][:10])
            except (ValueError, TypeError):
                pass
            try:
                if row.get("REINDATE"):
                    rein_date = date.fromisoformat(row["REINDATE"][:10])
            except (ValueError, TypeError):
                pass

            records.append(
                LEIERecord(
                    last_name=row.get("LASTNAME", ""),
                    first_name=row.get("FIRSTNAME", ""),
                    npi=row.get("NPI") or None,
                    exclusion_type=row.get("EXCLTYPE") or None,
                    exclusion_date=excl_date,
                    reinstate_date=rein_date,
                    state=row.get("STATE") or None,
                    specialty=row.get("SPECIALTY") or None,
                )
            )
        logger.info("Loaded %d LEIE records", len(records))
        return records
    except Exception:
        logger.warning("Failed to load LEIE data", exc_info=True)
        return []


def _download_ofac(cache_dir: Path) -> list[OFACSAMRecord]:
    """Download and parse the OFAC SDN CSV."""
    cache_path = cache_dir / "ofac_sdn.csv"
    try:
        if not _cache_is_fresh(cache_path):
            logger.info("Downloading OFAC SDN list...")
            resp = httpx.get(
                "https://www.treasury.gov/ofac/downloads/sdn.csv",
                timeout=60.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            cache_path.write_bytes(resp.content)
            logger.info("OFAC data cached to %s", cache_path)
        else:
            logger.info("Using cached OFAC data from %s", cache_path)

        text = cache_path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        records: list[OFACSAMRecord] = []
        for row in reader:
            if len(row) < 3:
                continue
            primary_name = row[1].strip() if len(row) > 1 else ""
            if not primary_name or primary_name == "-0-":
                continue
            record_type = row[2].strip() if len(row) > 2 else None
            program = row[3].strip() if len(row) > 3 else None
            remarks = row[4].strip() if len(row) > 4 else None
            records.append(
                OFACSAMRecord(
                    primary_name=primary_name,
                    aliases=[],
                    source="OFAC",
                    record_type=record_type,
                    program=program,
                    remarks=remarks,
                )
            )
        logger.info("Loaded %d OFAC records", len(records))
        return records
    except Exception:
        logger.warning("Failed to load OFAC data", exc_info=True)
        return []


def _download_ori(cache_dir: Path) -> list:  # noqa: ARG001
    """ORI has no public CSV download. Return empty list."""
    logger.warning(
        "ORI misconduct data has no public CSV endpoint; "
        "returning empty list. Populate manually if needed."
    )
    return []


def _download_retraction_watch(cache_dir: Path) -> list[RetractionRecord]:
    """Fetch recent retractions from CrossRef API and cache."""
    cache_path = cache_dir / "retractions.json"
    try:
        if not _cache_is_fresh(cache_path):
            logger.info("Downloading retraction data from CrossRef...")
            resp = httpx.get(
                "https://api.crossref.org/works",
                params={"filter": "type:retraction", "rows": "1000"},
                timeout=120.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            cache_path.write_text(resp.text, encoding="utf-8")
            logger.info("Retraction data cached to %s", cache_path)
        else:
            logger.info("Using cached retraction data from %s", cache_path)

        data = json.loads(cache_path.read_text(encoding="utf-8"))
        items = data.get("message", {}).get("items", [])
        records: list[RetractionRecord] = []
        for item in items:
            title_parts = item.get("title", [])
            title = title_parts[0] if title_parts else ""
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in item.get("author", [])
            ]
            doi = item.get("DOI")
            journal_parts = item.get("container-title", [])
            journal = journal_parts[0] if journal_parts else None

            retraction_date: date | None = None
            date_parts = item.get("issued", {}).get("date-parts", [[]])
            if date_parts and date_parts[0] and len(date_parts[0]) >= 3:
                try:
                    retraction_date = date(
                        date_parts[0][0], date_parts[0][1], date_parts[0][2]
                    )
                except (ValueError, TypeError):
                    pass

            records.append(
                RetractionRecord(
                    title=title,
                    authors=authors,
                    pmid=None,
                    doi=doi,
                    journal=journal,
                    retraction_date=retraction_date,
                    reason=None,
                    original_paper_date=None,
                )
            )
        logger.info("Loaded %d retraction records", len(records))
        return records
    except Exception:
        logger.warning("Failed to load retraction data", exc_info=True)
        return []


def load_integrity_stores(
    cache_dir: Path | None = None,
) -> tuple[LEIEStore, OFACSAMStore, ORIStore, RetractionWatchStore]:
    """Load all integrity stores, downloading data as needed.

    Returns (leie_store, ofac_sam_store, ori_store, retraction_store).
    """
    cd = cache_dir or _CACHE_DIR
    cd.mkdir(parents=True, exist_ok=True)

    leie_store = LEIEStore()
    leie_records = _download_leie(cd)
    if leie_records:
        leie_store.add_batch(leie_records)

    ofac_store = OFACSAMStore()
    ofac_records = _download_ofac(cd)
    if ofac_records:
        ofac_store.add_batch(ofac_records)

    ori_store = ORIStore()
    ori_records = _download_ori(cd)
    if ori_records:
        ori_store.add_batch(ori_records)

    retraction_store = RetractionWatchStore()
    retraction_records = _download_retraction_watch(cd)
    if retraction_records:
        retraction_store.add_batch(retraction_records)

    logger.info(
        "Integrity stores loaded: LEIE=%d, OFAC=%d, ORI=%d, Retractions=%d",
        leie_store.count(),
        ofac_store.count(),
        ori_store.count(),
        retraction_store.count(),
    )
    return leie_store, ofac_store, ori_store, retraction_store
