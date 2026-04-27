# Plan: Phase 3c — Downstream Feedback Ingestion & Steady-State Weight Relearning

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase3c-feedback-learning.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build the feedback loop and steady-state weight relearning system for Aegis Phase 3. This sub-spec covers two tightly coupled tasks:

- **Task 1.6** (downstream-task-quality feedback ingestion): When a customer routes a labeling task to candidates ranked by Aegis, the resulting label set has measurable quality (inter-rater agreement Fleiss kappa, customer-side accept rate, post-hoc consensus rate). Ingest these signals back into Aegis as the steady-state ground truth for weight relearning. The customer publishes outcomes via a feedback endpoint; Aegis maps outcomes to the (query, candidate) pairs that produced them. The mapping (query, candidate, outcome) feeds into a derived pairwise-judgment dataset that augments the audit-panel data from Phase 1. A candidate who consistently produces low-kappa outputs in a subdomain receives an implicit downweighting in that subdomain via weight learning, not via score override.

- **Task 1.7** (steady-state weight relearning loop): Schedule weight relearning weekly using the union of audit-panel pairwise judgments (Phase 1) and downstream-task-quality-derived pairs (Task 1.6). The fitter is the same Plackett-Luce from Phase 1 Task 1.14; the input grows over time. Per-specialty exponents diverge as evidence accumulates. Auto-deploy on small changes; manual gate on large. Every refit cycle writes a report comparing prior vs new weights, per-specialty coverage, and confidence intervals.

This plan covers Phase 3 tasks: **1.6** (downstream-task-quality feedback ingestion) and **1.7** (steady-state weight relearning loop).

## Objective

When this plan is complete:
1. A `DownstreamQualityStore` at `src/aegis/learning/downstream_quality.py` can ingest structured task outcomes (Fleiss kappa, accept rate, consensus rate) posted by customers via `POST /v1/feedback/tasks/{task_id}/outcomes`, store them in an append-only JSONL log, and derive pairwise judgment records suitable for the Plackett-Luce fitter.
2. A FastAPI feedback router at `src/aegis/api/feedback.py` exposes the `POST /v1/feedback/tasks/{task_id}/outcomes` endpoint, validates incoming payloads (no PHI accepted), maps outcomes to (query, candidate) pairs, and persists them via the downstream quality store.
3. A `SteadyStateRefitter` at `src/aegis/learning/refit_steady_state.py` extends the existing `RefitScheduler` to run weekly refits using the union of audit-panel and downstream-quality pairwise judgments, with configurable source weighting in the loss function (downstream is the higher-trust source once it has accumulated enough data). Each refit produces a `RefitReport` comparing prior vs new weights, per-specialty coverage, and confidence intervals.
4. Deployment gating: small changes (all exponent deltas < threshold) auto-deploy; large changes require manual approval.
5. The `src/aegis/learning/__init__.py` module exports all new public symbols.
6. All modules pass mypy strict, ruff lint, and have comprehensive unit tests.

## Problem Statement

Phase 1 built the Plackett-Luce weight fitter and audit-panel data collection. However, audit-panel judgments are expensive (expert reviewer time) and slow to accumulate. The ranking system has no mechanism to learn from the downstream outcomes of tasks that use its rankings. When Aegis recommends candidates for a labeling task, the quality of the resulting labels (Fleiss kappa, accept rate, consensus rate) is a direct signal of whether the ranking got it right. Without ingesting this signal, the system cannot close the learning loop and weights remain static after the initial cold-start fitting.

Additionally, the existing `RefitScheduler` operates only on audit-panel data and has no concept of mixed data sources, source weighting, or reporting on weight drift over time. The steady-state regime requires weekly refits that grow the training set monotonically as downstream data accumulates, with per-specialty exponent divergence as a natural consequence of different evidence distributions.

## Solution Approach

1. **Feedback API first**: Build the `POST /v1/feedback/tasks/{task_id}/outcomes` endpoint as a FastAPI router. The endpoint accepts structured outcome metrics (Fleiss kappa, accept rate, consensus rate) with the task-level metadata needed to map back to (query, candidate) pairs. No PHI fields are accepted; the endpoint validates and rejects payloads containing disallowed fields.

2. **Downstream quality store**: Build `DownstreamQualityStore` using the same append-only JSONL pattern as the existing `JudgmentStore` in `src/aegis/audit/storage.py`. Store raw `TaskOutcome` records. Implement a `derive_pairwise_judgments()` method that converts task outcomes into `JudgmentRecord` objects: within each task, candidates who produced higher-quality outputs (higher kappa, higher accept rate) are winners over candidates who produced lower-quality outputs.

3. **Source-weighted Plackett-Luce**: The existing `PlackettLuceFitter` accepts a list of `JudgmentRecord` objects. Rather than modifying the fitter itself, the `SteadyStateRefitter` merges audit-panel and downstream-quality judgments and applies source weighting by oversampling the higher-trust source. When downstream data has accumulated N >= `min_downstream_count`, downstream judgments are oversampled at `downstream_weight_multiplier` relative to audit-panel judgments.

4. **Deployment gating**: After fitting, compare new exponents to prior exponents. If all deltas are below `auto_deploy_threshold`, write the new weight YAML automatically. If any delta exceeds the threshold, write the YAML to a staging path and flag the refit as requiring manual approval.

5. **Refit report**: Each cycle produces a `RefitReport` Pydantic model with prior vs new exponents, per-specialty coverage (number of judgments per specialty), confidence intervals, source breakdown, and deployment decision.

## Relevant Files

### Existing Files (read-only context, do not modify unless noted)
- `src/aegis/learning/refit_scheduler.py` -- Phase 1 `RefitScheduler`, `RefitResult`, `RefitCadence`. Extend, do not replace.
- `src/aegis/learning/plackett_luce.py` -- `PlackettLuceFitter`, `FittedWeights`, `JudgmentRecord`, `_compute_score`. The fitter is reused as-is.
- `src/aegis/learning/cold_start_guard.py` -- `ColdStartGuard`, `GuardVerdict`. Reuse for deployment stability checks.
- `src/aegis/learning/__init__.py` -- Package exports (will be modified to add new symbols).
- `src/aegis/audit/storage.py` -- `JudgmentStore`, `PairwiseJudgment`. Pattern reference for JSONL storage.
- `src/aegis/audit/harness.py` -- `AuditHarness`, `PairSampler`, `ScoredCandidate`. Context for audit-panel data flow.
- `src/aegis/scoring/quality_prior.py` -- `WeightVector`, `QualityPrior`, `load_weight_vector`. Weight vector loading.
- `src/aegis/scoring/rank.py` -- `Ranker`, `CandidateScoreInput`, `RankedList`. Ranking formula context.
- `src/aegis/storage/schema.py` -- `Candidate`, `ArtifactRefBundle`, `MeshDescriptor` models.
- `config/aegis/weights/translational_v1.yaml` -- Existing weight config (pattern for new versioned YAMLs).
- `pyproject.toml` -- Project configuration (FastAPI already a dependency).

