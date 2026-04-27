# Plan: Phase 1b — Integrity Gate, Topical Fit, Recency, and End-to-End Ranking

> **Status:** COMPLETE (2026-04-26)
> All 10 tasks completed. 319/320 tests passing (1 pre-existing failure in cohort/audit_test.py outside Phase 1b scope). Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-26
> **Team:** phase1b-integrity-ranking-20260426-1200

### Test Results
- `src/aegis/integrity/` (hard_gate_test, llm_triage_test, papermill_test, predatory_test, soft_discounts_test) — 53/53 PASSED
- `src/aegis/scoring/topical_fit_test.py` — 14/14 PASSED
- `src/aegis/scoring/recency_test.py` — 10/10 PASSED
- `src/aegis/scoring/rank_test.py` — 12/12 PASSED
- `src/aegis/sources/leie_test.py` — 6/6 PASSED
- `src/aegis/sources/ofac_sam_test.py` — 5/5 PASSED
- `src/aegis/sources/ori_test.py` — 6/6 PASSED
- `src/aegis/sources/retraction_watch_test.py` — 7/7 PASSED
- Full test suite (`src/` + `tests/`) — 319/320 PASSED (1 pre-existing failure in `cohort/audit_test.py::test_daily_summary`, not in Phase 1b scope)
- mypy strict — 20 source files, 0 issues
- ruff check — All checks passed
- Key imports — `HardGate`, `SoftDiscounts`, `Ranker`, `TopicalFit`, `Recency` all import successfully

### Acceptance Criteria Verification
- [x] 4 integrity source clients exist — VERIFIED (leie.py, ofac_sam.py, ori.py, retraction_watch.py all present with LEIEStore, OFACSAMStore, ORIStore, RetractionWatchStore classes)
- [x] HardGate evaluates 5 rules with short-circuit and audit trails — VERIFIED (Rule 1: LEIE, Rule 2: OFAC/SAM, Rule 3: ORI, Rule 4: Retraction fabrication/falsification, Rule 5: Medical board stub; short-circuit on first match; HardGateResult includes rules_evaluated count and trigger_rule)
- [x] SoftDiscounts evaluates 4 discount types with floors — VERIFIED (predatory_load, out_of_subdomain_retraction, authorship_inconsistency, papermill_pending; floor constants enforced per discount)
- [x] TopicalFit computes cosine similarity in [0, 1] — VERIFIED (cosine similarity via dot product of L2-normalized vectors, clamped to [0, 1])
- [x] Recency computes time-decayed score in [0, 1] — VERIFIED (10/10 tests pass, exponential decay with squash function)
- [x] Ranker wires Rank(c,q) = I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma — VERIFIED (rank.py line 1 documents formula; exponents alpha/beta/gamma loaded with defaults; 12/12 tests pass)
- [x] All tests pass, mypy strict passes, ruff passes — VERIFIED (113/113 Phase 1b tests pass; mypy 0 issues in 20 files; ruff all checks passed)
- [x] No existing tests broken — VERIFIED (319/320 full suite pass; 1 failure is pre-existing in cohort/audit_test.py::test_daily_summary, not in Phase 1b scope)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `src/aegis/sources/leie.py` | Created | Yes |
| `src/aegis/sources/leie_test.py` | Created | Yes |
| `src/aegis/sources/ofac_sam.py` | Created | Yes |
| `src/aegis/sources/ofac_sam_test.py` | Created | Yes |
| `src/aegis/sources/ori.py` | Created | Yes |
| `src/aegis/sources/ori_test.py` | Created | Yes |
| `src/aegis/sources/retraction_watch.py` | Created | Yes |
| `src/aegis/sources/retraction_watch_test.py` | Created | Yes |
| `src/aegis/integrity/__init__.py` | Created | Yes |
| `src/aegis/integrity/hard_gate.py` | Created | Yes |
| `src/aegis/integrity/hard_gate_test.py` | Created | Yes |
| `src/aegis/integrity/soft_discounts.py` | Created | Yes |
| `src/aegis/integrity/soft_discounts_test.py` | Created | Yes |
| `src/aegis/integrity/predatory.py` | Created | Yes |
| `src/aegis/integrity/predatory_test.py` | Created | Yes |
| `src/aegis/integrity/papermill.py` | Created | Yes |
| `src/aegis/integrity/papermill_test.py` | Created | Yes |
| `src/aegis/integrity/llm_triage.py` | Created | Yes |
| `src/aegis/integrity/llm_triage_test.py` | Created | Yes |
| `src/aegis/scoring/topical_fit.py` | Created | Yes |
| `src/aegis/scoring/topical_fit_test.py` | Created | Yes |
| `src/aegis/scoring/candidate_vector.py` | Created | Yes |
| `src/aegis/scoring/recency.py` | Created | Yes |
| `src/aegis/scoring/recency_test.py` | Created | Yes |
| `src/aegis/scoring/rank.py` | Created | Yes |
| `src/aegis/scoring/rank_test.py` | Created | Yes |
| `src/aegis/scoring/result_format.py` | Created | Yes |
| `src/aegis/scoring/__init__.py` | Modified | Yes |
| `src/aegis/sources/__init__.py` | Modified | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase1b-integrity-ranking.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build the integrity gate, topical-fit scoring, recency scoring, and end-to-end ranking pipeline for Aegis Phase 1. This covers Tasks 1.8-1.12 from the Phase 1 scoring plan (`docs/plans/aegis/phase-1-scoring.md`):

- **Task 1.8**: Integrity gate hard rules -- hard-zero exclusion via LEIE, OFAC/SAM, ORI, Retraction Watch, and state medical board actions
- **Task 1.9**: Integrity gate soft discounts -- predatory-journal load, out-of-subdomain retractions, paper-mill signals, LLM retraction-notice triage
- **Task 1.10**: T(c,q) topical fit -- candidate topic vector construction, query MeSH vector, cosine similarity
- **Task 1.11**: R(c,q) recency -- time-decay scoring over query-relevant artifacts
- **Task 1.12**: End-to-end Rank(c,q) wiring -- `Rank(c,q) = I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma`

This is Phase 1b of three Phase 1 sub-specs. It depends on Phase 1a (`specs/aegis-phase1a-scoring-foundation.md`) being complete, which provides:
- `QualityPrior` at `src/aegis/scoring/quality_prior.py` (computes Q(c) with `WeightVector` from YAML)
- `WeightVector` and `load_weight_vector` (loads exponents alpha, beta, gamma from `config/aegis/weights/translational_v1.yaml`)
- All F1-F6 scoring modules at `src/aegis/scoring/f{1-6}_*.py`
- `src/aegis/scoring/__init__.py` with exports for all scoring classes

Phase 0 codebase provides:
- `Candidate` schema at `src/aegis/storage/schema.py` (uuid, strong_keys, name_variants, affiliations, artifact_refs, mesh_descriptors, linkage_confidence)
- `MeshDescriptor` at `src/aegis/storage/schema.py` (descriptor, qualifier, major_topic)
- `CandidateStore` at `src/aegis/storage/candidate_store.py` (DuckDB-backed CRUD)
- `PubMedClient` at `src/aegis/sources/pubmed.py` (returns `PubMedRecord` with authors, mesh_descriptors, article_type, publication_date, journal_nlm_id, medline_indexed)
- `CtgovClient` at `src/aegis/sources/ctgov.py` (returns `StudyRecord` with investigators, phase, sponsor)
- `IndexManager` at `src/aegis/storage/indexes.py` (MeSH inverted index, yearly counts)
- `Cohort` at `src/aegis/cohort/nsclc_translational.py` (cohort builder with candidate UUIDs)
- `ArchetypeFixture` at `src/aegis/validation/archetypes.py` (Dr. A, Dr. B, Dr. C, Dr. D)
- `RetryPolicy` / `RetryConfig` at `src/aegis/sources/retry.py`
- All Pydantic models use `ConfigDict(frozen=True)`, `from __future__ import annotations`, mypy strict mode

## Objective

When this plan is complete:
1. An integrity gate evaluates each candidate via hard-zero rules (LEIE, OFAC/SAM, ORI, Retraction Watch, medical board) and soft discounts (predatory load, paper-mill signals, out-of-subdomain retractions, LLM triage).
2. A topical-fit module computes `T(c,q)` as cosine similarity between sparse MeSH-weighted candidate and query vectors.
3. A recency module computes `R(c,q)` as time-decayed activity over query-relevant artifacts.
4. An end-to-end ranker wires `Rank(c,q) = I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma` with per-component breakdowns and evidence trails.
5. Hard-zero candidates are excluded from output but retained in audit logs.
6. All modules pass mypy strict, ruff lint, and have unit tests with >=90% coverage.

## Problem Statement

Phase 1a produced the quality prior Q(c) scoring foundation. To produce a complete ranking, Aegis needs: (a) an integrity gate that zeros or discounts candidates with serious integrity issues, (b) query-dependent topical-fit and recency scores, and (c) a composition layer that multiplies these components with configurable exponents to produce the final ranked list. The integrity gate must be auditable (every decision logged with source artifact IDs) and the ranking must include per-component breakdowns for transparency.

## Solution Approach

1. **Integrity source clients first**: Create source clients for LEIE, OFAC/SAM, ORI, and Retraction Watch data. These are in-memory stores for Phase 1 (same pattern as Phase 0/1a source clients).
2. **Hard gate then soft discounts**: Hard gate evaluates binary exclusion rules. Soft discounts compute multiplicative discount factors. Both are independent of query context.
3. **Topical fit and recency in parallel**: T(c,q) and R(c,q) are query-dependent but independent of each other. They can be built in parallel.
4. **End-to-end ranking last**: Once all components exist, wire the Rank formula with result formatting and evidence trails.
5. **Testing**: Each module gets synthetic-data unit tests. The ranking module gets archetype regression tests (Dr. A top 5%, Dr. D excluded).

## Relevant Files

### Existing Files (from Phase 0, read-only)
- `src/aegis/storage/schema.py` -- `Candidate`, `MeshDescriptor`, `ArtifactRefBundle` models
- `src/aegis/storage/candidate_store.py` -- `CandidateStore` DuckDB-backed API
- `src/aegis/storage/indexes.py` -- `IndexManager` with MeSH inverted index
- `src/aegis/sources/pubmed.py` -- `PubMedClient`, `PubMedRecord`, `AuthorAffiliation`
- `src/aegis/sources/ctgov.py` -- `CtgovClient`, `StudyRecord`, `InvestigatorRole`
- `src/aegis/sources/reporter.py` -- `ReporterClient`, `GrantRecord`
- `src/aegis/sources/retry.py` -- `RetryPolicy`, `RetryConfig`
- `src/aegis/sources/__init__.py` -- Source client exports
- `src/aegis/cohort/nsclc_translational.py` -- `Cohort`, `CohortConfig`
- `src/aegis/validation/archetypes.py` -- `ArchetypeFixture`, `load_archetypes`
- `pyproject.toml` -- Project configuration

### Existing Files (from Phase 1a, read-only)
- `src/aegis/scoring/__init__.py` -- Scoring package exports (F1-F6, QualityPrior, WeightVector)
- `src/aegis/scoring/quality_prior.py` -- `QualityPrior`, `QualityScore`, `WeightVector`, `load_weight_vector`
- `src/aegis/scoring/f1_rcr.py` through `src/aegis/scoring/f6_lineage.py` -- F-score modules
- `config/aegis/weights/translational_v1.yaml` -- Weight vector with exponents (alpha=0.7, beta=1.0, gamma=0.4)

### New Files
- `src/aegis/sources/leie.py` -- HHS-OIG LEIE exclusion list client
- `src/aegis/sources/ofac_sam.py` -- OFAC/SAM exclusion list client
- `src/aegis/sources/ori.py` -- ORI misconduct findings client
- `src/aegis/sources/retraction_watch.py` -- Retraction Watch database client
- `src/aegis/integrity/__init__.py` -- Integrity package init
- `src/aegis/integrity/hard_gate.py` -- Hard-zero integrity rules
- `src/aegis/integrity/hard_gate_test.py` -- Hard gate tests
- `src/aegis/integrity/soft_discounts.py` -- Soft discount evaluation
- `src/aegis/integrity/predatory.py` -- Predatory-journal detection
- `src/aegis/integrity/papermill.py` -- Paper-mill signal detection
- `src/aegis/integrity/llm_triage.py` -- LLM retraction-notice triage
- `src/aegis/integrity/soft_discounts_test.py` -- Soft discount tests
- `src/aegis/scoring/topical_fit.py` -- T(c,q) topical fit cosine
- `src/aegis/scoring/candidate_vector.py` -- Candidate MeSH topic vector construction
- `src/aegis/scoring/topical_fit_test.py` -- Topical fit tests
- `src/aegis/scoring/recency.py` -- R(c,q) recency scoring
- `src/aegis/scoring/recency_test.py` -- Recency tests
- `src/aegis/scoring/rank.py` -- End-to-end Rank(c,q) wiring
- `src/aegis/scoring/result_format.py` -- Ranked output schema
- `src/aegis/scoring/rank_test.py` -- Ranking tests

