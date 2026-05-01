# Plan: Aegis Ingestion Pipeline Overhaul

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-ingestion-pipeline-overhaul.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Comprehensive overhaul of the Aegis ingestion pipeline to fix scoring bias, dead features, and missing F-score components. The pipeline currently produces PubMed-dominated results because: (1) `list_by_cohort(None)` returns ALL candidates ever ingested from all past queries rather than filtering to the current query's candidate set, and (2) Reporter grant evidence trails lack `project_title`, causing `topical_fit = 0` which zeros out the entire score via the beta exponent. Additionally, F1 lacks iCite RCR enrichment, F2 misses international grants, F3 only credits CT.gov PIs, F4 has no apex roster data, F5 has no patent data, F7 is never computed, and the integrity gate is completely bypassed (hardcoded `is_zero=False`). This plan also removes ~30 unused source files to reduce codebase noise, wires the query type override from frontend to backend, and removes the no-op background refresh task.

## Objective

When this plan is complete:
1. Query results reflect only candidates discovered in the current query (not accumulated across all past queries)
2. All 7 F-scores (F1-F7) are computed using real data from live sources
3. The integrity hard gate evaluates every candidate against LEIE, OFAC/SAM, ORI, and Retraction Watch data
4. USPTO patent search is wired as a 5th parallel source
5. iCite RCR enrichment runs as a sequential step after parallel fetch
6. Frontend query type override is passed through to the backend
7. ~30 unused source files and their tests are removed
8. The no-op background refresh task is removed from server.py

## Problem Statement

The Aegis pipeline has two critical ranking bugs and six incomplete F-score computations that cause it to produce biased, inaccurate results:

**Critical Bug 1 — Global DB scoring bias**: `candidate_store.list_by_cohort(None)` at `orchestrator.py:152` ignores the `cohort_id` parameter entirely (no WHERE clause) and returns ALL candidates ever ingested. Researchers from previous queries accumulate PMIDs across multiple runs and dominate rankings via inflated F1 percentiles.

**Critical Bug 2 — Reporter topical_fit = 0**: `GrantRecord` has no `project_title` field. The evidence trail for Reporter candidates is `"NIH R01XX ($450K)"` — zero topic words overlap with the query. With `beta=1.0`, `T(c,q)=0` zeros the entire composite score for every NIH-funded researcher.

**F-score gaps**: F1 uses raw pub count (iCite not wired), F2 misses international grants, F3 only credits CT.gov PIs, F4 always 0 (no apex data), F5 always 0 (no patents), F7 never computed.

**Integrity bypass**: Every candidate gets `is_zero=False` regardless of LEIE/OFAC/ORI/Retraction Watch status.

**Dead features**: Query type override dropdown has no effect (never sent to backend). Background refresh runs every 6 hours but does nothing (empty source list).

## Solution Approach

The overhaul proceeds in 6 phases:

1. **Dead code removal** — Delete ~30 unused source files, their tests, and related imports. Clean up `__init__.py` files.
2. **Data foundation** — Add `project_title` to `GrantRecord`, create integrity data loader, create apex roster YAML files and loader.
3. **Source additions** — Add `search_by_text()` to `UsptoClient`, add `patent_record_to_candidates()` converter, extract grants from OpenAlex `raw_json`.
4. **Pipeline fixes** — Track `ingested_uuids` in `RecordIngester`, fix CT.gov query to use full task_description, fix evidence trails for PI credit, wire iCite enrichment after parallel fetch, wire USPTO as 5th parallel source.
5. **Scoring and integrity** — Compute F1 with RCR, F2 with international grants, F3 with fixed evidence, F4 with apex lookup, F5 with patents, F7 with K-awards/CT.gov/clinical affiliation. Wire `HardGate.evaluate()` per candidate.
6. **API and frontend wiring** — Add `query_type_override` to `QueryRequest`, pass through frontend, remove background refresh.

## Relevant Files

### Existing Files to Modify

- `src/aegis/sources/reporter.py` — Add `project_title: str | None` to `GrantRecord`, parse `data.get("project_title")` in `_parse_grant()`
- `src/aegis/sources/uspto.py` — Add `search_by_text()` method using PatentsView `_text_any` operator
- `src/aegis/sources/openalex.py` — Remove `get_grants_by_funder()` method and `NonUsGrantRecord` import
- `src/aegis/sources/__init__.py` — Rewrite to export only kept sources (12 modules)
- `src/aegis/ingestion/converters.py` — Fix PubMed/Reporter evidence trails, extract grants from OpenAlex raw_json, add `patent_record_to_candidates()`
- `src/aegis/ingestion/record_ingester.py` — Add `ingested_uuids: set[str]` tracking
- `src/aegis/pipeline/orchestrator.py` — Major rewrite: scoring isolation, iCite enrichment, USPTO source, CT.gov query fix, F4/F5/F7 computation, integrity gate wiring
- `src/aegis/api/server.py` — Remove lifespan/background refresh, load integrity+apex stores at startup, pass to QueryPipeline
- `src/aegis/api/schemas.py` — Add `query_type_override: str | None` to `QueryRequest`
- `src/aegis/taxonomy/__init__.py` — Remove chembl_xwalk import
- `frontend/src/app/api/queries/route.ts` — Pass `query_type_override` through to backend
- `frontend/src/components/query/QueryForm.tsx` — Include `query_type` in POST body
- `frontend/src/types/api.ts` — Add `query_type_override?: string` to `QueryRequest` interface

### New Files to Create

- `src/aegis/integrity/data_loader.py` — Auto-download LEIE CSV, OFAC SDN CSV, ORI findings CSV, Retraction Watch via CrossRef API. Cache in `data/integrity/`.
- `src/aegis/ingestion/apex_loader.py` — Load YAML files into `ApexRosterStore` at startup
- `data/apex_rosters/hhmi.yaml` — HHMI Investigators (static bundled member list)
- `data/apex_rosters/nas.yaml` — National Academy of Sciences members
- `data/apex_rosters/nae.yaml` — National Academy of Engineering members
- `data/apex_rosters/nam.yaml` — National Academy of Medicine members
- `data/apex_rosters/lasker.yaml` — Lasker Award laureates
- `data/apex_rosters/nih_merit.yaml` — NIH MERIT Award recipients

### Files to Delete

**Source files**: `src/aegis/sources/abms.py`, `src/aegis/sources/abms_test.py`, `src/aegis/sources/academic_tree.py`, `src/aegis/sources/academic_tree_test.py`, `src/aegis/sources/biorxiv.py`, `src/aegis/sources/preprints_test.py`, `src/aegis/sources/chembl.py`, `src/aegis/sources/cihr.py`, `src/aegis/sources/cihr_test.py`, `src/aegis/sources/cms_ppsas.py`, `src/aegis/sources/cursor.py`, `src/aegis/sources/cursor_test.py`, `src/aegis/sources/drugs_fda.py`, `src/aegis/sources/drugs_fda_test.py`, `src/aegis/sources/epo.py`, `src/aegis/sources/epo_test.py`, `src/aegis/sources/epo_bulk.py`, `src/aegis/sources/patent_bulk_test.py`, `src/aegis/sources/erc.py`, `src/aegis/sources/erc_test.py`, `src/aegis/sources/horizon_europe.py`, `src/aegis/sources/horizon_europe_test.py`, `src/aegis/sources/jst_kaken.py`, `src/aegis/sources/jst_kaken_test.py`, `src/aegis/sources/medrxiv.py`, `src/aegis/sources/mrc.py`, `src/aegis/sources/mrc_test.py`, `src/aegis/sources/nccn.py`, `src/aegis/sources/nccn_test.py`, `src/aegis/sources/non_us_grants.py`, `src/aegis/sources/nppes.py`, `src/aegis/sources/nppes_test.py`, `src/aegis/sources/nsfc.py`, `src/aegis/sources/nsfc_test.py`, `src/aegis/sources/usnwr.py`, `src/aegis/sources/usnwr_test.py`, `src/aegis/sources/uspto_bulk.py`, `src/aegis/sources/wipo.py`, `src/aegis/sources/wipo_test.py`

**Conference directory**: `src/aegis/sources/conferences/` (entire directory)

**State medical boards directory**: `src/aegis/sources/state_medical_boards/` (entire directory)

**Taxonomy**: `src/aegis/taxonomy/chembl_xwalk.py` and its test

**Observability**: `src/aegis/observability/regional_coverage.py`, `src/aegis/observability/regional_coverage_test.py`, `src/aegis/observability/geographic_tracking.py`, `src/aegis/observability/geographic_tracking_test.py`

## Implementation Phases

### Phase 1: Dead Code Removal and Cleanup
Remove ~30 unused source files, their test files, the `conferences/` and `state_medical_boards/` directories, `taxonomy/chembl_xwalk.py`, and the observability modules that depend on removed sources. Rewrite `src/aegis/sources/__init__.py` and `src/aegis/taxonomy/__init__.py` to only export kept modules. Remove the no-op `_background_refresh` function and `lifespan` from `server.py`.

### Phase 2: Data Foundation
Add `project_title: str | None` to `GrantRecord` and parse it from NIH Reporter API responses. Create integrity data loader (`data_loader.py`) that downloads LEIE CSV, OFAC SDN CSV, ORI findings CSV, and Retraction Watch data. Create 6 apex roster YAML files with known members. Create `apex_loader.py` to load YAMLs into `ApexRosterStore`.

### Phase 3: Source and Converter Enhancements
Add `search_by_text()` to `UsptoClient`. Add `patent_record_to_candidates()` to converters. Fix PubMed evidence trail to include "Principal Investigator" when author is senior author. Fix Reporter evidence trail to include project title. Extract grants from OpenAlex `raw_json` and add to `grant_ids`. Remove `get_grants_by_funder()` and `NonUsGrantRecord` import from `openalex.py`.