### New Files
- `src/aegis/learning/downstream_quality.py` -- `DownstreamQualityStore`, `TaskOutcome`, `TaskOutcomeCandidate`, derived pairwise judgment logic
- `src/aegis/learning/downstream_quality_test.py` -- Tests for downstream quality store and pairwise derivation
- `src/aegis/api/__init__.py` -- API package init
- `src/aegis/api/feedback.py` -- FastAPI router for `POST /v1/feedback/tasks/{task_id}/outcomes`
- `src/aegis/api/feedback_test.py` -- Tests for feedback API endpoint
- `src/aegis/learning/refit_steady_state.py` -- `SteadyStateRefitter`, `RefitReport`, `DeploymentDecision`
- `src/aegis/learning/refit_steady_state_test.py` -- Tests for steady-state refitter

## Implementation Phases

### Phase 1: Foundation
- Create the API package scaffold (`src/aegis/api/__init__.py`)
- Build the downstream quality store with `TaskOutcome` model and JSONL persistence
- Implement pairwise judgment derivation from task outcomes

### Phase 2: Core Implementation
- Build the feedback API endpoint with validation and PHI rejection
- Build the steady-state refitter with source-weighted judgment merging
- Implement deployment gating (auto-deploy vs manual gate)
- Implement the `RefitReport` model

### Phase 3: Integration & Polish
- Update `src/aegis/learning/__init__.py` exports
- Write the synthetic feedback loop verification test (100 outcomes, refit, observe weight shifts)
- Run full validation suite

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Downstream quality store, pairwise judgment derivation, downstream quality tests, learning package exports
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Feedback API endpoint, feedback API tests, API package scaffold
  - Agent Type: general-purpose
- Builder
  - Name: builder-3
  - Role: Steady-state refitter, refit report, deployment gating, steady-state tests, synthetic feedback loop verification
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build`.
- Task descriptions must be **exhaustive** -- agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Start with foundational work, then core implementation, then validation.

### 1. Build Downstream Quality Store and Pairwise Derivation

- **Task ID**: downstream-quality-store
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the downstream quality data store that ingests task outcome records and derives pairwise judgments for the Plackett-Luce fitter.

    ## What to do

    1. Create `src/aegis/learning/downstream_quality.py` with the following models and store:

       ```python
       """Downstream-task-quality feedback store and pairwise judgment derivation."""

       from __future__ import annotations

       import logging
       from datetime import datetime
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       from aegis.learning.plackett_luce import JudgmentRecord

       logger = logging.getLogger(__name__)
       ```

       **Models to define:**

       a) `TaskOutcomeCandidate` (Pydantic BaseModel, frozen):
          - `candidate_uuid: str` -- UUID of the candidate who was part of this task
          - `candidate_rank: int` -- Rank assigned by Aegis at task creation time
          - `quality_prior_score: float` -- Q(c) percentile at task time
          - `topical_fit_score: float` -- T(c,q) at task time
          - `recency_score: float` -- R(c,q) at task time

       b) `TaskOutcome` (Pydantic BaseModel, frozen):
          - `task_id: str` -- Unique task identifier from the customer system
          - `query_specialty: str` -- Specialty/subdomain of this task (e.g., "translational", "drug_discovery")
          - `query_mesh_terms: list[str]` -- MeSH terms defining the query context
          - `candidates: list[TaskOutcomeCandidate]` -- Candidates who participated
          - `fleiss_kappa: float | None` -- Inter-rater agreement on the label set (None if not computable)
          - `accept_rate: float | None` -- Fraction of labels accepted by the customer [0, 1]
          - `consensus_rate: float | None` -- Post-hoc consensus rate [0, 1]
          - `submitted_at: datetime` -- When the outcome was reported
          - `metadata: dict[str, str]` -- Extra key-value pairs (non-PHI)

       c) `DownstreamQualityStore`:
          - Constructor: `__init__(self, *, storage_path: Path) -> None`
            - Store path for the JSONL file
          - `append(self, *, outcome: TaskOutcome) -> None`
            - Append a task outcome to the JSONL file. Use the same pattern as `JudgmentStore.append` in `src/aegis/audit/storage.py`:
              ```python
              with open(self._path, mode="a", encoding="utf-8") as fh:
                  fh.write(outcome.model_dump_json() + "\n")
                  fh.flush()
              ```
          - `load_all(self) -> list[TaskOutcome]`
            - Load all outcomes from the JSONL file. Return empty list if file does not exist.
          - `count(self) -> int`
            - Return the number of stored outcomes.
          - `by_specialty(self, *, specialty: str) -> list[TaskOutcome]`
            - Filter outcomes by `query_specialty`.
          - `derive_pairwise_judgments(self, *, specialty: str | None = None) -> list[JudgmentRecord]`
            - Convert stored task outcomes into pairwise `JudgmentRecord` objects for the Plackett-Luce fitter.
            - Algorithm:
              1. Load all outcomes (optionally filtered by specialty).
              2. For each task outcome with >= 2 candidates:
                 a. Compute a composite quality signal for each candidate:
                    `quality_signal = 0.0`; if `fleiss_kappa is not None`: `quality_signal += fleiss_kappa * 0.4`; if `accept_rate is not None`: `quality_signal += accept_rate * 0.35`; if `consensus_rate is not None`: `quality_signal += consensus_rate * 0.25`.
                 b. Sort candidates by quality_signal descending.
                 c. For each adjacent pair (higher, lower) in the sorted list:
                    - Create a `JudgmentRecord` where `winner_scores` comes from the higher-quality candidate's component scores (`quality_prior_score`, `topical_fit_score`, `recency_score`) mapped as `{"quality_prior": ..., "topical_fit": ..., "recency": ...}`, and `loser_scores` comes from the lower-quality candidate.
              3. Return the list of `JudgmentRecord` objects.
            - This mapping ensures that candidates who produced higher-quality task outputs are treated as "winners" in the pairwise comparison, allowing the Plackett-Luce fitter to learn which component scores (Q, T, R) predict downstream task quality.

    2. Create `src/aegis/learning/downstream_quality_test.py` with these tests:

       a) `test_task_outcome_model_creation`: Create a `TaskOutcome` with 3 candidates and verify all fields.

       b) `test_store_append_and_load(tmp_path)`: Create a `DownstreamQualityStore`, append 5 outcomes, `load_all()` returns 5, `count()` returns 5.

       c) `test_store_empty_file(tmp_path)`: Store with non-existent file returns empty list from `load_all()`.

       d) `test_by_specialty_filter(tmp_path)`: Append 3 outcomes (2 "translational", 1 "drug_discovery"), verify `by_specialty(specialty="translational")` returns 2.

       e) `test_derive_pairwise_basic(tmp_path)`: Create a store with 1 outcome containing 3 candidates with different quality signals. Verify `derive_pairwise_judgments()` returns 2 `JudgmentRecord` objects (adjacent pairs). Verify the winner's component scores map to `winner_scores` and the loser's to `loser_scores`.

       f) `test_derive_pairwise_single_candidate(tmp_path)`: Outcome with 1 candidate produces 0 judgments.

       g) `test_derive_pairwise_multiple_outcomes(tmp_path)`: 3 outcomes with 3 candidates each produces 6 judgments total (2 per outcome).

       h) `test_derive_pairwise_specialty_filter(tmp_path)`: Append mixed-specialty outcomes, derive with `specialty="translational"`, verify only translational outcomes contribute to judgments.

       i) `test_derive_pairwise_none_metrics(tmp_path)`: Outcome with `fleiss_kappa=None`, `accept_rate=0.8`, `consensus_rate=None` produces valid judgments using only the non-None metric.

       Use `from __future__ import annotations`, `from pathlib import Path`, no async tests needed. Follow the test pattern from `src/aegis/learning/refit_scheduler_test.py`.

    ## Files to create
    - `src/aegis/learning/downstream_quality.py`
    - `src/aegis/learning/downstream_quality_test.py`

    ## Files to modify
    None.

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - Append-only JSONL pattern from `src/aegis/audit/storage.py` (`JudgmentStore`)
    - `JudgmentRecord` import from `src/aegis/learning/plackett_luce.py`:
      ```python
      from aegis.learning.plackett_luce import JudgmentRecord
      ```
    - Logger at module level: `logger = logging.getLogger(__name__)`
    - Test pattern from `src/aegis/learning/refit_scheduler_test.py` (use `tmp_path` fixture, plain sync tests)

    ## Acceptance criteria
    - `src/aegis/learning/downstream_quality.py` exists and exports `DownstreamQualityStore`, `TaskOutcome`, `TaskOutcomeCandidate`
    - `TaskOutcome` has all required fields: `task_id`, `query_specialty`, `query_mesh_terms`, `candidates`, `fleiss_kappa`, `accept_rate`, `consensus_rate`, `submitted_at`, `metadata`
    - `DownstreamQualityStore.derive_pairwise_judgments()` returns `list[JudgmentRecord]`
    - All 9 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/learning/downstream_quality_test.py -v && uv run mypy src/aegis/learning/downstream_quality.py && uv run ruff check src/aegis/learning/downstream_quality.py
    ```

