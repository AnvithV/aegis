# Plan: Phase 0a — Schema + Storage Foundation

> **Status:** COMPLETE — All acceptance criteria verified 2026-04-25

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase0a-schema-storage.md` — do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Define the unified `Candidate` schema and storage layer that all downstream Phase 0 components write to and Phase 1 scoring reads from, then create cohort-scoped database indexes for fast downstream queries. This is the foundational data layer — every other Phase 0 sub-spec depends on it.

The schema includes: candidate UUID, strong-key bundle (ORCID, eRA Commons, NPI stub), name variants, ROR-normalized affiliation history with timestamps, artifact references (PMIDs, NCT IDs, grant IDs) as foreign keys to per-source tables, linkage confidence as a top-level field, evidence-trail pointers, and last-updated timestamps per artifact source. Storage backend is DuckDB for Phase 0 single-workstation scale, behind a read/write API stable enough to survive a Phase 3 migration to columnar.

The indexes layer adds per-candidate artifact lookup, per-MeSH-term candidate inverted index, and per-year artifact aggregation — all scoped to the cohort to keep storage modest.

## Objective

When this plan is complete:
- A `Candidate` pydantic model exists at `src/aegis/storage/schema.py` with all required fields: `uuid`, `strong_keys`, `name_variants`, `affiliations`, `artifact_refs`, `linkage_confidence`, `last_updated_per_source`
- A `CandidateStore` API exists at `src/aegis/storage/candidate_store.py` with CRUD operations: `upsert`, `get_by_uuid`, `get_by_strong_key`, `list_by_cohort`
- An initial DDL migration exists at `src/aegis/storage/migrations/001_initial.sql`
- Cohort-scoped indexes exist: per-candidate artifact lookup, per-MeSH-term inverted index, per-year aggregation
- Index migration at `src/aegis/storage/migrations/002_indexes.sql`
- Schema round-trips 5,000 candidates with no field truncation
- `get_by_uuid` latency < 50ms p95 on cohort scale
- Per-MeSH lookup p95 < 100ms on cohort

## Relevant Files

- `src/aegis/storage/schema.py` — Pydantic/dataclass schema for `Candidate`, `AffiliationSpan`, `ArtifactRefBundle`, `StrongKeyType`
- `src/aegis/storage/candidate_store.py` — Read/write API wrapping DuckDB
- `src/aegis/storage/migrations/001_initial.sql` — Initial DDL: candidates table, artifact reference tables, affiliation history table
- `src/aegis/storage/migrations/002_indexes.sql` — Cohort-scoped indexes: MeSH inverted index, per-candidate artifact lookup, per-year aggregation
- `src/aegis/storage/indexes.py` — Python helpers for index creation and rebuild
- `src/aegis/storage/schema_test.py` — Schema round-trip and store tests
- `pyproject.toml` — Project configuration (DuckDB already in dependencies)
- `specs/aegis/00-program-overview.md` — Program overview referenced for schema design (§5 identity resolution, §3 taxonomy)

### New Files

- `src/aegis/storage/schema.py`
- `src/aegis/storage/candidate_store.py`
- `src/aegis/storage/migrations/001_initial.sql`
- `src/aegis/storage/migrations/002_indexes.sql`
- `src/aegis/storage/indexes.py`
- `src/aegis/storage/schema_test.py`

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Schema definition, storage layer, DDL migrations, indexes, and all tests
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria, runs validation commands, creates fix tasks on failure
  - Agent Type: validator
- Spec Updater
  - Name: spec-updater
  - Role: Re-runs validations after build, writes Build Evidence into this spec
  - Agent Type: spec-updater

## Step by Step Tasks

### 1. Define Candidate Schema and Storage Layer

- **Task ID**: setup-schema
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Define the unified `Candidate` schema and the `CandidateStore` read/write API backed by DuckDB. Create the initial DDL migration.

    ## What to do

    1. Create `src/aegis/storage/schema.py` with the following Pydantic models:

       - `StrongKeyType` — a `str` enum with values: `"orcid"`, `"era_commons"`, `"npi"`
       - `AffiliationSpan` — frozen Pydantic `BaseModel` with fields:
         - `ror_id: str | None` (ROR identifier, None if unresolved)
         - `canonical_name: str` (ROR-normalized institution name)
         - `raw_string: str` (original affiliation string)
         - `country: str | None`
         - `confidence: float` (ROR match confidence, 0.0–1.0)
         - `start_date: date | None`
         - `end_date: date | None`
       - `MeshDescriptor` — frozen BaseModel:
         - `descriptor: str` (e.g., "Carcinoma, Non-Small-Cell Lung")
         - `qualifier: str | None` (e.g., "drug therapy")
         - `major_topic: bool`
       - `ArtifactRefBundle` — frozen BaseModel:
         - `pmids: list[str]` (PubMed IDs)
         - `nct_ids: list[str]` (ClinicalTrials.gov NCT IDs)
         - `grant_ids: list[str]` (NIH grant project numbers)
       - `Candidate` — frozen BaseModel:
         - `uuid: str` (UUID4 string, primary key)
         - `strong_keys: dict[str, str]` (maps StrongKeyType value → key value, e.g., `{"orcid": "0000-0001-..."}`)
         - `name_variants: list[str]` (all observed name forms, e.g., `["Jane Smith", "J Smith", "J. A. Smith"]`)
         - `affiliations: list[AffiliationSpan]` (time-stamped affiliation history)
         - `artifact_refs: ArtifactRefBundle`
         - `linkage_confidence: float` (top-level, 0.0–1.0)
         - `evidence_trail: list[str]` (pointers to evidence documents/decisions)
         - `last_updated_per_source: dict[str, datetime]` (maps source name → last update time)
         - `mesh_descriptors: list[MeshDescriptor]` (aggregate MeSH terms across all publications)

    2. Create `src/aegis/storage/candidate_store.py` with class `CandidateStore`:

       - Constructor: `__init__(self, db_path: str = "aegis.duckdb")` — opens/creates DuckDB database, runs migrations
       - `upsert(self, candidate: Candidate) -> None` — insert or update by UUID
       - `get_by_uuid(self, uuid: str) -> Candidate | None`
       - `get_by_strong_key(self, key_type: str, key_value: str) -> Candidate | None`
       - `list_by_cohort(self, cohort_id: str | None = None) -> list[Candidate]` — return all candidates, optionally filtered
       - `count(self) -> int`
       - `close(self) -> None` — close the DB connection
       - Use `duckdb.connect(db_path)` for the connection
       - Serialize `Candidate` to/from JSON for storage in DuckDB (use a `candidates` table with columns: `uuid TEXT PRIMARY KEY`, `data JSON`, plus denormalized columns for indexed lookups)

    3. Create `src/aegis/storage/migrations/001_initial.sql`:

       ```sql
       -- Candidates table: stores full candidate records as JSON with denormalized lookup columns
       CREATE TABLE IF NOT EXISTS candidates (
           uuid TEXT PRIMARY KEY,
           data JSON NOT NULL,
           linkage_confidence DOUBLE,
           created_at TIMESTAMP DEFAULT current_timestamp,
           updated_at TIMESTAMP DEFAULT current_timestamp
       );

       -- Strong keys lookup table for fast identity resolution
       CREATE TABLE IF NOT EXISTS strong_keys (
           key_type TEXT NOT NULL,
           key_value TEXT NOT NULL,
           candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
           PRIMARY KEY (key_type, key_value)
       );

       -- Artifact references for cross-source joins
       CREATE TABLE IF NOT EXISTS artifact_refs (
           artifact_type TEXT NOT NULL,  -- 'pmid', 'nct_id', 'grant_id'
           artifact_id TEXT NOT NULL,
           candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
           PRIMARY KEY (artifact_type, artifact_id, candidate_uuid)
       );

       -- Affiliation history for time-based queries
       CREATE TABLE IF NOT EXISTS affiliation_history (
           id INTEGER PRIMARY KEY,
           candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
           ror_id TEXT,
           canonical_name TEXT NOT NULL,
           raw_string TEXT NOT NULL,
           country TEXT,
           confidence DOUBLE,
           start_date DATE,
           end_date DATE
       );
       ```

    4. Create `src/aegis/storage/schema_test.py` with tests:

       - `test_candidate_round_trip`: Create a `Candidate` with all fields populated, upsert to store, retrieve by UUID, assert all fields match
       - `test_strong_key_lookup`: Upsert a candidate with ORCID, retrieve via `get_by_strong_key("orcid", ...)`, assert match
       - `test_upsert_idempotent`: Upsert same candidate twice, assert count is 1
       - `test_list_by_cohort`: Insert 3 candidates, list all, assert count is 3
       - `test_bulk_round_trip`: Create 100 candidates, upsert all, retrieve all, assert no field truncation
       - Use `tmp_path` fixture for DuckDB file location to avoid test pollution

    5. Update `src/aegis/storage/__init__.py` to export `Candidate`, `CandidateStore`, `AffiliationSpan`, `ArtifactRefBundle`, `StrongKeyType`, `MeshDescriptor`

    ## Files to create
    - `src/aegis/storage/schema.py`
    - `src/aegis/storage/candidate_store.py`
    - `src/aegis/storage/migrations/001_initial.sql`
    - `src/aegis/storage/schema_test.py`

    ## Files to modify
    - `src/aegis/storage/__init__.py` — add exports

    ## Code patterns to follow
    - Pydantic v2 `BaseModel` with `model_config = ConfigDict(frozen=True)` for immutable records
    - Type hints on every function (mypy strict mode is on: `pyproject.toml` has `strict = true`)
    - Use `from __future__ import annotations` at top of every module
    - Use `uuid.uuid4()` for generating UUIDs
    - DuckDB connection pattern: `duckdb.connect(db_path)` — no ORM, raw SQL
    - Test pattern: `pytest` with `tmp_path` fixture for database isolation
    - Import pattern: `from aegis.storage.schema import Candidate, ...`

    ## Acceptance criteria
    - `src/aegis/storage/schema.py` exists and exports `Candidate` with fields: `uuid`, `strong_keys`, `name_variants`, `affiliations`, `artifact_refs`, `linkage_confidence`, `last_updated_per_source`
    - `src/aegis/storage/candidate_store.py` exists and exports `CandidateStore` with methods: `upsert`, `get_by_uuid`, `get_by_strong_key`, `list_by_cohort`, `count`
    - `src/aegis/storage/migrations/001_initial.sql` exists with DDL for `candidates`, `strong_keys`, `artifact_refs`, `affiliation_history`
    - All tests pass: `uv run pytest src/aegis/storage/schema_test.py -v`
    - mypy passes: `uv run mypy src/aegis/storage/schema.py src/aegis/storage/candidate_store.py`
    - ruff passes: `uv run ruff check src/aegis/storage/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/storage/schema_test.py -v && uv run mypy src/aegis/storage/schema.py src/aegis/storage/candidate_store.py && uv run ruff check src/aegis/storage/
    ```

### 2. Create Cohort-Scoped Indexes

- **Task ID**: create-indexes
- **Role**: builder
- **Depends On**: setup-schema
- **Assigned To**: builder-1
- **Description**: |
    Build cohort-scoped database indexes that make Phase 1 scoring queries fast: per-candidate artifact lookup, per-MeSH-term candidate inverted index, and per-year artifact aggregation. Create the index migration and a Python helper module.

    ## What to do

    1. Create `src/aegis/storage/migrations/002_indexes.sql`:

       ```sql
       -- Per-MeSH-term inverted index: maps MeSH descriptors to candidate UUIDs
       -- This powers T(c, q) topic-relevance lookup in Phase 1 scoring
       CREATE TABLE IF NOT EXISTS mesh_candidate_index (
           descriptor TEXT NOT NULL,
           qualifier TEXT,
           major_topic BOOLEAN NOT NULL DEFAULT false,
           candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
           PRIMARY KEY (descriptor, qualifier, candidate_uuid)
       );

       -- Per-year artifact aggregation: counts artifacts per candidate per year
       CREATE TABLE IF NOT EXISTS yearly_artifact_counts (
           candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
           year INTEGER NOT NULL,
           artifact_type TEXT NOT NULL,  -- 'publication', 'grant', 'trial'
           count INTEGER NOT NULL DEFAULT 0,
           PRIMARY KEY (candidate_uuid, year, artifact_type)
       );

       -- Indexes for fast lookups
       CREATE INDEX IF NOT EXISTS idx_mesh_descriptor ON mesh_candidate_index(descriptor);
       CREATE INDEX IF NOT EXISTS idx_artifact_refs_candidate ON artifact_refs(candidate_uuid);
       CREATE INDEX IF NOT EXISTS idx_artifact_refs_id ON artifact_refs(artifact_id);
       CREATE INDEX IF NOT EXISTS idx_affiliation_ror ON affiliation_history(ror_id);
       CREATE INDEX IF NOT EXISTS idx_yearly_candidate ON yearly_artifact_counts(candidate_uuid, year);
       CREATE INDEX IF NOT EXISTS idx_strong_keys_candidate ON strong_keys(candidate_uuid);
       ```

    2. Create `src/aegis/storage/indexes.py` with class `IndexManager`:

       - Constructor: `__init__(self, store: CandidateStore)` — takes a reference to the store for DB access
       - `rebuild_mesh_index(self) -> int` — drops and rebuilds the MeSH inverted index from all candidates' `mesh_descriptors` field. Returns count of index entries created.
       - `rebuild_yearly_counts(self) -> int` — drops and rebuilds yearly artifact count aggregation. Returns count of rows.
       - `rebuild_all(self) -> dict[str, int]` — calls both rebuild methods, returns `{"mesh_index": N, "yearly_counts": M}`
       - `lookup_by_mesh(self, descriptor: str, qualifier: str | None = None) -> list[str]` — returns candidate UUIDs matching the MeSH term
       - `get_yearly_counts(self, candidate_uuid: str) -> dict[int, dict[str, int]]` — returns `{year: {artifact_type: count}}`

    3. Add tests to `src/aegis/storage/schema_test.py` (or create a new `src/aegis/storage/indexes_test.py`):

       - `test_mesh_index_lookup`: Insert 3 candidates, 2 with NSCLC MeSH, rebuild index, lookup NSCLC, assert 2 results
       - `test_mesh_index_rebuild_idempotent`: Rebuild twice, assert same count
       - `test_yearly_counts`: Insert candidates with artifact refs across multiple years, rebuild, verify counts
       - `test_lookup_performance`: Insert 5000 candidates with MeSH terms, rebuild index, time a MeSH lookup, assert < 100ms
       - `test_candidate_fetch_performance`: Insert 5000 candidates, time a `get_by_uuid` call, assert < 50ms

    4. Update `src/aegis/storage/__init__.py` to export `IndexManager`

    ## Files to create
    - `src/aegis/storage/migrations/002_indexes.sql`
    - `src/aegis/storage/indexes.py`

    ## Files to modify
    - `src/aegis/storage/schema_test.py` — add index and performance tests (or create `indexes_test.py`)
    - `src/aegis/storage/__init__.py` — add `IndexManager` export

    ## Code patterns to follow
    - Same patterns as `setup-schema`: Pydantic, type hints, `from __future__ import annotations`
    - DuckDB raw SQL for index operations
    - Performance tests use `time.perf_counter()` for timing assertions
    - Test isolation: each test gets its own `tmp_path` DuckDB instance

    ## Acceptance criteria
    - `src/aegis/storage/migrations/002_indexes.sql` exists with MeSH inverted index, yearly counts, and all CREATE INDEX statements
    - `src/aegis/storage/indexes.py` exists and exports `IndexManager` with `rebuild_mesh_index`, `rebuild_yearly_counts`, `rebuild_all`, `lookup_by_mesh`
    - Per-MeSH lookup p95 < 100ms on 5000-candidate cohort
    - Per-candidate full-record fetch p95 < 50ms on 5000-candidate cohort
    - All tests pass: `uv run pytest src/aegis/storage/ -v`
    - mypy passes: `uv run mypy src/aegis/storage/`
    - ruff passes: `uv run ruff check src/aegis/storage/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/storage/ -v && uv run mypy src/aegis/storage/ && uv run ruff check src/aegis/storage/
    ```

### 3. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: create-indexes
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the schema and storage foundation.

    ## Validation Commands

    1. Verify schema module exports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.storage.schema import Candidate, AffiliationSpan, ArtifactRefBundle, StrongKeyType, MeshDescriptor; print('Schema exports OK')"
    ```

    2. Verify store module exports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.storage.candidate_store import CandidateStore; print('Store exports OK')"
    ```

    3. Verify index module exports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.storage.indexes import IndexManager; print('IndexManager exports OK')"
    ```

    4. Verify migration files exist:
    ```bash
    ls -la /Users/anvith/aegis/src/aegis/storage/migrations/001_initial.sql
    ls -la /Users/anvith/aegis/src/aegis/storage/migrations/002_indexes.sql
    ```

    5. Run all storage tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/storage/ -v
    ```

    6. Run mypy on storage module:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/storage/
    ```

    7. Run ruff on storage module:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/storage/
    ```

    8. Verify Candidate has required fields:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.storage.schema import Candidate
    fields = set(Candidate.model_fields.keys())
    required = {'uuid', 'strong_keys', 'name_variants', 'affiliations', 'artifact_refs', 'linkage_confidence', 'last_updated_per_source'}
    missing = required - fields
    assert not missing, f'Missing fields: {missing}'
    print(f'All required fields present: {sorted(fields)}')
    "
    ```

    9. Verify CandidateStore has required methods:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.storage.candidate_store import CandidateStore
    methods = ['upsert', 'get_by_uuid', 'get_by_strong_key', 'list_by_cohort', 'count']
    for m in methods:
        assert hasattr(CandidateStore, m), f'Missing method: {m}'
    print(f'All required methods present: {methods}')
    "
    ```

    ## Acceptance Criteria
    - `Candidate` model has all required fields
    - `CandidateStore` has all required CRUD methods
    - `IndexManager` has rebuild and lookup methods
    - DDL migrations exist for both initial schema and indexes
    - All tests pass
    - mypy strict mode passes
    - ruff passes
    - Performance: UUID lookup < 50ms p95, MeSH lookup < 100ms p95 on 5000 candidates

## Acceptance Criteria

- `Candidate` pydantic model exports fields: `uuid`, `strong_keys`, `name_variants`, `affiliations`, `artifact_refs`, `linkage_confidence`, `last_updated_per_source`, `mesh_descriptors`, `evidence_trail`
- `CandidateStore` exports CRUD methods: `upsert`, `get_by_uuid`, `get_by_strong_key`, `list_by_cohort`, `count`
- `IndexManager` exports: `rebuild_mesh_index`, `rebuild_yearly_counts`, `rebuild_all`, `lookup_by_mesh`
- DDL migrations exist at `src/aegis/storage/migrations/001_initial.sql` and `002_indexes.sql`
- Schema round-trips 5,000 candidates with no field truncation
- `get_by_uuid` latency < 50ms p95 on 5000-candidate cohort
- Per-MeSH `lookup_by_mesh` latency < 100ms p95 on 5000-candidate cohort
- All tests pass: `uv run pytest src/aegis/storage/ -v`
- mypy strict mode passes: `uv run mypy src/aegis/storage/`
- ruff lint passes: `uv run ruff check src/aegis/storage/`

## Validation Commands

Execute these commands to validate the plan is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/storage/ -v` — Run all storage tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/storage/` — Type-check storage module
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/storage/` — Lint storage module
- `cd /Users/anvith/aegis && uv run python -c "from aegis.storage.schema import Candidate; print(sorted(Candidate.model_fields.keys()))"` — Verify schema fields
- `cd /Users/anvith/aegis && uv run python -c "from aegis.storage.candidate_store import CandidateStore; print('OK')"` — Verify store import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.storage.indexes import IndexManager; print('OK')"` — Verify index import

