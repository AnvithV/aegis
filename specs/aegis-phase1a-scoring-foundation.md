# Plan: Phase 1a — Scoring Foundation (Quality Prior F1–F6 + Composition)

> **Status:** COMPLETE (2026-04-26)
> All 13 tasks completed. 43/43 scoring tests passing, 16/16 source tests passing. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-26
> **Team:** aegis-phase1a-scoring-20260426-1000

### Test Results
- `src/aegis/scoring/f1_rcr_test.py` — 6/6 PASSED
- `src/aegis/scoring/f2_funding_test.py` — 6/6 PASSED
- `src/aegis/scoring/f3_leadership_test.py` — 6/6 PASSED
- `src/aegis/scoring/f4_apex_test.py` — 6/6 PASSED
- `src/aegis/scoring/f5_translational_test.py` — 6/6 PASSED
- `src/aegis/scoring/f6_lineage_test.py` — 5/5 PASSED
- `src/aegis/scoring/quality_prior_test.py` — 8/8 PASSED
- `src/aegis/sources/icite_test.py` — 3/3 PASSED
- `src/aegis/sources/apex_rosters_test.py` — 5/5 PASSED
- `src/aegis/sources/drugs_fda_test.py` — 2/2 PASSED
- `src/aegis/sources/nccn_test.py` — 3/3 PASSED
- `src/aegis/sources/academic_tree_test.py` — 3/3 PASSED
- Full test suite: 206/207 passed (1 pre-existing failure in `cohort/audit_test.py::test_daily_summary`, unrelated to Phase 1a)
- mypy: Success, no issues found in 20 source files
- ruff: All checks passed

### Acceptance Criteria Verification
- [x] All 6 F-score modules (F1-F6) exist — VERIFIED (f1_rcr.py, f2_funding.py, f3_leadership.py, f4_apex.py, f5_translational.py, f6_lineage.py each with Computer and Score classes)
- [x] Each Score type includes a percentile field in [0, 1] — VERIFIED (all 6 Score models have `percentile: float` field, tests confirm range [0, 1])
- [x] QualityPrior at quality_prior.py composes F-scores via geometric mean with YAML-loaded weights — VERIFIED (geometric mean in log space, loads WeightVector from YAML)
- [x] WeightVector loaded from config/aegis/weights/translational_v1.yaml — VERIFIED (v1: F1=0.35, F2=0.25, F3=0.20, F4=0.05, F5=0.10, F6=0.05, sum=1.0)
- [x] 5 new source clients — VERIFIED (icite.py, apex_rosters.py, drugs_fda.py, nccn.py, academic_tree.py all exist)
- [x] data/aegis/editorial_roles_phase1.yaml exists with >= 5 journals — VERIFIED (5 journals)
- [x] Reweight invariance — VERIFIED (quality_prior_test.py tests pass, scaling weights by constant does not change percentile output)
- [x] Geometric-mean penalizes spiky candidates — VERIFIED (quality_prior_test.py tests pass, one high + one low < two medium)
- [x] All scoring tests pass — VERIFIED (43/43 passed)
- [x] All new source tests pass — VERIFIED (16/16 passed)
- [x] mypy strict passes on all new modules — VERIFIED (no issues in 20 source files)
- [x] ruff passes on all new modules — VERIFIED (all checks passed)
- [x] No existing Phase 0 tests broken — VERIFIED (1 pre-existing failure in audit_test.py predates Phase 1a; all other 206 tests pass)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `src/aegis/scoring/__init__.py` | Created | Yes |
| `src/aegis/scoring/f1_rcr.py` | Created | Yes |
| `src/aegis/scoring/f1_rcr_test.py` | Created | Yes |
| `src/aegis/scoring/f2_funding.py` | Created | Yes |
| `src/aegis/scoring/f2_funding_test.py` | Created | Yes |
| `src/aegis/scoring/f3_leadership.py` | Created | Yes |
| `src/aegis/scoring/f3_leadership_test.py` | Created | Yes |
| `src/aegis/scoring/f4_apex.py` | Created | Yes |
| `src/aegis/scoring/f4_apex_test.py` | Created | Yes |
| `src/aegis/scoring/f5_translational.py` | Created | Yes |
| `src/aegis/scoring/f5_translational_test.py` | Created | Yes |
| `src/aegis/scoring/f6_lineage.py` | Created | Yes |
| `src/aegis/scoring/f6_lineage_test.py` | Created | Yes |
| `src/aegis/scoring/quality_prior.py` | Created | Yes |
| `src/aegis/scoring/quality_prior_test.py` | Created | Yes |
| `src/aegis/sources/icite.py` | Created | Yes |
| `src/aegis/sources/icite_test.py` | Created | Yes |
| `src/aegis/sources/apex_rosters.py` | Created | Yes |
| `src/aegis/sources/apex_rosters_test.py` | Created | Yes |
| `src/aegis/sources/drugs_fda.py` | Created | Yes |
| `src/aegis/sources/drugs_fda_test.py` | Created | Yes |
| `src/aegis/sources/nccn.py` | Created | Yes |
| `src/aegis/sources/nccn_test.py` | Created | Yes |
| `src/aegis/sources/academic_tree.py` | Created | Yes |
| `src/aegis/sources/academic_tree_test.py` | Created | Yes |
| `config/aegis/weights/translational_v1.yaml` | Created | Yes |
| `data/aegis/editorial_roles_phase1.yaml` | Created | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase1a-scoring-foundation.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build the quality prior `Q(c)` scoring foundation for Aegis Phase 1. This covers all six feature families (F1–F6) that compose the quality prior, the geometric-mean composition layer, percentile calibration, and the versioned weight configuration. This is the first of three Phase 1 sub-specs; it establishes the scoring modules that Phase 1b (integrity gate, topical-fit, recency, ranking) and Phase 1c (audit harness, weight learning, observability) depend on.

Each feature family (F1–F6) computes a sub-score for a candidate, producing a percentile rank within the specialty cohort. The sub-scores compose into `Q(c) = prod(F_i(c)^{w_i})` via a geometric mean, then percentile-calibrated for output stability.

This plan depends on Phase 0 being complete. The Phase 0 codebase provides:
- `Candidate` schema at `src/aegis/storage/schema.py` (uuid, strong_keys, name_variants, affiliations, artifact_refs, mesh_descriptors, linkage_confidence)
- `CandidateStore` at `src/aegis/storage/candidate_store.py` (DuckDB-backed CRUD)
- `PubMedClient` at `src/aegis/sources/pubmed.py` (returns `PubMedRecord` with authors, mesh_descriptors, article_type, publication_date)
- `ReporterClient` at `src/aegis/sources/reporter.py` (returns `GrantRecord` with pis, activity_code, total_cost, is_active)
- `CtgovClient` at `src/aegis/sources/ctgov.py` (returns `StudyRecord` with investigators, phase, sponsor)
- `IndexManager` at `src/aegis/storage/indexes.py` (MeSH inverted index, yearly counts)
- `Cohort` at `src/aegis/cohort/nsclc_translational.py` (cohort builder with candidate UUIDs)
- `ArchetypeFixture` at `src/aegis/validation/archetypes.py` (Dr. A, Dr. B, Dr. C, Dr. D)
- All Pydantic models use `ConfigDict(frozen=True)`, `from __future__ import annotations`, mypy strict mode

The plan also creates new source clients for iCite, Drugs@FDA, NCCN, apex rosters, and Academic Family Tree.

## Objective

When this plan is complete:
1. Six scoring modules (F1–F6) exist, each exporting a `Computer` class with a `score(candidate) -> FScore` method returning percentile and component fields.
2. A `QualityPrior` composition module computes `Q(c)` via geometric mean with configurable weights loaded from versioned YAML.
3. A default weight configuration exists at `config/aegis/weights/translational_v1.yaml`.
4. New source clients exist for iCite (RCR data), Drugs@FDA, NCCN guideline panels, apex rosters, and Academic Family Tree.
5. All modules pass mypy strict, ruff lint, and have unit tests with >=90% coverage on the scoring directory.
6. `Q(c)` percentile distribution is approximately uniform on synthetic cohort data.

## Problem Statement

Phase 0 produced a candidate substrate with identity resolution and artifact linkage. To rank candidates, Aegis needs a multi-dimensional quality prior that captures research impact (F1), funding success (F2), leadership signals (F3), apex-tier recognition (F4), translational impact (F5), and mentorship lineage (F6). Each dimension must be independently computable, percentile-calibrated, and composable via a weighted geometric mean. The weights must be versioned for the learning loop in Phase 1c.

## Solution Approach

1. **Data ingestion first**: Create new source clients (iCite, Drugs@FDA, NCCN, apex rosters, Academic Family Tree) that the scoring modules depend on.
2. **Parallel F-score implementation**: F1–F6 are independent and can be built in parallel by separate builders. Each follows the same interface pattern: `FNComputer.score(candidate) -> FNScore`.
3. **Composition layer**: After all F-scores exist, wire the geometric-mean composition with YAML-loaded weights and percentile calibration.
4. **Testing**: Each module gets synthetic-data unit tests. The composition layer gets a distribution uniformity test.

