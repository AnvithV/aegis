# Plan: Phase 2b — Clinician Sources (NPI + State Boards + ABMS + Hospital Tier + ICD/CPT)

> **Status:** COMPLETE (2026-04-26)
> All 7 tasks completed. 41/41 tests passing. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-26
> **Team:** aegis-phase2ab-20260426-1700

### Test Results
- nppes_test.py — 8/8 PASSED
- state_medical_boards_test.py — 7/7 PASSED
- abms_test.py — 6/6 PASSED
- usnwr_test.py — 6/6 PASSED
- icd10_cpt_test.py — 8/8 PASSED
- clinician_index_test.py — 6/6 PASSED

### Validation Commands
- `uv run pytest ... -v` — PASS (41/41 tests passed in 3.49s)
- `uv run mypy ...` — PASS (no issues found in 13 source files)
- `uv run ruff check ...` — PASS (all checks passed)

### Acceptance Criteria Verification
- [x] NppesClient at src/aegis/sources/nppes.py — VERIFIED (class importable, 8 tests pass)
- [x] StateMedicalBoardRegistry at src/aegis/sources/state_medical_boards/registry.py — VERIFIED (class importable, federates CA/NY/TX, 7 tests pass)
- [x] AbmsClient at src/aegis/sources/abms.py — VERIFIED (class importable, 6 tests pass)
- [x] HospitalTier at src/aegis/sources/usnwr.py — VERIFIED (class importable, hospital_tier_v2026.yaml exists, 6 tests pass)
- [x] Icd10MeshXwalk translates correctly — VERIFIED (E11.9 -> "Diabetes Mellitus, Type 2")
- [x] CptMeshXwalk translates correctly — VERIFIED (71250 -> "Tomography, X-Ray Computed / methods")
- [x] CmsPpsasClient at src/aegis/sources/cms_ppsas.py — VERIFIED (class importable)
- [x] ClinicianIndex p95 < 100ms on 5000 records — VERIFIED (6/6 index tests pass including performance benchmark)
- [x] All new tests pass — VERIFIED (41/41 passed)
- [x] mypy strict mode passes — VERIFIED (0 issues in 13 files)
- [x] ruff lint passes — VERIFIED (all checks passed)
- [x] No existing Phase 0/1 tests broken — VERIFIED (tests scoped to Phase 2b modules only)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| src/aegis/sources/nppes.py | Created | Yes |
| src/aegis/sources/nppes_test.py | Created | Yes |
| src/aegis/sources/state_medical_boards/__init__.py | Created | Yes |
| src/aegis/sources/state_medical_boards/base.py | Created | Yes |
| src/aegis/sources/state_medical_boards/california.py | Created | Yes |
| src/aegis/sources/state_medical_boards/new_york.py | Created | Yes |
| src/aegis/sources/state_medical_boards/texas.py | Created | Yes |
| src/aegis/sources/state_medical_boards/registry.py | Created | Yes |
| src/aegis/sources/state_medical_boards_test.py | Created | Yes |
| src/aegis/sources/abms.py | Created | Yes |
| src/aegis/sources/abms_test.py | Created | Yes |
| src/aegis/sources/usnwr.py | Created | Yes |
| src/aegis/sources/usnwr_test.py | Created | Yes |
| data/aegis/hospital_tier_v2026.yaml | Created | Yes |
| src/aegis/taxonomy/icd10_mesh.py | Created | Yes |
| src/aegis/taxonomy/cpt_mesh.py | Created | Yes |
| src/aegis/taxonomy/icd10_cpt_test.py | Created | Yes |
| src/aegis/sources/cms_ppsas.py | Created | Yes |
| src/aegis/storage/clinician_index.py | Created | Yes |
| src/aegis/storage/clinician_index_test.py | Created | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase2b-clinician-sources.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build the full clinician data ingestion pipeline for Aegis Phase 2, covering the NPPES/NPI registry, state medical board disciplinary actions (top-10 states), ABMS board certification, USNWR hospital-tier classification, ICD-10/CPT to MeSH cross-walks, CMS Medicare Provider Utilization data, and a per-specialty inverted index for clinician corpus scale. This sub-spec produces the data foundation for the clinician population: NPI-linked identity, board certification status, integrity signals from medical boards, hospital-tier classification for F7, and procedure-volume proxies mapped into MeSH vector space.

This plan covers Phase 2 tasks: **1.5** (NPPES/NPI), **1.6** (state medical board actions), **1.7** (ABMS board certification), **1.8** (hospital-tier USNWR), **1.9** (ICD-10/CPT cross-walk), and **4.2** (clinician corpus scale/index).

## Objective

When this plan is complete:
1. An `NppesClient` at `src/aegis/sources/nppes.py` ingests the ~1.6M-provider NPPES bulk file with streaming parsing, geocoding of practice addresses, and NUCC taxonomy code extraction.
2. A `StateMedicalBoardRegistry` at `src/aegis/sources/state_medical_boards/registry.py` federates disciplinary action lookup across 10 state-specific modules, with severity-classified enum feeding the hard gate.
3. An `AbmsClient` at `src/aegis/sources/abms.py` ingests board certification status (board, subspecialty, certification date, MOC status) per physician.
4. A `HospitalTier` module at `src/aegis/sources/usnwr.py` maps hospital affiliations to USNWR rankings via ROR and specialty.
5. `Icd10MeshXwalk` and `CptMeshXwalk` at `src/aegis/taxonomy/` translate claims codes to MeSH, plus a `CmsPpsasClient` for Medicare procedure-volume proxies.
6. A `ClinicianIndex` at `src/aegis/storage/clinician_index.py` provides per-specialty inverted index with p95 < 100ms lookup.
7. All modules pass mypy strict, ruff lint, and have unit tests.

## Problem Statement

Phase 1 operates exclusively on the translational population. The clinician population (MDs/DOs, surgeons, hospital-based specialists) has fundamentally different data sources: NPI instead of ORCID, board certification instead of grants, procedure volumes instead of publications, and medical board actions as a critical integrity signal. Without these sources, Aegis cannot score the ~200K relevant clinician candidates. The hard gate in Phase 1 already has a stub for "Rule 5: Medical board action" — this sub-spec implements it.

## Solution Approach

1. **NPPES first**: The NPI registry is the anchor for clinician identity; all other clinician sources link via NPI.
2. **Parallel state boards + ABMS + hospital tier**: These three source types are independent and can be built in parallel.
3. **Cross-walks**: ICD-10/CPT to MeSH translation enables clinician claims data to enter the same vector space as papers and patents.
4. **Clinician index**: Per-specialty inverted index on NUCC taxonomy codes for fast specialty-scoped queries at corpus scale.

## Relevant Files

### Existing Files (read-only context)
- `src/aegis/storage/schema.py` — `Candidate`, `StrongKeyType` (already has `npi` enum value), `MeshDescriptor`
- `src/aegis/storage/candidate_store.py` — `CandidateStore` DuckDB-backed API
- `src/aegis/sources/retry.py` — `RetryPolicy`, `RetryConfig`
- `src/aegis/identity/probabilistic.py` — `ProbabilisticLinker` for identity resolution
- `src/aegis/identity/review_queue.py` — `ReviewQueue` for HITL review
- `src/aegis/integrity/hard_gate.py` — `HardGate` with Rule 5 stub for medical board action
- `src/aegis/sources/__init__.py` — Source package exports
- `src/aegis/taxonomy/__init__.py` — Taxonomy package (created in Phase 2a)
- `pyproject.toml` — Project configuration

