# Plan: Phase 3b — Customer-Facing Query API

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase3b-customer-api.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build the customer-facing query API layer for Aegis Phase 3. This sub-spec covers eight tasks from the Phase 3 master plan:

- **Task 1.3** (customer-facing query API): FastAPI REST API with `POST /v1/queries`, JWT auth, audit logging
- **Task 1.4** (LLM-backed query expansion): Constrained-generation expansion via Anthropic tool use with MetaMap fallback
- **Task 1.5** (result formatter): Evidence trails, variance bands, integrity disclosures, provenance pointers
- **Task 3.1** (rate-limit and abuse handling): Token-bucket rate limiting per customer, abuse detection
- **Task 3.2** (LLM hallucination detection): Expansion validator fail-closed against MeSH ontology
- **Task 3.3** (stale-data circuit breaker): Caveat injection when integrity sources lag beyond SLA
- **Task 4.1** (query throughput SLO): 100 qps sustained / 500 qps peak, <500ms p95
- **Task 4.3** (LLM cost monitoring): Per-customer LLM spend tracking with budget caps

## Objective

When this plan is complete:
1. A FastAPI application at `src/aegis/api/server.py` mounts all API routers and serves `POST /v1/queries`, `GET /v1/queries/{query_id}`, and `GET /v1/candidates/{uuid}/evidence`.
2. JWT-based authentication at `src/aegis/api/auth.py` scopes API tokens per-customer with optional per-cohort restrictions.
3. Token-bucket rate limiting at `src/aegis/api/rate_limit.py` enforces per-customer request budgets, returns 429 with `Retry-After`, and detects abuse patterns.
4. An LLM query expansion service at `src/aegis/query/llm_expansion.py` uses Anthropic tool use for constrained MeSH expansion with MetaMap fallback.
5. An expansion validator at `src/aegis/query/expansion_validator.py` rejects any LLM-proposed terms not in the MeSH ontology (fail-closed).
6. A query expansion cache at `src/aegis/query/cache.py` keyed on `(raw_query, mesh_version)` achieves >= 95% hit rate on warmed populations.
7. A result formatter at `src/aegis/api/formatter.py` produces per-candidate output with ROR-normalized affiliation, top-3 artifacts, component scores, variance band, integrity disclosures, and provenance pointer.
8. A stale-data circuit breaker at `src/aegis/api/staleness.py` adds informational caveats when integrity sources lag beyond SLA.
9. An audit log at `src/aegis/api/audit_log.py` records every request with customer, query, response candidate UUIDs, and served weight/integrity-rule versions.
10. LLM cost monitoring at `src/aegis/observability/llm_cost.py` tracks per-customer LLM spend with budget caps and graceful degradation.
11. A load-test harness at `tests/perf/test_throughput.py` sustains 100 qps for configurable duration with latency SLO verification.
12. All modules pass mypy strict, ruff lint, and have comprehensive unit tests.

## Problem Statement

Aegis Phases 0-2 built the scoring engine internally: quality prior, integrity gate, topical fit, recency, ranking formula, and multi-population support. Phase 3a adds continuous ingestion. Phase 3c adds feedback learning. But there is no customer-facing interface. Customers cannot query the system, results are not formatted for external consumption, there is no authentication or rate limiting, and the LLM query expansion from the program overview is not yet implemented. Without this API layer, the ranking engine cannot serve paying customers.

## Solution Approach

1. **API scaffold first**: Build the FastAPI application shell with JWT auth middleware, rate-limit middleware, and audit-log middleware. This is the foundation all other components plug into.

2. **Query expansion pipeline**: Build the LLM expansion service using Anthropic's tool-use API for constrained generation. The expansion validator checks every proposed term against the MeSH ontology and CPC/ChEMBL crosswalks. Invalid terms are rejected; the system falls back to MetaMap-only with a low-confidence flag. Results are cached per `(raw_query, mesh_version)`.

3. **Result formatting**: Build the formatter that takes a `RankedList` (from the existing `Ranker`) and produces the customer-facing response shape with variance bands (from `Bootstrap`), integrity disclosures (from `SoftDiscounts`), top-3 contributing artifacts with hyperlinks, and provenance pointers to weight and integrity-rule versions.

4. **Operational hardening**: Add the stale-data circuit breaker (checks `FreshnessMetrics` SLO compliance, injects caveats), abuse detection (pattern analysis on rate-limit violations), and LLM cost monitoring (per-customer token counting with budget enforcement).

5. **Performance verification**: Build the load-test harness targeting 100 qps sustained with <500ms p95.

## Relevant Files

### Existing Files (read-only context, do not modify unless noted)
- `src/aegis/scoring/rank.py` -- `Ranker`, `CandidateScoreInput`, existing ranking formula
- `src/aegis/scoring/result_format.py` -- `RankedCandidate`, `RankedList`, `ComponentBreakdown`, `ContributingArtifact`
- `src/aegis/scoring/variance.py` -- `Bootstrap`, `ScoreBand`, `BootstrapInput` for variance bands
- `src/aegis/scoring/quality_prior.py` -- `WeightVector`, `QualityPrior`, `load_weight_vector`
- `src/aegis/scoring/topical_fit.py` -- `TopicalFit` cosine similarity
- `src/aegis/scoring/recency.py` -- `Recency` time-decayed scoring
- `src/aegis/scoring/candidate_vector.py` -- `SparseVector`, `CandidateVectorBuilder`, `QueryVectorBuilder`
- `src/aegis/scoring/cache.py` -- `ScoreCache`, `CacheBackend`, `SQLiteCacheBackend`, `CacheKey`, `CachedScore`
- `src/aegis/integrity/hard_gate.py` -- `HardGate`, `HardGateResult`, `ArtifactRef`
- `src/aegis/integrity/soft_discounts.py` -- `SoftDiscounts`, `SoftDiscountResult`, `SoftDiscount`, `DiscountType`
- `src/aegis/integrity/contestability.py` -- `ContestabilityStore`, `OverrideRecord`, `OverrideAction`
- `src/aegis/storage/schema.py` -- `Candidate`, `MeshDescriptor`, `ArtifactRefBundle`, `StrongKeyType`
- `src/aegis/storage/candidate_store.py` -- `CandidateStore` DuckDB-backed API
- `src/aegis/sources/retry.py` -- `RetryPolicy`, `RetryConfig` for HTTP clients
- `src/aegis/observability/freshness.py` -- `FreshnessMetrics`, `SOURCE_SLOS` for staleness detection
- `src/aegis/taxonomy/cpc_mesh_xwalk.py` -- CPC-to-MeSH crosswalk for expansion validation
- `src/aegis/taxonomy/chembl_xwalk.py` -- ChEMBL-to-MeSH crosswalk for expansion validation
- `config/aegis/weights/translational_v1.yaml` -- Weight config pattern
- `pyproject.toml` -- Project configuration (FastAPI, uvicorn already dependencies)

### New Files
- `src/aegis/api/__init__.py` -- API package init
- `src/aegis/api/server.py` -- FastAPI application, router mounting, middleware
- `src/aegis/api/schemas.py` -- Request/response Pydantic models for query API
- `src/aegis/api/auth.py` -- JWT authentication and customer scoping
- `src/aegis/api/rate_limit.py` -- Token-bucket rate limiting and abuse detection
- `src/aegis/api/audit_log.py` -- Per-request audit logging
- `src/aegis/api/formatter.py` -- Result formatter with evidence trails and variance bands
- `src/aegis/api/staleness.py` -- Stale-data circuit breaker
- `src/aegis/api/schemas_test.py` -- Tests for request/response schemas
- `src/aegis/api/auth_test.py` -- Tests for JWT auth
- `src/aegis/api/rate_limit_test.py` -- Tests for rate limiting
- `src/aegis/api/formatter_test.py` -- Tests for result formatter
- `src/aegis/api/staleness_test.py` -- Tests for circuit breaker
- `src/aegis/api/server_test.py` -- Integration tests for API endpoints
- `src/aegis/query/__init__.py` -- Query package init
- `src/aegis/query/llm_expansion.py` -- LLM-backed query expansion
- `src/aegis/query/expansion_validator.py` -- MeSH ontology validator for expansions
- `src/aegis/query/cache.py` -- Query expansion cache
- `src/aegis/query/llm_expansion_test.py` -- Tests for LLM expansion
- `src/aegis/query/expansion_validator_test.py` -- Tests for expansion validator
- `src/aegis/query/cache_test.py` -- Tests for expansion cache
- `src/aegis/observability/llm_cost.py` -- LLM cost monitoring
- `src/aegis/observability/llm_cost_test.py` -- Tests for LLM cost monitoring
- `tests/perf/test_throughput.py` -- Load-test harness

## Implementation Phases

### Phase 1: Foundation
- Create API and query package scaffolds
- Build JWT auth module with customer scoping
- Build request/response schemas
- Build token-bucket rate limiter

### Phase 2: Core Implementation
- Build LLM query expansion service with constrained generation
- Build expansion validator (fail-closed against MeSH)
- Build query expansion cache
- Build result formatter with variance bands and integrity disclosures
- Build stale-data circuit breaker
- Build audit log module

### Phase 3: Integration & Polish
- Build FastAPI server wiring all components together
- Build LLM cost monitoring
- Build load-test harness
- Run full validation suite

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: API foundation -- auth, rate limiting, schemas, audit log, staleness circuit breaker, API server wiring
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Query expansion pipeline -- LLM expansion, expansion validator, expansion cache, LLM cost monitoring
  - Agent Type: general-purpose