## Implementation Phases

### Phase 1: Foundation
- Create integrity source clients (LEIE, OFAC/SAM, ORI, Retraction Watch)
- Create the `src/aegis/integrity/` package structure
- Create predatory-journal and paper-mill detection helpers

### Phase 2: Core Implementation
- Implement hard gate evaluation (binary zero on serious integrity violations)
- Implement soft discount evaluation (multiplicative factors for lesser issues)
- Implement candidate vector construction and topical-fit cosine
- Implement recency time-decay scoring

### Phase 3: Integration & Polish
- Wire end-to-end Rank(c,q) composition with result formatting
- Archetype regression tests (Dr. A top 5%, Dr. D excluded)
- Ensure all modules pass mypy, ruff, and have adequate test coverage

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Integrity source clients (LEIE, OFAC/SAM, ORI, Retraction Watch), integrity package scaffold, predatory/papermill helpers, LLM triage, hard gate, soft discounts
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Topical fit (candidate vector + cosine), recency scoring, end-to-end ranking wiring, result formatting
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Design Updater
  - Name: design-updater
  - Role: Updates docs/design/scoring.md with integrity gate and ranking design decisions after build completes
  - Agent Type: design-updater

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build_v2`.
- Task descriptions must be **exhaustive** -- agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Every task MUST have an `Assigned To` matching a name in Team Members. This is enforced -- tasks without a valid `Assigned To` will not be claimed.
- Start with foundational work, then core implementation, then validation.

### 1. Integrity Source Clients (LEIE, OFAC/SAM, ORI, Retraction Watch)

- **Task ID**: integrity-sources
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create four integrity data source clients following the same in-memory store pattern used by Phase 0 source clients (e.g., `src/aegis/sources/pubmed.py` for Pydantic patterns, but these are simpler in-memory stores). These provide the raw data that the hard gate and soft discounts modules query.

    ## What to do

    1. Create `src/aegis/sources/leie.py`:

       ```python
       """HHS-OIG List of Excluded Individuals/Entities (LEIE) client."""

       from __future__ import annotations

       import logging
       from datetime import date

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class LEIERecord(BaseModel):
           """A single exclusion record from the LEIE database."""

           model_config = ConfigDict(frozen=True)

           name: str
           npi: str | None
           specialty: str | None
           exclusion_type: str  # e.g., "1128(a)(1)", "1128(a)(2)"
           exclusion_date: date
           reinstate_date: date | None
           state: str | None
           waiverstate: str | None


       class LEIEStore:
           """In-memory store for LEIE exclusion records.

           Phase 1 loads from bulk CSV download (updated monthly).
           Phase 3 will add automated download and DB persistence.
           """

           def __init__(self) -> None:
               self._records: list[LEIERecord] = []

           def add_batch(self, records: list[LEIERecord]) -> None:
               self._records.extend(records)

           def is_excluded(self, name: str, npi: str | None = None) -> LEIERecord | None:
               """Check if a person is on the LEIE.

               Match by NPI first (exact), then fall back to name (case-insensitive).
               Returns the matching record or None.
               """
               if npi:
                   for r in self._records:
                       if r.npi == npi and r.reinstate_date is None:
                           return r
               name_lower = name.lower()
               for r in self._records:
                   if r.name.lower() == name_lower and r.reinstate_date is None:
                       return r
               return None

           def lookup_by_name(self, name: str) -> list[LEIERecord]:
               name_lower = name.lower()
               return [r for r in self._records if r.name.lower() == name_lower]

           def count(self) -> int:
               return len(self._records)
       ```

    2. Create `src/aegis/sources/ofac_sam.py`:

       ```python
       """OFAC Specially Designated Nationals (SDN) and SAM.gov exclusion client."""

       from __future__ import annotations

       import logging
       from datetime import date

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class OFACSAMRecord(BaseModel):
           """A single record from OFAC SDN list or SAM.gov exclusions."""

           model_config = ConfigDict(frozen=True)

           name: str
           source: str  # "OFAC" or "SAM"
           entry_type: str  # "Individual" or "Entity"
           program: str | None  # OFAC program, e.g., "SDGT"
           listing_date: date | None
           aliases: list[str]


       class OFACSAMStore:
           """In-memory store for OFAC/SAM exclusion records.

           Phase 1 uses bulk download data.
           Phase 3 will add API integration.
           """

           def __init__(self) -> None:
               self._records: list[OFACSAMRecord] = []

           def add_batch(self, records: list[OFACSAMRecord]) -> None:
               self._records.extend(records)

           def is_listed(self, name: str) -> OFACSAMRecord | None:
               """Check if a name appears on OFAC/SAM lists.

               Checks primary name and aliases (case-insensitive).
               Returns the matching record or None.
               """
               name_lower = name.lower()
               for r in self._records:
                   if r.name.lower() == name_lower:
                       return r
                   if any(a.lower() == name_lower for a in r.aliases):
                       return r
               return None

           def count(self) -> int:
               return len(self._records)
       ```

    3. Create `src/aegis/sources/ori.py`:

       ```python
       """Office of Research Integrity (ORI) misconduct findings client."""

       from __future__ import annotations

       import logging
       from datetime import date

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class ORIFinding(BaseModel):
           """A single ORI misconduct finding."""

           model_config = ConfigDict(frozen=True)

           name: str
           institution: str | None
           finding_date: date
           finding_type: str  # "Fabrication", "Falsification", "Plagiarism"
           case_summary_url: str | None
           voluntary_exclusion_years: int | None
           debarment_end_date: date | None


       class ORIStore:
           """In-memory store for ORI misconduct findings.

           Phase 1 loads from ORI case summaries page.
           Phase 3 will add automated scraping.
           """

           def __init__(self) -> None:
               self._findings: list[ORIFinding] = []

           def add_batch(self, findings: list[ORIFinding]) -> None:
               self._findings.extend(findings)

           def lookup_by_name(self, name: str) -> list[ORIFinding]:
               """Find ORI findings by name (case-insensitive)."""
               name_lower = name.lower()
               return [f for f in self._findings if f.name.lower() == name_lower]

           def has_recent_finding(self, name: str, within_years: int = 10) -> ORIFinding | None:
               """Check if person has an ORI finding within the last N years.

               Returns the most recent matching finding or None.
               """
               name_lower = name.lower()
               cutoff = date.today().year - within_years
               matches = [
                   f for f in self._findings
                   if f.name.lower() == name_lower and f.finding_date.year >= cutoff
               ]
               if not matches:
                   return None
               return max(matches, key=lambda f: f.finding_date)

           def count(self) -> int:
               return len(self._findings)
       ```

    4. Create `src/aegis/sources/retraction_watch.py`:

       ```python
       """Retraction Watch database client for retraction records."""

       from __future__ import annotations

       import logging
       from datetime import date

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class RetractionRecord(BaseModel):
           """A single retraction record from the Retraction Watch database."""

           model_config = ConfigDict(frozen=True)

           pmid: str | None
           doi: str | None
           title: str
           authors: list[str]
           journal: str | None
           retraction_date: date | None
           retraction_nature: str | None  # "Retraction", "Correction", "Expression of Concern"
           reason_tags: list[str]  # e.g., ["Fabrication/Falsification", "Duplication"]
           retraction_notice_url: str | None
           mesh_descriptors: list[str]  # MeSH terms on the retracted paper (for subdomain matching)


       class RetractionWatchStore:
           """In-memory store for Retraction Watch records.

           Phase 1 loads from Retraction Watch database export.
           Phase 3 will add live API integration.
           """

           def __init__(self) -> None:
               self._records: list[RetractionRecord] = []

           def add_batch(self, records: list[RetractionRecord]) -> None:
               self._records.extend(records)

           def lookup_by_author(self, author_name: str) -> list[RetractionRecord]:
               """Find retractions involving a given author (case-insensitive substring)."""
               name_lower = author_name.lower()
               return [
                   r for r in self._records
                   if any(name_lower in a.lower() for a in r.authors)
               ]

           def lookup_by_pmid(self, pmid: str) -> list[RetractionRecord]:
               """Find retraction records for a given PMID."""
               return [r for r in self._records if r.pmid == pmid]

           def count(self) -> int:
               return len(self._records)
       ```

    5. Create test files for each source client:

       `src/aegis/sources/leie_test.py`:
       - `test_add_and_is_excluded`: Add records, verify excluded lookup
       - `test_npi_match_priority`: NPI match takes priority over name
       - `test_reinstated_not_excluded`: Record with reinstate_date is not excluded
       - `test_lookup_case_insensitive`: Case-insensitive name matching

       `src/aegis/sources/ofac_sam_test.py`:
       - `test_add_and_is_listed`: Add records, verify listed lookup
       - `test_alias_match`: Match on an alias name
       - `test_not_listed`: Returns None for unlisted name

       `src/aegis/sources/ori_test.py`:
       - `test_add_and_lookup`: Add findings, lookup by name
       - `test_has_recent_finding_within_window`: Finding within 10 years returns match
       - `test_has_recent_finding_outside_window`: Finding older than 10 years returns None
       - `test_most_recent_returned`: Multiple findings returns most recent

       `src/aegis/sources/retraction_watch_test.py`:
       - `test_add_and_lookup_by_author`: Add records, lookup by author substring
       - `test_lookup_by_pmid`: Lookup by PMID
       - `test_author_case_insensitive`: Case-insensitive author matching

    6. Update `src/aegis/sources/__init__.py` to add exports for all four new stores and their record types. Read the existing file first and append the new imports. The current file imports from ctgov, cursor, pubmed, reporter, retry. Add:

       ```python
       from aegis.sources.leie import LEIERecord, LEIEStore
       from aegis.sources.ofac_sam import OFACSAMRecord, OFACSAMStore
       from aegis.sources.ori import ORIFinding, ORIStore
       from aegis.sources.retraction_watch import RetractionRecord, RetractionWatchStore
       ```

       And add these names to the `__all__` list.

    ## Files to create
    - `src/aegis/sources/leie.py`
    - `src/aegis/sources/leie_test.py`
    - `src/aegis/sources/ofac_sam.py`
    - `src/aegis/sources/ofac_sam_test.py`
    - `src/aegis/sources/ori.py`
    - `src/aegis/sources/ori_test.py`
    - `src/aegis/sources/retraction_watch.py`
    - `src/aegis/sources/retraction_watch_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` -- add new exports (read existing file first, append only)

    ## Code patterns to follow
    - Follow exact patterns from existing source clients in `src/aegis/sources/`:
      - `from __future__ import annotations`
      - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
      - Logger at module level: `logger = logging.getLogger(__name__)`
      - In-memory stores with `add_batch`, lookup methods, `count`
      - Type hints on all functions (mypy strict)
    - Test patterns from existing tests (e.g., `src/aegis/sources/pubmed_test.py`):
      - Standard pytest (not async -- these are in-memory stores)
      - No fixtures needed -- construct data inline
      - Use `from aegis.sources.leie import ...` style imports

    ## Acceptance criteria
    - All four source clients exist and export Store + Record classes
    - Each store has `add_batch` and at least one lookup method
    - LEIE: `is_excluded` returns None for reinstated records
    - ORI: `has_recent_finding` respects the 10-year window
    - Retraction Watch: `lookup_by_author` does substring matching
    - All tests pass
    - mypy strict passes on all four modules
    - ruff passes on all four modules
    - `src/aegis/sources/__init__.py` exports all new types

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/leie_test.py src/aegis/sources/ofac_sam_test.py src/aegis/sources/ori_test.py src/aegis/sources/retraction_watch_test.py -v && uv run mypy src/aegis/sources/leie.py src/aegis/sources/ofac_sam.py src/aegis/sources/ori.py src/aegis/sources/retraction_watch.py && uv run ruff check src/aegis/sources/leie.py src/aegis/sources/ofac_sam.py src/aegis/sources/ori.py src/aegis/sources/retraction_watch.py
    ```

### 2. Integrity Package Scaffold + Predatory/Papermill Helpers