### Phase 4: Pipeline Orchestrator Rewrite
Track `ingested_uuids` in `RecordIngester._ingest_safe()`. Filter candidates to current-query set. Wire USPTO as 5th parallel source. Fix CT.gov query to use `task_description` directly. Add iCite enrichment as sequential step. Compute F1 with RCR data, F2 with international grants from OpenAlex, F3 with fixed evidence trails, F4 with apex roster lookup, F5 with patents, F7 with K-awards + CT.gov PI count + clinical affiliation keywords. Wire `HardGate.evaluate()` per candidate using loaded stores. Accept integrity/apex stores as constructor args to `QueryPipeline`.

### Phase 5: API and Frontend Wiring
Add `query_type_override: str | None` to `QueryRequest` schema. Pass it from `server.py._run_pipeline()` to `pipeline.execute()`. Load integrity and apex stores at startup in `create_app()`. Update frontend `QueryRequest` type to include `query_type_override`. Update `QueryForm.tsx` to include `classification.query_type` in POST body. Update frontend proxy to pass it through.

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Dead code removal, source cleanup, and data foundation (files to delete, __init__.py rewrites, reporter.py, openalex.py, data loaders)
  - Agent Type: general-purpose

- Builder
  - Name: builder-2
  - Role: Pipeline orchestrator rewrite, scoring, and integrity wiring (orchestrator.py, record_ingester.py, server.py)
  - Agent Type: general-purpose

- Builder
  - Name: builder-3
  - Role: Converter enhancements, USPTO source, API schemas, and frontend wiring (converters.py, uspto.py, schemas.py, QueryForm.tsx, route.ts)
  - Agent Type: general-purpose

- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator

## Step by Step Tasks

### 1. Remove unused source files and directories
- **Task ID**: remove-unused-sources
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Remove all unused source files, test files, and directories from the codebase. These modules are not wired into the query pipeline and add noise.

    ## What to do
    Delete the following files and directories using `rm` or `git rm`:

    **Source files to delete** (in `src/aegis/sources/`):
    - `abms.py`, `abms_test.py`
    - `academic_tree.py`, `academic_tree_test.py`
    - `biorxiv.py`, `preprints_test.py`
    - `chembl.py`
    - `cihr.py`, `cihr_test.py`
    - `cms_ppsas.py`
    - `cursor.py`, `cursor_test.py`
    - `drugs_fda.py`, `drugs_fda_test.py`
    - `epo.py`, `epo_test.py`
    - `epo_bulk.py`, `patent_bulk_test.py`
    - `erc.py`, `erc_test.py`
    - `horizon_europe.py`, `horizon_europe_test.py`
    - `jst_kaken.py`, `jst_kaken_test.py`
    - `medrxiv.py`
    - `mrc.py`, `mrc_test.py`
    - `nccn.py`, `nccn_test.py`
    - `non_us_grants.py`
    - `nppes.py`, `nppes_test.py`
    - `nsfc.py`, `nsfc_test.py`
    - `usnwr.py`, `usnwr_test.py`
    - `uspto_bulk.py`
    - `wipo.py`, `wipo_test.py`

    **Directories to delete** (entire directories):
    - `src/aegis/sources/conferences/` (contains `__init__.py`, `base.py`, `llm_extract.py`, `asco.py`, `acs.py`, `aacr.py`, `failure_log.py`, `failure_log_test.py`)
    - `src/aegis/sources/state_medical_boards/` (contains `__init__.py`, `base.py`, `registry.py`, `california.py`, `new_york.py`, `texas.py`, `florida.py`, `pennsylvania.py`, `ohio.py`, `michigan.py`, `new_jersey.py`, `massachusetts.py`, `illinois.py`)
    - Also delete `src/aegis/sources/conferences_test.py` and `src/aegis/sources/state_medical_boards_test.py`

    **Taxonomy file to delete**:
    - `src/aegis/taxonomy/chembl_xwalk.py` (and its test if one exists)

    **Observability files to delete**:
    - `src/aegis/observability/regional_coverage.py`
    - `src/aegis/observability/regional_coverage_test.py`
    - `src/aegis/observability/geographic_tracking.py`
    - `src/aegis/observability/geographic_tracking_test.py`

    ## Files to modify
    None in this task (init files are updated in the next task).

    ## Acceptance criteria
    - All listed files and directories are deleted
    - No import errors from the deleted files remain (verified in next task)

    ## Validation command
    ```bash
    # Verify files are deleted
    test ! -f src/aegis/sources/abms.py && \
    test ! -f src/aegis/sources/chembl.py && \
    test ! -d src/aegis/sources/conferences && \
    test ! -d src/aegis/sources/state_medical_boards && \
    test ! -f src/aegis/taxonomy/chembl_xwalk.py && \
    test ! -f src/aegis/observability/regional_coverage.py && \
    echo "All unused files removed successfully"
    ```

### 2. Rewrite __init__.py files for kept sources
- **Task ID**: rewrite-init-files
- **Role**: builder
- **Depends On**: remove-unused-sources
- **Assigned To**: builder-1
- **Description**: |
    Rewrite the `__init__.py` files for sources, taxonomy, and observability to only import the kept modules. Also remove the `NonUsGrantRecord` import from `openalex.py`.

    ## What to do

    ### 1. Rewrite `src/aegis/sources/__init__.py`
    Replace the entire file contents with imports for ONLY these 12 kept modules:
    ```python
    """Public-source ingestion clients (PubMed, NIH RePORTER, ClinicalTrials.gov, iCite, OpenAlex, USPTO)."""
    from aegis.sources.apex_rosters import ApexMembership, ApexRosterStore, ApexRosterType
    from aegis.sources.ctgov import CtgovClient, InvestigatorRole, StudyRecord
    from aegis.sources.icite import IciteClient, IciteRecord
    from aegis.sources.leie import LEIERecord, LEIEStore
    from aegis.sources.ofac_sam import OFACSAMRecord, OFACSAMStore
    from aegis.sources.openalex import OpenAlexClient, OpenAlexWork, OpenAlexAuthor, OpenAlexFunder, OpenAlexConcept
    from aegis.sources.ori import ORIFinding, ORIStore
    from aegis.sources.pubmed import AuthorAffiliation, PubMedClient, PubMedRecord
    from aegis.sources.reporter import GrantPI, GrantRecord, ReporterClient
    from aegis.sources.retraction_watch import RetractionRecord, RetractionWatchStore
    from aegis.sources.retry import RetryBudgetExhausted, RetryConfig, RetryPolicy
    from aegis.sources.uspto import InventorAttribution, PatentAssignee, PatentRecord, UsptoClient

    __all__ = [
        "ApexMembership",
        "ApexRosterStore",
        "ApexRosterType",
        "AuthorAffiliation",
        "CtgovClient",
        "IciteClient",
        "IciteRecord",
        "InventorAttribution",
        "InvestigatorRole",
        "LEIERecord",
        "LEIEStore",
        "GrantPI",
        "GrantRecord",
        "OFACSAMRecord",
        "OFACSAMStore",
        "OpenAlexAuthor",
        "OpenAlexClient",
        "OpenAlexConcept",
        "OpenAlexFunder",
        "OpenAlexWork",
        "ORIFinding",
        "ORIStore",
        "PatentAssignee",
        "PatentRecord",
        "PubMedClient",
        "PubMedRecord",
        "ReporterClient",
        "RetractionRecord",
        "RetractionWatchStore",
        "RetryBudgetExhausted",
        "RetryConfig",
        "RetryPolicy",
        "StudyRecord",
        "UsptoClient",
    ]
    ```

    ### 2. Rewrite `src/aegis/taxonomy/__init__.py`
    Remove the `chembl_xwalk` import and its exports. The new file should be:
    ```python
    """Aegis taxonomy cross-walks: CPC-MeSH, ICD-10-MeSH, CPT-MeSH."""
    from __future__ import annotations

    from aegis.taxonomy.cpc_mesh_xwalk import CpcMeshXwalk, MeshMapping
    from aegis.taxonomy.cpc_xwalk_cache import CacheStats, CpcXwalkCache
    from aegis.taxonomy.cpt_mesh import CptMeshXwalk
    from aegis.taxonomy.icd10_mesh import Icd10MeshXwalk

    __all__ = [
        "CacheStats",
        "CpcMeshXwalk",
        "CpcXwalkCache",
        "CptMeshXwalk",
        "Icd10MeshXwalk",
        "MeshMapping",
    ]
    ```

    ### 3. Edit `src/aegis/sources/openalex.py`
    Remove the import line `from aegis.sources.non_us_grants import NonUsGrantRecord` (line 17).
    Remove the `get_grants_by_funder()` method (lines 375-483) and the helper `_work_to_grant()` method (lines 417-483).
    Also remove the `FUNDER_IDS`, `_FUNDER_COUNTRY`, and `_FUNDER_CURRENCY` dicts (lines 24-53) since they are only used by `get_grants_by_funder()`.

    ### 4. Check for broken imports
    Search the codebase for any remaining imports of deleted modules. Fix any that are found. Common places to check:
    - `src/aegis/observability/__init__.py` — may import `regional_coverage` or `geographic_tracking`
    - Any test files that import removed modules
    - `src/aegis/taxonomy/chembl_xwalk.py` imported `ChemblIngestor` from `chembl.py` — but both are deleted so no issue

    ## Acceptance criteria
    - `src/aegis/sources/__init__.py` only imports 12 kept modules
    - `src/aegis/taxonomy/__init__.py` does not reference `chembl_xwalk`
    - `src/aegis/sources/openalex.py` does not import `NonUsGrantRecord` or contain `get_grants_by_funder`
    - `uv run python -c "from aegis.sources import PubMedClient, ReporterClient, CtgovClient, IciteClient, UsptoClient, LEIEStore, OFACSAMStore, ORIStore, RetractionWatchStore, ApexRosterStore"` succeeds
    - `uv run python -c "from aegis.taxonomy import CpcMeshXwalk, Icd10MeshXwalk, CptMeshXwalk"` succeeds

    ## Validation command
    ```bash
    uv run python -c "from aegis.sources import PubMedClient, ReporterClient, CtgovClient, IciteClient, UsptoClient, LEIEStore, OFACSAMStore, ORIStore, RetractionWatchStore, ApexRosterStore; print('sources OK')"
    uv run python -c "from aegis.taxonomy import CpcMeshXwalk, Icd10MeshXwalk, CptMeshXwalk; print('taxonomy OK')"
    uv run python -c "from aegis.sources.openalex import OpenAlexClient; print('openalex OK')"
    ```