- Builder
  - Name: builder-3
  - Role: Result formatter, load-test harness
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Design Updater
  - Name: design-updater
  - Role: Updates docs/design/api.md with code-aligned design decisions after build completes
  - Agent Type: design-updater

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build_v2`.
- Task descriptions must be **exhaustive** -- agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Every task MUST have an `Assigned To` matching a name in Team Members. This is enforced -- tasks without a valid `Assigned To` will not be claimed.
- Start with foundational work, then core implementation, then validation.

### 1. API + Query Package Scaffolds and Request/Response Schemas

- **Task ID**: api-schemas
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the API and query package scaffolds, and build all Pydantic request/response models for the customer-facing query API.

    ## What to do

    1. Create `src/aegis/api/__init__.py`:
       ```python
       """Aegis API -- customer-facing endpoints for querying and feedback."""

       from __future__ import annotations
       ```

    2. Create `src/aegis/query/__init__.py`:
       ```python
       """Aegis query -- LLM expansion, validation, and caching for query processing."""

       from __future__ import annotations
       ```

    3. Create `src/aegis/api/schemas.py` with the following models:

       ```python
       """Request and response Pydantic models for the Aegis query API."""

       from __future__ import annotations

       from datetime import datetime
       from enum import StrEnum

       from pydantic import BaseModel, ConfigDict, Field, field_validator
       ```

       **Request models:**

       a) `CutoffStrategy` (StrEnum):
          - `top_k = "top_k"` -- Return top K candidates
          - `score_threshold = "score_threshold"` -- Return candidates above score threshold

       b) `QueryRequest` (Pydantic BaseModel, frozen):
          - `task_description: str` -- Free-text task description from the customer
          - `mesh_override: list[str] | None = None` -- Optional explicit MeSH terms (bypass expansion)
          - `cohort_filter: str | None = None` -- Optional cohort restriction (e.g., "translational", "drug_discovery", "clinician")
          - `k: int = Field(default=50, ge=1, le=500)` -- Number of results to return
          - `cutoff_strategy: CutoffStrategy = CutoffStrategy.top_k`
          - `score_threshold: float | None = None` -- Threshold when using score_threshold strategy
          - `include_variance_bands: bool = True` -- Whether to include score variance bands
          - Add a `field_validator` on `task_description` that rejects empty strings or strings shorter than 10 characters. Raise `ValueError("Task description must be at least 10 characters")`.

       c) `ArtifactLink` (Pydantic BaseModel, frozen):
          - `artifact_type: str` -- "pmid", "nct_id", "patent_id", "grant_id"
          - `identifier: str` -- The actual ID
          - `title: str`
          - `url: str` -- Hyperlink to the artifact
          - `contribution_score: float`

       d) `IntegrityDisclosure` (Pydantic BaseModel, frozen):
          - `discount_type: str` -- From DiscountType enum value
          - `factor: float` -- The multiplicative discount applied
          - `detail: str` -- Human-readable explanation

       e) `VarianceBand` (Pydantic BaseModel, frozen):
          - `low: float`
          - `high: float`
          - `median: float`

       f) `CandidateResult` (Pydantic BaseModel, frozen):
          - `rank: int`
          - `candidate_uuid: str`
          - `candidate_name: str`
          - `affiliation: str` -- ROR-normalized current affiliation
          - `affiliation_country: str | None`
          - `score: float`
          - `component_scores: dict[str, float]` -- {"quality_prior": ..., "topical_fit": ..., "recency": ..., "integrity": ...}
          - `top_artifacts: list[ArtifactLink]` -- Top-3 contributing artifacts with hyperlinks
          - `linkage_confidence: float`
          - `variance_band: VarianceBand | None` -- Score confidence interval
          - `integrity_disclosures: list[IntegrityDisclosure]` -- Any soft discounts applied (never silent)
          - `specialty: str | None` -- Specialty annotation if available
          - `evidence_trail: list[str]` -- Evidence provenance chain

       g) `ExpansionInfo` (Pydantic BaseModel, frozen):
          - `original_query: str`
          - `expanded_mesh_terms: list[str]`
          - `expansion_method: str` -- "llm", "metamap", "override", "llm_fallback_metamap"
          - `low_confidence: bool = False` -- True if LLM expansion failed and MetaMap fallback was used
          - `cached: bool = False` -- True if expansion was served from cache

       h) `StalenessWarning` (Pydantic BaseModel, frozen):
          - `source: str` -- Which integrity source is stale
          - `last_updated: datetime` -- When it was last refreshed
          - `sla_hours: float` -- The expected SLA
          - `message: str` -- Human-readable caveat

       i) `QueryResponse` (Pydantic BaseModel, frozen):
          - `query_id: str` -- Unique query identifier for audit trail
          - `timestamp: datetime`
          - `candidates: list[CandidateResult]`
          - `total_candidates_evaluated: int`
          - `excluded_count: int` -- Candidates removed by integrity gate
          - `expansion_info: ExpansionInfo`
          - `staleness_warnings: list[StalenessWarning]` -- Circuit breaker caveats
          - `weight_version: int` -- Served weight version for reproducibility
          - `integrity_rule_version: str` -- Served integrity rule version
          - `metadata: dict[str, str]`

       j) `ErrorResponse` (Pydantic BaseModel, frozen):
          - `error: str`
          - `detail: str`
          - `retry_after: int | None = None` -- Seconds until retry (for 429)

    4. Create `src/aegis/api/schemas_test.py` with tests:

       a) `test_query_request_defaults`: Create QueryRequest with only task_description="Evaluate JAK2 inhibitor candidates for kinase selectivity screening". Verify k=50, cutoff_strategy=top_k, include_variance_bands=True.

       b) `test_query_request_short_description`: QueryRequest with task_description="short" should raise ValidationError.

       c) `test_query_request_empty_description`: QueryRequest with task_description="" should raise ValidationError.

       d) `test_query_request_custom_k`: QueryRequest with k=100 should work. k=0 should raise ValidationError. k=501 should raise ValidationError.

       e) `test_candidate_result_model`: Create a full CandidateResult with all fields populated including variance_band and integrity_disclosures. Verify model is frozen.

       f) `test_query_response_model`: Create a full QueryResponse with 3 candidates, expansion info, and staleness warnings. Verify all fields serialize correctly via model_dump_json().

       g) `test_artifact_link_model`: Create ArtifactLink for a PMID with URL. Verify fields.

       h) `test_staleness_warning_model`: Create StalenessWarning. Verify fields.

       Use `from __future__ import annotations`, `import pytest`, `from pydantic import ValidationError`. Follow the Pydantic frozen model pattern used throughout the codebase.

    ## Files to create
    - `src/aegis/api/__init__.py`
    - `src/aegis/query/__init__.py`
    - `src/aegis/api/schemas.py`
    - `src/aegis/api/schemas_test.py`

    ## Files to modify
    None.

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `StrEnum` for enumerations (same pattern as `StrongKeyType` in `src/aegis/storage/schema.py`)
    - `field_validator` from Pydantic v2 for validation rules
    - Logger at module level: `logger = logging.getLogger(__name__)`
    - Test files colocated with source (same pattern as `src/aegis/scoring/rank_test.py`)

    ## Acceptance criteria
    - `src/aegis/api/__init__.py` exists and is importable
    - `src/aegis/query/__init__.py` exists and is importable
    - `src/aegis/api/schemas.py` exports QueryRequest, QueryResponse, CandidateResult, ArtifactLink, IntegrityDisclosure, VarianceBand, ExpansionInfo, StalenessWarning, ErrorResponse, CutoffStrategy
    - QueryRequest validation: rejects short/empty task_description, enforces k bounds
    - All 8 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/schemas_test.py -v && uv run mypy src/aegis/api/schemas.py && uv run ruff check src/aegis/api/schemas.py src/aegis/api/__init__.py src/aegis/query/__init__.py
    ```

### 2. JWT Authentication Module

- **Task ID**: jwt-auth
- **Role**: builder
- **Depends On**: api-schemas
- **Assigned To**: builder-1
- **Description**: |
    Build the JWT authentication module for customer-facing API access with per-customer scoping and optional per-cohort restrictions.

    ## What to do

    1. Add `pyjwt>=2.8` to the `dependencies` list in `pyproject.toml`. The current dependencies list starts with:
       ```
       dependencies = [
           "biopython>=1.83",
           "httpx>=0.27",
           ...
       ]
       ```
       Add `"pyjwt>=2.8",` to this list (maintain alphabetical order -- insert after `"prometheus-client>=0.20",`). Then run `uv lock` to update the lock file.

    2. Create `src/aegis/api/auth.py`:

       ```python
       """JWT authentication for the Aegis customer-facing API.

       Provides token creation, validation, and FastAPI dependency injection
       for per-customer scoped authentication.
       """

       from __future__ import annotations

       import logging
       import os
       from datetime import UTC, datetime, timedelta
       from typing import Annotated

       import jwt
       from fastapi import Depends, HTTPException, status
       from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       _DEFAULT_SECRET = "aegis-dev-secret-change-in-production"
       _ALGORITHM = "HS256"
       _DEFAULT_EXPIRY_HOURS = 24

       _security = HTTPBearer()
       ```

       **Models:**

       a) `CustomerClaims` (Pydantic BaseModel, frozen):
          - `customer_id: str` -- Unique customer identifier
          - `customer_name: str` -- Human-readable name
          - `allowed_cohorts: list[str] | None = None` -- If set, restricts queries to these cohorts only. None = all cohorts.
          - `rate_limit_qps: int = 10` -- Per-customer rate limit in queries per second
          - `llm_budget_cents: int = 1000` -- Per-customer LLM cost budget in cents per day

       b) `TokenPayload` (Pydantic BaseModel, frozen):
          - `sub: str` -- Subject (customer_id)
          - `customer_name: str`
          - `allowed_cohorts: list[str] | None`
          - `rate_limit_qps: int`
          - `llm_budget_cents: int`
          - `exp: datetime` -- Expiry timestamp
          - `iat: datetime` -- Issued-at timestamp

       **Functions:**

       a) `create_token(claims: CustomerClaims, *, secret: str | None = None, expiry_hours: int = _DEFAULT_EXPIRY_HOURS) -> str`:
          - Build a JWT with the customer claims as payload.
          - Use `secret or os.environ.get("AEGIS_JWT_SECRET", _DEFAULT_SECRET)`.
          - Set `exp` to now + expiry_hours, `iat` to now, `sub` to claims.customer_id.
          - Return the encoded JWT string.

       b) `decode_token(token: str, *, secret: str | None = None) -> TokenPayload`:
          - Decode and validate the JWT. Use same secret resolution as create_token.
          - On `jwt.ExpiredSignatureError`: raise `HTTPException(status_code=401, detail="Token expired")`.
          - On `jwt.InvalidTokenError`: raise `HTTPException(status_code=401, detail="Invalid token")`.
          - Return a `TokenPayload` from the decoded claims.

       c) `get_current_customer(credentials: Annotated[HTTPAuthorizationCredentials, Depends(_security)]) -> TokenPayload`:
          - This is the FastAPI dependency. Extract the token from credentials.credentials.
          - Call decode_token and return the result.
          - This allows endpoints to declare `customer: TokenPayload = Depends(get_current_customer)`.

       d) `require_cohort_access(customer: TokenPayload, cohort: str | None) -> None`:
          - If customer.allowed_cohorts is not None and cohort is not None:
            - If cohort not in customer.allowed_cohorts: raise HTTPException(403, "Access denied for cohort: {cohort}")
          - Otherwise: pass (no restriction).

    3. Create `src/aegis/api/auth_test.py` with tests:

       a) `test_create_and_decode_token`: Create a token with CustomerClaims(customer_id="cust-1", customer_name="Test Corp"), decode it, verify sub="cust-1", customer_name="Test Corp".

       b) `test_expired_token`: Create a token with expiry_hours=0 (or manually set exp in the past using a custom secret and jwt.encode). Verify decode_token raises HTTPException with status 401.

       c) `test_invalid_token`: Call decode_token with garbage string. Verify HTTPException 401.

       d) `test_wrong_secret`: Create token with secret="secret-a", decode with secret="secret-b". Verify HTTPException 401.

       e) `test_cohort_restriction_allowed`: Token with allowed_cohorts=["translational"]. Call require_cohort_access with cohort="translational". Should not raise.

       f) `test_cohort_restriction_denied`: Token with allowed_cohorts=["translational"]. Call require_cohort_access with cohort="drug_discovery". Should raise HTTPException 403.

       g) `test_cohort_restriction_none_allows_all`: Token with allowed_cohorts=None. Call require_cohort_access with cohort="anything". Should not raise.

       h) `test_customer_claims_defaults`: Create CustomerClaims with only customer_id and customer_name. Verify rate_limit_qps=10, llm_budget_cents=1000, allowed_cohorts=None.

       i) `test_token_contains_all_claims`: Create token with all fields set (including allowed_cohorts, custom rate_limit_qps). Decode and verify all fields are present.

       Use `import pytest`, `from fastapi import HTTPException`. Do NOT use FastAPI TestClient -- just test the functions directly.

    ## Files to create
    - `src/aegis/api/auth.py`
    - `src/aegis/api/auth_test.py`

    ## Files to modify
    - `pyproject.toml` -- Add `pyjwt>=2.8` dependency

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - FastAPI dependency injection pattern with `Depends`
    - `HTTPBearer` security scheme for JWT bearer tokens
    - Logger at module level

    ## Acceptance criteria
    - `pyjwt>=2.8` added to pyproject.toml dependencies
    - `src/aegis/api/auth.py` exports create_token, decode_token, get_current_customer, require_cohort_access, CustomerClaims, TokenPayload
    - Token creation and validation works with HS256
    - Expired tokens return 401
    - Invalid tokens return 401
    - Cohort restrictions enforced (403 on mismatch)
    - All 9 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run uv lock && uv run pytest src/aegis/api/auth_test.py -v && uv run mypy src/aegis/api/auth.py && uv run ruff check src/aegis/api/auth.py
    ```

### 3. Token-Bucket Rate Limiter and Abuse Detection

- **Task ID**: rate-limiter
- **Role**: builder
- **Depends On**: jwt-auth
- **Assigned To**: builder-1
- **Description**: |
    Build the token-bucket rate limiter with per-customer enforcement and abuse pattern detection.

    ## What to do

    1. Create `src/aegis/api/rate_limit.py`:

       ```python
       """Token-bucket rate limiting with per-customer enforcement and abuse detection.

       Enforces per-customer QPS limits using the token-bucket algorithm.
       Detects abuse patterns (e.g., database scraping via systematic queries)
       and triggers automated throttling with admin alerts.
       """

       from __future__ import annotations

       import logging
       import time
       from collections import defaultdict
       from dataclasses import dataclass, field

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Models:**

       a) `RateLimitResult` (Pydantic BaseModel, frozen):
          - `allowed: bool`
          - `remaining_tokens: float`
          - `retry_after_seconds: float | None` -- Seconds until a token is available (only set when not allowed)
          - `customer_id: str`

       b) `AbuseAlert` (Pydantic BaseModel, frozen):
          - `customer_id: str`
          - `pattern: str` -- "high_frequency_burst", "systematic_enumeration", "repeated_identical"
          - `detail: str`
          - `timestamp: float` -- epoch seconds
          - `recommended_action: str` -- "throttle", "review", "block"

       **Classes:**

       a) `TokenBucket`:
          - `__init__(self, *, rate: float, capacity: float) -> None`: rate = tokens per second, capacity = max burst size. Initialize `self._tokens = capacity`, `self._last_refill = time.monotonic()`.
          - `consume(self, tokens: float = 1.0) -> RateLimitResult`: Refill tokens based on elapsed time. If enough tokens: consume and return allowed=True. If not: return allowed=False with retry_after_seconds = (tokens - self._tokens) / rate.
          - `_refill(self) -> None`: Add `(now - last_refill) * rate` tokens, capped at capacity.

       b) `AbuseDetector`:
          - `__init__(self, *, window_seconds: float = 60.0, burst_threshold: int = 100, identical_threshold: int = 10) -> None`
          - Internal state: `self._request_timestamps: defaultdict[str, list[float]]` (customer_id -> list of timestamps), `self._query_hashes: defaultdict[str, defaultdict[str, int]]` (customer_id -> {query_hash -> count}).
          - `record_request(self, *, customer_id: str, query_hash: str) -> AbuseAlert | None`:
            - Append timestamp, prune timestamps outside window.
            - Check burst: if requests in window > burst_threshold, return AbuseAlert with pattern="high_frequency_burst".
            - Check identical queries: if same query_hash count > identical_threshold in window, return AbuseAlert with pattern="repeated_identical".
            - Otherwise return None.
          - `_prune_window(self, customer_id: str) -> None`: Remove timestamps older than window_seconds.

       c) `RateLimiterRegistry`:
          - `__init__(self) -> None`: Stores `self._buckets: dict[str, TokenBucket]` keyed by customer_id, `self._detector = AbuseDetector()`, `self._alerts: list[AbuseAlert] = []`.
          - `get_or_create(self, *, customer_id: str, rate: float, capacity: float) -> TokenBucket`: Return existing bucket or create new one.
          - `check(self, *, customer_id: str, rate: float, capacity: float, query_hash: str = "") -> RateLimitResult`: Get bucket, consume 1 token. Also record request in abuse detector. If abuse alert, append to alerts and log warning. Return the RateLimitResult (rate limit and abuse are independent -- rate limit is the gating decision).
          - `get_alerts(self) -> list[AbuseAlert]`: Return and clear pending alerts.
          - `stats(self) -> dict[str, dict[str, float]]`: Return per-customer stats (remaining tokens, total requests in window).

    2. Create `src/aegis/api/rate_limit_test.py` with tests:

       a) `test_token_bucket_allows_within_rate`: Create TokenBucket(rate=10.0, capacity=10.0). 10 consecutive consumes should all be allowed.

       b) `test_token_bucket_denies_over_capacity`: Create TokenBucket(rate=1.0, capacity=2.0). First 2 consumes allowed. 3rd denied with retry_after > 0.

       c) `test_token_bucket_refills`: Create TokenBucket(rate=100.0, capacity=1.0). Consume 1. Use `time.sleep(0.02)` to allow refill. Consume again should be allowed.

       d) `test_abuse_detector_burst`: Create AbuseDetector(burst_threshold=5, window_seconds=10.0). Record 6 requests in rapid succession for same customer. 6th should return AbuseAlert with pattern="high_frequency_burst".

       e) `test_abuse_detector_identical_queries`: Create AbuseDetector(identical_threshold=3). Record 4 requests with same query_hash. 4th should return AbuseAlert with pattern="repeated_identical".

       f) `test_abuse_detector_no_abuse`: Record 3 requests with different query_hashes, all below thresholds. All should return None.

       g) `test_rate_limiter_registry_creates_bucket`: Create RateLimiterRegistry. Call check twice for same customer. Verify both return RateLimitResult.

       h) `test_rate_limiter_registry_429_scenario`: Create registry. Create a bucket with rate=1.0, capacity=1.0 for customer "cust-1". Check once (allowed). Check again immediately (denied with retry_after).

       i) `test_rate_limiter_alerts_collected`: Registry with AbuseDetector(burst_threshold=2). Record 3 requests. get_alerts() should return 1 alert. Calling get_alerts() again returns empty.

    ## Files to create
    - `src/aegis/api/rate_limit.py`
    - `src/aegis/api/rate_limit_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for result models
    - `dataclass` for internal mutable state (TokenBucket)
    - `defaultdict` for per-customer tracking
    - `time.monotonic()` for timing (not wall-clock)

    ## Acceptance criteria
    - Token-bucket correctly allows within rate and denies over capacity
    - Tokens refill over time
    - Abuse detection catches burst and identical-query patterns
    - RateLimiterRegistry manages per-customer buckets
    - retry_after_seconds is set correctly when denied
    - All 9 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/rate_limit_test.py -v && uv run mypy src/aegis/api/rate_limit.py && uv run ruff check src/aegis/api/rate_limit.py
    ```