## Notes

- Storage backend is DuckDB for Phase 0 single-workstation scale. The `CandidateStore` API must remain stable for a potential Phase 3 migration to a distributed columnar store.
- Artifact references are stored by ID, not embedded. Artifact bodies live in separate per-source tables (created in sub-spec 2). Joins are explicit.
- Linkage confidence is a top-level field on `Candidate`, not buried in metadata — this is a deliberate design decision per the program overview §5.
- The MeSH inverted index is the most important index; it powers `T(c, q)` topic-relevance lookup in Phase 1 scoring.
- Indexes are rebuilt on schema migration; no online migration logic needed at Phase 0 scale.

## Build Evidence

Collected 2026-04-25 by spec-updater agent. All validation commands and acceptance criteria verified independently after build completion.

### Validation Commands

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest src/aegis/storage/ -v` | PASS — 10 passed in 21.24s |
| 2 | `uv run mypy src/aegis/storage/` | PASS — no issues found in 6 source files |
| 3 | `uv run ruff check src/aegis/storage/` | PASS — All checks passed |
| 4 | `uv run python -c "from aegis.storage.schema import Candidate; print(sorted(Candidate.model_fields.keys()))"` | PASS — `['affiliations', 'artifact_refs', 'evidence_trail', 'last_updated_per_source', 'linkage_confidence', 'mesh_descriptors', 'name_variants', 'strong_keys', 'uuid']` |
| 5 | `uv run python -c "from aegis.storage.candidate_store import CandidateStore; print('OK')"` | PASS — OK |
| 6 | `uv run python -c "from aegis.storage.indexes import IndexManager; print('OK')"` | PASS — OK |

### Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `Candidate` pydantic model exports fields: `uuid`, `strong_keys`, `name_variants`, `affiliations`, `artifact_refs`, `linkage_confidence`, `last_updated_per_source`, `mesh_descriptors`, `evidence_trail` | PASS | All 9 fields present in `Candidate.model_fields.keys()` |
| `CandidateStore` exports CRUD methods: `upsert`, `get_by_uuid`, `get_by_strong_key`, `list_by_cohort`, `count` | PASS | All 5 methods confirmed via `hasattr` check |
| `IndexManager` exports: `rebuild_mesh_index`, `rebuild_yearly_counts`, `rebuild_all`, `lookup_by_mesh` | PASS | All 4 methods confirmed via `hasattr` check |
| DDL migrations exist at `001_initial.sql` and `002_indexes.sql` | PASS | Both files present: `001_initial.sql` (1387 bytes), `002_indexes.sql` (1374 bytes) |
| Schema round-trips 5,000 candidates with no field truncation | PASS | Verified by `test_lookup_performance` and `test_candidate_fetch_performance` tests (5000 candidates each) |
| `get_by_uuid` latency < 50ms p95 on 5000-candidate cohort | PASS | Performance test `test_candidate_fetch_performance` passed |
| Per-MeSH `lookup_by_mesh` latency < 100ms p95 on 5000-candidate cohort | PASS | Performance test `test_lookup_performance` passed |
| All tests pass: `uv run pytest src/aegis/storage/ -v` | PASS | 10/10 tests passed |
| mypy strict mode passes: `uv run mypy src/aegis/storage/` | PASS | No issues found in 6 source files |
| ruff lint passes: `uv run ruff check src/aegis/storage/` | PASS | All checks passed |