### 3. Add project_title to GrantRecord and fix Reporter evidence trail
- **Task ID**: reporter-project-title
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Add `project_title: str | None` to `GrantRecord` and parse it from the NIH Reporter API response. This is the root cause of Reporter candidates getting `topical_fit = 0` (the evidence trail has no topic words).

    ## What to do

    ### 1. Edit `src/aegis/sources/reporter.py`

    Add `project_title: str | None = None` field to the `GrantRecord` model (after `activity_code` field, line ~39):
    ```python
    class GrantRecord(BaseModel):
        """A single NIH grant record from RePORTER."""

        model_config = ConfigDict(frozen=True)

        project_number: str
        activity_code: str
        project_title: str | None = None    # <-- ADD THIS
        pis: list[GrantPI]
        total_cost: int | None = None
        ...
    ```

    In the `_parse_grant()` function, extract `project_title` from the API response and include it in the `GrantRecord` constructor. Add this line before the `return GrantRecord(...)` call (around line 109):
    ```python
    project_title = data.get("project_title") or data.get("project_title_text") or None
    ```

    Then add `project_title=project_title` to the `GrantRecord(...)` constructor call.

    ### 2. Edit `src/aegis/ingestion/converters.py` — fix grant_record_to_candidates evidence trail

    In the `grant_record_to_candidates()` function (line 116-171), change the evidence trail string from:
    ```python
    evidence_trail=[
        f"NIH {record.project_number} ({record.fiscal_year}, {cost_str})"
    ],
    ```
    To:
    ```python
    title_part = f": '{record.project_title[:80]}'" if record.project_title else ""
    ...
    evidence_trail=[
        f"Principal Investigator on NIH {record.project_number}{title_part} ({record.fiscal_year}, {cost_str})"
    ],
    ```

    The `title_part` variable should be computed before the `Candidate()` constructor. This change does TWO things:
    1. Adds the project title so topical_fit can match query words
    2. Adds "Principal Investigator" so F3 leadership detection finds PI credit

    ## Files to modify
    - `src/aegis/sources/reporter.py` — Add `project_title` field and parse it
    - `src/aegis/ingestion/converters.py` — Fix evidence trail in `grant_record_to_candidates()`

    ## Code patterns to follow
    - All models use `ConfigDict(frozen=True)`
    - Use `from __future__ import annotations` at top of every module
    - Fields with defaults use `field_name: type = default`

    ## Acceptance criteria
    - `GrantRecord` has a `project_title: str | None` field
    - `_parse_grant()` extracts `project_title` from API response
    - `grant_record_to_candidates()` evidence trail includes project title and "Principal Investigator"
    - `uv run python -c "from aegis.sources.reporter import GrantRecord; print(GrantRecord.model_fields.keys())"` shows `project_title`

    ## Validation command
    ```bash
    uv run python -c "from aegis.sources.reporter import GrantRecord; assert 'project_title' in GrantRecord.model_fields; print('GrantRecord has project_title')"
    uv run python -m py_compile src/aegis/sources/reporter.py
    uv run python -m py_compile src/aegis/ingestion/converters.py
    ```