- **Task ID**: integrity-scaffold
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the integrity package structure and the predatory-journal and paper-mill signal detection helper modules. These are standalone utilities used by the soft discounts module.

    ## What to do

    1. Create `src/aegis/integrity/__init__.py`:
       ```python
       """Aegis integrity gate -- hard-zero exclusions and soft discount evaluation."""
       ```

    2. Create `src/aegis/integrity/predatory.py`:

       ```python
       """Predatory-journal detection via Cabells/DOAJ/MEDLINE triangulation."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class PredatorySignal(BaseModel):
           """Result of predatory-journal analysis for a single paper."""

           model_config = ConfigDict(frozen=True)

           pmid: str | None
           journal_nlm_id: str | None
           journal_name: str | None
           is_medline_indexed: bool
           is_doaj_listed: bool
           cabells_flagged: bool  # True if on Cabells predatory list (if access available)
           heuristic_flags: list[str]  # e.g., ["rapid_turnaround", "no_peer_review_evidence"]
           is_predatory: bool  # final determination


       class PredatoryClassifier:
           """Classify journals as predatory via triangulation.

           Strategy (per program overview section 8):
           - If Cabells access available: flagged on Cabells -> predatory
           - Triangulation fallback: NOT MEDLINE-indexed AND NOT in DOAJ AND
             has >= 2 heuristic flags -> predatory
           - MEDLINE-indexed journals are never classified as predatory
           """

           def __init__(
               self,
               cabells_available: bool = False,
               doaj_nlm_ids: frozenset[str] | None = None,
           ) -> None:
               self._cabells_available = cabells_available
               self._doaj_nlm_ids = doaj_nlm_ids or frozenset()

           def classify(
               self,
               journal_nlm_id: str | None,
               is_medline_indexed: bool,
               cabells_flagged: bool = False,
               heuristic_flags: list[str] | None = None,
               pmid: str | None = None,
               journal_name: str | None = None,
           ) -> PredatorySignal:
               """Classify a single journal/paper as predatory or not."""
               flags = heuristic_flags or []
               is_doaj = journal_nlm_id in self._doaj_nlm_ids if journal_nlm_id else False

               # MEDLINE-indexed journals are never predatory
               if is_medline_indexed:
                   is_predatory = False
               elif self._cabells_available and cabells_flagged:
                   is_predatory = True
               elif not is_medline_indexed and not is_doaj and len(flags) >= 2:
                   is_predatory = True
               else:
                   is_predatory = False

               return PredatorySignal(
                   pmid=pmid,
                   journal_nlm_id=journal_nlm_id,
                   journal_name=journal_name,
                   is_medline_indexed=is_medline_indexed,
                   is_doaj_listed=is_doaj,
                   cabells_flagged=cabells_flagged,
                   heuristic_flags=flags,
                   is_predatory=is_predatory,
               )


       class PredatoryLoadCalculator:
           """Calculate the predatory-journal load for a candidate.

           Predatory load = fraction of candidate's papers published in
           predatory journals, weighted by author position.
           """

           def __init__(self, classifier: PredatoryClassifier) -> None:
               self._classifier = classifier

           def compute_load(
               self,
               papers: list[dict[str, object]],
           ) -> tuple[float, list[PredatorySignal]]:
               """Compute predatory load from a list of paper metadata dicts.

               Each dict must have keys: 'pmid', 'journal_nlm_id',
               'is_medline_indexed', 'author_weight' (float 0-1).

               Returns (predatory_load_fraction, list of signals).
               """
               if not papers:
                   return (0.0, [])

               signals: list[PredatorySignal] = []
               total_weight = 0.0
               predatory_weight = 0.0

               for paper in papers:
                   author_weight = float(paper.get("author_weight", 1.0))
                   signal = self._classifier.classify(
                       journal_nlm_id=str(paper.get("journal_nlm_id", "")) or None,
                       is_medline_indexed=bool(paper.get("is_medline_indexed", False)),
                       pmid=str(paper.get("pmid", "")) or None,
                       journal_name=str(paper.get("journal_name", "")) or None,
                   )
                   signals.append(signal)
                   total_weight += author_weight
                   if signal.is_predatory:
                       predatory_weight += author_weight

               load = predatory_weight / total_weight if total_weight > 0 else 0.0
               return (round(load, 6), signals)
       ```

    3. Create `src/aegis/integrity/papermill.py`:

       ```python
       """Paper-mill signal detection via tortured phrases and network analysis."""

       from __future__ import annotations

       import logging
       import re

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       # Tortured-phrase dictionary (Cabanac et al.)
       # These are known machine-generated synonyms for standard scientific terms.
       _TORTURED_PHRASES: dict[str, str] = {
           "sham movement": "random walk",
           "counterfeit neural organization": "artificial neural network",
           "sham network": "artificial neural network",
           "profound learning": "deep learning",
           "huge information": "big data",
           "neural system": "neural network",
           "calculated movement": "random walk",
           "sham neural system": "artificial neural network",
           "massive information": "big data",
           "enormous information": "big data",
       }

       _TORTURED_PATTERN = re.compile(
           "|".join(re.escape(phrase) for phrase in _TORTURED_PHRASES),
           re.IGNORECASE,
       )


       class PaperMillSignal(BaseModel):
           """Paper-mill signal analysis for a single paper."""

           model_config = ConfigDict(frozen=True)

           pmid: str | None
           tortured_phrases_found: list[str]
           tortured_phrase_count: int
           coordinated_authorship_score: float  # 0.0-1.0, network density measure
           is_suspected_papermill: bool


       class PaperMillDetector:
           """Detect paper-mill signals in paper titles and abstracts.

           Two signal types (per program overview section 8):
           1. Tortured-phrase detection (Cabanac): known machine-generated
              synonym substitutions in titles/abstracts.
           2. Coordinated-authorship network density: high density of
              co-authorships among a small group across many papers
              (stub in Phase 1 -- returns 0.0).
           """

           def __init__(self, tortured_phrase_threshold: int = 2) -> None:
               self._threshold = tortured_phrase_threshold

           def analyze(
               self,
               title: str,
               abstract: str | None = None,
               pmid: str | None = None,
               coordinated_authorship_score: float = 0.0,
           ) -> PaperMillSignal:
               """Analyze a single paper for paper-mill signals."""
               text = title
               if abstract:
                   text = text + " " + abstract

               found_phrases: list[str] = []
               for match in _TORTURED_PATTERN.finditer(text):
                   found_phrases.append(match.group())

               # Deduplicate while preserving order
               seen: set[str] = set()
               unique_phrases: list[str] = []
               for phrase in found_phrases:
                   pl = phrase.lower()
                   if pl not in seen:
                       seen.add(pl)
                       unique_phrases.append(phrase)

               is_suspected = (
                   len(unique_phrases) >= self._threshold
                   or coordinated_authorship_score > 0.7
               )

               return PaperMillSignal(
                   pmid=pmid,
                   tortured_phrases_found=unique_phrases,
                   tortured_phrase_count=len(unique_phrases),
                   coordinated_authorship_score=coordinated_authorship_score,
                   is_suspected_papermill=is_suspected,
               )

           def analyze_batch(
               self,
               papers: list[dict[str, str | None]],
           ) -> list[PaperMillSignal]:
               """Analyze multiple papers. Each dict needs 'title', optionally 'abstract' and 'pmid'."""
               return [
                   self.analyze(
                       title=str(p.get("title", "")),
                       abstract=p.get("abstract"),
                       pmid=p.get("pmid"),
                   )
                   for p in papers
               ]
       ```

    4. Create test files:

       `src/aegis/integrity/predatory_test.py`:
       - `test_medline_indexed_never_predatory`: MEDLINE-indexed journal -> not predatory regardless of other flags
       - `test_cabells_flagged_predatory`: Cabells flagged with cabells_available=True -> predatory
       - `test_triangulation_fallback`: Not MEDLINE, not DOAJ, >=2 heuristic flags -> predatory
       - `test_triangulation_insufficient_flags`: Not MEDLINE, not DOAJ, <2 flags -> not predatory
       - `test_predatory_load_calculation`: 10 papers, 3 predatory, weighted by author position -> expected load fraction
       - `test_empty_papers_load`: Empty list -> load 0.0

       `src/aegis/integrity/papermill_test.py`:
       - `test_tortured_phrase_detection`: Title with "deep learning" replaced by "profound learning" -> detected
       - `test_no_tortured_phrases`: Clean title -> no detection
       - `test_threshold_behavior`: 1 phrase with threshold=2 -> not suspected; 2 phrases -> suspected
       - `test_abstract_also_scanned`: Phrase in abstract (not title) -> detected
       - `test_coordinated_authorship_trigger`: Score > 0.7 triggers suspected even without phrases
       - `test_batch_analysis`: Multiple papers analyzed in batch

    ## Files to create
    - `src/aegis/integrity/__init__.py`
    - `src/aegis/integrity/predatory.py`
    - `src/aegis/integrity/predatory_test.py`
    - `src/aegis/integrity/papermill.py`
    - `src/aegis/integrity/papermill_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every file
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for all data classes
    - Logger at module level
    - Type hints on all functions (mypy strict)
    - Tests use standard pytest (not async)

    ## Acceptance criteria
    - `src/aegis/integrity/__init__.py` exists with docstring
    - `PredatoryClassifier` correctly triangulates MEDLINE/DOAJ/heuristics
    - MEDLINE-indexed journals are NEVER classified as predatory
    - `PaperMillDetector` finds tortured phrases in titles and abstracts
    - `PaperMillDetector.analyze_batch` processes multiple papers
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/integrity/predatory_test.py src/aegis/integrity/papermill_test.py -v && uv run mypy src/aegis/integrity/predatory.py src/aegis/integrity/papermill.py && uv run ruff check src/aegis/integrity/predatory.py src/aegis/integrity/papermill.py
    ```

### 3. LLM Retraction-Notice Triage

