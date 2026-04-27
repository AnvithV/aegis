# Plan: Phase 2a — Patent Ingestion (USPTO + EPO + Cross-walks + Bulk)

> **Status:** COMPLETE (2026-04-26)
> All 7 tasks completed. 27/27 tests passing. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-26
> **Team:** aegis-phase2ab-20260426-1700

### Test Results
- uspto_test.py — 5/5 PASSED
- epo_test.py — 5/5 PASSED
- cpc_mesh_test.py — 6/6 PASSED
- chembl_xwalk_test.py — 5/5 PASSED
- patent_bulk_test.py — 6/6 PASSED
- storage/ (existing) — 22/22 PASSED (no regression)

### Validation Commands
- `uv run pytest ... -v` (Phase 2a tests) — PASS (27/27 tests passed in 0.28s)
- `uv run mypy ...` — PASS (no issues found in 7 source files)
- `uv run ruff check ...` — PASS (all checks passed)
- `uv run pytest src/aegis/storage/ -v` — PASS (22/22 existing storage tests passed)
- `uv run python -c "... CpcMeshXwalk ... curated_count ..."` — PASS (46 entries)

### Acceptance Criteria Verification
- [x] UsptoClient at src/aegis/sources/uspto.py — VERIFIED (class importable, 5 tests pass)
- [x] EpoClient at src/aegis/sources/epo.py — VERIFIED (class importable, 5 tests pass)
- [x] CpcMeshXwalk at src/aegis/taxonomy/cpc_mesh_xwalk.py — VERIFIED (class importable, curated YAML with 46 entries >= 40, 6 tests pass)
- [x] ChemblXwalk at src/aegis/taxonomy/chembl_xwalk.py — VERIFIED (class importable, 5 tests pass)
- [x] UsptoBulkIngestor and EpoBulkIngestor exist — VERIFIED (both importable from sources, 6 bulk tests pass)
- [x] ArtifactRefBundle.patent_ids field exists — VERIFIED (field present in model_fields: ['pmids', 'nct_ids', 'grant_ids', 'patent_ids'])
- [x] Migration 003_patent_refs.sql exists — VERIFIED (file at src/aegis/storage/migrations/003_patent_refs.sql)
- [x] All new tests pass — VERIFIED (27/27 passed)
- [x] mypy strict mode passes — VERIFIED (0 issues in 7 files)
- [x] ruff lint passes — VERIFIED (all checks passed)
- [x] No existing Phase 0/1 tests broken — VERIFIED (22/22 storage tests pass)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| src/aegis/taxonomy/__init__.py | Created | Yes |
| src/aegis/taxonomy/cpc_mesh_xwalk.py | Created | Yes |
| src/aegis/taxonomy/cpc_mesh_test.py | Created | Yes |
| src/aegis/taxonomy/chembl_xwalk.py | Created | Yes |
| src/aegis/taxonomy/chembl_xwalk_test.py | Created | Yes |
| data/aegis/cpc_mesh_xwalk_v1.yaml | Created | Yes |
| src/aegis/sources/uspto.py | Created | Yes |
| src/aegis/sources/uspto_test.py | Created | Yes |
| src/aegis/sources/epo.py | Created | Yes |
| src/aegis/sources/epo_test.py | Created | Yes |
| src/aegis/sources/chembl.py | Created | Yes |
| src/aegis/sources/uspto_bulk.py | Created | Yes |
| src/aegis/sources/epo_bulk.py | Created | Yes |
| src/aegis/sources/patent_bulk_test.py | Created | Yes |
| src/aegis/storage/schema.py | Modified | Yes |
| src/aegis/storage/migrations/003_patent_refs.sql | Created | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase2a-patent-ingestion.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build the full patent ingestion pipeline for Aegis Phase 2, covering USPTO PatentsView, EPO Espacenet, CPC/IPC-to-MeSH cross-walk, ChEMBL target-to-MeSH cross-walk, and bulk/volume-scale ingestion for historical patent pulls. This sub-spec produces the data foundation for the drug-discovery population: patent records with inventor-level attribution, CPC classification codes translated into the same MeSH vector space used by PubMed papers, and ChEMBL bioactivity targets mapped to MeSH for chemistry-oriented queries.

This plan covers Phase 2 tasks: **1.1** (USPTO PatentsView), **1.2** (EPO Espacenet), **1.3** (CPC/MeSH cross-walk), **1.4** (ChEMBL target cross-walk), and **4.1** (patent ingestion volume/bulk).

## Objective

When this plan is complete:
1. A `UsptoClient` exists at `src/aegis/sources/uspto.py` with typed `PatentRecord` and `InventorAttribution` models, returning patents by CPC code and date range via the PatentsView API, with inventor disambiguation IDs.
2. An `EpoClient` exists at `src/aegis/sources/epo.py` returning EP patents via the OPS API, with patent-family deduplication against USPTO records.
3. A `CpcMeshXwalk` exists at `src/aegis/taxonomy/cpc_mesh_xwalk.py` with a curated YAML mapping for ~500 high-priority CPC codes and an LLM fallback for tail codes, translating CPC/IPC codes to weighted MeSH descriptors.
4. A `ChemblXwalk` exists at `src/aegis/taxonomy/chembl_xwalk.py` mapping ChEMBL target IDs to MeSH descriptors via UniProt/pathway/disease associations, plus a `ChemblIngestor` for bulk SQLite dump ingestion.
5. Bulk ingestion modules exist at `src/aegis/sources/uspto_bulk.py` and `src/aegis/sources/epo_bulk.py` capable of processing ~10M patents in <72 hours with daily incremental refresh <30 min.
6. All modules pass mypy strict, ruff lint, and have unit tests.

## Problem Statement

Phase 1 scoring treats translational candidates only and explicitly excludes patents (`f5_translational.py` has coverage caveat: "Phase 1: patents excluded; Phase 2 will include patent linkage"). The drug-discovery population is patent-dominant — medicinal chemists may have 50+ patents and zero PubMed papers. Without patent ingestion and CPC-to-MeSH translation, these candidates cannot be scored. Additionally, ChEMBL target-to-MeSH mapping is needed so chemistry queries (e.g., "JAK2 inhibitor") expand into the same vector space as biological queries. The bulk pipeline must handle 10M+ patents at historical scale.

## Solution Approach

1. **USPTO client first**: Build the PatentsView API client with typed models, then the EPO client with family-level deduplication.
2. **Taxonomy layer**: Create `src/aegis/taxonomy/` package with CPC-MeSH and ChEMBL-MeSH cross-walks. The CPC cross-walk uses a curated YAML for high-frequency codes plus an LLM-constrained-generation fallback for the long tail.
3. **Bulk ingestion**: USPTO bulk dumps (Google Cloud / Bulk Data Storage System) and EPO bulk feeds for historical pulls, with streaming parsers and parallelized processing.
4. **Testing**: Fixture-based tests with no live API calls; mock responses for USPTO, EPO, and ChEMBL.

## Relevant Files

### Existing Files (read-only context, do not modify unless noted)
- `src/aegis/storage/schema.py` — `Candidate`, `MeshDescriptor`, `ArtifactRefBundle` models (may need extension for patent refs)
- `src/aegis/storage/candidate_store.py` — `CandidateStore` DuckDB-backed API
- `src/aegis/sources/retry.py` — `RetryPolicy`, `RetryConfig` for HTTP clients
- `src/aegis/sources/pubmed.py` — Pattern reference for typed API client (httpx + Pydantic + RetryPolicy)
- `src/aegis/sources/__init__.py` — Source package exports (will be modified to add new exports)
- `src/aegis/scoring/f5_translational.py` — F5 sub-score (references patent caveat, will be extended in Phase 2c)
- `pyproject.toml` — Project configuration (may need new dependencies)

### New Files
- `src/aegis/sources/uspto.py` — USPTO PatentsView API client
- `src/aegis/sources/uspto_test.py` — USPTO client tests
- `src/aegis/sources/epo.py` — EPO Espacenet OPS API client
- `src/aegis/sources/epo_test.py` — EPO client tests
- `src/aegis/sources/uspto_bulk.py` — USPTO bulk dump ingestion
- `src/aegis/sources/epo_bulk.py` — EPO bulk feed ingestion
- `src/aegis/sources/patent_bulk_test.py` — Bulk ingestion tests
- `src/aegis/taxonomy/__init__.py` — Taxonomy package init
- `src/aegis/taxonomy/cpc_mesh_xwalk.py` — CPC/IPC to MeSH cross-walk
- `src/aegis/taxonomy/cpc_mesh_test.py` — CPC-MeSH cross-walk tests
- `src/aegis/taxonomy/chembl_xwalk.py` — ChEMBL target to MeSH cross-walk
- `src/aegis/sources/chembl.py` — ChEMBL bulk SQLite ingestion
- `src/aegis/taxonomy/chembl_xwalk_test.py` — ChEMBL cross-walk tests
- `data/aegis/cpc_mesh_xwalk_v1.yaml` — Curated CPC-to-MeSH mapping (~500 codes)