### 4. LLM Query Expansion Service

- **Task ID**: llm-expansion
- **Role**: builder
- **Depends On**: api-schemas
- **Assigned To**: builder-2
- **Description**: |
    Build the LLM-backed query expansion service using Anthropic tool use for constrained MeSH generation with MetaMap fallback.

    ## What to do

    1. Add `anthropic>=0.25` to the `dependencies` list in `pyproject.toml`. Insert alphabetically (before `"biopython>=1.83"`). Then run `uv lock`.

    2. Create `src/aegis/query/llm_expansion.py`:

       ```python
       """LLM-backed query expansion using Anthropic tool use for constrained MeSH generation.

       Implements the program overview section 10 pattern: deterministic MetaMap pass first,
       then LLM expansion constrained to MeSH vocabulary for synonyms, related subtopics,
       and disambiguation. Falls back to MetaMap-only on LLM failure.
       """

       from __future__ import annotations

       import hashlib
       import logging
       import os
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       _DEFAULT_MODEL = "claude-sonnet-4-20250514"
       ```

       **Models:**

       a) `ExpandedQuery` (Pydantic BaseModel, frozen):
          - `original_query: str`
          - `mesh_terms: list[str]` -- Final expanded MeSH terms
          - `expansion_method: str` -- "llm", "metamap", "override", "llm_fallback_metamap"
          - `low_confidence: bool` -- True if LLM expansion was rejected/failed
          - `raw_llm_terms: list[str] | None` -- LLM-proposed terms before validation (for debugging)
          - `rejected_terms: list[str]` -- Terms rejected by validator
          - `cached: bool`
          - `cost_tokens: int` -- Total tokens consumed (input + output)
          - `expanded_at: datetime`

       b) `MetaMapResult` (Pydantic BaseModel, frozen):
          - `mesh_terms: list[str]`
          - `confidence: float` -- 0-1 confidence score

       c) `LlmExpansionConfig` (Pydantic BaseModel, frozen):
          - `model: str = "claude-sonnet-4-20250514"`
          - `max_terms: int = 20` -- Maximum MeSH terms to request from LLM
          - `temperature: float = 0.0` -- Deterministic
          - `max_tokens: int = 1024`
          - `timeout_seconds: float = 10.0`

       **Classes:**

       a) `MetaMapExpander`:
          - `__init__(self) -> None`: Stub implementation for MetaMap.
          - `expand(self, query: str) -> MetaMapResult`: Stub that extracts simple terms from the query. For the initial implementation, split the query into words, filter to words > 3 chars, capitalize, and return as mesh_terms with confidence=0.5. This is a placeholder -- real MetaMap integration is out of scope.
          - IMPORTANT: This is a stub. Comment it clearly as such. Real MetaMap integration would use the MetaMap API or UMLS REST API.

       b) `LlmQueryExpander`:
          - `__init__(self, *, config: LlmExpansionConfig | None = None, validator: Any = None) -> None`:
            - `self._config = config or LlmExpansionConfig()`
            - `self._validator = validator` -- The expansion validator (injected, type hint as `Any` to avoid circular import; will be `ExpansionValidator` from task 5)
            - `self._metamap = MetaMapExpander()`
            - `self._client: Any = None` -- Lazy-initialized Anthropic client

          - `_get_client(self) -> Any`:
            - Lazy-initialize: `if self._client is None: from anthropic import Anthropic; self._client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))`.
            - Return client.

          - `_build_tool_schema(self) -> dict`:
            - Return the Anthropic tool-use schema for constrained MeSH expansion:
            ```python
            return {
                "name": "expand_mesh_terms",
                "description": "Expand a biomedical query into relevant MeSH descriptor terms. Return ONLY valid MeSH descriptors from the NLM Medical Subject Headings vocabulary.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "mesh_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of valid MeSH descriptor terms relevant to the query. Each must be an exact MeSH descriptor heading.",
                            "maxItems": self._config.max_terms,
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of why these terms were selected.",
                        },
                    },
                    "required": ["mesh_terms", "reasoning"],
                },
            }
            ```

          - `async def expand_via_llm(self, query: str) -> tuple[list[str], int]`:
            - Call Anthropic API with the tool schema. Use `self._get_client().messages.create(...)` with `model=self._config.model`, `max_tokens=self._config.max_tokens`, `temperature=self._config.temperature`, `tools=[self._build_tool_schema()]`, `tool_choice={"type": "tool", "name": "expand_mesh_terms"}`.
            - System prompt: "You are a biomedical query expansion assistant. Given a research task description, identify the most relevant MeSH (Medical Subject Headings) descriptor terms. Only use exact MeSH descriptor headings from the NLM vocabulary. Include synonyms, related concepts, and relevant subtopics."
            - User message: f"Expand this research task into MeSH terms: {query}"
            - Parse the tool_use content block to extract mesh_terms list.
            - Count total tokens from response.usage (input_tokens + output_tokens).
            - Return (mesh_terms, total_tokens).
            - On any exception (API error, timeout, parse error): log warning and return ([], 0).

          - `def expand(self, query: str, *, mesh_override: list[str] | None = None) -> ExpandedQuery`:
            - If mesh_override is provided and non-empty: return immediately with expansion_method="override", the override terms, low_confidence=False, cost_tokens=0.
            - Step 1: MetaMap pass. `metamap_result = self._metamap.expand(query)`.
            - Step 2: Try LLM expansion. Use `asyncio.run()` to call `expand_via_llm(query)` synchronously (the API server runs sync endpoints). Catch all exceptions.
            - If LLM returns terms:
              - If validator is available: validate terms via `self._validator.validate(terms)`. Keep only valid terms. Track rejected terms.
              - If all LLM terms rejected or LLM returned empty: fall back to MetaMap. Set expansion_method="llm_fallback_metamap", low_confidence=True.
              - If some valid LLM terms: merge with MetaMap terms (LLM terms first, deduplicated). Set expansion_method="llm".
            - If LLM fails entirely: use MetaMap terms. Set expansion_method="metamap", low_confidence=True if MetaMap confidence < 0.7.
            - Return ExpandedQuery with all fields populated.

       **IMPORTANT DESIGN NOTES**:
       - The expand() method is synchronous because FastAPI endpoints in this codebase are sync (matching Phase 3c feedback.py pattern).
       - asyncio.run() inside expand() creates a new event loop for the Anthropic call. If the caller is already in an async context, use a thread pool instead. For simplicity in the initial implementation, wrap with `import asyncio; try: loop = asyncio.get_event_loop(); if loop.is_running(): import concurrent.futures; with concurrent.futures.ThreadPoolExecutor() as pool: result = pool.submit(asyncio.run, self.expand_via_llm(query)).result(timeout=self._config.timeout_seconds) else: result = asyncio.run(self.expand_via_llm(query)) except RuntimeError: result = asyncio.run(self.expand_via_llm(query))`.
       - Actually, simplify: use `httpx` sync client wrapping instead. The cleanest approach: since the Anthropic SDK supports sync calls natively, use `self._get_client().messages.create(...)` directly (it's synchronous by default). No asyncio needed. Make `expand_via_llm` a regular sync method returning `tuple[list[str], int]`.

    3. Create `src/aegis/query/llm_expansion_test.py` with tests:

       a) `test_metamap_expander_stub`: Call MetaMapExpander().expand("evaluate JAK2 kinase inhibitor candidates"). Verify returns MetaMapResult with mesh_terms non-empty.

       b) `test_expand_with_override`: Call LlmQueryExpander().expand("test query", mesh_override=["Neoplasms", "Drug Therapy"]). Verify expansion_method="override", mesh_terms matches override, cost_tokens=0.

       c) `test_expand_metamap_fallback_no_api_key`: Create LlmQueryExpander() with no ANTHROPIC_API_KEY set. Call expand("evaluate JAK2 inhibitors"). LLM should fail gracefully. Verify expansion_method is "metamap" or "llm_fallback_metamap", low_confidence may be True, cost_tokens=0.

       d) `test_expanded_query_model`: Create an ExpandedQuery with all fields. Verify model is frozen and serializes.

       e) `test_llm_expansion_config_defaults`: Verify LlmExpansionConfig() has expected defaults.

       f) `test_build_tool_schema`: Create LlmQueryExpander(), call _build_tool_schema(). Verify it returns a dict with "name"="expand_mesh_terms" and "input_schema" with "mesh_terms" property.

       g) `test_expand_empty_override_uses_expansion`: Call expand("test query at least 10 chars", mesh_override=[]). Should NOT use override path (empty list). Should go through normal expansion.

       IMPORTANT: Tests must NOT require a real Anthropic API key. Test the fallback behavior and model construction. Use monkeypatch to mock the Anthropic client if needed.

    ## Files to create
    - `src/aegis/query/llm_expansion.py`
    - `src/aegis/query/llm_expansion_test.py`

    ## Files to modify
    - `pyproject.toml` -- Add `anthropic>=0.25` dependency

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - Lazy client initialization pattern (same as used in `src/aegis/integrity/llm_triage.py`)
    - Logger at module level
    - httpx-based HTTP clients (consistent with source clients in `src/aegis/sources/`)
    - Graceful degradation on LLM failure (never crash, always fall back)

    ## Acceptance criteria
    - `src/aegis/query/llm_expansion.py` exports LlmQueryExpander, ExpandedQuery, MetaMapExpander, MetaMapResult, LlmExpansionConfig
    - Design assertion: `LlmQueryExpander.expand(raw_query) -> ExpandedQuery`
    - Override path returns immediately without LLM call
    - LLM failure falls back to MetaMap gracefully
    - Tool schema constrains output to MeSH terms
    - All 7 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run uv lock && uv run pytest src/aegis/query/llm_expansion_test.py -v && uv run mypy src/aegis/query/llm_expansion.py && uv run ruff check src/aegis/query/llm_expansion.py
    ```

### 5. Expansion Validator (Fail-Closed Against MeSH Ontology)

- **Task ID**: expansion-validator
- **Role**: builder
- **Depends On**: llm-expansion
- **Assigned To**: builder-2
- **Description**: |
    Build the expansion validator that checks every LLM-proposed term against the MeSH ontology and CPC/ChEMBL crosswalks. Fail-closed: anything not in the ontology is rejected.

    ## What to do

    1. Create `src/aegis/query/expansion_validator.py`:

       ```python
       """Expansion validator: fail-closed MeSH ontology validation for LLM query expansion.

       Validates every LLM-proposed MeSH term against:
       1. MeSH descriptor vocabulary (primary check)
       2. CPC-to-MeSH crosswalk (secondary)
       3. ChEMBL-to-MeSH crosswalk (tertiary)

       Any term not found in any vocabulary is REJECTED. This is fail-closed:
       we prefer missing a valid expansion over accepting an invented term.
       """

       from __future__ import annotations

       import logging
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Models:**

       a) `ValidationResult` (Pydantic BaseModel, frozen):
          - `term: str`
          - `valid: bool`
          - `source: str | None` -- Which vocabulary confirmed it: "mesh", "cpc_xwalk", "chembl_xwalk", None if invalid
          - `normalized: str | None` -- Normalized form of the term if found

       b) `ValidationReport` (Pydantic BaseModel, frozen):
          - `total_terms: int`
          - `valid_count: int`
          - `rejected_count: int`
          - `valid_terms: list[str]`
          - `rejected_terms: list[str]`
          - `details: list[ValidationResult]`
          - `validated_at: datetime`

       c) `ValidatorStats` (Pydantic BaseModel, frozen):
          - `total_validations: int`
          - `total_terms_checked: int`
          - `total_rejected: int`
          - `rejection_rate: float` -- rejected / checked

       **Class: `ExpansionValidator`**

       ```python
       class ExpansionValidator:
           """Fail-closed validator for LLM-expanded MeSH terms.

           Checks proposed terms against the MeSH vocabulary and taxonomy
           crosswalks. Rejects anything not found.
           """

           def __init__(
               self,
               *,
               mesh_descriptors: set[str] | None = None,
               cpc_mesh_terms: set[str] | None = None,
               chembl_mesh_terms: set[str] | None = None,
           ) -> None:
               # If not provided, use empty sets (in production, these are loaded from
               # the taxonomy modules at startup)
               self._mesh = mesh_descriptors or set()
               self._cpc = cpc_mesh_terms or set()
               self._chembl = chembl_mesh_terms or set()
               self._total_validations = 0
               self._total_terms = 0
               self._total_rejected = 0
       ```

       **Methods:**

       a) `_normalize_term(self, term: str) -> str`:
          - Strip whitespace, title-case. Return normalized.

       b) `_check_term(self, term: str) -> ValidationResult`:
          - Normalize the term.
          - Check self._mesh (case-insensitive lookup by normalizing both sides). If found: return valid=True, source="mesh".
          - Check self._cpc. If found: return valid=True, source="cpc_xwalk".
          - Check self._chembl. If found: return valid=True, source="chembl_xwalk".
          - Otherwise: return valid=False, source=None.

       c) `validate(self, terms: list[str]) -> ValidationReport`:
          - Validate each term via _check_term.
          - Build and return ValidationReport.
          - Update stats counters.

       d) `validate_single(self, term: str) -> bool`:
          - Convenience method: return True if term is valid.

       e) `get_stats(self) -> ValidatorStats`:
          - Return current stats.

       **IMPORTANT**: For case-insensitive matching, store all vocabulary terms as lowercase in __init__ and compare normalized lowercase terms. This avoids issues with MeSH casing variations.

    2. Create `src/aegis/query/expansion_validator_test.py` with tests:

       a) `test_valid_mesh_term`: Create validator with mesh_descriptors={"Neoplasms", "Protein Kinases", "Drug Therapy"}. Validate ["Neoplasms"]. All valid.

       b) `test_invalid_term_rejected`: Validator with mesh_descriptors={"Neoplasms"}. Validate ["Neoplasms", "MadeUpTerm123"]. First valid, second rejected. Report: valid_count=1, rejected_count=1.

       c) `test_case_insensitive`: Validator with mesh_descriptors={"Neoplasms"}. Validate ["neoplasms", "NEOPLASMS"]. Both should be valid.

       d) `test_cpc_xwalk_fallback`: Validator with mesh_descriptors=set(), cpc_mesh_terms={"Organic Chemistry"}. Validate ["Organic Chemistry"]. Valid with source="cpc_xwalk".

       e) `test_chembl_xwalk_fallback`: Validator with mesh_descriptors=set(), cpc_mesh_terms=set(), chembl_mesh_terms={"Imatinib"}. Validate ["Imatinib"]. Valid with source="chembl_xwalk".

       f) `test_fail_closed_empty_vocab`: Validator with all empty sets. Validate ["Anything"]. Rejected.

       g) `test_validate_single`: Validator with mesh_descriptors={"Neoplasms"}. validate_single("Neoplasms") returns True. validate_single("Fake") returns False.

       h) `test_stats_tracking`: Validator. Validate 5 terms (3 valid, 2 rejected). Stats: total_terms_checked=5, total_rejected=2.

       i) `test_validation_report_structure`: Validate terms, check ValidationReport has all fields, details list matches term count.

       j) `test_whitespace_handling`: Validate [" Neoplasms ", "  Drug Therapy  "]. Both should match if in vocabulary.

    ## Files to create
    - `src/aegis/query/expansion_validator.py`
    - `src/aegis/query/expansion_validator_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - Case-insensitive matching via lowercase normalization
    - Fail-closed design: anything not in vocabulary is rejected

    ## Acceptance criteria
    - ExpansionValidator validates terms against MeSH, CPC crosswalk, and ChEMBL crosswalk
    - Fail-closed: unknown terms rejected
    - Case-insensitive matching works
    - Stats tracking accurate
    - Per-day rejection rate metric trackable
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/query/expansion_validator_test.py -v && uv run mypy src/aegis/query/expansion_validator.py && uv run ruff check src/aegis/query/expansion_validator.py
    ```

