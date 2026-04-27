# Plan: Phase 3d — Geographic Broadening

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase3d-geographic-broadening.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build geographic broadening for Aegis Phase 3, covering three master-plan tasks:

1. **Task 1.8 (Geographic Broadening):** Extend ingestion to non-US patent and grant sources — EPO full coverage (completing the Phase 2 EU subset), WIPO PCT applications, and non-US grant agencies: ERC (European Research Council), Horizon Europe, MRC (UK Medical Research Council), CIHR (Canadian Institutes of Health Research), JST/KAKEN (Japan Science and Technology Agency / Grants-in-Aid for Scientific Research), and NSFC (National Natural Science Foundation of China).

2. **Task 1.9 (Per-Region Coverage Diagnostics):** Coverage diagnostics broken down by region (US, EU, UK, Canada, Japan, China, Rest-of-World). Customer API responses include a regional caveat when query results are >75% from one region.

3. **Task 2.4 (Geographic-Coverage Tracking Over Time):** Per-region coverage tracked over time as new sources come online. Target: cohort non-US ratio reaches 40%+ steady state.

## Objective

When this plan is complete:
- Seven new typed source clients exist (WIPO, ERC, Horizon Europe, MRC, CIHR, JST/KAKEN, NSFC), each following the Phase 0 pattern (httpx + Pydantic frozen models + RetryPolicy from `src/aegis/sources/retry.py`)
- EPO client is extended for full geographic coverage (all EP member states, not just the Phase 2 EU subset)
- KAKEN client handles Japanese-named researchers with transliteration / native-script support
- NSFC client is best-effort for public records with an explicit coverage caveat
- Region is derived from ROR-normalized affiliation using the existing `RorResolver` country field
- Per-region coverage diagnostics module produces region-level breakdowns (identity-resolution coverage, source coverage, per-population breakdown)
- API responses include a regional caveat when >75% of results come from one region
- Geographic-coverage tracking records per-region ratios over time with trend analysis
- A DuckDB migration adds grant_refs table for non-US grant tracking
- All new source clients are registered in `src/aegis/sources/__init__.py`
- All tests are fixture-based (no live API calls), pass mypy strict, and pass ruff

## Problem Statement

Aegis currently has strong US bias: PubMed and ClinicalTrials.gov are globally representative, but grant data (NIH RePORTER) and patent data (USPTO with partial EPO) are heavily US/EU-centric. The program overview Section 15 explicitly calls out that geographic bias must be addressed before production. Without non-US grant and patent sources, ranking results silently underweight researchers whose primary funding comes from non-US agencies (ERC, MRC, CIHR, JST/KAKEN, NSFC). The coverage diagnostics must expose this bias transparently so customers can interpret results correctly.

## Solution Approach

### Source Client Architecture

Each new source client follows the established pattern from Phase 0b / Phase 2a:
- Class-level: typed client class with `__init__(self, retry_policy: RetryPolicy | None = None)`
- Credential handling: optional credentials model (Pydantic frozen) for sources requiring auth
- Fetch methods: `async def fetch_grants(...) -> AsyncIterator[GrantRecord]` (or equivalent)
- Parsing: static `_parse_*` methods that convert raw API responses to typed Pydantic models
- Retry: delegates to `RetryPolicy.execute()` for HTTP calls
- Tests: fixture-based using `respx` mock, no live API calls

### Grant Record Model

A new `NonUsGrantRecord` model extends the grant pattern from `ReporterClient` but with fields appropriate to non-US funders (funder name, funder country, grant reference number, PI names, institution, amount in local currency, start/end dates, subject areas). This model is shared across all non-US grant sources.

### Region Derivation

Region is derived from the existing `RorResolver` (`src/aegis/identity/ror.py`), which already stores a `country` field in both the curated ROR data and the `affiliation_history` table. The region mapping is:
- US: country == "US"
- EU: country in {AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE}
- UK: country == "GB"
- Canada: country == "CA"
- Japan: country == "JP"
- China: country == "CN"
- Rest-of-World: everything else

### KAKEN Transliteration

KAKEN data includes Japanese researcher names in native script (kanji/kana). The client must:
1. Store both native-script and romanized name variants
2. Use the `name_variants` field on `Candidate` to store both forms
3. Transliterate using standard Hepburn romanization for identity resolution

### NSFC Coverage Caveat

NSFC (China) data is partially restricted. The client ingests only publicly accessible records from the NSFC open data portal. A coverage caveat flag is set on every record indicating "partial coverage" so downstream diagnostics can report this accurately.

### ROR Expansion

The existing `_CURATED_ROR` dictionary in `src/aegis/identity/ror.py` needs expansion with major non-US biomedical institutions relevant to the new grant sources (Japanese universities, Chinese research institutions, UK medical schools, Canadian research hospitals, major EU research centers). This is a data-only change to the curated dictionary, adding approximately 40-60 new entries with appropriate country codes.

## Relevant Files

Use these files to complete the task:

- `src/aegis/sources/retry.py` — RetryPolicy and RetryConfig patterns all new clients must use
- `src/aegis/sources/epo.py` — Existing EPO client to extend for full coverage
- `src/aegis/sources/epo_test.py` — Existing EPO tests showing test pattern
- `src/aegis/sources/reporter.py` — NIH RePORTER grant client (pattern reference for grant sources)
- `src/aegis/sources/reporter_test.py` — RePORTER test patterns
- `src/aegis/sources/uspto.py` — USPTO client and PatentRecord model (reused by EPO, WIPO)
- `src/aegis/sources/__init__.py` — Source module exports (must add new clients)
- `src/aegis/identity/ror.py` — ROR resolver with curated data and country field (must expand)
- `src/aegis/storage/schema.py` — Candidate, ArtifactRefBundle, AffiliationSpan schemas
- `src/aegis/storage/candidate_store.py` — CandidateStore with DuckDB backend
- `src/aegis/storage/migrations/001_initial.sql` — Initial schema (affiliation_history has country column)
- `src/aegis/storage/migrations/003_patent_refs.sql` — Patent refs migration (pattern for new migrations)
- `src/aegis/observability/coverage.py` — Existing CoverageDiagnostics (extend or parallel for regional)
- `src/aegis/observability/clinician_coverage.py` — ClinicianCoverageDashboard (pattern reference)
- `src/aegis/observability/freshness.py` — FreshnessMetrics with Prometheus gauges (pattern reference)
- `docs/design/scoring.md` — Living design document for scoring domain
- `pyproject.toml` — Project dependencies (may need `cutlet` for Japanese transliteration)

### New Files

- `src/aegis/sources/wipo.py` — WIPO PCT client
- `src/aegis/sources/wipo_test.py` — WIPO PCT tests
- `src/aegis/sources/erc.py` — ERC grant client
- `src/aegis/sources/erc_test.py` — ERC tests
- `src/aegis/sources/horizon_europe.py` — Horizon Europe grant client
- `src/aegis/sources/horizon_europe_test.py` — Horizon Europe tests
- `src/aegis/sources/mrc.py` — MRC (UK) grant client
- `src/aegis/sources/mrc_test.py` — MRC tests
- `src/aegis/sources/cihr.py` — CIHR (Canada) grant client
- `src/aegis/sources/cihr_test.py` — CIHR tests
- `src/aegis/sources/jst_kaken.py` — JST/KAKEN (Japan) grant client with transliteration
- `src/aegis/sources/jst_kaken_test.py` — JST/KAKEN tests
- `src/aegis/sources/nsfc.py` — NSFC (China) grant client (best-effort)
- `src/aegis/sources/nsfc_test.py` — NSFC tests
- `src/aegis/sources/non_us_grants.py` — Shared NonUsGrantRecord model and region mapping
- `src/aegis/observability/regional_coverage.py` — Per-region coverage diagnostics
- `src/aegis/observability/regional_coverage_test.py` — Regional coverage tests
- `src/aegis/observability/geographic_tracking.py` — Geographic-coverage tracking over time
- `src/aegis/observability/geographic_tracking_test.py` — Geographic tracking tests
- `src/aegis/storage/migrations/004_grant_refs.sql` — Migration for non-US grant references
- `config/aegis/ror_international.yaml` — Extended curated ROR data for non-US institutions

## Implementation Phases

### Phase 1: Foundation (Tasks 1-3)
- Shared non-US grant record model and region-mapping utilities
- DuckDB migration for non-US grant references
- ROR curated data expansion with international institutions
- Dependency addition (`cutlet` for Japanese transliteration)

### Phase 2: Source Clients (Tasks 4-10)
- EPO full coverage extension
- WIPO PCT client
- ERC client
- Horizon Europe client
- MRC client
- CIHR client
- JST/KAKEN client (with transliteration)
- NSFC client (best-effort)

### Phase 3: Diagnostics and Observability (Tasks 11-13)
- Per-region coverage diagnostics
- Regional caveat in API responses
- Geographic-coverage tracking over time with trend analysis