## Relevant Files

### Existing Files (read-only, do not modify)
- `src/aegis/storage/schema.py` — `Candidate`, `MeshDescriptor`, `ArtifactRefBundle` models
- `src/aegis/storage/candidate_store.py` — `CandidateStore` DuckDB-backed API
- `src/aegis/sources/pubmed.py` — `PubMedClient`, `PubMedRecord`, `AuthorAffiliation`
- `src/aegis/sources/reporter.py` — `ReporterClient`, `GrantRecord`, `GrantPI`
- `src/aegis/sources/ctgov.py` — `CtgovClient`, `StudyRecord`, `InvestigatorRole`
- `src/aegis/sources/retry.py` — `RetryPolicy`, `RetryConfig`
- `src/aegis/storage/indexes.py` — `IndexManager`
- `src/aegis/cohort/nsclc_translational.py` — `Cohort`, `build_nsclc_translational_cohort`
- `src/aegis/validation/archetypes.py` — `ArchetypeFixture`, `load_archetypes`
- `pyproject.toml` — Project configuration

### New Files
- `src/aegis/sources/icite.py` — iCite RCR data client
- `src/aegis/sources/drugs_fda.py` — Drugs@FDA bulk data client
- `src/aegis/sources/nccn.py` — NCCN guideline panel scraper
- `src/aegis/sources/apex_rosters.py` — Apex roster ingestion (HHMI, NAS, NAM, NAE, MERIT, Lasker, Hanna Gray)
- `src/aegis/sources/academic_tree.py` — Academic Family Tree data client
- `src/aegis/scoring/__init__.py` — Package init with exports
- `src/aegis/scoring/f1_rcr.py` — F1: RCR aggregation
- `src/aegis/scoring/f1_rcr_test.py` — F1 tests
- `src/aegis/scoring/f2_funding.py` — F2: NIH funding
- `src/aegis/scoring/f2_funding_test.py` — F2 tests
- `src/aegis/scoring/f3_leadership.py` — F3: PI / leadership
- `src/aegis/scoring/f3_leadership_test.py` — F3 tests
- `src/aegis/scoring/f4_apex.py` — F4: Apex-tier flag
- `src/aegis/scoring/f4_apex_test.py` — F4 tests
- `src/aegis/scoring/f5_translational.py` — F5: Translational impact
- `src/aegis/scoring/f5_translational_test.py` — F5 tests
- `src/aegis/scoring/f6_lineage.py` — F6: Mentorship / lineage
- `src/aegis/scoring/f6_lineage_test.py` — F6 tests
- `src/aegis/scoring/quality_prior.py` — Q(c) composition + percentile calibration
- `src/aegis/scoring/quality_prior_test.py` — Q(c) tests
- `config/aegis/weights/translational_v1.yaml` — Default weight vector
- `data/aegis/editorial_roles_phase1.yaml` — Handcrafted editorial roles for F3

## Implementation Phases

### Phase 1: Foundation
- Create the `src/aegis/scoring/` package structure
- Build new source clients (iCite, apex_rosters, drugs_fda, nccn, academic_tree)
- Create the versioned weight config YAML and editorial roles data file

### Phase 2: Core Implementation
- Implement F1–F6 scoring modules in parallel (each is independent)
- Each module: data ingestion helper, scoring logic, percentile computation, unit tests

### Phase 3: Integration & Polish
- Wire the geometric-mean composition layer (`quality_prior.py`)
- Test composition: uniform distribution, reweight invariance
- Ensure all modules pass mypy, ruff, and have adequate coverage

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Package scaffold, iCite source client, F1 (RCR), F2 (Funding), quality prior composition
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: F3 (Leadership), F4 (Apex), apex rosters source client, editorial roles data
  - Agent Type: general-purpose
- Builder
  - Name: builder-3
  - Role: F5 (Translational), F6 (Lineage), drugs_fda source client, nccn source client, academic_tree source client
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Design Updater
  - Name: design-updater
  - Role: Updates docs/design/scoring.md with code-aligned design decisions after build completes
  - Agent Type: design-updater

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build_v2`.
- Task descriptions must be **exhaustive** — agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Every task MUST have an `Assigned To` matching a name in Team Members. This is enforced — tasks without a valid `Assigned To` will not be claimed.
- Start with foundational work, then core implementation, then validation.

### 1. Scaffold Scoring Package + Weight Config + Dependencies

- **Task ID**: scaffold-scoring
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the scoring package structure, weight configuration, and add new dependencies to pyproject.toml.

    ## What to do

    1. Create `src/aegis/scoring/__init__.py` with a docstring:
       ```python
       """Aegis scoring engine — quality prior, topical fit, recency, and ranking."""
       ```

    2. Create `config/aegis/weights/translational_v1.yaml` with the default weight vector from the program overview:
       ```yaml
       # Translational specialty weight vector v1 (cold-start prior)
       # Weights sum to 1.0; used in geometric-mean composition Q(c) = prod(F_i^w_i)
       version: 1
       specialty: translational
       created: "2026-04-25"
       weights:
         f1_rcr: 0.35
         f2_funding: 0.25
         f3_leadership: 0.20
         f4_apex: 0.05
         f5_translational: 0.10
         f6_lineage: 0.05
       exponents:
         alpha: 0.7   # Q(c) exponent in Rank formula
         beta: 1.0    # T(c,q) exponent
         gamma: 0.4   # R(c,q) exponent
       exponent_bounds:
         alpha: [0.3, 1.2]
         beta: [0.5, 1.5]
         gamma: [0.1, 0.8]
       ```

    3. Create the directory structure:
       - `config/aegis/weights/` (create parent dirs as needed)
       - `data/aegis/` (create if not exists)

    4. Add `scipy` and `choix` to `pyproject.toml` dependencies (needed for Plackett-Luce in Phase 1c, but add now to avoid dependency issues later):
       Add to the `dependencies` list in `pyproject.toml`:
       - `"scipy>=1.12"`
       - `"numpy>=1.26"`

       Do NOT remove or modify any existing dependencies. Only append new ones to the list.

    5. After modifying `pyproject.toml`, run `cd /Users/anvith/aegis && uv lock` to update the lock file (do NOT run `uv sync` — just `uv lock`).

    ## Files to create
    - `src/aegis/scoring/__init__.py`
    - `config/aegis/weights/translational_v1.yaml`

    ## Files to modify
    - `pyproject.toml` — append `scipy>=1.12` and `numpy>=1.26` to dependencies list

    ## Code patterns to follow
    - Use `from __future__ import annotations` at top of every `.py` file
    - YAML files use standard YAML syntax with comments
    - pyproject.toml: append to existing list, do not rewrite

    ## Acceptance criteria
    - `src/aegis/scoring/__init__.py` exists
    - `config/aegis/weights/translational_v1.yaml` exists and is valid YAML with weights summing to 1.0
    - `pyproject.toml` contains `scipy` and `numpy` in dependencies
    - `uv lock` succeeds without errors

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -c "import yaml; d=yaml.safe_load(open('config/aegis/weights/translational_v1.yaml')); w=d['weights']; assert abs(sum(w.values()) - 1.0) < 0.001, f'Weights sum to {sum(w.values())}'; print('Weight config OK')" && uv lock --check && echo "Lock file OK"
    ```

### 2. iCite Source Client