### 6. Query Expansion Cache

- **Task ID**: expansion-cache
- **Role**: builder
- **Depends On**: llm-expansion
- **Assigned To**: builder-2
- **Description**: |
    Build the query expansion cache keyed on (raw_query, mesh_version) to avoid redundant LLM calls and achieve >= 95% hit rate on warmed populations.

    ## What to do

    1. Create `src/aegis/query/cache.py`:

       ```python
       """Query expansion cache: per-(query, mesh_version) caching of LLM expansions.

       Aggressively caches expansion results to minimize LLM costs.
       Target: >= 95% hit rate on warmed query populations.
       """

       from __future__ import annotations

       import hashlib
       import json
       import logging
       import sqlite3
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Models:**

       a) `ExpansionCacheKey` (Pydantic BaseModel, frozen):
          - `raw_query: str`
          - `mesh_version: str` -- Version of the MeSH vocabulary used
          - `def to_hash(self) -> str`: Return SHA-256 hex of `f"{self.raw_query}|{self.mesh_version}"`.

       b) `ExpansionCacheEntry` (Pydantic BaseModel, frozen):
          - `key_hash: str`
          - `raw_query: str`
          - `mesh_version: str`
          - `mesh_terms: list[str]` -- Cached expanded terms
          - `expansion_method: str`
          - `low_confidence: bool`
          - `cached_at: str` -- ISO datetime

       c) `ExpansionCacheStats` (Pydantic BaseModel, frozen):
          - `total_requests: int`
          - `hits: int`
          - `misses: int`
          - `hit_rate: float`
          - `entry_count: int`

       **Class: `ExpansionCache`**

       - `__init__(self, *, db_path: str = ":memory:") -> None`:
         - Initialize SQLite connection. Create table:
           `CREATE TABLE IF NOT EXISTS expansion_cache (key_hash TEXT PRIMARY KEY, data TEXT, created_at TEXT)`.
         - Initialize hit/miss counters.

       - `get(self, key: ExpansionCacheKey) -> ExpansionCacheEntry | None`:
         - Look up by key_hash. On hit: increment hits, return entry. On miss: increment misses, return None.

       - `put(self, key: ExpansionCacheKey, *, mesh_terms: list[str], expansion_method: str, low_confidence: bool) -> None`:
         - Serialize and store. Use INSERT OR REPLACE.

       - `invalidate(self, key: ExpansionCacheKey) -> None`:
         - Delete by key_hash.

       - `invalidate_by_mesh_version(self, mesh_version: str) -> int`:
         - Delete all entries for a given mesh_version. Return count deleted. This requires storing mesh_version in the data column and scanning -- or add a mesh_version column to the table for efficient deletion.
         - Better approach: add `mesh_version TEXT` as a column. Schema: `(key_hash TEXT PRIMARY KEY, mesh_version TEXT, data TEXT, created_at TEXT)`.

       - `get_stats(self) -> ExpansionCacheStats`:
         - Return current stats.

       - `clear(self) -> None`:
         - Delete all entries, reset counters.

       Follow the exact same SQLite cache pattern as `src/aegis/scoring/cache.py` (`SQLiteCacheBackend`).

    2. Create `src/aegis/query/cache_test.py` with tests:

       a) `test_cache_miss_then_hit`: Create cache. Get key -> None (miss). Put entry. Get same key -> entry (hit). Verify hit_rate=0.5 after.

       b) `test_cache_key_hash_deterministic`: Same key produces same hash. Different keys produce different hashes.

       c) `test_cache_stats`: Put 1 entry. 3 gets for that key (3 hits). 1 get for different key (1 miss). Stats: hits=3, misses=1, hit_rate=0.75.

       d) `test_invalidate_single`: Put entry, verify get returns it, invalidate, verify get returns None.

       e) `test_invalidate_by_mesh_version`: Put 3 entries (2 with version "2024", 1 with version "2025"). Invalidate version "2024". Verify only version "2025" entry remains.

       f) `test_clear`: Put 3 entries. Clear. Stats: entry_count=0, hits=0, misses=0.

       g) `test_cache_entry_model`: Create ExpansionCacheEntry, verify frozen and serializes.

       h) `test_overwrite_existing`: Put entry with key. Put different data with same key. Get returns the newer data.

    ## Files to create
    - `src/aegis/query/cache.py`
    - `src/aegis/query/cache_test.py`

    ## Code patterns to follow
    - Follow `src/aegis/scoring/cache.py` SQLite pattern exactly
    - `from __future__ import annotations`
    - Pydantic frozen models
    - SQLite for persistence

    ## Acceptance criteria
    - Cache keyed on (raw_query, mesh_version) with SHA-256 hash
    - Hit/miss tracking with stats
    - Invalidation per-key and per-mesh-version
    - SQLite-backed persistence
    - All 8 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/query/cache_test.py -v && uv run mypy src/aegis/query/cache.py && uv run ruff check src/aegis/query/cache.py
    ```