### Phase 4: Integration and Validation (Tasks 14-16)
- Source module exports update
- Full validation
- Design doc update

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Foundation models, EPO extension, WIPO, ERC, Horizon Europe source clients
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: MRC, CIHR, JST/KAKEN, NSFC source clients, ROR expansion
  - Agent Type: general-purpose
- Builder
  - Name: builder-3
  - Role: Regional coverage diagnostics, geographic tracking, API caveat, source exports
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Design Updater
  - Name: design-updater
  - Role: Updates docs/design/scoring.md with geographic broadening decisions after build completes
  - Agent Type: design-updater

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build_v2`.
- Task descriptions must be **exhaustive** — agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Every task MUST have an `Assigned To` matching a name in Team Members. This is enforced — tasks without a valid `Assigned To` will not be claimed.
- Start with foundational work, then core implementation, then validation.

### 1. Shared Non-US Grant Model and Region Mapping

- **Task ID**: non-us-grant-model
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the shared data model for non-US grant records and the region-mapping utility that all geographic-broadening code will use.

    ## What to do

    1. Create `src/aegis/sources/non_us_grants.py` with:

       - `from __future__ import annotations` at top of file

       - `NonUsGrantRecord` — a Pydantic `BaseModel` (frozen) with fields:
         - `grant_reference: str` — the funder's grant ID (e.g., "ERC-2023-StG-101075123")
         - `funder: str` — canonical funder name (e.g., "ERC", "MRC", "CIHR", "JST", "KAKEN", "NSFC", "Horizon Europe")
         - `funder_country: str` — ISO 3166-1 alpha-2 country code of the funder (e.g., "EU", "GB", "CA", "JP", "CN")
         - `title: str` — grant title
         - `abstract: str | None = None`
         - `pi_names: list[str]` — list of PI full names
         - `pi_orcids: list[str | None]` — list of PI ORCIDs (None if unknown), same length as pi_names
         - `institution: str | None = None` — host institution name
         - `institution_country: str | None = None` — ISO country code
         - `amount_local: float | None = None` — funding amount in local currency
         - `currency: str | None = None` — ISO 4217 currency code
         - `start_date: date | None = None`
         - `end_date: date | None = None`
         - `subject_areas: list[str]` — funder-specific subject classifications
         - `source: str` — which source this came from (e.g., "erc", "mrc", "cihr", "kaken", "nsfc", "horizon_europe")
         - `coverage_caveat: str | None = None` — None for full-coverage sources, description string for partial-coverage (e.g., NSFC)
         - `raw_json: str` — raw API response JSON

       - `Region` — a `StrEnum` with values: `US`, `EU`, `UK`, `CANADA`, `JAPAN`, `CHINA`, `REST_OF_WORLD`

       - `COUNTRY_TO_REGION: dict[str, Region]` — mapping from ISO alpha-2 country codes to Region. Include:
         - "US" -> Region.US
         - EU member states (AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE) -> Region.EU
         - "GB" -> Region.UK
         - "CA" -> Region.CANADA
         - "JP" -> Region.JAPAN
         - "CN" -> Region.CHINA
         - All other codes default to Region.REST_OF_WORLD

       - `def country_to_region(country_code: str | None) -> Region` — lookup function that returns Region.REST_OF_WORLD for None or unknown codes

       - `def candidate_region(affiliations: list[AffiliationSpan]) -> Region` — derive region from a candidate's affiliation history. Uses the most recent affiliation's country field (by end_date, or latest in list). Import `AffiliationSpan` from `aegis.storage.schema`.

    2. Import `date` from `datetime`, `StrEnum` from `enum`, `BaseModel` and `ConfigDict` from `pydantic`.

    ## Files to modify
    - `src/aegis/sources/non_us_grants.py` — CREATE new file

    ## Code patterns to follow
    - Match the `GrantRecord` pattern from `src/aegis/sources/reporter.py`: frozen Pydantic model, raw_json field, typed PI list
    - Match `StrongKeyType` StrEnum pattern from `src/aegis/storage/schema.py`
    - Every module starts with `from __future__ import annotations`

    ## Acceptance criteria
    - `NonUsGrantRecord` can be instantiated with all required fields
    - `Region` enum has 7 values
    - `country_to_region("US")` returns `Region.US`
    - `country_to_region("FR")` returns `Region.EU`
    - `country_to_region("GB")` returns `Region.UK`
    - `country_to_region("JP")` returns `Region.JAPAN`
    - `country_to_region("CN")` returns `Region.CHINA`
    - `country_to_region("BR")` returns `Region.REST_OF_WORLD`
    - `country_to_region(None)` returns `Region.REST_OF_WORLD`
    - mypy strict passes on the new file

    ## Validation command
    ```bash
    uv run python -c "
    from aegis.sources.non_us_grants import NonUsGrantRecord, Region, country_to_region, candidate_region
    assert country_to_region('US') == Region.US
    assert country_to_region('FR') == Region.EU
    assert country_to_region('GB') == Region.UK
    assert country_to_region('JP') == Region.JAPAN
    assert country_to_region('CN') == Region.CHINA
    assert country_to_region(None) == Region.REST_OF_WORLD
    print('non_us_grants model OK')
    " && uv run mypy src/aegis/sources/non_us_grants.py --strict
    ```

### 2. DuckDB Migration for Non-US Grant References

- **Task ID**: grant-refs-migration
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create a DuckDB migration to store non-US grant references, following the pattern from `003_patent_refs.sql`.

    ## What to do

    1. Create `src/aegis/storage/migrations/004_grant_refs.sql` with:

       ```sql
       CREATE TABLE IF NOT EXISTS grant_refs (
           grant_reference TEXT NOT NULL,
           candidate_uuid TEXT NOT NULL REFERENCES candidates(uuid),
           source TEXT NOT NULL,  -- 'erc', 'horizon_europe', 'mrc', 'cihr', 'kaken', 'nsfc'
           funder_country TEXT,
           PRIMARY KEY (grant_reference, candidate_uuid)
       );
       CREATE INDEX IF NOT EXISTS idx_grant_refs_candidate ON grant_refs(candidate_uuid);
       CREATE INDEX IF NOT EXISTS idx_grant_refs_source ON grant_refs(source);
       CREATE INDEX IF NOT EXISTS idx_grant_refs_country ON grant_refs(funder_country);
       ```

    2. This migration will be automatically picked up by `CandidateStore._run_migrations()` which globs `*.sql` files from the migrations directory in sorted order.

    ## Files to modify
    - `src/aegis/storage/migrations/004_grant_refs.sql` — CREATE new file

    ## Code patterns to follow
    - Match `src/aegis/storage/migrations/003_patent_refs.sql` exactly: CREATE TABLE IF NOT EXISTS, TEXT types, REFERENCES candidates(uuid), PRIMARY KEY on (id, candidate_uuid), CREATE INDEX IF NOT EXISTS
    - The `source` column uses lowercase source identifiers matching the `NonUsGrantRecord.source` field

    ## Acceptance criteria
    - Migration file exists at `src/aegis/storage/migrations/004_grant_refs.sql`
    - File is valid SQL that DuckDB can execute
    - Table has columns: grant_reference, candidate_uuid, source, funder_country
    - Primary key is (grant_reference, candidate_uuid)
    - Three indexes exist: on candidate_uuid, source, and funder_country

    ## Validation command
    ```bash
    uv run python -c "
    import duckdb
    conn = duckdb.connect(':memory:')
    conn.execute('CREATE TABLE candidates (uuid TEXT PRIMARY KEY, data JSON NOT NULL, linkage_confidence DOUBLE, created_at TIMESTAMP, updated_at TIMESTAMP)')
    sql = open('src/aegis/storage/migrations/004_grant_refs.sql').read()
    conn.execute(sql)
    cols = [r[0] for r in conn.execute('DESCRIBE grant_refs').fetchall()]
    assert 'grant_reference' in cols
    assert 'candidate_uuid' in cols
    assert 'source' in cols
    assert 'funder_country' in cols
    print('migration OK')
    "
    ```

### 3. ROR Curated Data Expansion

- **Task ID**: ror-expansion
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Expand the curated ROR data in `src/aegis/identity/ror.py` with major non-US biomedical research institutions from the UK, EU, Canada, Japan, and China. This ensures the `RorResolver` can resolve affiliations for researchers funded by the new non-US grant sources.

    ## What to do

    1. Edit `src/aegis/identity/ror.py` — add entries to the `_CURATED_ROR` dictionary. Add at least 50 new entries covering:

       **Japan (JP)** — at least 8 entries:
       - University of Tokyo (already present, verify)
       - Kyoto University: ror_id "https://ror.org/02kpeqv85", country "JP"
       - Osaka University: ror_id "https://ror.org/035t8zc32", country "JP"
       - Tohoku University: ror_id "https://ror.org/01dq60k83", country "JP"
       - Nagoya University: ror_id "https://ror.org/04chrp450", country "JP"
       - RIKEN (already present, verify)
       - National Institute of Advanced Industrial Science and Technology: ror_id "https://ror.org/01703db54", country "JP"
       - Keio University: ror_id "https://ror.org/02kn6nx58", country "JP"

       **China (CN)** — at least 8 entries:
       - Peking University (already present, verify)
       - Fudan University (already present, verify)
       - Tsinghua University: ror_id "https://ror.org/03cve4549", country "CN"
       - Zhejiang University: ror_id "https://ror.org/00a2xv884", country "CN"
       - Shanghai Jiao Tong University: ror_id "https://ror.org/0220qvk04", country "CN"
       - Sun Yat-sen University: ror_id "https://ror.org/0064kty71", country "CN"
       - Chinese Academy of Sciences: ror_id "https://ror.org/034t30j35", country "CN"
       - Nanjing University: ror_id "https://ror.org/01rxvg760", country "CN"

       **UK (GB)** — at least 8 entries (some already present):
       - University College London (already present, verify)
       - University of Oxford (already present, verify)
       - University of Cambridge (already present, verify)
       - Imperial College London (already present, verify)
       - King's College London: ror_id "https://ror.org/0220mzb33", country "GB"
       - University of Edinburgh: ror_id "https://ror.org/01nrxwf90", country "GB"
       - University of Manchester: ror_id "https://ror.org/027m9bs27", country "GB"
       - University of Glasgow: ror_id "https://ror.org/00vtgdb53", country "GB"
       - Francis Crick Institute: ror_id "https://ror.org/048s57834", country "GB"

       **Canada (CA)** — at least 8 entries:
       - University of Toronto (already present, verify)
       - University Health Network (already present, verify)
       - McGill University: ror_id "https://ror.org/01pxwe438", country "CA"
       - University of British Columbia: ror_id "https://ror.org/03rmrcq20", country "CA"
       - University of Alberta: ror_id "https://ror.org/0160cpw27", country "CA"
       - McMaster University: ror_id "https://ror.org/02fa3aq29", country "CA"
       - University of Montreal: ror_id "https://ror.org/0161xgx34", country "CA"
       - Ottawa Hospital Research Institute: ror_id "https://ror.org/03c4atk17", country "CA"

       **EU (various)** — at least 10 entries (some already present):
       - Karolinska Institutet (already present, SE, verify)
       - INSERM (already present, FR, verify)
       - Charite Berlin (already present, DE, verify)
       - Max Planck Society (already present, DE, verify)
       - CNRS (already present, FR, verify)
       - ETH Zurich: ror_id "https://ror.org/05a28rw58", country "CH"
       - Leiden University: ror_id "https://ror.org/027bh9e22", country "NL"
       - University of Copenhagen: ror_id "https://ror.org/035b05819", country "DK"
       - Helmholtz Association: ror_id "https://ror.org/0281dp749", country "DE"
       - Pasteur Institute: ror_id "https://ror.org/0495fxg12", country "FR"
       - University of Zurich: ror_id "https://ror.org/02crff812", country "CH"
       - KU Leuven: ror_id "https://ror.org/05f950310", country "BE"

       **Australia (AU)** — at least 4 entries:
       - Peter MacCallum Cancer Centre (already present, verify)
       - University of Melbourne: ror_id "https://ror.org/01ej9dk98", country "AU"
       - University of Sydney: ror_id "https://ror.org/0384j8v12", country "AU"
       - Monash University: ror_id "https://ror.org/02bfwt286", country "AU"

    2. Each entry follows the exact pattern of existing entries:
       ```python
       "Institution Name": {
           "ror_id": "https://ror.org/XXXXXXXXX",
           "parent_ror_id": None,  # or parent ROR URL
           "parent_name": None,  # or parent name string
           "country": "XX",  # ISO 3166-1 alpha-2
       },
       ```

    3. Do NOT modify any existing entries — only add new ones.
    4. Do NOT modify any methods or class definitions in the file — only expand the `_CURATED_ROR` dictionary.

    ## Files to modify
    - `src/aegis/identity/ror.py` — ADD entries to `_CURATED_ROR` dictionary (do NOT modify existing entries or any code)

    ## Code patterns to follow
    - Match the exact dict format of existing entries in `_CURATED_ROR`
    - All entries must have `ror_id`, `parent_ror_id`, `parent_name`, `country` keys
    - Country codes must be ISO 3166-1 alpha-2

    ## Acceptance criteria
    - At least 50 new entries added to `_CURATED_ROR`
    - Existing entries are unchanged
    - Every new entry has all 4 required keys (ror_id, parent_ror_id, parent_name, country)
    - Entries cover JP, CN, GB, CA, EU countries, AU
    - mypy strict passes
    - Existing ROR tests still pass

    ## Validation command
    ```bash
    uv run python -c "
    from aegis.identity.ror import RorResolver
    r = RorResolver()
    # Verify new entries are resolvable
    assert r.resolve('Kyoto University') is not None
    assert r.resolve('Tsinghua University') is not None
    assert r.resolve('University of Edinburgh') is not None
    assert r.resolve('McGill University') is not None
    # Verify existing entries still work
    assert r.resolve('Harvard University') is not None
    assert r.resolve('Stanford University') is not None
    # Count check
    from aegis.identity.ror import _CURATED_ROR
    assert len(_CURATED_ROR) >= 95, f'Expected >= 95 entries, got {len(_CURATED_ROR)}'
    print(f'ROR expansion OK: {len(_CURATED_ROR)} entries')
    " && uv run mypy src/aegis/identity/ror.py --strict && uv run pytest src/aegis/identity/ror_test.py -v
    ```

### 4. Add cutlet Dependency for Japanese Transliteration

- **Task ID**: add-cutlet-dep
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Add the `cutlet` library for Japanese-to-romaji transliteration, needed by the KAKEN client.

    ## What to do

    1. Edit `pyproject.toml` to add `cutlet>=0.4` to the `dependencies` list. Insert it alphabetically after `biopython`.

    2. Run `uv lock` to update the lock file (do NOT run uv sync as that may fail in CI; just lock).

    ## Files to modify
    - `pyproject.toml` — ADD `"cutlet>=0.4"` to the `dependencies` list

    ## Code patterns to follow
    - Match existing dependency format: `"package>=version"`

    ## Acceptance criteria
    - `cutlet>=0.4` appears in `pyproject.toml` dependencies
    - `uv lock` succeeds

    ## Validation command
    ```bash
    uv run python -c "import cutlet; print('cutlet OK')"
    ```

### 5. EPO Full Coverage Extension

- **Task ID**: epo-full-coverage
- **Role**: builder
- **Depends On**: non-us-grant-model
- **Assigned To**: builder-1
- **Description**: |
    Extend the existing EPO client to support full geographic coverage across all EP member states (not just the Phase 2 EU subset). Add a method to fetch patents by country office and expand CPC code coverage.

    ## What to do

    1. Edit `src/aegis/sources/epo.py` to add:

       - `EP_MEMBER_STATES: list[str]` — class-level constant listing all 39 EPO member states by their 2-letter country codes: AL, AT, BE, BG, CH, CY, CZ, DE, DK, EE, ES, FI, FR, GB, GR, HR, HU, IE, IS, IT, LI, LT, LU, LV, MC, ME, MK, MT, NL, NO, PL, PT, RO, RS, SE, SI, SK, SM, TR

       - `async def fetch_patents_by_country(self, country: str, since: date, batch_size: int = 100) -> AsyncIterator[PatentRecord]` — fetch patents for a specific EPO member state. Constructs an OPS query filtering by country (e.g., `pn=EP and pa=DE` or by country in the publication reference). Delegates to existing `_retry` and `_parse_ops_response`.

       - `async def fetch_all_member_state_patents(self, since: date, batch_size: int = 100) -> AsyncIterator[PatentRecord]` — iterates over all EP_MEMBER_STATES and yields patents from each. This provides full EPO coverage.

    2. Add tests to `src/aegis/sources/epo_test.py`:

       - `test_ep_member_states_count()` — verify `EP_MEMBER_STATES` has 39 entries
       - `test_fetch_patents_by_country()` — mock OPS API, verify country-specific query

    ## Files to modify
    - `src/aegis/sources/epo.py` — ADD `EP_MEMBER_STATES` constant, ADD `fetch_patents_by_country` method, ADD `fetch_all_member_state_patents` method
    - `src/aegis/sources/epo_test.py` — ADD tests for new methods

    ## Code patterns to follow
    - Match existing `fetch_patents` method pattern in `EpoClient`
    - Use `self._retry.execute()` for HTTP calls
    - Use `respx.mock` decorator and `Response` fixtures in tests (see existing `test_fetch_pagination`)
    - Every module starts with `from __future__ import annotations`

    ## Acceptance criteria
    - `EP_MEMBER_STATES` has exactly 39 entries
    - `fetch_patents_by_country` yields PatentRecord objects
    - `fetch_all_member_state_patents` iterates over all member states
    - Existing EPO tests still pass
    - New tests pass
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/epo_test.py -v && uv run mypy src/aegis/sources/epo.py --strict
    ```