## Implementation Phases

### Phase 1: Foundation
- Create `src/aegis/taxonomy/` package structure
- Build USPTO PatentsView client with typed models
- Build EPO OPS client with patent-family linking

### Phase 2: Core Implementation
- Build CPC-MeSH cross-walk (curated YAML + LLM fallback)
- Build ChEMBL target-MeSH cross-walk and bulk ingestor
- Build bulk ingestion modules for USPTO and EPO

### Phase 3: Integration & Polish
- Wire patent refs into ArtifactRefBundle (schema extension)
- Update source package exports
- Run full validation suite

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: USPTO client, EPO client, patent-family deduplication, bulk ingestion modules, schema extension for patent refs
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Taxonomy package, CPC-MeSH cross-walk (curated YAML + LLM fallback), ChEMBL cross-walk, ChEMBL bulk ingestor
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Spec Updater
  - Name: spec-updater
  - Role: Re-runs validations after build, writes Build Evidence into this spec
  - Agent Type: spec-updater

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build`.
- Task descriptions must be **exhaustive** — agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Start with foundational work, then core implementation, then validation.

### 1. Scaffold Taxonomy Package + Extend Schema for Patents

- **Task ID**: scaffold-taxonomy
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the taxonomy package structure and extend the storage schema to support patent artifact references.

    ## What to do

    1. Create `src/aegis/taxonomy/__init__.py`:
       ```python
       """Aegis taxonomy cross-walks: CPC-MeSH, ChEMBL-MeSH, ICD-10-MeSH, CPT-MeSH."""

       from __future__ import annotations
       ```

    2. Extend `src/aegis/storage/schema.py` to support patent references. Add a new field to `ArtifactRefBundle`:
       - Add `patent_ids: list[str]` to `ArtifactRefBundle` (patent numbers, e.g., "US10123456B2", "EP3456789A1")
       - This is a list of patent document numbers that link the candidate to their patent portfolio

       The existing `ArtifactRefBundle` has: `pmids`, `nct_ids`, `grant_ids`. Add `patent_ids` as a new field with default `[]`.

       **IMPORTANT**: The `ArtifactRefBundle` model uses `ConfigDict(frozen=True)`. Add the field with a default value:
       ```python
       patent_ids: list[str] = []
       ```

    3. Create a new DDL migration `src/aegis/storage/migrations/003_patent_refs.sql`:
       ```sql
       -- Patent artifact references table
       CREATE TABLE IF NOT EXISTS patent_refs (
           patent_id TEXT NOT NULL,
           candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
           source TEXT NOT NULL,  -- 'uspto' or 'epo'
           family_id TEXT,        -- DOCDB family ID for deduplication
           PRIMARY KEY (patent_id, candidate_uuid)
       );

       CREATE INDEX IF NOT EXISTS idx_patent_refs_candidate ON patent_refs(candidate_uuid);
       CREATE INDEX IF NOT EXISTS idx_patent_refs_family ON patent_refs(family_id);
       ```

    4. Update `src/aegis/storage/candidate_store.py` to run migration 003 on init (add it to the migration list alongside 001 and 002).

    ## Files to create
    - `src/aegis/taxonomy/__init__.py`
    - `src/aegis/storage/migrations/003_patent_refs.sql`

    ## Files to modify
    - `src/aegis/storage/schema.py` — add `patent_ids: list[str] = []` to `ArtifactRefBundle`
    - `src/aegis/storage/candidate_store.py` — run migration 003

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - DuckDB raw SQL for migrations (same pattern as `001_initial.sql` and `002_indexes.sql`)
    - Look at how `candidate_store.py` currently runs migrations (reads and executes SQL files from `migrations/` directory)

    ## Acceptance criteria
    - `src/aegis/taxonomy/__init__.py` exists and is importable
    - `ArtifactRefBundle` has `patent_ids` field
    - Migration `003_patent_refs.sql` exists with `patent_refs` table DDL
    - Existing tests still pass: `uv run pytest src/aegis/storage/ -v`
    - mypy passes: `uv run mypy src/aegis/storage/schema.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.taxonomy import *; print('Taxonomy package OK')" && uv run python -c "from aegis.storage.schema import ArtifactRefBundle; assert 'patent_ids' in ArtifactRefBundle.model_fields; print('patent_ids field OK')" && uv run pytest src/aegis/storage/ -v && uv run mypy src/aegis/storage/schema.py
    ```

### 2. USPTO PatentsView API Client

- **Task ID**: uspto-client
- **Role**: builder
- **Depends On**: scaffold-taxonomy
- **Assigned To**: builder-1
- **Description**: |
    Build a typed client for the USPTO PatentsView API returning granted US patents with full inventor attribution and CPC classification.

    ## What to do

    1. Create `src/aegis/sources/uspto.py` with the following models and client:

       ```python
       """USPTO PatentsView API client for patent ingestion."""

       from __future__ import annotations

       import logging
       from collections.abc import AsyncIterator
       from datetime import date

       import httpx
       from pydantic import BaseModel, ConfigDict

       from aegis.sources.retry import RetryConfig, RetryPolicy

       logger = logging.getLogger(__name__)

       PATENTSVIEW_API_URL = "https://api.patentsview.org/patents/query"


       class InventorAttribution(BaseModel):
           """An inventor listed on a patent."""

           model_config = ConfigDict(frozen=True)

           inventor_id: str          # PatentsView disambiguated inventor ID
           full_name: str
           first_name: str | None
           last_name: str | None
           is_lead_inventor: bool    # First-listed inventor (position 0)


       class PatentAssignee(BaseModel):
           """Assignee (organization or individual) on a patent."""

           model_config = ConfigDict(frozen=True)

           assignee_id: str | None
           organization: str | None
           assignee_type: str        # "organization" or "individual"


       class PatentRecord(BaseModel):
           """Structured representation of a granted US patent."""

           model_config = ConfigDict(frozen=True)

           patent_number: str                 # e.g., "US10123456B2"
           grant_date: date | None
           application_date: date | None
           title: str
           abstract: str | None
           claims_text: str | None            # First independent claim text
           inventors: list[InventorAttribution]
           assignees: list[PatentAssignee]
           cpc_codes: list[str]               # e.g., ["A61K31/00", "C07D401/12"]
           ipc_codes: list[str]               # IPC classification codes
           forward_citation_count: int
           family_id: str | None              # DOCDB family ID for dedup
           maintenance_status: str | None      # "maintained" / "lapsed" / None


       class UsptoClient:
           """Typed client wrapping the PatentsView API."""

           def __init__(
               self,
               retry_policy: RetryPolicy | None = None,
           ) -> None:
               self._retry = retry_policy or RetryPolicy(RetryConfig())

           async def fetch_patents(
               self,
               cpc_codes: list[str],
               since: date,
               batch_size: int = 100,
           ) -> AsyncIterator[PatentRecord]:
               """Fetch patents matching CPC codes granted since a given date.

               Uses PatentsView query API with pagination.
               Yields PatentRecord objects.
               """
               # Build PatentsView query filter
               cpc_filter = [{"cpc_subgroup_id": cpc} for cpc in cpc_codes]
               query = {
                   "_and": [
                       {"_or": cpc_filter},
                       {"_gte": {"patent_date": since.isoformat()}},
                   ]
               }
               fields = [
                   "patent_number", "patent_date", "patent_title",
                   "patent_abstract", "patent_firstnamed_inventor_id",
                   "patent_num_cited_by_us_patents",
               ]
               inventor_fields = [
                   "inventor_id", "inventor_first_name",
                   "inventor_last_name", "inventor_sequence",
               ]
               assignee_fields = [
                   "assignee_id", "assignee_organization",
                   "assignee_type",
               ]
               cpc_fields = ["cpc_subgroup_id"]

               page = 1
               async with httpx.AsyncClient(timeout=60.0) as client:
                   while True:
                       payload = {
                           "q": query,
                           "f": fields,
                           "o": {"page": page, "per_page": batch_size},
                           "s": [{"patent_date": "desc"}],
                       }

                       async def _do_post(p: dict = payload) -> httpx.Response:
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

                       # Check if there are more pages
                       total = body.get("total_patent_count", 0)
                       if page * batch_size >= total:
                           break
                       page += 1

           @staticmethod
           def _parse_patent(data: dict) -> PatentRecord | None:
               """Parse a PatentsView API response into a PatentRecord."""
               try:
                   inventors = []
                   for inv in (data.get("inventors") or []):
                       inventors.append(InventorAttribution(
                           inventor_id=inv.get("inventor_id", ""),
                           full_name=f"{inv.get('inventor_first_name', '')} {inv.get('inventor_last_name', '')}".strip(),
                           first_name=inv.get("inventor_first_name"),
                           last_name=inv.get("inventor_last_name"),
                           is_lead_inventor=inv.get("inventor_sequence", 1) == 0,
                       ))

                   assignees = []
                   for asg in (data.get("assignees") or []):
                       assignees.append(PatentAssignee(
                           assignee_id=asg.get("assignee_id"),
                           organization=asg.get("assignee_organization"),
                           assignee_type="organization" if asg.get("assignee_type", 0) in (2, 3) else "individual",
                       ))

                   cpc_codes = [
                       c.get("cpc_subgroup_id", "")
                       for c in (data.get("cpcs") or [])
                       if c.get("cpc_subgroup_id")
                   ]

                   grant_date = None
                   if data.get("patent_date"):
                       grant_date = date.fromisoformat(data["patent_date"])

                   return PatentRecord(
                       patent_number=data.get("patent_number", ""),
                       grant_date=grant_date,
                       application_date=None,  # Not always in API response
                       title=data.get("patent_title", ""),
                       abstract=data.get("patent_abstract"),
                       claims_text=None,
                       inventors=inventors,
                       assignees=assignees,
                       cpc_codes=cpc_codes,
                       ipc_codes=[],
                       forward_citation_count=data.get("patent_num_cited_by_us_patents", 0),
                       family_id=None,
                       maintenance_status=None,
                   )
               except (KeyError, ValueError, TypeError):
                   logger.warning("Failed to parse patent: %s", data.get("patent_number", "?"))
                   return None
       ```

    2. Create `src/aegis/sources/uspto_test.py` with fixture-based tests (no live API calls):
       - `test_patent_record_parse`: Create a mock PatentsView API response dict, pass to `_parse_patent`, verify all fields parse correctly
       - `test_inventor_lead_detection`: Mock patent with 3 inventors, verify `is_lead_inventor` is True only for sequence=0
       - `test_fetch_patents_pagination`: Use `respx` to mock two pages of results, verify all patents are yielded
       - `test_parse_patent_missing_fields`: Mock patent missing optional fields (abstract, claims), verify parsing succeeds with None values
       - `test_cpc_code_extraction`: Mock patent with 4 CPC codes, verify all are extracted

       Use `respx` for HTTP mocking, `@pytest.mark.asyncio(strict=True)` for async tests.

    3. Update `src/aegis/sources/__init__.py` to add exports: `UsptoClient`, `PatentRecord`, `InventorAttribution`, `PatentAssignee`.

    ## Files to create
    - `src/aegis/sources/uspto.py`
    - `src/aegis/sources/uspto_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add USPTO exports

    ## Code patterns to follow
    - Follow exact patterns from `src/aegis/sources/pubmed.py`:
      - `from __future__ import annotations`
      - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
      - `RetryPolicy` integration via constructor injection
      - `AsyncIterator` return type for paginated methods
      - `httpx.AsyncClient` with timeout
      - Logger at module level: `logger = logging.getLogger(__name__)`
    - Test patterns from `src/aegis/sources/pubmed_test.py` and `src/aegis/sources/icite_test.py`:
      - `respx` for HTTP mocking
      - `@pytest.mark.asyncio(strict=True)` decorator

    ## Acceptance criteria
    - `src/aegis/sources/uspto.py` exists and exports `UsptoClient`, `PatentRecord`, `InventorAttribution`
    - `PatentRecord` has fields: `patent_number`, `grant_date`, `inventors`, `cpc_codes`, `forward_citation_count`, `family_id`
    - `InventorAttribution` has: `inventor_id`, `full_name`, `is_lead_inventor`
    - Design assertion: `UsptoClient.fetch_patents(cpc_codes: list[str], since: date) -> AsyncIterator[PatentRecord]`
    - All tests pass: `uv run pytest src/aegis/sources/uspto_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/uspto.py`
    - ruff passes: `uv run ruff check src/aegis/sources/uspto.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/uspto_test.py -v && uv run mypy src/aegis/sources/uspto.py && uv run ruff check src/aegis/sources/uspto.py
    ```