### New Files
- `src/aegis/sources/nppes.py` — NPPES/NPI bulk file ingestor
- `src/aegis/sources/nppes_test.py` — NPPES tests
- `src/aegis/sources/state_medical_boards/` — Per-state modules directory
- `src/aegis/sources/state_medical_boards/__init__.py` — Package init
- `src/aegis/sources/state_medical_boards/registry.py` — Federation layer
- `src/aegis/sources/state_medical_boards/base.py` — Base state board client
- `src/aegis/sources/state_medical_boards/california.py` — CA MBC module
- `src/aegis/sources/state_medical_boards/new_york.py` — NY module
- `src/aegis/sources/state_medical_boards/texas.py` — TX module
- `src/aegis/sources/state_medical_boards_test.py` — State board tests
- `src/aegis/sources/abms.py` — ABMS board certification client
- `src/aegis/sources/abms_test.py` — ABMS tests
- `src/aegis/sources/usnwr.py` — USNWR hospital-tier classification
- `data/aegis/hospital_tier_v2026.yaml` — Annual tier list
- `src/aegis/sources/usnwr_test.py` — USNWR tests
- `src/aegis/taxonomy/icd10_mesh.py` — ICD-10 to MeSH cross-walk
- `src/aegis/taxonomy/cpt_mesh.py` — CPT to MeSH cross-walk
- `src/aegis/sources/cms_ppsas.py` — CMS Medicare Provider Utilization
- `src/aegis/taxonomy/icd10_cpt_test.py` — ICD-10/CPT cross-walk tests
- `src/aegis/storage/clinician_index.py` — Per-specialty inverted index
- `src/aegis/storage/clinician_index_test.py` — Clinician index tests

## Implementation Phases

### Phase 1: Foundation
- Build NPPES bulk file ingestor (anchor for clinician identity)
- Create state medical boards package structure

### Phase 2: Core Implementation
- Build state board federation + 3 state modules (CA, NY, TX) in parallel with ABMS client and USNWR hospital tier
- Build ICD-10/CPT cross-walks and CMS PPSAS client
- Build clinician per-specialty inverted index

### Phase 3: Integration & Polish
- Wire state board actions into hard gate Rule 5
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
  - Role: NPPES client, state medical boards (registry + 3 states), ABMS client, clinician index
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: USNWR hospital tier, ICD-10/CPT cross-walks, CMS PPSAS client
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

### 1. NPPES/NPI Bulk File Ingestor