### 6. WIPO PCT Client

- **Task ID**: wipo-client
- **Role**: builder
- **Depends On**: non-us-grant-model
- **Assigned To**: builder-1
- **Description**: |
    Build a typed client for WIPO PCT (Patent Cooperation Treaty) international patent applications. WIPO provides the PATENTSCOPE API for searching PCT applications.

    ## What to do

    1. Create `src/aegis/sources/wipo.py` with:

       - `from __future__ import annotations` at top

       - `PATENTSCOPE_API_URL = "https://patentscope.wipo.int/search/api/v1"` — base URL

       - `WipoCredentials(BaseModel)` — frozen Pydantic model:
         - `access_token: str`

       - `PctApplication(BaseModel)` — frozen Pydantic model for PCT records:
         - `application_number: str` — e.g., "PCT/US2023/012345"
         - `publication_number: str | None`
         - `filing_date: date | None`
         - `publication_date: date | None`
         - `title: str`
         - `abstract: str | None`
         - `applicants: list[str]`
         - `inventors: list[str]`
         - `ipc_codes: list[str]`
         - `designated_states: list[str]` — states designated in the PCT application
         - `origin_country: str | None` — country of origin (receiving office)
         - `family_id: str | None`

       - `WipoClient` class:
         - `__init__(self, credentials: WipoCredentials | None = None, retry_policy: RetryPolicy | None = None)`
         - `async def fetch_pct_applications(self, ipc_codes: list[str], since: date, batch_size: int = 100) -> AsyncIterator[PctApplication]` — search PATENTSCOPE for PCT applications by IPC codes published since a date. Paginate with offset/limit. Use `self._retry.execute()` for HTTP calls.
         - `async def fetch_pct_by_applicant(self, applicant_name: str, since: date) -> AsyncIterator[PctApplication]` — search by applicant name
         - `@staticmethod def _parse_patentscope_result(data: dict[str, Any]) -> PctApplication | None` — parse a single result from the PATENTSCOPE API response

    2. Create `src/aegis/sources/wipo_test.py` with fixture-based tests:

       - `SAMPLE_PATENTSCOPE_RESPONSE` fixture dict
       - `test_parse_patentscope_result()` — verify parsing
       - `test_pct_application_model()` — verify model creation
       - `test_fetch_pagination()` — mock API, verify pagination with respx
       - `test_wipo_credentials_model()` — verify credentials model

    ## Files to modify
    - `src/aegis/sources/wipo.py` — CREATE new file
    - `src/aegis/sources/wipo_test.py` — CREATE new file

    ## Code patterns to follow
    - Match `EpoClient` pattern exactly: credentials model, `__init__` with optional retry_policy, async fetch methods returning AsyncIterator, static parse method
    - Match `epo_test.py` test pattern: fixture dicts, `@pytest.mark.asyncio`, `@respx.mock`, `Response` from httpx
    - Use `from aegis.sources.retry import RetryConfig, RetryPolicy`

    ## Acceptance criteria
    - `WipoClient` importable from `aegis.sources.wipo`
    - `PctApplication` model works with all fields
    - At least 4 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/wipo_test.py -v && uv run mypy src/aegis/sources/wipo.py --strict
    ```

### 7. ERC Grant Client

- **Task ID**: erc-client
- **Role**: builder
- **Depends On**: non-us-grant-model
- **Assigned To**: builder-1
- **Description**: |
    Build a typed client for European Research Council (ERC) grant data. ERC publishes grant data via the CORDIS (Community Research and Development Information Service) API.

    ## What to do

    1. Create `src/aegis/sources/erc.py` with:

       - `from __future__ import annotations` at top

       - `CORDIS_API_URL = "https://cordis.europa.eu/api/v1"` — base URL for CORDIS

       - `ErcClient` class:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async def fetch_grants(self, subject_areas: list[str] | None = None, since_year: int | None = None, batch_size: int = 100) -> AsyncIterator[NonUsGrantRecord]` — fetch ERC grants from CORDIS, filtering by subject area and start year. Paginate with offset/limit. Use `self._retry.execute()`. Each result is converted to `NonUsGrantRecord` with `funder="ERC"`, `funder_country="EU"`, `source="erc"`.
         - `async def fetch_grants_by_pi(self, pi_name: str) -> AsyncIterator[NonUsGrantRecord]` — search by PI name
         - `@staticmethod def _parse_cordis_project(data: dict[str, Any]) -> NonUsGrantRecord | None` — parse a CORDIS project record. Extract: project acronym + ID as grant_reference, title, abstract (objective), PI names from participants, institution from host institution, EUR amount, start/end dates, subject areas from euroSciVoc or similar.

    2. Create `src/aegis/sources/erc_test.py` with fixture-based tests:

       - `SAMPLE_CORDIS_RESPONSE` fixture dict mimicking CORDIS API structure
       - `test_parse_cordis_project()` — verify parsing to NonUsGrantRecord
       - `test_erc_grant_has_correct_funder()` — verify funder="ERC", source="erc"
       - `test_fetch_pagination()` — mock API, verify pagination with respx
       - At least 4 tests total

    ## Files to modify
    - `src/aegis/sources/erc.py` — CREATE new file
    - `src/aegis/sources/erc_test.py` — CREATE new file

    ## Code patterns to follow
    - Match `ReporterClient` pattern: `__init__` with optional retry_policy, async fetch methods returning `AsyncIterator`, static parse method
    - Return `NonUsGrantRecord` from `aegis.sources.non_us_grants` (not a custom model)
    - Match test pattern from `reporter_test.py`

    ## Acceptance criteria
    - `ErcClient` importable from `aegis.sources.erc`
    - Fetch methods return `NonUsGrantRecord` with `funder="ERC"` and `source="erc"`
    - At least 4 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/erc_test.py -v && uv run mypy src/aegis/sources/erc.py --strict
    ```

### 8. Horizon Europe Grant Client

- **Task ID**: horizon-europe-client
- **Role**: builder
- **Depends On**: non-us-grant-model
- **Assigned To**: builder-1
- **Description**: |
    Build a typed client for Horizon Europe framework programme grants. Horizon Europe also uses the CORDIS API but with different programme filtering than ERC.

    ## What to do

    1. Create `src/aegis/sources/horizon_europe.py` with:

       - `from __future__ import annotations` at top

       - `CORDIS_API_URL = "https://cordis.europa.eu/api/v1"` — same base URL as ERC

       - `HorizonEuropeClient` class:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async def fetch_grants(self, programme_part: str | None = None, since_year: int | None = None, batch_size: int = 100) -> AsyncIterator[NonUsGrantRecord]` — fetch Horizon Europe projects from CORDIS. Filter by `frameworkProgramme=HORIZON` to distinguish from older FP7/H2020. Paginate. Use `self._retry.execute()`. Each result converted to `NonUsGrantRecord` with `funder="Horizon Europe"`, `funder_country="EU"`, `source="horizon_europe"`.
         - `async def fetch_grants_by_institution(self, institution: str) -> AsyncIterator[NonUsGrantRecord]` — search by host institution
         - `@staticmethod def _parse_horizon_project(data: dict[str, Any]) -> NonUsGrantRecord | None` — parse CORDIS response. Similar to ERC parsing but with programme-specific field extraction.

    2. Create `src/aegis/sources/horizon_europe_test.py` with fixture-based tests:

       - `SAMPLE_HORIZON_RESPONSE` fixture dict
       - `test_parse_horizon_project()` — verify parsing
       - `test_horizon_grant_funder()` — verify funder="Horizon Europe", source="horizon_europe"
       - `test_fetch_pagination()` — mock API with respx
       - At least 4 tests total

    ## Files to modify
    - `src/aegis/sources/horizon_europe.py` — CREATE new file
    - `src/aegis/sources/horizon_europe_test.py` — CREATE new file

    ## Code patterns to follow
    - Same pattern as ERC client (they share the CORDIS API)
    - Return `NonUsGrantRecord` from `aegis.sources.non_us_grants`

    ## Acceptance criteria
    - `HorizonEuropeClient` importable
    - Returns `NonUsGrantRecord` with correct funder/source
    - At least 4 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/horizon_europe_test.py -v && uv run mypy src/aegis/sources/horizon_europe.py --strict
    ```

### 9. MRC (UK) Grant Client

- **Task ID**: mrc-client
- **Role**: builder
- **Depends On**: non-us-grant-model
- **Assigned To**: builder-2
- **Description**: |
    Build a typed client for UK Medical Research Council (MRC) grant data. MRC publishes grant data via the Gateway to Research (GtR) API.

    ## What to do

    1. Create `src/aegis/sources/mrc.py` with:

       - `from __future__ import annotations` at top

       - `GTR_API_URL = "https://gtr.ukri.org/gtr/api"` — base URL for GtR

       - `MrcClient` class:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async def fetch_grants(self, search_term: str | None = None, since_year: int | None = None, batch_size: int = 100) -> AsyncIterator[NonUsGrantRecord]` — fetch MRC grants from GtR API. Filter by funder "MRC" in the GtR query. Paginate with `page` and `fetchSize` params. Use `self._retry.execute()`. Convert to `NonUsGrantRecord` with `funder="MRC"`, `funder_country="GB"`, `source="mrc"`.
         - `async def fetch_grants_by_pi(self, pi_name: str) -> AsyncIterator[NonUsGrantRecord]` — search GtR by PI name
         - `@staticmethod def _parse_gtr_project(data: dict[str, Any]) -> NonUsGrantRecord | None` — parse GtR project response. Extract: grant reference from identifiers, title, abstract from abstractText, PI names from principalInvestigator, institution from lead organisation, GBP amount from fund, start/end dates, research topics as subject_areas.

    2. Create `src/aegis/sources/mrc_test.py` with fixture-based tests:

       - `SAMPLE_GTR_RESPONSE` fixture dict mimicking GtR API structure
       - `test_parse_gtr_project()` — verify parsing
       - `test_mrc_grant_metadata()` — verify funder="MRC", funder_country="GB", source="mrc"
       - `test_fetch_pagination()` — mock API with respx
       - `test_fetch_grants_by_pi()` — mock PI search
       - At least 5 tests total

    ## Files to modify
    - `src/aegis/sources/mrc.py` — CREATE new file
    - `src/aegis/sources/mrc_test.py` — CREATE new file

    ## Code patterns to follow
    - Match `ReporterClient` pattern from `src/aegis/sources/reporter.py`
    - Return `NonUsGrantRecord` from `aegis.sources.non_us_grants`
    - Test pattern from `reporter_test.py` with respx mocking

    ## Acceptance criteria
    - `MrcClient` importable from `aegis.sources.mrc`
    - Returns `NonUsGrantRecord` with `funder="MRC"`, `funder_country="GB"`, `source="mrc"`
    - At least 5 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/mrc_test.py -v && uv run mypy src/aegis/sources/mrc.py --strict
    ```

### 10. CIHR (Canada) Grant Client

- **Task ID**: cihr-client
- **Role**: builder
- **Depends On**: non-us-grant-model
- **Assigned To**: builder-2
- **Description**: |
    Build a typed client for Canadian Institutes of Health Research (CIHR) grant data. CIHR publishes funded research via the CIHR Funding Decisions Database API.

    ## What to do

    1. Create `src/aegis/sources/cihr.py` with:

       - `from __future__ import annotations` at top

       - `CIHR_API_URL = "https://webapps.cihr-irsc.gc.ca/decisions/api/v1"` — base URL

       - `CihrClient` class:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async def fetch_grants(self, keywords: list[str] | None = None, since_year: int | None = None, batch_size: int = 100) -> AsyncIterator[NonUsGrantRecord]` — fetch CIHR grants. Paginate. Use `self._retry.execute()`. Convert to `NonUsGrantRecord` with `funder="CIHR"`, `funder_country="CA"`, `source="cihr"`, `currency="CAD"`.
         - `async def fetch_grants_by_pi(self, pi_name: str) -> AsyncIterator[NonUsGrantRecord]` — search by PI
         - `@staticmethod def _parse_cihr_grant(data: dict[str, Any]) -> NonUsGrantRecord | None` — parse CIHR response. Extract: application ID as grant_reference, title, PI names, institution, CAD amount, fiscal year to dates, research areas as subject_areas.

    2. Create `src/aegis/sources/cihr_test.py` with fixture-based tests:

       - `SAMPLE_CIHR_RESPONSE` fixture dict
       - `test_parse_cihr_grant()` — verify parsing
       - `test_cihr_grant_metadata()` — verify funder="CIHR", currency="CAD", source="cihr"
       - `test_fetch_pagination()` — mock API
       - At least 4 tests total

    ## Files to modify
    - `src/aegis/sources/cihr.py` — CREATE new file
    - `src/aegis/sources/cihr_test.py` — CREATE new file

    ## Code patterns to follow
    - Match `ReporterClient` pattern
    - Return `NonUsGrantRecord` from `aegis.sources.non_us_grants`

    ## Acceptance criteria
    - `CihrClient` importable from `aegis.sources.cihr`
    - Returns `NonUsGrantRecord` with correct metadata
    - At least 4 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/cihr_test.py -v && uv run mypy src/aegis/sources/cihr.py --strict
    ```

### 11. JST/KAKEN (Japan) Grant Client with Transliteration

- **Task ID**: kaken-client
- **Role**: builder
- **Depends On**: non-us-grant-model, add-cutlet-dep
- **Assigned To**: builder-2
- **Description**: |
    Build a typed client for Japanese grant data from JST (Japan Science and Technology Agency) and KAKEN (Grants-in-Aid for Scientific Research). KAKEN provides a public API (KAKEN API / CiNii Research API). This client requires special handling for Japanese-named researchers: store both native-script (kanji/kana) and romanized name variants.

    ## What to do

    1. Create `src/aegis/sources/jst_kaken.py` with:

       - `from __future__ import annotations` at top

       - `KAKEN_API_URL = "https://kaken.nii.ac.jp/api/v1"` — KAKEN search API base URL
       - `CINII_API_URL = "https://cir.nii.ac.jp/api/v1"` — CiNii Research API alternative

       - `KakenResearcher(BaseModel)` — frozen Pydantic model:
         - `researcher_number: str` — KAKEN researcher number
         - `name_ja: str | None` — name in Japanese (kanji)
         - `name_en: str | None` — name in English/romaji
         - `name_kana: str | None` — name in kana
         - `name_romaji: str | None` — auto-transliterated romaji (from cutlet)
         - `affiliation_ja: str | None` — affiliation in Japanese
         - `affiliation_en: str | None` — affiliation in English
         - `orcid: str | None`

       - `def transliterate_japanese_name(name_ja: str) -> str` — uses `cutlet.Cutlet()` to convert Japanese name to romaji (Hepburn romanization). Wrap in try/except: if cutlet fails (e.g., non-Japanese text input), return the original string. Import cutlet inside the function to avoid import errors if cutlet is not installed.

       - `def build_name_variants(researcher: KakenResearcher) -> list[str]` — collect all non-None name forms into a list for the `Candidate.name_variants` field. Include: name_ja, name_en, name_kana, name_romaji. Deduplicate.

       - `KakenClient` class:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async def fetch_grants(self, keywords: list[str] | None = None, since_year: int | None = None, batch_size: int = 100) -> AsyncIterator[NonUsGrantRecord]` — fetch KAKEN grants. Paginate. Use `self._retry.execute()`. Convert to `NonUsGrantRecord` with `funder="KAKEN"`, `funder_country="JP"`, `source="kaken"`, `currency="JPY"`.
         - `async def fetch_grants_by_researcher(self, researcher_number: str) -> AsyncIterator[NonUsGrantRecord]` — search by KAKEN researcher number
         - `async def fetch_researcher(self, researcher_number: str) -> KakenResearcher | None` — fetch researcher profile including Japanese-name fields. Auto-transliterate name_ja to populate name_romaji.
         - `@staticmethod def _parse_kaken_grant(data: dict[str, Any]) -> NonUsGrantRecord | None` — parse KAKEN API response. Extract: grant number as grant_reference, title (prefer English, fall back to Japanese), PI names (both ja and en), institution, JPY amount, fiscal year to dates, research category as subject_areas.
         - `@staticmethod def _parse_researcher(data: dict[str, Any]) -> KakenResearcher | None` — parse researcher profile data

    2. Create `src/aegis/sources/jst_kaken_test.py` with fixture-based tests:

       - `SAMPLE_KAKEN_RESPONSE` fixture dict mimicking KAKEN API structure with Japanese text
       - `SAMPLE_RESEARCHER_RESPONSE` fixture dict with Japanese and English name fields
       - `test_parse_kaken_grant()` — verify parsing
       - `test_kaken_grant_metadata()` — verify funder="KAKEN", currency="JPY", source="kaken"
       - `test_transliterate_japanese_name()` — verify transliteration produces romaji output (test with a simple katakana name)
       - `test_build_name_variants()` — verify all name forms are collected and deduplicated
       - `test_parse_researcher()` — verify researcher model with Japanese fields
       - `test_fetch_pagination()` — mock API
       - At least 7 tests total

    ## Files to modify
    - `src/aegis/sources/jst_kaken.py` — CREATE new file
    - `src/aegis/sources/jst_kaken_test.py` — CREATE new file

    ## Code patterns to follow
    - Match `ReporterClient` pattern for grant fetching
    - Use `cutlet.Cutlet()` for transliteration (import inside function)
    - Return `NonUsGrantRecord` from `aegis.sources.non_us_grants`

    ## Acceptance criteria
    - `KakenClient` importable from `aegis.sources.jst_kaken`
    - `KakenResearcher` model stores Japanese name variants
    - `transliterate_japanese_name` converts Japanese text to romaji
    - `build_name_variants` collects and deduplicates name forms
    - Returns `NonUsGrantRecord` with correct metadata
    - At least 7 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/jst_kaken_test.py -v && uv run mypy src/aegis/sources/jst_kaken.py --strict
    ```

### 12. NSFC (China) Grant Client — Best-Effort

- **Task ID**: nsfc-client
- **Role**: builder
- **Depends On**: non-us-grant-model
- **Assigned To**: builder-2
- **Description**: |
    Build a typed client for National Natural Science Foundation of China (NSFC) grant data. NSFC data is partially restricted; this client ingests only publicly accessible records and sets an explicit coverage caveat on every record.

    ## What to do

    1. Create `src/aegis/sources/nsfc.py` with:

       - `from __future__ import annotations` at top

       - `NSFC_API_URL = "https://kd.nsfc.cn/api/v1"` — NSFC public query API (or open data portal)

       - `NSFC_COVERAGE_CAVEAT = "NSFC data is best-effort from public records only. Coverage is partial — not all funded projects are publicly accessible. Grant amounts and detailed project information may be incomplete."` — constant string used for all NSFC records

       - `NsfcClient` class:
         - `__init__(self, retry_policy: RetryPolicy | None = None)`
         - `async def fetch_grants(self, keywords: list[str] | None = None, since_year: int | None = None, batch_size: int = 50) -> AsyncIterator[NonUsGrantRecord]` — fetch NSFC grants from public API. **Lower default batch_size (50)** due to rate constraints. Use `self._retry.execute()`. Convert to `NonUsGrantRecord` with `funder="NSFC"`, `funder_country="CN"`, `source="nsfc"`, `currency="CNY"`, and `coverage_caveat=NSFC_COVERAGE_CAVEAT`.
         - `async def fetch_grants_by_pi(self, pi_name: str) -> AsyncIterator[NonUsGrantRecord]` — search by PI name (supports both Chinese and English names)
         - `@staticmethod def _parse_nsfc_grant(data: dict[str, Any]) -> NonUsGrantRecord | None` — parse NSFC response. Extract: grant code as grant_reference, title (Chinese with English if available), PI names, institution, CNY amount, start/end dates, discipline code as subject_areas. Always set `coverage_caveat=NSFC_COVERAGE_CAVEAT`.

    2. Create `src/aegis/sources/nsfc_test.py` with fixture-based tests:

       - `SAMPLE_NSFC_RESPONSE` fixture dict
       - `test_parse_nsfc_grant()` — verify parsing
       - `test_nsfc_coverage_caveat()` — verify every record has the coverage caveat string
       - `test_nsfc_grant_metadata()` — verify funder="NSFC", currency="CNY", source="nsfc"
       - `test_fetch_pagination()` — mock API
       - `test_nsfc_lower_batch_size()` — verify default batch_size is 50 (not 100)
       - At least 5 tests total

    ## Files to modify
    - `src/aegis/sources/nsfc.py` — CREATE new file
    - `src/aegis/sources/nsfc_test.py` — CREATE new file

    ## Code patterns to follow
    - Match `ReporterClient` pattern
    - Return `NonUsGrantRecord` from `aegis.sources.non_us_grants`
    - Always set `coverage_caveat` on NSFC records

    ## Acceptance criteria
    - `NsfcClient` importable from `aegis.sources.nsfc`
    - Every `NonUsGrantRecord` from NSFC has `coverage_caveat` set (not None)
    - Default `batch_size` is 50
    - Returns `NonUsGrantRecord` with correct metadata
    - At least 5 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/sources/nsfc_test.py -v && uv run mypy src/aegis/sources/nsfc.py --strict
    ```