- **Task ID**: llm-triage
- **Role**: builder
- **Depends On**: integrity-scaffold
- **Assigned To**: builder-1
- **Description**: |
    Implement the LLM-based retraction-notice classifier that categorizes retraction notices into severity buckets. This module is used by soft discounts to distinguish fabrication/falsification retractions (severe) from honest errors (mild).

    ## What to do

    1. Create `src/aegis/integrity/llm_triage.py`:

       ```python
       """LLM-based retraction-notice severity triage.

       Classifies retraction notice text into severity buckets using
       constrained generation. Output is restricted to a closed enum.
       """

       from __future__ import annotations

       import logging
       from enum import StrEnum

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class RetractionSeverity(StrEnum):
           """Severity classification for a retraction notice."""

           fabrication = "fabrication"
           falsification = "falsification"
           honest_error = "honest_error"
           duplicate_publication = "duplicate_publication"
           no_statement = "no_statement"
           unclassifiable = "unclassifiable"


       class TriageResult(BaseModel):
           """Result of LLM triage on a retraction notice."""

           model_config = ConfigDict(frozen=True)

           pmid: str | None
           retraction_notice_text: str
           severity: RetractionSeverity
           confidence: float  # 0.0-1.0
           reasoning: str  # brief explanation from LLM
           grounded: bool  # True if LLM output was in the allowed enum


       # Severity -> discount floor mapping (per program overview section 8)
       SEVERITY_DISCOUNT_MAP: dict[RetractionSeverity, float] = {
           RetractionSeverity.fabrication: 0.0,       # hard zero (goes to hard gate)
           RetractionSeverity.falsification: 0.0,     # hard zero (goes to hard gate)
           RetractionSeverity.honest_error: 0.85,     # mild discount
           RetractionSeverity.duplicate_publication: 0.7,  # moderate discount
           RetractionSeverity.no_statement: 0.6,      # uncertain -> moderate discount
           RetractionSeverity.unclassifiable: 0.7,    # fallback moderate
       }


       _SYSTEM_PROMPT = """You are a scientific integrity classifier. Given the text of a retraction notice, classify it into exactly one of these categories:

       - fabrication: Data fabrication (making up data)
       - falsification: Data falsification (manipulating data or results)
       - honest_error: Honest error (miscalculation, contamination, methodology flaw)
       - duplicate_publication: Duplicate or overlapping publication
       - no_statement: The retraction notice does not state a clear reason

       Respond with a JSON object: {"severity": "<category>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}

       IMPORTANT: The "severity" field MUST be exactly one of: fabrication, falsification, honest_error, duplicate_publication, no_statement"""


       class LLMTriageClassifier:
           """Classify retraction notices into severity buckets.

           Phase 1 uses a keyword-based heuristic as fallback when LLM is
           unavailable. The LLM path uses low-temperature constrained generation.
           Ungrounded (out-of-enum) outputs are rejected and fall back to heuristic.
           """

           def __init__(self, llm_available: bool = False) -> None:
               self._llm_available = llm_available

           def classify(
               self,
               retraction_notice_text: str,
               pmid: str | None = None,
           ) -> TriageResult:
               """Classify a retraction notice into a severity bucket.

               Falls back to keyword heuristic if LLM is not available or
               returns ungrounded output.
               """
               if self._llm_available:
                   # Phase 1 stub: LLM integration placeholder
                   # In production, call LLM API with _SYSTEM_PROMPT and
                   # constrained generation. For now, fall through to heuristic.
                   pass

               return self._heuristic_classify(retraction_notice_text, pmid)

           def _heuristic_classify(
               self,
               text: str,
               pmid: str | None = None,
           ) -> TriageResult:
               """Keyword-based heuristic classification."""
               text_lower = text.lower()

               # Check for fabrication/falsification keywords
               fabrication_keywords = [
                   "fabricat", "made up", "invented data", "fictional",
               ]
               falsification_keywords = [
                   "falsif", "manipulat", "altered data", "image manipulation",
                   "data manipulation", "doctored",
               ]
               honest_error_keywords = [
                   "honest error", "inadvertent", "miscalculation",
                   "contamination", "methodology error", "coding error",
                   "computational error",
               ]
               duplicate_keywords = [
                   "duplicate", "overlapping publication", "redundant publication",
                   "previously published",
               ]

               severity = RetractionSeverity.no_statement
               confidence = 0.4

               if any(kw in text_lower for kw in fabrication_keywords):
                   severity = RetractionSeverity.fabrication
                   confidence = 0.7
               elif any(kw in text_lower for kw in falsification_keywords):
                   severity = RetractionSeverity.falsification
                   confidence = 0.7
               elif any(kw in text_lower for kw in honest_error_keywords):
                   severity = RetractionSeverity.honest_error
                   confidence = 0.6
               elif any(kw in text_lower for kw in duplicate_keywords):
                   severity = RetractionSeverity.duplicate_publication
                   confidence = 0.6

               return TriageResult(
                   pmid=pmid,
                   retraction_notice_text=text,
                   severity=severity,
                   confidence=confidence,
                   reasoning=f"Keyword heuristic: matched '{severity.value}' pattern",
                   grounded=True,
               )

           def classify_batch(
               self,
               notices: list[tuple[str, str | None]],
           ) -> list[TriageResult]:
               """Classify multiple retraction notices.

               Input: list of (notice_text, pmid) tuples.
               """
               return [self.classify(text, pmid) for text, pmid in notices]
       ```

    2. Create `src/aegis/integrity/llm_triage_test.py`:
       - `test_fabrication_keyword_detection`: Notice with "fabrication" -> severity=fabrication
       - `test_falsification_keyword_detection`: Notice with "data manipulation" -> severity=falsification
       - `test_honest_error_detection`: Notice with "honest error" -> severity=honest_error
       - `test_duplicate_detection`: Notice with "overlapping publication" -> severity=duplicate_publication
       - `test_no_statement_fallback`: Generic text without keywords -> severity=no_statement
       - `test_confidence_levels`: Matched keywords get confidence >= 0.6; no_statement gets 0.4
       - `test_batch_classification`: Multiple notices classified correctly
       - `test_grounded_always_true_heuristic`: Heuristic results always have grounded=True
       - `test_severity_discount_map_completeness`: All RetractionSeverity values have an entry in SEVERITY_DISCOUNT_MAP

    ## Files to create
    - `src/aegis/integrity/llm_triage.py`
    - `src/aegis/integrity/llm_triage_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations`
    - Pydantic BaseModel with ConfigDict(frozen=True)
    - StrEnum for severity classification (same pattern as `StrongKeyType` in `src/aegis/storage/schema.py`)
    - Logger at module level
    - Type hints on all functions

    ## Acceptance criteria
    - `LLMTriageClassifier` with `classify` and `classify_batch` methods
    - `RetractionSeverity` enum with 6 values
    - `SEVERITY_DISCOUNT_MAP` maps all 6 severity values to discount floors
    - Heuristic fallback correctly classifies keyword matches
    - All results from heuristic have `grounded=True`
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/integrity/llm_triage_test.py -v && uv run mypy src/aegis/integrity/llm_triage.py && uv run ruff check src/aegis/integrity/llm_triage.py
    ```

### 4. Hard Gate (I(c) Hard-Zero Rules)

- **Task ID**: hard-gate
- **Role**: builder
- **Depends On**: integrity-sources, integrity-scaffold, llm-triage
- **Assigned To**: builder-1
- **Description**: |
    Implement the hard-zero integrity gate that evaluates candidates for exclusion. A hard zero means `I(c) = 0`, which removes the candidate from ranked output entirely. Hard-zero decisions are logged with source artifact IDs for auditability.

    ## What to do

    1. Create `src/aegis/integrity/hard_gate.py`:

       ```python
       """Hard-zero integrity gate: binary exclusion on serious integrity violations."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       from aegis.sources.leie import LEIEStore
       from aegis.sources.ofac_sam import OFACSAMStore
       from aegis.sources.ori import ORIStore
       from aegis.sources.retraction_watch import RetractionWatchStore
       from aegis.integrity.llm_triage import (
           LLMTriageClassifier,
           RetractionSeverity,
       )

       logger = logging.getLogger(__name__)


       class ArtifactRef(BaseModel):
           """Reference to the source artifact that triggered a hard-zero decision."""

           model_config = ConfigDict(frozen=True)

           source: str  # "LEIE", "OFAC", "SAM", "ORI", "RetractionWatch", "MedicalBoard"
           identifier: str  # entry ID, URL, or record identifier
           detail: str  # human-readable summary


       class HardGateResult(BaseModel):
           """Result of hard-gate evaluation for a single candidate."""

           model_config = ConfigDict(frozen=True)

           candidate_uuid: str
           is_zero: bool
           reason: str | None  # human-readable reason for the zero
           artifact_ref: ArtifactRef | None  # pointer to source evidence
           rules_evaluated: list[str]  # which rules were checked


       class HardGate:
           """Evaluate hard-zero integrity rules against a candidate.

           Hard-zero rules (per program overview section 8):
           1. License revocation/suspension (state medical board) -- Phase 1 stub
           2. Federal exclusion (LEIE)
           3. OFAC/SAM listing
           4. ORI misconduct finding within 10 years
           5. Retraction in target subdomain for fabrication/falsification
              (subdomain match via MeSH overlap >= 0.6)
           """

           def __init__(
               self,
               leie_store: LEIEStore,
               ofac_sam_store: OFACSAMStore,
               ori_store: ORIStore,
               retraction_store: RetractionWatchStore,
               llm_triage: LLMTriageClassifier,
               ori_lookback_years: int = 10,
               mesh_overlap_threshold: float = 0.6,
           ) -> None:
               self._leie = leie_store
               self._ofac_sam = ofac_sam_store
               self._ori = ori_store
               self._retractions = retraction_store
               self._llm_triage = llm_triage
               self._ori_lookback = ori_lookback_years
               self._mesh_threshold = mesh_overlap_threshold

           def evaluate(
               self,
               candidate_uuid: str,
               candidate_name: str,
               candidate_npi: str | None,
               candidate_mesh: set[str],
               target_subdomain: set[str],
           ) -> HardGateResult:
               """Evaluate all hard-zero rules for a candidate.

               Args:
                   candidate_uuid: Unique candidate identifier.
                   candidate_name: Primary name for lookups.
                   candidate_npi: NPI number if available.
                   candidate_mesh: Set of MeSH descriptor strings for the candidate.
                   target_subdomain: Set of MeSH descriptor strings for the query/cohort subdomain.

               Returns:
                   HardGateResult with is_zero=True if any hard rule triggers.
               """
               rules_evaluated: list[str] = []

               # Rule 1: LEIE federal exclusion
               rules_evaluated.append("leie_exclusion")
               leie_match = self._leie.is_excluded(candidate_name, candidate_npi)
               if leie_match is not None:
                   return HardGateResult(
                       candidate_uuid=candidate_uuid,
                       is_zero=True,
                       reason=f"Federal exclusion (LEIE): {leie_match.exclusion_type}",
                       artifact_ref=ArtifactRef(
                           source="LEIE",
                           identifier=leie_match.npi or leie_match.name,
                           detail=f"Excluded {leie_match.exclusion_date.isoformat()}, type {leie_match.exclusion_type}",
                       ),
                       rules_evaluated=rules_evaluated,
                   )

               # Rule 2: OFAC/SAM listing
               rules_evaluated.append("ofac_sam_listing")
               ofac_match = self._ofac_sam.is_listed(candidate_name)
               if ofac_match is not None:
                   return HardGateResult(
                       candidate_uuid=candidate_uuid,
                       is_zero=True,
                       reason=f"OFAC/SAM listing ({ofac_match.source}): {ofac_match.program or 'listed'}",
                       artifact_ref=ArtifactRef(
                           source=ofac_match.source,
                           identifier=ofac_match.name,
                           detail=f"Listed on {ofac_match.source}, program={ofac_match.program}",
                       ),
                       rules_evaluated=rules_evaluated,
                   )

               # Rule 3: ORI misconduct finding within lookback window
               rules_evaluated.append("ori_finding")
               ori_match = self._ori.has_recent_finding(candidate_name, self._ori_lookback)
               if ori_match is not None:
                   return HardGateResult(
                       candidate_uuid=candidate_uuid,
                       is_zero=True,
                       reason=f"ORI finding ({ori_match.finding_type}): {ori_match.finding_date.isoformat()}",
                       artifact_ref=ArtifactRef(
                           source="ORI",
                           identifier=ori_match.case_summary_url or ori_match.name,
                           detail=f"{ori_match.finding_type} at {ori_match.institution or 'unknown'}, {ori_match.finding_date.isoformat()}",
                       ),
                       rules_evaluated=rules_evaluated,
                   )

               # Rule 4: Retraction in target subdomain for fabrication/falsification
               rules_evaluated.append("retraction_subdomain")
               retractions = self._retractions.lookup_by_author(candidate_name)
               for retraction in retractions:
                   # Check subdomain overlap via MeSH (Jaccard similarity)
                   retraction_mesh = set(retraction.mesh_descriptors)
                   if target_subdomain and retraction_mesh:
                       overlap = len(retraction_mesh & target_subdomain)
                       union = len(retraction_mesh | target_subdomain)
                       jaccard = overlap / union if union > 0 else 0.0

                       if jaccard >= self._mesh_threshold:
                           # Check if retraction is for fabrication/falsification
                           notice_text = " ".join(retraction.reason_tags)
                           triage = self._llm_triage.classify(notice_text, retraction.pmid)

                           if triage.severity in (
                               RetractionSeverity.fabrication,
                               RetractionSeverity.falsification,
                           ):
                               return HardGateResult(
                                   candidate_uuid=candidate_uuid,
                                   is_zero=True,
                                   reason=f"Subdomain retraction ({triage.severity.value}): PMID {retraction.pmid}",
                                   artifact_ref=ArtifactRef(
                                       source="RetractionWatch",
                                       identifier=retraction.pmid or retraction.doi or "unknown",
                                       detail=f"{triage.severity.value} retraction in target subdomain (Jaccard={jaccard:.2f})",
                                   ),
                                   rules_evaluated=rules_evaluated,
                               )

               # Rule 5: Medical board action -- Phase 1 stub
               rules_evaluated.append("medical_board_stub")

               # No hard-zero triggers
               return HardGateResult(
                   candidate_uuid=candidate_uuid,
                   is_zero=False,
                   reason=None,
                   artifact_ref=None,
                   rules_evaluated=rules_evaluated,
               )
       ```

    2. Create `src/aegis/integrity/hard_gate_test.py`:
       - `test_leie_exclusion_triggers_zero`: Candidate on LEIE -> is_zero=True
       - `test_ofac_listing_triggers_zero`: Candidate on OFAC -> is_zero=True
       - `test_ori_recent_finding_triggers_zero`: ORI finding within 10 years -> is_zero=True
       - `test_ori_old_finding_no_zero`: ORI finding older than 10 years -> is_zero=False
       - `test_subdomain_retraction_fabrication_zero`: Retraction with fabrication + MeSH overlap >= 0.6 -> is_zero=True
       - `test_subdomain_retraction_honest_error_no_zero`: Retraction with honest error + MeSH overlap >= 0.6 -> is_zero=False
       - `test_retraction_low_mesh_overlap_no_zero`: Fabrication retraction but MeSH overlap < 0.6 -> is_zero=False
       - `test_clean_candidate_no_zero`: Candidate not on any list -> is_zero=False
       - `test_rules_evaluated_list`: All 5 rules appear in rules_evaluated when candidate is clean
       - `test_early_exit_on_first_trigger`: When LEIE matches, only "leie_exclusion" is in rules_evaluated (short-circuit)
       - `test_artifact_ref_populated`: Hard-zero result has artifact_ref with source and identifier

       For all tests, create in-memory stores, add test data, and construct `HardGate` with those stores. Use `LLMTriageClassifier(llm_available=False)` for heuristic mode.

       For the subdomain retraction test:
       - Create a `RetractionRecord` with `mesh_descriptors=["Carcinoma, Non-Small-Cell Lung", "Biomarkers, Tumor"]` and `reason_tags=["Fabrication/Falsification"]`
       - Use `target_subdomain={"Carcinoma, Non-Small-Cell Lung", "Biomarkers, Tumor", "Immunotherapy"}` (Jaccard overlap >= 0.6)
       - The LLM heuristic will match "fabricat" in the reason_tags text

    ## Files to create
    - `src/aegis/integrity/hard_gate.py`
    - `src/aegis/integrity/hard_gate_test.py`

    ## Code patterns to follow
    - Pydantic BaseModel with frozen config for all results
    - `from __future__ import annotations`
    - Early-return pattern: first matching rule returns immediately (short-circuit)
    - All decisions include artifact_ref for auditability
    - Logger at module level

    ## Acceptance criteria
    - `HardGate.evaluate` checks LEIE, OFAC/SAM, ORI, and retraction rules in order
    - Short-circuits on first matching rule (doesn't evaluate remaining rules)
    - `HardGateResult` includes `is_zero`, `reason`, `artifact_ref`, and `rules_evaluated`
    - Subdomain retraction uses Jaccard MeSH overlap with threshold 0.6
    - Only fabrication/falsification retractions trigger hard zero (honest errors do not)
    - Medical board rule is stubbed but present in rules_evaluated
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/integrity/hard_gate_test.py -v && uv run mypy src/aegis/integrity/hard_gate.py && uv run ruff check src/aegis/integrity/hard_gate.py
    ```

### 5. Soft Discounts (I(c) Soft Factors)

- **Task ID**: soft-discounts
- **Role**: builder
- **Depends On**: integrity-sources, integrity-scaffold, llm-triage
- **Assigned To**: builder-1
- **Description**: |
    Implement the soft discount evaluation that computes multiplicative discount factors for lesser integrity issues. The combined I(c) value is: if hard_gate is_zero, I(c)=0; otherwise I(c) = product of all soft discount factors, each clamped to its floor.

    ## What to do

    1. Create `src/aegis/integrity/soft_discounts.py`:

       ```python
       """Soft discount evaluation for integrity gate."""

       from __future__ import annotations

       import logging
       from enum import StrEnum

       from pydantic import BaseModel, ConfigDict

       from aegis.integrity.predatory import PredatoryLoadCalculator, PredatorySignal
       from aegis.integrity.papermill import PaperMillDetector, PaperMillSignal
       from aegis.integrity.llm_triage import (
           LLMTriageClassifier,
           RetractionSeverity,
           SEVERITY_DISCOUNT_MAP,
       )
       from aegis.sources.retraction_watch import RetractionWatchStore

       logger = logging.getLogger(__name__)


       # Discount floor caps from program overview section 8
       PREDATORY_FLOOR: float = 0.5
       RETRACTION_FLOOR: float = 0.4
       AUTHORSHIP_INCONSISTENCY_FLOOR: float = 0.85
       PAPERMILL_PENDING_FLOOR: float = 0.7


       class DiscountType(StrEnum):
           """Types of soft discounts."""

           predatory_load = "predatory_load"
           out_of_subdomain_retraction = "out_of_subdomain_retraction"
           authorship_inconsistency = "authorship_inconsistency"
           papermill_pending = "papermill_pending"


       class SoftDiscount(BaseModel):
           """A single soft discount applied to a candidate."""

           model_config = ConfigDict(frozen=True)

           discount_type: DiscountType
           factor: float  # multiplicative factor in (0, 1]
           floor: float  # the minimum this discount can reach
           detail: str  # human-readable explanation
           evidence: list[str]  # artifact references


       class SoftDiscountResult(BaseModel):
           """Combined soft discount result for a candidate."""

           model_config = ConfigDict(frozen=True)

           candidate_uuid: str
           discounts: list[SoftDiscount]
           combined_factor: float  # product of all discount factors


       class SoftDiscounts:
           """Evaluate soft integrity discounts for a candidate.

           Discount types (per program overview section 8):
           1. Predatory-journal load: fraction of papers in predatory journals -> discount
           2. Out-of-subdomain retraction: proportional discount for retractions outside query subdomain
           3. Authorship inconsistency: flag for inconsistent authorship patterns (Phase 1 stub)
           4. Paper-mill pending: suspected paper-mill involvement -> discount

           Each discount has a floor (minimum factor). The combined I(c) soft
           component is the product of all discount factors.
           """

           def __init__(
               self,
               predatory_calculator: PredatoryLoadCalculator,
               papermill_detector: PaperMillDetector,
               retraction_store: RetractionWatchStore,
               llm_triage: LLMTriageClassifier,
           ) -> None:
               self._predatory = predatory_calculator
               self._papermill = papermill_detector
               self._retractions = retraction_store
               self._llm_triage = llm_triage

           def evaluate(
               self,
               candidate_uuid: str,
               candidate_name: str,
               candidate_papers: list[dict[str, object]],
               target_subdomain: set[str],
           ) -> SoftDiscountResult:
               """Evaluate all soft discounts for a candidate.

               Args:
                   candidate_uuid: Unique candidate identifier.
                   candidate_name: Primary name for lookups.
                   candidate_papers: List of paper dicts with keys: 'pmid', 'title',
                       'abstract', 'journal_nlm_id', 'is_medline_indexed',
                       'author_weight', 'mesh_descriptors' (list of str).
                   target_subdomain: MeSH descriptor set for query/cohort.

               Returns:
                   SoftDiscountResult with combined multiplicative factor.
               """
               discounts: list[SoftDiscount] = []

               # 1. Predatory-journal load
               predatory_discount = self._evaluate_predatory(candidate_papers)
               if predatory_discount is not None:
                   discounts.append(predatory_discount)

               # 2. Out-of-subdomain retractions
               retraction_discount = self._evaluate_retractions(
                   candidate_name, target_subdomain
               )
               if retraction_discount is not None:
                   discounts.append(retraction_discount)

               # 3. Authorship inconsistency (Phase 1 stub -- always returns None)
               authorship_discount = self._evaluate_authorship_inconsistency()
               if authorship_discount is not None:
                   discounts.append(authorship_discount)

               # 4. Paper-mill signals
               papermill_discount = self._evaluate_papermill(candidate_papers)
               if papermill_discount is not None:
                   discounts.append(papermill_discount)

               # Combine: product of all factors
               combined = 1.0
               for d in discounts:
                   combined *= d.factor

               return SoftDiscountResult(
                   candidate_uuid=candidate_uuid,
                   discounts=discounts,
                   combined_factor=round(max(combined, 0.0), 6),
               )

           def _evaluate_predatory(
               self, papers: list[dict[str, object]]
           ) -> SoftDiscount | None:
               """Compute predatory-load discount."""
               load, signals = self._predatory.compute_load(papers)
               if load <= 0.0:
                   return None

               # Linear mapping: load 0.0 -> factor 1.0, load 1.0 -> factor PREDATORY_FLOOR
               factor = max(1.0 - load * (1.0 - PREDATORY_FLOOR), PREDATORY_FLOOR)

               predatory_pmids = [
                   s.pmid or "unknown" for s in signals if s.is_predatory
               ]

               return SoftDiscount(
                   discount_type=DiscountType.predatory_load,
                   factor=round(factor, 6),
                   floor=PREDATORY_FLOOR,
                   detail=f"Predatory load {load:.1%}: {len(predatory_pmids)} predatory papers",
                   evidence=predatory_pmids[:10],
               )

           def _evaluate_retractions(
               self, candidate_name: str, target_subdomain: set[str]
           ) -> SoftDiscount | None:
               """Compute out-of-subdomain retraction discount.

               Only applies to retractions that did NOT trigger a hard zero
               (i.e., retractions outside the target subdomain or for non-fabrication reasons).
               """
               retractions = self._retractions.lookup_by_author(candidate_name)
               if not retractions:
                   return None

               out_of_subdomain_count = 0
               evidence: list[str] = []

               for r in retractions:
                   retraction_mesh = set(r.mesh_descriptors)
                   # Check if this retraction is OUT of subdomain
                   if target_subdomain and retraction_mesh:
                       overlap = len(retraction_mesh & target_subdomain)
                       union = len(retraction_mesh | target_subdomain)
                       jaccard = overlap / union if union > 0 else 0.0
                   else:
                       jaccard = 0.0

                   # Out-of-subdomain retraction (Jaccard < 0.6) or non-fabrication
                   if jaccard < 0.6:
                       out_of_subdomain_count += 1
                       evidence.append(r.pmid or r.doi or "unknown")
                   else:
                       # In-subdomain: check if it's non-fabrication (honest error, etc.)
                       notice_text = " ".join(r.reason_tags)
                       triage = self._llm_triage.classify(notice_text, r.pmid)
                       if triage.severity not in (
                           RetractionSeverity.fabrication,
                           RetractionSeverity.falsification,
                       ):
                           out_of_subdomain_count += 1
                           evidence.append(r.pmid or r.doi or "unknown")

               if out_of_subdomain_count == 0:
                   return None

               # Proportional discount: each out-of-subdomain retraction reduces by 0.1
               factor = max(1.0 - out_of_subdomain_count * 0.1, RETRACTION_FLOOR)

               return SoftDiscount(
                   discount_type=DiscountType.out_of_subdomain_retraction,
                   factor=round(factor, 6),
                   floor=RETRACTION_FLOOR,
                   detail=f"{out_of_subdomain_count} out-of-subdomain or non-fabrication retractions",
                   evidence=evidence[:10],
               )

           def _evaluate_authorship_inconsistency(self) -> SoftDiscount | None:
               """Authorship inconsistency check -- Phase 1 stub.

               Phase 1 does not implement authorship inconsistency detection.
               This returns None (no discount applied).
               """
               return None

           def _evaluate_papermill(
               self, papers: list[dict[str, object]]
           ) -> SoftDiscount | None:
               """Check for paper-mill signals across candidate's papers."""
               paper_inputs = [
                   {
                       "title": str(p.get("title", "")),
                       "abstract": p.get("abstract"),
                       "pmid": p.get("pmid"),
                   }
                   for p in papers
               ]

               # Filter to only include papers with string values
               clean_inputs: list[dict[str, str | None]] = []
               for pi in paper_inputs:
                   clean_inputs.append({
                       "title": str(pi["title"]),
                       "abstract": str(pi["abstract"]) if pi["abstract"] else None,
                       "pmid": str(pi["pmid"]) if pi["pmid"] else None,
                   })

               signals = self._papermill.analyze_batch(clean_inputs)
               suspected_count = sum(1 for s in signals if s.is_suspected_papermill)

               if suspected_count == 0:
                   return None

               suspected_pmids = [
                   s.pmid or "unknown"
                   for s in signals
                   if s.is_suspected_papermill
               ]

               # Any suspected paper-mill involvement -> apply floor discount
               return SoftDiscount(
                   discount_type=DiscountType.papermill_pending,
                   factor=PAPERMILL_PENDING_FLOOR,
                   floor=PAPERMILL_PENDING_FLOOR,
                   detail=f"{suspected_count} papers with paper-mill signals",
                   evidence=suspected_pmids[:10],
               )
       ```

    2. Create `src/aegis/integrity/soft_discounts_test.py`:
       - `test_no_discounts_clean_candidate`: Candidate with no issues -> combined_factor=1.0, empty discounts list
       - `test_predatory_load_discount`: Candidate with 30% predatory load -> factor between PREDATORY_FLOOR and 1.0
       - `test_predatory_floor_enforced`: Candidate with 100% predatory load -> factor = PREDATORY_FLOOR (0.5)
       - `test_out_of_subdomain_retraction_discount`: One out-of-subdomain retraction -> factor = 0.9
       - `test_retraction_floor_enforced`: 10 out-of-subdomain retractions -> factor = RETRACTION_FLOOR (0.4)
       - `test_papermill_signals_discount`: Paper with tortured phrases -> factor = PAPERMILL_PENDING_FLOOR (0.7)
       - `test_combined_multiple_discounts`: Predatory + retraction discounts multiply together
       - `test_authorship_inconsistency_stub`: Always returns None (no discount)

       For tests, construct stores with test data and create the SoftDiscounts instance:
       ```python
       from aegis.integrity.predatory import PredatoryClassifier, PredatoryLoadCalculator
       from aegis.integrity.papermill import PaperMillDetector
       from aegis.integrity.llm_triage import LLMTriageClassifier
       from aegis.sources.retraction_watch import RetractionWatchStore, RetractionRecord
       ```

    3. Update `src/aegis/integrity/__init__.py` to export key classes:
       ```python
       """Aegis integrity gate -- hard-zero exclusions and soft discount evaluation."""

       from aegis.integrity.hard_gate import ArtifactRef, HardGate, HardGateResult
       from aegis.integrity.soft_discounts import (
           DiscountType,
           SoftDiscount,
           SoftDiscountResult,
           SoftDiscounts,
       )

       __all__ = [
           "ArtifactRef",
           "DiscountType",
           "HardGate",
           "HardGateResult",
           "SoftDiscount",
           "SoftDiscountResult",
           "SoftDiscounts",
       ]
       ```

    ## Files to create
    - `src/aegis/integrity/soft_discounts.py`
    - `src/aegis/integrity/soft_discounts_test.py`

    ## Files to modify
    - `src/aegis/integrity/__init__.py` -- replace with exports for hard_gate and soft_discounts

    ## Code patterns to follow
    - Same as other integrity modules
    - Multiplicative discount factors (each in (0, 1])
    - Floor enforcement: `max(computed_factor, FLOOR)`

    ## Acceptance criteria
    - `SoftDiscounts.evaluate` returns `SoftDiscountResult` with combined multiplicative factor
    - Predatory load maps linearly from load fraction to discount factor, capped at floor 0.5
    - Out-of-subdomain retractions: each reduces by 0.1, capped at floor 0.4
    - Paper-mill suspicion applies floor discount 0.7
    - Authorship inconsistency is stubbed (returns None)
    - Combined factor is product of all individual discount factors
    - `src/aegis/integrity/__init__.py` exports HardGate, SoftDiscounts, and result types
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/integrity/soft_discounts_test.py -v && uv run mypy src/aegis/integrity/soft_discounts.py && uv run ruff check src/aegis/integrity/soft_discounts.py
    ```