- **Task ID**: icite-client
- **Role**: builder
- **Depends On**: scaffold-scoring
- **Assigned To**: builder-1
- **Description**: |
    Build the iCite source client for ingesting Relative Citation Ratio (RCR) data from NIH iCite. iCite provides RCR as a field-normalized citation metric for each PMID.

    ## What to do

    1. Create `src/aegis/sources/icite.py` with:

       ```python
       """NIH iCite API client for Relative Citation Ratio (RCR) data."""

       from __future__ import annotations

       import logging
       from collections.abc import AsyncIterator

       import httpx
       from pydantic import BaseModel, ConfigDict

       from aegis.sources.retry import RetryConfig, RetryPolicy

       logger = logging.getLogger(__name__)

       ICITE_API_URL = "https://icite.od.nih.gov/api/pubs"


       class IciteRecord(BaseModel):
           """RCR and citation data for a single PubMed article."""

           model_config = ConfigDict(frozen=True)

           pmid: str
           year: int | None
           relative_citation_ratio: float | None
           citation_count: int
           expected_citations_per_year: float | None
           field_citation_rate: float | None
           is_research_article: bool
           doi: str | None


       class IciteClient:
           """Client for the NIH iCite API (batch PMID lookups)."""

           def __init__(
               self,
               retry_policy: RetryPolicy | None = None,
           ) -> None:
               self._retry = retry_policy or RetryPolicy(RetryConfig())

           async def fetch_by_pmids(
               self,
               pmids: list[str],
               batch_size: int = 200,
           ) -> AsyncIterator[IciteRecord]:
               """Fetch iCite records for a list of PMIDs in batches.

               The iCite API accepts up to 200 PMIDs per request.
               """
               async with httpx.AsyncClient(timeout=60.0) as client:
                   for i in range(0, len(pmids), batch_size):
                       batch = pmids[i : i + batch_size]
                       pmid_str = ",".join(batch)

                       async def _do_get(p: str = pmid_str) -> httpx.Response:
                           resp = await client.get(
                               ICITE_API_URL,
                               params={"pmids": p, "format": "json"},
                           )
                           resp.raise_for_status()
                           return resp

                       response = await self._retry.execute(_do_get)
                       body = response.json()
                       records = body.get("data") or body if isinstance(body, list) else [body]
                       if isinstance(body, dict) and "data" in body:
                           records = body["data"]

                       for item in records:
                           if not isinstance(item, dict):
                               continue
                           yield IciteRecord(
                               pmid=str(item.get("pmid", "")),
                               year=item.get("year"),
                               relative_citation_ratio=item.get("relative_citation_ratio"),
                               citation_count=item.get("citation_count", 0),
                               expected_citations_per_year=item.get("expected_citations_per_year"),
                               field_citation_rate=item.get("field_citation_rate"),
                               is_research_article=bool(item.get("is_research_article", False)),
                               doi=item.get("doi"),
                           )
       ```

    2. Create `src/aegis/sources/icite_test.py` with fixture-based tests (no live API calls):
       - `test_icite_parse_single_record`: Create a mock response dict, verify `IciteRecord` parses correctly
       - `test_icite_batch_fetch`: Mock httpx to return a batch of 5 records, verify all 5 are yielded
       - `test_icite_missing_rcr`: Verify a record with `relative_citation_ratio: null` parses as `None`
       - Use `respx` for mocking HTTP calls (already in dev dependencies)
       - Use `pytest.mark.asyncio(strict=True)` for async tests (asyncio_mode is "strict" in pyproject.toml)

    3. Update `src/aegis/sources/__init__.py` to add `IciteClient` and `IciteRecord` exports.

    ## Files to create
    - `src/aegis/sources/icite.py`
    - `src/aegis/sources/icite_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add icite exports

    ## Code patterns to follow
    - Follow exact patterns from `src/aegis/sources/pubmed.py` and `src/aegis/sources/reporter.py`:
      - `from __future__ import annotations`
      - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
      - `RetryPolicy` integration
      - `AsyncIterator` return type for batch methods
      - `httpx.AsyncClient` with timeout
      - Logger at module level
    - Test patterns from `src/aegis/sources/pubmed_test.py`:
      - `respx` for HTTP mocking
      - `@pytest.mark.asyncio(strict=True)` decorator

    ## Acceptance criteria
    - `src/aegis/sources/icite.py` exists and exports `IciteClient` and `IciteRecord`
    - `IciteRecord` has fields: `pmid`, `relative_citation_ratio`, `citation_count`, `is_research_article`
    - Tests pass: `cd /Users/anvith/aegis && uv run pytest src/aegis/sources/icite_test.py -v`
    - mypy passes: `cd /Users/anvith/aegis && uv run mypy src/aegis/sources/icite.py`
    - ruff passes: `cd /Users/anvith/aegis && uv run ruff check src/aegis/sources/icite.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/icite_test.py -v && uv run mypy src/aegis/sources/icite.py && uv run ruff check src/aegis/sources/icite.py
    ```

### 3. F1 — RCR Aggregation (Field-Normalized Impact)

- **Task ID**: f1-rcr
- **Role**: builder
- **Depends On**: icite-client
- **Assigned To**: builder-1
- **Description**: |
    Implement the F1 sub-score: aggregate iCite Relative Citation Ratio across each candidate's PubMed publications, weighted by author position, and produce percentile rank within the specialty cohort.

    ## What to do

    1. Create `src/aegis/scoring/f1_rcr.py`:

       ```python
       """F1 sub-score: RCR aggregation (field-normalized citation impact)."""

       from __future__ import annotations

       import math
       from dataclasses import dataclass

       from pydantic import BaseModel, ConfigDict


       class F1Score(BaseModel):
           """Result of F1 computation for a single candidate."""

           model_config = ConfigDict(frozen=True)

           mean_rcr_log: float
           top_rcr_log: float  # 90th percentile RCR in log space
           percentile: float   # percentile within cohort, 0.0-1.0
           low_confidence: bool  # True if <10 RCR-eligible papers
           eligible_paper_count: int


       # Author-position weights per program overview
       AUTHOR_WEIGHT_LAST: float = 1.0
       AUTHOR_WEIGHT_CORRESPONDING: float = 1.0
       AUTHOR_WEIGHT_FIRST: float = 0.7
       AUTHOR_WEIGHT_MIDDLE: float = 0.3

       # Article types to exclude from RCR aggregation
       _EXCLUDED_ARTICLE_TYPES: frozenset[str] = frozenset({
           "Editorial",
           "Letter",
           "Published Erratum",
           "Corrected and Republished Article",
           "Comment",
       })

       _LOW_CONFIDENCE_THRESHOLD: int = 10


       @dataclass
       class PaperRCR:
           """Intermediate: a single paper's RCR with author-position weight."""
           pmid: str
           rcr: float
           author_weight: float
           article_type: str | None


       class F1Computer:
           """Compute F1 sub-score (RCR aggregation) for candidates."""

           def score_raw(
               self,
               paper_rcrs: list[PaperRCR],
           ) -> tuple[float, float, bool, int]:
               """Compute raw F1 values (before percentile).

               Returns (mean_rcr_log, top_rcr_log, low_confidence, eligible_count).
               """
               # Filter out excluded article types
               eligible = [
                   p for p in paper_rcrs
                   if p.article_type not in _EXCLUDED_ARTICLE_TYPES
                   and p.rcr > 0
               ]

               if not eligible:
                   return (0.0, 0.0, True, 0)

               low_confidence = len(eligible) < _LOW_CONFIDENCE_THRESHOLD

               # Weighted RCR values in log space
               weighted_log_rcrs: list[float] = []
               for p in eligible:
                   log_rcr = math.log(p.rcr + 1e-9)  # avoid log(0)
                   weighted_log_rcrs.append(log_rcr * p.author_weight)

               mean_rcr_log = sum(weighted_log_rcrs) / len(weighted_log_rcrs)

               # 90th percentile: sort and pick index
               sorted_rcrs = sorted(weighted_log_rcrs)
               idx_90 = int(len(sorted_rcrs) * 0.9)
               idx_90 = min(idx_90, len(sorted_rcrs) - 1)
               top_rcr_log = sorted_rcrs[idx_90]

               return (mean_rcr_log, top_rcr_log, low_confidence, len(eligible))

           def compute_percentiles(
               self,
               raw_scores: list[tuple[str, float, float, bool, int]],
           ) -> dict[str, F1Score]:
               """Given list of (uuid, mean_rcr_log, top_rcr_log, low_confidence, count),
               compute percentile rank for each candidate.

               Percentile is based on the composite: 0.6 * mean_rcr_log + 0.4 * top_rcr_log.
               """
               if not raw_scores:
                   return {}

               # Compute composite for each candidate
               composites: list[tuple[str, float, float, float, bool, int]] = []
               for uuid, mean_log, top_log, low_conf, count in raw_scores:
                   composite = 0.6 * mean_log + 0.4 * top_log
                   composites.append((uuid, mean_log, top_log, composite, low_conf, count))

               # Sort by composite to assign percentiles
               composites.sort(key=lambda x: x[3])

               n = len(composites)
               results: dict[str, F1Score] = {}
               for rank_idx, (uuid, mean_log, top_log, _comp, low_conf, count) in enumerate(composites):
                   percentile = (rank_idx + 0.5) / n  # midpoint percentile
                   results[uuid] = F1Score(
                       mean_rcr_log=round(mean_log, 6),
                       top_rcr_log=round(top_log, 6),
                       percentile=round(percentile, 6),
                       low_confidence=low_conf,
                       eligible_paper_count=count,
                   )

               return results
       ```

    2. Create `src/aegis/scoring/f1_rcr_test.py` with tests:

       - `test_score_raw_basic`: 15 papers with varying RCR and positions, verify mean and top are computed correctly
       - `test_score_raw_excludes_editorials`: Include an editorial, verify it's excluded
       - `test_score_raw_low_confidence`: <10 eligible papers sets low_confidence=True
       - `test_score_raw_empty`: No papers returns (0.0, 0.0, True, 0)
       - `test_compute_percentiles_uniform`: 100 candidates with uniformly distributed RCR, verify percentiles span [0, 1]
       - `test_compute_percentiles_single`: One candidate gets percentile 0.5
       - All tests use `from aegis.scoring.f1_rcr import F1Computer, F1Score, PaperRCR, AUTHOR_WEIGHT_LAST, AUTHOR_WEIGHT_FIRST, AUTHOR_WEIGHT_MIDDLE`

    ## Files to create
    - `src/aegis/scoring/f1_rcr.py`
    - `src/aegis/scoring/f1_rcr_test.py`

    ## Code patterns to follow
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for score output
    - `from __future__ import annotations` at top
    - Type hints on all functions (mypy strict)
    - Use `math.log` for log-space computation
    - Percentile via rank-order (midpoint method)

    ## Acceptance criteria
    - `F1Computer` class exists with `score_raw` and `compute_percentiles` methods
    - `F1Score` has fields: `mean_rcr_log`, `top_rcr_log`, `percentile`, `low_confidence`, `eligible_paper_count`
    - Editorials/letters/corrections are excluded from RCR aggregation
    - Author-position weighting: last=1.0, first=0.7, middle=0.3
    - <10 eligible papers triggers `low_confidence=True`
    - Tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f1_rcr_test.py -v && uv run mypy src/aegis/scoring/f1_rcr.py && uv run ruff check src/aegis/scoring/f1_rcr.py
    ```