### 7. Result Formatter with Evidence Trails and Variance Bands

- **Task ID**: result-formatter
- **Role**: builder
- **Depends On**: api-schemas
- **Assigned To**: builder-3
- **Description**: |
    Build the result formatter that converts internal RankedList output to the customer-facing QueryResponse shape with variance bands, integrity disclosures, artifact hyperlinks, and provenance pointers.

    ## What to do

    1. Create `src/aegis/api/formatter.py`:

       ```python
       """Result formatter: converts internal RankedList to customer-facing QueryResponse.

       Produces per-candidate output with:
       - ROR-normalized affiliation
       - Top-3 contributing artifacts with hyperlinks
       - Per-component scores
       - Identity-linkage confidence
       - Score-variance band (from Bootstrap)
       - Integrity-gate disclosures (any soft discounts applied; never silent)
       - Specialty annotation
       - Provenance pointer (served weight-version and integrity-rule version)
       """

       from __future__ import annotations

       import logging
       import uuid
       from datetime import UTC, datetime

       from aegis.api.schemas import (
           ArtifactLink,
           CandidateResult,
           ExpansionInfo,
           IntegrityDisclosure,
           QueryResponse,
           StalenessWarning,
           VarianceBand,
       )
       from aegis.scoring.result_format import RankedCandidate, RankedList
       from aegis.scoring.variance import ScoreBand

       logger = logging.getLogger(__name__)
       ```

       **Constants for artifact URL templates:**

       ```python
       _ARTIFACT_URL_TEMPLATES: dict[str, str] = {
           "pmid": "https://pubmed.ncbi.nlm.nih.gov/{id}",
           "nct_id": "https://clinicaltrials.gov/study/{id}",
           "patent_id": "https://patents.google.com/patent/{id}",
           "grant_id": "https://reporter.nih.gov/project-details/{id}",
       }
       ```

       **Functions:**

       a) `_build_artifact_link(artifact_type: str, identifier: str, title: str, contribution_score: float) -> ArtifactLink`:
          - Look up URL template from _ARTIFACT_URL_TEMPLATES. If not found, use `"https://search.crossref.org/?q={id}"` as fallback.
          - Format URL with the identifier.
          - Return ArtifactLink.

       b) `_build_integrity_disclosures(discounts: list[dict[str, object]]) -> list[IntegrityDisclosure]`:
          - Convert soft discount dicts (from SoftDiscount model_dump) to IntegrityDisclosure models.
          - Each discount dict has keys: "discount_type", "factor", "detail".
          - Return list of IntegrityDisclosure. Return empty list if no discounts.

       **Class: `ResultFormatter`**

       ```python
       class ResultFormatter:
           """Format ranked results for customer consumption."""

           def __init__(
               self,
               *,
               integrity_rule_version: str = "1.0.0",
           ) -> None:
               self._integrity_rule_version = integrity_rule_version
       ```

       **Methods:**

       a) `format(self, *, ranked: RankedList, expansion_info: ExpansionInfo, variance_bands: dict[str, ScoreBand] | None = None, soft_discounts: dict[str, list[dict[str, object]]] | None = None, affiliations: dict[str, tuple[str, str | None]] | None = None, specialties: dict[str, str] | None = None, staleness_warnings: list[StalenessWarning] | None = None) -> QueryResponse`:
          - Generate a unique query_id (uuid4 hex).
          - For each RankedCandidate in ranked.candidates:
            - Build ArtifactLinks from candidate.top_artifacts using _build_artifact_link.
            - Look up variance band from variance_bands dict (keyed by candidate_uuid). Build VarianceBand or None.
            - Look up soft discounts from soft_discounts dict (keyed by candidate_uuid). Build IntegrityDisclosures.
            - Look up affiliation from affiliations dict: tuple of (affiliation_name, country). Default to ("Unknown", None).
            - Look up specialty from specialties dict. Default to None.
            - Build component_scores dict: {"quality_prior": breakdown.quality_prior, "topical_fit": breakdown.topical_fit, "recency": breakdown.recency, "integrity": breakdown.integrity_score}.
            - Build CandidateResult.
          - Build QueryResponse with all fields.
          - Return QueryResponse.

    2. Create `src/aegis/api/formatter_test.py` with tests:

       a) `test_build_artifact_link_pmid`: Build link for pmid "12345678". Verify URL is "https://pubmed.ncbi.nlm.nih.gov/12345678".

       b) `test_build_artifact_link_nct`: Build link for nct_id "NCT00000001". Verify URL contains clinicaltrials.gov.

       c) `test_build_artifact_link_unknown_type`: Build link for type "other" with id "xyz". Verify fallback URL used.

       d) `test_format_basic`: Create a RankedList with 2 candidates (use the existing RankedCandidate, ComponentBreakdown, ContributingArtifact models from src/aegis/scoring/result_format.py). Create a minimal ExpansionInfo. Call format(). Verify QueryResponse has 2 candidates, query_id is set, weight_version matches.

       e) `test_format_with_variance_bands`: Format with variance_bands mapping for one candidate. Verify that candidate has VarianceBand set, others have None.

       f) `test_format_with_integrity_disclosures`: Format with soft_discounts for one candidate (e.g., [{"discount_type": "predatory_load", "factor": 0.8, "detail": "predatory load 0.15"}]). Verify IntegrityDisclosure present in result.

       g) `test_format_with_staleness_warnings`: Format with a StalenessWarning. Verify it appears in response.

       h) `test_format_snapshot_shape`: Format a full result, dump to JSON, verify key fields exist in the JSON: "query_id", "candidates", "expansion_info", "weight_version", "integrity_rule_version".

       i) `test_format_empty_ranked_list`: Format with empty RankedList (0 candidates). Verify response has empty candidates list.

       j) `test_format_preserves_rank_order`: Format with 5 candidates. Verify ranks in response are 1,2,3,4,5 in order.

       Import needed test models:
       ```python
       from aegis.scoring.result_format import (
           ComponentBreakdown,
           ContributingArtifact,
           RankedCandidate,
           RankedList,
       )
       from aegis.scoring.variance import ScoreBand
       from aegis.api.schemas import ExpansionInfo, StalenessWarning
       from aegis.api.formatter import ResultFormatter, _build_artifact_link
       ```

    ## Files to create
    - `src/aegis/api/formatter.py`
    - `src/aegis/api/formatter_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations`
    - Reuse existing models from `src/aegis/scoring/result_format.py` and `src/aegis/scoring/variance.py`
    - Pydantic frozen models
    - UUID generation for query_id

    ## Acceptance criteria
    - Design assertion: `ResultFormatter.format(ranked=RankedList) -> QueryResponse`
    - Artifact URLs generated correctly for PMID, NCT, patent, grant
    - Variance bands included when available
    - Integrity disclosures included (never silent when I(c) < 1.0)
    - Provenance: weight_version and integrity_rule_version in response
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/formatter_test.py -v && uv run mypy src/aegis/api/formatter.py && uv run ruff check src/aegis/api/formatter.py
    ```

### 8. Audit Log and Stale-Data Circuit Breaker

- **Task ID**: audit-staleness
- **Role**: builder
- **Depends On**: api-schemas, jwt-auth
- **Assigned To**: builder-1
- **Description**: |
    Build the per-request audit log and the stale-data circuit breaker that adds informational caveats when integrity sources lag beyond their SLA.

    ## What to do

    1. Create `src/aegis/api/audit_log.py`:

       ```python
       """Per-request audit logging for the Aegis query API.

       Every API request is logged with: customer identity, query content,
       response candidate UUIDs, served weight version, and integrity rule version.
       This enables exact ranking reproduction for compliance review.
       """

       from __future__ import annotations

       import json
       import logging
       from datetime import UTC, datetime
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Models:**

       a) `AuditEntry` (Pydantic BaseModel, frozen):
          - `request_id: str` -- Unique request identifier
          - `customer_id: str`
          - `customer_name: str`
          - `timestamp: datetime`
          - `endpoint: str` -- e.g., "POST /v1/queries"
          - `query_text: str` -- Original task description
          - `expanded_mesh_terms: list[str]`
          - `response_candidate_uuids: list[str]`
          - `weight_version: int`
          - `integrity_rule_version: str`
          - `latency_ms: float`
          - `status_code: int`
          - `cohort_filter: str | None`

       **Class: `AuditLog`**

       - `__init__(self, *, storage_path: Path) -> None`: Store path for JSONL file.
       - `append(self, *, entry: AuditEntry) -> None`: Append-only write to JSONL (same pattern as ContestabilityStore in `src/aegis/integrity/contestability.py`).
       - `load_all(self) -> list[AuditEntry]`: Load all entries.
       - `load_by_customer(self, customer_id: str) -> list[AuditEntry]`: Filter by customer.
       - `load_by_request_id(self, request_id: str) -> AuditEntry | None`: Look up specific request.
       - `count(self) -> int`: Total entries.

    2. Create `src/aegis/api/staleness.py`:

       ```python
       """Stale-data circuit breaker for integrity source freshness.

       When a hard-gate integrity source has lagged beyond its SLA, the circuit
       breaker opens and adds a 'stale integrity data' caveat to API responses.
       Caveats are INFORMATIONAL -- they never block responses. Better to disclose
       than silently serve potentially-wrong rankings.
       """

       from __future__ import annotations

       import logging
       import time
       from datetime import UTC, datetime

       from aegis.api.schemas import StalenessWarning

       logger = logging.getLogger(__name__)
       ```

       **Constants:**

       ```python
       # Per-source SLA thresholds in seconds (hard-gate sources have tighter SLAs)
       _INTEGRITY_SOURCE_SLAS: dict[str, float] = {
           "retraction_watch": 6 * 3600,    # 6 hours
           "ori": 24 * 3600,                # 24 hours
           "ofac_sam": 6 * 3600,            # 6 hours
           "leie": 24 * 3600,               # 24 hours
           "state_medical_boards": 48 * 3600, # 48 hours
       }
       ```

       **Class: `StalenessCircuitBreaker`**

       - `__init__(self, *, sla_overrides: dict[str, float] | None = None) -> None`:
         - Merge overrides with defaults.
         - `self._last_refresh: dict[str, float] = {}` -- Epoch timestamp of last successful refresh per source.
         - `self._open_circuits: set[str] = set()` -- Sources currently in stale state.

       - `record_refresh(self, source: str) -> None`:
         - Record a successful refresh timestamp. Close the circuit for this source if it was open.

       - `check_all(self) -> list[StalenessWarning]`:
         - For each source in SLAs: check if (now - last_refresh) > SLA. If yes: add to open_circuits and create StalenessWarning.
         - Sources with no recorded refresh are always stale (produce a warning with message "No refresh recorded for {source}").
         - Return list of warnings.

       - `is_stale(self, source: str) -> bool`:
         - Return True if source is currently stale.

       - `get_open_circuits(self) -> set[str]`:
         - Return set of source names with open circuits.

    3. Create `src/aegis/api/staleness_test.py` with tests:

       a) `test_no_refresh_all_stale`: Create breaker. check_all() should return warnings for all sources (no refreshes recorded).

       b) `test_refresh_clears_staleness`: Create breaker. Record refresh for "retraction_watch". check_all() should NOT include retraction_watch warning.

       c) `test_stale_after_sla`: Create breaker with sla_overrides={"retraction_watch": 0.01} (very short SLA, ~10ms). Record refresh. Sleep 0.02s. check_all() should include retraction_watch warning.

       d) `test_warning_format`: Get a warning, verify it has source, last_updated, sla_hours, message fields.

       e) `test_is_stale`: No refresh -> is_stale("retraction_watch") returns True. Record refresh -> returns False.

       f) `test_open_circuits`: No refresh -> get_open_circuits() includes all sources. Record all refreshes -> empty set.

       g) `test_audit_log_append_and_load(tmp_path)`: Create AuditLog, append 3 entries, load_all returns 3.

       h) `test_audit_log_by_customer(tmp_path)`: Append entries for 2 customers, load_by_customer returns correct subset.

       i) `test_audit_log_by_request_id(tmp_path)`: Append entry with known request_id, load_by_request_id returns it. Unknown request_id returns None.

       j) `test_audit_entry_model`: Create AuditEntry with all fields. Verify frozen.

    ## Files to create
    - `src/aegis/api/audit_log.py`
    - `src/aegis/api/staleness.py`
    - `src/aegis/api/staleness_test.py`

    ## Code patterns to follow
    - Append-only JSONL pattern from `src/aegis/integrity/contestability.py`
    - `from __future__ import annotations`
    - Pydantic frozen models
    - `time.monotonic()` for SLA checks (or `time.time()` for epoch timestamps to match FreshnessMetrics pattern)
    - Informational caveats: never block responses

    ## Acceptance criteria
    - AuditLog persists entries in append-only JSONL
    - AuditLog supports lookup by customer and request_id
    - Circuit breaker detects stale sources based on SLA thresholds
    - Circuit breaker produces StalenessWarning models
    - Caveats are informational, never block responses
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/staleness_test.py -v && uv run mypy src/aegis/api/audit_log.py src/aegis/api/staleness.py && uv run ruff check src/aegis/api/audit_log.py src/aegis/api/staleness.py
    ```

### 9. LLM Cost Monitoring

- **Task ID**: llm-cost-monitor
- **Role**: builder
- **Depends On**: llm-expansion, jwt-auth
- **Assigned To**: builder-2
- **Description**: |
    Build per-customer LLM cost monitoring with budget caps and graceful degradation.

    ## What to do

    1. Create `src/aegis/observability/llm_cost.py`:

       ```python
       """LLM cost monitoring: per-customer spend tracking with budget enforcement.

       Tracks token consumption and estimated cost per customer. When a customer
       exceeds their daily budget, the system degrades gracefully by falling back
       to MetaMap-only expansion (no LLM call) and flags the response.
       """

       from __future__ import annotations

       import logging
       import time
       from collections import defaultdict
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       # Approximate cost per token (in cents) -- configurable per model
       _DEFAULT_COST_PER_INPUT_TOKEN_CENTS = 0.0003  # $3/M input tokens
       _DEFAULT_COST_PER_OUTPUT_TOKEN_CENTS = 0.0015  # $15/M output tokens
       ```

       **Models:**

       a) `CostRecord` (Pydantic BaseModel, frozen):
          - `customer_id: str`
          - `timestamp: float` -- epoch
          - `input_tokens: int`
          - `output_tokens: int`
          - `estimated_cost_cents: float`
          - `model: str`
          - `operation: str` -- "query_expansion", "mesh_fallback", etc.

       b) `CustomerBudgetStatus` (Pydantic BaseModel, frozen):
          - `customer_id: str`
          - `daily_budget_cents: float`
          - `spent_today_cents: float`
          - `remaining_cents: float`
          - `over_budget: bool`
          - `request_count_today: int`

       c) `CostDashboard` (Pydantic BaseModel, frozen):
          - `total_spend_cents: float`
          - `total_tokens: int`
          - `customer_breakdown: dict[str, float]` -- customer_id -> spend_cents
          - `model_breakdown: dict[str, float]` -- model -> spend_cents
          - `over_budget_customers: list[str]`

       **Class: `LlmCostMonitor`**

       - `__init__(self, *, cost_per_input_token: float = _DEFAULT_COST_PER_INPUT_TOKEN_CENTS, cost_per_output_token: float = _DEFAULT_COST_PER_OUTPUT_TOKEN_CENTS) -> None`:
         - Store cost rates.
         - `self._records: list[CostRecord] = []`
         - `self._daily_budgets: dict[str, float] = {}` -- customer_id -> daily budget in cents

       - `set_budget(self, customer_id: str, daily_budget_cents: float) -> None`:
         - Set or update a customer's daily budget.

       - `record_usage(self, *, customer_id: str, input_tokens: int, output_tokens: int, model: str, operation: str = "query_expansion") -> CostRecord`:
         - Compute estimated_cost_cents = input_tokens * cost_per_input_token + output_tokens * cost_per_output_token.
         - Create and store CostRecord.
         - Return it.

       - `check_budget(self, customer_id: str) -> CustomerBudgetStatus`:
         - Sum today's spend for this customer (filter records by date).
         - Compare against daily_budget. Default budget if not set: 1000 cents ($10/day).
         - Return CustomerBudgetStatus.

       - `is_over_budget(self, customer_id: str) -> bool`:
         - Convenience: return check_budget(customer_id).over_budget.

       - `get_dashboard(self) -> CostDashboard`:
         - Aggregate across all records (today only).
         - Return CostDashboard.

       - `_today_records(self, customer_id: str | None = None) -> list[CostRecord]`:
         - Filter records to today. Optionally filter by customer.
         - "Today" = records where datetime.fromtimestamp(timestamp, tz=UTC).date() == datetime.now(UTC).date().

    2. Create `src/aegis/observability/llm_cost_test.py` with tests:

       a) `test_record_usage`: Record usage. Verify CostRecord has correct cost calculation.

       b) `test_check_budget_within`: Set budget 1000 cents. Record 100 tokens. Verify not over budget.

       c) `test_check_budget_exceeded`: Set budget 1 cent. Record 10000 input tokens (should exceed). Verify over_budget=True.

       d) `test_is_over_budget`: Same as above but use convenience method.

       e) `test_dashboard`: Record usage for 2 customers. Dashboard shows both in customer_breakdown.

       f) `test_over_budget_customers_listed`: One customer over budget. Dashboard lists them in over_budget_customers.

       g) `test_default_budget`: Don't set budget. check_budget returns default (1000 cents).

       h) `test_cost_record_model`: Create CostRecord, verify frozen.

    ## Files to create
    - `src/aegis/observability/llm_cost.py`
    - `src/aegis/observability/llm_cost_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations`
    - Pydantic frozen models
    - In-memory tracking (production would use Prometheus counters)
    - defaultdict for per-customer aggregation

    ## Acceptance criteria
    - Per-customer token and cost tracking
    - Budget enforcement with over_budget detection
    - Dashboard aggregation across customers and models
    - Graceful degradation concept: is_over_budget() signals callers to skip LLM
    - All 8 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/llm_cost_test.py -v && uv run mypy src/aegis/observability/llm_cost.py && uv run ruff check src/aegis/observability/llm_cost.py
    ```