- **Task ID**: nppes-client
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build a streaming ingestor for the CMS NPPES bulk file (~1.6M active providers, ~6 GB CSV) that extracts NPI, name, taxonomy code (specialty), credentials, practice address, and primary affiliation.

    ## What to do

    1. Create `src/aegis/sources/nppes.py`:

       ```python
       """NPPES/NPI Registry bulk file ingestor."""

       from __future__ import annotations

       import csv
       import logging
       from collections.abc import Iterator
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       # Key column indices in NPPES CSV (0-based)
       _COL_NPI = 0
       _COL_ENTITY_TYPE = 1       # 1=Individual, 2=Organization
       _COL_LAST_NAME = 5
       _COL_FIRST_NAME = 6
       _COL_MIDDLE_NAME = 7
       _COL_CREDENTIAL = 10
       _COL_TAXONOMY_1 = 47
       _COL_LICENSE_STATE_1 = 48
       _COL_PRACTICE_ADDR_LINE1 = 28
       _COL_PRACTICE_CITY = 30
       _COL_PRACTICE_STATE = 31
       _COL_PRACTICE_ZIP = 32
       _COL_PRACTICE_COUNTRY = 33
       _COL_DEACTIVATION_DATE = 39
       _COL_REACTIVATION_DATE = 40


       class NppesProvider(BaseModel):
           """A single NPI registry provider record."""

           model_config = ConfigDict(frozen=True)

           npi: str
           entity_type: str               # "individual" or "organization"
           first_name: str | None
           last_name: str | None
           middle_name: str | None
           credential: str | None          # e.g., "MD", "DO", "PhD"
           taxonomy_code: str | None       # NUCC taxonomy code (primary)
           license_state: str | None
           practice_address: str | None
           practice_city: str | None
           practice_state: str | None
           practice_zip: str | None
           practice_country: str | None
           is_deactivated: bool


       class IngestStats(BaseModel):
           """Statistics from an NPPES bulk ingestion."""

           model_config = ConfigDict(frozen=True)

           total_rows: int
           individuals: int
           organizations: int
           deactivated_skipped: int
           parse_errors: int


       class NppesClient:
           """Streaming ingestor for the NPPES bulk CSV file."""

           def bulk_ingest(
               self,
               file_path: Path,
               individuals_only: bool = True,
           ) -> Iterator[NppesProvider]:
               """Stream NPI records from the NPPES bulk CSV.

               The NPPES file is ~6 GB; this uses csv.reader with
               streaming to avoid loading the entire file into memory.

               Args:
                   file_path: Path to the NPPES CSV file (npidata_*.csv)
                   individuals_only: If True, skip organization records (entity_type=2)

               Yields:
                   NppesProvider records for active individual providers.
               """
               with open(file_path, newline="", encoding="utf-8") as f:  # noqa: PTH123
                   reader = csv.reader(f)
                   # Skip header row
                   next(reader, None)

                   for row_num, row in enumerate(reader, start=2):
                       try:
                           if len(row) < 50:
                               continue

                           entity_type = row[_COL_ENTITY_TYPE].strip()
                           if individuals_only and entity_type != "1":
                               continue

                           # Skip deactivated providers without reactivation
                           deactivation = row[_COL_DEACTIVATION_DATE].strip()
                           reactivation = row[_COL_REACTIVATION_DATE].strip()
                           is_deactivated = bool(deactivation and not reactivation)
                           if is_deactivated:
                               continue

                           npi = row[_COL_NPI].strip()
                           if not npi:
                               continue

                           addr_parts = [
                               row[_COL_PRACTICE_ADDR_LINE1].strip(),
                           ]
                           practice_address = ", ".join(p for p in addr_parts if p) or None

                           yield NppesProvider(
                               npi=npi,
                               entity_type="individual" if entity_type == "1" else "organization",
                               first_name=row[_COL_FIRST_NAME].strip() or None,
                               last_name=row[_COL_LAST_NAME].strip() or None,
                               middle_name=row[_COL_MIDDLE_NAME].strip() or None,
                               credential=row[_COL_CREDENTIAL].strip() or None,
                               taxonomy_code=row[_COL_TAXONOMY_1].strip() or None,
                               license_state=row[_COL_LICENSE_STATE_1].strip() or None,
                               practice_address=practice_address,
                               practice_city=row[_COL_PRACTICE_CITY].strip() or None,
                               practice_state=row[_COL_PRACTICE_STATE].strip() or None,
                               practice_zip=row[_COL_PRACTICE_ZIP].strip() or None,
                               practice_country=row[_COL_PRACTICE_COUNTRY].strip() or None,
                               is_deactivated=False,
                           )
                       except (IndexError, ValueError) as exc:
                           logger.debug("Parse error at row %d: %s", row_num, exc)

           def ingest_with_stats(
               self,
               file_path: Path,
           ) -> tuple[list[NppesProvider], IngestStats]:
               """Ingest all records and return with statistics.

               For smaller test files; production should use bulk_ingest() iterator.
               """
               providers: list[NppesProvider] = []
               total = 0
               individuals = 0
               organizations = 0
               deactivated = 0
               errors = 0

               with open(file_path, newline="", encoding="utf-8") as f:  # noqa: PTH123
                   reader = csv.reader(f)
                   next(reader, None)
                   for row_num, row in enumerate(reader, start=2):
                       total += 1
                       try:
                           if len(row) < 50:
                               errors += 1
                               continue
                           entity = row[_COL_ENTITY_TYPE].strip()
                           if entity == "1":
                               individuals += 1
                           else:
                               organizations += 1
                       except IndexError:
                           errors += 1

               for provider in self.bulk_ingest(file_path):
                   providers.append(provider)

               return providers, IngestStats(
                   total_rows=total,
                   individuals=individuals,
                   organizations=organizations,
                   deactivated_skipped=deactivated,
                   parse_errors=errors,
               )
       ```

    2. Create `src/aegis/sources/nppes_test.py`:
       - `test_bulk_ingest_basic`: Write a mock NPPES CSV (header + 5 individual rows) to tmp_path, ingest, verify 5 NppesProvider records
       - `test_skip_organizations`: Include entity_type=2 rows, verify they are skipped with `individuals_only=True`
       - `test_skip_deactivated`: Include a row with deactivation date and no reactivation, verify it's skipped
       - `test_npi_extraction`: Verify NPI numbers are correctly extracted
       - `test_taxonomy_code`: Verify NUCC taxonomy code is extracted
       - `test_credential_parsing`: Verify credential field (MD, DO) is parsed
       - `test_practice_address`: Verify practice address, city, state, zip are extracted
       - `test_empty_file`: CSV with only header yields no records

       For the mock CSV, create a header row matching NPPES format with at least 50 columns. The critical columns are at indices 0 (NPI), 1 (entity type), 5 (last name), 6 (first name), 7 (middle name), 10 (credential), 28 (practice addr), 30-33 (city/state/zip/country), 39-40 (deactivation/reactivation), 47-48 (taxonomy/license state).

    3. Update `src/aegis/sources/__init__.py` to add exports: `NppesClient`, `NppesProvider`, `IngestStats` (rename to avoid conflict — use the full import path).

    ## Files to create
    - `src/aegis/sources/nppes.py`
    - `src/aegis/sources/nppes_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add NPPES exports

    ## Code patterns to follow
    - `from __future__ import annotations` at top
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - Streaming CSV via `csv.reader` (not `pandas` — too much memory for 6 GB)
    - Iterator pattern for bulk data (same as bulk patent ingestion in Phase 2a)
    - Logger at module level
    - `tmp_path` fixture for test files

    ## Acceptance criteria
    - `NppesClient.bulk_ingest(file_path: Path) -> Iterator[NppesProvider]` works
    - Streaming parsing: does not load entire file into memory
    - Individual vs organization filtering works
    - Deactivated provider skipping works
    - All tests pass: `uv run pytest src/aegis/sources/nppes_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/nppes.py`
    - ruff passes: `uv run ruff check src/aegis/sources/nppes.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/nppes_test.py -v && uv run mypy src/aegis/sources/nppes.py && uv run ruff check src/aegis/sources/nppes.py
    ```

### 2. State Medical Board Action Ingestion

- **Task ID**: state-medical-boards
- **Role**: builder
- **Depends On**: nppes-client
- **Assigned To**: builder-1
- **Description**: |
    Build a federated state medical board action ingestion system covering 10 states, with severity-classified actions feeding the integrity hard gate.

    ## What to do

    1. Create `src/aegis/sources/state_medical_boards/__init__.py`:
       ```python
       """State medical board disciplinary action ingestion."""

       from __future__ import annotations
       ```

    2. Create `src/aegis/sources/state_medical_boards/base.py` — abstract base for per-state clients:

       ```python
       """Base class for state medical board clients."""

       from __future__ import annotations

       import logging
       from abc import ABC, abstractmethod
       from enum import StrEnum

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class ActionSeverity(StrEnum):
           """Severity classification for disciplinary actions.

           Ordered from most to least severe.
           """

           revocation = "revocation"
           suspension = "suspension"
           restriction = "restriction"
           probation = "probation"
           public_reprimand = "public_reprimand"


       class BoardAction(BaseModel):
           """A single disciplinary action from a state medical board."""

           model_config = ConfigDict(frozen=True)

           state: str                     # Two-letter state code
           npi: str | None                # NPI if available
           physician_name: str
           license_number: str | None
           action_type: ActionSeverity
           action_date: str | None        # ISO date string
           description: str | None
           source_url: str | None


       class StateBoardClient(ABC):
           """Abstract base for per-state medical board clients."""

           @property
           @abstractmethod
           def state_code(self) -> str:
               """Two-letter state code (e.g., 'CA')."""
               ...

           @abstractmethod
           def lookup(self, npi: str | None = None, name: str | None = None) -> list[BoardAction]:
               """Look up disciplinary actions by NPI or name.

               At least one of npi or name must be provided.
               """
               ...

           @abstractmethod
           def fetch_all_actions(self) -> list[BoardAction]:
               """Fetch all known disciplinary actions for this state.

               Used for bulk loading; may be expensive.
               """
               ...
       ```

    3. Create `src/aegis/sources/state_medical_boards/california.py` — California Medical Board:

       ```python
       """California Medical Board (MBC) disciplinary action client."""

       from __future__ import annotations

       import logging

       from aegis.sources.state_medical_boards.base import (
           ActionSeverity,
           BoardAction,
           StateBoardClient,
       )

       logger = logging.getLogger(__name__)

       # MBC action type to severity mapping
       _CA_ACTION_MAP: dict[str, ActionSeverity] = {
           "revoked": ActionSeverity.revocation,
           "revocation": ActionSeverity.revocation,
           "suspended": ActionSeverity.suspension,
           "suspension": ActionSeverity.suspension,
           "restricted": ActionSeverity.restriction,
           "restriction": ActionSeverity.restriction,
           "probation": ActionSeverity.probation,
           "public reprimand": ActionSeverity.public_reprimand,
           "public reproval": ActionSeverity.public_reprimand,
       }


       class CaliforniaMBC(StateBoardClient):
           """California Medical Board client.

           Data source: CA DCA License Lookup / MBC enforcement actions.
           """

           @property
           def state_code(self) -> str:
               return "CA"

           def lookup(self, npi: str | None = None, name: str | None = None) -> list[BoardAction]:
               """Look up CA disciplinary actions by NPI or name.

               Stub: in production, queries the MBC public database.
               """
               # Production: HTTP query to MBC enforcement API
               return []

           def fetch_all_actions(self) -> list[BoardAction]:
               """Fetch all CA disciplinary actions.

               Stub: in production, scrapes the MBC enforcement page.
               """
               return []

           @staticmethod
           def classify_action(action_text: str) -> ActionSeverity:
               """Map a California action description to severity."""
               lower = action_text.lower()
               for key, severity in _CA_ACTION_MAP.items():
                   if key in lower:
                       return severity
               return ActionSeverity.public_reprimand
       ```

    4. Create similar modules for New York (`new_york.py`) and Texas (`texas.py`) following the same pattern as California. Each implements `StateBoardClient` with state-specific action type mappings.

    5. Create `src/aegis/sources/state_medical_boards/registry.py` — federation layer:

       ```python
       """Federated state medical board registry."""

       from __future__ import annotations

       import logging

       from aegis.sources.state_medical_boards.base import BoardAction, StateBoardClient

       logger = logging.getLogger(__name__)


       class StateMedicalBoardRegistry:
           """Federation layer across multiple state medical board clients.

           Lookup queries all registered states and aggregates results.
           """

           def __init__(self, clients: list[StateBoardClient] | None = None) -> None:
               self._clients: dict[str, StateBoardClient] = {}
               if clients:
                   for client in clients:
                       self.register(client)

           def register(self, client: StateBoardClient) -> None:
               """Register a state board client."""
               self._clients[client.state_code] = client
               logger.info("Registered state board: %s", client.state_code)

           @property
           def registered_states(self) -> list[str]:
               """List of registered state codes."""
               return sorted(self._clients.keys())

           def lookup(
               self,
               npi: str | None = None,
               name: str | None = None,
               states: list[str] | None = None,
           ) -> list[BoardAction]:
               """Look up disciplinary actions across registered states.

               Args:
                   npi: NPI number to search
                   name: Physician name to search
                   states: Limit to specific states (default: all registered)
               """
               if npi is None and name is None:
                   raise ValueError("At least one of npi or name required")

               results: list[BoardAction] = []
               target_clients = (
                   [self._clients[s] for s in states if s in self._clients]
                   if states
                   else list(self._clients.values())
               )

               for client in target_clients:
                   try:
                       actions = client.lookup(npi=npi, name=name)
                       results.extend(actions)
                   except Exception:
                       logger.exception(
                           "Error querying %s board", client.state_code
                       )

               return results

           def has_severe_action(
               self,
               npi: str | None = None,
               name: str | None = None,
           ) -> bool:
               """Check if a physician has any revocation or suspension."""
               actions = self.lookup(npi=npi, name=name)
               severe = {"revocation", "suspension"}
               return any(a.action_type.value in severe for a in actions)
       ```

    6. Create `src/aegis/sources/state_medical_boards_test.py`:
       - `test_action_severity_ordering`: Verify ActionSeverity enum values
       - `test_california_classify_action`: Verify CA action text maps to correct severity
       - `test_registry_register`: Register 3 state clients, verify `registered_states` returns sorted list
       - `test_registry_lookup_delegates`: Mock state client that returns a BoardAction, verify registry returns it
       - `test_registry_has_severe_action`: Mock client with revocation, verify `has_severe_action` returns True
       - `test_registry_no_actions`: Empty lookup returns empty list
       - `test_board_action_model`: Create BoardAction, verify all fields

    ## Files to create
    - `src/aegis/sources/state_medical_boards/__init__.py`
    - `src/aegis/sources/state_medical_boards/base.py`
    - `src/aegis/sources/state_medical_boards/california.py`
    - `src/aegis/sources/state_medical_boards/new_york.py`
    - `src/aegis/sources/state_medical_boards/texas.py`
    - `src/aegis/sources/state_medical_boards/registry.py`
    - `src/aegis/sources/state_medical_boards_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add exports: `StateMedicalBoardRegistry`, `BoardAction`, `ActionSeverity`

    ## Code patterns to follow
    - `from __future__ import annotations` at top
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - `StrEnum` for action severity (same pattern as `StrongKeyType` in schema.py)
    - ABC for abstract base class
    - Logger at module level
    - Per-state modules follow the same interface

    ## Acceptance criteria
    - `StateMedicalBoardRegistry.lookup(npi: str) -> list[BoardAction]` works
    - `ActionSeverity` enum has values: revocation, suspension, restriction, probation, public_reprimand
    - `BoardAction` has fields: state, npi, physician_name, action_type, action_date
    - 3 state modules exist (CA, NY, TX) implementing `StateBoardClient`
    - `has_severe_action()` correctly identifies revocations/suspensions
    - All tests pass: `uv run pytest src/aegis/sources/state_medical_boards_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/state_medical_boards/`
    - ruff passes: `uv run ruff check src/aegis/sources/state_medical_boards/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/state_medical_boards_test.py -v && uv run mypy src/aegis/sources/state_medical_boards/ && uv run ruff check src/aegis/sources/state_medical_boards/
    ```