### 4. F2 — NIH Funding & Resource-Getting

- **Task ID**: f2-funding
- **Role**: builder
- **Depends On**: scaffold-scoring
- **Assigned To**: builder-1
- **Description**: |
    Implement the F2 sub-score: aggregate NIH grants per candidate from RePORTER data, weighted by PI role, grant type, and activity status.

    ## What to do

    1. Create `src/aegis/scoring/f2_funding.py`:

       The module must contain:

       - `F2Score(BaseModel)` with fields:
         - `total_cost_log: float` — log of total funding
         - `active_r01_equivalent: float` — count of active R01-equivalent grants (fractional for multi-PI)
         - `percentile: float` — percentile within cohort [0, 1]
         - `grant_count: int` — total grants considered

       - Constants for role weights:
         - Contact PI = 1.0
         - Multi-PI / Co-PI = 0.7
         - Co-I = 0.3

       - Constants for grant type weights:
         - R01, U01, P01 = 1.0
         - K-series (K01, K08, K23, K99, etc.) = 0.6
         - R03, R21 = 0.4
         - Others = 0.2

       - Active grants weighted 2x vs expired (active_multiplier = 2.0)

       - `GrantInput` dataclass with fields: `project_number: str`, `activity_code: str`, `pi_role: str`, `total_cost: int | None`, `is_active: bool`, `pi_count: int` (number of PIs on the grant, for fractional counting)

       - `F2Computer` class with:
         - `score_raw(grants: list[GrantInput]) -> tuple[float, float, int]` returning (total_cost_log, active_r01_equiv, grant_count)
         - `compute_percentiles(raw_scores: list[tuple[str, float, float, int]]) -> dict[str, F2Score]`

       - Grant type classification: parse activity_code prefix to determine grant type weight. If activity_code starts with "R01", "U01", "P01" -> 1.0. Starts with "K" -> 0.6. Starts with "R03" or "R21" -> 0.4. Else -> 0.2.

       - Active R01 equivalent: sum over grants where activity_code matches R01/U01/P01 AND is_active, each counted as (1.0 / pi_count) * role_weight.

       - Fractional PI: when `pi_count > 1`, each PI's share is `1.0 / pi_count`.

    2. Create `src/aegis/scoring/f2_funding_test.py` with tests:
       - `test_score_raw_basic`: 5 grants with mixed types and roles
       - `test_score_raw_active_vs_expired`: Active R01 counts toward active_r01_equivalent, expired does not
       - `test_score_raw_multi_pi_fractional`: Multi-PI grant counted fractionally
       - `test_score_raw_no_grants`: Returns (0.0, 0.0, 0)
       - `test_compute_percentiles_distribution`: 50 candidates, verify percentiles are uniformly distributed
       - `test_fractional_pi_shares_sum_to_one`: 3 PIs on one grant, each gets 1/3 share

    ## Files to create
    - `src/aegis/scoring/f2_funding.py`
    - `src/aegis/scoring/f2_funding_test.py`

    ## Code patterns to follow
    - Same patterns as f1_rcr.py: Pydantic BaseModel, frozen, future annotations, type hints
    - Use `math.log` for log-space computation of total_cost
    - Percentile via rank-order (midpoint method), same as F1

    ## Acceptance criteria
    - `F2Computer.score_raw` and `F2Computer.compute_percentiles` work correctly
    - `F2Score` has fields: `total_cost_log`, `active_r01_equivalent`, `percentile`, `grant_count`
    - Multi-PI grants count fractionally
    - Active grants weighted 2x
    - Tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f2_funding_test.py -v && uv run mypy src/aegis/scoring/f2_funding.py && uv run ruff check src/aegis/scoring/f2_funding.py
    ```

### 5. Apex Rosters Source Client + Editorial Roles Data

- **Task ID**: apex-rosters-client
- **Role**: builder
- **Depends On**: scaffold-scoring
- **Assigned To**: builder-2
- **Description**: |
    Create the apex rosters source client for ingesting public roster data (HHMI, NAS, NAM, NAE, MERIT, Lasker, Hanna Gray Fellows) and the editorial roles data file for F3.

    ## What to do

    1. Create `src/aegis/sources/apex_rosters.py`:

       ```python
       """Apex roster ingestion for elite recognition markers."""

       from __future__ import annotations

       import logging
       from enum import StrEnum

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class ApexRosterType(StrEnum):
           """Types of apex recognition rosters."""
           hhmi_investigator = "hhmi_investigator"
           nas_member = "nas_member"
           nae_member = "nae_member"
           nam_member = "nam_member"
           nih_merit = "nih_merit"
           lasker_laureate = "lasker_laureate"
           hhmi_hanna_gray = "hhmi_hanna_gray"


       class ApexMembership(BaseModel):
           """A single membership record on an apex roster."""

           model_config = ConfigDict(frozen=True)

           roster_type: ApexRosterType
           name: str
           year: int | None
           institution: str | None
           confidence: float  # identity match confidence


       class ApexRosterStore:
           """In-memory store for apex roster memberships.

           Phase 1 uses a static in-memory store loaded from YAML/JSON.
           Phase 3 will add live scraping and DB persistence.
           """

           def __init__(self) -> None:
               self._memberships: list[ApexMembership] = []

           def add(self, membership: ApexMembership) -> None:
               """Add a membership record."""
               self._memberships.append(membership)

           def add_batch(self, memberships: list[ApexMembership]) -> None:
               """Add multiple membership records."""
               self._memberships.extend(memberships)

           def lookup_by_name(
               self,
               name: str,
               institution: str | None = None,
           ) -> list[ApexMembership]:
               """Find memberships matching a name (case-insensitive).

               If institution is provided, prefer matches with matching institution.
               """
               name_lower = name.lower()
               matches = [
                   m for m in self._memberships
                   if m.name.lower() == name_lower
               ]
               if institution and len(matches) > 1:
                   inst_lower = institution.lower()
                   inst_matches = [
                       m for m in matches
                       if m.institution and inst_lower in m.institution.lower()
                   ]
                   if inst_matches:
                       return inst_matches
               return matches

           def list_by_roster(self, roster_type: ApexRosterType) -> list[ApexMembership]:
               """List all memberships for a roster type."""
               return [m for m in self._memberships if m.roster_type == roster_type]

           def count(self) -> int:
               """Total membership records loaded."""
               return len(self._memberships)
       ```

    2. Create `src/aegis/sources/apex_rosters_test.py` with tests:
       - `test_add_and_lookup`: Add 3 members, lookup by name, verify found
       - `test_lookup_case_insensitive`: Lookup with different case still matches
       - `test_lookup_with_institution_disambiguation`: Two people same name, different institutions
       - `test_list_by_roster`: Add members to 2 rosters, verify correct filtering
       - `test_count`: Verify count after batch add

    3. Create `data/aegis/editorial_roles_phase1.yaml`:
       ```yaml
       # Handcrafted editorial roles for major NSCLC journals (Phase 1)
       # Phase 3 will replace with automated journal masthead scraping
       journals:
         - name: "Journal of Clinical Oncology"
           nlm_id: "8309333"
           roles:
             - title: "Editor-in-Chief"
               weight: 1.0
             - title: "Deputy Editor"
               weight: 0.8
             - title: "Associate Editor"
               weight: 0.6
         - name: "Journal of Thoracic Oncology"
           nlm_id: "101274235"
           roles:
             - title: "Editor-in-Chief"
               weight: 1.0
             - title: "Deputy Editor"
               weight: 0.8
             - title: "Associate Editor"
               weight: 0.6
         - name: "The Lancet Oncology"
           nlm_id: "100957246"
           roles:
             - title: "Editor"
               weight: 1.0
             - title: "Senior Editor"
               weight: 0.8
         - name: "Clinical Cancer Research"
           nlm_id: "9502500"
           roles:
             - title: "Editor-in-Chief"
               weight: 1.0
             - title: "Associate Editor"
               weight: 0.6
         - name: "Annals of Oncology"
           nlm_id: "9007735"
           roles:
             - title: "Editor-in-Chief"
               weight: 1.0
             - title: "Associate Editor"
               weight: 0.6
       ```

    4. Update `src/aegis/sources/__init__.py` to add `ApexRosterStore`, `ApexMembership`, `ApexRosterType` exports.

    ## Files to create
    - `src/aegis/sources/apex_rosters.py`
    - `src/aegis/sources/apex_rosters_test.py`
    - `data/aegis/editorial_roles_phase1.yaml`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add apex roster exports

    ## Code patterns to follow
    - Same patterns as other source clients: `from __future__ import annotations`, Pydantic BaseModel, frozen, logging
    - StrEnum for roster types (same as `StrongKeyType` in schema.py)
    - YAML for data files (same as weight config)

    ## Acceptance criteria
    - `ApexRosterStore` with `add`, `add_batch`, `lookup_by_name`, `list_by_roster`, `count`
    - `ApexMembership` with fields: `roster_type`, `name`, `year`, `institution`, `confidence`
    - `data/aegis/editorial_roles_phase1.yaml` exists and is valid YAML
    - Tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/apex_rosters_test.py -v && uv run mypy src/aegis/sources/apex_rosters.py && uv run ruff check src/aegis/sources/apex_rosters.py && python -c "import yaml; yaml.safe_load(open('data/aegis/editorial_roles_phase1.yaml')); print('Editorial roles YAML OK')"
    ```