### 6. Candidate Vector Construction + Topical Fit T(c,q)

- **Task ID**: topical-fit
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Implement the candidate topic vector construction and topical-fit cosine similarity T(c,q). The candidate vector v_c aggregates MeSH descriptors from all artifacts, weighted by author role, venue quality, recency, and evidence type. The query vector v_q is built from the query's MeSH terms. T(c,q) = cosine(v_c, v_q).

    ## What to do

    1. Create `src/aegis/scoring/candidate_vector.py`:

       ```python
       """Candidate topic vector construction from MeSH-weighted artifacts."""

       from __future__ import annotations

       import math
       import logging
       from dataclasses import dataclass, field

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       @dataclass
       class ArtifactWeight:
           """Per-artifact weighting factors for topic vector construction."""

           pmid: str | None = None
           role_weight: float = 1.0       # author position: last=1.0, first=0.7, middle=0.3
           venue_weight: float = 1.0      # journal quality proxy (RCR-based); predatory -> ~0
           recency_weight: float = 1.0    # time decay; more recent -> higher
           evidence_type_weight: float = 1.0  # paper=1.0, trial=0.8, grant=0.6
           mesh_descriptors: list[str] = field(default_factory=list)


       class SparseVector:
           """Sparse vector representation for MeSH descriptor space.

           Keys are MeSH descriptor strings. Values are accumulated weights.
           Uses dict internally -- avoids dense 30K-element arrays.
           """

           def __init__(self) -> None:
               self._data: dict[str, float] = {}

           def add(self, key: str, value: float) -> None:
               """Add value to the given key (accumulate)."""
               self._data[key] = self._data.get(key, 0.0) + value

           def get(self, key: str) -> float:
               return self._data.get(key, 0.0)

           def keys(self) -> set[str]:
               return set(self._data.keys())

           def l2_norm(self) -> float:
               """Compute L2 norm of the vector."""
               return math.sqrt(sum(v * v for v in self._data.values()))

           def normalize(self) -> SparseVector:
               """Return a new L2-normalized vector."""
               norm = self.l2_norm()
               result = SparseVector()
               if norm > 0:
                   for k, v in self._data.items():
                       result._data[k] = v / norm  # noqa: SLF001
               return result

           def dot(self, other: SparseVector) -> float:
               """Compute dot product with another sparse vector."""
               # Iterate over the smaller vector for efficiency
               if len(self._data) > len(other._data):
                   return other.dot(self)
               total = 0.0
               for k, v in self._data.items():
                   total += v * other.get(k)
               return total

           def nonzero_count(self) -> int:
               return len(self._data)

           def to_dict(self) -> dict[str, float]:
               return dict(self._data)


       class CandidateVectorBuilder:
           """Build a candidate's MeSH topic vector from their artifacts.

           Per program overview section 3, the candidate vector is constructed
           by accumulating MeSH descriptors across all artifacts, with each
           descriptor weighted by: w_role * w_venue * w_recency * w_evidence_type.

           The result is L2-normalized for cosine similarity computation.
           """

           def build(self, artifacts: list[ArtifactWeight]) -> SparseVector:
               """Build and normalize a candidate topic vector.

               Returns L2-normalized sparse vector over MeSH descriptor space.
               """
               vec = SparseVector()

               for artifact in artifacts:
                   combined_weight = (
                       artifact.role_weight
                       * artifact.venue_weight
                       * artifact.recency_weight
                       * artifact.evidence_type_weight
                   )
                   for mesh_term in artifact.mesh_descriptors:
                       vec.add(mesh_term, combined_weight)

               return vec.normalize()


       class QueryVectorBuilder:
           """Build a query MeSH vector from query terms.

           The query vector assigns equal weight to each query MeSH term,
           then L2-normalizes.
           """

           def build(self, mesh_terms: list[str], weights: dict[str, float] | None = None) -> SparseVector:
               """Build and normalize a query topic vector.

               Args:
                   mesh_terms: List of MeSH descriptor strings for the query.
                   weights: Optional per-term weights (default 1.0 for all).

               Returns L2-normalized sparse vector.
               """
               vec = SparseVector()
               for term in mesh_terms:
                   w = weights.get(term, 1.0) if weights else 1.0
                   vec.add(term, w)
               return vec.normalize()
       ```

    2. Create `src/aegis/scoring/topical_fit.py`:

       ```python
       """T(c,q) topical fit: cosine similarity between candidate and query MeSH vectors."""

       from __future__ import annotations

       import logging

       from aegis.scoring.candidate_vector import (
           CandidateVectorBuilder,
           QueryVectorBuilder,
           SparseVector,
       )

       logger = logging.getLogger(__name__)


       class TopicalFit:
           """Compute topical fit T(c,q) as cosine similarity.

           T(c,q) = cosine(v_c, v_q) where:
           - v_c is the candidate's L2-normalized MeSH topic vector
           - v_q is the query's L2-normalized MeSH topic vector

           Both vectors are pre-normalized, so T = dot(v_c, v_q).
           Result is in [0, 1] for non-negative vectors.
           """

           def compute(
               self,
               candidate_vector: SparseVector,
               query_vector: SparseVector,
           ) -> float:
               """Compute cosine similarity between candidate and query vectors.

               Both vectors should be L2-normalized. Result in [0, 1].
               """
               similarity = candidate_vector.dot(query_vector)
               # Clamp to [0, 1] to handle floating point edge cases
               return max(0.0, min(1.0, round(similarity, 6)))
       ```

    3. Create `src/aegis/scoring/topical_fit_test.py`:
       - `test_sparse_vector_add_and_get`: Basic add/get operations
       - `test_sparse_vector_l2_norm`: Known vector -> expected norm
       - `test_sparse_vector_normalize`: Normalized vector has L2 norm ~1.0
       - `test_sparse_vector_dot`: Dot product of known vectors
       - `test_sparse_vector_empty`: Empty vector has norm 0, dot product 0
       - `test_candidate_vector_builder_basic`: Build vector from 5 artifacts with different weights, verify non-zero entries exist for each MeSH term
       - `test_candidate_vector_builder_predatory_near_zero`: Artifact with venue_weight=0.01 (predatory) contributes ~0 to the vector
       - `test_candidate_vector_builder_empty_artifacts`: No artifacts -> empty normalized vector (all zeros)
       - `test_query_vector_builder_basic`: Build from 3 MeSH terms -> each has equal weight after normalization
       - `test_query_vector_builder_with_weights`: Custom term weights applied correctly
       - `test_topical_fit_identical_vectors`: Candidate and query have same MeSH terms -> T ~= 1.0
       - `test_topical_fit_orthogonal_vectors`: No overlapping MeSH terms -> T = 0.0
       - `test_topical_fit_partial_overlap`: Some shared MeSH terms -> T between 0 and 1
       - `test_topical_fit_range_clamped`: Result always in [0, 1]

    ## Files to create
    - `src/aegis/scoring/candidate_vector.py`
    - `src/aegis/scoring/topical_fit.py`
    - `src/aegis/scoring/topical_fit_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations`
    - Sparse vector representation (dict-based, NOT dense numpy arrays)
    - L2 normalization for cosine similarity
    - Pydantic BaseModel with ConfigDict(frozen=True) for result types
    - Type hints on all functions
    - `math.sqrt` for norm computation (no numpy dependency for this module)

    ## Acceptance criteria
    - `SparseVector` supports add, get, l2_norm, normalize, dot, nonzero_count, to_dict
    - `CandidateVectorBuilder.build` returns L2-normalized SparseVector
    - Predatory-venue artifacts (venue_weight ~0) contribute near-zero to candidate vector
    - `QueryVectorBuilder.build` returns L2-normalized SparseVector
    - `TopicalFit.compute` returns cosine similarity in [0, 1]
    - Identical vectors -> ~1.0; orthogonal vectors -> 0.0
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/topical_fit_test.py -v && uv run mypy src/aegis/scoring/candidate_vector.py src/aegis/scoring/topical_fit.py && uv run ruff check src/aegis/scoring/candidate_vector.py src/aegis/scoring/topical_fit.py
    ```

### 7. R(c,q) Recency Scoring

- **Task ID**: recency
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Implement the recency score R(c,q): time-decayed sum over a candidate's artifacts whose MeSH overlaps the query, squashed to [0, 1].

    ## What to do

    1. Create `src/aegis/scoring/recency.py`:

       ```python
       """R(c,q) recency scoring: time-decayed activity over query-relevant artifacts."""

       from __future__ import annotations

       import math
       import logging
       from dataclasses import dataclass
       from datetime import date

       logger = logging.getLogger(__name__)

       # Default half-life in years (program overview section 9)
       DEFAULT_HALF_LIFE_YEARS: float = 3.0

       # Preprint discount factor (bioRxiv/medRxiv at 0.6x peer-reviewed)
       PREPRINT_DISCOUNT: float = 0.6

       # Squash parameter: controls the saturation curve
       # 1 - exp(-A/s) where s controls how quickly the score saturates
       DEFAULT_SQUASH_SCALE: float = 3.0


       @dataclass
       class RecencyArtifact:
           """A single artifact for recency computation."""

           publication_date: date
           role_weight: float  # author position: last=1.0, first=0.7, middle=0.3
           type_weight: float  # paper=1.0, trial=0.8, grant=0.6
           is_preprint: bool  # bioRxiv/medRxiv
           mesh_descriptors: list[str]  # MeSH terms on this artifact


       class Recency:
           """Compute recency score R(c,q) for a candidate.

           Formula (per program overview section 9):
           A = sum over query-relevant artifacts of:
               w_role * w_type * preprint_discount * exp(-delta_t / tau)
           R(c,q) = 1 - exp(-A / s)

           where:
           - delta_t = years since publication
           - tau = half_life_years / ln(2) (decay constant)
           - s = squash scale parameter
           - preprint_discount = 0.6 for preprints, 1.0 for peer-reviewed

           Result is in [0, 1]. Higher = more recent activity.
           """

           def compute(
               self,
               candidate_artifacts: list[RecencyArtifact],
               query_mesh: set[str],
               reference_date: date | None = None,
               half_life_years: float = DEFAULT_HALF_LIFE_YEARS,
               squash_scale: float = DEFAULT_SQUASH_SCALE,
           ) -> float:
               """Compute R(c,q) for a candidate's artifacts.

               Args:
                   candidate_artifacts: All artifacts for this candidate.
                   query_mesh: MeSH terms from the query (for relevance filtering).
                   reference_date: Date to compute recency from (default: today).
                   half_life_years: Time constant for exponential decay (default: 3.0 years).
                   squash_scale: Saturation parameter for the squash function.

               Returns:
                   R(c,q) in [0, 1].
               """
               if reference_date is None:
                   reference_date = date.today()

               tau = half_life_years / math.log(2)  # decay constant

               accumulated = 0.0
               for artifact in candidate_artifacts:
                   # Filter: only count artifacts with MeSH overlap to query
                   artifact_mesh = set(artifact.mesh_descriptors)
                   if not query_mesh or not artifact_mesh:
                       continue
                   if not (artifact_mesh & query_mesh):
                       continue

                   # Time delta in years
                   delta_days = (reference_date - artifact.publication_date).days
                   delta_years = delta_days / 365.25

                   if delta_years < 0:
                       delta_years = 0.0  # future-dated artifacts treated as today

                   # Exponential decay
                   decay = math.exp(-delta_years / tau) if tau > 0 else 0.0

                   # Preprint discount
                   preprint_factor = PREPRINT_DISCOUNT if artifact.is_preprint else 1.0

                   # Weighted contribution
                   contribution = (
                       artifact.role_weight
                       * artifact.type_weight
                       * preprint_factor
                       * decay
                   )
                   accumulated += contribution

               # Squash to [0, 1]
               if squash_scale <= 0:
                   return 0.0
               score = 1.0 - math.exp(-accumulated / squash_scale)
               return round(max(0.0, min(1.0, score)), 6)
       ```

    2. Create `src/aegis/scoring/recency_test.py`:
       - `test_recent_activity_high_score`: Artifacts from last year with query-relevant MeSH -> R > 0.7
       - `test_old_activity_low_score`: All artifacts > 5 years old -> R < 0.1
       - `test_no_relevant_artifacts`: Artifacts with no MeSH overlap to query -> R = 0.0
       - `test_no_artifacts`: Empty artifact list -> R = 0.0
       - `test_preprint_discount`: Same artifact as preprint vs peer-reviewed -> preprint scores lower
       - `test_half_life_tunable`: Shorter half-life (1 year) penalizes older artifacts more
       - `test_role_weight_matters`: Last-author artifact contributes more than middle-author
       - `test_squash_saturation`: Many recent artifacts -> R approaches 1.0 but never exceeds it
       - `test_result_range`: R is always in [0, 1] for various inputs
       - `test_future_dated_artifact`: Artifact with future date treated as 0 delta

       For test construction, create `RecencyArtifact` objects directly:
       ```python
       from datetime import date, timedelta
       from aegis.scoring.recency import Recency, RecencyArtifact, DEFAULT_HALF_LIFE_YEARS
       ```
       Use a fixed `reference_date=date(2026, 4, 25)` in all tests for determinism.

    ## Files to create
    - `src/aegis/scoring/recency.py`
    - `src/aegis/scoring/recency_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations`
    - `math.exp` and `math.log` for exponential decay (no numpy)
    - Dataclass for input artifacts
    - Logger at module level
    - Type hints on all functions

    ## Acceptance criteria
    - `Recency.compute` returns float in [0, 1]
    - Exponential decay with configurable half-life
    - Preprints discounted at 0.6x
    - Only MeSH-overlapping artifacts count
    - Squash function: `1 - exp(-A/s)` produces smooth saturation
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/recency_test.py -v && uv run mypy src/aegis/scoring/recency.py && uv run ruff check src/aegis/scoring/recency.py
    ```