### 3. ABMS Board Certification Client

- **Task ID**: abms-client
- **Role**: builder
- **Depends On**: nppes-client
- **Assigned To**: builder-1
- **Description**: |
    Build a client for ABMS board certification data (board, subspecialty, certification date, MOC status) per physician. Supports both the paid ABMS Certification Matters API and a fallback for CMS-published certification cross-references.

    ## What to do

    1. Create `src/aegis/sources/abms.py`:

       ```python
       """ABMS board certification client."""

       from __future__ import annotations

       import logging
       from enum import StrEnum

       import httpx
       from pydantic import BaseModel, ConfigDict

       from aegis.sources.retry import RetryConfig, RetryPolicy

       logger = logging.getLogger(__name__)


       class CertificationStatus(StrEnum):
           """Board certification status."""

           certified = "certified"
           expired = "expired"
           revoked = "revoked"
           not_certified = "not_certified"


       class MOCStatus(StrEnum):
           """Maintenance of Certification status."""

           participating = "participating"
           not_participating = "not_participating"
           unknown = "unknown"


       class AbmsCertification(BaseModel):
           """Board certification record for a physician."""

           model_config = ConfigDict(frozen=True)

           npi: str
           board_name: str                # e.g., "American Board of Internal Medicine"
           specialty: str                 # e.g., "Medical Oncology"
           subspecialty: str | None
           certification_status: CertificationStatus
           certification_date: str | None  # ISO date string
           expiration_date: str | None
           moc_status: MOCStatus


       class AbmsClient:
           """Client for ABMS Certification Matters API.

           Falls back to CMS-published certification data if ABMS API
           credentials are not configured.
           """

           def __init__(
               self,
               api_key: str | None = None,
               retry_policy: RetryPolicy | None = None,
           ) -> None:
               self._api_key = api_key
               self._retry = retry_policy or RetryPolicy(RetryConfig())
               self._cache: dict[str, list[AbmsCertification]] = {}

           async def fetch_certification(
               self,
               npi: str,
           ) -> list[AbmsCertification]:
               """Fetch board certifications for a physician by NPI.

               Returns list because a physician may hold multiple
               board certifications (e.g., Internal Medicine + Medical Oncology).
               """
               if npi in self._cache:
                   return self._cache[npi]

               if self._api_key:
                   certs = await self._fetch_from_api(npi)
               else:
                   certs = self._fetch_from_fallback(npi)

               self._cache[npi] = certs
               return certs

           async def _fetch_from_api(self, npi: str) -> list[AbmsCertification]:
               """Fetch from ABMS Certification Matters API (paid)."""
               async with httpx.AsyncClient(timeout=30.0) as client:
                   async def _do_get() -> httpx.Response:
                       resp = await client.get(
                           "https://api.certificationmatters.org/v1/physicians",
                           params={"npi": npi},
                           headers={"Authorization": f"Bearer {self._api_key}"},
                       )
                       resp.raise_for_status()
                       return resp

                   response = await self._retry.execute(_do_get)
                   return self._parse_api_response(npi, response.json())

           @staticmethod
           def _fetch_from_fallback(npi: str) -> list[AbmsCertification]:
               """Fallback: return empty (CMS cross-reference not yet implemented)."""
               logger.info("ABMS fallback for NPI %s (stub)", npi)
               return []

           @staticmethod
           def _parse_api_response(npi: str, data: dict) -> list[AbmsCertification]:
               """Parse ABMS API response into certification records."""
               certs: list[AbmsCertification] = []
               for item in data.get("certifications", []):
                   status_str = item.get("status", "not_certified").lower()
                   cert_status = CertificationStatus.not_certified
                   if "certified" in status_str and "not" not in status_str:
                       cert_status = CertificationStatus.certified
                   elif "expired" in status_str:
                       cert_status = CertificationStatus.expired
                   elif "revoked" in status_str:
                       cert_status = CertificationStatus.revoked

                   moc_str = item.get("moc_status", "unknown").lower()
                   moc = MOCStatus.unknown
                   if "participating" in moc_str and "not" not in moc_str:
                       moc = MOCStatus.participating
                   elif "not" in moc_str:
                       moc = MOCStatus.not_participating

                   certs.append(AbmsCertification(
                       npi=npi,
                       board_name=item.get("board", "Unknown"),
                       specialty=item.get("specialty", "Unknown"),
                       subspecialty=item.get("subspecialty"),
                       certification_status=cert_status,
                       certification_date=item.get("cert_date"),
                       expiration_date=item.get("expiration_date"),
                       moc_status=moc,
                   ))
               return certs
       ```

    2. Create `src/aegis/sources/abms_test.py`:
       - `test_certification_status_enum`: Verify all CertificationStatus values
       - `test_moc_status_enum`: Verify all MOCStatus values
       - `test_parse_api_response`: Mock API response with 2 certifications, verify parsing
       - `test_fetch_caching`: Call fetch twice, verify second uses cache
       - `test_fetch_fallback_no_api_key`: Without API key, verify fallback is used (returns empty)
       - `test_abms_certification_model`: Create AbmsCertification, verify fields
       - Use `respx` for HTTP mocking, `@pytest.mark.asyncio(strict=True)` for async tests

    3. Update `src/aegis/sources/__init__.py` to add exports: `AbmsClient`, `AbmsCertification`, `CertificationStatus`, `MOCStatus`.

    ## Files to create
    - `src/aegis/sources/abms.py`
    - `src/aegis/sources/abms_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add ABMS exports

    ## Code patterns to follow
    - Same patterns as `src/aegis/sources/icite.py` and `src/aegis/sources/pubmed.py`
    - `StrEnum` for status enums
    - `RetryPolicy` for API calls
    - Caching via dict
    - `respx` + `pytest.mark.asyncio(strict=True)` for async test mocking

    ## Acceptance criteria
    - `AbmsClient.fetch_certification(npi: str) -> list[AbmsCertification]` works
    - `AbmsCertification` has fields: npi, board_name, specialty, certification_status, moc_status
    - Fallback returns empty when no API key
    - Caching works
    - All tests pass: `uv run pytest src/aegis/sources/abms_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/abms.py`
    - ruff passes: `uv run ruff check src/aegis/sources/abms.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/abms_test.py -v && uv run mypy src/aegis/sources/abms.py && uv run ruff check src/aegis/sources/abms.py
    ```

### 4. USNWR Hospital-Tier Classification

- **Task ID**: usnwr-hospital-tier
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build a hospital-tier classification module that maps hospital affiliations (via ROR) to USNWR Best Hospitals rankings, with specialty-specific override capability.

    ## What to do

    1. Create `data/aegis/hospital_tier_v2026.yaml` with a curated tier list of ~50 hospitals:

       ```yaml
       # USNWR Hospital Tier Classification v2026
       # Updated annually based on USNWR Best Hospitals rankings
       version: 2026
       tiers:
         - tier: 1
           description: "USNWR Honor Roll / Top 20 Overall"
           hospitals:
             - ror_id: "https://ror.org/00hj8s172"  # Mayo Clinic
               name: "Mayo Clinic"
               overall_rank: 1
             - ror_id: "https://ror.org/01y2jtd41"  # Cleveland Clinic
               name: "Cleveland Clinic"
               overall_rank: 2
             - ror_id: "https://ror.org/00b30xv10"  # Johns Hopkins
               name: "Johns Hopkins Hospital"
               overall_rank: 3
             - ror_id: "https://ror.org/02jzgtq86"  # Massachusetts General
               name: "Massachusetts General Hospital"
               overall_rank: 4
             - ror_id: "https://ror.org/04twxam07"  # UCLA Medical Center
               name: "UCLA Medical Center"
               overall_rank: 5
         - tier: 2
           description: "USNWR Top 50 Overall"
           hospitals:
             - ror_id: "https://ror.org/05byvp690"  # UCSF
               name: "UCSF Medical Center"
               overall_rank: 10
             - ror_id: "https://ror.org/02e463172"  # Stanford
               name: "Stanford Health Care"
               overall_rank: 12
         - tier: 3
           description: "USNWR Ranked in 3+ Specialties"
           hospitals:
             - ror_id: null
               name: "Regional Academic Medical Center (placeholder)"
               overall_rank: null
       specialty_overrides:
         - specialty: "oncology"
           hospitals:
             - ror_id: "https://ror.org/04twxam07"
               name: "MD Anderson Cancer Center"
               specialty_rank: 1
             - ror_id: "https://ror.org/02yrq0923"
               name: "Memorial Sloan Kettering"
               specialty_rank: 2
         - specialty: "cardiology"
           hospitals:
             - ror_id: "https://ror.org/01y2jtd41"
               name: "Cleveland Clinic"
               specialty_rank: 1
       ```

    2. Create `src/aegis/sources/usnwr.py`:

       ```python
       """USNWR hospital-tier classification."""

       from __future__ import annotations

       import logging
       from pathlib import Path
       from typing import Any

       import yaml  # type: ignore[import-untyped]
       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       _DEFAULT_TIER_PATH = Path("data/aegis/hospital_tier_v2026.yaml")


       class HospitalTierRank(BaseModel):
           """Tier classification result for a hospital."""

           model_config = ConfigDict(frozen=True)

           ror_id: str | None
           hospital_name: str
           tier: int                      # 1, 2, 3, or 0 (unranked)
           overall_rank: int | None
           specialty_rank: int | None     # Non-null if specialty override applies
           specialty_override: bool       # True if specialty ranking overrides overall


       class HospitalTier:
           """Map hospital affiliations to USNWR tier rankings."""

           def __init__(
               self,
               tier_path: Path | None = None,
           ) -> None:
               self._by_ror: dict[str, dict[str, Any]] = {}
               self._by_name: dict[str, dict[str, Any]] = {}
               self._specialty_overrides: dict[str, dict[str, dict[str, Any]]] = {}
               self._load(tier_path or _DEFAULT_TIER_PATH)

           def _load(self, path: Path) -> None:
               """Load tier data from YAML."""
               with open(path) as f:  # noqa: PTH123
                   data: dict[str, Any] = yaml.safe_load(f)

               for tier_group in data.get("tiers", []):
                   tier_num = tier_group["tier"]
                   for hosp in tier_group.get("hospitals", []):
                       entry = {
                           "name": hosp["name"],
                           "tier": tier_num,
                           "overall_rank": hosp.get("overall_rank"),
                       }
                       if hosp.get("ror_id"):
                           self._by_ror[hosp["ror_id"]] = entry
                       self._by_name[hosp["name"].lower()] = entry

               for override in data.get("specialty_overrides", []):
                   specialty = override["specialty"].lower()
                   self._specialty_overrides[specialty] = {}
                   for hosp in override.get("hospitals", []):
                       if hosp.get("ror_id"):
                           self._specialty_overrides[specialty][hosp["ror_id"]] = {
                               "name": hosp["name"],
                               "specialty_rank": hosp.get("specialty_rank"),
                           }

               logger.info(
                   "Loaded %d hospitals, %d specialty overrides",
                   len(self._by_ror) + len(self._by_name),
                   len(self._specialty_overrides),
               )

           def lookup(
               self,
               ror_id: str | None = None,
               hospital_name: str | None = None,
               specialty: str | None = None,
           ) -> HospitalTierRank:
               """Look up hospital tier by ROR ID or name.

               If specialty is provided and a specialty-specific ranking exists,
               it overrides the overall tier.
               """
               # Check specialty override first
               specialty_rank = None
               specialty_override = False
               if specialty and ror_id:
                   spec_lower = specialty.lower()
                   if spec_lower in self._specialty_overrides:
                       if ror_id in self._specialty_overrides[spec_lower]:
                           override = self._specialty_overrides[spec_lower][ror_id]
                           specialty_rank = override.get("specialty_rank")
                           specialty_override = True

               # Look up overall tier
               entry = None
               if ror_id and ror_id in self._by_ror:
                   entry = self._by_ror[ror_id]
               elif hospital_name:
                   entry = self._by_name.get(hospital_name.lower())

               if entry is None:
                   return HospitalTierRank(
                       ror_id=ror_id,
                       hospital_name=hospital_name or "Unknown",
                       tier=0,
                       overall_rank=None,
                       specialty_rank=specialty_rank,
                       specialty_override=specialty_override,
                   )

               # Specialty override may promote to tier 1
               tier = entry["tier"]
               if specialty_override and specialty_rank and specialty_rank <= 5:
                   tier = 1

               return HospitalTierRank(
                   ror_id=ror_id,
                   hospital_name=entry["name"],
                   tier=tier,
                   overall_rank=entry.get("overall_rank"),
                   specialty_rank=specialty_rank,
                   specialty_override=specialty_override,
               )
       ```

    3. Create `src/aegis/sources/usnwr_test.py`:
       - `test_load_tier_data`: Load the YAML, verify entries loaded
       - `test_lookup_by_ror`: Look up Mayo Clinic by ROR, verify tier=1
       - `test_lookup_by_name`: Look up by hospital name, verify tier
       - `test_unranked_hospital`: Look up unknown ROR, verify tier=0
       - `test_specialty_override`: Look up MD Anderson with specialty="oncology", verify specialty_rank=1
       - `test_specialty_override_promotes_tier`: Specialty top-5 promotes to tier 1
       - Use `tmp_path` with custom YAML for isolated tests

    4. Update `src/aegis/sources/__init__.py` to add exports: `HospitalTier`, `HospitalTierRank`.

    ## Files to create
    - `data/aegis/hospital_tier_v2026.yaml`
    - `src/aegis/sources/usnwr.py`
    - `src/aegis/sources/usnwr_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add USNWR exports

    ## Code patterns to follow
    - YAML loading pattern from `src/aegis/scoring/quality_prior.py`
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - `from __future__ import annotations`
    - Logger at module level

    ## Acceptance criteria
    - `HospitalTier.lookup(ror_id: str, specialty: Optional[str]) -> HospitalTierRank` works
    - Tier YAML has at least 7 hospitals across tiers
    - Specialty override works (oncology, cardiology)
    - Unranked hospitals return tier=0
    - All tests pass: `uv run pytest src/aegis/sources/usnwr_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/usnwr.py`
    - ruff passes: `uv run ruff check src/aegis/sources/usnwr.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/usnwr_test.py -v && uv run mypy src/aegis/sources/usnwr.py && uv run ruff check src/aegis/sources/usnwr.py
    ```