### 13. Per-Region Coverage Diagnostics

- **Task ID**: regional-coverage
- **Role**: builder
- **Depends On**: non-us-grant-model, ror-expansion
- **Assigned To**: builder-3
- **Description**: |
    Build per-region coverage diagnostics that break down cohort coverage by geographic region (US, EU, UK, Canada, Japan, China, Rest-of-World). Each region reports identity-resolution coverage, source coverage, and per-population breakdown.

    ## What to do

    1. Create `src/aegis/observability/regional_coverage.py` with:

       - `from __future__ import annotations` at top

       - `RegionalCoverageMetrics(BaseModel)` — frozen Pydantic model:
         - `total_candidates: int`
         - `per_region_count: dict[str, int]` — key is Region value, value is count
         - `per_region_pct: dict[str, float]` — key is Region value, value is percentage
         - `non_us_ratio: float` — fraction of candidates NOT in US region
         - `dominant_region: str` — Region with highest count
         - `dominant_region_pct: float` — percentage of dominant region
         - `is_geographically_biased: bool` — True if dominant_region_pct > 75.0
         - `per_region_linkage_confidence: dict[str, float]` — median linkage confidence per region
         - `per_region_source_coverage: dict[str, dict[str, float]]` — per-region, per-source coverage %
         - `coverage_caveats: list[str]` — list of caveat strings (e.g., "NSFC coverage is partial")
         - `regional_caveat: str | None` — the API-response caveat string, or None if not biased

       - `REGIONAL_CAVEAT_THRESHOLD = 75.0` — percentage threshold for triggering API caveat

       - `def build_regional_caveat(dominant_region: str, pct: float) -> str` — returns a string like "Results are >75% from {dominant_region} ({pct:.1f}%). Coverage for other regions may be incomplete. Interpret global ranking with this regional weighting in mind."

       - `RegionalCoverageDashboard` class:
         - `__init__(self, store: CandidateStore)` — takes CandidateStore (from `aegis.storage.candidate_store`). Import with TYPE_CHECKING guard.
         - `def compute(self, cohort_candidates: list[str] | None = None) -> RegionalCoverageMetrics` — compute regional coverage:
           1. Load candidates from store (all or by UUID list)
           2. For each candidate, derive region from affiliations using `candidate_region()` from `aegis.sources.non_us_grants`
           3. Count per-region, compute percentages
           4. Compute non-US ratio
           5. Find dominant region and check if > REGIONAL_CAVEAT_THRESHOLD
           6. Compute per-region median linkage confidence
           7. Compute per-region source coverage (which sources have artifacts per region)
           8. Build coverage_caveats list (include NSFC caveat if China region present)
           9. Build regional_caveat string if biased
         - `def generate_html_report(self, metrics: RegionalCoverageMetrics) -> str` — HTML dashboard with per-region bar chart, non-US ratio gauge, bias warning if applicable. Follow pattern from `src/aegis/observability/coverage.py`.
         - `def compare(self, current: RegionalCoverageMetrics, previous: RegionalCoverageMetrics) -> dict[str, float]` — return deltas between two snapshots (follow pattern from `coverage.py`)

    2. Create `src/aegis/observability/regional_coverage_test.py` with tests:

       - Build mock candidates with different affiliations (US, UK, JP, CN, FR, CA, BR)
       - `test_compute_basic()` — verify per-region counts and percentages
       - `test_non_us_ratio()` — verify non-US ratio calculation
       - `test_geographic_bias_detection()` — cohort with >75% US triggers `is_geographically_biased=True`
       - `test_regional_caveat_text()` — verify caveat text when biased
       - `test_no_caveat_when_balanced()` — verify no caveat when balanced
       - `test_build_regional_caveat()` — verify caveat string format
       - `test_empty_cohort()` — verify empty cohort returns zeros
       - At least 7 tests total

    The tests should NOT use DuckDB — instead, mock the CandidateStore or pass pre-built candidate lists. Use the `Candidate` model from `aegis.storage.schema` to build test fixtures directly.

    ## Files to modify
    - `src/aegis/observability/regional_coverage.py` — CREATE new file
    - `src/aegis/observability/regional_coverage_test.py` — CREATE new file

    ## Code patterns to follow
    - Match `CoverageDiagnostics` pattern from `src/aegis/observability/coverage.py` exactly (CandidateStore init, compute method, HTML report, compare method)
    - Match `ClinicianCoverageDashboard` pattern from `src/aegis/observability/clinician_coverage.py` (coverage_caveats list)
    - Use `TYPE_CHECKING` guard for CandidateStore import (same as coverage.py)
    - Frozen Pydantic models with `model_config = ConfigDict(frozen=True)`

    ## Acceptance criteria
    - `RegionalCoverageDashboard` importable
    - `compute()` returns `RegionalCoverageMetrics` with all fields populated
    - Bias detection triggers at >75% from one region
    - Regional caveat is a human-readable string
    - Non-US ratio computed correctly
    - At least 7 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/observability/regional_coverage_test.py -v && uv run mypy src/aegis/observability/regional_coverage.py --strict
    ```

### 14. Geographic-Coverage Tracking Over Time

- **Task ID**: geographic-tracking
- **Role**: builder
- **Depends On**: regional-coverage
- **Assigned To**: builder-3
- **Description**: |
    Build geographic-coverage tracking that records per-region ratios over time as new sources come online. Tracks trends and alerts when the non-US ratio regresses below target (40%).

    ## What to do

    1. Create `src/aegis/observability/geographic_tracking.py` with:

       - `from __future__ import annotations` at top

       - `NON_US_TARGET_RATIO = 0.40` — target: 40%+ non-US candidates

       - `GeographicSnapshot(BaseModel)` — frozen Pydantic model:
         - `timestamp: datetime`
         - `total_candidates: int`
         - `per_region_count: dict[str, int]`
         - `per_region_pct: dict[str, float]`
         - `non_us_ratio: float`
         - `new_sources_active: list[str]` — which non-US sources were active at this time

       - `GeographicTrend(BaseModel)` — frozen Pydantic model:
         - `snapshots: list[GeographicSnapshot]`
         - `current_non_us_ratio: float`
         - `target_non_us_ratio: float`
         - `target_met: bool`
         - `ratio_trend: str` — "improving", "stable", or "regressing" based on last 4 snapshots
         - `regression_alert: bool` — True if ratio dropped >5% from previous snapshot

       - `GeographicTracker` class:
         - `__init__(self, store_path: str = "geographic_tracking.jsonl")` — path to JSONL file for snapshot persistence
         - `def record_snapshot(self, metrics: RegionalCoverageMetrics, active_sources: list[str]) -> GeographicSnapshot` — create a snapshot from current RegionalCoverageMetrics and append to JSONL store. Import `RegionalCoverageMetrics` from `aegis.observability.regional_coverage`.
         - `def load_history(self) -> list[GeographicSnapshot]` — read all snapshots from JSONL
         - `def compute_trend(self) -> GeographicTrend` — load history, compute trend direction and regression alert:
           - "improving" if last 4 snapshots show increasing non_us_ratio
           - "regressing" if last 4 show decreasing
           - "stable" otherwise
           - regression_alert if current - previous > 0.05 drop
         - `def generate_prometheus_metrics(self) -> str` — emit `aegis_geographic_non_us_ratio` gauge, `aegis_geographic_target_met` gauge (0/1), per-region count gauges. Follow pattern from `src/aegis/observability/freshness.py`.

    2. Create `src/aegis/observability/geographic_tracking_test.py` with tests:

       - `test_record_snapshot()` — verify snapshot creation and JSONL persistence
       - `test_load_history()` — verify reading back from JSONL
       - `test_compute_trend_improving()` — 4 snapshots with increasing ratio -> "improving"
       - `test_compute_trend_regressing()` — 4 snapshots with decreasing ratio -> "regressing"
       - `test_regression_alert()` — >5% drop triggers alert
       - `test_target_met()` — non_us_ratio >= 0.40 -> target_met=True
       - `test_target_not_met()` — non_us_ratio < 0.40 -> target_met=False
       - At least 7 tests total. Use `tmp_path` pytest fixture for JSONL file path.

    ## Files to modify
    - `src/aegis/observability/geographic_tracking.py` — CREATE new file
    - `src/aegis/observability/geographic_tracking_test.py` — CREATE new file

    ## Code patterns to follow
    - Match JSONL persistence pattern (write one JSON line per snapshot)
    - Match `FreshnessMetrics` Prometheus gauge pattern from `src/aegis/observability/freshness.py`
    - Frozen Pydantic models

    ## Acceptance criteria
    - `GeographicTracker` importable
    - Snapshot persistence round-trips (write + read)
    - Trend computation correctly identifies improving/regressing/stable
    - Regression alert triggers on >5% drop
    - Target check uses 0.40 threshold
    - At least 7 tests, all passing
    - mypy strict passes

    ## Validation command
    ```bash
    uv run pytest src/aegis/observability/geographic_tracking_test.py -v && uv run mypy src/aegis/observability/geographic_tracking.py --strict
    ```

### 15. Update Source Module Exports

- **Task ID**: source-exports
- **Role**: builder
- **Depends On**: epo-full-coverage, wipo-client, erc-client, horizon-europe-client, mrc-client, cihr-client, kaken-client, nsfc-client
- **Assigned To**: builder-3
- **Description**: |
    Update `src/aegis/sources/__init__.py` to export all new source clients and models, following the existing pattern.

    ## What to do

    1. Edit `src/aegis/sources/__init__.py` to add imports and __all__ entries for:

       From `aegis.sources.non_us_grants`:
       - `NonUsGrantRecord`
       - `Region`
       - `country_to_region`
       - `candidate_region`

       From `aegis.sources.wipo`:
       - `WipoClient`
       - `WipoCredentials`
       - `PctApplication`

       From `aegis.sources.erc`:
       - `ErcClient`

       From `aegis.sources.horizon_europe`:
       - `HorizonEuropeClient`

       From `aegis.sources.mrc`:
       - `MrcClient`

       From `aegis.sources.cihr`:
       - `CihrClient`

       From `aegis.sources.jst_kaken`:
       - `KakenClient`
       - `KakenResearcher`

       From `aegis.sources.nsfc`:
       - `NsfcClient`
       - `NSFC_COVERAGE_CAVEAT`

    2. Add all new names to the `__all__` list in alphabetical order, matching existing style.

    3. Insert imports in alphabetical order by module name, matching existing style.

    ## Files to modify
    - `src/aegis/sources/__init__.py` — ADD imports and __all__ entries

    ## Code patterns to follow
    - Match existing import style exactly: `from aegis.sources.module_name import ClassName`
    - `__all__` entries in alphabetical order as strings

    ## Acceptance criteria
    - All new client classes importable via `from aegis.sources import XyzClient`
    - `NonUsGrantRecord` and `Region` importable via `from aegis.sources import NonUsGrantRecord, Region`
    - No import errors
    - Existing imports still work
    - mypy strict passes on __init__.py

    ## Validation command
    ```bash
    uv run python -c "
    from aegis.sources import (
        NonUsGrantRecord, Region, country_to_region, candidate_region,
        WipoClient, WipoCredentials, PctApplication,
        ErcClient, HorizonEuropeClient, MrcClient, CihrClient,
        KakenClient, KakenResearcher, NsfcClient, NSFC_COVERAGE_CAVEAT,
    )
    print('All source exports OK')
    " && uv run mypy src/aegis/sources/__init__.py --strict
    ```

### 16. Validate All

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: non-us-grant-model, grant-refs-migration, ror-expansion, add-cutlet-dep, epo-full-coverage, wipo-client, erc-client, horizon-europe-client, mrc-client, cihr-client, kaken-client, nsfc-client, regional-coverage, geographic-tracking, source-exports
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria.

    ## Validation Commands

    Run each of these commands. All must pass:

    ```bash
    # 1. All new source client tests
    uv run pytest src/aegis/sources/wipo_test.py src/aegis/sources/erc_test.py src/aegis/sources/horizon_europe_test.py src/aegis/sources/mrc_test.py src/aegis/sources/cihr_test.py src/aegis/sources/jst_kaken_test.py src/aegis/sources/nsfc_test.py -v

    # 2. EPO tests (existing + new)
    uv run pytest src/aegis/sources/epo_test.py -v

    # 3. Observability tests
    uv run pytest src/aegis/observability/regional_coverage_test.py src/aegis/observability/geographic_tracking_test.py -v

    # 4. Existing tests (no regression)
    uv run pytest src/aegis/sources/ src/aegis/storage/ src/aegis/identity/ src/aegis/observability/ -v

    # 5. mypy strict on all new files
    uv run mypy src/aegis/sources/non_us_grants.py src/aegis/sources/wipo.py src/aegis/sources/erc.py src/aegis/sources/horizon_europe.py src/aegis/sources/mrc.py src/aegis/sources/cihr.py src/aegis/sources/jst_kaken.py src/aegis/sources/nsfc.py src/aegis/observability/regional_coverage.py src/aegis/observability/geographic_tracking.py --strict

    # 6. ruff check on all new files
    uv run ruff check src/aegis/sources/non_us_grants.py src/aegis/sources/wipo.py src/aegis/sources/erc.py src/aegis/sources/horizon_europe.py src/aegis/sources/mrc.py src/aegis/sources/cihr.py src/aegis/sources/jst_kaken.py src/aegis/sources/nsfc.py src/aegis/observability/regional_coverage.py src/aegis/observability/geographic_tracking.py

    # 7. Source exports
    uv run python -c "
    from aegis.sources import (
        NonUsGrantRecord, Region, country_to_region, candidate_region,
        WipoClient, WipoCredentials, PctApplication,
        ErcClient, HorizonEuropeClient, MrcClient, CihrClient,
        KakenClient, KakenResearcher, NsfcClient, NSFC_COVERAGE_CAVEAT,
    )
    print('All source exports OK')
    "

    # 8. Region mapping
    uv run python -c "
    from aegis.sources.non_us_grants import Region, country_to_region
    assert country_to_region('US') == Region.US
    assert country_to_region('FR') == Region.EU
    assert country_to_region('GB') == Region.UK
    assert country_to_region('CA') == Region.CANADA
    assert country_to_region('JP') == Region.JAPAN
    assert country_to_region('CN') == Region.CHINA
    assert country_to_region(None) == Region.REST_OF_WORLD
    print('Region mapping OK')
    "

    # 9. Migration
    uv run python -c "
    import duckdb
    conn = duckdb.connect(':memory:')
    conn.execute('CREATE TABLE candidates (uuid TEXT PRIMARY KEY, data JSON NOT NULL, linkage_confidence DOUBLE, created_at TIMESTAMP, updated_at TIMESTAMP)')
    sql = open('src/aegis/storage/migrations/004_grant_refs.sql').read()
    conn.execute(sql)
    cols = [r[0] for r in conn.execute('DESCRIBE grant_refs').fetchall()]
    assert 'grant_reference' in cols
    print('Migration OK')
    "

    # 10. ROR expansion
    uv run python -c "
    from aegis.identity.ror import _CURATED_ROR
    assert len(_CURATED_ROR) >= 95, f'Only {len(_CURATED_ROR)} entries'
    print(f'ROR: {len(_CURATED_ROR)} entries OK')
    "

    # 11. NSFC coverage caveat
    uv run python -c "
    from aegis.sources.nsfc import NSFC_COVERAGE_CAVEAT
    assert 'best-effort' in NSFC_COVERAGE_CAVEAT.lower() or 'partial' in NSFC_COVERAGE_CAVEAT.lower()
    print('NSFC caveat OK')
    "
    ```

    ## Acceptance Criteria

    All of the following must be true:
    - [ ] 7 new source client files exist and are importable (wipo, erc, horizon_europe, mrc, cihr, jst_kaken, nsfc)
    - [ ] NonUsGrantRecord shared model exists with all required fields
    - [ ] Region enum has 7 values
    - [ ] country_to_region mapping works for all 7 regions
    - [ ] EPO client has EP_MEMBER_STATES (39 entries), fetch_patents_by_country, fetch_all_member_state_patents
    - [ ] WIPO client has PctApplication model and fetch methods
    - [ ] ERC client returns NonUsGrantRecord with funder="ERC"
    - [ ] Horizon Europe client returns NonUsGrantRecord with funder="Horizon Europe"
    - [ ] MRC client returns NonUsGrantRecord with funder="MRC", funder_country="GB"
    - [ ] CIHR client returns NonUsGrantRecord with funder="CIHR", currency="CAD"
    - [ ] KAKEN client has transliteration support and KakenResearcher model
    - [ ] NSFC client sets coverage_caveat on every record
    - [ ] DuckDB migration 004_grant_refs.sql creates grant_refs table
    - [ ] ROR curated data has >= 95 entries covering JP, CN, GB, CA, EU
    - [ ] RegionalCoverageDashboard computes per-region breakdown
    - [ ] Regional caveat triggers at >75% from one region
    - [ ] GeographicTracker records snapshots, computes trends, detects regression
    - [ ] Non-US ratio target is 40%
    - [ ] All new exports registered in sources/__init__.py
    - [ ] All tests pass (new and existing — no regression)
    - [ ] mypy strict passes on all new files
    - [ ] ruff check passes on all new files
    - [ ] cutlet dependency added to pyproject.toml

### 17. Update Design Document

- **Task ID**: update-design-scoring
- **Role**: design-updater
- **Depends On**: validate-all
- **Assigned To**: design-updater
- **Description**: |
    Update the living design document for the scoring domain to reflect
    what was actually built in this plan.

    ## Target Design Doc
    docs/design/scoring.md

    ## Spec File
    specs/aegis-phase3d-geographic-broadening.md

    ## Scope
    Geographic broadening: new non-US source clients (WIPO, ERC, Horizon Europe,
    MRC, CIHR, JST/KAKEN, NSFC), EPO full coverage extension, NonUsGrantRecord
    shared model, Region enum and country-to-region mapping, per-region coverage
    diagnostics with API caveat, geographic-coverage tracking over time, ROR
    curated data expansion, KAKEN transliteration, NSFC best-effort coverage caveat,
    grant_refs DuckDB migration.

    ## Prior Decisions to Check
    - Source client pattern (httpx + Pydantic + RetryPolicy) established in Phase 0b
    - ROR resolver country field established in Phase 0c
    - PatentRecord reuse across USPTO/EPO established in Phase 2a
    - CoverageDiagnostics pattern established in Phase 0e
    - Prometheus metric emission pattern from Phase 1d

    ## What to Record
    Read git diff HEAD~1 HEAD, then the changed source files, then the existing
    design doc. Update Current Design to match the implementation. Append a
    Design Decision entry for each non-trivial architectural choice made in
    this build. Every claim must cite a file:line from the actual code.

    Key decisions to document:
    1. NonUsGrantRecord as shared model vs per-source models (and why)
    2. Region derivation from ROR-normalized affiliation (not from grant funder country)
    3. NSFC best-effort pattern with coverage_caveat field
    4. KAKEN transliteration via cutlet with graceful fallback
    5. Regional caveat threshold at 75%
    6. Geographic tracking via JSONL snapshots
    7. grant_refs table (migration 004) for non-US grant references

## Acceptance Criteria

- 7 new typed source clients (WIPO, ERC, Horizon Europe, MRC, CIHR, JST/KAKEN, NSFC) exist and pass tests
- EPO client extended with full member-state coverage (39 states)
- `NonUsGrantRecord` shared model with `coverage_caveat` field
- `Region` enum and `country_to_region()` function with 7 regions
- KAKEN client stores Japanese name variants and performs transliteration
- NSFC client sets `coverage_caveat` on every record
- DuckDB migration `004_grant_refs.sql` creates `grant_refs` table
- ROR curated data expanded to 95+ entries covering JP, CN, GB, CA, EU, AU
- `RegionalCoverageDashboard` computes per-region coverage with bias detection at >75%
- `GeographicTracker` records snapshots and computes trend (improving/stable/regressing)
- Non-US ratio target is 40%, tracked over time with regression alerting
- All new clients registered in `src/aegis/sources/__init__.py`
- All tests pass (50+ new tests, zero existing test regression)
- mypy strict passes on all new files
- ruff check passes on all new files
- `cutlet` dependency added to `pyproject.toml`

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# All new and existing tests
uv run pytest src/aegis/sources/ src/aegis/storage/ src/aegis/identity/ src/aegis/observability/ -v

# mypy strict on all new files
uv run mypy src/aegis/sources/non_us_grants.py src/aegis/sources/wipo.py src/aegis/sources/erc.py src/aegis/sources/horizon_europe.py src/aegis/sources/mrc.py src/aegis/sources/cihr.py src/aegis/sources/jst_kaken.py src/aegis/sources/nsfc.py src/aegis/observability/regional_coverage.py src/aegis/observability/geographic_tracking.py --strict

# ruff check
uv run ruff check src/aegis/sources/non_us_grants.py src/aegis/sources/wipo.py src/aegis/sources/erc.py src/aegis/sources/horizon_europe.py src/aegis/sources/mrc.py src/aegis/sources/cihr.py src/aegis/sources/jst_kaken.py src/aegis/sources/nsfc.py src/aegis/observability/regional_coverage.py src/aegis/observability/geographic_tracking.py

# Source exports smoke test
uv run python -c "
from aegis.sources import (
    NonUsGrantRecord, Region, country_to_region, candidate_region,
    WipoClient, WipoCredentials, PctApplication,
    ErcClient, HorizonEuropeClient, MrcClient, CihrClient,
    KakenClient, KakenResearcher, NsfcClient, NSFC_COVERAGE_CAVEAT,
)
print('All exports OK')
"

# Migration smoke test
uv run python -c "
import duckdb
conn = duckdb.connect(':memory:')
conn.execute('CREATE TABLE candidates (uuid TEXT PRIMARY KEY, data JSON NOT NULL, linkage_confidence DOUBLE, created_at TIMESTAMP, updated_at TIMESTAMP)')
sql = open('src/aegis/storage/migrations/004_grant_refs.sql').read()
conn.execute(sql)
print('Migration OK')
"
```

## Notes

- **cutlet dependency**: Add via `uv add cutlet>=0.4` or by editing pyproject.toml directly. cutlet requires a one-time download of its Japanese dictionary on first use; tests should mock the transliteration function if the dictionary download is unreliable in CI.
- **ROR IDs**: The ROR IDs listed in the ROR expansion task are representative. Builders should verify they are valid by checking the format (https://ror.org/ followed by alphanumeric). The exact IDs do not need to match real ROR records for Phase 3 since the curated subset is a bootstrapping mechanism that will be replaced by a full ROR dump in a future phase.
- **API endpoints**: The API URLs for KAKEN, NSFC, CORDIS, GtR, etc. are best-effort approximations. The source clients are designed to be testable with fixture data regardless of whether the actual APIs match these exact URLs. The important thing is the client pattern (typed, async, retry-wrapped) and the output model (NonUsGrantRecord).
- **EPO full coverage**: The "full coverage" extension adds per-member-state querying. The existing `fetch_patents` method still works for CPC-based queries across all EP patents. The new methods add country-specific access.
- **Geographic tracking JSONL**: The JSONL-based snapshot store is intentionally simple for Phase 3. A future phase may migrate this to DuckDB for richer time-series queries.