### 2. Build Feedback API Endpoint

- **Task ID**: feedback-api
- **Role**: builder
- **Depends On**: downstream-quality-store
- **Assigned To**: builder-2
- **Description**: |
    Build the FastAPI router that exposes `POST /v1/feedback/tasks/{task_id}/outcomes` for customers to submit downstream task quality outcomes.

    ## What to do

    1. Create `src/aegis/api/__init__.py`:
       ```python
       """Aegis API — customer-facing endpoints for feedback and querying."""

       from __future__ import annotations
       ```

    2. Create `src/aegis/api/feedback.py` with a FastAPI router:

       ```python
       """Feedback API: POST /v1/feedback/tasks/{task_id}/outcomes."""

       from __future__ import annotations

       import logging
       from datetime import datetime
       from pathlib import Path

       from fastapi import APIRouter, HTTPException, status
       from pydantic import BaseModel, ConfigDict, field_validator

       from aegis.learning.downstream_quality import (
           DownstreamQualityStore,
           TaskOutcome,
           TaskOutcomeCandidate,
       )

       logger = logging.getLogger(__name__)

       router = APIRouter(prefix="/v1/feedback", tags=["feedback"])
       ```

       **Request models:**

       a) `CandidateOutcomeRequest` (Pydantic BaseModel):
          - `candidate_uuid: str`
          - `candidate_rank: int`
          - `quality_prior_score: float`
          - `topical_fit_score: float`
          - `recency_score: float`

       b) `TaskOutcomeRequest` (Pydantic BaseModel):
          - `query_specialty: str`
          - `query_mesh_terms: list[str]`
          - `candidates: list[CandidateOutcomeRequest]`
          - `fleiss_kappa: float | None = None`
          - `accept_rate: float | None = None`
          - `consensus_rate: float | None = None`
          - `metadata: dict[str, str] = {}`
          - Add a `field_validator` on `metadata` that rejects keys containing PHI-related strings. The validator should check that no key in metadata matches any of: `"ssn"`, `"social_security"`, `"dob"`, `"date_of_birth"`, `"mrn"`, `"medical_record"`, `"patient_name"`, `"patient_id"`, `"phi"`. If any match (case-insensitive), raise `ValueError("PHI fields are not accepted")`.
          - Add a `field_validator` on `fleiss_kappa` that ensures it is between -1.0 and 1.0 (inclusive) if not None. Raise `ValueError` if out of range.
          - Add a `field_validator` on `accept_rate` that ensures it is between 0.0 and 1.0 (inclusive) if not None. Raise `ValueError` if out of range.
          - Add a `field_validator` on `consensus_rate` that ensures it is between 0.0 and 1.0 (inclusive) if not None. Raise `ValueError` if out of range.

       c) `TaskOutcomeResponse` (Pydantic BaseModel):
          - `task_id: str`
          - `status: str` -- always "accepted"
          - `outcome_count: int` -- total outcomes stored after this submission
          - `derived_judgments_count: int` -- number of pairwise judgments derived from this outcome

       **Endpoint:**

       ```python
       # Module-level store (will be overridden in tests via dependency injection)
       _default_store_path = Path("data/aegis/downstream_quality.jsonl")


       def _get_store(store_path: Path | None = None) -> DownstreamQualityStore:
           """Factory for the downstream quality store."""
           return DownstreamQualityStore(storage_path=store_path or _default_store_path)


       @router.post(
           "/tasks/{task_id}/outcomes",
           response_model=TaskOutcomeResponse,
           status_code=status.HTTP_201_CREATED,
       )
       def submit_task_outcome(
           task_id: str,
           body: TaskOutcomeRequest,
       ) -> TaskOutcomeResponse:
           """Submit downstream task quality outcomes for a completed task.

           Maps task outcomes to (query, candidate) pairs and persists
           them for weight relearning.
           """
           store = _get_store()

           # Build internal TaskOutcome from request
           candidates = [
               TaskOutcomeCandidate(
                   candidate_uuid=c.candidate_uuid,
                   candidate_rank=c.candidate_rank,
                   quality_prior_score=c.quality_prior_score,
                   topical_fit_score=c.topical_fit_score,
                   recency_score=c.recency_score,
               )
               for c in body.candidates
           ]

           outcome = TaskOutcome(
               task_id=task_id,
               query_specialty=body.query_specialty,
               query_mesh_terms=body.query_mesh_terms,
               candidates=candidates,
               fleiss_kappa=body.fleiss_kappa,
               accept_rate=body.accept_rate,
               consensus_rate=body.consensus_rate,
               submitted_at=datetime.now(),
               metadata=body.metadata,
           )

           store.append(outcome=outcome)

           # Derive pairwise judgments to report count
           # (only from this single outcome, not the full store)
           n_candidates = len(candidates)
           derived_count = max(0, n_candidates - 1)  # adjacent pairs

           return TaskOutcomeResponse(
               task_id=task_id,
               status="accepted",
               outcome_count=store.count(),
               derived_judgments_count=derived_count,
           )
       ```

       **IMPORTANT**: The `_get_store` function must be designed so tests can override the store path. Use a module-level variable pattern so tests can monkeypatch it or pass a custom store path.

    3. Create `src/aegis/api/feedback_test.py` with tests using FastAPI's `TestClient`:

       ```python
       """Tests for the feedback API endpoint."""

       from __future__ import annotations

       from pathlib import Path
       from unittest.mock import patch

       import pytest
       from fastapi import FastAPI
       from fastapi.testclient import TestClient

       from aegis.api.feedback import router, _get_store
       from aegis.learning.downstream_quality import DownstreamQualityStore
       ```

       Create a test app fixture:
       ```python
       @pytest.fixture
       def app():
           app = FastAPI()
           app.include_router(router)
           return app

       @pytest.fixture
       def client(app):
           return TestClient(app)
       ```

       Tests to write:

       a) `test_submit_outcome_success(client, tmp_path)`: POST a valid outcome with 3 candidates and kappa=0.7, accept_rate=0.85, consensus_rate=0.9. Patch `_get_store` to use `tmp_path`. Assert 201 status, response has `task_id`, `status == "accepted"`, `derived_judgments_count == 2`.

       b) `test_submit_outcome_phi_rejection(client, tmp_path)`: POST with metadata containing `{"ssn": "123-45-6789"}`. Assert 422 status (validation error).

       c) `test_submit_outcome_phi_case_insensitive(client, tmp_path)`: POST with metadata containing `{"Patient_Name": "test"}`. Assert 422 status.

       d) `test_submit_outcome_kappa_out_of_range(client, tmp_path)`: POST with `fleiss_kappa=2.0`. Assert 422 status.

       e) `test_submit_outcome_accept_rate_out_of_range(client, tmp_path)`: POST with `accept_rate=-0.1`. Assert 422 status.

       f) `test_submit_outcome_none_metrics(client, tmp_path)`: POST with all metrics as None. Assert 201 status.

       g) `test_submit_outcome_single_candidate(client, tmp_path)`: POST with 1 candidate. Assert 201 status, `derived_judgments_count == 0`.

       h) `test_submit_multiple_outcomes(client, tmp_path)`: POST two outcomes for different task_ids. Verify second response has `outcome_count == 2`.

       For patching, use:
       ```python
       def _make_store(tmp_path: Path) -> DownstreamQualityStore:
           return DownstreamQualityStore(storage_path=tmp_path / "test_outcomes.jsonl")
       ```
       and monkeypatch the `_get_store` function or use `app.dependency_overrides`.

       **IMPORTANT**: The test must handle the store path override correctly. The simplest approach is to monkeypatch `aegis.api.feedback._default_store_path` to point to `tmp_path / "test_outcomes.jsonl"` in each test, or use a shared fixture that does this.

    ## Files to create
    - `src/aegis/api/__init__.py`
    - `src/aegis/api/feedback.py`
    - `src/aegis/api/feedback_test.py`

    ## Files to modify
    None.

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - FastAPI `APIRouter` with prefix and tags
    - `field_validator` from Pydantic v2 for validation rules
    - Logger at module level: `logger = logging.getLogger(__name__)`
    - FastAPI's `TestClient` for API testing (not async)
    - `pyproject.toml` already has `fastapi>=0.110` as a dependency

    ## Acceptance criteria
    - `src/aegis/api/__init__.py` exists and is importable
    - `src/aegis/api/feedback.py` exists and exports a FastAPI `router`
    - Design assertion: `POST /v1/feedback/tasks/{task_id}/outcomes` returns 201 with `TaskOutcomeResponse`
    - PHI metadata is rejected with 422
    - Metric range validation works (kappa in [-1, 1], rates in [0, 1])
    - All 8 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/feedback_test.py -v && uv run mypy src/aegis/api/feedback.py && uv run ruff check src/aegis/api/feedback.py src/aegis/api/__init__.py
    ```

### 3. Build Steady-State Refitter

- **Task ID**: steady-state-refitter
- **Role**: builder
- **Depends On**: downstream-quality-store
- **Assigned To**: builder-3
- **Description**: |
    Build the steady-state weight relearning loop that runs weekly refits using the union of audit-panel and downstream-quality pairwise judgments, with deployment gating and per-cycle reporting.

    ## What to do

    1. Create `src/aegis/learning/refit_steady_state.py`:

       ```python
       """Steady-state weight relearning: weekly refits from mixed data sources."""

       from __future__ import annotations

       import logging
       from datetime import datetime
       from pathlib import Path

       import yaml  # type: ignore[import-untyped]
       from pydantic import BaseModel, ConfigDict

       from aegis.learning.cold_start_guard import ColdStartGuard, GuardVerdict
       from aegis.learning.downstream_quality import DownstreamQualityStore
       from aegis.learning.plackett_luce import (
           FittedWeights,
           JudgmentRecord,
           PlackettLuceFitter,
       )
       from aegis.learning.refit_scheduler import RefitCadence, RefitScheduler
       from aegis.scoring.quality_prior import WeightVector, load_weight_vector

       logger = logging.getLogger(__name__)
       ```

       **Models to define:**

       a) `DeploymentDecision` (Pydantic BaseModel, frozen):
          - `action: str` -- One of: "auto_deploy", "manual_gate", "blocked"
          - `reason: str` -- Human-readable reason for the decision
          - `max_exponent_delta: float` -- The largest absolute exponent change
          - `threshold: float` -- The auto-deploy threshold used

       b) `SourceBreakdown` (Pydantic BaseModel, frozen):
          - `audit_panel_count: int` -- Number of audit-panel judgments used
          - `downstream_count: int` -- Number of downstream-derived judgments used
          - `downstream_weight_multiplier: float` -- The oversampling multiplier applied to downstream judgments
          - `total_effective_count: int` -- Total after oversampling

       c) `SpecialtyCoverage` (Pydantic BaseModel, frozen):
          - `specialty: str`
          - `judgment_count: int`
          - `downstream_outcome_count: int`
          - `has_sufficient_data: bool` -- True if judgment_count >= min_judgments threshold

       d) `RefitReport` (Pydantic BaseModel, frozen):
          - `version: int` -- The new weight version number
          - `specialty: str`
          - `timestamp: datetime`
          - `prior_exponents: dict[str, float]` -- alpha, beta, gamma before refit
          - `new_exponents: dict[str, float]` -- alpha, beta, gamma after refit
          - `exponent_deltas: dict[str, float]` -- absolute change per exponent
          - `prior_ci: dict[str, tuple[float, float]]` -- confidence intervals before
          - `new_ci: dict[str, tuple[float, float]]` -- confidence intervals after
          - `source_breakdown: SourceBreakdown`
          - `specialty_coverage: list[SpecialtyCoverage]`
          - `deployment_decision: DeploymentDecision`
          - `guard_verdict: GuardVerdict`
          - `fitted_weights: FittedWeights`

       e) `SteadyStateConfig` (Pydantic BaseModel, frozen):
          - `auto_deploy_threshold: float = 0.05` -- Max exponent delta for auto-deploy
          - `min_downstream_count: int = 50` -- Minimum downstream outcomes before upweighting
          - `downstream_weight_multiplier: float = 1.5` -- Oversampling factor for downstream judgments
          - `min_judgments_per_specialty: int = 20` -- Minimum judgments per specialty for sufficient data
          - `ci_threshold: float = 0.2` -- ColdStartGuard CI threshold

       **Class: `SteadyStateRefitter`**

       ```python
       class SteadyStateRefitter:
           """Steady-state weight relearning with mixed data sources."""

           def __init__(
               self,
               *,
               weights_dir: Path,
               audit_judgments_path: Path,
               downstream_store_path: Path,
               config: SteadyStateConfig | None = None,
           ) -> None:
               self._weights_dir = weights_dir
               self._config = config or SteadyStateConfig()
               self._audit_judgments_path = audit_judgments_path
               self._downstream_store = DownstreamQualityStore(
                   storage_path=downstream_store_path,
               )
               # Use the audit judgment store from Phase 1
               from aegis.audit.storage import JudgmentStore
               self._audit_store = JudgmentStore(
                   storage_path=audit_judgments_path,
               )
       ```

       **Methods:**

       a) `_load_audit_judgments(self, *, specialty: str | None = None) -> list[JudgmentRecord]`:
          - Load all pairwise judgments from the audit store.
          - Convert each `PairwiseJudgment` into a `JudgmentRecord`. The conversion requires component scores which are not stored in `PairwiseJudgment`. Since Phase 1 audit data doesn't carry component scores, return them as-is if they can be converted, OR load pre-converted JudgmentRecord files.
          - **SIMPLIFICATION**: For this implementation, assume audit-panel judgments are stored as pre-converted `JudgmentRecord` objects in a separate JSONL file at `{audit_judgments_path}`. Each line is a JSON object with `winner_scores` and `loser_scores` dicts. Load them directly:
            ```python
            import json
            records: list[JudgmentRecord] = []
            if self._audit_judgments_path.exists():
                with open(self._audit_judgments_path, encoding="utf-8") as fh:
                    for line in fh:
                        stripped = line.strip()
                        if stripped:
                            data = json.loads(stripped)
                            records.append(JudgmentRecord(
                                winner_scores=data["winner_scores"],
                                loser_scores=data["loser_scores"],
                            ))
            return records
            ```

       b) `_merge_judgments(self, *, audit: list[JudgmentRecord], downstream: list[JudgmentRecord]) -> tuple[list[JudgmentRecord], SourceBreakdown]`:
          - Merge audit-panel and downstream-derived judgments.
          - If downstream count >= `config.min_downstream_count`, oversample downstream by repeating each downstream judgment `config.downstream_weight_multiplier` times (round to int).
          - Return merged list and a `SourceBreakdown` summarizing counts.
          - Implementation:
            ```python
            multiplier = 1.0
            if len(downstream) >= self._config.min_downstream_count:
                multiplier = self._config.downstream_weight_multiplier

            # Oversample downstream by repeating
            effective_downstream = []
            repeat_count = max(1, round(multiplier))
            for _ in range(repeat_count):
                effective_downstream.extend(downstream)

            merged = list(audit) + effective_downstream

            breakdown = SourceBreakdown(
                audit_panel_count=len(audit),
                downstream_count=len(downstream),
                downstream_weight_multiplier=multiplier,
                total_effective_count=len(merged),
            )
            return merged, breakdown
            ```

       c) `_compute_deployment_decision(self, *, prior_exponents: dict[str, float], new_exponents: dict[str, float]) -> DeploymentDecision`:
          - Compare prior and new exponents. Compute absolute deltas.
          - If max delta < `config.auto_deploy_threshold`: return `action="auto_deploy"`.
          - If max delta >= `config.auto_deploy_threshold`: return `action="manual_gate"`.
          - The `"blocked"` action is reserved for when the cold-start guard rejects the fit (handled separately).

       d) `run(self, *, specialty: str, current_weights: WeightVector) -> RefitReport`:
          - This is the main entry point. Orchestrates one refit cycle.
          - Steps:
            1. Load audit-panel judgments.
            2. Load downstream-derived judgments via `self._downstream_store.derive_pairwise_judgments(specialty=specialty)`.
            3. Merge with source weighting via `_merge_judgments`.
            4. Create `PlackettLuceFitter` with bounds from `current_weights.exponent_bounds`.
            5. Fit using merged judgments and `current_weights` as initial.
            6. Evaluate fit stability via `ColdStartGuard(ci_threshold=self._config.ci_threshold).evaluate(fitted=fitted)`.
            7. Compute deployment decision.
            8. If auto_deploy and guard allows: write new weight YAML via the existing `RefitScheduler.execute_refit` pattern (write YAML to `weights_dir / "{specialty}_v{N}.yaml"`).
            9. If manual_gate: write to staging path `weights_dir / "staging" / "{specialty}_v{N}_pending.yaml"`.
            10. If guard blocks: do not write. Set deployment decision action to "blocked".
            11. Build and return `RefitReport`.

          - Version bumping: find the highest existing version for the specialty in `weights_dir` by globbing `{specialty}_v*.yaml` and incrementing.

       **IMPORTANT**: The `run()` method must return a `RefitReport` in all cases (auto-deploy, manual-gate, or blocked). The report contains the full analysis regardless of deployment outcome.

    2. Create `src/aegis/learning/refit_steady_state_test.py` with these tests:

       a) `test_steady_state_config_defaults`: Verify `SteadyStateConfig()` has expected defaults.

       b) `test_merge_judgments_no_oversample`: 10 audit + 10 downstream (below min_downstream_count=50) produces 20 total, multiplier=1.0.

       c) `test_merge_judgments_with_oversample`: 10 audit + 60 downstream (above min_downstream_count=50) with multiplier=1.5 produces 10 + 60*2 = 130 total (round(1.5)=2).

       d) `test_deployment_decision_auto_deploy`: Prior exponents `{"alpha": 0.7, "beta": 1.0, "gamma": 0.4}`, new exponents `{"alpha": 0.72, "beta": 1.01, "gamma": 0.41}` (all deltas < 0.05). Expect `action="auto_deploy"`.

       e) `test_deployment_decision_manual_gate`: Prior exponents `{"alpha": 0.7, "beta": 1.0, "gamma": 0.4}`, new exponents `{"alpha": 0.8, "beta": 1.0, "gamma": 0.4}` (alpha delta = 0.1 > 0.05). Expect `action="manual_gate"`.

       f) `test_run_produces_refit_report(tmp_path)`: Full integration test:
          1. Create a weights dir with a `translational_v1.yaml` (copy format from `config/aegis/weights/translational_v1.yaml` -- contents provided below).
          2. Create an audit judgments JSONL with 30 synthetic `JudgmentRecord` entries (JSON lines with `winner_scores` and `loser_scores` dicts).
          3. Create a downstream quality store with 20 `TaskOutcome` entries containing 3 candidates each.
          4. Create a `SteadyStateRefitter` and call `run(specialty="translational", current_weights=weight_vector)`.
          5. Assert the result is a `RefitReport`.
          6. Assert `report.source_breakdown.audit_panel_count == 30`.
          7. Assert `report.source_breakdown.downstream_count > 0`.
          8. Assert `report.deployment_decision.action in ("auto_deploy", "manual_gate", "blocked")`.
          9. Assert `report.new_exponents` has keys "alpha", "beta", "gamma".
          10. Assert `report.guard_verdict` is a `GuardVerdict`.

          Weight YAML content for test:
          ```yaml
          version: 1
          specialty: translational
          created: "2026-04-26"
          weights:
            f1_rcr: 0.35
            f2_funding: 0.25
            f3_leadership: 0.20
            f4_apex: 0.05
            f5_translational: 0.10
            f6_lineage: 0.05
          exponents:
            alpha: 0.7
            beta: 1.0
            gamma: 0.4
          exponent_bounds:
            alpha: [0.3, 1.2]
            beta: [0.5, 1.5]
            gamma: [0.1, 0.8]
          ```

          Use `_generate_synthetic_judgments` helper (same pattern as `src/aegis/learning/plackett_luce_test.py`):
          ```python
          import json
          import random

          def _write_audit_judgments(path: Path, n: int = 30) -> None:
              rng = random.Random(42)
              with open(path, "w", encoding="utf-8") as fh:
                  for _ in range(n):
                      record = {
                          "winner_scores": {
                              "quality_prior": rng.uniform(0.1, 1.0),
                              "topical_fit": rng.uniform(0.1, 1.0),
                              "recency": rng.uniform(0.1, 1.0),
                          },
                          "loser_scores": {
                              "quality_prior": rng.uniform(0.1, 1.0),
                              "topical_fit": rng.uniform(0.1, 1.0),
                              "recency": rng.uniform(0.1, 1.0),
                          },
                      }
                      fh.write(json.dumps(record) + "\n")
          ```

          Use `_write_downstream_outcomes` helper:
          ```python
          from datetime import datetime
          from aegis.learning.downstream_quality import (
              DownstreamQualityStore,
              TaskOutcome,
              TaskOutcomeCandidate,
          )

          def _write_downstream_outcomes(store: DownstreamQualityStore, n: int = 20) -> None:
              rng = random.Random(99)
              for i in range(n):
                  candidates = [
                      TaskOutcomeCandidate(
                          candidate_uuid=f"cand-{i}-{j}",
                          candidate_rank=j + 1,
                          quality_prior_score=rng.uniform(0.1, 1.0),
                          topical_fit_score=rng.uniform(0.1, 1.0),
                          recency_score=rng.uniform(0.1, 1.0),
                      )
                      for j in range(3)
                  ]
                  outcome = TaskOutcome(
                      task_id=f"task-{i}",
                      query_specialty="translational",
                      query_mesh_terms=["Neoplasms", "Drug Therapy"],
                      candidates=candidates,
                      fleiss_kappa=rng.uniform(0.3, 0.9),
                      accept_rate=rng.uniform(0.5, 1.0),
                      consensus_rate=rng.uniform(0.6, 1.0),
                      submitted_at=datetime(2026, 4, 26),
                      metadata={},
                  )
                  store.append(outcome=outcome)
          ```

       g) `test_run_auto_deploys_yaml(tmp_path)`: Run with `auto_deploy_threshold=1.0` (very high, so any fit auto-deploys). Verify a new weight YAML file was written to `weights_dir`.

       h) `test_run_manual_gate_stages(tmp_path)`: Run with `auto_deploy_threshold=0.001` (very low, so any change triggers manual gate). Verify YAML was written to `weights_dir / "staging"`.

       i) `test_run_blocked_when_guard_rejects(tmp_path)`: Run with only 5 audit judgments and 0 downstream (below cold-start guard minimum of 20). Verify `deployment_decision.action == "blocked"`.

       j) `test_synthetic_feedback_loop(tmp_path)`: Synthetic feedback loop verification test:
          1. Generate 100 task outcomes where candidates with higher quality_prior_score tend to have higher fleiss_kappa (positive correlation). Use a seeded RNG for reproducibility.
          2. Create weight vector with alpha=0.7, beta=1.0, gamma=0.4.
          3. Run the steady-state refitter.
          4. Verify the resulting alpha moved upward (or at least didn't decrease significantly) since quality_prior is the signal positively correlated with task quality. Assert `report.new_exponents["alpha"] >= 0.5` (the fitter should not drive alpha to the floor).
          5. This is the verification test specified in the task requirements: "feed 100 task outcomes, refit weights, observe expected weight shifts."

    ## Files to create
    - `src/aegis/learning/refit_steady_state.py`
    - `src/aegis/learning/refit_steady_state_test.py`

    ## Files to modify
    None.

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - YAML writing follows `src/aegis/learning/refit_scheduler.py` `execute_refit` pattern
    - Import `PlackettLuceFitter`, `JudgmentRecord`, `FittedWeights` from `aegis.learning.plackett_luce`
    - Import `ColdStartGuard`, `GuardVerdict` from `aegis.learning.cold_start_guard`
    - Import `WeightVector`, `load_weight_vector` from `aegis.scoring.quality_prior`
    - Logger at module level: `logger = logging.getLogger(__name__)`
    - Test pattern from `src/aegis/learning/refit_scheduler_test.py` and `src/aegis/learning/plackett_luce_test.py`

    ## Acceptance criteria
    - `src/aegis/learning/refit_steady_state.py` exists and exports `SteadyStateRefitter`, `RefitReport`, `DeploymentDecision`, `SourceBreakdown`, `SpecialtyCoverage`, `SteadyStateConfig`
    - Design assertion: `SteadyStateRefitter.run(specialty, current_weights) -> RefitReport`
    - `RefitReport` contains prior/new exponents, deltas, CIs, source breakdown, deployment decision, guard verdict
    - Deployment gating: auto-deploy on small changes, manual gate on large, blocked when guard rejects
    - Synthetic feedback loop test passes (100 outcomes, refit, weight shifts observed)
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/learning/refit_steady_state_test.py -v && uv run mypy src/aegis/learning/refit_steady_state.py && uv run ruff check src/aegis/learning/refit_steady_state.py
    ```