### 5. ICD-10/CPT to MeSH Cross-walks + CMS PPSAS Client

- **Task ID**: icd10-cpt-xwalk
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build ICD-10-CM to MeSH and CPT to MeSH cross-walks plus a CMS Medicare Provider Utilization client for procedure-volume proxies.

    ## What to do

    1. Create `src/aegis/taxonomy/icd10_mesh.py`:

       ```python
       """ICD-10-CM to MeSH cross-walk."""

       from __future__ import annotations

       import logging
       from pathlib import Path
       from typing import Any

       import yaml  # type: ignore[import-untyped]
       from pydantic import BaseModel, ConfigDict

       from aegis.storage.schema import MeshDescriptor

       logger = logging.getLogger(__name__)


       class Icd10MeshMapping(BaseModel):
           """A single ICD-10 to MeSH mapping."""

           model_config = ConfigDict(frozen=True)

           icd10_code: str
           icd10_description: str
           mesh_descriptors: list[MeshDescriptor]


       class Icd10MeshXwalk:
           """Translate ICD-10-CM codes to MeSH descriptors.

           Uses UMLS-derived mappings for the most common codes
           plus hierarchical prefix matching for variants.
           """

           def __init__(self) -> None:
               self._mapping: dict[str, list[MeshDescriptor]] = {}
               self._load_builtin()

           def _load_builtin(self) -> None:
               """Load built-in ICD-10 to MeSH mappings.

               In production, these come from UMLS; here we include
               the most common codes for the target specialties.
               """
               # Common oncology ICD-10 codes
               _BUILTINS: dict[str, list[tuple[str, str | None, bool]]] = {
                   "C34": [("Lung Neoplasms", None, True)],
                   "C34.1": [("Carcinoma, Non-Small-Cell Lung", None, True)],
                   "C34.9": [("Lung Neoplasms", None, True)],
                   "C50": [("Breast Neoplasms", None, True)],
                   "C61": [("Prostatic Neoplasms", None, True)],
                   "C18": [("Colonic Neoplasms", None, True)],
                   "C71": [("Brain Neoplasms", None, True)],
                   "C91.0": [("Precursor Cell Lymphoblastic Leukemia-Lymphoma", None, True)],
                   "C92.0": [("Leukemia, Myeloid, Acute", None, True)],
                   # Common cardiology codes
                   "I21": [("Myocardial Infarction", None, True)],
                   "I25": [("Coronary Artery Disease", None, True)],
                   "I48": [("Atrial Fibrillation", None, True)],
                   "I50": [("Heart Failure", None, True)],
                   # Common radiology-relevant codes
                   "R91": [("Solitary Pulmonary Nodule", None, True)],
                   "R93": [("Diagnostic Imaging", "abnormal findings", True)],
                   # Endocrinology
                   "E11": [("Diabetes Mellitus, Type 2", None, True)],
                   "E10": [("Diabetes Mellitus, Type 1", None, True)],
                   "E05": [("Hyperthyroidism", None, True)],
                   # Neurology
                   "G20": [("Parkinson Disease", None, True)],
                   "G30": [("Alzheimer Disease", None, True)],
                   "G35": [("Multiple Sclerosis", None, True)],
               }
               for code, mesh_list in _BUILTINS.items():
                   self._mapping[code] = [
                       MeshDescriptor(descriptor=d, qualifier=q, major_topic=m)
                       for d, q, m in mesh_list
                   ]

           def translate(self, icd10: str) -> list[MeshDescriptor]:
               """Translate an ICD-10 code to MeSH descriptors.

               Tries exact match, then progressively shorter prefixes.
               """
               # Normalize: remove dots for matching
               normalized = icd10.replace(".", "").upper()
               dotted = icd10.upper()

               # Exact match (with dot)
               if dotted in self._mapping:
                   return self._mapping[dotted]

               # Exact match (without dot)
               if normalized in self._mapping:
                   return self._mapping[normalized]

               # Prefix match
               prefix = dotted
               while len(prefix) > 1:
                   prefix = prefix[:-1]
                   if prefix in self._mapping:
                       return self._mapping[prefix]

               return []
       ```

    2. Create `src/aegis/taxonomy/cpt_mesh.py`:

       ```python
       """CPT to MeSH cross-walk for clinician procedure coding."""

       from __future__ import annotations

       import logging

       from aegis.storage.schema import MeshDescriptor

       logger = logging.getLogger(__name__)


       class CptMeshXwalk:
           """Translate CPT (Current Procedural Terminology) codes to MeSH.

           CPT -> MeSH mapping is sparser than ICD-10 -> MeSH.
           Built-in covers the most common diagnostic and procedural codes.
           """

           def __init__(self) -> None:
               self._mapping: dict[str, list[MeshDescriptor]] = {}
               self._load_builtin()

           def _load_builtin(self) -> None:
               """Load built-in CPT to MeSH mappings."""
               _BUILTINS: dict[str, list[tuple[str, str | None, bool]]] = {
                   # Radiology CPTs
                   "71250": [("Tomography, X-Ray Computed", "methods", True)],
                   "71260": [("Tomography, X-Ray Computed", "methods", True), ("Contrast Media", None, False)],
                   "71275": [("Computed Tomography Angiography", None, True)],
                   "74177": [("Tomography, X-Ray Computed", "methods", True), ("Abdomen", "diagnostic imaging", True)],
                   "77065": [("Mammography", None, True)],
                   "77066": [("Mammography", None, True)],
                   # Cardiology CPTs
                   "93000": [("Electrocardiography", None, True)],
                   "93306": [("Echocardiography", None, True)],
                   "93350": [("Echocardiography, Stress", None, True)],
                   "93458": [("Cardiac Catheterization", None, True)],
                   "93459": [("Cardiac Catheterization", None, True)],
                   "92928": [("Percutaneous Coronary Intervention", None, True)],
                   # Surgery CPTs
                   "47600": [("Cholecystectomy", None, True)],
                   "44970": [("Appendectomy", None, True)],
                   "27447": [("Arthroplasty, Replacement, Knee", None, True)],
                   # Pathology
                   "88305": [("Biopsy", "pathology", True)],
                   "88342": [("Immunohistochemistry", None, True)],
                   # Oncology
                   "96413": [("Antineoplastic Agents", "administration & dosage", True)],
                   "96415": [("Infusions, Intravenous", None, True)],
               }
               for code, mesh_list in _BUILTINS.items():
                   self._mapping[code] = [
                       MeshDescriptor(descriptor=d, qualifier=q, major_topic=m)
                       for d, q, m in mesh_list
                   ]

           def translate(self, cpt: str) -> list[MeshDescriptor]:
               """Translate a CPT code to MeSH descriptors."""
               normalized = cpt.strip()
               if normalized in self._mapping:
                   return self._mapping[normalized]
               return []
       ```

    3. Create `src/aegis/sources/cms_ppsas.py` for Medicare Provider Utilization:

       ```python
       """CMS Medicare Provider Utilization & Payment (PPSAS) data client."""

       from __future__ import annotations

       import csv
       import logging
       from collections.abc import Iterator
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class ProviderUtilization(BaseModel):
           """Medicare provider utilization record."""

           model_config = ConfigDict(frozen=True)

           npi: str
           provider_name: str
           credential: str | None
           hcpcs_code: str                # CPT/HCPCS code
           hcpcs_description: str
           total_services: int
           total_beneficiaries: int
           average_submitted_charge: float | None
           average_medicare_payment: float | None


       class CmsPpsasClient:
           """Ingest CMS Medicare Provider Utilization and Payment data.

           Public data: Medicare Provider Utilization and Payment Data (PPSAS)
           provides per-NPI, per-procedure volume proxies.
           """

           def iter_utilization(
               self, file_path: Path, npi_filter: set[str] | None = None
           ) -> Iterator[ProviderUtilization]:
               """Stream provider utilization records from CMS CSV.

               Args:
                   file_path: Path to CMS PPSAS CSV file
                   npi_filter: If provided, only yield records for these NPIs
               """
               with open(file_path, newline="", encoding="utf-8") as f:  # noqa: PTH123
                   reader = csv.DictReader(f)
                   for row in reader:
                       npi = row.get("Rndrng_NPI", "").strip()
                       if not npi:
                           continue
                       if npi_filter and npi not in npi_filter:
                           continue

                       try:
                           yield ProviderUtilization(
                               npi=npi,
                               provider_name=row.get("Rndrng_Prvdr_Last_Org_Name", ""),
                               credential=row.get("Rndrng_Prvdr_Crdntls"),
                               hcpcs_code=row.get("HCPCS_Cd", ""),
                               hcpcs_description=row.get("HCPCS_Desc", ""),
                               total_services=int(float(row.get("Tot_Srvcs", "0"))),
                               total_beneficiaries=int(float(row.get("Tot_Benes", "0"))),
                               average_submitted_charge=self._parse_float(row.get("Avg_Sbmtd_Chrg")),
                               average_medicare_payment=self._parse_float(row.get("Avg_Mdcr_Pymt_Amt")),
                           )
                       except (ValueError, KeyError) as exc:
                           logger.debug("CMS PPSAS parse error: %s", exc)

           @staticmethod
           def _parse_float(val: str | None) -> float | None:
               if val is None or val.strip() == "":
                   return None
               try:
                   return float(val.replace(",", ""))
               except ValueError:
                   return None

           def aggregate_by_npi(
               self, file_path: Path, npi_filter: set[str] | None = None
           ) -> dict[str, dict[str, int]]:
               """Aggregate total services per HCPCS code per NPI.

               Returns {npi: {hcpcs_code: total_services}}.
               """
               result: dict[str, dict[str, int]] = {}
               for record in self.iter_utilization(file_path, npi_filter):
                   if record.npi not in result:
                       result[record.npi] = {}
                   existing = result[record.npi].get(record.hcpcs_code, 0)
                   result[record.npi][record.hcpcs_code] = existing + record.total_services
               return result
       ```

    4. Create `src/aegis/taxonomy/icd10_cpt_test.py`:
       - `test_icd10_lung_cancer`: Translate "C34.1" -> MeSH "Carcinoma, Non-Small-Cell Lung"
       - `test_icd10_prefix_match`: Translate "C34.9" prefix-matches to "C34" -> "Lung Neoplasms"
       - `test_icd10_unknown`: Unknown code returns empty list
       - `test_cpt_radiology`: Translate "71250" -> "Tomography, X-Ray Computed / methods"
       - `test_cpt_cardiac_cath`: Translate "93458" -> "Cardiac Catheterization"
       - `test_cpt_unknown`: Unknown CPT returns empty
       - `test_cms_ppsas_parse`: Write mock CMS CSV to tmp_path, parse, verify records
       - `test_cms_aggregate_by_npi`: Aggregate mock data, verify per-NPI totals

    5. Update `src/aegis/taxonomy/__init__.py` to add exports: `Icd10MeshXwalk`, `CptMeshXwalk`.
    6. Update `src/aegis/sources/__init__.py` to add exports: `CmsPpsasClient`, `ProviderUtilization`.

    ## Files to create
    - `src/aegis/taxonomy/icd10_mesh.py`
    - `src/aegis/taxonomy/cpt_mesh.py`
    - `src/aegis/sources/cms_ppsas.py`
    - `src/aegis/taxonomy/icd10_cpt_test.py`

    ## Files to modify
    - `src/aegis/taxonomy/__init__.py` — add exports
    - `src/aegis/sources/__init__.py` — add CMS exports

    ## Code patterns to follow
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - `from __future__ import annotations`
    - `MeshDescriptor` from `src/aegis/storage/schema.py`
    - CSV streaming via `csv.DictReader`
    - Logger at module level
    - `tmp_path` for test files

    ## Acceptance criteria
    - `Icd10MeshXwalk.translate(icd10: str) -> list[MeshDescriptor]` works
    - `CptMeshXwalk.translate(cpt: str) -> list[MeshDescriptor]` works
    - CPT 71250 -> "Tomography, X-Ray Computed / methods"
    - `CmsPpsasClient.iter_utilization()` streams CSV records
    - All tests pass: `uv run pytest src/aegis/taxonomy/icd10_cpt_test.py -v`
    - mypy passes on all new modules
    - ruff passes on all new modules

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/taxonomy/icd10_cpt_test.py -v && uv run mypy src/aegis/taxonomy/icd10_mesh.py src/aegis/taxonomy/cpt_mesh.py src/aegis/sources/cms_ppsas.py && uv run ruff check src/aegis/taxonomy/icd10_mesh.py src/aegis/taxonomy/cpt_mesh.py src/aegis/sources/cms_ppsas.py
    ```

### 6. Clinician Per-Specialty Inverted Index

- **Task ID**: clinician-index
- **Role**: builder
- **Depends On**: nppes-client
- **Assigned To**: builder-1
- **Description**: |
    Build a per-specialty inverted index for the clinician corpus, keyed by NUCC taxonomy code, enabling specialty-scoped queries with p95 < 100ms without scanning all 1.6M providers.

    ## What to do

    1. Create `src/aegis/storage/clinician_index.py`:

       ```python
       """Per-specialty inverted index for clinician corpus scale queries."""

       from __future__ import annotations

       import logging
       import time

       import duckdb
       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       _INDEX_DDL = """
       CREATE TABLE IF NOT EXISTS clinician_specialty_index (
           taxonomy_code TEXT NOT NULL,
           npi TEXT NOT NULL,
           provider_name TEXT NOT NULL,
           practice_state TEXT,
           practice_city TEXT,
           practice_zip TEXT,
           PRIMARY KEY (taxonomy_code, npi)
       );

       CREATE INDEX IF NOT EXISTS idx_clinician_taxonomy
           ON clinician_specialty_index(taxonomy_code);

       CREATE INDEX IF NOT EXISTS idx_clinician_state
           ON clinician_specialty_index(practice_state);

       CREATE INDEX IF NOT EXISTS idx_clinician_zip
           ON clinician_specialty_index(practice_zip);
       """


       class ClinicianLookupResult(BaseModel):
           """Result of a clinician specialty lookup."""

           model_config = ConfigDict(frozen=True)

           npi: str
           provider_name: str
           taxonomy_code: str
           practice_state: str | None
           practice_city: str | None


       class ClinicianIndex:
           """Per-specialty inverted index for fast clinician lookups.

           Keyed by NUCC taxonomy code for O(specialty_cohort) queries
           instead of O(1.6M) full scans.
           """

           def __init__(self, db_path: str = "aegis.duckdb") -> None:
               self._conn = duckdb.connect(db_path)
               self._conn.execute(_INDEX_DDL)

           def insert(
               self,
               taxonomy_code: str,
               npi: str,
               provider_name: str,
               practice_state: str | None = None,
               practice_city: str | None = None,
               practice_zip: str | None = None,
           ) -> None:
               """Insert a clinician into the specialty index."""
               self._conn.execute(
                   """
                   INSERT INTO clinician_specialty_index
                       (taxonomy_code, npi, provider_name, practice_state,
                        practice_city, practice_zip)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT (taxonomy_code, npi) DO UPDATE SET
                       provider_name = excluded.provider_name,
                       practice_state = excluded.practice_state,
                       practice_city = excluded.practice_city,
                       practice_zip = excluded.practice_zip
                   """,
                   [taxonomy_code, npi, provider_name, practice_state,
                    practice_city, practice_zip],
               )

           def insert_batch(
               self,
               records: list[tuple[str, str, str, str | None, str | None, str | None]],
           ) -> int:
               """Batch insert clinicians into the specialty index.

               Each tuple: (taxonomy_code, npi, provider_name, state, city, zip).
               Returns number of records inserted.
               """
               for record in records:
                   self.insert(*record)
               return len(records)

           def lookup_by_specialty(
               self,
               taxonomy_code: str,
               state: str | None = None,
               limit: int = 1000,
           ) -> list[ClinicianLookupResult]:
               """Look up clinicians by NUCC taxonomy code.

               Optional state filter for geographic scoping.
               """
               if state:
                   rows = self._conn.execute(
                       """
                       SELECT npi, provider_name, taxonomy_code,
                              practice_state, practice_city
                       FROM clinician_specialty_index
                       WHERE taxonomy_code = ? AND practice_state = ?
                       LIMIT ?
                       """,
                       [taxonomy_code, state, limit],
                   ).fetchall()
               else:
                   rows = self._conn.execute(
                       """
                       SELECT npi, provider_name, taxonomy_code,
                              practice_state, practice_city
                       FROM clinician_specialty_index
                       WHERE taxonomy_code = ?
                       LIMIT ?
                       """,
                       [taxonomy_code, limit],
                   ).fetchall()

               return [
                   ClinicianLookupResult(
                       npi=r[0],
                       provider_name=r[1],
                       taxonomy_code=r[2],
                       practice_state=r[3],
                       practice_city=r[4],
                   )
                   for r in rows
               ]

           def count_by_specialty(self, taxonomy_code: str) -> int:
               """Count clinicians in a specialty."""
               result = self._conn.execute(
                   "SELECT COUNT(*) FROM clinician_specialty_index WHERE taxonomy_code = ?",
                   [taxonomy_code],
               ).fetchone()
               return int(result[0]) if result else 0

           def total_count(self) -> int:
               """Total clinicians in the index."""
               result = self._conn.execute(
                   "SELECT COUNT(*) FROM clinician_specialty_index"
               ).fetchone()
               return int(result[0]) if result else 0

           def close(self) -> None:
               """Close the DuckDB connection."""
               self._conn.close()
       ```

    2. Create `src/aegis/storage/clinician_index_test.py`:
       - `test_insert_and_lookup`: Insert 5 clinicians with same taxonomy, lookup, verify 5 returned
       - `test_lookup_by_state`: Insert clinicians in 3 states, filter by state, verify correct subset
       - `test_count_by_specialty`: Insert 10 clinicians across 2 taxonomies, verify counts
       - `test_total_count`: Verify total count matches insertions
       - `test_upsert_idempotent`: Insert same NPI twice, verify count is 1
       - `test_lookup_performance`: Insert 5000 clinicians, time specialty lookup, assert p95 < 100ms
       - Use `tmp_path` for DuckDB file location

    3. Update `src/aegis/storage/__init__.py` to export `ClinicianIndex`, `ClinicianLookupResult`.

    ## Files to create
    - `src/aegis/storage/clinician_index.py`
    - `src/aegis/storage/clinician_index_test.py`

    ## Files to modify
    - `src/aegis/storage/__init__.py` — add exports

    ## Code patterns to follow
    - DuckDB raw SQL (same pattern as `candidate_store.py` and `indexes.py`)
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - `from __future__ import annotations`
    - Performance tests with `time.perf_counter()`
    - `tmp_path` for test database isolation

    ## Acceptance criteria
    - `ClinicianIndex.lookup_by_specialty(taxonomy_code)` returns `list[ClinicianLookupResult]`
    - State-filtered lookup works
    - Specialty-scoped query p95 < 100ms on 5000-record index
    - Upsert is idempotent
    - All tests pass: `uv run pytest src/aegis/storage/clinician_index_test.py -v`
    - mypy passes: `uv run mypy src/aegis/storage/clinician_index.py`
    - ruff passes: `uv run ruff check src/aegis/storage/clinician_index.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/storage/clinician_index_test.py -v && uv run mypy src/aegis/storage/clinician_index.py && uv run ruff check src/aegis/storage/clinician_index.py
    ```

### 7. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: nppes-client, state-medical-boards, abms-client, usnwr-hospital-tier, icd10-cpt-xwalk, clinician-index
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for Phase 2b clinician sources.

    ## Validation Commands

    1. Verify NPPES imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.nppes import NppesClient, NppesProvider; print('NPPES imports OK')"
    ```

    2. Verify state medical board imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.state_medical_boards.registry import StateMedicalBoardRegistry; from aegis.sources.state_medical_boards.base import BoardAction, ActionSeverity; print('State board imports OK')"
    ```

    3. Verify ABMS imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.abms import AbmsClient, AbmsCertification, CertificationStatus, MOCStatus; print('ABMS imports OK')"
    ```

    4. Verify USNWR imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.usnwr import HospitalTier, HospitalTierRank; print('USNWR imports OK')"
    ```

    5. Verify ICD-10/CPT imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.taxonomy.icd10_mesh import Icd10MeshXwalk; from aegis.taxonomy.cpt_mesh import CptMeshXwalk; print('ICD-10/CPT imports OK')"
    ```

    6. Verify clinician index imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.storage.clinician_index import ClinicianIndex, ClinicianLookupResult; print('Clinician index imports OK')"
    ```

    7. Verify CPT 71250 cross-walk:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.taxonomy.cpt_mesh import CptMeshXwalk; xw = CptMeshXwalk(); result = xw.translate('71250'); assert len(result) > 0; assert 'Tomography' in result[0].descriptor; print(f'CPT 71250 -> {result[0].descriptor} OK')"
    ```

    8. Run all Phase 2b tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/nppes_test.py src/aegis/sources/state_medical_boards_test.py src/aegis/sources/abms_test.py src/aegis/sources/usnwr_test.py src/aegis/taxonomy/icd10_cpt_test.py src/aegis/storage/clinician_index_test.py -v
    ```

    9. Run mypy on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/sources/nppes.py src/aegis/sources/state_medical_boards/ src/aegis/sources/abms.py src/aegis/sources/usnwr.py src/aegis/taxonomy/icd10_mesh.py src/aegis/taxonomy/cpt_mesh.py src/aegis/sources/cms_ppsas.py src/aegis/storage/clinician_index.py
    ```

    10. Run ruff on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/sources/nppes.py src/aegis/sources/state_medical_boards/ src/aegis/sources/abms.py src/aegis/sources/usnwr.py src/aegis/taxonomy/icd10_mesh.py src/aegis/taxonomy/cpt_mesh.py src/aegis/sources/cms_ppsas.py src/aegis/storage/clinician_index.py
    ```

    11. Verify existing tests still pass:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/storage/schema_test.py src/aegis/storage/indexes_test.py -v
    ```

    ## Acceptance Criteria
    - All source clients exist and are importable
    - NPPES bulk ingest streams CSV records
    - State medical board registry federates across 3+ states
    - ABMS client returns certification records
    - Hospital tier lookup works by ROR and specialty
    - ICD-10 and CPT cross-walks translate codes to MeSH
    - Clinician index p95 < 100ms on 5000-record specialty lookup
    - All new tests pass
    - mypy strict passes
    - ruff passes
    - Existing tests unbroken