### 8. End-to-End Rank(c,q) Wiring + Result Format

- **Task ID**: rank-wiring
- **Role**: builder
- **Depends On**: topical-fit, recency, hard-gate, soft-discounts
- **Assigned To**: builder-2
- **Description**: |
    Wire the full scoring identity `Rank(c,q) = I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma` with result formatting, per-component breakdowns, top-3 contributing artifacts, evidence-trail pointers, and identity-linkage confidence.

    This task depends on topical-fit, recency, hard-gate, and soft-discounts being implemented. It imports types from integrity modules (HardGateResult, SoftDiscountResult) and uses its own input type (CandidateScoreInput) that the caller assembles from Q(c), T, R, and I(c) values.

    ## What to do

    1. Create `src/aegis/scoring/result_format.py`:

       ```python
       """Ranked output schema for Aegis scoring engine."""

       from __future__ import annotations

       from pydantic import BaseModel, ConfigDict


       class ContributingArtifact(BaseModel):
           """A top-contributing artifact for a ranked candidate."""

           model_config = ConfigDict(frozen=True)

           artifact_type: str  # "publication", "trial", "grant"
           identifier: str  # PMID, NCT ID, or grant ID
           title: str | None
           contribution_score: float  # how much this artifact contributed to the rank


       class ComponentBreakdown(BaseModel):
           """Per-component score breakdown for a ranked candidate."""

           model_config = ConfigDict(frozen=True)

           integrity_score: float  # I(c): 0.0 or product of soft discounts
           quality_prior: float  # Q(c): percentile
           quality_prior_powered: float  # Q(c)^alpha
           topical_fit: float  # T(c,q): cosine similarity
           topical_fit_powered: float  # T(c,q)^beta
           recency: float  # R(c,q): time-decay score
           recency_powered: float  # R(c,q)^gamma
           final_score: float  # Rank(c,q) = I * Q^a * T^b * R^g


       class RankedCandidate(BaseModel):
           """A single candidate in the ranked output."""

           model_config = ConfigDict(frozen=True)

           rank: int
           candidate_uuid: str
           candidate_name: str | None
           linkage_confidence: float
           score: float  # final Rank(c,q)
           breakdown: ComponentBreakdown
           top_artifacts: list[ContributingArtifact]
           evidence_trail: list[str]


       class RankedList(BaseModel):
           """Complete ranked output for a query."""

           model_config = ConfigDict(frozen=True)

           query_mesh_terms: list[str]
           cohort_size: int
           result_count: int
           candidates: list[RankedCandidate]
           excluded_count: int  # hard-zero candidates excluded
           weight_version: int
           exponents: dict[str, float]  # alpha, beta, gamma used
           metadata: dict[str, str]  # additional context
       ```

    2. Create `src/aegis/scoring/rank.py`:

       ```python
       """End-to-end Rank(c,q) wiring: I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma."""

       from __future__ import annotations

       import logging
       import math

       from aegis.scoring.result_format import (
           ComponentBreakdown,
           ContributingArtifact,
           RankedCandidate,
           RankedList,
       )

       logger = logging.getLogger(__name__)

       # Default exponents from program overview section 9
       DEFAULT_ALPHA: float = 0.7  # Q(c) exponent
       DEFAULT_BETA: float = 1.0   # T(c,q) exponent
       DEFAULT_GAMMA: float = 0.4  # R(c,q) exponent


       class CandidateScoreInput:
           """All scoring components for a single candidate, assembled by the caller."""

           def __init__(
               self,
               candidate_uuid: str,
               candidate_name: str | None,
               linkage_confidence: float,
               integrity_score: float,  # I(c): 0.0 if hard-zero, else product of soft discounts
               quality_percentile: float,  # Q(c) percentile
               topical_fit: float,  # T(c,q)
               recency: float,  # R(c,q)
               top_artifacts: list[ContributingArtifact] | None = None,
               evidence_trail: list[str] | None = None,
               is_hard_zero: bool = False,
           ) -> None:
               self.candidate_uuid = candidate_uuid
               self.candidate_name = candidate_name
               self.linkage_confidence = linkage_confidence
               self.integrity_score = integrity_score
               self.quality_percentile = quality_percentile
               self.topical_fit = topical_fit
               self.recency = recency
               self.top_artifacts = top_artifacts or []
               self.evidence_trail = evidence_trail or []
               self.is_hard_zero = is_hard_zero


       class Ranker:
           """Compute Rank(c,q) = I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma.

           Hard-zero candidates (I(c) = 0) are excluded from the ranked output
           but counted in excluded_count for audit purposes.

           Exponents are loaded from versioned config (WeightVector.exponents).
           """

           def __init__(
               self,
               alpha: float = DEFAULT_ALPHA,
               beta: float = DEFAULT_BETA,
               gamma: float = DEFAULT_GAMMA,
               weight_version: int = 1,
           ) -> None:
               self._alpha = alpha
               self._beta = beta
               self._gamma = gamma
               self._weight_version = weight_version

           def _score_candidate(self, candidate: CandidateScoreInput) -> float:
               """Compute final score for a single candidate."""
               if candidate.is_hard_zero or candidate.integrity_score <= 0.0:
                   return 0.0

               # Clamp components to avoid math domain errors
               q = max(candidate.quality_percentile, 1e-9)
               t = max(candidate.topical_fit, 1e-9)
               r = max(candidate.recency, 1e-9)

               score = (
                   candidate.integrity_score
                   * math.pow(q, self._alpha)
                   * math.pow(t, self._beta)
                   * math.pow(r, self._gamma)
               )
               return round(score, 8)

           def rank(
               self,
               query_mesh_terms: list[str],
               candidates: list[CandidateScoreInput],
               k: int = 50,
               metadata: dict[str, str] | None = None,
           ) -> RankedList:
               """Rank candidates and return top-k results.

               Hard-zero candidates are excluded from the output but counted.
               Results are sorted by descending score.

               Args:
                   query_mesh_terms: MeSH terms used in the query.
                   candidates: All candidate score inputs (including hard-zeros).
                   k: Number of top results to return.
                   metadata: Optional metadata to include in the output.

               Returns:
                   RankedList with top-k candidates and exclusion count.
               """
               excluded_count = 0
               scored: list[tuple[float, CandidateScoreInput]] = []

               for c in candidates:
                   if c.is_hard_zero or c.integrity_score <= 0.0:
                       excluded_count += 1
                       logger.info(
                           "Excluded candidate %s (hard-zero)", c.candidate_uuid
                       )
                       continue

                   score = self._score_candidate(c)
                   scored.append((score, c))

               # Sort by descending score
               scored.sort(key=lambda x: x[0], reverse=True)

               # Build ranked candidates (top-k)
               ranked_candidates: list[RankedCandidate] = []
               for rank_idx, (score, c) in enumerate(scored[:k]):
                   q = max(c.quality_percentile, 1e-9)
                   t = max(c.topical_fit, 1e-9)
                   r = max(c.recency, 1e-9)

                   breakdown = ComponentBreakdown(
                       integrity_score=round(c.integrity_score, 6),
                       quality_prior=round(c.quality_percentile, 6),
                       quality_prior_powered=round(math.pow(q, self._alpha), 6),
                       topical_fit=round(c.topical_fit, 6),
                       topical_fit_powered=round(math.pow(t, self._beta), 6),
                       recency=round(c.recency, 6),
                       recency_powered=round(math.pow(r, self._gamma), 6),
                       final_score=round(score, 8),
                   )

                   ranked_candidates.append(
                       RankedCandidate(
                           rank=rank_idx + 1,
                           candidate_uuid=c.candidate_uuid,
                           candidate_name=c.candidate_name,
                           linkage_confidence=c.linkage_confidence,
                           score=round(score, 8),
                           breakdown=breakdown,
                           top_artifacts=c.top_artifacts[:3],
                           evidence_trail=c.evidence_trail,
                       )
                   )

               return RankedList(
                   query_mesh_terms=query_mesh_terms,
                   cohort_size=len(candidates),
                   result_count=len(ranked_candidates),
                   candidates=ranked_candidates,
                   excluded_count=excluded_count,
                   weight_version=self._weight_version,
                   exponents={
                       "alpha": self._alpha,
                       "beta": self._beta,
                       "gamma": self._gamma,
                   },
                   metadata=metadata or {},
               )
       ```

    3. Create `src/aegis/scoring/rank_test.py`:
       - `test_basic_ranking`: 5 candidates with known scores -> correct rank order
       - `test_hard_zero_excluded`: Candidate with is_hard_zero=True not in output, excluded_count=1
       - `test_zero_integrity_excluded`: Candidate with integrity_score=0.0 not in output
       - `test_top_k_limit`: 10 candidates, k=3 -> only 3 in output
       - `test_component_breakdown_correct`: Known inputs -> verify Q^alpha, T^beta, R^gamma in breakdown
       - `test_exponents_applied`: alpha=0.7 -> Q(c)^0.7 in breakdown matches math.pow(q, 0.7)
       - `test_top_artifacts_limited_to_3`: Candidate with 5 artifacts -> only 3 in output
       - `test_evidence_trail_preserved`: Evidence trail strings passed through to output
       - `test_weight_version_in_output`: weight_version propagated to RankedList
       - `test_empty_candidates`: No candidates -> empty result with result_count=0
       - `test_all_excluded`: All candidates are hard-zero -> empty results, excluded_count matches
       - `test_score_deterministic`: Same inputs -> same output (no randomness)

       For tests, construct `CandidateScoreInput` objects directly:
       ```python
       from aegis.scoring.rank import Ranker, CandidateScoreInput
       from aegis.scoring.result_format import ContributingArtifact
       ```

    4. Update `src/aegis/scoring/__init__.py` to add new exports. Read the existing file first (it has F1-F6, QualityPrior, WeightVector, load_weight_vector). Append:
       ```python
       from aegis.scoring.candidate_vector import (
           ArtifactWeight,
           CandidateVectorBuilder,
           QueryVectorBuilder,
           SparseVector,
       )
       from aegis.scoring.topical_fit import TopicalFit
       from aegis.scoring.recency import Recency, RecencyArtifact
       from aegis.scoring.rank import CandidateScoreInput, Ranker
       from aegis.scoring.result_format import (
           ComponentBreakdown,
           ContributingArtifact,
           RankedCandidate,
           RankedList,
       )
       ```
       And add all these names to the `__all__` list.

    ## Files to create
    - `src/aegis/scoring/result_format.py`
    - `src/aegis/scoring/rank.py`
    - `src/aegis/scoring/rank_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` -- append new exports (read existing first)

    ## Code patterns to follow
    - Pydantic BaseModel with ConfigDict(frozen=True) for all output schemas
    - `from __future__ import annotations`
    - `math.pow` for exponentiation
    - Early return for hard-zero candidates
    - Sorted descending by score
    - Type hints on all functions

    ## Acceptance criteria
    - `Ranker.rank` produces `RankedList` with candidates sorted by descending score
    - Hard-zero candidates excluded from output, counted in `excluded_count`
    - `ComponentBreakdown` shows raw and powered values for Q, T, R
    - Top artifacts limited to 3 per candidate
    - Evidence trail preserved in output
    - Weight version and exponents included in `RankedList`
    - `src/aegis/scoring/__init__.py` exports all new types
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/rank_test.py -v && uv run mypy src/aegis/scoring/rank.py src/aegis/scoring/result_format.py && uv run ruff check src/aegis/scoring/rank.py src/aegis/scoring/result_format.py
    ```

### 9. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: hard-gate, soft-discounts, topical-fit, recency, rank-wiring
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the Phase 1b integrity gate and ranking pipeline.

    ## Validation Commands

    1. Verify integrity package exists and imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.integrity import (
        ArtifactRef, HardGate, HardGateResult,
        DiscountType, SoftDiscount, SoftDiscountResult, SoftDiscounts,
    )
    from aegis.integrity.predatory import PredatoryClassifier, PredatoryLoadCalculator, PredatorySignal
    from aegis.integrity.papermill import PaperMillDetector, PaperMillSignal
    from aegis.integrity.llm_triage import LLMTriageClassifier, RetractionSeverity, TriageResult, SEVERITY_DISCOUNT_MAP
    print('All integrity imports OK')
    "
    ```

    2. Verify integrity source clients import:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.leie import LEIEStore, LEIERecord
    from aegis.sources.ofac_sam import OFACSAMStore, OFACSAMRecord
    from aegis.sources.ori import ORIStore, ORIFinding
    from aegis.sources.retraction_watch import RetractionWatchStore, RetractionRecord
    print('All integrity source imports OK')
    "
    ```

    3. Verify scoring imports (new modules):
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.scoring.candidate_vector import CandidateVectorBuilder, QueryVectorBuilder, SparseVector, ArtifactWeight
    from aegis.scoring.topical_fit import TopicalFit
    from aegis.scoring.recency import Recency, RecencyArtifact
    from aegis.scoring.rank import Ranker, CandidateScoreInput
    from aegis.scoring.result_format import RankedList, RankedCandidate, ComponentBreakdown, ContributingArtifact
    print('All new scoring imports OK')
    "
    ```

    4. Verify scoring __init__ exports all new types:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.scoring import (
        TopicalFit, Recency, RecencyArtifact,
        Ranker, CandidateScoreInput,
        RankedList, RankedCandidate,
        CandidateVectorBuilder, QueryVectorBuilder, SparseVector, ArtifactWeight,
        ComponentBreakdown, ContributingArtifact,
    )
    print('All scoring __init__ exports OK')
    "
    ```

    5. Verify SEVERITY_DISCOUNT_MAP is complete:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.integrity.llm_triage import RetractionSeverity, SEVERITY_DISCOUNT_MAP
    for sev in RetractionSeverity:
        assert sev in SEVERITY_DISCOUNT_MAP, f'Missing {sev}'
    print(f'SEVERITY_DISCOUNT_MAP covers all {len(RetractionSeverity)} severities')
    "
    ```

    6. Run all integrity tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/integrity/ -v
    ```

    7. Run all new scoring tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/topical_fit_test.py src/aegis/scoring/recency_test.py src/aegis/scoring/rank_test.py -v
    ```

    8. Run new source client tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/leie_test.py src/aegis/sources/ofac_sam_test.py src/aegis/sources/ori_test.py src/aegis/sources/retraction_watch_test.py -v
    ```

    9. Run mypy on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/integrity/ src/aegis/scoring/candidate_vector.py src/aegis/scoring/topical_fit.py src/aegis/scoring/recency.py src/aegis/scoring/rank.py src/aegis/scoring/result_format.py src/aegis/sources/leie.py src/aegis/sources/ofac_sam.py src/aegis/sources/ori.py src/aegis/sources/retraction_watch.py
    ```

    10. Run ruff on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/integrity/ src/aegis/scoring/candidate_vector.py src/aegis/scoring/topical_fit.py src/aegis/scoring/recency.py src/aegis/scoring/rank.py src/aegis/scoring/result_format.py src/aegis/sources/leie.py src/aegis/sources/ofac_sam.py src/aegis/sources/ori.py src/aegis/sources/retraction_watch.py
    ```

    11. Verify no existing tests were broken:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/ tests/ -v --tb=short
    ```

    ## Acceptance Criteria
    - 4 integrity source clients exist: leie, ofac_sam, ori, retraction_watch
    - `HardGate.evaluate` checks LEIE, OFAC/SAM, ORI, subdomain retraction, medical board (stub)
    - `SoftDiscounts.evaluate` checks predatory load, out-of-subdomain retractions, paper-mill signals
    - `LLMTriageClassifier` classifies retraction notices into 6 severity buckets
    - `TopicalFit.compute` returns cosine similarity in [0, 1]
    - `Recency.compute` returns time-decayed score in [0, 1] with configurable half-life
    - `Ranker.rank` produces `RankedList` sorted by descending Rank(c,q)
    - Hard-zero candidates excluded from output, counted in excluded_count
    - All results include per-component breakdowns and evidence trails
    - `src/aegis/integrity/__init__.py` exports HardGate, SoftDiscounts, and result types
    - `src/aegis/scoring/__init__.py` exports all new scoring types
    - All tests pass (new and existing)
    - mypy strict passes on all new modules
    - ruff passes on all new modules