### 4. Update Learning Package Exports

- **Task ID**: update-learning-exports
- **Role**: builder
- **Depends On**: downstream-quality-store, steady-state-refitter
- **Assigned To**: builder-1
- **Description**: |
    Update the `src/aegis/learning/__init__.py` package to export all new public symbols from the downstream quality store and steady-state refitter modules.

    ## What to do

    1. Edit `src/aegis/learning/__init__.py` to add imports and exports for the new modules.

       The current file contents are:
       ```python
       """Aegis learning — exponent fitting from pairwise audit judgments."""

       from aegis.learning.cold_start_guard import ColdStartGuard, GuardVerdict
       from aegis.learning.plackett_luce import (
           FittedWeights,
           JudgmentRecord,
           PlackettLuceFitter,
       )
       from aegis.learning.refit_scheduler import (
           RefitCadence,
           RefitResult,
           RefitScheduler,
       )

       __all__ = [
           "ColdStartGuard",
           "FittedWeights",
           "GuardVerdict",
           "JudgmentRecord",
           "PlackettLuceFitter",
           "RefitCadence",
           "RefitResult",
           "RefitScheduler",
       ]
       ```

       Add these new imports:
       ```python
       from aegis.learning.downstream_quality import (
           DownstreamQualityStore,
           TaskOutcome,
           TaskOutcomeCandidate,
       )
       from aegis.learning.refit_steady_state import (
           DeploymentDecision,
           RefitReport,
           SourceBreakdown,
           SpecialtyCoverage,
           SteadyStateConfig,
           SteadyStateRefitter,
       )
       ```

       Add these new symbols to `__all__`:
       ```python
       "DeploymentDecision",
       "DownstreamQualityStore",
       "RefitReport",
       "SourceBreakdown",
       "SpecialtyCoverage",
       "SteadyStateConfig",
       "SteadyStateRefitter",
       "TaskOutcome",
       "TaskOutcomeCandidate",
       ```

       Update the module docstring to:
       ```python
       """Aegis learning — exponent fitting from pairwise audit judgments and downstream task-quality feedback."""
       ```

       The final `__all__` list should be sorted alphabetically.

    ## Files to modify
    - `src/aegis/learning/__init__.py` -- Add imports and exports for downstream quality and steady-state refitter modules

    ## Code patterns to follow
    - Alphabetically sorted `__all__` list (consistent with existing codebase style)
    - Explicit imports from submodules (no wildcard imports)

    ## Acceptance criteria
    - All new symbols are importable from `aegis.learning`:
      - `DownstreamQualityStore`, `TaskOutcome`, `TaskOutcomeCandidate`
      - `SteadyStateRefitter`, `RefitReport`, `DeploymentDecision`, `SourceBreakdown`, `SpecialtyCoverage`, `SteadyStateConfig`
    - `__all__` contains all new symbols
    - Existing symbols still importable (no regression)
    - mypy passes on `__init__.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.learning import (
        ColdStartGuard, FittedWeights, GuardVerdict, JudgmentRecord,
        PlackettLuceFitter, RefitCadence, RefitResult, RefitScheduler,
        DownstreamQualityStore, TaskOutcome, TaskOutcomeCandidate,
        SteadyStateRefitter, RefitReport, DeploymentDecision,
        SourceBreakdown, SpecialtyCoverage, SteadyStateConfig,
    )
    print('All learning exports OK')
    " && uv run mypy src/aegis/learning/__init__.py && uv run ruff check src/aegis/learning/__init__.py
    ```