### 10. FastAPI Server Wiring and Integration Tests

- **Task ID**: api-server
- **Role**: builder
- **Depends On**: api-schemas, jwt-auth, rate-limiter, result-formatter, audit-staleness, llm-expansion, expansion-validator, expansion-cache, llm-cost-monitor
- **Assigned To**: builder-1
- **Description**: |
    Build the FastAPI application that wires together all API components: auth, rate limiting, query expansion, ranking, formatting, audit logging, and staleness detection. Create integration tests.

    ## What to do

    1. Create `src/aegis/api/server.py`:

       ```python
       """Aegis customer-facing query API server.

       Mounts all routers and middleware: JWT auth, rate limiting, audit logging,
       query expansion, ranking, result formatting, and staleness detection.
       """

       from __future__ import annotations

       import hashlib
       import logging
       import time
       import uuid
       from datetime import UTC, datetime
       from pathlib import Path

       from fastapi import Depends, FastAPI, HTTPException, status
       from fastapi.responses import JSONResponse

       from aegis.api.audit_log import AuditEntry, AuditLog
       from aegis.api.auth import (
           CustomerClaims,
           TokenPayload,
           get_current_customer,
           require_cohort_access,
       )
       from aegis.api.formatter import ResultFormatter
       from aegis.api.rate_limit import RateLimiterRegistry, RateLimitResult
       from aegis.api.schemas import (
           ErrorResponse,
           ExpansionInfo,
           QueryRequest,
           QueryResponse,
       )
       from aegis.api.staleness import StalenessCircuitBreaker

       logger = logging.getLogger(__name__)
       ```

       **Application factory:**

       ```python
       def create_app(
           *,
           audit_log_path: Path | None = None,
           rate_limiter: RateLimiterRegistry | None = None,
           circuit_breaker: StalenessCircuitBreaker | None = None,
           formatter: ResultFormatter | None = None,
       ) -> FastAPI:
           """Create and configure the Aegis API application."""
           app = FastAPI(
               title="Aegis Expert Discovery API",
               version="1.0.0",
               description="Customer-facing query API for expert discovery and ranking",
           )

           # Initialize components with defaults
           _audit_log = AuditLog(storage_path=audit_log_path or Path("data/aegis/audit_log.jsonl"))
           _rate_limiter = rate_limiter or RateLimiterRegistry()
           _circuit_breaker = circuit_breaker or StalenessCircuitBreaker()
           _formatter = formatter or ResultFormatter()

           @app.post(
               "/v1/queries",
               response_model=QueryResponse,
               status_code=status.HTTP_200_OK,
               responses={
                   429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
                   401: {"model": ErrorResponse, "description": "Authentication failed"},
                   403: {"model": ErrorResponse, "description": "Access denied"},
               },
           )
           def submit_query(
               body: QueryRequest,
               customer: TokenPayload = Depends(get_current_customer),
           ) -> QueryResponse | JSONResponse:
               """Submit a query for expert ranking.

               Authenticates the customer, checks rate limits, expands the query
               via LLM + MetaMap, runs the ranking pipeline, formats results,
               and returns with full evidence trails.
               """
               start_time = time.monotonic()

               # 1. Cohort access check
               require_cohort_access(customer, body.cohort_filter)

               # 2. Rate limit check
               query_hash = hashlib.sha256(body.task_description.encode()).hexdigest()[:16]
               rl_result = _rate_limiter.check(
                   customer_id=customer.sub,
                   rate=float(customer.rate_limit_qps),
                   capacity=float(customer.rate_limit_qps) * 2,
                   query_hash=query_hash,
               )
               if not rl_result.allowed:
                   return JSONResponse(
                       status_code=429,
                       content=ErrorResponse(
                           error="rate_limit_exceeded",
                           detail="Too many requests",
                           retry_after=int(rl_result.retry_after_seconds or 1),
                       ).model_dump(),
                       headers={"Retry-After": str(int(rl_result.retry_after_seconds or 1))},
                   )

               # 3. Check staleness
               staleness_warnings = _circuit_breaker.check_all()

               # 4. Query expansion (stub: in production, wire LlmQueryExpander here)
               # For the initial server, we return the mesh_override or a placeholder expansion.
               if body.mesh_override:
                   expansion_info = ExpansionInfo(
                       original_query=body.task_description,
                       expanded_mesh_terms=body.mesh_override,
                       expansion_method="override",
                       low_confidence=False,
                       cached=False,
                   )
               else:
                   # Placeholder: in production, call LlmQueryExpander.expand()
                   expansion_info = ExpansionInfo(
                       original_query=body.task_description,
                       expanded_mesh_terms=[],
                       expansion_method="pending_integration",
                       low_confidence=True,
                       cached=False,
                   )

               # 5. Ranking (stub: in production, wire Ranker here)
               # For the initial server, return empty results.
               # The actual ranking pipeline (CandidateStore -> QualityPrior -> TopicalFit
               # -> Recency -> Ranker) is wired by the deployment layer.
               from aegis.scoring.result_format import RankedList
               ranked = RankedList(
                   query_mesh_terms=expansion_info.expanded_mesh_terms,
                   cohort_size=0,
                   result_count=0,
                   candidates=[],
                   excluded_count=0,
                   weight_version=1,
                   exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
                   metadata={},
               )

               # 6. Format response
               response = _formatter.format(
                   ranked=ranked,
                   expansion_info=expansion_info,
                   staleness_warnings=staleness_warnings,
               )

               # 7. Audit log
               elapsed_ms = (time.monotonic() - start_time) * 1000
               _audit_log.append(entry=AuditEntry(
                   request_id=response.query_id,
                   customer_id=customer.sub,
                   customer_name=customer.customer_name,
                   timestamp=datetime.now(UTC),
                   endpoint="POST /v1/queries",
                   query_text=body.task_description,
                   expanded_mesh_terms=expansion_info.expanded_mesh_terms,
                   response_candidate_uuids=[c.candidate_uuid for c in response.candidates],
                   weight_version=ranked.weight_version,
                   integrity_rule_version=_formatter._integrity_rule_version,
                   latency_ms=round(elapsed_ms, 2),
                   status_code=200,
                   cohort_filter=body.cohort_filter,
               ))

               return response

           @app.get("/v1/health")
           def health_check() -> dict[str, str]:
               """Health check endpoint."""
               return {"status": "healthy", "version": "1.0.0"}

           return app
       ```

       **IMPORTANT DESIGN NOTES:**
       - The ranking pipeline (steps 4-5) is stubbed. The actual wiring of CandidateStore, QualityPrior, TopicalFit, Recency, and Ranker is done by the deployment layer, not by this module. This server provides the HTTP plumbing; the scoring engine integration happens at deployment time via dependency injection.
       - The `/v1/queries` endpoint is synchronous (matching the Phase 3c feedback.py pattern).
       - The server returns QueryResponse directly. FastAPI handles serialization.

    2. Create `src/aegis/api/server_test.py` with integration tests:

       ```python
       """Integration tests for the Aegis query API server."""

       from __future__ import annotations

       from pathlib import Path

       import pytest
       from fastapi.testclient import TestClient

       from aegis.api.auth import CustomerClaims, create_token
       from aegis.api.server import create_app
       from aegis.api.staleness import StalenessCircuitBreaker
       ```

       Tests:

       a) `test_health_check`: Create app, GET /v1/health, verify 200 with status "healthy".

       b) `test_query_requires_auth`: POST /v1/queries without token. Verify 403 (FastAPI's HTTPBearer returns 403 when no token).

       c) `test_query_invalid_token`: POST /v1/queries with Authorization: Bearer garbage. Verify 401.

       d) `test_query_success(tmp_path)`: Create valid JWT token. POST /v1/queries with valid QueryRequest body. Verify 200, response has query_id, candidates list (empty for stub), expansion_info, weight_version.

       e) `test_query_with_mesh_override(tmp_path)`: POST with mesh_override=["Neoplasms"]. Verify expansion_method="override".

       f) `test_query_rate_limited(tmp_path)`: Create token with rate_limit_qps=1. Send 3 rapid requests. At least one should get 429 with Retry-After header.

       g) `test_query_cohort_denied(tmp_path)`: Create token with allowed_cohorts=["translational"]. POST with cohort_filter="drug_discovery". Verify 403.

       h) `test_query_short_description(tmp_path)`: POST with task_description="short". Verify 422 (validation error).

       i) `test_staleness_warnings_included(tmp_path)`: Create app with StalenessCircuitBreaker that has no refreshes recorded. POST valid query. Verify response has staleness_warnings non-empty.

       j) `test_audit_log_written(tmp_path)`: POST a valid query. Read the audit log file. Verify an entry was written with the customer_id and query text.

       For each test that requires auth, create a token like:
       ```python
       token = create_token(
           CustomerClaims(customer_id="test-customer", customer_name="Test Corp"),
           secret="test-secret",
       )
       ```
       And set the env var: `monkeypatch.setenv("AEGIS_JWT_SECRET", "test-secret")`.

       Use `client = TestClient(create_app(audit_log_path=tmp_path / "audit.jsonl"))`.

    ## Files to create
    - `src/aegis/api/server.py`
    - `src/aegis/api/server_test.py`

    ## Code patterns to follow
    - FastAPI application factory pattern
    - `from __future__ import annotations`
    - Dependency injection via constructor parameters
    - TestClient for integration tests (same as Phase 3c feedback_test.py)
    - monkeypatch for env vars in tests

    ## Acceptance criteria
    - Design assertions: `POST /v1/queries` returns QueryResponse, `GET /v1/health` returns 200
    - JWT auth enforced on /v1/queries
    - Rate limiting returns 429 with Retry-After
    - Cohort restrictions enforced (403)
    - Staleness warnings included in response
    - Audit log written per request
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/server_test.py -v && uv run mypy src/aegis/api/server.py && uv run ruff check src/aegis/api/server.py
    ```

### 11. Load-Test Harness

- **Task ID**: load-test
- **Role**: builder
- **Depends On**: api-server
- **Assigned To**: builder-3
- **Description**: |
    Build the load-test harness that verifies the query throughput SLO: 100 qps sustained, 500 qps peak, <500ms p95 latency.

    ## What to do

    1. Create `tests/perf/__init__.py`:
       ```python
       """Performance test harness for Aegis API."""
       from __future__ import annotations
       ```

    2. Create `tests/perf/test_throughput.py`:

       ```python
       """Load-test harness for Aegis query API throughput SLO.

       Targets:
       - 100 queries/second sustained for configurable duration
       - 500 queries/second peak burst
       - <500ms p95 latency
       - <1500ms p99 latency

       Uses FastAPI's TestClient with concurrent.futures for parallel request generation.
       For production load testing, use locust or k6 against a running server.
       """

       from __future__ import annotations

       import statistics
       import time
       from concurrent.futures import ThreadPoolExecutor, as_completed
       from pathlib import Path

       import pytest
       from fastapi.testclient import TestClient

       from aegis.api.auth import CustomerClaims, create_token
       from aegis.api.server import create_app
       ```

       **Helper functions:**

       a) `_make_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, str]`:
          - Set AEGIS_JWT_SECRET env var.
          - Create app with tmp_path audit log.
          - Create token with high rate_limit_qps (10000).
          - Return (TestClient, token).

       b) `_send_query(client: TestClient, token: str, query_text: str) -> tuple[int, float]`:
          - Record start time.
          - POST /v1/queries with valid body and auth header.
          - Record elapsed time in ms.
          - Return (status_code, latency_ms).

       **Tests:**

       a) `test_sustained_throughput(tmp_path, monkeypatch)`:
          - Create client and token.
          - Target: 100 queries over ~1 second (approximating 100 qps for a short burst).
          - Use ThreadPoolExecutor with max_workers=20.
          - Submit 100 requests in parallel.
          - Collect all latencies.
          - Assert: >= 95% of requests returned 200.
          - Assert: p95 latency < 500ms.
          - Assert: p99 latency < 1500ms.
          - Log throughput: total_requests / total_wall_time.

       b) `test_peak_burst(tmp_path, monkeypatch)`:
          - Target: 50 concurrent requests (simulating burst).
          - ThreadPoolExecutor with max_workers=50.
          - Submit 50 requests simultaneously.
          - Assert: all returned 200 (no 5xx errors).
          - Assert: p95 latency < 1000ms (relaxed for burst).

       c) `test_p95_latency_single(tmp_path, monkeypatch)`:
          - Send 20 sequential requests.
          - Assert: p95 latency < 500ms.

       d) `test_rate_limit_under_load(tmp_path, monkeypatch)`:
          - Create token with rate_limit_qps=5.
          - Send 20 concurrent requests.
          - Assert: some requests get 429 (rate limited).
          - Assert: no 5xx errors.

       **IMPORTANT**: These tests use TestClient (synchronous, in-process) which is much faster than real HTTP. The p95 < 500ms target applies to the application logic, not network overhead. For production load testing, a separate locust/k6 harness against a running uvicorn server would be needed. Mark longer tests with `@pytest.mark.slow` so they can be skipped in CI fast runs.

    ## Files to create
    - `tests/perf/__init__.py`
    - `tests/perf/test_throughput.py`

    ## Code patterns to follow
    - `from __future__ import annotations`
    - ThreadPoolExecutor for concurrent load generation
    - `statistics.quantiles` for percentile calculation
    - `@pytest.mark.slow` for long-running tests
    - TestClient for in-process HTTP testing

    ## Acceptance criteria
    - Load test runs 100 concurrent queries
    - p95 latency measured and asserted < 500ms
    - p99 latency measured and asserted < 1500ms
    - Rate limiting verified under load
    - No 5xx errors under sustained load
    - All 4 tests pass
    - mypy strict passes on test file
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest tests/perf/test_throughput.py -v && uv run ruff check tests/perf/test_throughput.py
    ```