### 10. Update Design Doc -- Scoring and Integrity Domain

- **Task ID**: update-design-scoring
- **Role**: design-updater
- **Depends On**: validate-all
- **Assigned To**: design-updater
- **Description**: |
    Update the living design document for the scoring domain to reflect
    what was actually built in this plan (integrity gate + ranking pipeline).

    ## Target Design Doc
    docs/design/scoring.md

    ## Spec File
    specs/aegis-phase1b-integrity-ranking.md

    ## Scope
    Integrity gate architecture (hard-zero rules, soft discount factors), integrity
    source clients (LEIE, OFAC/SAM, ORI, Retraction Watch), predatory-journal
    triangulation, paper-mill detection, LLM retraction triage, topical-fit sparse
    vector construction, recency time-decay scoring, end-to-end Rank(c,q) composition,
    and result formatting.

    ## Prior Decisions to Check
    If `docs/design/scoring.md` exists from Phase 1a, check decisions about:
    - F-score interface patterns (FNComputer.score -> FNScore with percentile)
    - Geometric-mean composition choice
    - Weight configuration schema and versioning
    - Percentile calibration method
    These should be preserved; this build adds integrity and ranking on top.

    ## What to Record
    Read `git diff HEAD~1 HEAD`, then the changed source files, then the existing
    design doc (if it exists). Update Current Design to include:
    - Integrity gate two-tier architecture (hard-zero + soft discounts)
    - Hard gate rule evaluation order and short-circuit behavior
    - Soft discount multiplication pattern with floor enforcement
    - Predatory triangulation strategy (MEDLINE/DOAJ/heuristic)
    - LLM triage keyword heuristic fallback pattern
    - Sparse vector MeSH representation for topical fit
    - Exponential decay formula for recency with squash function
    - Rank(c,q) composition formula and exponent loading
    - Result format schema (RankedList -> RankedCandidate -> ComponentBreakdown)

    Append Design Decision entries for:
    - Jaccard (not cosine) for subdomain retraction MeSH overlap (with threshold 0.6)
    - Sparse dict representation over dense numpy for MeSH vectors
    - Multiplicative (not additive) discount combination
    - Short-circuit evaluation in hard gate
    - Keyword heuristic as LLM fallback in Phase 1

    Every claim must cite a file:line from the actual code.