### 5. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: downstream-quality-store, feedback-api, steady-state-refitter, update-learning-exports
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the Phase 3c feedback and learning sub-spec.

    ## Validation Commands

    Run each of these commands. ALL must pass for validation to succeed.

    1. Downstream quality store tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/learning/downstream_quality_test.py -v
    ```

    2. Feedback API tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/feedback_test.py -v
    ```

    3. Steady-state refitter tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/learning/refit_steady_state_test.py -v
    ```

    4. All Phase 3c tests together:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/learning/downstream_quality_test.py src/aegis/api/feedback_test.py src/aegis/learning/refit_steady_state_test.py -v
    ```

    5. mypy strict on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/learning/downstream_quality.py src/aegis/api/feedback.py src/aegis/learning/refit_steady_state.py src/aegis/learning/__init__.py src/aegis/api/__init__.py
    ```

    6. ruff lint on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/learning/downstream_quality.py src/aegis/api/feedback.py src/aegis/learning/refit_steady_state.py src/aegis/learning/__init__.py src/aegis/api/__init__.py
    ```

    7. Verify learning package exports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.learning import (
        ColdStartGuard, FittedWeights, GuardVerdict, JudgmentRecord,
        PlackettLuceFitter, RefitCadence, RefitResult, RefitScheduler,
        DownstreamQualityStore, TaskOutcome, TaskOutcomeCandidate,
        SteadyStateRefitter, RefitReport, DeploymentDecision,
        SourceBreakdown, SpecialtyCoverage, SteadyStateConfig,
    )
    print('All learning exports OK')
    "
    ```

    8. Verify API package imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.api.feedback import router; print('Feedback router OK')"
    ```

    9. Verify design assertions:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.learning.downstream_quality import DownstreamQualityStore, TaskOutcome, TaskOutcomeCandidate
    from aegis.learning.refit_steady_state import SteadyStateRefitter, RefitReport
    from aegis.learning.plackett_luce import JudgmentRecord

    # Verify DownstreamQualityStore has derive_pairwise_judgments
    assert hasattr(DownstreamQualityStore, 'derive_pairwise_judgments')

    # Verify SteadyStateRefitter has run method
    assert hasattr(SteadyStateRefitter, 'run')

    # Verify TaskOutcome has all required fields
    fields = TaskOutcome.model_fields
    for f in ['task_id', 'query_specialty', 'query_mesh_terms', 'candidates',
              'fleiss_kappa', 'accept_rate', 'consensus_rate', 'submitted_at', 'metadata']:
        assert f in fields, f'Missing field: {f}'

    print('All design assertions OK')
    "
    ```

    10. Verify existing Phase 1 learning tests still pass (no regression):
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/learning/plackett_luce_test.py src/aegis/learning/refit_scheduler_test.py src/aegis/learning/cold_start_guard_test.py -v
    ```

    11. Verify existing audit tests still pass (no regression):
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/audit/harness_test.py -v
    ```

    ## Acceptance Criteria

    ALL of these must be verified:

    - [ ] `src/aegis/learning/downstream_quality.py` exists and exports `DownstreamQualityStore`, `TaskOutcome`, `TaskOutcomeCandidate`
    - [ ] `src/aegis/api/__init__.py` exists and is importable
    - [ ] `src/aegis/api/feedback.py` exists and exports FastAPI `router`
    - [ ] Design assertion: `POST /v1/feedback/tasks/{task_id}/outcomes` endpoint exists and returns 201
    - [ ] PHI metadata fields are rejected with 422
    - [ ] Metric range validation works (kappa in [-1, 1], rates in [0, 1])
    - [ ] `src/aegis/learning/refit_steady_state.py` exists and exports `SteadyStateRefitter`, `RefitReport`, `DeploymentDecision`
    - [ ] Design assertion: `SteadyStateRefitter.run() -> RefitReport`
    - [ ] `RefitReport` contains: prior/new exponents, deltas, CIs, source breakdown, deployment decision, guard verdict
    - [ ] Auto-deploy on small changes (exponent deltas < threshold)
    - [ ] Manual gate on large changes (exponent deltas >= threshold)
    - [ ] Blocked when cold-start guard rejects
    - [ ] Synthetic feedback loop: 100 outcomes fed, refit completed, weight shifts observed
    - [ ] Weight-version monotonically increases on auto-deploy
    - [ ] All downstream quality tests pass (9 tests)
    - [ ] All feedback API tests pass (8 tests)
    - [ ] All steady-state refitter tests pass (10 tests)
    - [ ] mypy strict passes on all new modules
    - [ ] ruff lint passes on all new modules
    - [ ] `src/aegis/learning/__init__.py` exports all new symbols
    - [ ] Existing Phase 1 learning tests unbroken
    - [ ] Existing audit tests unbroken

## Acceptance Criteria

- `DownstreamQualityStore` at `src/aegis/learning/downstream_quality.py` exports `TaskOutcome`, `TaskOutcomeCandidate`, and `derive_pairwise_judgments() -> list[JudgmentRecord]`
- `POST /v1/feedback/tasks/{task_id}/outcomes` endpoint at `src/aegis/api/feedback.py` accepts structured outcome metrics, rejects PHI, validates metric ranges, and persists to the downstream quality store
- `SteadyStateRefitter.run(specialty, current_weights) -> RefitReport` at `src/aegis/learning/refit_steady_state.py` runs a complete refit cycle with mixed audit + downstream data
- `RefitReport` contains prior vs new exponents, per-specialty coverage, confidence intervals, source breakdown, and deployment decision
- Deployment gating: auto-deploy on small exponent changes (all deltas < 0.05), manual gate on large changes, blocked when cold-start guard rejects
- Downstream-quality data is the higher-trust source once accumulated (oversampled at 1.5x when N >= 50)
- Synthetic feedback loop verification: 100 task outcomes fed, refit weights, observe expected weight shifts
- Weight-version table grows monotonically on auto-deploy
- All new tests pass (9 downstream quality + 8 feedback API + 10 steady-state refitter = 27 tests)
- mypy strict mode passes on all new modules
- ruff lint passes on all new modules
- No existing Phase 1 learning or audit tests broken
- `src/aegis/learning/__init__.py` exports all new public symbols

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/learning/downstream_quality_test.py src/aegis/api/feedback_test.py src/aegis/learning/refit_steady_state_test.py -v` -- Run all Phase 3c tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/learning/downstream_quality.py src/aegis/api/feedback.py src/aegis/learning/refit_steady_state.py src/aegis/learning/__init__.py src/aegis/api/__init__.py` -- Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/learning/downstream_quality.py src/aegis/api/feedback.py src/aegis/learning/refit_steady_state.py src/aegis/learning/__init__.py src/aegis/api/__init__.py` -- Lint all new modules
- `cd /Users/anvith/aegis && uv run pytest src/aegis/learning/plackett_luce_test.py src/aegis/learning/refit_scheduler_test.py src/aegis/learning/cold_start_guard_test.py src/aegis/audit/harness_test.py -v` -- Verify existing tests unbroken
- `cd /Users/anvith/aegis && uv run python -c "from aegis.learning import DownstreamQualityStore, SteadyStateRefitter, RefitReport, DeploymentDecision; print('Exports OK')"` -- Verify package exports