### 6. F3 — PI / Leadership

- **Task ID**: f3-leadership
- **Role**: builder
- **Depends On**: apex-rosters-client
- **Assigned To**: builder-2
- **Description**: |
    Implement the F3 sub-score: leadership signals including last-author rate, trial-PI count, corresponding-author rate, and editorial roles.

    ## What to do

    1. Create `src/aegis/scoring/f3_leadership.py`:

       The module must contain:

       - `F3Score(BaseModel)` with fields:
         - `last_author_rate: float` — fraction of papers where candidate is last author (over eligible papers only)
         - `trial_pi_count: float` — weighted count of clinical trials where candidate is PI (Study Chair at 0.7 weight)
         - `corresponding_author_rate: float` — fraction of papers where candidate is corresponding author
         - `editorial_role_flag: bool` — True if candidate holds editorial role at a major journal
         - `percentile: float` — percentile within cohort [0, 1]

       - `LeadershipInput` dataclass with:
         - `total_papers: int`
         - `last_author_papers: int` (papers where candidate is last author, excluding ambiguous middle-author papers)
         - `corresponding_author_papers: int`
         - `trial_pi_roles: int` (CT.gov PI roles)
         - `trial_chair_roles: int` (CT.gov Study Chair roles)
         - `has_editorial_role: bool`

       - `F3Computer` class with:
         - `score_raw(input: LeadershipInput) -> tuple[float, float, float, bool]` returning (last_author_rate, trial_pi_count, corresponding_author_rate, editorial_role_flag)
         - `compute_percentiles(raw_scores: list[tuple[str, float, float, float, bool]]) -> dict[str, F3Score]`

       - Composite for percentile ranking: `0.35 * last_author_rate + 0.30 * normalized_trial_pi + 0.25 * corresponding_author_rate + 0.10 * editorial_flag`
         - `normalized_trial_pi` = `min(trial_pi_count / 5.0, 1.0)` (cap at 5 for normalization)
         - `editorial_flag` = 1.0 if True, 0.0 if False

       - Study Chair weight: 0.7 vs full PI = 1.0
       - `trial_pi_count = trial_pi_roles * 1.0 + trial_chair_roles * 0.7`

    2. Create `src/aegis/scoring/f3_leadership_test.py` with tests:
       - `test_score_raw_established_pi`: High last-author rate, multiple trial PI roles
       - `test_score_raw_early_career`: Low last-author rate, no trial roles
       - `test_score_raw_study_chair_weighted`: Study Chair contributes at 0.7 weight
       - `test_score_raw_no_papers`: zero papers -> 0 rates
       - `test_editorial_role_flag`: True when candidate has editorial role
       - `test_compute_percentiles`: 30 candidates, verify percentile distribution

    ## Files to create
    - `src/aegis/scoring/f3_leadership.py`
    - `src/aegis/scoring/f3_leadership_test.py`

    ## Code patterns to follow
    - Same as f1_rcr.py: Pydantic, frozen, annotations, type hints, rank-order percentile

    ## Acceptance criteria
    - `F3Computer` with `score_raw` and `compute_percentiles`
    - `F3Score` with all 5 fields
    - Study Chair weighted at 0.7
    - Last-author rate excludes ambiguous middle-author papers (by using only `last_author_papers` / `total_papers`)
    - Tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f3_leadership_test.py -v && uv run mypy src/aegis/scoring/f3_leadership.py && uv run ruff check src/aegis/scoring/f3_leadership.py
    ```

### 7. F4 — Apex-Tier Flag

- **Task ID**: f4-apex
- **Role**: builder
- **Depends On**: apex-rosters-client
- **Assigned To**: builder-2
- **Description**: |
    Implement the F4 sub-score: apex-tier recognition using public rosters (HHMI, NAS, NAE, NAM, MERIT, Lasker, Hanna Gray). Small monotonic mapping from membership count to [0, 1]. Weight capped at 0.05.

    ## What to do

    1. Create `src/aegis/scoring/f4_apex.py`:

       The module must contain:

       - `F4Score(BaseModel)` with fields:
         - `memberships: list[str]` — list of roster type names for matched memberships
         - `membership_count: int`
         - `score: float` — monotonic mapping from count to [0, 1]
         - `percentile: float` — percentile within cohort [0, 1]

       - Monotonic mapping function (count -> score):
         - 0 memberships -> 0.0
         - 1 membership -> 0.4
         - 2 memberships -> 0.65
         - 3 memberships -> 0.8
         - 4 memberships -> 0.9
         - 5+ memberships -> 1.0
         This is a diminishing-returns curve: `min(1.0, 0.4 * count ** 0.55)` approximation,
         or use a simple lookup table.

       - `F4Computer` class with:
         - `score_from_memberships(memberships: list[str]) -> tuple[float, int]` returning (raw_score, count)
         - `compute_percentiles(raw_scores: list[tuple[str, float, int]]) -> dict[str, F4Score]` — note that F4 percentile is computed same as other F-scores, but the weight in Q(c) is capped at 0.05 (enforced by the weight config, not by this module)

       - The module does NOT enforce the 0.05 weight cap — that's the composition layer's job via the weight config. This module just computes the raw F4 score.

    2. Create `src/aegis/scoring/f4_apex_test.py` with tests:
       - `test_score_zero_memberships`: Returns score 0.0
       - `test_score_one_membership`: Returns score ~0.4
       - `test_score_multiple_memberships`: 3 memberships -> score ~0.8
       - `test_score_cap_at_one`: 7 memberships still returns <= 1.0
       - `test_monotonic`: Scores are non-decreasing as membership count increases (test 0 through 7)
       - `test_compute_percentiles`: 20 candidates, verify percentile distribution

    ## Files to create
    - `src/aegis/scoring/f4_apex.py`
    - `src/aegis/scoring/f4_apex_test.py`

    ## Code patterns to follow
    - Same as other F-score modules

    ## Acceptance criteria
    - `F4Computer` with `score_from_memberships` and `compute_percentiles`
    - `F4Score` with fields: `memberships`, `membership_count`, `score`, `percentile`
    - Mapping is monotonically non-decreasing
    - Score capped at 1.0
    - Tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f4_apex_test.py -v && uv run mypy src/aegis/scoring/f4_apex.py && uv run ruff check src/aegis/scoring/f4_apex.py
    ```

### 8. Drugs@FDA + NCCN + Academic Tree Source Clients