## Acceptance Criteria

- 4 integrity source clients exist at `src/aegis/sources/{leie,ofac_sam,ori,retraction_watch}.py`
- `HardGate` at `src/aegis/integrity/hard_gate.py` evaluates 5 rules (LEIE, OFAC/SAM, ORI, subdomain retraction, medical board stub) with short-circuit and audit trails
- `SoftDiscounts` at `src/aegis/integrity/soft_discounts.py` evaluates 4 discount types with floors (predatory=0.5, retraction=0.4, authorship=0.85, papermill=0.7)
- `PredatoryClassifier` correctly implements MEDLINE/DOAJ/heuristic triangulation (MEDLINE never predatory)
- `PaperMillDetector` detects tortured phrases and supports batch analysis
- `LLMTriageClassifier` classifies retraction notices via keyword heuristic fallback
- `TopicalFit` at `src/aegis/scoring/topical_fit.py` computes cosine similarity via sparse MeSH vectors in [0, 1]
- `Recency` at `src/aegis/scoring/recency.py` computes time-decayed score in [0, 1] with configurable half-life and preprint discount
- `Ranker` at `src/aegis/scoring/rank.py` wires `Rank(c,q) = I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma` with default exponents alpha=0.7, beta=1.0, gamma=0.4
- `RankedList` includes per-component breakdowns, top-3 artifacts, evidence trails, and excluded count
- Hard-zero candidates excluded from output, retained in audit logs (excluded_count)
- `src/aegis/integrity/__init__.py` exports HardGate, SoftDiscounts, and related types
- `src/aegis/scoring/__init__.py` exports all new scoring types (TopicalFit, Recency, Ranker, etc.)
- All tests pass: `uv run pytest src/aegis/integrity/ src/aegis/scoring/topical_fit_test.py src/aegis/scoring/recency_test.py src/aegis/scoring/rank_test.py -v`
- mypy strict passes on all new modules
- ruff passes on all new modules
- No existing Phase 0/1a tests broken

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/integrity/ -v` -- Run all integrity tests
- `cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/topical_fit_test.py src/aegis/scoring/recency_test.py src/aegis/scoring/rank_test.py -v` -- Run new scoring tests
- `cd /Users/anvith/aegis && uv run pytest src/aegis/sources/leie_test.py src/aegis/sources/ofac_sam_test.py src/aegis/sources/ori_test.py src/aegis/sources/retraction_watch_test.py -v` -- Run integrity source tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/integrity/ src/aegis/scoring/candidate_vector.py src/aegis/scoring/topical_fit.py src/aegis/scoring/recency.py src/aegis/scoring/rank.py src/aegis/scoring/result_format.py src/aegis/sources/leie.py src/aegis/sources/ofac_sam.py src/aegis/sources/ori.py src/aegis/sources/retraction_watch.py` -- Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/integrity/ src/aegis/scoring/candidate_vector.py src/aegis/scoring/topical_fit.py src/aegis/scoring/recency.py src/aegis/scoring/rank.py src/aegis/scoring/result_format.py src/aegis/sources/leie.py src/aegis/sources/ofac_sam.py src/aegis/sources/ori.py src/aegis/sources/retraction_watch.py` -- Lint all new modules
- `cd /Users/anvith/aegis && uv run pytest src/ tests/ -v --tb=short` -- Verify no existing tests broken
- `cd /Users/anvith/aegis && uv run python -c "from aegis.integrity import HardGate, SoftDiscounts; from aegis.scoring import Ranker, TopicalFit, Recency; print('All key imports OK')"` -- Verify key imports

## Notes

- This is Phase 1b of 3 Phase 1 sub-specs. Phase 1a covers Q(c) foundation (F1-F6 + composition). Phase 1c covers audit harness, Plackett-Luce weight learning, bootstrap variance, and observability dashboards.
- Medical board actions are stubbed in Phase 1 (rule is present but returns no match). Full federation of state APIs is Phase 2+.
- Cabells predatory list access is assumed unavailable in Phase 1; the triangulation fallback (MEDLINE/DOAJ/heuristic) is documented as having lower coverage.
- LLM retraction triage uses a keyword heuristic in Phase 1. The LLM integration (constrained generation with low temperature) is the Phase 3 upgrade path. The `llm_available` constructor flag controls the switch.
- Authorship inconsistency detection is Phase 1 stub (returns None / no discount). Phase 2 adds the full detection logic.
- bioRxiv/medRxiv ingestion is Phase 3 daily; Phase 1 uses Phase 0's monthly-snapshot ingestion. Preprint discount factor (0.6x) is in place but will under-count preprint activity.
- The `SparseVector` class uses a Python dict internally, not numpy dense arrays. This avoids the ~30K-element MeSH descriptor space allocation per candidate. At Phase 1 cohort scale (~5K candidates), this is sufficient.
- The `Ranker` class does NOT depend on Phase 1a being importable at runtime -- it only uses its own types (`CandidateScoreInput`) and the caller is responsible for assembling the inputs from Q(c), T, R, and I(c). This allows the ranking module to be tested independently.