### 3. EPO Espacenet OPS API Client

- **Task ID**: epo-client
- **Role**: builder
- **Depends On**: scaffold-taxonomy
- **Assigned To**: builder-1
- **Description**: |
    Build a typed client for the European Patent Office Espacenet via the OPS (Open Patent Services) API, covering EP applications and grants with patent-family-level deduplication against USPTO records.

    ## What to do

    1. Create `src/aegis/sources/epo.py` with the following models and client:

       ```python
       """EPO Espacenet OPS API client for European patent ingestion."""

       from __future__ import annotations

       import logging
       from collections.abc import AsyncIterator
       from datetime import date

       import httpx
       from pydantic import BaseModel, ConfigDict

       from aegis.sources.retry import RetryConfig, RetryPolicy
       from aegis.sources.uspto import PatentRecord, InventorAttribution, PatentAssignee

       logger = logging.getLogger(__name__)

       OPS_API_URL = "https://ops.epo.org/3.2/rest-services"
       OPS_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"


       class EpoCredentials(BaseModel):
           """OAuth2 credentials for EPO OPS API."""

           model_config = ConfigDict(frozen=True)

           consumer_key: str
           consumer_secret: str


       class PatentFamily(BaseModel):
           """Patent family grouping (DOCDB family)."""

           model_config = ConfigDict(frozen=True)

           family_id: str
           members: list[str]  # Patent document numbers in this family


       class EpoClient:
           """Typed client wrapping EPO Open Patent Services API."""

           def __init__(
               self,
               credentials: EpoCredentials | None = None,
               retry_policy: RetryPolicy | None = None,
           ) -> None:
               self._credentials = credentials
               self._retry = retry_policy or RetryPolicy(RetryConfig())
               self._access_token: str | None = None

           async def _ensure_token(self, client: httpx.AsyncClient) -> str:
               """Obtain or refresh OAuth2 access token."""
               if self._access_token is not None:
                   return self._access_token
               if self._credentials is None:
                   raise ValueError("EPO credentials required for API access")
               resp = await client.post(
                   OPS_AUTH_URL,
                   data={"grant_type": "client_credentials"},
                   auth=(self._credentials.consumer_key, self._credentials.consumer_secret),
               )
               resp.raise_for_status()
               self._access_token = resp.json()["access_token"]
               return self._access_token

           async def fetch_patents(
               self,
               cpc_codes: list[str],
               since: date,
               batch_size: int = 100,
           ) -> AsyncIterator[PatentRecord]:
               """Fetch EP patents matching CPC codes published since a given date.

               Reuses PatentRecord from the USPTO module for uniform downstream handling.
               Yields PatentRecord objects with source-specific fields.
               """
               async with httpx.AsyncClient(timeout=60.0) as client:
                   token = await self._ensure_token(client)
                   headers = {"Authorization": f"Bearer {token}"}

                   for cpc in cpc_codes:
                       query = f'cpc={cpc} and pd>={since.strftime("%Y%m%d")}'
                       start = 1
                       while True:
                           end = start + batch_size - 1
                           url = f"{OPS_API_URL}/published-data/search"

                           async def _do_get(
                               q: str = query, s: int = start, e: int = end
                           ) -> httpx.Response:
                               resp = await client.get(
                                   url,
                                   params={"q": q, "Range": f"{s}-{e}"},
                                   headers=headers,
                               )
                               resp.raise_for_status()
                               return resp

                           try:
                               response = await self._retry.execute(_do_get)
                           except httpx.HTTPStatusError as exc:
                               if exc.response.status_code == 404:
                                   break  # No more results
                               raise

                           records = self._parse_ops_response(response.json())
                           if not records:
                               break

                           for record in records:
                               yield record

                           if len(records) < batch_size:
                               break
                           start += batch_size

           async def get_patent_family(
               self,
               patent_number: str,
               client: httpx.AsyncClient | None = None,
           ) -> PatentFamily | None:
               """Look up the DOCDB family for a patent number."""
               should_close = client is None
               if client is None:
                   client = httpx.AsyncClient(timeout=30.0)
               try:
                   token = await self._ensure_token(client)
                   url = f"{OPS_API_URL}/family/publication/docdb/{patent_number}"
                   resp = await client.get(
                       url,
                       headers={"Authorization": f"Bearer {token}"},
                   )
                   if resp.status_code == 404:
                       return None
                   resp.raise_for_status()
                   body = resp.json()
                   # Parse family members from response
                   members = self._extract_family_members(body)
                   family_id = body.get("ops:world-patent-data", {}).get(
                       "ops:patent-family", {}
                   ).get("@family-id", patent_number)
                   return PatentFamily(family_id=str(family_id), members=members)
               finally:
                   if should_close:
                       await client.aclose()

           @staticmethod
           def _parse_ops_response(data: dict) -> list[PatentRecord]:
               """Parse OPS search response into PatentRecord objects."""
               records: list[PatentRecord] = []
               search_result = data.get("ops:world-patent-data", {}).get(
                   "ops:biblio-search", {}
               ).get("ops:search-result", {}).get("ops:publication-reference", [])

               if isinstance(search_result, dict):
                   search_result = [search_result]

               for pub_ref in search_result:
                   doc_id = pub_ref.get("document-id", {})
                   patent_number = f"EP{doc_id.get('doc-number', '')}{doc_id.get('kind', '')}"

                   records.append(PatentRecord(
                       patent_number=patent_number,
                       grant_date=None,
                       application_date=None,
                       title="",
                       abstract=None,
                       claims_text=None,
                       inventors=[],
                       assignees=[],
                       cpc_codes=[],
                       ipc_codes=[],
                       forward_citation_count=0,
                       family_id=None,
                       maintenance_status=None,
                   ))

               return records

           @staticmethod
           def _extract_family_members(data: dict) -> list[str]:
               """Extract member patent numbers from family lookup response."""
               members: list[str] = []
               family = data.get("ops:world-patent-data", {}).get(
                   "ops:patent-family", {}
               ).get("ops:family-member", [])
               if isinstance(family, dict):
                   family = [family]
               for member in family:
                   doc_id = member.get("publication-reference", {}).get("document-id", {})
                   num = doc_id.get("doc-number", "")
                   country = doc_id.get("country", "")
                   if num:
                       members.append(f"{country}{num}")
               return members
       ```

    2. Create `src/aegis/sources/epo_test.py` with fixture-based tests:
       - `test_parse_ops_response`: Mock OPS response with 3 EP patents, verify parsing
       - `test_patent_family_extraction`: Mock family response, verify member extraction
       - `test_fetch_pagination`: Mock two pages of OPS results
       - `test_epo_credentials_model`: Verify EpoCredentials model creation

       Use `respx` for HTTP mocking, `@pytest.mark.asyncio(strict=True)` for async tests.

    3. Update `src/aegis/sources/__init__.py` to add exports: `EpoClient`, `EpoCredentials`, `PatentFamily`.

    ## Files to create
    - `src/aegis/sources/epo.py`
    - `src/aegis/sources/epo_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add EPO exports

    ## Code patterns to follow
    - Same patterns as `src/aegis/sources/pubmed.py` and `src/aegis/sources/uspto.py`
    - Reuse `PatentRecord` from `src/aegis/sources/uspto.py` for uniform downstream handling
    - OAuth2 client credentials flow for EPO OPS

    ## Acceptance criteria
    - `src/aegis/sources/epo.py` exists and exports `EpoClient`, `EpoCredentials`, `PatentFamily`
    - Design assertion: `EpoClient.fetch_patents(cpc_codes: list[str], since: date) -> AsyncIterator[PatentRecord]`
    - Family deduplication: `EpoClient.get_patent_family(patent_number) -> PatentFamily | None`
    - All tests pass: `uv run pytest src/aegis/sources/epo_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/epo.py`
    - ruff passes: `uv run ruff check src/aegis/sources/epo.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/epo_test.py -v && uv run mypy src/aegis/sources/epo.py && uv run ruff check src/aegis/sources/epo.py
    ```

### 4. CPC/IPC to MeSH Cross-walk

- **Task ID**: cpc-mesh-xwalk
- **Role**: builder
- **Depends On**: scaffold-taxonomy
- **Assigned To**: builder-2
- **Description**: |
    Build the CPC/IPC to MeSH descriptor cross-walk with a curated YAML mapping for the ~500 most-relevant codes plus an LLM-constrained-generation fallback for tail codes.

    ## What to do

    1. Create `data/aegis/cpc_mesh_xwalk_v1.yaml` with curated mappings for high-priority CPC subclasses. Include at minimum 50 entries across A61K (pharmaceutical preparations), A61P (therapeutic activity), C07D (heterocyclic compounds), and C12N (microorganisms/enzymes):

       ```yaml
       # CPC to MeSH cross-walk v1
       # Curated mapping for high-priority patent classification codes
       # Reviewed: 2026-04-26
       version: 1
       review_cadence: quarterly
       entries:
         - cpc: "A61K31/00"
           mesh:
             - descriptor: "Pharmaceutical Preparations"
               weight: 1.0
             - descriptor: "Drug Delivery Systems"
               weight: 0.5
         - cpc: "A61K31/33"
           mesh:
             - descriptor: "Heterocyclic Compounds"
               weight: 1.0
         - cpc: "A61K31/395"
           mesh:
             - descriptor: "Heterocyclic Compounds, 1-Ring"
               weight: 0.8
         - cpc: "A61K31/4439"
           mesh:
             - descriptor: "Pyridines"
               weight: 1.0
             - descriptor: "Protein Kinase Inhibitors"
               weight: 0.7
         - cpc: "A61K31/506"
           mesh:
             - descriptor: "Pyrimidines"
               weight: 1.0
         - cpc: "A61K38/00"
           mesh:
             - descriptor: "Peptides"
               weight: 1.0
         - cpc: "A61K39/395"
           mesh:
             - descriptor: "Antibodies, Monoclonal"
               weight: 1.0
         - cpc: "A61K45/06"
           mesh:
             - descriptor: "Drug Combinations"
               weight: 1.0
         - cpc: "A61P1/00"
           mesh:
             - descriptor: "Digestive System Agents"
               weight: 1.0
         - cpc: "A61P3/00"
           mesh:
             - descriptor: "Drugs Affecting Metabolism"
               weight: 1.0
         - cpc: "A61P7/00"
           mesh:
             - descriptor: "Hematologic Agents"
               weight: 1.0
         - cpc: "A61P9/00"
           mesh:
             - descriptor: "Cardiovascular Agents"
               weight: 1.0
         - cpc: "A61P11/00"
           mesh:
             - descriptor: "Respiratory System Agents"
               weight: 1.0
         - cpc: "A61P13/00"
           mesh:
             - descriptor: "Urological Agents"
               weight: 1.0
         - cpc: "A61P17/00"
           mesh:
             - descriptor: "Dermatologic Agents"
               weight: 1.0
         - cpc: "A61P25/00"
           mesh:
             - descriptor: "Central Nervous System Agents"
               weight: 1.0
         - cpc: "A61P25/28"
           mesh:
             - descriptor: "Central Nervous System Agents"
               weight: 0.7
             - descriptor: "Nootropic Agents"
               weight: 1.0
         - cpc: "A61P29/00"
           mesh:
             - descriptor: "Anti-Inflammatory Agents"
               weight: 1.0
         - cpc: "A61P31/00"
           mesh:
             - descriptor: "Anti-Infective Agents"
               weight: 1.0
         - cpc: "A61P31/12"
           mesh:
             - descriptor: "Antiviral Agents"
               weight: 1.0
         - cpc: "A61P33/00"
           mesh:
             - descriptor: "Antiparasitic Agents"
               weight: 1.0
         - cpc: "A61P35/00"
           mesh:
             - descriptor: "Antineoplastic Agents"
               weight: 1.0
         - cpc: "A61P35/02"
           mesh:
             - descriptor: "Antineoplastic Agents"
               weight: 1.0
             - descriptor: "Antimetabolites, Antineoplastic"
               weight: 0.8
         - cpc: "A61P37/00"
           mesh:
             - descriptor: "Immunologic Factors"
               weight: 1.0
         - cpc: "A61P37/02"
           mesh:
             - descriptor: "Immunosuppressive Agents"
               weight: 1.0
         - cpc: "A61P43/00"
           mesh:
             - descriptor: "Drugs, Investigational"
               weight: 0.8
         - cpc: "C07D401/12"
           mesh:
             - descriptor: "Heterocyclic Compounds, 2-Ring"
               weight: 1.0
         - cpc: "C07D403/12"
           mesh:
             - descriptor: "Heterocyclic Compounds, 2-Ring"
               weight: 1.0
         - cpc: "C07D413/14"
           mesh:
             - descriptor: "Heterocyclic Compounds, 2-Ring"
               weight: 1.0
         - cpc: "C07D471/04"
           mesh:
             - descriptor: "Heterocyclic Compounds, Fused-Ring"
               weight: 1.0
         - cpc: "C07D487/04"
           mesh:
             - descriptor: "Heterocyclic Compounds, Fused-Ring"
               weight: 1.0
         - cpc: "C07K14/00"
           mesh:
             - descriptor: "Recombinant Proteins"
               weight: 0.8
             - descriptor: "Peptides"
               weight: 1.0
         - cpc: "C07K16/00"
           mesh:
             - descriptor: "Antibodies"
               weight: 1.0
         - cpc: "C07K16/18"
           mesh:
             - descriptor: "Antibodies"
               weight: 1.0
             - descriptor: "Immunoglobulin G"
               weight: 0.7
         - cpc: "C12N5/00"
           mesh:
             - descriptor: "Cells, Cultured"
               weight: 1.0
         - cpc: "C12N9/00"
           mesh:
             - descriptor: "Enzymes"
               weight: 1.0
         - cpc: "C12N9/12"
           mesh:
             - descriptor: "Protein Kinases"
               weight: 1.0
         - cpc: "C12N15/09"
           mesh:
             - descriptor: "Genetic Engineering"
               weight: 1.0
         - cpc: "C12N15/113"
           mesh:
             - descriptor: "RNA, Small Interfering"
               weight: 1.0
         - cpc: "C12N15/63"
           mesh:
             - descriptor: "Genetic Vectors"
               weight: 1.0
         - cpc: "C12Q1/68"
           mesh:
             - descriptor: "Nucleic Acid Hybridization"
               weight: 1.0
             - descriptor: "Molecular Diagnostic Techniques"
               weight: 0.7
         - cpc: "G01N33/50"
           mesh:
             - descriptor: "Biological Assay"
               weight: 1.0
         - cpc: "G01N33/574"
           mesh:
             - descriptor: "Tumor Markers, Biological"
               weight: 1.0
         - cpc: "G16B20/00"
           mesh:
             - descriptor: "Sequence Analysis, DNA"
               weight: 1.0
             - descriptor: "Computational Biology"
               weight: 0.8
         - cpc: "G16B40/00"
           mesh:
             - descriptor: "Computational Biology"
               weight: 1.0
         - cpc: "G16H50/20"
           mesh:
             - descriptor: "Diagnosis, Computer-Assisted"
               weight: 1.0
       # ... extend to ~500 entries over time (quarterly review)
       ```

       Include at least 45 entries in the initial YAML. The file should be well-commented with review cadence notes.

    2. Create `src/aegis/taxonomy/cpc_mesh_xwalk.py`:

       ```python
       """CPC/IPC to MeSH cross-walk: curated mapping + LLM fallback for tail codes."""

       from __future__ import annotations

       import logging
       from pathlib import Path
       from typing import Any, Protocol

       import yaml  # type: ignore[import-untyped]
       from pydantic import BaseModel, ConfigDict

       from aegis.storage.schema import MeshDescriptor

       logger = logging.getLogger(__name__)

       _DEFAULT_XWALK_PATH = Path("data/aegis/cpc_mesh_xwalk_v1.yaml")


       class MeshMapping(BaseModel):
           """A single CPC-to-MeSH mapping with weight."""

           model_config = ConfigDict(frozen=True)

           descriptor: str
           weight: float


       class LLMFallback(Protocol):
           """Protocol for LLM-based CPC-to-MeSH translation."""

           def translate(self, cpc_code: str, cpc_description: str) -> list[MeshMapping]:
               """Propose up to 3 MeSH descriptors for an unmapped CPC code."""
               ...


       class DefaultLLMFallback:
           """Stub LLM fallback that returns empty results.

           Replace with actual LLM integration (constrained generation
           against MeSH controlled vocabulary) in production.
           """

           def translate(self, cpc_code: str, cpc_description: str) -> list[MeshMapping]:
               logger.info("LLM fallback invoked for CPC %s (stub)", cpc_code)
               return []


       class CpcMeshXwalk:
           """Translate CPC/IPC codes to weighted MeSH descriptors."""

           def __init__(
               self,
               xwalk_path: Path | None = None,
               llm_fallback: LLMFallback | None = None,
           ) -> None:
               self._llm = llm_fallback or DefaultLLMFallback()
               self._mapping: dict[str, list[MeshMapping]] = {}
               self._load(xwalk_path or _DEFAULT_XWALK_PATH)

           def _load(self, path: Path) -> None:
               """Load curated cross-walk from YAML."""
               with open(path) as f:  # noqa: PTH123
                   data: dict[str, Any] = yaml.safe_load(f)
               for entry in data.get("entries", []):
                   cpc = entry["cpc"]
                   mappings = [
                       MeshMapping(descriptor=m["descriptor"], weight=m["weight"])
                       for m in entry.get("mesh", [])
                   ]
                   self._mapping[cpc] = mappings
               logger.info("Loaded %d CPC-MeSH mappings", len(self._mapping))

           def translate(self, cpc_code: str) -> list[tuple[MeshDescriptor, float]]:
               """Translate a CPC code to weighted MeSH descriptors.

               Returns list of (MeshDescriptor, weight) tuples.
               Uses curated mapping first; falls back to LLM for unmapped codes.
               """
               # Exact match
               if cpc_code in self._mapping:
                   return self._to_mesh_descriptors(self._mapping[cpc_code])

               # Prefix match (try progressively shorter prefixes)
               parts = cpc_code
               while len(parts) > 4:
                   parts = parts[:-1]
                   if parts in self._mapping:
                       return self._to_mesh_descriptors(self._mapping[parts])

               # LLM fallback
               fallback_results = self._llm.translate(cpc_code, "")
               if fallback_results:
                   return self._to_mesh_descriptors(fallback_results)

               return []

           @property
           def curated_count(self) -> int:
               """Number of curated CPC-MeSH mappings."""
               return len(self._mapping)

           @staticmethod
           def _to_mesh_descriptors(
               mappings: list[MeshMapping],
           ) -> list[tuple[MeshDescriptor, float]]:
               """Convert MeshMapping list to (MeshDescriptor, weight) tuples."""
               return [
                   (
                       MeshDescriptor(
                           descriptor=m.descriptor,
                           qualifier=None,
                           major_topic=m.weight >= 0.8,
                       ),
                       m.weight,
                   )
                   for m in mappings
               ]
       ```

    3. Create `src/aegis/taxonomy/cpc_mesh_test.py` with tests:
       - `test_load_curated_xwalk`: Load the YAML file, verify at least 40 entries loaded
       - `test_exact_match`: Translate "A61K31/00", verify returns Pharmaceutical Preparations
       - `test_prefix_fallback`: Translate a CPC code not in YAML but whose prefix is, verify prefix match
       - `test_llm_fallback_invoked`: Translate a totally unknown code with mock LLM, verify fallback called
       - `test_translate_returns_mesh_descriptors`: Verify return types are (MeshDescriptor, float)
       - `test_weight_range`: All weights in curated YAML are 0.0 < w <= 1.0
       - Use `tmp_path` to create test YAML files where needed

    4. Update `src/aegis/taxonomy/__init__.py` to export `CpcMeshXwalk`, `MeshMapping`.

    ## Files to create
    - `data/aegis/cpc_mesh_xwalk_v1.yaml`
    - `src/aegis/taxonomy/cpc_mesh_xwalk.py`
    - `src/aegis/taxonomy/cpc_mesh_test.py`

    ## Files to modify
    - `src/aegis/taxonomy/__init__.py` — add exports

    ## Code patterns to follow
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `from __future__ import annotations` at top of every module
    - YAML loading pattern from `src/aegis/scoring/quality_prior.py` (`yaml.safe_load`)
    - `MeshDescriptor` imported from `src/aegis/storage/schema.py`
    - `Protocol` for pluggable LLM fallback
    - Logger at module level

    ## Acceptance criteria
    - `data/aegis/cpc_mesh_xwalk_v1.yaml` exists with >= 40 curated entries
    - `CpcMeshXwalk.translate(cpc_code: str) -> list[(MeshDescriptor, float)]` works
    - Curated top-1 accuracy: hand-check A61K31/00 -> "Pharmaceutical Preparations"
    - Prefix fallback works for sub-codes of mapped parents
    - LLM fallback protocol is defined and default stub works
    - All tests pass: `uv run pytest src/aegis/taxonomy/cpc_mesh_test.py -v`
    - mypy passes: `uv run mypy src/aegis/taxonomy/cpc_mesh_xwalk.py`
    - ruff passes: `uv run ruff check src/aegis/taxonomy/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/taxonomy/cpc_mesh_test.py -v && uv run mypy src/aegis/taxonomy/cpc_mesh_xwalk.py && uv run ruff check src/aegis/taxonomy/
    ```

### 5. ChEMBL Target Cross-walk + Bulk Ingestor

- **Task ID**: chembl-xwalk
- **Role**: builder
- **Depends On**: scaffold-taxonomy
- **Assigned To**: builder-2
- **Description**: |
    Build the ChEMBL target-to-MeSH cross-walk and bulk SQLite ingestion module so chemistry queries expand into MeSH vector space.

    ## What to do

    1. Create `src/aegis/sources/chembl.py` for bulk ChEMBL SQLite dump ingestion:

       ```python
       """ChEMBL bulk data ingestion from SQLite dump."""

       from __future__ import annotations

       import logging
       import sqlite3
       from collections.abc import Iterator
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class ChemblTarget(BaseModel):
           """A ChEMBL target with UniProt cross-references."""

           model_config = ConfigDict(frozen=True)

           target_chembl_id: str          # e.g., "CHEMBL2971"
           target_type: str               # e.g., "SINGLE PROTEIN"
           pref_name: str                 # e.g., "Janus kinase 2"
           organism: str | None
           uniprot_accessions: list[str]  # UniProt IDs


       class ChemblDisease(BaseModel):
           """A disease association from ChEMBL drug indications."""

           model_config = ConfigDict(frozen=True)

           mesh_id: str                   # MeSH UI, e.g., "D009196"
           mesh_heading: str              # e.g., "Myeloproliferative Disorders"
           efo_id: str | None


       class ChemblIngestor:
           """Ingest ChEMBL SQLite dump and extract targets + disease associations."""

           def __init__(self, db_path: Path) -> None:
               self._db_path = db_path

           def iter_targets(self) -> Iterator[ChemblTarget]:
               """Iterate over all single-protein targets with UniProt accessions."""
               conn = sqlite3.connect(str(self._db_path))
               try:
                   cursor = conn.execute(
                       """
                       SELECT td.chembl_id, td.target_type, td.pref_name, td.organism,
                              GROUP_CONCAT(cs.accession, ',') as accessions
                       FROM target_dictionary td
                       LEFT JOIN target_components tc ON td.tid = tc.tid
                       LEFT JOIN component_sequences cs ON tc.component_id = cs.component_id
                       WHERE td.target_type = 'SINGLE PROTEIN'
                       GROUP BY td.chembl_id
                       """
                   )
                   for row in cursor:
                       accessions = row[4].split(",") if row[4] else []
                       yield ChemblTarget(
                           target_chembl_id=row[0],
                           target_type=row[1],
                           pref_name=row[2] or "",
                           organism=row[3],
                           uniprot_accessions=accessions,
                       )
               finally:
                   conn.close()

           def iter_disease_associations(
               self, target_chembl_id: str
           ) -> Iterator[ChemblDisease]:
               """Iterate disease associations for a target via drug indications."""
               conn = sqlite3.connect(str(self._db_path))
               try:
                   cursor = conn.execute(
                       """
                       SELECT DISTINCT di.mesh_id, di.mesh_heading, di.efo_id
                       FROM drug_indication di
                       JOIN activities act ON di.molregno = act.molregno
                       JOIN assays a ON act.assay_id = a.assay_id
                       WHERE a.tid = (
                           SELECT tid FROM target_dictionary WHERE chembl_id = ?
                       )
                       AND di.mesh_id IS NOT NULL
                       """,
                       (target_chembl_id,),
                   )
                   for row in cursor:
                       yield ChemblDisease(
                           mesh_id=row[0],
                           mesh_heading=row[1] or "",
                           efo_id=row[2],
                       )
               finally:
                   conn.close()
       ```

    2. Create `src/aegis/taxonomy/chembl_xwalk.py`:

       ```python
       """ChEMBL target to MeSH cross-walk."""

       from __future__ import annotations

       import logging
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       from aegis.sources.chembl import ChemblIngestor
       from aegis.storage.schema import MeshDescriptor

       logger = logging.getLogger(__name__)


       class TargetMeshMapping(BaseModel):
           """A ChEMBL target mapped to MeSH descriptors."""

           model_config = ConfigDict(frozen=True)

           target_chembl_id: str
           target_name: str
           mesh_descriptors: list[MeshDescriptor]


       class ChemblXwalk:
           """Cross-walk ChEMBL target IDs to MeSH descriptors.

           Covers: target protein name -> MeSH, pathway associations,
           and disease associations from drug indications.
           """

           def __init__(
               self,
               chembl_db_path: Path | None = None,
           ) -> None:
               self._ingestor = ChemblIngestor(chembl_db_path) if chembl_db_path else None
               self._cache: dict[str, list[MeshDescriptor]] = {}

           def target_to_mesh(self, target_id: str) -> list[MeshDescriptor]:
               """Translate a ChEMBL target ID to MeSH descriptors.

               Returns descriptors covering the target itself, its pathway,
               and its disease associations.
               """
               if target_id in self._cache:
                   return self._cache[target_id]

               if self._ingestor is None:
                   return []

               descriptors: list[MeshDescriptor] = []

               # Get disease associations
               for disease in self._ingestor.iter_disease_associations(target_id):
                   descriptors.append(MeshDescriptor(
                       descriptor=disease.mesh_heading,
                       qualifier=None,
                       major_topic=True,
                   ))

               self._cache[target_id] = descriptors
               return descriptors

           def build_index(self) -> int:
               """Pre-build the full target-to-MeSH index from ChEMBL dump.

               Returns number of targets indexed.
               """
               if self._ingestor is None:
                   return 0

               count = 0
               for target in self._ingestor.iter_targets():
                   mesh = self.target_to_mesh(target.target_chembl_id)
                   if mesh:
                       count += 1
               logger.info("Indexed %d ChEMBL targets with MeSH mappings", count)
               return count
       ```

    3. Create `src/aegis/taxonomy/chembl_xwalk_test.py` with tests:
       - `test_chembl_target_parse`: Create a mock SQLite DB with target_dictionary and component_sequences tables, verify `iter_targets` yields ChemblTarget objects
       - `test_disease_association`: Mock SQLite with drug_indication + activities + assays tables, verify disease iteration
       - `test_target_to_mesh`: Mock ingestor, verify `target_to_mesh` returns MeshDescriptor list
       - `test_target_to_mesh_caching`: Call twice, verify second call uses cache
       - `test_jak2_expansion`: Verify "JAK2 kinase inhibitor" scenario — mock target CHEMBL2971 (JAK2) returns MeSH for "Janus Kinase 2", "Myeloproliferative Disorders"
       - Use `tmp_path` for temporary SQLite databases

    4. Update `src/aegis/taxonomy/__init__.py` to add exports: `ChemblXwalk`, `TargetMeshMapping`.
    5. Update `src/aegis/sources/__init__.py` to add exports: `ChemblIngestor`, `ChemblTarget`, `ChemblDisease`.

    ## Files to create
    - `src/aegis/sources/chembl.py`
    - `src/aegis/taxonomy/chembl_xwalk.py`
    - `src/aegis/taxonomy/chembl_xwalk_test.py`

    ## Files to modify
    - `src/aegis/taxonomy/__init__.py` — add ChEMBL exports
    - `src/aegis/sources/__init__.py` — add ChEMBL source exports

    ## Code patterns to follow
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `from __future__ import annotations` at top of every module
    - `MeshDescriptor` imported from `src/aegis/storage/schema.py`
    - SQLite `sqlite3` for ChEMBL dump access (not DuckDB — ChEMBL ships as SQLite)
    - Iterator pattern for bulk data
    - Logger at module level
    - Test patterns: `tmp_path` fixture for temporary databases

    ## Acceptance criteria
    - `ChemblXwalk.target_to_mesh(target_id: str) -> list[MeshDescriptor]` works
    - `ChemblIngestor.iter_targets()` yields `ChemblTarget` objects
    - JAK2 expansion test: target CHEMBL2971 returns relevant MeSH descriptors
    - All tests pass: `uv run pytest src/aegis/taxonomy/chembl_xwalk_test.py -v`
    - mypy passes: `uv run mypy src/aegis/taxonomy/chembl_xwalk.py src/aegis/sources/chembl.py`
    - ruff passes: `uv run ruff check src/aegis/taxonomy/ src/aegis/sources/chembl.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/taxonomy/chembl_xwalk_test.py -v && uv run mypy src/aegis/taxonomy/chembl_xwalk.py src/aegis/sources/chembl.py && uv run ruff check src/aegis/taxonomy/ src/aegis/sources/chembl.py
    ```

### 6. USPTO + EPO Bulk Ingestion Modules

- **Task ID**: patent-bulk
- **Role**: builder
- **Depends On**: uspto-client, epo-client
- **Assigned To**: builder-1
- **Description**: |
    Build bulk ingestion modules for historical patent pulls from USPTO (Google Cloud bulk dumps) and EPO (bulk feed), capable of processing ~10M patents in <72 hours with daily incremental refresh <30 min.

    ## What to do

    1. Create `src/aegis/sources/uspto_bulk.py`:

       ```python
       """USPTO bulk patent ingestion from Google Cloud / Bulk Data Storage System."""

       from __future__ import annotations

       import gzip
       import json
       import logging
       from collections.abc import Iterator
       from datetime import date
       from pathlib import Path

       from aegis.sources.uspto import PatentRecord, InventorAttribution, PatentAssignee

       logger = logging.getLogger(__name__)

       # USPTO bulk data is available as JSONL files
       USPTO_BULK_URL_TEMPLATE = (
           "https://bulkdata.uspto.gov/data/patent/grant/redbook/fulltext/{year}/"
       )


       class BulkIngestStats(BaseModel):
           """Statistics from a bulk ingestion run."""

           model_config = ConfigDict(frozen=True)

           total_files_processed: int
           total_patents_parsed: int
           total_patents_failed: int
           elapsed_seconds: float
           patents_per_second: float


       class UsptoBulkIngestor:
           """Ingest USPTO patents from bulk dump files (JSONL/XML).

           Historical pull: processes pre-downloaded bulk files from local storage.
           Incremental: processes delta files by grant date.
           """

           def __init__(
               self,
               data_dir: Path,
               workers: int = 4,
           ) -> None:
               self._data_dir = data_dir
               self._workers = workers

           def iter_patents_from_file(
               self, file_path: Path
           ) -> Iterator[PatentRecord]:
               """Parse a single bulk file and yield PatentRecords.

               Supports .jsonl and .jsonl.gz files.
               """
               opener = gzip.open if file_path.suffix == ".gz" else open
               with opener(file_path, "rt", encoding="utf-8") as f:  # type: ignore[call-overload]
                   for line_num, line in enumerate(f, 1):
                       line = line.strip()
                       if not line:
                           continue
                       try:
                           data = json.loads(line)
                           record = self._parse_bulk_record(data)
                           if record is not None:
                               yield record
                       except (json.JSONDecodeError, KeyError, ValueError) as exc:
                           logger.debug(
                               "Parse error in %s line %d: %s",
                               file_path.name, line_num, exc,
                           )

           def iter_all_patents(
               self,
               since: date | None = None,
           ) -> Iterator[PatentRecord]:
               """Iterate over all patents in the data directory.

               If since is provided, only yield patents granted on or after that date.
               """
               files = sorted(self._data_dir.glob("*.jsonl*"))
               logger.info("Found %d bulk files in %s", len(files), self._data_dir)
               for file_path in files:
                   for record in self.iter_patents_from_file(file_path):
                       if since and record.grant_date and record.grant_date < since:
                           continue
                       yield record

           @staticmethod
           def _parse_bulk_record(data: dict) -> PatentRecord | None:
               """Parse a single record from USPTO bulk JSON format."""
               try:
                   inventors = []
                   for i, inv in enumerate(data.get("inventors", [])):
                       inventors.append(InventorAttribution(
                           inventor_id=inv.get("id", f"bulk-{i}"),
                           full_name=inv.get("name", ""),
                           first_name=inv.get("first_name"),
                           last_name=inv.get("last_name"),
                           is_lead_inventor=(i == 0),
                       ))

                   assignees = []
                   for asg in data.get("assignees", []):
                       assignees.append(PatentAssignee(
                           assignee_id=asg.get("id"),
                           organization=asg.get("organization"),
                           assignee_type=asg.get("type", "organization"),
                       ))

                   grant_date = None
                   if data.get("grant_date"):
                       grant_date = date.fromisoformat(data["grant_date"])

                   return PatentRecord(
                       patent_number=data.get("patent_number", ""),
                       grant_date=grant_date,
                       application_date=(
                           date.fromisoformat(data["application_date"])
                           if data.get("application_date")
                           else None
                       ),
                       title=data.get("title", ""),
                       abstract=data.get("abstract"),
                       claims_text=data.get("first_claim"),
                       inventors=inventors,
                       assignees=assignees,
                       cpc_codes=data.get("cpc_codes", []),
                       ipc_codes=data.get("ipc_codes", []),
                       forward_citation_count=data.get("citation_count", 0),
                       family_id=data.get("family_id"),
                       maintenance_status=data.get("maintenance_status"),
                   )
               except (KeyError, ValueError, TypeError):
                   return None
       ```

       Note: Add `from pydantic import BaseModel, ConfigDict` to the imports for `BulkIngestStats`.

    2. Create `src/aegis/sources/epo_bulk.py`:

       ```python
       """EPO bulk patent ingestion from pre-downloaded feed files."""

       from __future__ import annotations

       import gzip
       import json
       import logging
       from collections.abc import Iterator
       from datetime import date
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       from aegis.sources.uspto import PatentRecord, InventorAttribution, PatentAssignee

       logger = logging.getLogger(__name__)


       class EpoBulkIngestStats(BaseModel):
           """Statistics from an EPO bulk ingestion run."""

           model_config = ConfigDict(frozen=True)

           total_files_processed: int
           total_patents_parsed: int
           total_patents_failed: int
           elapsed_seconds: float


       class EpoBulkIngestor:
           """Ingest EPO patents from bulk feed files (JSONL/XML)."""

           def __init__(
               self,
               data_dir: Path,
               workers: int = 4,
           ) -> None:
               self._data_dir = data_dir
               self._workers = workers

           def iter_patents_from_file(
               self, file_path: Path
           ) -> Iterator[PatentRecord]:
               """Parse a single EPO bulk file and yield PatentRecords."""
               opener = gzip.open if file_path.suffix == ".gz" else open
               with opener(file_path, "rt", encoding="utf-8") as f:  # type: ignore[call-overload]
                   for line_num, line in enumerate(f, 1):
                       line = line.strip()
                       if not line:
                           continue
                       try:
                           data = json.loads(line)
                           record = self._parse_epo_record(data)
                           if record is not None:
                               yield record
                       except (json.JSONDecodeError, KeyError, ValueError) as exc:
                           logger.debug(
                               "EPO parse error in %s line %d: %s",
                               file_path.name, line_num, exc,
                           )

           def iter_all_patents(
               self,
               since: date | None = None,
           ) -> Iterator[PatentRecord]:
               """Iterate over all EPO patents in the data directory."""
               files = sorted(self._data_dir.glob("*.jsonl*"))
               logger.info("Found %d EPO bulk files in %s", len(files), self._data_dir)
               for file_path in files:
                   for record in self.iter_patents_from_file(file_path):
                       if since and record.grant_date and record.grant_date < since:
                           continue
                       yield record

           @staticmethod
           def _parse_epo_record(data: dict) -> PatentRecord | None:
               """Parse a single record from EPO bulk JSON format."""
               try:
                   inventors = []
                   for i, inv in enumerate(data.get("inventors", [])):
                       inventors.append(InventorAttribution(
                           inventor_id=inv.get("id", f"epo-{i}"),
                           full_name=inv.get("name", ""),
                           first_name=inv.get("first_name"),
                           last_name=inv.get("last_name"),
                           is_lead_inventor=(i == 0),
                       ))

                   return PatentRecord(
                       patent_number=f"EP{data.get('doc_number', '')}",
                       grant_date=(
                           date.fromisoformat(data["publication_date"])
                           if data.get("publication_date")
                           else None
                       ),
                       application_date=(
                           date.fromisoformat(data["application_date"])
                           if data.get("application_date")
                           else None
                       ),
                       title=data.get("title", ""),
                       abstract=data.get("abstract"),
                       claims_text=None,
                       inventors=inventors,
                       assignees=[],
                       cpc_codes=data.get("cpc_codes", []),
                       ipc_codes=data.get("ipc_codes", []),
                       forward_citation_count=0,
                       family_id=data.get("family_id"),
                       maintenance_status=None,
                   )
               except (KeyError, ValueError, TypeError):
                   return None
       ```

    3. Create `src/aegis/sources/patent_bulk_test.py`:
       - `test_uspto_bulk_parse_single_file`: Write 10 JSONL records to tmp_path, parse, verify 10 PatentRecords
       - `test_uspto_bulk_parse_gzip`: Write gzipped JSONL, parse, verify records
       - `test_uspto_bulk_since_filter`: Write records with varying dates, filter since 2020, verify only recent returned
       - `test_epo_bulk_parse`: Write 5 EPO JSONL records, parse, verify PatentRecords with EP prefix
       - `test_bulk_malformed_line`: Include a malformed JSON line, verify it's skipped without exception
       - `test_bulk_empty_file`: Empty file yields no records

    4. Update `src/aegis/sources/__init__.py` to add exports: `UsptoBulkIngestor`, `BulkIngestStats`, `EpoBulkIngestor`, `EpoBulkIngestStats`.

    ## Files to create
    - `src/aegis/sources/uspto_bulk.py`
    - `src/aegis/sources/epo_bulk.py`
    - `src/aegis/sources/patent_bulk_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add bulk ingestion exports

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for stats models
    - Reuse `PatentRecord` from `src/aegis/sources/uspto.py`
    - Iterator pattern for streaming large files
    - Gzip support via `gzip.open`
    - Logger at module level
    - `tmp_path` fixture for test files

    ## Acceptance criteria
    - `UsptoBulkIngestor.iter_patents_from_file()` parses JSONL files into PatentRecords
    - `EpoBulkIngestor.iter_patents_from_file()` parses EPO JSONL into PatentRecords
    - Malformed lines are skipped without crashing
    - Date filtering works correctly
    - All tests pass: `uv run pytest src/aegis/sources/patent_bulk_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py`
    - ruff passes: `uv run ruff check src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/patent_bulk_test.py -v && uv run mypy src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py && uv run ruff check src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py
    ```