### 4. Create integrity data loader
- **Task ID**: integrity-data-loader
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create `src/aegis/integrity/data_loader.py` that downloads integrity data files at startup and populates the in-memory stores (`LEIEStore`, `OFACSAMStore`, `ORIStore`, `RetractionWatchStore`).

    ## What to do

    Create the file `src/aegis/integrity/data_loader.py` with the following structure:

    ```python
    """Auto-download and cache integrity data for LEIE, OFAC/SAM, ORI, Retraction Watch."""

    from __future__ import annotations

    import csv
    import io
    import logging
    import zipfile
    from datetime import date
    from pathlib import Path

    import httpx

    from aegis.sources.leie import LEIERecord, LEIEStore
    from aegis.sources.ofac_sam import OFACSAMRecord, OFACSAMStore
    from aegis.sources.ori import ORIFinding, ORIStore
    from aegis.sources.retraction_watch import RetractionRecord, RetractionWatchStore

    logger = logging.getLogger(__name__)

    _CACHE_DIR = Path("data/integrity")
    _LEIE_URL = "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv"
    _OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
    # ORI case summaries page (no direct CSV; we'll parse from HTML or use cached data)
    _ORI_URL = "https://ori.hhs.gov/content/case-summary"
    ```

    The module should provide these functions:

    1. `load_integrity_stores(cache_dir: Path | None = None) -> tuple[LEIEStore, OFACSAMStore, ORIStore, RetractionWatchStore]`
       - Main entry point. Downloads data if not cached (or if cache is >30 days old), then loads into stores.
       - Returns all four populated stores.

    2. `_download_leie(cache_dir: Path) -> list[LEIERecord]`
       - Downloads LEIE CSV from HHS-OIG
       - Parses CSV columns: LASTNAME, FIRSTNAME, NPI, EXCLTYPE, EXCLDATE, REINDATE, STATE, SPECIALTY
       - Caches to `{cache_dir}/leie.csv`
       - Returns list of `LEIERecord`

    3. `_download_ofac(cache_dir: Path) -> list[OFACSAMRecord]`
       - Downloads OFAC SDN CSV
       - Parses columns: primary_name, aliases (pipe-delimited), source="OFAC", record_type, program
       - Caches to `{cache_dir}/ofac_sdn.csv`
       - Returns list of `OFACSAMRecord`

    4. `_download_ori(cache_dir: Path) -> list[ORIFinding]`
       - For now, creates an empty list (ORI has no public CSV API)
       - Logs a warning that ORI data must be manually populated
       - Returns empty `list[ORIFinding]`

    5. `_download_retraction_watch(cache_dir: Path) -> list[RetractionRecord]`
       - Uses CrossRef API `https://api.crossref.org/works?filter=type:retraction&rows=1000`
       - Parses title, authors, DOI
       - Caches to `{cache_dir}/retractions.json`
       - Returns list of `RetractionRecord`

    **Important**: Each download function should:
    - Create `cache_dir` if it doesn't exist (`cache_dir.mkdir(parents=True, exist_ok=True)`)
    - Check if cached file exists and is less than 30 days old before downloading
    - Use `httpx` for HTTP requests (consistent with rest of codebase)
    - Catch and log all exceptions without crashing (integrity data is best-effort)
    - Use `from __future__ import annotations` at top

    ## Files to modify
    - NEW: `src/aegis/integrity/data_loader.py`

    ## Code patterns to follow
    - Use `from __future__ import annotations` at top
    - Use `httpx` for HTTP (not `requests`)
    - Use `logging.getLogger(__name__)` for logging
    - Use `Path` from pathlib for file paths
    - All errors should be caught and logged, never crash the server

    ## Acceptance criteria
    - `data_loader.py` exists and compiles
    - `load_integrity_stores()` returns a tuple of 4 stores
    - `_download_leie()` parses LEIE CSV into `LEIERecord` objects
    - `_download_ofac()` parses OFAC SDN CSV into `OFACSAMRecord` objects
    - Errors are caught and logged, never crash

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/integrity/data_loader.py
    uv run python -c "from aegis.integrity.data_loader import load_integrity_stores; print('data_loader imports OK')"
    ```

### 5. Create apex roster YAML files and loader
- **Task ID**: apex-roster-data
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create static YAML files with known apex roster members and a loader module to populate `ApexRosterStore`.

    ## What to do

    ### 1. Create directory `data/apex_rosters/`

    ### 2. Create 6 YAML files with the following format:

    Each YAML file has this structure:
    ```yaml
    roster_type: hhmi_investigator  # matches ApexRosterType enum
    members:
      - name: "Jennifer Doudna"
        year: 1997
        institution: "UC Berkeley"
      - name: "Feng Zhang"
        year: 2018
        institution: "MIT"
    ```

    Create these files with 5-10 real members each (from public record):

    **`data/apex_rosters/hhmi.yaml`** — `roster_type: hhmi_investigator`
    Include well-known HHMI Investigators: Jennifer Doudna, Feng Zhang, David Baker, Carolyn Bertozzi, Karl Deisseroth, Huda Zoghbi, Xiaowei Zhuang, Alice Bhatt, David Julius, Clifford Brangwynne

    **`data/apex_rosters/nas.yaml`** — `roster_type: nas_member`
    Include: Frances Arnold, Jennifer Doudna, David Baltimore, Eric Lander, Charles Lieber, Robert Langer, Huda Zoghbi, Feng Zhang, David Baker, Emmanuelle Charpentier

    **`data/apex_rosters/nae.yaml`** — `roster_type: nae_member`
    Include: Robert Langer, Frances Arnold, Subra Suresh, Pradeep Khosla, Mark Humayun, Angela Belcher, Paula Hammond, Chad Mirkin, Nicholas Peppas, Kristi Anseth

    **`data/apex_rosters/nam.yaml`** — `roster_type: nam_member`
    Include: Anthony Fauci, Francis Collins, Harvey Fineberg, Victor Dzau, David Satcher, Margaret Hamburg, Atul Gawande, Siddhartha Mukherjee, Eric Topol, Vivek Murthy

    **`data/apex_rosters/lasker.yaml`** — `roster_type: lasker_laureate`
    Include: Katalin Kariko, Drew Weissman, David Julius, Ardem Patapoutian, Jennifer Doudna, Emmanuelle Charpentier, James Allison, Carl June, Michael Hall, Franz-Ulrich Hartl

    **`data/apex_rosters/nih_merit.yaml`** — `roster_type: nih_merit`
    Include: Robert Weinberg, Bert Vogelstein, Mary-Claire King, Eric Lander, Francis Collins, Harold Varmus, Elizabeth Blackburn, Carol Greider, Jack Szostak, Thomas Cech

    ### 3. Create `src/aegis/ingestion/apex_loader.py`

    ```python
    """Load apex roster YAML files into ApexRosterStore."""

    from __future__ import annotations

    import logging
    from pathlib import Path

    import yaml  # type: ignore[import-untyped]

    from aegis.sources.apex_rosters import ApexMembership, ApexRosterStore, ApexRosterType

    logger = logging.getLogger(__name__)

    _DEFAULT_ROSTER_DIR = Path("data/apex_rosters")


    def load_apex_rosters(
        roster_dir: Path | None = None,
    ) -> ApexRosterStore:
        """Load all YAML roster files from the given directory into an ApexRosterStore."""
        directory = roster_dir or _DEFAULT_ROSTER_DIR
        store = ApexRosterStore()

        if not directory.exists():
            logger.warning("Apex roster directory not found: %s", directory)
            return store

        for yaml_file in sorted(directory.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                roster_type = ApexRosterType(data["roster_type"])
                members = []
                for m in data.get("members", []):
                    members.append(
                        ApexMembership(
                            roster_type=roster_type,
                            name=m["name"],
                            year=m.get("year"),
                            institution=m.get("institution"),
                            confidence=1.0,
                        )
                    )
                store.add_batch(members)
                logger.info("Loaded %d members from %s", len(members), yaml_file.name)
            except Exception:
                logger.warning("Failed to load roster %s", yaml_file.name, exc_info=True)

        logger.info("Apex roster store loaded: %d total members", store.count())
        return store
    ```

    ## Files to modify
    - NEW: `data/apex_rosters/hhmi.yaml`
    - NEW: `data/apex_rosters/nas.yaml`
    - NEW: `data/apex_rosters/nae.yaml`
    - NEW: `data/apex_rosters/nam.yaml`
    - NEW: `data/apex_rosters/lasker.yaml`
    - NEW: `data/apex_rosters/nih_merit.yaml`
    - NEW: `src/aegis/ingestion/apex_loader.py`

    ## Acceptance criteria
    - All 6 YAML files exist in `data/apex_rosters/` with valid YAML
    - `apex_loader.py` compiles and imports successfully
    - `load_apex_rosters()` returns an `ApexRosterStore` with >50 members total
    - `store.lookup_by_name("Jennifer Doudna")` returns at least 1 result

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/ingestion/apex_loader.py
    uv run python -c "
    from aegis.ingestion.apex_loader import load_apex_rosters
    store = load_apex_rosters()
    assert store.count() > 50, f'Expected >50 members, got {store.count()}'
    results = store.lookup_by_name('Jennifer Doudna')
    assert len(results) > 0, 'Jennifer Doudna not found'
    print(f'Apex roster store: {store.count()} members, Jennifer Doudna found')
    "
    ```

### 6. Add search_by_text to UsptoClient and patent converter
- **Task ID**: uspto-text-search
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-3
- **Description**: |
    Add a `search_by_text()` method to `UsptoClient` that searches patents by abstract text, and add a `patent_record_to_candidates()` converter function.

    ## What to do

    ### 1. Edit `src/aegis/sources/uspto.py`

    Add a new method `search_by_text()` to the `UsptoClient` class (after the existing `fetch_patents()` method). The PatentsView API supports text search using the `_text_any` operator on `patent_abstract`:

    ```python
    async def search_by_text(
        self,
        query_text: str,
        since: date | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[PatentRecord]:
        """Search patents by abstract text matching.

        Uses PatentsView `_text_any` operator on patent_abstract.
        """
        text_filter: dict[str, Any] = {
            "_text_any": {"patent_abstract": query_text}
        }
        if since is not None:
            query: dict[str, Any] = {
                "_and": [
                    text_filter,
                    {"_gte": {"patent_date": since.isoformat()}},
                ]
            }
        else:
            query = text_filter

        fields = [
            "patent_number",
            "patent_date",
            "patent_title",
            "patent_abstract",
            "patent_num_cited_by_us_patents",
        ]

        page = 1
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                payload = {
                    "q": query,
                    "f": fields,
                    "o": {"page": page, "per_page": batch_size},
                    "s": [{"patent_date": "desc"}],
                }

                async def _do_post(p: dict[str, Any] = payload) -> httpx.Response:
                    resp = await client.post(
                        PATENTSVIEW_API_URL,
                        json=p,
                    )
                    resp.raise_for_status()
                    return resp

                response = await self._retry.execute(_do_post)
                body = response.json()
                patents = body.get("patents") or []

                if not patents:
                    break

                for pat in patents:
                    record = self._parse_patent(pat)
                    if record is not None:
                        yield record

                total = body.get("total_patent_count", 0)
                if page * batch_size >= total:
                    break
                page += 1
    ```

    ### 2. Edit `src/aegis/ingestion/converters.py`

    Add a new converter function `patent_record_to_candidates()` at the bottom of the file, after the OpenAlex section:

    ```python
    # ---------------------------------------------------------------------------
    # USPTO Patents
    # ---------------------------------------------------------------------------

    from aegis.sources.uspto import PatentRecord


    def patent_record_to_candidates(record: PatentRecord) -> list[Candidate]:
        """Extract lead inventor as candidate from a patent record."""
        lead_inventors = [i for i in record.inventors if i.is_lead_inventor]
        if not lead_inventors and record.inventors:
            lead_inventors = [record.inventors[0]]

        results: list[Candidate] = []
        for inventor in lead_inventors:
            name = inventor.full_name.strip()
            if not name:
                continue

            uuid = _make_uuid({}, name)
            title_short = record.title[:80] if record.title else record.patent_number

            results.append(
                Candidate(
                    uuid=uuid,
                    strong_keys={},
                    name_variants=[name],
                    affiliations=[],
                    artifact_refs=ArtifactRefBundle(
                        pmids=[],
                        nct_ids=[],
                        grant_ids=[],
                        patent_ids=[record.patent_number],
                    ),
                    linkage_confidence=0.60,
                    evidence_trail=[
                        f"Lead inventor on US{record.patent_number}: '{title_short}' ({record.grant_date or 'date unknown'})"
                    ],
                    last_updated_per_source={"uspto": datetime.now(UTC)},
                    mesh_descriptors=[],
                )
            )
        return results
    ```

    Also add the import of `patent_record_to_candidates` to the top-level imports that other modules use. The function should be importable from `aegis.ingestion.converters`.

    ## Files to modify
    - `src/aegis/sources/uspto.py` — Add `search_by_text()` method
    - `src/aegis/ingestion/converters.py` — Add `patent_record_to_candidates()` function (add `from aegis.sources.uspto import PatentRecord` import)

    ## Code patterns to follow
    - Async generators use `AsyncIterator` return type
    - All methods use `self._retry.execute()` for HTTP calls
    - Converter functions return `list[Candidate]`
    - Evidence trail strings should be descriptive with key identifying info

    ## Acceptance criteria
    - `UsptoClient` has a `search_by_text()` method
    - `patent_record_to_candidates()` is importable from `aegis.ingestion.converters`
    - Both files compile without errors

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/sources/uspto.py
    uv run python -m py_compile src/aegis/ingestion/converters.py
    uv run python -c "from aegis.sources.uspto import UsptoClient; assert hasattr(UsptoClient, 'search_by_text'); print('search_by_text exists')"
    uv run python -c "from aegis.ingestion.converters import patent_record_to_candidates; print('patent converter importable')"
    ```

### 7. Fix PubMed evidence trail and OpenAlex grant extraction
- **Task ID**: fix-evidence-trails
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-3
- **Description**: |
    Fix PubMed evidence trail to include "Principal Investigator" for senior authors (so F3 gives credit). Extract grants from OpenAlex `raw_json` and add to `grant_ids`.

    ## What to do

    ### 1. Edit `src/aegis/ingestion/converters.py` — PubMed evidence trail

    In the `pubmed_record_to_candidates()` function (lines 54-108), change the evidence trail from:
    ```python
    evidence_trail=[
        f"Published '{title_short}' (PMID:{record.pmid}, {date_str})"
    ],
    ```
    To:
    ```python
    evidence_trail=[
        f"Principal Investigator: '{title_short}' (PMID:{record.pmid}, {date_str})"
    ],
    ```

    This is appropriate because `pubmed_record_to_candidates()` already extracts only last/senior authors (line 56: `authors = [a for a in record.authors if a.is_last_author]`), and senior/last authors on biomedical publications are typically the principal investigator of the lab.

    ### 2. Edit `src/aegis/ingestion/converters.py` — OpenAlex grant extraction

    In the `openalex_work_to_candidates()` function (lines 242-286), extract grant IDs from the `raw_json` field. The OpenAlex API response includes a `grants` array in the work JSON with format:
    ```json
    {
        "grants": [
            {"funder": "https://openalex.org/F...", "funder_display_name": "ERC", "award_id": "123456"},
            {"funder": "https://openalex.org/F...", "funder_display_name": "NIH", "award_id": "R01CA123456"}
        ]
    }
    ```

    Add grant extraction by parsing `raw_json` before creating the `Candidate`:
    ```python
    import json as json_mod  # add near top of file if not already imported

    # In openalex_work_to_candidates, before the Candidate() constructor:
    # Extract grants from raw_json
    grant_ids: list[str] = []
    try:
        raw_data = json_mod.loads(record.raw_json)
        for grant in raw_data.get("grants") or []:
            award_id = grant.get("award_id")
            funder_name = grant.get("funder_display_name", "")
            if award_id:
                grant_ids.append(f"{funder_name}-{award_id}" if funder_name else award_id)
    except (json_mod.JSONDecodeError, TypeError):
        pass
    ```

    Then update the `ArtifactRefBundle` in the `Candidate` constructor to include `grant_ids`:
    ```python
    artifact_refs=ArtifactRefBundle(
        pmids=[record.pmid] if record.pmid else [],
        nct_ids=[],
        grant_ids=grant_ids,  # <-- was [] before
        patent_ids=[],
    ),
    ```

    Note: `json` is already imported at the top of `openalex.py` (as `json`), but in `converters.py` it needs to be imported. Since `json` is a stdlib module, add `import json` near the other imports at the top of `converters.py`.

    ## Files to modify
    - `src/aegis/ingestion/converters.py` — Fix PubMed evidence trail, add OpenAlex grant extraction

    ## Code patterns to follow
    - Error handling: wrap JSON parsing in try/except, never crash
    - Grant IDs: formatted as `"{funder_name}-{award_id}"` for consistency with existing grant_id formats

    ## Acceptance criteria
    - PubMed evidence trail starts with "Principal Investigator:"
    - OpenAlex candidates have `grant_ids` populated from raw_json grants array
    - File compiles without errors

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/ingestion/converters.py
    uv run python -c "
    from aegis.ingestion.converters import pubmed_record_to_candidates, openalex_work_to_candidates
    print('converters compile OK')
    "
    ```

### 8. Add ingested_uuids tracking to RecordIngester
- **Task ID**: ingester-uuid-tracking
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Add `ingested_uuids: set[str]` to `RecordIngester` to track all candidate UUIDs touched during the current query. This set will be used by the orchestrator to filter candidates to only those from the current query, fixing the global DB scoring bias.

    ## What to do

    ### Edit `src/aegis/ingestion/record_ingester.py`

    1. Add `self.ingested_uuids: set[str] = set()` to `__init__()` (after `self.linked_count = 0`, around line 97):
    ```python
    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._store = CandidateStore(db_path=db_path)
        self._cache: dict[tuple[str, str], str] = {}
        self.new_count = 0
        self.merged_count = 0
        self.error_count = 0
        self.linked_count = 0
        self.ingested_uuids: set[str] = set()  # <-- ADD THIS

        # Load existing candidates once for probabilistic linking.
        self._snapshot: list[Candidate] = self._store.list_by_cohort(None)
        ...
    ```

    2. In `_ingest_safe()` (line 114-135), add the UUID to `ingested_uuids` in BOTH code paths (merge and new):

    In the merge path (around line 127, after `self.merged_count += 1`):
    ```python
    self.ingested_uuids.add(merged.uuid)
    ```

    In the new candidate path (around line 134, after `self.new_count += 1`):
    ```python
    self.ingested_uuids.add(candidate.uuid)
    ```

    The full `_ingest_safe` method should look like:
    ```python
    def _ingest_safe(self, candidate: Candidate) -> bool:
        existing_uuid = self._find_existing(candidate)

        if existing_uuid:
            existing = self._store.get_by_uuid(existing_uuid)
            if existing:
                merged = _merge_candidates(existing, candidate)
                self._upsert_with_retry(merged)
                self._snapshot = [
                    merged if c.uuid == merged.uuid else c
                    for c in self._snapshot
                ]
                self.merged_count += 1
                self.ingested_uuids.add(merged.uuid)  # <-- ADD
                return False

        # New candidate
        self._upsert_with_retry(candidate)
        self._update_cache(candidate)
        self._snapshot.append(candidate)
        self.new_count += 1
        self.ingested_uuids.add(candidate.uuid)  # <-- ADD
        return True
    ```

    ## Files to modify
    - `src/aegis/ingestion/record_ingester.py` — Add `ingested_uuids` set, populate in `_ingest_safe()`

    ## Acceptance criteria
    - `RecordIngester` has an `ingested_uuids` attribute of type `set[str]`
    - Both merge and new-candidate paths add the UUID to the set
    - File compiles without errors

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/ingestion/record_ingester.py
    uv run python -c "
    from aegis.ingestion.record_ingester import RecordIngester
    # Check attribute exists (don't connect to DB)
    import inspect
    source = inspect.getsource(RecordIngester.__init__)
    assert 'ingested_uuids' in source, 'ingested_uuids not in __init__'
    print('ingested_uuids tracking verified')
    "
    ```

### 9. Add query_type_override to API schema
- **Task ID**: schema-query-type-override
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-3
- **Description**: |
    Add `query_type_override: str | None` to the `QueryRequest` Pydantic model so the frontend can pass a user-selected query type override to the backend.

    ## What to do

    ### 1. Edit `src/aegis/api/schemas.py`

    Add `query_type_override: str | None = None` to the `QueryRequest` model (after the `include_variance_bands` field, around line 33):

    ```python
    class QueryRequest(BaseModel):
        """Customer query request for expert discovery."""

        model_config = ConfigDict(frozen=True)

        task_description: str
        mesh_override: list[str] | None = None
        cohort_filter: str | None = None
        k: int = Field(default=50, ge=1, le=500)
        cutoff_strategy: CutoffStrategy = CutoffStrategy.top_k
        score_threshold: float | None = None
        include_variance_bands: bool = True
        query_type_override: str | None = None  # <-- ADD THIS
    ```

    ### 2. Edit `src/aegis/api/server.py`

    In the `_run_pipeline()` function (around line 142), pass `query_type_override` from the request body to `pipeline.execute()`:

    Change:
    ```python
    pipeline_result = await pipeline.execute(
        task_description=body.task_description,
        mesh_override=body.mesh_override,
        k=body.k,
        progress_callback=_progress_callback,
    )
    ```
    To:
    ```python
    pipeline_result = await pipeline.execute(
        task_description=body.task_description,
        mesh_override=body.mesh_override,
        k=body.k,
        query_type_override=body.query_type_override,
        progress_callback=_progress_callback,
    )
    ```

    ### 3. Edit `frontend/src/types/api.ts`

    Add `query_type_override?: string;` to the `QueryRequest` interface:
    ```typescript
    export interface QueryRequest {
      task_description: string;
      population?: Population;
      mesh_override?: string[];
      k?: number;
      cutoff_strategy?: string;
      query_type_override?: string;  // <-- ADD THIS
    }
    ```

    ### 4. Edit `frontend/src/components/query/QueryForm.tsx`

    In the `handleSubmit` function (around line 80), include the classification query type in the POST body if the user has overridden it:

    Change:
    ```typescript
    const body: QueryRequest = {
        task_description: taskDescription.trim(),
        k,
    };
    ```
    To:
    ```typescript
    const body: QueryRequest = {
        task_description: taskDescription.trim(),
        k,
    };

    // Include query type override if user changed it
    if (classification?.query_type) {
        body.query_type_override = classification.query_type;
    }
    ```

    ### 5. Edit `frontend/src/app/api/queries/route.ts`

    The proxy already has `& { query_type_override?: string }` in the type but it passes through `body` directly, so this should work automatically. Verify it does.

    ## Files to modify
    - `src/aegis/api/schemas.py` — Add `query_type_override` field
    - `src/aegis/api/server.py` — Pass `query_type_override` to `pipeline.execute()`
    - `frontend/src/types/api.ts` — Add `query_type_override` to interface
    - `frontend/src/components/query/QueryForm.tsx` — Include override in POST body

    ## Acceptance criteria
    - `QueryRequest` schema has `query_type_override: str | None = None`
    - `server.py` passes `query_type_override` to pipeline
    - Frontend `QueryRequest` type has `query_type_override`
    - `QueryForm` includes classification query type in POST body

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/api/schemas.py
    uv run python -c "from aegis.api.schemas import QueryRequest; assert 'query_type_override' in QueryRequest.model_fields; print('schema OK')"
    uv run python -m py_compile src/aegis/api/server.py
    ```

### 10. Rewrite pipeline orchestrator — source wiring, scoring isolation, and integrity gate
- **Task ID**: orchestrator-rewrite
- **Role**: builder
- **Depends On**: ingester-uuid-tracking, reporter-project-title, uspto-text-search, fix-evidence-trails, integrity-data-loader, apex-roster-data
- **Assigned To**: builder-2
- **Description**: |
    Major rewrite of `src/aegis/pipeline/orchestrator.py` to fix scoring isolation (use ingested_uuids instead of global DB), wire USPTO as 5th source, add iCite enrichment, fix CT.gov query, compute all F-scores correctly, and wire the integrity hard gate.

    ## What to do

    ### 1. Accept integrity and apex stores as constructor args

    Change the `__init__` signature to accept optional stores:
    ```python
    def __init__(
        self,
        *,
        db_path: str = "aegis.duckdb",
        leie_store: LEIEStore | None = None,
        ofac_sam_store: OFACSAMStore | None = None,
        ori_store: ORIStore | None = None,
        retraction_store: RetractionWatchStore | None = None,
        apex_store: ApexRosterStore | None = None,
    ) -> None:
        self._db_path = db_path
        self._classifier = QueryClassifier()
        self._expander = LlmQueryExpander()
        self._leie_store = leie_store or LEIEStore()
        self._ofac_sam_store = ofac_sam_store or OFACSAMStore()
        self._ori_store = ori_store or ORIStore()
        self._retraction_store = retraction_store or RetractionWatchStore()
        self._apex_store = apex_store or ApexRosterStore()
    ```

    Add imports at top:
    ```python
    from aegis.sources.leie import LEIEStore
    from aegis.sources.ofac_sam import OFACSAMStore
    from aegis.sources.ori import ORIStore
    from aegis.sources.retraction_watch import RetractionWatchStore
    from aegis.sources.apex_rosters import ApexRosterStore
    from aegis.ingestion.converters import patent_record_to_candidates
    ```

    ### 2. Fix candidate loading — use ingested_uuids

    In the `execute()` method, replace the global DB load (lines 150-154):
    ```python
    # OLD — loads ALL candidates ever
    store = CandidateStore(db_path=self._db_path)
    try:
        all_candidates = store.list_by_cohort(None)
    finally:
        store.close()
    ```

    With filtered loading using `ingester.ingested_uuids`:
    ```python
    # NEW — load only candidates from current query
    store = CandidateStore(db_path=self._db_path)
    try:
        all_candidates = [
            c for c in store.list_by_cohort(None)
            if c.uuid in ingester.ingested_uuids
        ]
    finally:
        store.close()
    ```

    **IMPORTANT**: `ingester` must be available at this point. Currently the code creates `ingester` in the try block (line 141) and closes it (line 147) before loading candidates. Restructure so that `ingester.ingested_uuids` is captured before closing:

    ```python
    ingester = RecordIngester(db_path=self._db_path)
    try:
        fetched_count, source_progress = await self._fetch_all_sources(
            task_description, mesh_terms, progress_callback, ingester
        )
        current_uuids = set(ingester.ingested_uuids)  # capture before close
    finally:
        ingester.close()

    # Load only current-query candidates
    store = CandidateStore(db_path=self._db_path)
    try:
        all_candidates = [
            c for c in store.list_by_cohort(None)
            if c.uuid in current_uuids
        ]
    finally:
        store.close()
    ```

    ### 3. Add iCite enrichment after parallel fetch

    After `_fetch_all_sources()` completes but before loading candidates, add an iCite enrichment step. This collects all PMIDs from ingested candidates and fetches RCR data:

    ```python
    # After _fetch_all_sources, before closing ingester:
    # Collect all PMIDs from ingested candidates for iCite enrichment
    all_pmids: list[str] = []
    for c_snap in ingester._snapshot:
        if c_snap.uuid in ingester.ingested_uuids:
            all_pmids.extend(c_snap.artifact_refs.pmids)
    all_pmids = list(set(all_pmids))  # deduplicate

    # iCite enrichment (sequential, after parallel fetch)
    icite_rcr: dict[str, float] = {}
    if all_pmids:
        try:
            from aegis.sources.icite import IciteClient
            icite_client = IciteClient()
            async for icite_rec in icite_client.fetch_by_pmids(all_pmids):
                if icite_rec.relative_citation_ratio is not None:
                    icite_rcr[icite_rec.pmid] = icite_rec.relative_citation_ratio
            logger.info("iCite enrichment: %d/%d PMIDs have RCR", len(icite_rcr), len(all_pmids))
        except Exception as exc:
            logger.warning("iCite enrichment failed: %s", exc)
    ```

    Store `icite_rcr` so it can be used in `_compute_scores()`.

    ### 4. Add USPTO as 5th parallel source

    In `_fetch_all_sources()`, add "uspto" to `source_names`:
    ```python
    source_names = [
        "pubmed",
        "reporter",
        "ctgov",
        "openalex_works",
        "uspto",
    ]
    ```

    In `_fetch_source()`, add the USPTO branch:
    ```python
    elif source_name == "uspto":
        from aegis.sources.uspto import UsptoClient
        from datetime import date, timedelta

        uspto_client = UsptoClient()
        since = date.today() - timedelta(days=365 * 5)  # last 5 years
        async for pat_rec in uspto_client.search_by_text(query, since=since):
            for candidate in patent_record_to_candidates(pat_rec):
                ingester.ingest(candidate)
            count += 1
            if count >= 100:  # fewer patents than pubs
                break
        ingester.log_summary("uspto")
    ```

    ### 5. Fix CT.gov query

    Change the CT.gov query from `mesh_terms[0]` to `task_description`:
    ```python
    elif source_name == "ctgov":
        from aegis.sources.ctgov import CtgovClient

        ct_client = CtgovClient()
        # Use full task description for more precise trial matching
        # instead of mesh_terms[0] which is too broad
        ctgov_query = query  # query = task_description
        async for ct_rec in ct_client.fetch_studies_by_text(
            query_text=ctgov_query
        ):
    ```

    ### 6. Rewrite _compute_scores to use real F1-F7

    Pass `icite_rcr` dict and `self._apex_store` to `_compute_scores()`. Update the method signature:
    ```python
    def _compute_scores(
        self,
        candidates: list[Candidate],
        mesh_terms: list[str],
        query_text: str,
        weight_vector: WeightVector,
        icite_rcr: dict[str, float] | None = None,
    ) -> tuple[list[CandidateScoreInput], dict[str, dict[str, float]]]:
    ```

    **F1 — Research output quality with RCR**:
    ```python
    # F1: Use iCite RCR if available, fallback to pub count
    if icite_rcr:
        candidate_rcrs = [icite_rcr.get(pmid, 0.0) for pmid in c.artifact_refs.pmids]
        mean_rcr = sum(candidate_rcrs) / len(candidate_rcrs) if candidate_rcrs else 0.0
        f1_raw = min(1.0, mean_rcr / 5.0)  # RCR of 5 = max score
    else:
        pub_count = len(c.artifact_refs.pmids)
        nct_count = len(c.artifact_refs.nct_ids)
        f1_raw = min(1.0, pub_count / 20.0 + nct_count / 15.0)
    ```

    **F2 — Funding (now includes international grants via OpenAlex)**:
    No code change needed — OpenAlex grant extraction (from task 7) already populates `grant_ids` in the candidate's `ArtifactRefBundle`. The existing F2 code `grant_count = len(c.artifact_refs.grant_ids)` will automatically include them.

    **F3 — Leadership (already fixed by evidence trail changes)**:
    No code change needed — tasks 3 and 7 fixed the evidence trails to include "Principal Investigator", which the existing F3 code `if "PI" in e.upper() or "principal" in e.lower()` already detects.

    **F4 — Apex roster membership**:
    Replace the evidence-trail-based F4 with a real apex lookup:
    ```python
    # F4: Apex roster membership (real lookup)
    name = c.name_variants[0] if c.name_variants else ""
    institution = c.affiliations[0].canonical_name if c.affiliations else None
    apex_matches = self._apex_store.lookup_by_name(name, institution)
    f4_raw = min(1.0, len(apex_matches) / 2.0)  # 2+ memberships = max
    f_raw["f4"].append((c.uuid, f4_raw))
    ```

    **F5 — Translational (now includes patents)**:
    No code change needed — USPTO converter (from task 6) populates `patent_ids` in the candidate's `ArtifactRefBundle`. The existing F5 code already uses `patent_count = len(c.artifact_refs.patent_ids)`.

    **F7 — Clinician-scientist indicators (NEW)**:
    Add F7 computation after F6. Only compute when query_type is `clinical_trial_pi`:
    ```python
    # F7: Clinician-scientist indicators
    f_raw["f7"] = []
    for c in candidates:
        # K-award grants (K08/K23/K24/K12/KL2 = clinician-scientist NIH mechanisms)
        k_award_count = sum(
            1 for gid in c.artifact_refs.grant_ids
            if any(gid.upper().startswith(prefix) for prefix in ("K08", "K23", "K24", "K12", "KL2"))
        )

        # CT.gov PI count
        ct_pi_count = len(c.artifact_refs.nct_ids)

        # Clinical site affiliation (hospital/medical center keywords)
        clinical_keywords = {"hospital", "medical center", "clinic", "health system", "school of medicine"}
        has_clinical_aff = 0.0
        for aff in c.affiliations:
            if any(kw in aff.canonical_name.lower() for kw in clinical_keywords):
                has_clinical_aff = 1.0
                break

        f7_raw = min(1.0, (k_award_count / 2.0 + ct_pi_count / 5.0 + has_clinical_aff) / 3.0)
        f_raw["f7"].append((c.uuid, f7_raw))
    ```

    Then update the percentile computation to include f7:
    ```python
    f_raw: dict[str, list[tuple[str, float]]] = {
        f"f{i}": [] for i in range(1, 8)  # was range(1, 7)
    }
    ```

    And update the quality prior to include f7 in the component dict:
    ```python
    component = {
        f"f{i}_rcr" if i == 1 else f"f{i}_funding" if i == 2 else f"f{i}_leadership" if i == 3 else f"f{i}_apex" if i == 4 else f"f{i}_translational" if i == 5 else f"f{i}_lineage" if i == 6 else f"f{i}_clinician": f_percentiles[f"f{i}"][c.uuid]
        for i in range(1, 8)  # was range(1, 7)
    }
    ```

    Also update the f_percentiles return to include f7:
    ```python
    # In execute(), update f7_scores:
    f7_scores=f_scores.get("f7"),
    ```

    ### 7. Wire HardGate.evaluate() per candidate

    Replace the hardcoded `is_zero=False` block (lines 167-175) with real evaluation:
    ```python
    # Step 6: Run integrity hard gate
    from aegis.integrity.hard_gate import HardGate

    hard_gate = HardGate(
        leie_store=self._leie_store,
        ofac_sam_store=self._ofac_sam_store,
        ori_store=self._ori_store,
        retraction_store=self._retraction_store,
    )

    integrity_results: dict[str, HardGateResult] = {}
    query_mesh_set = {m.lower() for m in mesh_terms}
    for c in all_candidates:
        candidate_name = c.name_variants[0] if c.name_variants else c.uuid
        candidate_mesh = {m.descriptor.lower() for m in c.mesh_descriptors}

        # Look up retraction notices for this candidate
        retraction_notices: list[dict[str, str]] = []
        rw_records = self._retraction_store.lookup_by_author(candidate_name)
        for rw in rw_records:
            retraction_notices.append({
                "pmid": rw.pmid or "",
                "title": rw.title,
                "reason": rw.reason or "",
            })

        result = hard_gate.evaluate(
            candidate_uuid=c.uuid,
            candidate_name=candidate_name,
            candidate_mesh=candidate_mesh if candidate_mesh else None,
            query_mesh=query_mesh_set if query_mesh_set else None,
            retraction_notices=retraction_notices if retraction_notices else None,
        )
        integrity_results[c.uuid] = result
    ```

    Also update the `CandidateScoreInput` construction to use the real integrity score:
    ```python
    integrity_score = 0.0 if integrity_results.get(c.uuid, HardGateResult(candidate_uuid=c.uuid, is_zero=False, reason=None, artifact_ref=None, rules_evaluated=0)).is_zero else 1.0
    ```

    And mark hard-zeroed candidates with `is_hard_zero=True` in `CandidateScoreInput` (if that field exists, otherwise set `integrity_score=0.0`).

    ## Files to modify
    - `src/aegis/pipeline/orchestrator.py` — Major rewrite as described above

    ## Code patterns to follow
    - `from __future__ import annotations` at top
    - All async generators wrapped in try/except
    - Defensive coding: every store lookup wrapped in try/except with logger.warning
    - Use `self._apex_store` and `self._*_store` consistently

    ## Acceptance criteria
    - `QueryPipeline.__init__()` accepts optional integrity and apex stores
    - Candidates filtered to `ingested_uuids` (current query only)
    - USPTO wired as 5th parallel source
    - CT.gov uses full `task_description` as query
    - iCite RCR enrichment runs after parallel fetch
    - F1 uses RCR when available
    - F4 uses apex roster lookup
    - F7 computed for clinician-scientist indicators
    - HardGate.evaluate() called per candidate
    - File compiles without errors

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/pipeline/orchestrator.py
    uv run python -c "
    from aegis.pipeline.orchestrator import QueryPipeline
    import inspect
    sig = inspect.signature(QueryPipeline.__init__)
    params = list(sig.parameters.keys())
    assert 'leie_store' in params, 'Missing leie_store param'
    assert 'apex_store' in params, 'Missing apex_store param'
    print('QueryPipeline accepts integrity and apex stores')
    "
    ```

### 11. Wire stores at startup and remove background refresh
- **Task ID**: server-startup-wiring
- **Role**: builder
- **Depends On**: orchestrator-rewrite, schema-query-type-override
- **Assigned To**: builder-2
- **Description**: |
    Update `src/aegis/api/server.py` to load integrity and apex stores at startup and pass them to `QueryPipeline`. Remove the no-op `_background_refresh` function and `lifespan`.

    ## What to do

    ### 1. Remove background refresh

    Delete the `_background_refresh()` async function (lines 55-70).
    Delete the `lifespan()` async context manager (lines 73-85).

    In `create_app()`, remove `lifespan=lifespan` from the `FastAPI()` constructor (line 100):
    ```python
    app = FastAPI(
        title="Aegis Expert Discovery API",
        version="1.0.0",
        description="Customer-facing query API for expert discovery and ranking",
        # lifespan removed — no-op background refresh deleted
    )
    ```

    Also remove the import of `RefreshOrchestrator` (line 57-58 inside `_background_refresh`).

    ### 2. Load integrity and apex stores at module level

    Add store loading at the top of `create_app()` or at module level. The stores should be loaded once and reused:

    ```python
    # At the top of the file, after existing imports:
    from aegis.integrity.data_loader import load_integrity_stores
    from aegis.ingestion.apex_loader import load_apex_rosters

    # Inside create_app(), before app creation:
    logger.info("Loading integrity stores...")
    try:
        _leie, _ofac_sam, _ori, _retraction = load_integrity_stores()
        logger.info("Integrity stores loaded: LEIE=%d, OFAC/SAM=%d, ORI=%d, Retractions=%d",
                     _leie.count(), _ofac_sam.count(), _ori.count(), _retraction.count())
    except Exception:
        logger.warning("Failed to load integrity stores, using empty stores", exc_info=True)
        from aegis.sources.leie import LEIEStore
        from aegis.sources.ofac_sam import OFACSAMStore
        from aegis.sources.ori import ORIStore
        from aegis.sources.retraction_watch import RetractionWatchStore
        _leie, _ofac_sam, _ori, _retraction = LEIEStore(), OFACSAMStore(), ORIStore(), RetractionWatchStore()

    logger.info("Loading apex roster stores...")
    try:
        _apex = load_apex_rosters()
    except Exception:
        logger.warning("Failed to load apex rosters, using empty store", exc_info=True)
        from aegis.sources.apex_rosters import ApexRosterStore
        _apex = ApexRosterStore()
    ```

    ### 3. Pass stores to QueryPipeline in _run_pipeline

    In the `_run_pipeline()` function, change:
    ```python
    pipeline = QueryPipeline()
    ```
    To:
    ```python
    pipeline = QueryPipeline(
        leie_store=_leie,
        ofac_sam_store=_ofac_sam,
        ori_store=_ori,
        retraction_store=_retraction,
        apex_store=_apex,
    )
    ```

    ### 4. Clean up imports

    Remove unused imports that were only needed by the deleted background refresh:
    - Remove `from aegis.ingestion.orchestrator import RefreshOrchestrator` if it exists at top level
    - The `asynccontextmanager` import from contextlib may still be needed by other code — only remove if unused
    - The `AsyncIterator` import may still be needed — only remove if unused

    ## Files to modify
    - `src/aegis/api/server.py` — Remove background refresh, load stores, pass to pipeline

    ## Code patterns to follow
    - Error handling: wrap store loading in try/except, fall back to empty stores
    - Logging: log store counts at startup
    - Use `from __future__ import annotations` (already present)

    ## Acceptance criteria
    - `_background_refresh()` function is deleted
    - `lifespan()` function is deleted
    - `FastAPI()` constructor does not reference `lifespan`
    - Integrity stores loaded at startup with error fallback
    - Apex roster loaded at startup with error fallback
    - `QueryPipeline()` receives all 5 stores
    - File compiles without errors

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/api/server.py
    uv run python -c "
    import inspect
    from aegis.api.server import create_app
    source = inspect.getsource(create_app)
    assert '_background_refresh' not in source, 'background refresh still referenced in create_app'
    print('server.py compiles and background refresh removed')
    "
    ```

### 12. Final validation
- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: remove-unused-sources, rewrite-init-files, reporter-project-title, integrity-data-loader, apex-roster-data, uspto-text-search, fix-evidence-trails, ingester-uuid-tracking, schema-query-type-override, orchestrator-rewrite, server-startup-wiring
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria.

    ## Validation Commands

    ### 1. Verify deleted files are gone
    ```bash
    test ! -f src/aegis/sources/abms.py && \
    test ! -f src/aegis/sources/chembl.py && \
    test ! -f src/aegis/sources/cursor.py && \
    test ! -f src/aegis/sources/drugs_fda.py && \
    test ! -f src/aegis/sources/epo.py && \
    test ! -f src/aegis/sources/epo_bulk.py && \
    test ! -f src/aegis/sources/erc.py && \
    test ! -f src/aegis/sources/cihr.py && \
    test ! -f src/aegis/sources/mrc.py && \
    test ! -f src/aegis/sources/nsfc.py && \
    test ! -f src/aegis/sources/nppes.py && \
    test ! -f src/aegis/sources/usnwr.py && \
    test ! -f src/aegis/sources/wipo.py && \
    test ! -f src/aegis/sources/non_us_grants.py && \
    test ! -d src/aegis/sources/conferences && \
    test ! -d src/aegis/sources/state_medical_boards && \
    test ! -f src/aegis/taxonomy/chembl_xwalk.py && \
    test ! -f src/aegis/observability/regional_coverage.py && \
    test ! -f src/aegis/observability/geographic_tracking.py && \
    echo "PASS: all unused files removed"
    ```

    ### 2. Verify module imports work
    ```bash
    uv run python -c "
    from aegis.sources import PubMedClient, ReporterClient, CtgovClient, IciteClient, UsptoClient
    from aegis.sources import LEIEStore, OFACSAMStore, ORIStore, RetractionWatchStore, ApexRosterStore
    from aegis.taxonomy import CpcMeshXwalk, Icd10MeshXwalk, CptMeshXwalk
    from aegis.sources.openalex import OpenAlexClient
    print('PASS: all imports work')
    "
    ```

    ### 3. Verify GrantRecord has project_title
    ```bash
    uv run python -c "
    from aegis.sources.reporter import GrantRecord
    assert 'project_title' in GrantRecord.model_fields
    print('PASS: GrantRecord has project_title')
    "
    ```

    ### 4. Verify integrity data loader
    ```bash
    uv run python -m py_compile src/aegis/integrity/data_loader.py
    uv run python -c "from aegis.integrity.data_loader import load_integrity_stores; print('PASS: data_loader imports')"
    ```

    ### 5. Verify apex roster loader
    ```bash
    uv run python -c "
    from aegis.ingestion.apex_loader import load_apex_rosters
    store = load_apex_rosters()
    assert store.count() > 50, f'Expected >50 apex members, got {store.count()}'
    print(f'PASS: apex roster loaded {store.count()} members')
    "
    ```

    ### 6. Verify USPTO search_by_text
    ```bash
    uv run python -c "
    from aegis.sources.uspto import UsptoClient
    assert hasattr(UsptoClient, 'search_by_text')
    print('PASS: UsptoClient has search_by_text')
    "
    ```

    ### 7. Verify patent converter
    ```bash
    uv run python -c "
    from aegis.ingestion.converters import patent_record_to_candidates
    print('PASS: patent converter importable')
    "
    ```

    ### 8. Verify ingested_uuids tracking
    ```bash
    uv run python -c "
    import inspect
    from aegis.ingestion.record_ingester import RecordIngester
    source = inspect.getsource(RecordIngester)
    assert 'ingested_uuids' in source
    print('PASS: ingested_uuids tracking exists')
    "
    ```

    ### 9. Verify schema has query_type_override
    ```bash
    uv run python -c "
    from aegis.api.schemas import QueryRequest
    assert 'query_type_override' in QueryRequest.model_fields
    print('PASS: QueryRequest has query_type_override')
    "
    ```

    ### 10. Verify orchestrator accepts stores
    ```bash
    uv run python -c "
    import inspect
    from aegis.pipeline.orchestrator import QueryPipeline
    sig = inspect.signature(QueryPipeline.__init__)
    params = list(sig.parameters.keys())
    assert 'leie_store' in params
    assert 'apex_store' in params
    print('PASS: QueryPipeline accepts stores')
    "
    ```

    ### 11. Verify server compiles without background refresh
    ```bash
    uv run python -m py_compile src/aegis/api/server.py
    uv run python -c "
    import inspect
    import aegis.api.server as mod
    source = inspect.getsource(mod)
    assert '_background_refresh' not in source or 'def _background_refresh' not in source
    print('PASS: background refresh removed')
    "
    ```

    ### 12. Compile all modified files
    ```bash
    uv run python -m py_compile src/aegis/sources/reporter.py
    uv run python -m py_compile src/aegis/sources/uspto.py
    uv run python -m py_compile src/aegis/sources/openalex.py
    uv run python -m py_compile src/aegis/sources/__init__.py
    uv run python -m py_compile src/aegis/ingestion/converters.py
    uv run python -m py_compile src/aegis/ingestion/record_ingester.py
    uv run python -m py_compile src/aegis/ingestion/apex_loader.py
    uv run python -m py_compile src/aegis/pipeline/orchestrator.py
    uv run python -m py_compile src/aegis/api/schemas.py
    uv run python -m py_compile src/aegis/api/server.py
    uv run python -m py_compile src/aegis/integrity/data_loader.py
    uv run python -m py_compile src/aegis/taxonomy/__init__.py
    echo "PASS: all files compile"
    ```

    ### 13. Run existing tests to check for regressions
    ```bash
    uv run pytest src/aegis/sources/pubmed_test.py src/aegis/sources/reporter_test.py src/aegis/sources/ctgov_test.py src/aegis/sources/icite_test.py src/aegis/sources/uspto_test.py src/aegis/sources/leie_test.py src/aegis/sources/ofac_sam_test.py src/aegis/sources/ori_test.py src/aegis/sources/retraction_watch_test.py src/aegis/sources/apex_rosters_test.py -x --tb=short 2>&1 | tail -20
    ```

    ### 14. Check for broken imports across codebase
    ```bash
    uv run python -c "
    import importlib
    modules = [
        'aegis.sources',
        'aegis.taxonomy',
        'aegis.ingestion.converters',
        'aegis.ingestion.record_ingester',
        'aegis.ingestion.apex_loader',
        'aegis.integrity.data_loader',
        'aegis.pipeline.orchestrator',
        'aegis.api.schemas',
        'aegis.api.server',
    ]
    for m in modules:
        try:
            importlib.import_module(m)
            print(f'  OK: {m}')
        except Exception as e:
            print(f'  FAIL: {m} — {e}')
    "
    ```

    ## Acceptance Criteria
    - All unused files and directories deleted
    - All __init__.py files only import kept modules
    - GrantRecord has project_title field
    - Integrity data loader exists and imports
    - Apex roster YAML files exist with >50 members total
    - UsptoClient has search_by_text method
    - patent_record_to_candidates converter exists
    - RecordIngester tracks ingested_uuids
    - QueryRequest has query_type_override field
    - QueryPipeline accepts integrity and apex stores
    - Server compiles without background refresh
    - All modified Python files compile
    - Existing tests for kept sources still pass
    - No broken imports across the codebase

## Acceptance Criteria

1. **Scoring isolation**: Candidates scored per-query, not globally across all past queries
2. **Reporter topical_fit > 0**: Evidence trail includes project title, enabling word-overlap scoring
3. **F1 with RCR**: iCite enrichment fetches RCR for all PMIDs, used in F1 computation
4. **F2 with international grants**: OpenAlex grant extraction populates grant_ids from raw_json
5. **F3 multi-source PI credit**: PubMed and Reporter evidence trails include "Principal Investigator"
6. **F4 with real apex data**: ApexRosterStore populated from YAML, lookup used in F4
7. **F5 with patents**: USPTO text search wired as 5th parallel source, patent_ids populated
8. **F7 computed**: K-awards, CT.gov PI count, and clinical affiliation used for clinician-scientist indicator
9. **Integrity gate live**: HardGate.evaluate() runs per candidate using loaded LEIE/OFAC/ORI/Retraction Watch stores
10. **CT.gov precision**: Uses full task_description instead of mesh_terms[0]
11. **Query type override wired**: Frontend dropdown -> POST body -> backend pipeline
12. **Dead code removed**: ~30 unused source files, conferences/, state_medical_boards/ deleted
13. **Background refresh removed**: No-op lifespan task deleted from server.py
14. **All files compile**: `uv run python -m py_compile` passes on all modified files
15. **Existing tests pass**: Tests for kept sources (pubmed, reporter, ctgov, icite, uspto, leie, ofac_sam, ori, retraction_watch, apex_rosters) still pass

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# 1. Verify unused files deleted
test ! -d src/aegis/sources/conferences && test ! -d src/aegis/sources/state_medical_boards && test ! -f src/aegis/sources/chembl.py && echo "Unused files removed"

# 2. Verify all imports work
uv run python -c "from aegis.sources import PubMedClient, ReporterClient, CtgovClient, IciteClient, UsptoClient, LEIEStore, OFACSAMStore, ORIStore, RetractionWatchStore, ApexRosterStore; print('imports OK')"

# 3. Verify all files compile
uv run python -m py_compile src/aegis/sources/reporter.py && \
uv run python -m py_compile src/aegis/sources/uspto.py && \
uv run python -m py_compile src/aegis/sources/openalex.py && \
uv run python -m py_compile src/aegis/sources/__init__.py && \
uv run python -m py_compile src/aegis/ingestion/converters.py && \
uv run python -m py_compile src/aegis/ingestion/record_ingester.py && \
uv run python -m py_compile src/aegis/ingestion/apex_loader.py && \
uv run python -m py_compile src/aegis/pipeline/orchestrator.py && \
uv run python -m py_compile src/aegis/api/schemas.py && \
uv run python -m py_compile src/aegis/api/server.py && \
uv run python -m py_compile src/aegis/integrity/data_loader.py && \
echo "All files compile"

# 4. Run existing tests
uv run pytest src/aegis/sources/pubmed_test.py src/aegis/sources/reporter_test.py src/aegis/sources/ctgov_test.py src/aegis/sources/icite_test.py src/aegis/sources/uspto_test.py src/aegis/sources/leie_test.py src/aegis/sources/ofac_sam_test.py src/aegis/sources/ori_test.py src/aegis/sources/retraction_watch_test.py src/aegis/sources/apex_rosters_test.py -x --tb=short

# 5. Verify key features
uv run python -c "
from aegis.sources.reporter import GrantRecord
assert 'project_title' in GrantRecord.model_fields

from aegis.sources.uspto import UsptoClient
assert hasattr(UsptoClient, 'search_by_text')

from aegis.ingestion.converters import patent_record_to_candidates

from aegis.api.schemas import QueryRequest
assert 'query_type_override' in QueryRequest.model_fields

import inspect
from aegis.pipeline.orchestrator import QueryPipeline
sig = inspect.signature(QueryPipeline.__init__)
assert 'leie_store' in sig.parameters
assert 'apex_store' in sig.parameters

from aegis.ingestion.apex_loader import load_apex_rosters
store = load_apex_rosters()
assert store.count() > 50

print('All key features verified')
"
```

## Notes

- **No new libraries needed** — all dependencies (httpx, pydantic, yaml, duckdb) are already in the project
- **Integrity data downloads are best-effort** — if downloads fail at startup, the server continues with empty stores. This is acceptable for development; production should alert on empty stores.
- **Apex roster YAML files** are populated with real, publicly known members from public record. These are static and can be updated manually.
- **F7 computation** only runs for `clinical_trial_pi` query type but the f_raw dict always includes it. The weight vector's `f7_clinician` weight will be 0 for non-clinical query types, effectively disabling it.
- **The `ingested_uuids` fix** is the single most impactful change. Without it, the global DB accumulates candidates across queries and F1 percentiles are computed across the entire historical pool, causing researchers with many past publications to dominate.
- **CT.gov query fix** changes from `mesh_terms[0]` (e.g., "Lung Cancer" — returns ALL lung cancer trials) to full `task_description` (e.g., "KRAS G12C mutation clinical trials investigator" — returns targeted trials).
- **OpenAlex `get_grants_by_funder()` removal** is safe because this method was never called from the pipeline. International grants are now captured via the `grants` array in OpenAlex work records, extracted by the converter.