## Notes

- FastAPI is already in `pyproject.toml` as `fastapi>=0.110`. No new dependencies are needed.
- The feedback endpoint is part of Phase 3b (customer API) being built in parallel. The `POST /v1/feedback/tasks/{task_id}/outcomes` endpoint is defined here but will be mounted into the main FastAPI application by Phase 3b.
- The `DownstreamQualityStore` uses the same append-only JSONL pattern as `JudgmentStore` for consistency and auditability.
- The pairwise derivation algorithm (adjacent-pair comparison by composite quality signal) is a simplification. In production, more sophisticated derivation strategies (e.g., all-pairs with confidence weighting) could be used, but adjacent-pair is sufficient for the initial implementation and has fewer false-positive pair assignments.
- The `downstream_weight_multiplier` of 1.5 means downstream judgments are oversampled by repeating each judgment twice (round(1.5) = 2). This is a discrete approximation of continuous weighting. The fitter's log-likelihood is additive, so repeating judgments is equivalent to giving them higher weight.
- Per-specialty exponent divergence is expected and desirable. As evidence accumulates differently across specialties (e.g., translational vs drug_discovery), the fitted alpha/beta/gamma will naturally diverge.
- The `staging/` subdirectory for manual-gate deployments is created lazily. The operator reviews staged YAMLs and either promotes them to the main weights directory or rejects them.
- The weight-stability dashboard (Phase 1 Task 2.5) will consume the `RefitReport` objects to visualize drift over time. That integration is out of scope for this sub-spec.