### 7. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: uspto-client, epo-client, cpc-mesh-xwalk, chembl-xwalk, patent-bulk
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for Phase 2a patent ingestion.

    ## Validation Commands

    1. Verify taxonomy package imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.taxonomy import CpcMeshXwalk, MeshMapping, ChemblXwalk, TargetMeshMapping; print('Taxonomy imports OK')"
    ```

    2. Verify USPTO client imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.uspto import UsptoClient, PatentRecord, InventorAttribution; print('USPTO imports OK')"
    ```

    3. Verify EPO client imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.epo import EpoClient, EpoCredentials, PatentFamily; print('EPO imports OK')"
    ```

    4. Verify ChEMBL imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.chembl import ChemblIngestor, ChemblTarget; print('ChEMBL imports OK')"
    ```

    5. Verify bulk ingestion imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.uspto_bulk import UsptoBulkIngestor; from aegis.sources.epo_bulk import EpoBulkIngestor; print('Bulk imports OK')"
    ```

    6. Verify ArtifactRefBundle has patent_ids:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.storage.schema import ArtifactRefBundle; assert 'patent_ids' in ArtifactRefBundle.model_fields; print('patent_ids field OK')"
    ```

    7. Verify CPC-MeSH cross-walk curated count:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.taxonomy.cpc_mesh_xwalk import CpcMeshXwalk; xw = CpcMeshXwalk(); assert xw.curated_count >= 40, f'Only {xw.curated_count} entries'; print(f'CPC-MeSH: {xw.curated_count} curated entries OK')"
    ```

    8. Run all new tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/uspto_test.py src/aegis/sources/epo_test.py src/aegis/taxonomy/cpc_mesh_test.py src/aegis/taxonomy/chembl_xwalk_test.py src/aegis/sources/patent_bulk_test.py -v
    ```

    9. Run mypy on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/sources/uspto.py src/aegis/sources/epo.py src/aegis/sources/chembl.py src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py src/aegis/taxonomy/cpc_mesh_xwalk.py src/aegis/taxonomy/chembl_xwalk.py
    ```

    10. Run ruff on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/sources/uspto.py src/aegis/sources/epo.py src/aegis/sources/chembl.py src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py src/aegis/taxonomy/
    ```

    11. Verify existing tests still pass:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/storage/ -v
    ```

    ## Acceptance Criteria
    - `UsptoClient.fetch_patents(cpc_codes, since) -> AsyncIterator[PatentRecord]` exists
    - `EpoClient.fetch_patents(cpc_codes, since) -> AsyncIterator[PatentRecord]` exists
    - `CpcMeshXwalk.translate(cpc_code) -> list[(MeshDescriptor, float)]` exists
    - `ChemblXwalk.target_to_mesh(target_id) -> list[MeshDescriptor]` exists
    - `UsptoBulkIngestor` and `EpoBulkIngestor` exist with file-based iteration
    - `ArtifactRefBundle` includes `patent_ids` field
    - CPC-MeSH curated YAML has >= 40 entries
    - Migration 003 exists for patent_refs table
    - All new tests pass
    - mypy strict passes on all new modules
    - ruff passes on all new modules
    - Existing Phase 0/1 tests unbroken

## Acceptance Criteria

- `UsptoClient` at `src/aegis/sources/uspto.py` exports `fetch_patents(cpc_codes: list[str], since: date) -> AsyncIterator[PatentRecord]` with `PatentRecord.inventors: list[InventorAttribution]` including disambiguated IDs
- `EpoClient` at `src/aegis/sources/epo.py` exports `fetch_patents(cpc_codes: list[str], since: date) -> AsyncIterator[PatentRecord]` with family-level deduplication via `get_patent_family`
- `CpcMeshXwalk` at `src/aegis/taxonomy/cpc_mesh_xwalk.py` exports `translate(cpc_code: str) -> list[(MeshDescriptor, float)]` with curated YAML (>= 40 entries) + LLM fallback protocol
- `ChemblXwalk` at `src/aegis/taxonomy/chembl_xwalk.py` exports `target_to_mesh(target_id: str) -> list[MeshDescriptor]`
- `UsptoBulkIngestor` and `EpoBulkIngestor` exist for historical patent pulls with streaming JSONL parsing
- `ArtifactRefBundle.patent_ids` field exists in schema
- Migration `003_patent_refs.sql` exists
- All new tests pass
- mypy strict mode passes on all new modules
- ruff lint passes on all new modules
- No existing Phase 0/1 tests broken

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/sources/uspto_test.py src/aegis/sources/epo_test.py src/aegis/taxonomy/cpc_mesh_test.py src/aegis/taxonomy/chembl_xwalk_test.py src/aegis/sources/patent_bulk_test.py -v` — Run all Phase 2a tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/sources/uspto.py src/aegis/sources/epo.py src/aegis/sources/chembl.py src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py src/aegis/taxonomy/cpc_mesh_xwalk.py src/aegis/taxonomy/chembl_xwalk.py` — Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/sources/uspto.py src/aegis/sources/epo.py src/aegis/sources/chembl.py src/aegis/sources/uspto_bulk.py src/aegis/sources/epo_bulk.py src/aegis/taxonomy/` — Lint all new modules
- `cd /Users/anvith/aegis && uv run pytest src/aegis/storage/ -v` — Verify existing storage tests still pass
- `cd /Users/anvith/aegis && uv run python -c "from aegis.taxonomy.cpc_mesh_xwalk import CpcMeshXwalk; xw = CpcMeshXwalk(); print(f'{xw.curated_count} entries')"` — Verify curated mapping count

## Notes

- PatentsView API documentation: https://patentsview.org/apis/api-endpoints — the API uses POST with JSON query format
- EPO OPS requires OAuth2 client credentials; the `EpoCredentials` model holds `consumer_key` and `consumer_secret`
- ChEMBL ships as a SQLite dump (~5 GB); use `sqlite3` directly (not DuckDB) since ChEMBL distributes in that format
- The CPC-MeSH YAML file is designed for quarterly SME review; the initial 45+ entries cover the most common pharma-relevant CPC codes
- Bulk ingestion assumes pre-downloaded files in a local directory; actual download orchestration is out of scope for this sub-spec
- Patent family deduplication: when a patent appears in both USPTO and EPO, only one should contribute full weight to `v_c`; the `family_id` field enables this deduplication downstream