- **Task ID**: translational-sources
- **Role**: builder
- **Depends On**: scaffold-scoring
- **Assigned To**: builder-3
- **Description**: |
    Create the source clients needed by F5 (Translational) and F6 (Lineage): Drugs@FDA, NCCN guideline panels, and Academic Family Tree.

    ## What to do

    1. Create `src/aegis/sources/drugs_fda.py`:

       ```python
       """Drugs@FDA bulk data client for FDA submission cross-referencing."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class FDASubmission(BaseModel):
           """A drug submission record from Drugs@FDA."""

           model_config = ConfigDict(frozen=True)

           application_number: str
           sponsor_name: str
           drug_name: str
           active_ingredient: str | None
           submission_type: str | None
           approval_date: str | None  # ISO date string
           application_type: str | None  # NDA, BLA, ANDA


       class DrugsFDAStore:
           """In-memory store for FDA submission records.

           Phase 1 uses bulk download data loaded into memory.
           Phase 3 will add the openFDA API integration.
           """

           def __init__(self) -> None:
               self._submissions: list[FDASubmission] = []

           def add_batch(self, submissions: list[FDASubmission]) -> None:
               self._submissions.extend(submissions)

           def lookup_by_sponsor(self, sponsor_name: str) -> list[FDASubmission]:
               """Find submissions by sponsor name (case-insensitive substring)."""
               sponsor_lower = sponsor_name.lower()
               return [
                   s for s in self._submissions
                   if sponsor_lower in s.sponsor_name.lower()
               ]

           def count(self) -> int:
               return len(self._submissions)
       ```

    2. Create `src/aegis/sources/nccn.py`:

       ```python
       """NCCN guideline panel roster ingestion (Phase 1: NSCLC panel only)."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class NCCNPanelMember(BaseModel):
           """A member of an NCCN guideline panel."""

           model_config = ConfigDict(frozen=True)

           name: str
           institution: str | None
           panel_name: str
           role: str | None  # "Chair", "Vice Chair", "Member"
           guideline_version: str | None


       class NCCNPanelStore:
           """In-memory store for NCCN guideline panel rosters.

           Phase 1: manually curated NSCLC panel only.
           Phase 3: automated PDF extraction across all panels.
           """

           def __init__(self) -> None:
               self._members: list[NCCNPanelMember] = []

           def add_batch(self, members: list[NCCNPanelMember]) -> None:
               self._members.extend(members)

           def is_panel_member(self, name: str, panel_name: str | None = None) -> bool:
               """Check if a name appears on any (or a specific) panel."""
               name_lower = name.lower()
               for m in self._members:
                   if m.name.lower() == name_lower:
                       if panel_name is None or m.panel_name.lower() == panel_name.lower():
                           return True
               return False

           def lookup_by_name(self, name: str) -> list[NCCNPanelMember]:
               name_lower = name.lower()
               return [m for m in self._members if m.name.lower() == name_lower]

           def list_panel(self, panel_name: str) -> list[NCCNPanelMember]:
               panel_lower = panel_name.lower()
               return [m for m in self._members if m.panel_name.lower() == panel_lower]

           def count(self) -> int:
               return len(self._members)
       ```

    3. Create `src/aegis/sources/academic_tree.py`:

       ```python
       """Academic Family Tree (academictree.org) data client for mentorship lineage."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class MentorEdge(BaseModel):
           """A mentor-mentee relationship edge."""

           model_config = ConfigDict(frozen=True)

           mentor_name: str
           mentee_name: str
           mentor_institution: str | None
           mentee_institution: str | None
           relationship_type: str | None  # "PhD advisor", "Postdoc mentor", etc.
           year: int | None
           confidence: float  # linkage confidence to cohort candidate


       class AcademicTreeStore:
           """In-memory store for academic lineage data.

           Coverage is ~30% of biomed researchers.
           Phase 1 loads from bulk export; Phase 3 adds live API.
           """

           def __init__(self) -> None:
               self._edges: list[MentorEdge] = []

           def add_batch(self, edges: list[MentorEdge]) -> None:
               self._edges.extend(edges)

           def get_mentees(self, mentor_name: str) -> list[MentorEdge]:
               """Get all mentees for a given mentor (case-insensitive)."""
               name_lower = mentor_name.lower()
               return [e for e in self._edges if e.mentor_name.lower() == name_lower]

           def get_mentors(self, mentee_name: str) -> list[MentorEdge]:
               """Get all mentors for a given mentee (case-insensitive)."""
               name_lower = mentee_name.lower()
               return [e for e in self._edges if e.mentee_name.lower() == name_lower]

           def get_lineage_depth(self, name: str, max_depth: int = 5) -> int:
               """BFS up the mentor chain to find lineage depth."""
               visited: set[str] = set()
               queue: list[tuple[str, int]] = [(name.lower(), 0)]
               max_found = 0

               while queue:
                   current, depth = queue.pop(0)
                   if current in visited:
                       continue
                   visited.add(current)
                   max_found = max(max_found, depth)

                   if depth >= max_depth:
                       continue

                   for edge in self._edges:
                       if edge.mentee_name.lower() == current:
                           queue.append((edge.mentor_name.lower(), depth + 1))

               return max_found

           def count(self) -> int:
               return len(self._edges)
       ```

    4. Create test files for each:

       `src/aegis/sources/drugs_fda_test.py`:
       - `test_add_and_lookup_by_sponsor`: Add submissions, lookup by sponsor substring
       - `test_lookup_case_insensitive`: Lookup with different case

       `src/aegis/sources/nccn_test.py`:
       - `test_is_panel_member`: Add members, verify lookup
       - `test_is_panel_member_specific_panel`: Filter by panel name
       - `test_list_panel`: List all members of a specific panel

       `src/aegis/sources/academic_tree_test.py`:
       - `test_get_mentees`: Add edges, query mentees of a mentor
       - `test_get_lineage_depth`: Build a 3-level chain, verify depth
       - `test_lineage_depth_cycle_safe`: Add a cycle, verify it doesn't infinite-loop

    5. Update `src/aegis/sources/__init__.py` to add exports for all three new stores.

    ## Files to create
    - `src/aegis/sources/drugs_fda.py`
    - `src/aegis/sources/drugs_fda_test.py`
    - `src/aegis/sources/nccn.py`
    - `src/aegis/sources/nccn_test.py`
    - `src/aegis/sources/academic_tree.py`
    - `src/aegis/sources/academic_tree_test.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add new exports

    ## Code patterns to follow
    - Same patterns as `apex_rosters.py`: Pydantic, frozen, annotations, logging
    - In-memory stores for Phase 1, with clear Phase 3 migration path documented in docstrings

    ## Acceptance criteria
    - All three store classes exist with documented methods
    - All tests pass
    - mypy passes on all three modules
    - ruff passes on all three modules

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/drugs_fda_test.py src/aegis/sources/nccn_test.py src/aegis/sources/academic_tree_test.py -v && uv run mypy src/aegis/sources/drugs_fda.py src/aegis/sources/nccn.py src/aegis/sources/academic_tree.py && uv run ruff check src/aegis/sources/drugs_fda.py src/aegis/sources/nccn.py src/aegis/sources/academic_tree.py
    ```

### 9. F5 — Translational Impact (Phase 1 Subset)

- **Task ID**: f5-translational
- **Role**: builder
- **Depends On**: translational-sources
- **Assigned To**: builder-3
- **Description**: |
    Implement the F5 sub-score: translational impact using FDA submissions, Phase 2+ drugs from CT.gov, and NCCN guideline panel membership. Patents deferred to Phase 2.

    ## What to do

    1. Create `src/aegis/scoring/f5_translational.py`:

       The module must contain:

       - `F5Score(BaseModel)` with fields:
         - `fda_submissions: int` — count of linked FDA submissions
         - `phase2plus_drugs: int` — count of Phase 2+ trials where candidate is PI/sponsor-linked
         - `nccn_panel_member: bool`
         - `coverage_caveat: str` — documents that this is Phase 1 partial coverage (no patents)
         - `percentile: float` — percentile within cohort [0, 1]

       - `TranslationalInput` dataclass with:
         - `fda_submission_count: int`
         - `phase2plus_trial_count: int`
         - `is_nccn_panel_member: bool`

       - `F5Computer` class with:
         - `score_raw(input: TranslationalInput) -> tuple[float, int, int, bool, str]` returning (composite_score, fda_count, phase2_count, nccn_flag, coverage_caveat)
         - `compute_percentiles(raw_scores: list[tuple[str, float, int, int, bool, str]]) -> dict[str, F5Score]`

       - Composite scoring:
         - `fda_component = min(fda_submission_count / 3.0, 1.0)` (cap at 3 submissions)
         - `trial_component = min(phase2plus_trial_count / 5.0, 1.0)` (cap at 5 trials)
         - `nccn_component = 1.0 if is_nccn_panel_member else 0.0`
         - `composite = 0.35 * fda_component + 0.40 * trial_component + 0.25 * nccn_component`

       - `coverage_caveat` is always: `"Phase 1: patents excluded; Phase 2 will include patent linkage"`

    2. Create `src/aegis/scoring/f5_translational_test.py` with tests:
       - `test_score_raw_full_profile`: FDA + trials + NCCN all present
       - `test_score_raw_nccn_only`: Only NCCN panel membership
       - `test_score_raw_no_signals`: All zeros -> composite 0.0
       - `test_coverage_caveat_always_present`: Verify string is always set
       - `test_compute_percentiles`: 25 candidates, verify distribution
       - `test_component_capping`: FDA > 3 still caps component at 1.0

    ## Files to create
    - `src/aegis/scoring/f5_translational.py`
    - `src/aegis/scoring/f5_translational_test.py`

    ## Code patterns to follow
    - Same as other F-score modules

    ## Acceptance criteria
    - `F5Computer` with `score_raw` and `compute_percentiles`
    - `F5Score` with all 5 fields including `coverage_caveat`
    - Coverage caveat always set
    - Tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f5_translational_test.py -v && uv run mypy src/aegis/scoring/f5_translational.py && uv run ruff check src/aegis/scoring/f5_translational.py
    ```

### 10. F6 — Mentorship / Lineage

- **Task ID**: f6-lineage
- **Role**: builder
- **Depends On**: translational-sources
- **Assigned To**: builder-3
- **Description**: |
    Implement the F6 sub-score: mentorship lineage using Academic Family Tree data. Track traceable trainees and trainees who became R01 PIs.

    ## What to do

    1. Create `src/aegis/scoring/f6_lineage.py`:

       The module must contain:

       - `F6Score(BaseModel)` with fields:
         - `traceable_trainee_count: int`
         - `r01_trainee_count: int` — trainees in tree who later won R01s
         - `data_confidence: float` — based on AFT coverage (0.0-1.0)
         - `percentile: float` — percentile within cohort [0, 1]

       - `LineageInput` dataclass with:
         - `traceable_trainee_count: int`
         - `r01_trainee_count: int`
         - `aft_link_confidence: float` — linkage confidence from AFT to cohort candidate

       - `F6Computer` class with:
         - `score_raw(input: LineageInput) -> tuple[float, int, int, float]` returning (composite_score, traceable_count, r01_count, data_confidence)
         - `compute_percentiles(raw_scores: list[tuple[str, float, int, int, float]]) -> dict[str, F6Score]`

       - Composite scoring:
         - `trainee_component = min(traceable_trainee_count / 10.0, 1.0)` (cap at 10)
         - `r01_component = min(r01_trainee_count / 5.0, 1.0)` (cap at 5)
         - `raw_composite = 0.4 * trainee_component + 0.6 * r01_component`
         - `composite = raw_composite * aft_link_confidence` (downweight when data is sparse)
         - `data_confidence = aft_link_confidence`

       - F6 is deliberately downweighted when underlying AFT data is sparse. The `data_confidence` field propagates to `Q(c)` consumers.

    2. Create `src/aegis/scoring/f6_lineage_test.py` with tests:
       - `test_score_raw_prolific_mentor`: 8 trainees, 4 R01 PIs, high confidence
       - `test_score_raw_no_data`: 0 trainees, low confidence
       - `test_score_raw_low_confidence_downweights`: Same trainees but low confidence -> lower composite
       - `test_compute_percentiles_long_tail`: Most candidates have 0-2 trainees (long-tail distribution)
       - `test_r01_component_capping`: r01_trainee_count > 5 caps component at 1.0

    ## Files to create
    - `src/aegis/scoring/f6_lineage.py`
    - `src/aegis/scoring/f6_lineage_test.py`

    ## Code patterns to follow
    - Same as other F-score modules

    ## Acceptance criteria
    - `F6Computer` with `score_raw` and `compute_percentiles`
    - `F6Score` with all 4 fields
    - Data confidence downweights the composite score
    - Tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f6_lineage_test.py -v && uv run mypy src/aegis/scoring/f6_lineage.py && uv run ruff check src/aegis/scoring/f6_lineage.py
    ```