### 12. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: api-schemas, jwt-auth, rate-limiter, llm-expansion, expansion-validator, expansion-cache, result-formatter, audit-staleness, llm-cost-monitor, api-server, load-test
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the Phase 3b customer API sub-spec.

    ## Validation Commands

    Run each of these commands. ALL must pass for validation to succeed.

    1. Schema tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/schemas_test.py -v
    ```

    2. Auth tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/auth_test.py -v
    ```

    3. Rate limiter tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/rate_limit_test.py -v
    ```

    4. LLM expansion tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/query/llm_expansion_test.py -v
    ```

    5. Expansion validator tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/query/expansion_validator_test.py -v
    ```

    6. Expansion cache tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/query/cache_test.py -v
    ```

    7. Result formatter tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/formatter_test.py -v
    ```

    8. Audit log and staleness tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/staleness_test.py -v
    ```

    9. LLM cost monitor tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/llm_cost_test.py -v
    ```

    10. Server integration tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/server_test.py -v
    ```

    11. Load tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest tests/perf/test_throughput.py -v
    ```

    12. All Phase 3b tests together:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/schemas_test.py src/aegis/api/auth_test.py src/aegis/api/rate_limit_test.py src/aegis/query/llm_expansion_test.py src/aegis/query/expansion_validator_test.py src/aegis/query/cache_test.py src/aegis/api/formatter_test.py src/aegis/api/staleness_test.py src/aegis/observability/llm_cost_test.py src/aegis/api/server_test.py tests/perf/test_throughput.py -v
    ```

    13. mypy strict on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/api/schemas.py src/aegis/api/auth.py src/aegis/api/rate_limit.py src/aegis/api/formatter.py src/aegis/api/audit_log.py src/aegis/api/staleness.py src/aegis/api/server.py src/aegis/query/llm_expansion.py src/aegis/query/expansion_validator.py src/aegis/query/cache.py src/aegis/observability/llm_cost.py
    ```

    14. ruff lint on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/api/ src/aegis/query/ src/aegis/observability/llm_cost.py tests/perf/
    ```

    15. Verify API package imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.api.schemas import QueryRequest, QueryResponse, CandidateResult
    from aegis.api.auth import create_token, decode_token, CustomerClaims
    from aegis.api.rate_limit import RateLimiterRegistry, TokenBucket
    from aegis.api.formatter import ResultFormatter
    from aegis.api.audit_log import AuditLog, AuditEntry
    from aegis.api.staleness import StalenessCircuitBreaker
    from aegis.api.server import create_app
    from aegis.query.llm_expansion import LlmQueryExpander, ExpandedQuery
    from aegis.query.expansion_validator import ExpansionValidator
    from aegis.query.cache import ExpansionCache
    from aegis.observability.llm_cost import LlmCostMonitor
    print('All Phase 3b imports OK')
    "
    ```

    16. Verify design assertions:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.api.schemas import QueryRequest, QueryResponse
    from aegis.api.formatter import ResultFormatter
    from aegis.query.llm_expansion import LlmQueryExpander, ExpandedQuery

    # Verify ResultFormatter.format exists
    assert hasattr(ResultFormatter, 'format')

    # Verify LlmQueryExpander.expand exists
    assert hasattr(LlmQueryExpander, 'expand')

    # Verify QueryRequest has required fields
    fields = QueryRequest.model_fields
    for f in ['task_description', 'mesh_override', 'cohort_filter', 'k', 'cutoff_strategy']:
        assert f in fields, f'Missing field: {f}'

    # Verify QueryResponse has required fields
    fields = QueryResponse.model_fields
    for f in ['query_id', 'candidates', 'expansion_info', 'staleness_warnings', 'weight_version', 'integrity_rule_version']:
        assert f in fields, f'Missing field: {f}'

    print('All design assertions OK')
    "
    ```

    17. Verify existing Phase 1 scoring tests still pass (no regression):
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/rank_test.py src/aegis/scoring/variance_test.py src/aegis/scoring/cache_test.py -v
    ```

    ## Acceptance Criteria

    ALL of these must be verified:

    - [ ] `src/aegis/api/__init__.py` exists and is importable
    - [ ] `src/aegis/query/__init__.py` exists and is importable
    - [ ] `src/aegis/api/schemas.py` exports QueryRequest, QueryResponse, CandidateResult, ExpansionInfo, StalenessWarning, ErrorResponse
    - [ ] `src/aegis/api/auth.py` exports create_token, decode_token, get_current_customer, CustomerClaims, TokenPayload
    - [ ] JWT auth: token creation, validation, expiry, wrong-secret all work correctly
    - [ ] Cohort restrictions enforced (403 on mismatch)
    - [ ] `src/aegis/api/rate_limit.py` exports RateLimiterRegistry, TokenBucket, AbuseDetector
    - [ ] Token-bucket rate limiting: allows within rate, denies over capacity, returns retry_after
    - [ ] Abuse detection catches burst and identical-query patterns
    - [ ] Design assertion: `POST /v1/queries` endpoint exists and returns QueryResponse
    - [ ] Design assertion: `LlmQueryExpander.expand(raw_query) -> ExpandedQuery`
    - [ ] Design assertion: `ResultFormatter.format(ranked=RankedList) -> QueryResponse`
    - [ ] LLM expansion uses Anthropic tool-use for constrained generation
    - [ ] MetaMap fallback when LLM fails or terms rejected
    - [ ] Expansion validator is fail-closed against MeSH ontology
    - [ ] Query expansion cache keyed on (raw_query, mesh_version)
    - [ ] Result formatter includes variance bands, integrity disclosures, artifact hyperlinks, provenance
    - [ ] Stale-data circuit breaker adds caveats (never blocks responses)
    - [ ] Audit log records every request with full provenance
    - [ ] LLM cost monitoring tracks per-customer spend with budget caps
    - [ ] Load test: 100 concurrent queries, p95 < 500ms, no 5xx errors
    - [ ] Rate limiting verified under load (429 responses when over limit)
    - [ ] All schema tests pass (8 tests)
    - [ ] All auth tests pass (9 tests)
    - [ ] All rate limiter tests pass (9 tests)
    - [ ] All LLM expansion tests pass (7 tests)
    - [ ] All expansion validator tests pass (10 tests)
    - [ ] All expansion cache tests pass (8 tests)
    - [ ] All formatter tests pass (10 tests)
    - [ ] All audit/staleness tests pass (10 tests)
    - [ ] All LLM cost tests pass (8 tests)
    - [ ] All server integration tests pass (10 tests)
    - [ ] All load tests pass (4 tests)
    - [ ] mypy strict passes on all new modules
    - [ ] ruff lint passes on all new modules
    - [ ] Existing Phase 1 scoring tests unbroken

### 13. Update API Design Document

- **Task ID**: update-design-api
- **Role**: design-updater
- **Depends On**: validate-all
- **Assigned To**: design-updater
- **Description**: |
    Update the living design document for the API domain to reflect
    what was actually built in this plan.

    ## Target Design Doc
    docs/design/api.md

    ## Spec File
    specs/aegis-phase3b-customer-api.md

    ## Scope
    New API domain: customer-facing query API layer including authentication (JWT),
    rate limiting (token-bucket), query expansion (LLM + MetaMap), result formatting
    (evidence trails, variance bands, integrity disclosures), audit logging, staleness
    circuit breaker, and LLM cost monitoring. This is the first API design doc -- create it.

    ## Prior Decisions to Check
    - Scoring design doc (`docs/design/scoring.md`) -- ranking formula Rank(c,q) = I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma is consumed by the API formatter
    - Pydantic frozen model pattern from scoring domain
    - Score cache pattern from `src/aegis/scoring/cache.py`
    - Append-only JSONL pattern from `src/aegis/integrity/contestability.py`

    ## What to Record
    Read git diff HEAD~1 HEAD, then the changed source files, then the existing
    design doc (create if not present). Write a Current Design section describing the API architecture,
    component interactions, and key patterns. Append a Design Decision entry for each
    non-trivial architectural choice made in this build:
    - JWT HS256 authentication with per-customer scoping
    - Token-bucket rate limiting with abuse detection
    - Constrained-generation LLM expansion via Anthropic tool use
    - Fail-closed expansion validator against MeSH ontology
    - SQLite-backed expansion cache keyed on (raw_query, mesh_version)
    - Stale-data circuit breaker (informational caveats, never blocks)
    - Result formatter with variance bands and integrity disclosures
    - Per-request audit logging in append-only JSONL
    - Per-customer LLM cost monitoring with budget caps
    Every claim must cite a file:line from the actual code.

## Acceptance Criteria

- `POST /v1/queries` endpoint at `src/aegis/api/server.py` accepts authenticated QueryRequest, enforces rate limits, expands query via LLM + MetaMap, formats results with evidence trails, and returns QueryResponse
- JWT authentication with per-customer scoping and optional per-cohort restrictions at `src/aegis/api/auth.py`
- Token-bucket rate limiting at `src/aegis/api/rate_limit.py` with per-customer enforcement, 429 + Retry-After on over-budget, abuse pattern detection
- `LlmQueryExpander.expand(raw_query) -> ExpandedQuery` at `src/aegis/query/llm_expansion.py` uses Anthropic tool use for constrained MeSH generation with MetaMap fallback
- `ExpansionValidator.validate(terms) -> ValidationReport` at `src/aegis/query/expansion_validator.py` is fail-closed against MeSH + CPC + ChEMBL vocabularies
- Query expansion cache at `src/aegis/query/cache.py` keyed on (raw_query, mesh_version) with SQLite backend
- `ResultFormatter.format(ranked=RankedList) -> QueryResponse` at `src/aegis/api/formatter.py` includes variance bands, integrity disclosures (never silent when I(c) < 1.0), artifact hyperlinks, and provenance pointer
- Stale-data circuit breaker at `src/aegis/api/staleness.py` adds informational caveats when integrity sources lag beyond SLA (never blocks responses)
- Per-request audit log at `src/aegis/api/audit_log.py` records customer, query, response candidate UUIDs, served weight + integrity-rule versions
- LLM cost monitoring at `src/aegis/observability/llm_cost.py` tracks per-customer spend with budget caps and graceful degradation
- Load test at `tests/perf/test_throughput.py` sustains 100 concurrent queries with p95 < 500ms
- All new tests pass (93 tests total: 8+9+9+7+10+8+10+10+8+10+4)
- mypy strict passes on all new modules
- ruff lint passes on all new modules
- No existing Phase 1 scoring tests broken

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/api/schemas_test.py src/aegis/api/auth_test.py src/aegis/api/rate_limit_test.py src/aegis/query/llm_expansion_test.py src/aegis/query/expansion_validator_test.py src/aegis/query/cache_test.py src/aegis/api/formatter_test.py src/aegis/api/staleness_test.py src/aegis/observability/llm_cost_test.py src/aegis/api/server_test.py tests/perf/test_throughput.py -v` -- Run all Phase 3b tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/api/schemas.py src/aegis/api/auth.py src/aegis/api/rate_limit.py src/aegis/api/formatter.py src/aegis/api/audit_log.py src/aegis/api/staleness.py src/aegis/api/server.py src/aegis/query/llm_expansion.py src/aegis/query/expansion_validator.py src/aegis/query/cache.py src/aegis/observability/llm_cost.py` -- Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/api/ src/aegis/query/ src/aegis/observability/llm_cost.py tests/perf/` -- Lint all new modules
- `cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/rank_test.py src/aegis/scoring/variance_test.py src/aegis/scoring/cache_test.py -v` -- Verify existing tests unbroken
- `cd /Users/anvith/aegis && uv run python -c "from aegis.api.server import create_app; from aegis.query.llm_expansion import LlmQueryExpander; from aegis.api.formatter import ResultFormatter; print('Core imports OK')"` -- Verify core imports