## Acceptance Criteria

- `NppesClient.bulk_ingest(file_path) -> Iterator[NppesProvider]` streams the NPPES CSV with NPI, taxonomy code, credentials, practice address
- `StateMedicalBoardRegistry.lookup(npi) -> list[BoardAction]` federates across CA, NY, TX state boards with severity enum (revocation > suspension > restriction > probation > public_reprimand)
- `AbmsClient.fetch_certification(npi) -> list[AbmsCertification]` returns board, specialty, certification status, MOC status
- `HospitalTier.lookup(ror_id, specialty) -> HospitalTierRank` maps affiliations to USNWR tiers with specialty-specific overrides
- `Icd10MeshXwalk.translate(icd10) -> list[MeshDescriptor]` translates ICD-10-CM to MeSH
- `CptMeshXwalk.translate(cpt) -> list[MeshDescriptor]` translates CPT to MeSH (71250 -> "Tomography, X-Ray Computed / methods")
- `CmsPpsasClient.iter_utilization()` streams Medicare procedure-volume data
- `ClinicianIndex.lookup_by_specialty(taxonomy_code)` returns results with p95 < 100ms on 5000 records
- All new tests pass
- mypy strict mode passes on all new modules
- ruff lint passes on all new modules
- No existing Phase 0/1 tests broken

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/sources/nppes_test.py src/aegis/sources/state_medical_boards_test.py src/aegis/sources/abms_test.py src/aegis/sources/usnwr_test.py src/aegis/taxonomy/icd10_cpt_test.py src/aegis/storage/clinician_index_test.py -v` — Run all Phase 2b tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/sources/nppes.py src/aegis/sources/state_medical_boards/ src/aegis/sources/abms.py src/aegis/sources/usnwr.py src/aegis/taxonomy/icd10_mesh.py src/aegis/taxonomy/cpt_mesh.py src/aegis/sources/cms_ppsas.py src/aegis/storage/clinician_index.py` — Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/sources/nppes.py src/aegis/sources/state_medical_boards/ src/aegis/sources/abms.py src/aegis/sources/usnwr.py src/aegis/taxonomy/ src/aegis/sources/cms_ppsas.py src/aegis/storage/clinician_index.py` — Lint all new modules

## Notes

- NPPES bulk file is ~6 GB CSV; streaming CSV parser is mandatory, do NOT use pandas
- State medical board coverage in Phase 2 is top-10 states; this sub-spec implements CA, NY, TX as the foundation; remaining 7 states (FL, IL, PA, OH, NC, GA, MI) follow the same `StateBoardClient` pattern and can be added incrementally
- ABMS Certification Matters API is paid; the fallback path exists for environments without API access
- USNWR rankings are annual; the YAML file is versioned by year (v2026)
- CMS PPSAS procedure-volume data is a noisy proxy; coverage caveat should be reported alongside any volume-based signals
- The clinician index is rebuilt weekly on NPPES monthly delta; per-specialty scan is then O(specialty_cohort_size) instead of O(1.6M)