### 11. Q(c) Geometric-Mean Composition + Percentile Calibration

- **Task ID**: quality-prior
- **Role**: builder
- **Depends On**: f1-rcr, f2-funding, f3-leadership, f4-apex, f5-translational, f6-lineage
- **Assigned To**: builder-1
- **Description**: |
    Wire the full quality prior `Q(c) = prod(F_i(c)^{w_i})` using the translational weight vector from the YAML config. Convert to percentile within specialty cohort.

    ## What to do

    1. Create `src/aegis/scoring/quality_prior.py`:

       ```python
       """Quality prior Q(c): geometric-mean composition of F1-F6 sub-scores."""

       from __future__ import annotations

       import math
       from pathlib import Path
       from typing import Any

       import yaml
       from pydantic import BaseModel, ConfigDict

       _DEFAULT_CONFIG_PATH = Path("config/aegis/weights/translational_v1.yaml")


       class WeightVector(BaseModel):
           """Versioned weight configuration for quality prior composition."""

           model_config = ConfigDict(frozen=True)

           version: int
           specialty: str
           weights: dict[str, float]  # f1_rcr -> 0.35, etc.
           exponents: dict[str, float]  # alpha, beta, gamma
           exponent_bounds: dict[str, list[float]]  # alpha -> [0.3, 1.2]


       class QualityScore(BaseModel):
           """Result of Q(c) computation for a single candidate."""

           model_config = ConfigDict(frozen=True)

           raw_score: float  # raw geometric mean (internal)
           percentile: float  # percentile within cohort [0, 1]
           component_percentiles: dict[str, float]  # f1_rcr -> 0.85, etc.
           weight_version: int


       def load_weight_vector(config_path: Path | None = None) -> WeightVector:
           """Load weight vector from YAML config file."""
           path = config_path or _DEFAULT_CONFIG_PATH
           with open(path) as f:
               data: dict[str, Any] = yaml.safe_load(f)
           return WeightVector(
               version=data["version"],
               specialty=data["specialty"],
               weights=data["weights"],
               exponents=data["exponents"],
               exponent_bounds=data.get("exponent_bounds", {}),
           )


       class QualityPrior:
           """Compute Q(c) = prod(F_i(c)^{w_i}) with percentile calibration."""

           def __init__(self, weight_vector: WeightVector) -> None:
               self._weights = weight_vector

           @property
           def weight_vector(self) -> WeightVector:
               return self._weights

           def compute_raw(
               self,
               component_percentiles: dict[str, float],
           ) -> float:
               """Compute raw Q(c) from component percentiles.

               Q(c) = prod(F_i(c)^{w_i}) where F_i(c) is the percentile [0,1].
               Uses geometric mean in log space to avoid numerical issues.
               """
               log_sum = 0.0
               total_weight = 0.0

               for family, weight in self._weights.weights.items():
                   percentile = component_percentiles.get(family, 0.0)
                   # Clamp percentile to avoid log(0)
                   percentile = max(percentile, 1e-6)
                   log_sum += weight * math.log(percentile)
                   total_weight += weight

               if total_weight == 0:
                   return 0.0

               # Geometric mean: exp(sum(w_i * log(p_i)))
               return math.exp(log_sum)

           def compute_percentiles(
               self,
               candidates: list[tuple[str, dict[str, float]]],
           ) -> dict[str, QualityScore]:
               """Compute Q(c) percentile for a set of candidates.

               Input: list of (candidate_uuid, {family: percentile})
               Output: dict mapping uuid -> QualityScore
               """
               if not candidates:
                   return {}

               # Compute raw Q(c) for each candidate
               raw_scores: list[tuple[str, float, dict[str, float]]] = []
               for uuid, components in candidates:
                   raw = self.compute_raw(components)
                   raw_scores.append((uuid, raw, components))

               # Sort by raw score for percentile assignment
               raw_scores.sort(key=lambda x: x[1])

               n = len(raw_scores)
               results: dict[str, QualityScore] = {}
               for rank_idx, (uuid, raw, components) in enumerate(raw_scores):
                   percentile = (rank_idx + 0.5) / n
                   results[uuid] = QualityScore(
                       raw_score=round(raw, 8),
                       percentile=round(percentile, 6),
                       component_percentiles=components,
                       weight_version=self._weights.version,
                   )

               return results
       ```

    2. Create `src/aegis/scoring/quality_prior_test.py` with tests:

       - `test_load_weight_vector`: Load from YAML, verify weights sum to 1.0
       - `test_compute_raw_basic`: Known component percentiles -> expected Q(c) value
       - `test_compute_raw_all_ones`: All percentiles = 1.0 -> Q(c) = 1.0
       - `test_compute_raw_all_zeros`: All percentiles near 0 -> Q(c) near 0
       - `test_percentile_distribution_uniform`: 100 candidates with uniformly random components -> Q(c) percentiles span [0, 1] approximately uniformly
       - `test_reweight_invariance`: Scaling all weights by a constant does not change percentile output (geometric-mean property). Verify with scale factors 0.5 and 2.0.
       - `test_geometric_mean_punishes_spiky`: A candidate with one high and one low component scores lower than a balanced candidate (desired property per program overview)
       - `test_weight_version_propagated`: QualityScore.weight_version matches the loaded config version

       For `test_load_weight_vector`, use the actual config file at `config/aegis/weights/translational_v1.yaml`.
       For other tests, construct `WeightVector` directly in the test.

    3. Update `src/aegis/scoring/__init__.py` to export key classes:
       ```python
       """Aegis scoring engine — quality prior, topical fit, recency, and ranking."""

       from aegis.scoring.f1_rcr import F1Computer, F1Score
       from aegis.scoring.f2_funding import F2Computer, F2Score
       from aegis.scoring.f3_leadership import F3Computer, F3Score
       from aegis.scoring.f4_apex import F4Computer, F4Score
       from aegis.scoring.f5_translational import F5Computer, F5Score
       from aegis.scoring.f6_lineage import F6Computer, F6Score
       from aegis.scoring.quality_prior import (
           QualityPrior,
           QualityScore,
           WeightVector,
           load_weight_vector,
       )

       __all__ = [
           "F1Computer", "F1Score",
           "F2Computer", "F2Score",
           "F3Computer", "F3Score",
           "F4Computer", "F4Score",
           "F5Computer", "F5Score",
           "F6Computer", "F6Score",
           "QualityPrior", "QualityScore", "WeightVector", "load_weight_vector",
       ]
       ```

    ## Files to create
    - `src/aegis/scoring/quality_prior.py`
    - `src/aegis/scoring/quality_prior_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` — add exports for all scoring classes

    ## Code patterns to follow
    - Pydantic BaseModel with frozen config
    - YAML loading via `pyyaml` (already in dependencies)
    - `math.log` and `math.exp` for log-space computation
    - Rank-order percentile (midpoint method)

    ## Acceptance criteria
    - `QualityPrior.compute_raw` returns geometric mean of component percentiles
    - `QualityPrior.compute_percentiles` returns uniform percentile distribution
    - Reweight invariance test passes (scaling all weights preserves percentile order)
    - Weight version propagated to output
    - YAML config loads successfully
    - All tests pass, mypy passes, ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/quality_prior_test.py -v && uv run mypy src/aegis/scoring/quality_prior.py && uv run ruff check src/aegis/scoring/
    ```

### 12. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: quality-prior
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the Phase 1a scoring foundation.

    ## Validation Commands

    1. Verify scoring package exists and imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.scoring import (
        F1Computer, F1Score,
        F2Computer, F2Score,
        F3Computer, F3Score,
        F4Computer, F4Score,
        F5Computer, F5Score,
        F6Computer, F6Score,
        QualityPrior, QualityScore, WeightVector, load_weight_vector,
    )
    print('All scoring imports OK')
    "
    ```

    2. Verify source clients import:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.icite import IciteClient, IciteRecord
    from aegis.sources.apex_rosters import ApexRosterStore, ApexMembership, ApexRosterType
    from aegis.sources.drugs_fda import DrugsFDAStore, FDASubmission
    from aegis.sources.nccn import NCCNPanelStore, NCCNPanelMember
    from aegis.sources.academic_tree import AcademicTreeStore, MentorEdge
    print('All source client imports OK')
    "
    ```

    3. Verify weight config:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.scoring.quality_prior import load_weight_vector
    wv = load_weight_vector()
    assert abs(sum(wv.weights.values()) - 1.0) < 0.001
    assert wv.version == 1
    assert wv.specialty == 'translational'
    assert len(wv.weights) == 6
    assert len(wv.exponents) == 3
    print(f'Weight vector v{wv.version}: {wv.weights}')
    print(f'Exponents: {wv.exponents}')
    "
    ```

    4. Verify F-score interfaces:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.scoring.f1_rcr import F1Score
    from aegis.scoring.f2_funding import F2Score
    from aegis.scoring.f3_leadership import F3Score
    from aegis.scoring.f4_apex import F4Score
    from aegis.scoring.f5_translational import F5Score
    from aegis.scoring.f6_lineage import F6Score

    # Verify each score type has 'percentile' field
    for cls in [F1Score, F2Score, F3Score, F4Score, F5Score, F6Score]:
        assert 'percentile' in cls.model_fields, f'{cls.__name__} missing percentile'
    print('All F-score types have percentile field')
    "
    ```

    5. Run all scoring tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/ -v
    ```

    6. Run all source client tests (new ones):
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/icite_test.py src/aegis/sources/apex_rosters_test.py src/aegis/sources/drugs_fda_test.py src/aegis/sources/nccn_test.py src/aegis/sources/academic_tree_test.py -v
    ```

    7. Run mypy on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/scoring/ src/aegis/sources/icite.py src/aegis/sources/apex_rosters.py src/aegis/sources/drugs_fda.py src/aegis/sources/nccn.py src/aegis/sources/academic_tree.py
    ```

    8. Run ruff on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/scoring/ src/aegis/sources/icite.py src/aegis/sources/apex_rosters.py src/aegis/sources/drugs_fda.py src/aegis/sources/nccn.py src/aegis/sources/academic_tree.py
    ```

    9. Verify editorial roles data file:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    import yaml
    with open('data/aegis/editorial_roles_phase1.yaml') as f:
        data = yaml.safe_load(f)
    assert 'journals' in data
    assert len(data['journals']) >= 5
    print(f'Editorial roles: {len(data[\"journals\"])} journals loaded')
    "
    ```

    10. Verify no existing tests were broken:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/ tests/ -v --tb=short
    ```

    ## Acceptance Criteria
    - All 6 F-score modules exist and export Computer + Score classes
    - All F-score types have a `percentile` field in [0, 1]
    - QualityPrior composes F-scores via geometric mean
    - Weight config at `config/aegis/weights/translational_v1.yaml` is valid with weights summing to 1.0
    - 5 new source clients exist: icite, apex_rosters, drugs_fda, nccn, academic_tree
    - Editorial roles YAML exists at `data/aegis/editorial_roles_phase1.yaml`
    - All tests pass (new and existing)
    - mypy strict passes on all new modules
    - ruff passes on all new modules

### 13. Update Design Doc — Scoring Domain

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
    specs/aegis-phase1a-scoring-foundation.md

    ## Scope
    Quality prior F1-F6 sub-score architecture, geometric-mean composition pattern,
    versioned weight configuration, new source clients (iCite, apex rosters, Drugs@FDA,
    NCCN, Academic Family Tree), percentile calibration approach.

    ## Prior Decisions to Check
    No existing design doc for scoring domain — this is the initial creation.
    However, check the Phase 0 specs (specs/aegis-phase0a-schema-storage.md through
    specs/aegis-phase0e-observability.md) for any decisions that affect the scoring
    domain (e.g., Candidate schema structure, MeSH index patterns, DuckDB storage patterns).

    ## What to Record
    Read `git diff HEAD~1 HEAD`, then the changed source files, then any existing
    design docs. Create `docs/design/scoring.md` with:
    - Current Design section describing the F1-F6 + Q(c) architecture
    - Interface patterns (FNComputer.score -> FNScore with percentile)
    - Weight configuration schema and versioning approach
    - Source client patterns (in-memory stores for Phase 1, API clients where applicable)
    - Design Decision entries for: geometric-mean composition choice, percentile calibration method,
      author-position weighting scheme, log-space computation approach, component capping strategy
    - Every claim must cite a file:line from the actual code

## Acceptance Criteria

- All 6 F-score modules (F1–F6) exist at `src/aegis/scoring/f{1-6}_*.py` with `Computer` and `Score` classes
- Each `Score` type includes a `percentile` field in [0, 1]
- `QualityPrior` at `src/aegis/scoring/quality_prior.py` composes F-scores via geometric mean with YAML-loaded weights
- `WeightVector` loaded from `config/aegis/weights/translational_v1.yaml` with weights summing to 1.0 and F1=0.35, F2=0.25, F3=0.20, F4=0.05, F5=0.10, F6=0.05
- 5 new source clients: `icite.py`, `apex_rosters.py`, `drugs_fda.py`, `nccn.py`, `academic_tree.py`
- `data/aegis/editorial_roles_phase1.yaml` exists with >= 5 journals
- Reweight invariance: scaling all weights by a constant does not change percentile output
- Geometric-mean penalizes spiky candidates (one high + one low < two medium)
- All scoring tests pass: `uv run pytest src/aegis/scoring/ -v`
- All new source tests pass
- mypy strict passes on all new modules
- ruff passes on all new modules
- No existing Phase 0 tests broken

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/ -v` — Run all scoring tests
- `cd /Users/anvith/aegis && uv run pytest src/aegis/sources/icite_test.py src/aegis/sources/apex_rosters_test.py src/aegis/sources/drugs_fda_test.py src/aegis/sources/nccn_test.py src/aegis/sources/academic_tree_test.py -v` — Run new source client tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/scoring/ src/aegis/sources/icite.py src/aegis/sources/apex_rosters.py src/aegis/sources/drugs_fda.py src/aegis/sources/nccn.py src/aegis/sources/academic_tree.py` — Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/scoring/ src/aegis/sources/icite.py src/aegis/sources/apex_rosters.py src/aegis/sources/drugs_fda.py src/aegis/sources/nccn.py src/aegis/sources/academic_tree.py` — Lint all new modules
- `cd /Users/anvith/aegis && uv run pytest src/ tests/ -v --tb=short` — Verify no existing tests broken
- `cd /Users/anvith/aegis && uv run python -c "from aegis.scoring import QualityPrior, load_weight_vector; wv = load_weight_vector(); print(f'v{wv.version}: {wv.weights}')"` — Verify weight loading

## Notes

- This is Phase 1a of 3 Phase 1 sub-specs. Phase 1b covers integrity gate, topical-fit, recency, and end-to-end ranking. Phase 1c covers the audit harness, Plackett-Luce weight learning, bootstrap variance, and observability dashboards.
- New dependencies added: `scipy>=1.12`, `numpy>=1.26` (needed for Phase 1c Plackett-Luce, added now to avoid later dependency resolution issues).
- Source clients for iCite, Drugs@FDA, NCCN, apex rosters, and Academic Family Tree use in-memory stores in Phase 1. Phase 3 will migrate these to proper API clients with DB persistence. Each store documents this in its docstring.
- The `data/aegis/editorial_roles_phase1.yaml` is a handcrafted starter list of 5 major NSCLC journals. Phase 3 will replace this with automated journal masthead scraping.
- F5 explicitly documents its partial coverage (no patents) via the `coverage_caveat` field. Phase 2 closes the gap.
- F6 explicitly downweights when Academic Family Tree data is sparse via the `data_confidence` field.
- The geometric-mean composition `Q(c) = prod(F_i^{w_i})` deliberately punishes spiky candidates (one high dimension + five low dimensions scores worse than six medium dimensions). This is desirable per the program overview.