## Notes

- `pyjwt>=2.8` must be added to `pyproject.toml` for JWT authentication. Run `uv lock` after adding.
- `anthropic>=0.25` must be added to `pyproject.toml` for LLM expansion. Run `uv lock` after adding.
- The ranking pipeline (CandidateStore -> QualityPrior -> TopicalFit -> Recency -> Ranker) is stubbed in the server. Full pipeline wiring happens at deployment time via dependency injection. This keeps the API layer decoupled from the scoring engine.
- The MetaMapExpander is a stub. Real MetaMap integration (via the UMLS REST API or local MetaMap installation) is out of scope for the initial implementation.
- Tests must NOT require a real Anthropic API key. LLM expansion tests verify fallback behavior and model construction.
- The load-test harness uses TestClient (in-process) which is faster than real HTTP. Production load testing against a running uvicorn server is a separate operational concern.
- Phase 3c's feedback endpoint (`POST /v1/feedback/tasks/{task_id}/outcomes`) is built in the parallel phase3c spec. The server in this spec does not mount it -- that integration happens at deployment time.
- The `src/aegis/api/` directory may already exist if Phase 3c builds first (it creates `__init__.py` and `feedback.py`). Builders should check for existing files and not overwrite them. If `__init__.py` already exists, skip creating it.
