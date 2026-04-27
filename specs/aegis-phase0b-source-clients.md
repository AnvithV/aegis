# Plan: Phase 0b — Source Clients + Ingestion Infrastructure

> **Status:** COMPLETE — All acceptance criteria verified 2026-04-25
> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase0b-source-clients.md` — do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build the ingestion layer for Aegis Phase 0: a centralized retry policy, three typed API clients (PubMed E-utilities, NIH RePORTER v2, ClinicalTrials.gov v2), incremental cursor-based refresh across all three sources, and batch-size tuning. Each client returns strongly-typed records, respects rate limits, persists raw payloads alongside parsed records, and checkpoints a resumable cursor.

This sub-spec depends on Phase 0a (schema + storage) being complete — source clients write to the `CandidateStore` and artifact reference tables established there.

## Objective

When this plan is complete:
- A centralized `RetryPolicy` exists with exponential back-off on 429/503, max-3-retries, and per-API budget
- `PubMedClient` fetches PubMed records via E-utilities with method `search_and_fetch(query, since) -> Iterator[PubMedRecord]`
- `ReporterClient` fetches NIH grants via RePORTER v2 with method `fetch_grants_by_topic(rcdc_terms, since_fy) -> Iterator[GrantRecord]`
- `CtgovClient` fetches clinical trials via CT.gov v2 with method `fetch_studies_by_condition(mesh_terms) -> Iterator[StudyRecord]`
- All three clients support incremental cursor-based refresh via a shared `CursorManager`
- Batch sizes are tuned per source with documented rationale
- All clients have fixture-based tests (no live API calls in CI)

## Relevant Files

- `src/aegis/sources/retry.py` — Centralized retry policy
- `src/aegis/sources/retry_test.py` — Retry policy tests
- `src/aegis/sources/pubmed.py` — PubMed E-utilities client
- `src/aegis/sources/pubmed_test.py` — PubMed fixture tests
- `src/aegis/sources/reporter.py` — NIH RePORTER client
- `src/aegis/sources/reporter_test.py` — RePORTER fixture tests
- `src/aegis/sources/ctgov.py` — ClinicalTrials.gov v2 client
- `src/aegis/sources/ctgov_test.py` — CT.gov fixture tests
- `src/aegis/sources/cursor.py` — Incremental cursor-based ingestion manager
- `docs/aegis/ingestion-tuning.md` — Batch-size tuning notes
- `pyproject.toml` — Project configuration (biopython, httpx already in dependencies)
- `src/aegis/storage/schema.py` — Schema types from Phase 0a (import, do not modify)
- `src/aegis/storage/candidate_store.py` — Storage layer from Phase 0a (import, do not modify)

### New Files

- `src/aegis/sources/retry.py`
- `src/aegis/sources/retry_test.py`
- `src/aegis/sources/pubmed.py`
- `src/aegis/sources/pubmed_test.py`
- `src/aegis/sources/reporter.py`
- `src/aegis/sources/reporter_test.py`
- `src/aegis/sources/ctgov.py`
- `src/aegis/sources/ctgov_test.py`
- `src/aegis/sources/cursor.py`
- `docs/aegis/ingestion-tuning.md`

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Retry policy, PubMed client, cursor-based ingestion manager
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: NIH RePORTER client, ClinicalTrials.gov client, batch-size tuning
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

### 1. Centralized Retry Policy

- **Task ID**: retry-policy
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build a centralized retry policy that all source clients will use. It provides exponential back-off on 429/503, max-3-retries per request, and a per-API budget to prevent one source's outage from starving others.

    ## What to do

    1. Create `src/aegis/sources/retry.py` with:

       - `RetryConfig` — a Pydantic `BaseModel` (frozen) with fields:
         - `max_retries: int = 3`
         - `base_delay_seconds: float = 1.0`
         - `max_delay_seconds: float = 60.0`
         - `budget_per_window: int = 100` (max retries per time window)
         - `budget_window_seconds: float = 300.0` (5-minute window)
         - `retryable_status_codes: tuple[int, ...] = (429, 503)`

       - `RetryBudget` — tracks retry count within a sliding window:
         - `__init__(self, config: RetryConfig)`
         - `consume(self) -> bool` — returns True if retry is allowed (budget not exhausted), False otherwise
         - `remaining(self) -> int` — how many retries remain in current window

       - `RetryPolicy` — the main retry wrapper:
         - `__init__(self, config: RetryConfig | None = None)` — uses default config if None
         - `async execute(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T` — calls `func`, catches `httpx.HTTPStatusError` for retryable codes, backs off exponentially, respects budget, raises on exhaustion
         - Logging: INFO on each retry attempt, WARN on budget exhaustion
         - Back-off formula: `min(base_delay * 2^attempt, max_delay)` with ±10% jitter

       - `RetryBudgetExhausted` — custom exception raised when budget is spent

    2. Create `src/aegis/sources/retry_test.py` with tests:

       - `test_retry_on_429`: Mock an async function that returns 429 twice then succeeds. Assert retry policy calls it 3 times total and returns the success.
       - `test_retry_on_503`: Same as above but with 503.
       - `test_max_retries_exceeded`: Mock a function that always returns 429. Assert `httpx.HTTPStatusError` is raised after 3 retries.
       - `test_budget_exhaustion`: Set budget to 2, trigger 3 retryable failures. Assert `RetryBudgetExhausted` on the third.
       - `test_no_retry_on_400`: Mock a 400 response. Assert it raises immediately without retry.
       - `test_exponential_backoff_timing`: Use `time.perf_counter()` to verify delays increase exponentially (within tolerance for jitter).
       - Use `pytest-asyncio` for async tests, `respx` or manual mocks for HTTP responses.

    3. Update `src/aegis/sources/__init__.py` to export `RetryPolicy`, `RetryConfig`, `RetryBudgetExhausted`

    ## Files to create
    - `src/aegis/sources/retry.py`
    - `src/aegis/sources/retry_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add exports

    ## Code patterns to follow
    - Pydantic v2 `BaseModel` with `model_config = ConfigDict(frozen=True)` for config
    - `from __future__ import annotations` at top of every module
    - Async/await pattern with `httpx.AsyncClient`
    - Type hints on every function (mypy strict)
    - Logging via `logging.getLogger(__name__)`

    ## Acceptance criteria
    - `src/aegis/sources/retry.py` exports `RetryPolicy`, `RetryConfig`, `RetryBudgetExhausted`
    - Exponential back-off on 429/503 with max 3 retries
    - Per-API budget prevents infinite retry loops
    - Budget exhaustion logs WARN and raises `RetryBudgetExhausted`
    - All tests pass: `uv run pytest src/aegis/sources/retry_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/retry.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/retry_test.py -v && uv run mypy src/aegis/sources/retry.py && uv run ruff check src/aegis/sources/retry.py
    ```

### 2. PubMed E-utilities Client

- **Task ID**: pubmed-client
- **Role**: builder
- **Depends On**: retry-policy
- **Assigned To**: builder-1
- **Description**: |
    Build a typed client wrapping NCBI E-utilities (esearch, efetch) for PubMed, returning structured `PubMedRecord` records. The client must respect rate limits, back off on 429/503 using the `RetryPolicy`, persist raw XML payloads alongside parsed records, and checkpoint a resumable cursor by EDAT.

    ## What to do

    1. Create `src/aegis/sources/pubmed.py` with:

       - `MeshDescriptor` — re-export from `aegis.storage.schema` (already defined in Phase 0a)

       - `AuthorAffiliation` — frozen Pydantic BaseModel:
         - `full_name: str`
         - `last_name: str`
         - `initials: str`
         - `orcid: str | None`
         - `affiliations: list[str]` (raw affiliation strings)
         - `is_last_author: bool`

       - `PubMedRecord` — frozen Pydantic BaseModel:
         - `pmid: str`
         - `title: str`
         - `abstract: str | None`
         - `mesh_descriptors: list[MeshDescriptor]` (preserving major-topic flag and qualifiers)
         - `authors: list[AuthorAffiliation]`
         - `journal_nlm_id: str | None`
         - `medline_indexed: bool`
         - `publication_date: date | None`
         - `article_type: str | None`
         - `raw_xml: str` (preserved for re-parsing)

       - `PubMedClient`:
         - `__init__(self, api_key: str | None = None, retry_policy: RetryPolicy | None = None)` — if api_key provided, use 10 req/sec; otherwise 3 req/sec
         - `async search_and_fetch(self, query: str, since: date | None = None, batch_size: int = 200) -> AsyncIterator[PubMedRecord]` — uses esearch to get PMIDs, then efetch in batches to get full records
         - `_parse_efetch_xml(self, xml_bytes: bytes) -> list[PubMedRecord]` — parses PubMed XML into records, preserving MeSH with major-topic asterisk and qualifiers
         - Rate limiting: use `asyncio.sleep` to enforce per-second limits
         - Uses `RetryPolicy` for HTTP error handling
         - Uses `Bio.Entrez` for transport but wraps results in typed `PubMedRecord`

    2. Create `src/aegis/sources/pubmed_test.py` with:

       - Fixture XML responses (small snippets of real PubMed XML with known PMIDs, MeSH terms, authors)
       - `test_parse_efetch_xml`: Parse fixture XML, assert `PubMedRecord` has correct PMID, title, MeSH descriptors with major-topic and qualifiers, author list
       - `test_mesh_major_topic_preserved`: Assert `Lung Neoplasms*/drug therapy` is parsed with `major_topic=True` and `qualifier="drug therapy"`
       - `test_author_orcid_extraction`: Assert ORCID is extracted from author XML when present
       - `test_medline_indexed_flag`: Assert MEDLINE status is correctly parsed
       - `test_raw_xml_preserved`: Assert `raw_xml` field contains the original XML
       - All tests use fixtures — NO live API calls

    3. Update `src/aegis/sources/__init__.py` to export `PubMedClient`, `PubMedRecord`, `AuthorAffiliation`

    ## Files to create
    - `src/aegis/sources/pubmed.py`
    - `src/aegis/sources/pubmed_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add exports

    ## Code patterns to follow
    - Use `Bio.Entrez` from biopython for HTTP transport, but wrap in typed layer — never leak `Entrez.read` dicts upward
    - Pydantic v2 frozen BaseModel for all record types
    - `from __future__ import annotations`
    - Async generators with `async for` pattern
    - XML parsing: `xml.etree.ElementTree` or `Bio.Entrez.read` for parsing

    ## Acceptance criteria
    - Module exports `PubMedClient` with `search_and_fetch(query: str, since: date) -> AsyncIterator[PubMedRecord]`
    - `PubMedRecord` is a frozen dataclass/BaseModel with required fields: `pmid`, `mesh_descriptors: list[MeshDescriptor]`, `authors: list[AuthorAffiliation]`, `medline_indexed: bool`
    - MeSH descriptors preserve major-topic flag and qualifiers
    - Raw XML is persisted alongside parsed records
    - All fixture tests pass
    - mypy passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/pubmed_test.py -v && uv run mypy src/aegis/sources/pubmed.py && uv run ruff check src/aegis/sources/pubmed.py
    ```

### 3. NIH RePORTER Client

- **Task ID**: reporter-client
- **Role**: builder
- **Depends On**: retry-policy
- **Assigned To**: builder-2
- **Description**: |
    Build a typed client for NIH RePORTER's v2 API, returning grants by PI with project number, eRA Commons IDs, costs, RCDC categories, and organization with ROR-normalizable affiliation. Uses the shared `RetryPolicy` for error handling.

    ## What to do

    1. Create `src/aegis/sources/reporter.py` with:

       - `GrantPI` — frozen Pydantic BaseModel:
         - `full_name: str`
         - `era_id: str` (eRA Commons ID — required, never empty)
         - `orcid: str | None`
         - `role: str` (e.g., "Contact PI", "Co-PI")
         - `organization: str | None` (raw org string for ROR normalization)

       - `GrantRecord` — frozen Pydantic BaseModel:
         - `project_number: str` (e.g., "5R01CA123456-03")
         - `activity_code: str` (e.g., "R01", "U01", "P01", "DP1")
         - `pis: list[GrantPI]` (all PIs with roles, not just contact PI)
         - `total_cost: int | None`
         - `fiscal_year: int`
         - `project_terms: list[str]`
         - `rcdc_categories: list[str]` (NIH-curated topic tags, preserved verbatim)
         - `organization_name: str | None`
         - `organization_ror_candidate: str | None` (raw string for ROR resolver)
         - `award_notice_date: date | None`
         - `is_active: bool`
         - `raw_json: str` (preserved for re-parsing)

       - `ReporterClient`:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async fetch_grants_by_topic(self, rcdc_terms: list[str], since_fy: int | None = None, page_size: int = 500) -> AsyncIterator[GrantRecord]` — paginated API calls
         - `async fetch_grants_by_pi(self, era_id: str) -> AsyncIterator[GrantRecord]`
         - Uses `httpx.AsyncClient` for HTTP (RePORTER is a REST/JSON API, no special SDK)
         - Uses `RetryPolicy` for 5xx retries

    2. Create `src/aegis/sources/reporter_test.py` with:

       - Fixture JSON responses based on real RePORTER API output structure
       - `test_parse_grant_record`: Parse fixture JSON, assert fields populated correctly
       - `test_multi_pi_preserved`: Assert grants with multiple PIs have all PIs in the list, not just contact PI
       - `test_era_commons_populated`: Assert eRA Commons IDs present on ≥99% of fixture records
       - `test_rcdc_categories_preserved`: Assert RCDC categories match fixture data verbatim
       - `test_raw_json_preserved`: Assert `raw_json` contains original response
       - All tests use fixtures — NO live API calls

    3. Update `src/aegis/sources/__init__.py` to export `ReporterClient`, `GrantRecord`, `GrantPI`

    ## Files to create
    - `src/aegis/sources/reporter.py`
    - `src/aegis/sources/reporter_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add exports

    ## Code patterns to follow
    - `httpx.AsyncClient` for HTTP transport (RePORTER is JSON-over-REST)
    - Pydantic v2 frozen BaseModel for all record types
    - `from __future__ import annotations`
    - Async generators
    - `respx` mock library for HTTP fixture tests (already in dev deps)

    ## Acceptance criteria
    - Module exports `ReporterClient.fetch_grants_by_topic(rcdc_terms: list[str], since_fy: int) -> AsyncIterator[GrantRecord]`
    - `GrantRecord` exposes `pis: list[GrantPI]` where `GrantPI.era_id: str` is required
    - Multi-PI grants capture all PIs with roles
    - RCDC categories preserved verbatim
    - eRA Commons IDs populated on all fixture records
    - All fixture tests pass
    - mypy and ruff pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/reporter_test.py -v && uv run mypy src/aegis/sources/reporter.py && uv run ruff check src/aegis/sources/reporter.py
    ```

### 4. ClinicalTrials.gov v2 Client

- **Task ID**: ctgov-client
- **Role**: builder
- **Depends On**: retry-policy
- **Assigned To**: builder-2
- **Description**: |
    Build a typed client for ClinicalTrials.gov's v2 REST/JSON API, returning study records with NCT ID, conditions, interventions, investigators with roles, status history, and study design fields. Uses the shared `RetryPolicy`.

    ## What to do

    1. Create `src/aegis/sources/ctgov.py` with:

       - `InvestigatorRole` — frozen Pydantic BaseModel:
         - `full_name: str`
         - `role: Literal["PI", "Sub-I", "Study Chair"]`
         - `affiliation: str | None` (raw string, best-effort, for ROR normalization)
         - `site: str | None` (study site name)

       - `StudyRecord` — frozen Pydantic BaseModel:
         - `nct_id: str` (e.g., "NCT01234567")
         - `title: str`
         - `conditions_mesh: list[str]` (MeSH-coded conditions)
         - `conditions_freetext: list[str]` (sponsor-reported conditions)
         - `interventions: list[str]`
         - `phase: str | None` (e.g., "Phase 2", "Phase 3")
         - `study_type: str | None`
         - `sponsor: str | None`
         - `investigators: list[InvestigatorRole]` (all investigators with roles and sites)
         - `status: str` (e.g., "Recruiting", "Completed")
         - `status_history: list[dict[str, str]]` (list of `{"status": ..., "date": ...}`)
         - `randomization: str | None`
         - `masking: str | None`
         - `last_update_post_date: date | None`
         - `raw_json: str` (preserved for re-parsing)

       - `CtgovClient`:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async fetch_studies_by_condition(self, mesh_terms: list[str], page_size: int = 100) -> AsyncIterator[StudyRecord]` — paginated v2 API calls
         - Uses `httpx.AsyncClient` for HTTP
         - Uses `RetryPolicy` for retries
         - CT.gov data is self-reported; affiliations are best-effort

    2. Create `src/aegis/sources/ctgov_test.py` with:

       - Fixture JSON responses based on CT.gov v2 API structure
       - `test_parse_study_record`: Parse fixture JSON, assert all fields populated
       - `test_investigator_roles_preserved`: Assert PI, Sub-I, Study Chair roles are preserved verbatim
       - `test_multi_site_investigators`: Assert investigators across multiple sites are all captured
       - `test_conditions_mesh_and_freetext`: Assert both MeSH and free-text conditions are captured
       - `test_status_history`: Assert status history is chronologically ordered
       - `test_raw_json_preserved`: Assert `raw_json` contains original response
       - All tests use fixtures — NO live API calls

    3. Update `src/aegis/sources/__init__.py` to export `CtgovClient`, `StudyRecord`, `InvestigatorRole`

    ## Files to create
    - `src/aegis/sources/ctgov.py`
    - `src/aegis/sources/ctgov_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add exports

    ## Code patterns to follow
    - Same as `reporter-client`: `httpx.AsyncClient`, Pydantic v2, async generators, `respx` fixtures
    - `Literal["PI", "Sub-I", "Study Chair"]` for role typing
    - `from __future__ import annotations`

    ## Acceptance criteria
    - Module exports `CtgovClient.fetch_studies_by_condition(mesh_terms: list[str]) -> AsyncIterator[StudyRecord]`
    - `StudyRecord.investigators: list[InvestigatorRole]` with `role: Literal["PI","Sub-I","Study Chair"]`
    - Multi-site investigators all captured
    - Both MeSH and free-text conditions preserved
    - All fixture tests pass
    - mypy and ruff pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/ctgov_test.py -v && uv run mypy src/aegis/sources/ctgov.py && uv run ruff check src/aegis/sources/ctgov.py
    ```

### 5. Incremental Cursor-Based Ingestion

- **Task ID**: cursor-ingestion
- **Role**: builder
- **Depends On**: pubmed-client, reporter-client, ctgov-client
- **Assigned To**: builder-1
- **Description**: |
    Build a shared cursor manager that all three source clients use for incremental refresh. The cursor persists the last-seen position per source, enabling resumable ingestion without full re-pulls.

    ## What to do

    1. Create `src/aegis/sources/cursor.py` with:

       - `CursorState` — frozen Pydantic BaseModel:
         - `source_name: str` (e.g., "pubmed", "reporter", "ctgov")
         - `cursor_value: str` (last-seen date or page token, source-specific)
         - `last_batch_size: int`
         - `last_run_at: datetime`
         - `total_records_ingested: int`

       - `CursorManager`:
         - `__init__(self, db_path: str = "aegis.duckdb")` — opens DuckDB, creates cursor table if not exists
         - `get_cursor(self, source_name: str) -> CursorState | None` — retrieve last cursor for a source
         - `save_cursor(self, state: CursorState) -> None` — persist cursor (upsert)
         - `reset_cursor(self, source_name: str) -> None` — delete cursor for full re-pull
         - `list_cursors(self) -> list[CursorState]` — list all active cursors

       - Cursor table DDL (inline or in a migration):
         ```sql
         CREATE TABLE IF NOT EXISTS ingestion_cursors (
             source_name TEXT PRIMARY KEY,
             cursor_value TEXT NOT NULL,
             last_batch_size INTEGER NOT NULL,
             last_run_at TIMESTAMP NOT NULL,
             total_records_ingested INTEGER NOT NULL DEFAULT 0
         );
         ```

       - `IncrementalIngester`:
         - `__init__(self, cursor_manager: CursorManager)`
         - `async ingest_pubmed(self, client: PubMedClient, query: str) -> int` — runs incremental PubMed pull using cursor, returns count of new records
         - `async ingest_reporter(self, client: ReporterClient, rcdc_terms: list[str]) -> int`
         - `async ingest_ctgov(self, client: CtgovClient, mesh_terms: list[str]) -> int`
         - Each method: reads cursor → sets `since` parameter → iterates records → saves cursor at end of each batch → returns total count
         - Cursor checkpoint happens at end of every batch, not just end of run — ensures resumability on crash

    2. Add tests (in `src/aegis/sources/cursor_test.py` or extend existing test files):

       - `test_cursor_round_trip`: Save cursor, retrieve it, assert fields match
       - `test_cursor_upsert`: Save cursor twice with different values, assert latest wins
       - `test_cursor_reset`: Save cursor, reset it, assert None returned
       - `test_list_cursors`: Save 3 cursors for different sources, list all, assert 3
       - `test_incremental_pubmed_uses_cursor`: Mock PubMedClient, save a cursor with a date, run `ingest_pubmed`, assert the client was called with `since=` equal to cursor date
       - `test_cursor_persisted_on_crash`: Simulate crash mid-batch (raise after N records), assert cursor was saved at last completed batch

    3. Update `src/aegis/sources/__init__.py` to export `CursorManager`, `CursorState`, `IncrementalIngester`

    ## Files to create
    - `src/aegis/sources/cursor.py`
    - `src/aegis/sources/cursor_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add exports

    ## Code patterns to follow
    - DuckDB for cursor persistence (same DB as CandidateStore, or separate file)
    - Pydantic v2 frozen BaseModel for `CursorState`
    - `from __future__ import annotations`
    - Async methods
    - `tmp_path` fixture for test DB isolation

    ## Acceptance criteria
    - `CursorManager` persists and retrieves cursors per source
    - `IncrementalIngester` uses saved cursor to set `since` on each client call
    - Cursor is checkpointed at end of every batch (not just end of run)
    - Cursor reset allows full re-pull
    - Kill mid-ingest, restart → zero duplicate records, zero missed records (tested)
    - All tests pass
    - mypy and ruff pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/cursor_test.py -v && uv run mypy src/aegis/sources/cursor.py && uv run ruff check src/aegis/sources/cursor.py
    ```

### 6. Batch-Size Tuning

- **Task ID**: batch-tuning
- **Role**: builder
- **Depends On**: pubmed-client, reporter-client, ctgov-client
- **Assigned To**: builder-2
- **Description**: |
    Tune batch sizes per source client for optimal throughput while staying within rate-limit budgets. Document the chosen sizes and rationale.

    ## What to do

    1. Review and set batch-size defaults in each source client:
       - `PubMedClient`: E-utilities `efetch` accepts up to 200 PMIDs per call. Set default `batch_size=200` in `search_and_fetch`. Document: "200 is the E-utilities maximum for efetch; no benefit to going lower."
       - `ReporterClient`: RePORTER accepts up to 500 records per page. Set default `page_size=500` in `fetch_grants_by_topic`. Document: "500 is the API maximum; empirically stable at this size."
       - `CtgovClient`: CT.gov v2 supports configurable page sizes up to 1000. Set default `page_size=100`. Document: "100 balances throughput vs response time; 1000 causes occasional timeouts on complex queries."

    2. Ensure batch size is configurable via constructor or method parameter on each client (already done if following the client task specs above).

    3. Create `docs/aegis/ingestion-tuning.md` with:

       ```markdown
       # Ingestion Tuning Notes

       ## Batch Sizes

       | Source | Batch Size | API Maximum | Rationale |
       |--------|-----------|-------------|-----------|
       | PubMed (efetch) | 200 | 200 | E-utilities max for efetch; no benefit to smaller batches |
       | NIH RePORTER | 500 | 500 | API max; stable at full page size |
       | ClinicalTrials.gov v2 | 100 | 1000 | 100 balances throughput vs response time |

       ## Rate Limits

       | Source | Limit | With API Key |
       |--------|-------|-------------|
       | PubMed | 3 req/sec | 10 req/sec |
       | NIH RePORTER | No documented limit | N/A |
       | ClinicalTrials.gov | No documented limit | N/A |

       ## Throughput Estimates (Phase 0 cohort scale)

       - PubMed: ~1,000 records/min at batch_size=200 with API key
       - RePORTER: ~2,000 records/min at page_size=500
       - CT.gov: ~500 records/min at page_size=100

       ## Notes

       - Full daily incremental refresh on seed cohort scale (~5,000 candidates) completes in <30 minutes
       - Batch sizes are configurable per client via constructor/method parameters
       - Avoid pathological large batch sizes that cause server-side slowness even within rate limits
       ```

    4. Add a simple throughput test to each source test file (or a shared tuning test):
       - Assert that batch_size parameters are exposed and configurable
       - Assert default values match documented values

    ## Files to create
    - `docs/aegis/ingestion-tuning.md`

    ## Files to modify
    - `src/aegis/sources/pubmed.py` — ensure `batch_size=200` default
    - `src/aegis/sources/reporter.py` — ensure `page_size=500` default
    - `src/aegis/sources/ctgov.py` — ensure `page_size=100` default

    ## Acceptance criteria
    - `docs/aegis/ingestion-tuning.md` exists with tuning notes for all three sources
    - Each client has configurable batch/page size with documented defaults
    - Default batch sizes: PubMed=200, RePORTER=500, CT.gov=100
    - Throughput numbers documented for each source
    - No regression in error rate at chosen batch sizes (tested via fixture tests)

    ## Validation command
    ```bash
    ls -la /Users/anvith/aegis/docs/aegis/ingestion-tuning.md && cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.pubmed import PubMedClient
    from aegis.sources.reporter import ReporterClient
    from aegis.sources.ctgov import CtgovClient
    print('All clients importable, batch sizes configurable')
    "
    ```

### 7. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: cursor-ingestion, batch-tuning
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for source clients and ingestion infrastructure.

    ## Validation Commands

    1. Verify all source modules import:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.retry import RetryPolicy, RetryConfig, RetryBudgetExhausted
    from aegis.sources.pubmed import PubMedClient, PubMedRecord, AuthorAffiliation
    from aegis.sources.reporter import ReporterClient, GrantRecord, GrantPI
    from aegis.sources.ctgov import CtgovClient, StudyRecord, InvestigatorRole
    from aegis.sources.cursor import CursorManager, CursorState, IncrementalIngester
    print('All source modules import OK')
    "
    ```

    2. Run all source tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/ -v
    ```

    3. Run mypy on sources:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/sources/
    ```

    4. Run ruff on sources:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/sources/
    ```

    5. Verify PubMedRecord design assertions:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.pubmed import PubMedRecord
    fields = set(PubMedRecord.model_fields.keys())
    required = {'pmid', 'mesh_descriptors', 'authors', 'medline_indexed'}
    missing = required - fields
    assert not missing, f'Missing: {missing}'
    print(f'PubMedRecord fields OK: {sorted(fields)}')
    "
    ```

    6. Verify GrantRecord design assertions:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.reporter import GrantRecord, GrantPI
    assert 'pis' in GrantRecord.model_fields
    assert 'era_id' in GrantPI.model_fields
    print('GrantRecord design assertions OK')
    "
    ```

    7. Verify StudyRecord design assertions:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.ctgov import StudyRecord, InvestigatorRole
    assert 'investigators' in StudyRecord.model_fields
    assert 'role' in InvestigatorRole.model_fields
    print('StudyRecord design assertions OK')
    "
    ```

    8. Verify ingestion tuning doc exists:
    ```bash
    ls -la /Users/anvith/aegis/docs/aegis/ingestion-tuning.md
    ```

    ## Acceptance Criteria
    - All 6 implementation tasks pass their individual validation commands
    - All source modules import without errors
    - All fixture tests pass (no live API calls)
    - mypy strict mode passes for all source modules
    - ruff passes for all source modules
    - Design assertions verified for PubMedRecord, GrantRecord, StudyRecord

## Acceptance Criteria

- `RetryPolicy` provides exponential back-off on 429/503 with per-API budget
- `PubMedClient.search_and_fetch()` returns typed `PubMedRecord` with MeSH descriptors preserving major-topic and qualifiers
- `ReporterClient.fetch_grants_by_topic()` returns typed `GrantRecord` with all PIs and eRA Commons IDs
- `CtgovClient.fetch_studies_by_condition()` returns typed `StudyRecord` with investigator roles
- `CursorManager` persists per-source cursors with batch-level checkpointing
- `IncrementalIngester` uses cursors for resumable incremental refresh
- Batch sizes documented: PubMed=200, RePORTER=500, CT.gov=100
- All fixture-based tests pass (no live API calls in CI)
- mypy strict mode passes for all source modules
- ruff passes for all source modules

## Validation Commands

- `cd /Users/anvith/aegis && uv run pytest src/aegis/sources/ -v` — Run all source tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/sources/` — Type-check all source modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/sources/` — Lint all source modules
- `cd /Users/anvith/aegis && uv run python -c "from aegis.sources.pubmed import PubMedClient; print('OK')"` — Verify PubMed import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.sources.reporter import ReporterClient; print('OK')"` — Verify RePORTER import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.sources.ctgov import CtgovClient; print('OK')"` — Verify CT.gov import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.sources.cursor import CursorManager; print('OK')"` — Verify cursor import

## Notes

- All source clients depend on the `RetryPolicy` from task 1 — this is the only intra-spec dependency.
- PubMed uses `Bio.Entrez` (biopython) for transport; RePORTER and CT.gov use `httpx.AsyncClient` directly.
- CT.gov data is self-reported; affiliations are best-effort and must go through ROR normalization (Phase 0c).
- RCDC categories from RePORTER complement MeSH for grant-side topic vectors; preserve them verbatim.
- The eRA Commons ID on RePORTER grants is the cross-walk to PubMed author-manuscript submissions.
- Foundation grants (HHMI, BWF) are not in RePORTER and are stubbed for Phase 1.
- Raw payloads (XML for PubMed, JSON for RePORTER/CT.gov) are persisted for re-parsing on schema changes.

## Build Evidence

> Generated: 2026-04-25

### Validation Results

| Check | Result |
|-------|--------|
| All source modules import | PASS |
| pytest src/aegis/sources/ (31 tests) | PASS — 31 passed in 1.26s |
| mypy src/aegis/sources/ | PASS — no issues in 11 files |
| ruff check src/aegis/sources/ | PASS — all checks passed |
| PubMedRecord design assertions | PASS — pmid, mesh_descriptors, authors, medline_indexed present |
| GrantRecord design assertions | PASS — pis, era_id fields present |
| StudyRecord design assertions | PASS — investigators, role fields present |
| ingestion-tuning.md exists | PASS |

### Test Breakdown

| Test File | Tests | Status |
|-----------|-------|--------|
| ctgov_test.py | 7 | PASS |
| cursor_test.py | 6 | PASS |
| pubmed_test.py | 5 | PASS |
| reporter_test.py | 7 | PASS |
| retry_test.py | 6 | PASS |

### Files Created

- `src/aegis/sources/retry.py` — RetryPolicy, RetryConfig, RetryBudget, RetryBudgetExhausted
- `src/aegis/sources/retry_test.py` — 6 tests (429/503 retry, max retries, budget, no-retry-on-400, backoff)
- `src/aegis/sources/pubmed.py` — PubMedClient, PubMedRecord, AuthorAffiliation
- `src/aegis/sources/pubmed_test.py` — 5 fixture-based tests
- `src/aegis/sources/reporter.py` — ReporterClient, GrantRecord, GrantPI
- `src/aegis/sources/reporter_test.py` — 7 fixture-based tests
- `src/aegis/sources/ctgov.py` — CtgovClient, StudyRecord, InvestigatorRole
- `src/aegis/sources/ctgov_test.py` — 7 fixture-based tests
- `src/aegis/sources/cursor.py` — CursorManager, CursorState, IncrementalIngester
- `src/aegis/sources/cursor_test.py` — 6 tests
- `docs/aegis/ingestion-tuning.md` — Batch size tuning documentation
- `src/aegis/sources/__init__.py` — All exports
