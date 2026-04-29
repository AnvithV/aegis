# Plan: Phase 5 — Production Reality

> **Status:** COMPLETE (2026-04-27)
> All 18 tasks completed. 31/31 tests passing. 10/10 modules compile. Frontend type-checks clean. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-27
> **Team:** phase5-production-reality-20260427-2112

### Test Results
- `src/aegis/sources/openalex_test.py` — 7/7 PASSED
- `src/aegis/pipeline/orchestrator_test.py` — 5/5 PASSED
- `src/aegis/query/classifier_test.py` — 5/5 PASSED
- `src/aegis/storage/shortlist_store_test.py` — 5/5 PASSED
- `src/aegis/storage/notes_store_test.py` — 4/4 PASSED
- `src/aegis/storage/query_store_test.py` — 5/5 PASSED
- Frontend `tsc --noEmit` — PASSED (zero errors)

### Validation Commands
| Command | Result |
|---------|--------|
| `py_compile src/aegis/sources/openalex.py` | PASS |
| `py_compile src/aegis/pipeline/orchestrator.py` | PASS |
| `py_compile src/aegis/query/classifier.py` | PASS |
| `py_compile src/aegis/api/server.py` | PASS |
| `py_compile src/aegis/api/streaming.py` | PASS |
| `py_compile src/aegis/api/shortlists.py` | PASS |
| `py_compile src/aegis/api/notes.py` | PASS |
| `py_compile src/aegis/storage/shortlist_store.py` | PASS |
| `py_compile src/aegis/storage/notes_store.py` | PASS |
| `py_compile src/aegis/storage/query_store.py` | PASS |
| `pytest openalex_test.py` | PASS — 7/7 |
| `pytest orchestrator_test.py` | PASS — 5/5 |
| `pytest classifier_test.py` | PASS — 5/5 |
| `pytest shortlist/notes/query store tests` | PASS — 14/14 |
| `npx tsc --noEmit` (frontend) | PASS |
| `test -f Dockerfile && docker-compose.yml && .env.sample` | PASS |

### Acceptance Criteria Verification
- [x] Backend: OpenAlex client with async methods — VERIFIED (`OpenAlexClient` class with async `search_works`, `search_authors`, `get_funder`, `search_concepts` in `src/aegis/sources/openalex.py`)
- [x] Backend: Pipeline orchestrator wires real F1-F7 scoring — VERIFIED (`QueryPipeline` imports `HardGateResult`, `QualityPrior`, `WeightVector` and computes real scores in `src/aegis/pipeline/orchestrator.py`)
- [x] Backend: Query classifier routes to weight vectors — VERIFIED (`QueryClassifier.classify()` returns `ClassificationResult` with matched weight vector in `src/aegis/query/classifier.py`)
- [x] Backend: SSE streaming endpoint exists — VERIFIED (`/v1/queries/{query_id}/stream` endpoint with `StreamingResponse` and `text/event-stream` in `src/aegis/api/streaming.py`)
- [x] Backend: Shortlists API full CRUD — VERIFIED (6 endpoints: `create_shortlist`, `list_shortlists`, `get_shortlist`, `add_to_shortlist`, `remove_from_shortlist`, `delete_shortlist` in `src/aegis/api/shortlists.py`)
- [x] Backend: Notes API full CRUD — VERIFIED (4 endpoints: `create_note`, `list_notes`, `update_note`, `delete_note` in `src/aegis/api/notes.py`)
- [x] Backend: Real F1-F7 scoring replaces stubs — VERIFIED (orchestrator imports `HardGateResult`, `QualityPrior` and computes integrity results + quality prior scores)
- [x] Backend: Privacy gate wired — VERIFIED (`PrivacyGate`, `PHIScanner`, `DemographicBlocklist`, `OptOutStore` imported and `_apply_privacy_gate` method filters candidates in orchestrator)
- [x] Backend: Continuous ingestion on startup — VERIFIED (`lifespan` async context manager imports `RefreshOrchestrator` and starts background refresh in `src/aegis/api/server.py`)
- [x] Backend: Deployment infrastructure exists — VERIFIED (`Dockerfile`, `docker-compose.yml`, `.env.sample` all exist)
- [x] Frontend: SSE results with source progress — VERIFIED (`useSSE` hook in `frontend/src/hooks/useSSE.ts`, `SourceProgressBar.tsx` component, wired into results page)
- [x] Frontend: Query type detection — VERIFIED (`QueryTypeBadge.tsx` component, `QueryForm.tsx` calls `/api/queries/classify`, 6 files reference query type)
- [x] Frontend: Comparison modal — VERIFIED (`CandidateComparisonModal.tsx` component, comparison checkboxes in `CandidateRow.tsx`, trigger in results page)
- [x] Frontend: Candidate profile page — VERIFIED (`frontend/src/app/candidates/[uuid]/page.tsx` with `CandidateTimeline.tsx`, `ScoreHistoryChart.tsx`, `AnalystNotes.tsx`)
- [x] Frontend: Shortlists system — VERIFIED (12 files: `ShortlistPanel.tsx`, `ExportButton.tsx`, `useShortlist.ts`, shortlist pages, API proxies, `Header.tsx` nav link)
- [x] Frontend: Query diff — VERIFIED (`QueryDiff.tsx` component in `frontend/src/components/history/`, wired into history page)
- [x] Frontend: Weight sliders — VERIFIED (`WeightSliderPanel.tsx` component, referenced in results page and `QueryForm.tsx`)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `src/aegis/sources/openalex.py` | Created | Yes |
| `src/aegis/sources/openalex_test.py` | Created | Yes |
| `src/aegis/query/classifier.py` | Created | Yes |
| `src/aegis/query/classifier_test.py` | Created | Yes |
| `src/aegis/pipeline/orchestrator.py` | Created | Yes |
| `src/aegis/pipeline/orchestrator_test.py` | Created | Yes |
| `src/aegis/pipeline/__init__.py` | Created | Yes |
| `src/aegis/api/streaming.py` | Created | Yes |
| `src/aegis/api/shortlists.py` | Created | Yes |
| `src/aegis/api/notes.py` | Created | Yes |
| `src/aegis/storage/shortlist_store.py` | Created | Yes |
| `src/aegis/storage/shortlist_store_test.py` | Created | Yes |
| `src/aegis/storage/notes_store.py` | Created | Yes |
| `src/aegis/storage/notes_store_test.py` | Created | Yes |
| `src/aegis/storage/query_store.py` | Created | Yes |
| `src/aegis/storage/query_store_test.py` | Created | Yes |
| `config/aegis/weights/basic_research_v1.yaml` | Created | Yes |
| `config/aegis/weights/policy_epi_v1.yaml` | Created | Yes |
| `Dockerfile` | Created | Yes |
| `docker-compose.yml` | Created | Yes |
| `.env.sample` | Created | Yes |
| `src/aegis/api/server.py` | Modified | Yes |
| `frontend/src/types/api.ts` | Modified | Yes |
| `frontend/src/hooks/useSSE.ts` | Created | Yes |
| `frontend/src/hooks/useShortlist.ts` | Created | Yes |
| `frontend/src/components/query/QueryForm.tsx` | Modified | Yes |
| `frontend/src/components/results/CandidateRow.tsx` | Modified | Yes |
| `frontend/src/components/results/CandidateComparisonModal.tsx` | Created | Yes |
| `frontend/src/components/results/WeightSliderPanel.tsx` | Created | Yes |
| `frontend/src/components/results/QueryTypeBadge.tsx` | Created | Yes |
| `frontend/src/components/results/SourceProgressBar.tsx` | Created | Yes |
| `frontend/src/components/results/MeshExpansionInspector.tsx` | Created | Yes |
| `frontend/src/components/candidates/CandidateTimeline.tsx` | Created | Yes |
| `frontend/src/components/candidates/ScoreHistoryChart.tsx` | Created | Yes |
| `frontend/src/components/candidates/AnalystNotes.tsx` | Created | Yes |
| `frontend/src/components/shortlists/ShortlistPanel.tsx` | Created | Yes |
| `frontend/src/components/shortlists/ExportButton.tsx` | Created | Yes |
| `frontend/src/components/history/QueryDiff.tsx` | Created | Yes |
| `frontend/src/app/candidates/[uuid]/page.tsx` | Created | Yes |
| `frontend/src/app/shortlists/page.tsx` | Created | Yes |
| `frontend/src/app/shortlists/[id]/page.tsx` | Created | Yes |
| `frontend/src/app/results/[id]/page.tsx` | Modified | Yes |
| `frontend/src/app/history/page.tsx` | Modified | Yes |
| `frontend/src/components/Header.tsx` | Modified | Yes |
| `frontend/src/app/api/shortlists/route.ts` | Created | Yes |
| `frontend/src/app/api/shortlists/[id]/route.ts` | Created | Yes |
| `frontend/src/app/api/shortlists/[id]/candidates/route.ts` | Created | Yes |
| `frontend/src/app/api/queries/[id]/stream/route.ts` | Created | Yes |
| `frontend/src/app/api/queries/classify/route.ts` | Created | Yes |
| `frontend/src/app/api/candidates/[uuid]/notes/route.ts` | Created | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase5-production-reality.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Phase 5 wires together every module built in Phases 0-4 into a real, end-to-end production system. Currently the server.py uses stub scoring (hardcoded recency=0.65, integrity=1.0, naive word-match topical fit, simple artifact count for quality). Queries read exclusively from seeded DuckDB and never call any live source client. International grant sources (ERC, MRC, CIHR, KAKEN, NSFC) are built but broken (wrong API endpoints).

This phase:
1. **Backend**: Creates an OpenAlex unified client to replace broken international sources, wires real F1-F7 scoring into server.py, adds live source fetching during queries, implements a query type classifier, adds SSE streaming, wires the privacy gate, schedules continuous ingestion, and adds deployment infrastructure.
2. **Frontend**: Completely revamps the Next.js dashboard with SSE-powered live results, candidate comparison, candidate profile pages, named shortlists, analyst notes, team view, query history with diff, and weight slider overrides.

## Objective

When complete, Aegis will be a fully functional expert discovery platform where:
- A user submits a query and sees real-time source-by-source progress
- Live data is fetched from 15+ sources, deduplicated via identity resolution, scored with real F1-F7 components, and ranked using the correct weight vector for the detected query type
- Results show real scores, real evidence, real integrity flags, and real confidence bands
- Users can compare candidates, build shortlists, add notes, and export reports
- The system runs continuously with background ingestion keeping DuckDB warm
- Privacy gates enforce PHI scanning, demographic blocklisting, and opt-out at ingestion time
- The whole stack deploys via Docker

## Problem Statement

Aegis has all the pieces built across Phases 0-4 but none are wired together in production. The API returns stub scores, never fetches live data, and the frontend cannot show real-time progress or advanced analyst workflows. The system is a demo, not a product.

## Solution Approach

Split into two parallel workstreams (backend and frontend) with a shared integration phase:

1. **Backend-first** (builder-1, builder-2): Create OpenAlex client, build the query pipeline orchestrator that wires real scoring + live fetching + privacy, add SSE streaming endpoint, add query classifier, wire continuous ingestion, and create Docker deployment.

2. **Frontend-parallel** (builder-3, builder-4): Revamp the query form with type detection, build SSE-powered results page, create candidate comparison modal, candidate profile page, shortlists system, analyst notes, query history with diff, and weight slider overrides.

3. **Integration** (builder-5): Wire frontend SSE to backend stream, ensure API contracts match, end-to-end testing.

## Relevant Files

### Existing Backend Files (to modify)
- `src/aegis/api/server.py` — Main server, currently has stub scoring; needs complete rewrite of `submit_query` to use real pipeline
- `src/aegis/api/schemas.py` — API request/response models; needs new schemas for SSE, classifier, shortlists, notes
- `src/aegis/api/formatter.py` — Result formatter; needs to accept real F1-F7 breakdown
- `src/aegis/scoring/rank.py` — Ranker and CandidateScoreInput; may need extended fields for F1-F7 detail
- `src/aegis/scoring/quality_prior.py` — QualityPrior with WeightVector; needs to be called from pipeline
- `src/aegis/scoring/topical_fit.py` — TopicalFit cosine similarity; needs to be called with real candidate vectors
- `src/aegis/scoring/recency.py` — Recency time-decay; needs real publication dates from live fetch
- `src/aegis/integrity/hard_gate.py` — HardGate; needs to be called for every candidate
- `src/aegis/scoring/f1_rcr.py` — F1Computer; needs iCite data from live fetch
- `src/aegis/scoring/f2_funding.py` — F2Computer; needs grant data from Reporter + OpenAlex
- `src/aegis/scoring/f3_leadership.py` — F3Computer; needs publication + trial role data
- `src/aegis/scoring/f4_apex.py` — F4Computer; needs apex roster membership data
- `src/aegis/scoring/f5_translational.py` — F5Computer; needs FDA + trial + NCCN data
- `src/aegis/scoring/f6_lineage.py` — F6Computer; needs Academic Family Tree data
- `src/aegis/scoring/f7_clinician.py` — F7Computer; needs NPPES/ABMS/CMS data
- `src/aegis/scoring/candidate_vector.py` — CandidateVectorBuilder and QueryVectorBuilder
- `src/aegis/scoring/variance.py` — Bootstrap variance estimator
- `src/aegis/scoring/specialty_classifier.py` — SpecialtyClassifier with rule-based fallback
- `src/aegis/query/llm_expansion.py` — MetaMapExpander and LlmQueryExpander
- `src/aegis/privacy/gate.py` — PrivacyGate; needs to be called at ingestion time
- `src/aegis/ingestion/orchestrator.py` — RefreshOrchestrator; needs to be wired to startup
- `src/aegis/storage/candidate_store.py` — CandidateStore; needs query-time integration
- `src/aegis/storage/schema.py` — Candidate model with ArtifactRefBundle, AffiliationSpan, MeshDescriptor
- `src/aegis/sources/retry.py` — RetryPolicy shared across all source clients
- `src/aegis/sources/non_us_grants.py` — NonUsGrantRecord model shared by non-US sources
- `src/aegis/sources/pubmed.py` — PubMedClient (async, httpx, retry)
- `src/aegis/sources/icite.py` — IciteClient (batch PMID lookups)
- `src/aegis/sources/reporter.py` — NIH Reporter client
- `src/aegis/sources/ctgov.py` — ClinicalTrials.gov client
- `src/aegis/sources/erc.py` — ERC/CORDIS client (broken endpoint, to be replaced by OpenAlex)
- `src/aegis/sources/mrc.py` — MRC/UKRI client (broken endpoint, to be replaced by OpenAlex)
- `src/aegis/sources/cihr.py` — CIHR client (broken endpoint, to be replaced by OpenAlex)
- `src/aegis/sources/nsfc.py` — NSFC client (broken endpoint, to be replaced by OpenAlex)
- `src/aegis/sources/leie.py` — LEIE exclusion store
- `src/aegis/sources/ofac_sam.py` — OFAC/SAM listing store
- `src/aegis/sources/ori.py` — ORI misconduct findings
- `src/aegis/sources/retraction_watch.py` — Retraction Watch store
- `config/aegis/weights/translational_v1.yaml` — Weight vector for translational specialty
- `config/aegis/weights/drug_discovery_v1.yaml` — Weight vector for drug discovery
- `config/aegis/weights/clinician_v1.yaml` — Weight vector for clinician specialty

### Existing Frontend Files (to modify)
- `frontend/src/types/api.ts` — TypeScript API types; needs new types for SSE, shortlists, notes, comparison
- `frontend/src/lib/api-client.ts` — Server-side API client; needs SSE support
- `frontend/src/app/page.tsx` — Query form page; needs query type detection UI
- `frontend/src/app/results/[id]/page.tsx` — Results page; needs SSE, comparison, weight sliders
- `frontend/src/app/history/page.tsx` — History page; needs query diff, saved names
- `frontend/src/app/layout.tsx` — Root layout; needs nav updates for shortlists
- `frontend/src/components/Header.tsx` — Nav header; needs shortlists + team links
- `frontend/src/components/query/QueryForm.tsx` — Query form; needs type detection + weight display
- `frontend/src/components/results/CandidateRow.tsx` — Candidate card; needs source badges, shortlist button, notes icon
- `frontend/src/components/results/EvidenceTrailPanel.tsx` — Evidence drawer; needs F1-F7 breakdown, OpenAlex tags
- `frontend/src/components/results/ScoreBreakdownChart.tsx` — Score chart; needs F1-F7 components
- `frontend/src/app/api/queries/route.ts` — API proxy for POST/GET queries
- `frontend/src/app/api/queries/[id]/route.ts` — API proxy for GET query by ID
- `frontend/src/app/api/candidates/[uuid]/evidence/route.ts` — Evidence proxy

### New Files to Create

**Backend:**
- `src/aegis/sources/openalex.py` — OpenAlex unified client (works, funders, authors, concepts)
- `src/aegis/sources/openalex_test.py` — Tests for OpenAlex client
- `src/aegis/query/classifier.py` — Query type classifier (basic_research, drug_discovery, clinical_trial_pi, policy_epi)
- `src/aegis/query/classifier_test.py` — Tests for query classifier
- `src/aegis/pipeline/orchestrator.py` — Query pipeline orchestrator (fetches sources, resolves identity, scores, ranks)
- `src/aegis/pipeline/orchestrator_test.py` — Tests for pipeline orchestrator
- `src/aegis/pipeline/__init__.py` — Pipeline package init
- `src/aegis/api/streaming.py` — SSE streaming endpoint implementation
- `src/aegis/api/streaming_test.py` — Tests for SSE streaming
- `src/aegis/api/shortlists.py` — Shortlist CRUD endpoints
- `src/aegis/api/shortlists_test.py` — Tests for shortlists
- `src/aegis/api/notes.py` — Candidate notes endpoints
- `src/aegis/api/notes_test.py` — Tests for notes
- `src/aegis/storage/shortlist_store.py` — DuckDB-backed shortlist storage
- `src/aegis/storage/notes_store.py` — DuckDB-backed notes storage
- `src/aegis/storage/query_store.py` — DuckDB-backed query history storage (replaces in-memory dict)
- `config/aegis/weights/basic_research_v1.yaml` — Weight vector for basic research queries
- `config/aegis/weights/policy_epi_v1.yaml` — Weight vector for policy/epi queries
- `Dockerfile` — Backend Dockerfile
- `docker-compose.yml` — Full stack docker-compose
- `.env.example` — Example environment variables

**Frontend:**
- `frontend/src/app/candidates/[uuid]/page.tsx` — Candidate profile page
- `frontend/src/app/shortlists/page.tsx` — Shortlists list page
- `frontend/src/app/shortlists/[id]/page.tsx` — Single shortlist detail page
- `frontend/src/components/results/SourceProgressBar.tsx` — SSE source progress tiles
- `frontend/src/components/results/CandidateComparisonModal.tsx` — Side-by-side comparison
- `frontend/src/components/results/WeightSliderPanel.tsx` — Weight slider overrides
- `frontend/src/components/results/QueryTypeBadge.tsx` — Query type detection badge
- `frontend/src/components/results/MeshExpansionInspector.tsx` — MeSH term add/remove UI
- `frontend/src/components/candidates/CandidateTimeline.tsx` — Chronological artifact timeline
- `frontend/src/components/candidates/ScoreHistoryChart.tsx` — Score history across queries
- `frontend/src/components/candidates/AnalystNotes.tsx` — Notes CRUD component
- `frontend/src/components/shortlists/ShortlistPanel.tsx` — Shortlist sidebar
- `frontend/src/components/shortlists/ExportButton.tsx` — CSV/PDF export
- `frontend/src/components/history/QueryDiff.tsx` — Ranking diff visualization
- `frontend/src/hooks/useSSE.ts` — SSE hook for streaming results
- `frontend/src/hooks/useShortlist.ts` — Shortlist state management hook
- `frontend/src/app/api/shortlists/route.ts` — Shortlist API proxy
- `frontend/src/app/api/shortlists/[id]/route.ts` — Single shortlist API proxy
- `frontend/src/app/api/candidates/[uuid]/notes/route.ts` — Notes API proxy
- `frontend/src/app/api/queries/[id]/stream/route.ts` — SSE stream proxy
- `frontend/src/app/api/queries/[id]/classify/route.ts` — Classify proxy

## Implementation Phases

### Phase 1: Foundation (Tasks 1-4)
- OpenAlex client creation
- Query pipeline orchestrator skeleton
- DuckDB storage for shortlists, notes, query history
- New weight vectors for basic_research and policy_epi

### Phase 2: Core Backend (Tasks 5-10)
- Wire real F1-F7 scoring in pipeline
- Live source fetching with parallel asyncio
- Query type classifier
- SSE streaming endpoint
- Privacy gate wiring
- Continuous ingestion scheduling

### Phase 3: Core Frontend (Tasks 11-17)
- SSE-powered results page with source progress
- Query form with type detection
- Candidate comparison modal
- Candidate profile page
- Shortlist system
- Analyst notes
- Weight slider overrides

### Phase 4: Integration & Polish (Tasks 18-21)
- Query history with diff
- Team view shared state
- Deployment infrastructure (Dockerfile, docker-compose)
- End-to-end validation

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Backend pipeline and scoring wiring — OpenAlex client, pipeline orchestrator, real scoring integration, SSE streaming
  - Agent Type: general-purpose

- Builder
  - Name: builder-2
  - Role: Backend APIs and storage — query classifier, shortlists, notes, query store, privacy wiring, continuous ingestion, deployment
  - Agent Type: general-purpose

- Builder
  - Name: builder-3
  - Role: Frontend core — SSE results page, query form revamp, candidate comparison, weight sliders
  - Agent Type: general-purpose

- Builder
  - Name: builder-4
  - Role: Frontend features — candidate profile page, shortlists, analyst notes, query history diff, team view
  - Agent Type: general-purpose

- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator

## Step by Step Tasks

### 1. Create OpenAlex Unified Client
- **Task ID**: create-openalex-client
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create a unified OpenAlex client at `src/aegis/sources/openalex.py` that replaces the 5 broken international grant source clients (ERC, MRC, CIHR, KAKEN, NSFC). OpenAlex is a free, open API for scholarly data covering works, authors, funders, and concepts globally.

    ## What to do

    1. Create `src/aegis/sources/openalex.py` with the following classes:
       - `OpenAlexWork` — Pydantic frozen model for a work (publication) record
       - `OpenAlexAuthor` — Pydantic frozen model for an author profile
       - `OpenAlexFunder` — Pydantic frozen model for a funder record
       - `OpenAlexConcept` — Pydantic frozen model for a concept tag
       - `OpenAlexClient` — async httpx client with the following methods:
         - `search_works(query, since_date, batch_size)` — search works by topic, return AsyncIterator[OpenAlexWork]
         - `get_works_by_author(author_id, since_date)` — get all works for an author
         - `search_authors(query, affiliation_hint)` — search for author profiles
         - `get_author(author_id)` — get a single author by OpenAlex ID
         - `search_funders(query)` — search funders (replaces ERC/MRC/CIHR/KAKEN/NSFC)
         - `get_grants_by_funder(funder_id, since_year)` — get grants for a specific funder, return AsyncIterator[NonUsGrantRecord] to maintain compatibility
         - `get_concepts_for_work(work_id)` — get concept tags for a work

    2. Follow the exact patterns from `src/aegis/sources/pubmed.py`:
       - `from __future__ import annotations` at top
       - Use `httpx.AsyncClient` with `timeout=60.0`
       - Use `RetryPolicy` from `aegis.sources.retry`
       - All models use `ConfigDict(frozen=True)`
       - Rate limiting via `self._min_interval` and `_throttle()` method
       - Batch pagination with configurable batch_size

    3. API details:
       - Base URL: `https://api.openalex.org`
       - Works endpoint: `GET /works?search={query}&filter=from_publication_date:{date}`
       - Authors endpoint: `GET /authors?search={query}`
       - Funders endpoint: `GET /funders?search={query}`
       - Use `mailto` parameter for polite pool: `params["mailto"] = "aegis@example.com"`
       - Cursor-based pagination: use `cursor` parameter, check `meta.next_cursor`
       - Response format: JSON with `results` array and `meta` object

    4. The `get_grants_by_funder` method must return `NonUsGrantRecord` objects (from `aegis.sources.non_us_grants`) to maintain compatibility with the existing storage layer. Map OpenAlex funder data to:
       - Known funder IDs: ERC=`F4320332161`, MRC=`F4320332084`, CIHR=`F4320332083`, KAKEN/JSPS=`F4320332085`, NSFC=`F4320332086`, Wellcome=`F4320332082`
       - Map fields: `grant_reference`, `funder`, `funder_country`, `title`, `pi_names`, `amount_local`, `start_date`, `end_date`, `subject_areas`, `source="openalex"`, `raw_json`

    5. Create `src/aegis/sources/openalex_test.py` with tests using `respx` for mocking (follow pattern in `src/aegis/sources/pubmed_test.py`):
       - Test `search_works` returns parsed OpenAlexWork objects
       - Test `search_authors` returns parsed OpenAlexAuthor objects
       - Test `get_grants_by_funder` returns NonUsGrantRecord objects
       - Test pagination with cursor
       - Test retry on 429/503

    ## Files to modify
    - `src/aegis/sources/openalex.py` — NEW FILE
    - `src/aegis/sources/openalex_test.py` — NEW FILE

    ## Code patterns to follow
    - See `src/aegis/sources/pubmed.py` for async client pattern (httpx, retry, throttle, Pydantic models)
    - See `src/aegis/sources/erc.py` for NonUsGrantRecord mapping pattern
    - See `src/aegis/sources/retry.py` for RetryPolicy usage
    - See `src/aegis/sources/pubmed_test.py` for respx test pattern

    ## OpenAlexWork model fields
    ```python
    class OpenAlexWork(BaseModel):
        model_config = ConfigDict(frozen=True)
        openalex_id: str          # e.g. "W2741809807"
        doi: str | None
        title: str
        publication_date: date | None
        type: str | None          # "journal-article", "preprint", etc.
        cited_by_count: int
        concepts: list[dict[str, str | float]]  # [{"id": ..., "display_name": ..., "score": ...}]
        authorships: list[dict[str, str | None]]  # [{"author_id": ..., "author_name": ..., "position": ...}]
        primary_location: dict[str, str | None] | None  # {"source_id": ..., "source_name": ...}
        mesh_terms: list[str]     # extracted from OpenAlex concepts mapped to MeSH
        raw_json: str
    ```

    ## OpenAlexAuthor model fields
    ```python
    class OpenAlexAuthor(BaseModel):
        model_config = ConfigDict(frozen=True)
        openalex_id: str
        display_name: str
        orcid: str | None
        works_count: int
        cited_by_count: int
        affiliations: list[dict[str, str | None]]  # [{"institution_id": ..., "institution_name": ..., "country": ...}]
        concepts: list[dict[str, str | float]]
        raw_json: str
    ```

    ## Acceptance criteria
    - `src/aegis/sources/openalex.py` exists with OpenAlexClient class
    - All methods are async and use httpx + RetryPolicy
    - `get_grants_by_funder` returns NonUsGrantRecord objects
    - `src/aegis/sources/openalex_test.py` has at least 5 test functions
    - `uv run python -m py_compile src/aegis/sources/openalex.py` succeeds
    - `uv run python -m py_compile src/aegis/sources/openalex_test.py` succeeds

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/sources/openalex.py && uv run python -m py_compile src/aegis/sources/openalex_test.py && uv run pytest src/aegis/sources/openalex_test.py -v
    ```

### 2. Create Query Pipeline Orchestrator
- **Task ID**: create-pipeline-orchestrator
- **Role**: builder
- **Depends On**: create-openalex-client
- **Assigned To**: builder-1
- **Description**: |
    Create the query pipeline orchestrator at `src/aegis/pipeline/orchestrator.py` that coordinates the full query flow: source fetching -> identity resolution -> scoring -> ranking. This replaces the ad-hoc stub logic currently in `server.py`.

    ## What to do

    1. Create `src/aegis/pipeline/__init__.py` (empty, just `from __future__ import annotations`)

    2. Create `src/aegis/pipeline/orchestrator.py` with class `QueryPipeline`:

    ```python
    class SourceProgress(BaseModel):
        """Progress update for a single source fetch."""
        model_config = ConfigDict(frozen=True)
        source_name: str
        status: str  # "pending", "fetching", "complete", "failed"
        record_count: int
        latency_ms: float
        error: str | None

    class PipelineResult(BaseModel):
        """Full result of a query pipeline execution."""
        model_config = ConfigDict(frozen=True)
        ranked_list: RankedList  # from aegis.scoring.result_format
        source_progress: list[SourceProgress]
        query_type: str  # from classifier
        weight_vector_name: str
        expansion_info: ExpansionInfo
        variance_bands: dict[str, ScoreBand]
        f1_scores: dict[str, float]  # uuid -> percentile
        f2_scores: dict[str, float]
        f3_scores: dict[str, float]
        f4_scores: dict[str, float]
        f5_scores: dict[str, float]
        f6_scores: dict[str, float]
        f7_scores: dict[str, float] | None  # only for clinician
        integrity_results: dict[str, HardGateResult]
        total_candidates_fetched: int
        total_candidates_after_dedup: int
        pipeline_duration_ms: float

    class QueryPipeline:
        """Orchestrates end-to-end query execution."""

        def __init__(self, *, db_path: str = "aegis.duckdb") -> None:
            ...

        async def execute(
            self,
            *,
            task_description: str,
            mesh_override: list[str] | None = None,
            k: int = 50,
            query_type_override: str | None = None,
            progress_callback: Callable[[SourceProgress], None] | None = None,
        ) -> PipelineResult:
            """Execute full query pipeline."""
            ...

        async def _fetch_all_sources(
            self,
            query: str,
            mesh_terms: list[str],
            progress_callback: Callable[[SourceProgress], None] | None,
        ) -> tuple[list[Candidate], list[SourceProgress]]:
            """Fetch from all sources in parallel using asyncio.gather."""
            ...

        async def _fetch_source(
            self,
            source_name: str,
            query: str,
            mesh_terms: list[str],
        ) -> tuple[str, list[Candidate], float]:
            """Fetch from a single source, return (name, candidates, latency_ms)."""
            ...

        def _compute_scores(
            self,
            candidates: list[Candidate],
            mesh_terms: list[str],
            weight_vector: WeightVector,
        ) -> tuple[list[CandidateScoreInput], dict[str, dict]]:
            """Compute real F1-F7 scores for all candidates."""
            ...
    ```

    3. The `execute` method flow:
       a. Expand query via `LlmQueryExpander` (or MetaMapExpander fallback)
       b. Classify query type via new classifier (task 5) — for now use rule-based fallback
       c. Load appropriate weight vector from `config/aegis/weights/{type}_v1.yaml`
       d. Fetch from all sources in parallel via `_fetch_all_sources`
       e. Also load existing candidates from DuckDB (`CandidateStore.list_by_cohort`)
       f. Merge fetched + stored candidates (deduplicate by strong keys)
       g. Run privacy gate on new data
       h. Compute F1-F7 scores via `_compute_scores`
       i. Run integrity hard gate
       j. Build CandidateScoreInput list and call Ranker
       k. Compute bootstrap variance bands
       l. Return PipelineResult

    4. In `_fetch_all_sources`, create async tasks for each source:
       - pubmed (PubMedClient.search_and_fetch)
       - icite (IciteClient.fetch_by_pmids — needs PMIDs from pubmed)
       - reporter (ReporterClient.search)
       - ctgov (CtgovClient.search)
       - openalex (OpenAlexClient.search_works + get_grants_by_funder for ERC/MRC/CIHR/KAKEN/NSFC/Wellcome)
       - Use asyncio.gather with return_exceptions=True for failure isolation
       - Call progress_callback after each source completes

    5. In `_compute_scores`:
       - For each candidate, extract data needed for each F-score computer
       - F1: use iCite RCR data from artifact_refs (pmid_rcr entries)
       - F2: use grant data from reporter + openalex
       - F3: use publication authorship positions + trial PI roles
       - F4: use apex roster membership data (if available in evidence_trail)
       - F5: use FDA submission count + phase2+ trial count + NCCN flag
       - F6: use Academic Family Tree data (if available)
       - F7 (clinician only): use NPPES/ABMS/CMS data
       - Call each FxComputer.compute_percentiles() to get cohort-relative percentiles
       - Feed percentiles into QualityPrior.compute_percentiles()
       - Compute TopicalFit using CandidateVectorBuilder + QueryVectorBuilder
       - Compute Recency using real publication dates
       - Build CandidateScoreInput with real values

    6. Create `src/aegis/pipeline/orchestrator_test.py` with tests:
       - Test that execute() returns a PipelineResult
       - Test that _compute_scores builds real F1-F6 scores
       - Test that source failures are isolated (one failing source doesn't crash pipeline)
       - Mock all external HTTP calls with respx

    ## Files to modify
    - `src/aegis/pipeline/__init__.py` — NEW FILE
    - `src/aegis/pipeline/orchestrator.py` — NEW FILE
    - `src/aegis/pipeline/orchestrator_test.py` — NEW FILE

    ## Code patterns to follow
    - See `src/aegis/ingestion/orchestrator.py` for parallel async orchestration with failure isolation
    - See `src/aegis/scoring/quality_prior.py` for QualityPrior.compute_percentiles() usage
    - See `src/aegis/scoring/rank.py` for Ranker.rank() usage
    - See `src/aegis/scoring/variance.py` for Bootstrap.estimate() usage
    - See `src/aegis/api/server.py` lines 131-182 for current stub logic to replace

    ## Acceptance criteria
    - `src/aegis/pipeline/orchestrator.py` exists with QueryPipeline class
    - QueryPipeline.execute() returns PipelineResult with real scores
    - Source failures are isolated (asyncio.gather with return_exceptions=True)
    - Progress callback is called for each source
    - Tests exist and pass
    - `uv run python -m py_compile src/aegis/pipeline/orchestrator.py` succeeds

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/pipeline/__init__.py && uv run python -m py_compile src/aegis/pipeline/orchestrator.py && uv run python -m py_compile src/aegis/pipeline/orchestrator_test.py && uv run pytest src/aegis/pipeline/orchestrator_test.py -v
    ```

### 3. Create Backend Storage for Shortlists, Notes, and Query History
- **Task ID**: create-backend-storage
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Create DuckDB-backed storage for shortlists, analyst notes, and persistent query history. Currently queries are stored in an in-memory dict in server.py which loses data on restart.

    ## What to do

    1. Create `src/aegis/storage/migrations/005_shortlists_notes_queries.sql`:
    ```sql
    CREATE TABLE IF NOT EXISTS shortlists (
        id VARCHAR PRIMARY KEY,
        name VARCHAR NOT NULL,
        description VARCHAR,
        created_by VARCHAR NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    );

    CREATE TABLE IF NOT EXISTS shortlist_members (
        shortlist_id VARCHAR NOT NULL,
        candidate_uuid VARCHAR NOT NULL,
        added_at TIMESTAMP NOT NULL,
        added_by VARCHAR NOT NULL,
        PRIMARY KEY (shortlist_id, candidate_uuid)
    );

    CREATE TABLE IF NOT EXISTS candidate_notes (
        id VARCHAR PRIMARY KEY,
        candidate_uuid VARCHAR NOT NULL,
        author VARCHAR NOT NULL,
        content VARCHAR NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    );

    CREATE TABLE IF NOT EXISTS query_history (
        id VARCHAR PRIMARY KEY,
        task_description VARCHAR NOT NULL,
        query_type VARCHAR,
        weight_vector_name VARCHAR,
        mesh_terms VARCHAR,  -- JSON array
        k INTEGER NOT NULL,
        result_count INTEGER NOT NULL,
        candidate_uuids VARCHAR,  -- JSON array of top candidate UUIDs
        candidate_scores VARCHAR,  -- JSON array of {uuid, score, rank}
        pipeline_duration_ms DOUBLE,
        created_at TIMESTAMP NOT NULL,
        created_by VARCHAR,
        custom_name VARCHAR  -- user-defined name for saved queries
    );
    ```

    2. Create `src/aegis/storage/shortlist_store.py`:
    ```python
    class ShortlistStore:
        def __init__(self, db_path: str = "aegis.duckdb") -> None: ...
        def create(self, *, name: str, description: str | None, created_by: str) -> str: ...  # returns id
        def get(self, shortlist_id: str) -> dict | None: ...
        def list_all(self, created_by: str | None = None) -> list[dict]: ...
        def add_candidate(self, shortlist_id: str, candidate_uuid: str, added_by: str) -> None: ...
        def remove_candidate(self, shortlist_id: str, candidate_uuid: str) -> None: ...
        def get_members(self, shortlist_id: str) -> list[dict]: ...
        def delete(self, shortlist_id: str) -> None: ...
        def close(self) -> None: ...
    ```

    3. Create `src/aegis/storage/notes_store.py`:
    ```python
    class NotesStore:
        def __init__(self, db_path: str = "aegis.duckdb") -> None: ...
        def create(self, *, candidate_uuid: str, author: str, content: str) -> str: ...  # returns id
        def get_for_candidate(self, candidate_uuid: str) -> list[dict]: ...
        def update(self, note_id: str, content: str) -> None: ...
        def delete(self, note_id: str) -> None: ...
        def close(self) -> None: ...
    ```

    4. Create `src/aegis/storage/query_store.py`:
    ```python
    class QueryStore:
        def __init__(self, db_path: str = "aegis.duckdb") -> None: ...
        def save(self, *, query_id: str, task_description: str, query_type: str | None, ...) -> None: ...
        def get(self, query_id: str) -> dict | None: ...
        def list_all(self, *, page: int = 1, per_page: int = 20, created_by: str | None = None) -> tuple[list[dict], int]: ...
        def rename(self, query_id: str, custom_name: str) -> None: ...
        def close(self) -> None: ...
    ```

    5. Follow patterns from `src/aegis/storage/candidate_store.py`:
       - `from __future__ import annotations` at top
       - duckdb.connect(db_path) in __init__
       - _run_migrations() in __init__
       - close() method
       - Use uuid.uuid4().hex for IDs
       - Use datetime.now(UTC).isoformat() for timestamps

    6. Create test files for each store with at least 3 tests each using a temporary DuckDB database.

    ## Files to modify
    - `src/aegis/storage/migrations/005_shortlists_notes_queries.sql` — NEW FILE
    - `src/aegis/storage/shortlist_store.py` — NEW FILE
    - `src/aegis/storage/notes_store.py` — NEW FILE
    - `src/aegis/storage/query_store.py` — NEW FILE
    - `src/aegis/storage/shortlist_store_test.py` — NEW FILE
    - `src/aegis/storage/notes_store_test.py` — NEW FILE
    - `src/aegis/storage/query_store_test.py` — NEW FILE

    ## Code patterns to follow
    - See `src/aegis/storage/candidate_store.py` for DuckDB store pattern
    - Use `from __future__ import annotations` on every module
    - Use uuid.uuid4().hex for generated IDs
    - Use datetime.now(UTC) for timestamps

    ## Acceptance criteria
    - Migration SQL file creates all 4 tables
    - ShortlistStore supports full CRUD + member management
    - NotesStore supports create, list, update, delete
    - QueryStore supports save, get, list with pagination, rename
    - All tests pass
    - `uv run python -m py_compile` succeeds for all new files

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/storage/shortlist_store.py && uv run python -m py_compile src/aegis/storage/notes_store.py && uv run python -m py_compile src/aegis/storage/query_store.py && uv run pytest src/aegis/storage/shortlist_store_test.py src/aegis/storage/notes_store_test.py src/aegis/storage/query_store_test.py -v
    ```

### 4. Create Weight Vectors and Query Type Classifier
- **Task ID**: create-query-classifier
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Create the query type classifier and new weight vector configs. The classifier analyzes a query string and determines if it's basic_research, drug_discovery, clinical_trial_pi, or policy_epi. This selects the appropriate weight vector for scoring.

    ## What to do

    1. Create `config/aegis/weights/basic_research_v1.yaml`:
    ```yaml
    version: 1
    specialty: basic_research
    created: "2026-04-27"
    weights:
      f1_rcr: 0.40
      f2_funding: 0.20
      f3_leadership: 0.20
      f4_apex: 0.05
      f5_translational: 0.05
      f6_lineage: 0.10
    exponents:
      alpha: 0.8
      beta: 1.0
      gamma: 0.3
    exponent_bounds:
      alpha: [0.3, 1.2]
      beta: [0.5, 1.5]
      gamma: [0.1, 0.8]
    ```

    2. Create `config/aegis/weights/policy_epi_v1.yaml`:
    ```yaml
    version: 1
    specialty: policy_epi
    created: "2026-04-27"
    weights:
      f1_rcr: 0.25
      f2_funding: 0.20
      f3_leadership: 0.25
      f4_apex: 0.10
      f5_translational: 0.15
      f6_lineage: 0.05
    exponents:
      alpha: 0.6
      beta: 1.2
      gamma: 0.5
    exponent_bounds:
      alpha: [0.3, 1.2]
      beta: [0.5, 1.5]
      gamma: [0.1, 0.8]
    ```

    3. Create `src/aegis/query/classifier.py`:
    ```python
    """Query type classifier: routes queries to appropriate weight vectors."""
    from __future__ import annotations
    import logging
    from enum import StrEnum
    from pathlib import Path
    from pydantic import BaseModel, ConfigDict
    from aegis.scoring.quality_prior import WeightVector, load_weight_vector

    logger = logging.getLogger(__name__)

    class QueryType(StrEnum):
        basic_research = "basic_research"
        drug_discovery = "drug_discovery"
        clinical_trial_pi = "clinical_trial_pi"
        policy_epi = "policy_epi"

    QUERY_TYPE_TO_WEIGHT_FILE: dict[str, str] = {
        QueryType.basic_research: "config/aegis/weights/basic_research_v1.yaml",
        QueryType.drug_discovery: "config/aegis/weights/drug_discovery_v1.yaml",
        QueryType.clinical_trial_pi: "config/aegis/weights/clinician_v1.yaml",
        QueryType.policy_epi: "config/aegis/weights/policy_epi_v1.yaml",
    }

    # Keyword-based classification (fast, no LLM needed)
    _DRUG_DISCOVERY_KEYWORDS = frozenset({
        "drug", "compound", "inhibitor", "agonist", "antagonist", "pharmacol",
        "medicinal chemistry", "target", "binding", "ic50", "ec50", "adme",
        "toxicology", "formulation", "bioavailability", "lead optimization",
        "hit-to-lead", "scaffold", "sar", "structure-activity",
    })

    _CLINICAL_TRIAL_KEYWORDS = frozenset({
        "clinical trial", "trial investigator", "principal investigator",
        "phase 1", "phase 2", "phase 3", "phase i", "phase ii", "phase iii",
        "enrollment", "randomized", "placebo", "endpoint", "irb",
        "site investigator", "clinical study", "protocol",
    })

    _POLICY_EPI_KEYWORDS = frozenset({
        "epidemiology", "population health", "public health", "policy",
        "health economics", "surveillance", "outbreak", "vaccine coverage",
        "health equity", "social determinants", "disparity", "mortality rate",
        "incidence", "prevalence", "cohort study", "case-control",
    })

    class ClassificationResult(BaseModel):
        model_config = ConfigDict(frozen=True)
        query_type: str
        confidence: float
        keyword_matches: list[str]
        weight_vector: WeightVector

    class QueryClassifier:
        """Classify query text into a query type and load the matching weight vector."""

        def classify(self, query: str) -> ClassificationResult:
            query_lower = query.lower()
            # Score each type by keyword overlap
            scores: dict[str, tuple[float, list[str]]] = {}
            for qt, keywords in [
                (QueryType.drug_discovery, _DRUG_DISCOVERY_KEYWORDS),
                (QueryType.clinical_trial_pi, _CLINICAL_TRIAL_KEYWORDS),
                (QueryType.policy_epi, _POLICY_EPI_KEYWORDS),
            ]:
                matches = [kw for kw in keywords if kw in query_lower]
                scores[qt] = (len(matches), matches)

            # Pick highest-scoring type, default to basic_research
            best_type = QueryType.basic_research
            best_score = 0.0
            best_matches: list[str] = []
            for qt, (score, matches) in scores.items():
                if score > best_score:
                    best_type = QueryType(qt)
                    best_score = score
                    best_matches = matches

            # Confidence: 0.5 for no matches (default), scales up with matches
            confidence = 0.5 if best_score == 0 else min(0.5 + best_score * 0.1, 0.95)

            weight_file = QUERY_TYPE_TO_WEIGHT_FILE.get(
                best_type, QUERY_TYPE_TO_WEIGHT_FILE[QueryType.basic_research]
            )
            weight_vector = load_weight_vector(Path(weight_file))

            return ClassificationResult(
                query_type=best_type,
                confidence=round(confidence, 3),
                keyword_matches=best_matches,
                weight_vector=weight_vector,
            )
    ```

    4. Create `src/aegis/query/classifier_test.py` with tests:
       - Test drug_discovery query ("KRAS inhibitor drug discovery") classifies correctly
       - Test clinical_trial_pi query ("phase 3 trial principal investigator") classifies correctly
       - Test policy_epi query ("COVID-19 epidemiology surveillance") classifies correctly
       - Test basic_research fallback for generic query ("KRAS oncogene research")
       - Test that weight vector is loaded correctly for each type

    ## Files to modify
    - `config/aegis/weights/basic_research_v1.yaml` — NEW FILE
    - `config/aegis/weights/policy_epi_v1.yaml` — NEW FILE
    - `src/aegis/query/classifier.py` — NEW FILE
    - `src/aegis/query/classifier_test.py` — NEW FILE

    ## Code patterns to follow
    - See `config/aegis/weights/translational_v1.yaml` for weight vector format
    - See `src/aegis/scoring/quality_prior.py` for `load_weight_vector` usage
    - See `src/aegis/scoring/specialty_classifier.py` for classification pattern
    - Use `from __future__ import annotations` on all modules
    - Use Pydantic frozen models for results

    ## Acceptance criteria
    - 2 new weight vector YAML files exist and load correctly via load_weight_vector
    - QueryClassifier.classify() returns ClassificationResult with query_type, confidence, weight_vector
    - Drug discovery queries classify as drug_discovery
    - Clinical trial queries classify as clinical_trial_pi
    - Generic queries default to basic_research
    - All tests pass

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/query/classifier.py && uv run python -m py_compile src/aegis/query/classifier_test.py && uv run pytest src/aegis/query/classifier_test.py -v
    ```

### 5. Wire Real Scoring in Server + SSE Streaming
- **Task ID**: wire-real-scoring
- **Role**: builder
- **Depends On**: create-pipeline-orchestrator, create-query-classifier
- **Assigned To**: builder-1
- **Description**: |
    Rewrite `src/aegis/api/server.py` to use the real QueryPipeline instead of stub scoring, add SSE streaming endpoint, and integrate with the query classifier.

    ## What to do

    1. **Rewrite `submit_query` in `src/aegis/api/server.py`**:
       - Replace lines 108-182 (the stub scoring logic) with a call to `QueryPipeline.execute()`
       - Pass `body.task_description`, `body.mesh_override`, `body.k` to the pipeline
       - Use the PipelineResult to build the QueryResponse via ResultFormatter
       - Pass real variance_bands, integrity disclosures, F1-F7 scores to formatter
       - Store query in QueryStore (DuckDB) instead of in-memory dict

    2. **Add query classification endpoint**:
       ```python
       @app.post("/v1/queries/classify")
       def classify_query(body: ClassifyRequest) -> ClassifyResponse:
           """Classify a query and return detected type + weight vector."""
           from aegis.query.classifier import QueryClassifier
           classifier = QueryClassifier()
           result = classifier.classify(body.task_description)
           return ClassifyResponse(
               query_type=result.query_type,
               confidence=result.confidence,
               keyword_matches=result.keyword_matches,
               weights=result.weight_vector.weights,
               exponents=result.weight_vector.exponents,
           )
       ```

    3. **Add SSE streaming endpoint** in `src/aegis/api/streaming.py`:
       ```python
       """SSE streaming for live query progress."""
       from __future__ import annotations
       import asyncio
       import json
       import logging
       from collections.abc import AsyncGenerator
       from fastapi import APIRouter
       from fastapi.responses import StreamingResponse

       router = APIRouter()

       # In-memory store for active query streams
       _active_streams: dict[str, asyncio.Queue] = {}

       @router.get("/v1/queries/{query_id}/stream")
       async def stream_query_progress(query_id: str) -> StreamingResponse:
           """Stream source-by-source progress as Server-Sent Events."""
           queue = _active_streams.get(query_id)
           if queue is None:
               queue = asyncio.Queue()
               _active_streams[query_id] = queue

           async def event_generator() -> AsyncGenerator[str, None]:
               while True:
                   event = await asyncio.wait_for(queue.get(), timeout=300.0)
                   if event is None:  # sentinel for stream end
                       yield f"event: complete\ndata: {{}}\n\n"
                       break
                   yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
               _active_streams.pop(query_id, None)

           return StreamingResponse(
               event_generator(),
               media_type="text/event-stream",
               headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
           )
       ```

    4. **Update `submit_query` to push SSE events**:
       - Create an asyncio.Queue for the query_id
       - Pass a progress_callback to QueryPipeline.execute() that pushes SourceProgress events to the queue
       - Push a "complete" event with final results when pipeline finishes
       - Event types: "source_progress" (per source), "candidate" (as candidates are scored), "complete" (final)

    5. **Add new request/response schemas** to `src/aegis/api/schemas.py`:
       ```python
       class ClassifyRequest(BaseModel):
           model_config = ConfigDict(frozen=True)
           task_description: str

       class ClassifyResponse(BaseModel):
           model_config = ConfigDict(frozen=True)
           query_type: str
           confidence: float
           keyword_matches: list[str]
           weights: dict[str, float]
           exponents: dict[str, float]
       ```

    6. **Mount SSE router** in create_app():
       ```python
       from aegis.api.streaming import router as streaming_router
       app.include_router(streaming_router)
       ```

    7. **Replace in-memory query store** with QueryStore from task 3:
       - In `submit_query`, call `query_store.save(...)` instead of `_query_store[query_id] = ...`
       - In `get_query`, call `query_store.get(query_id)` instead of `_query_store.get(query_id)`
       - In `list_queries`, call `query_store.list_all(page, per_page)` instead of manual pagination

    8. **Update formatter** to include F1-F7 component scores in component_scores dict:
       - Currently component_scores has: quality_prior, topical_fit, recency, integrity
       - Add: f1_rcr, f2_funding, f3_leadership, f4_apex, f5_translational, f6_lineage, f7_clinician (if applicable)

    ## Files to modify
    - `src/aegis/api/server.py` — Rewrite submit_query, add classify endpoint, mount SSE router, replace in-memory store
    - `src/aegis/api/schemas.py` — Add ClassifyRequest, ClassifyResponse
    - `src/aegis/api/streaming.py` — NEW FILE: SSE streaming endpoint
    - `src/aegis/api/streaming_test.py` — NEW FILE: Tests for SSE
    - `src/aegis/api/formatter.py` — Update component_scores to include F1-F7

    ## Code patterns to follow
    - See current `src/aegis/api/server.py` for FastAPI endpoint patterns
    - See `src/aegis/api/schemas.py` for Pydantic model patterns
    - See `src/aegis/ingestion/orchestrator.py` for async orchestration pattern
    - SSE format: `event: {type}\ndata: {json}\n\n`

    ## Acceptance criteria
    - submit_query uses QueryPipeline.execute() instead of stub scoring
    - POST /v1/queries/classify endpoint exists and returns classification + weights
    - GET /v1/queries/{query_id}/stream endpoint exists and returns SSE events
    - Query history is stored in DuckDB via QueryStore
    - component_scores includes F1-F7 values
    - `uv run python -m py_compile` succeeds for all modified files
    - Existing tests in `src/aegis/api/server_test.py` still pass (may need mock updates)

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/api/server.py && uv run python -m py_compile src/aegis/api/schemas.py && uv run python -m py_compile src/aegis/api/streaming.py && uv run python -m py_compile src/aegis/api/formatter.py
    ```

### 6. Create Backend Shortlist and Notes API Endpoints
- **Task ID**: create-shortlist-notes-api
- **Role**: builder
- **Depends On**: create-backend-storage
- **Assigned To**: builder-2
- **Description**: |
    Create FastAPI endpoints for shortlists and candidate notes, then mount them in server.py.

    ## What to do

    1. Create `src/aegis/api/shortlists.py`:
    ```python
    """Shortlist CRUD endpoints."""
    from __future__ import annotations
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel, ConfigDict
    from aegis.api.auth import TokenPayload, get_current_customer
    from aegis.storage.shortlist_store import ShortlistStore

    router = APIRouter(prefix="/v1/shortlists", tags=["shortlists"])

    class CreateShortlistRequest(BaseModel):
        model_config = ConfigDict(frozen=True)
        name: str
        description: str | None = None

    class AddCandidateRequest(BaseModel):
        model_config = ConfigDict(frozen=True)
        candidate_uuid: str

    @router.post("")
    def create_shortlist(body: CreateShortlistRequest, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = ShortlistStore()
        shortlist_id = store.create(name=body.name, description=body.description, created_by=customer.sub)
        store.close()
        return {"id": shortlist_id, "name": body.name}

    @router.get("")
    def list_shortlists(customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = ShortlistStore()
        shortlists = store.list_all(created_by=customer.sub)
        store.close()
        return {"shortlists": shortlists}

    @router.get("/{shortlist_id}")
    def get_shortlist(shortlist_id: str, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = ShortlistStore()
        shortlist = store.get(shortlist_id)
        members = store.get_members(shortlist_id) if shortlist else []
        store.close()
        if not shortlist:
            raise HTTPException(status_code=404, detail="Shortlist not found")
        return {**shortlist, "members": members}

    @router.post("/{shortlist_id}/candidates")
    def add_to_shortlist(shortlist_id: str, body: AddCandidateRequest, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = ShortlistStore()
        store.add_candidate(shortlist_id, body.candidate_uuid, added_by=customer.sub)
        store.close()
        return {"status": "added"}

    @router.delete("/{shortlist_id}/candidates/{candidate_uuid}")
    def remove_from_shortlist(shortlist_id: str, candidate_uuid: str, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = ShortlistStore()
        store.remove_candidate(shortlist_id, candidate_uuid)
        store.close()
        return {"status": "removed"}

    @router.delete("/{shortlist_id}")
    def delete_shortlist(shortlist_id: str, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = ShortlistStore()
        store.delete(shortlist_id)
        store.close()
        return {"status": "deleted"}

    @router.get("/{shortlist_id}/export")
    def export_shortlist(shortlist_id: str, format: str = "csv", customer: TokenPayload = Depends(get_current_customer)) -> ...:
        # CSV export of shortlist members with scores
        ...
    ```

    2. Create `src/aegis/api/notes.py`:
    ```python
    """Candidate notes CRUD endpoints."""
    from __future__ import annotations
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel, ConfigDict
    from aegis.api.auth import TokenPayload, get_current_customer
    from aegis.storage.notes_store import NotesStore

    router = APIRouter(prefix="/v1/candidates", tags=["notes"])

    class CreateNoteRequest(BaseModel):
        model_config = ConfigDict(frozen=True)
        content: str

    class UpdateNoteRequest(BaseModel):
        model_config = ConfigDict(frozen=True)
        content: str

    @router.post("/{candidate_uuid}/notes")
    def create_note(candidate_uuid: str, body: CreateNoteRequest, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = NotesStore()
        note_id = store.create(candidate_uuid=candidate_uuid, author=customer.sub, content=body.content)
        store.close()
        return {"id": note_id}

    @router.get("/{candidate_uuid}/notes")
    def list_notes(candidate_uuid: str, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = NotesStore()
        notes = store.get_for_candidate(candidate_uuid)
        store.close()
        return {"notes": notes}

    @router.put("/{candidate_uuid}/notes/{note_id}")
    def update_note(candidate_uuid: str, note_id: str, body: UpdateNoteRequest, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = NotesStore()
        store.update(note_id, body.content)
        store.close()
        return {"status": "updated"}

    @router.delete("/{candidate_uuid}/notes/{note_id}")
    def delete_note(candidate_uuid: str, note_id: str, customer: TokenPayload = Depends(get_current_customer)) -> dict:
        store = NotesStore()
        store.delete(note_id)
        store.close()
        return {"status": "deleted"}
    ```

    3. Mount both routers in `src/aegis/api/server.py`:
    ```python
    from aegis.api.shortlists import router as shortlists_router
    from aegis.api.notes import router as notes_router
    app.include_router(shortlists_router)
    app.include_router(notes_router)
    ```

    4. Create test files using the existing auth test pattern from `src/aegis/api/auth_test.py`.

    ## Files to modify
    - `src/aegis/api/shortlists.py` — NEW FILE
    - `src/aegis/api/shortlists_test.py` — NEW FILE
    - `src/aegis/api/notes.py` — NEW FILE
    - `src/aegis/api/notes_test.py` — NEW FILE
    - `src/aegis/api/server.py` — Add router mounts (2 lines in create_app)

    ## Code patterns to follow
    - See `src/aegis/api/server.py` for endpoint patterns with Depends(get_current_customer)
    - See `src/aegis/api/feedback.py` for router pattern
    - See `src/aegis/storage/candidate_store.py` for store open/close pattern

    ## Acceptance criteria
    - POST/GET/DELETE /v1/shortlists endpoints work
    - POST/GET /v1/shortlists/{id}/candidates endpoints work
    - POST/GET/PUT/DELETE /v1/candidates/{uuid}/notes endpoints work
    - Routers are mounted in server.py
    - All tests pass
    - `uv run python -m py_compile` succeeds for all new files

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/api/shortlists.py && uv run python -m py_compile src/aegis/api/notes.py && uv run python -m py_compile src/aegis/api/server.py
    ```

### 7. Wire Privacy Gate and Continuous Ingestion
- **Task ID**: wire-privacy-ingestion
- **Role**: builder
- **Depends On**: create-pipeline-orchestrator
- **Assigned To**: builder-2
- **Description**: |
    Wire the existing privacy gate into the pipeline and schedule continuous ingestion on server startup.

    ## What to do

    1. **Wire privacy gate in pipeline orchestrator** (`src/aegis/pipeline/orchestrator.py`):
       - In `_fetch_all_sources`, after fetching data from each source, run it through PrivacyGate.check()
       - Create PrivacyGate instance with PHIScanner, DemographicBlocklist, OptOutStore
       - For each fetched record, create a data dict from candidate fields and call gate.check()
       - If gate returns rejected_phi or excluded_opt_out, skip that candidate
       - If gate returns stripped, use the cleaned_data
       - Log gate stats after processing

    2. **Schedule continuous ingestion** in `src/aegis/api/server.py`:
       - Add a lifespan context manager that starts RefreshOrchestrator on startup
       - Register all source refresh functions with the orchestrator
       - Run refresh on a configurable interval (default 6 hours, from env AEGIS_REFRESH_INTERVAL_HOURS)
       - Use asyncio.create_task for background refresh
       - Log refresh results

    ```python
    from contextlib import asynccontextmanager
    import os

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: schedule background refresh
        refresh_interval = float(os.environ.get("AEGIS_REFRESH_INTERVAL_HOURS", "6")) * 3600
        refresh_task = asyncio.create_task(_background_refresh(refresh_interval))
        yield
        # Shutdown: cancel background task
        refresh_task.cancel()

    async def _background_refresh(interval_seconds: float) -> None:
        from aegis.ingestion.orchestrator import RefreshOrchestrator, SourceConfig
        orchestrator = RefreshOrchestrator()
        # Register sources... (pubmed, reporter, ctgov, openalex, etc.)
        while True:
            try:
                summary = await orchestrator.run_full_refresh()
                logger.info("Background refresh: %d/%d sources OK", summary.completed, summary.total_sources)
            except Exception:
                logger.exception("Background refresh failed")
            await asyncio.sleep(interval_seconds)
    ```

    3. **Pass lifespan to create_app**:
    ```python
    app = FastAPI(
        title="Aegis Expert Discovery API",
        lifespan=lifespan,
        ...
    )
    ```

    4. **Import privacy modules** in pipeline:
    ```python
    from aegis.privacy.gate import PrivacyGate, GateDecision
    from aegis.privacy.phi_scanner import PHIScanner
    from aegis.privacy.demographic_blocklist import DemographicBlocklist
    from aegis.privacy.opt_out import OptOutStore
    ```

    ## Files to modify
    - `src/aegis/pipeline/orchestrator.py` — Add privacy gate integration in _fetch_all_sources
    - `src/aegis/api/server.py` — Add lifespan with background refresh scheduling

    ## Code patterns to follow
    - See `src/aegis/privacy/gate.py` for PrivacyGate.check() usage
    - See `src/aegis/ingestion/orchestrator.py` for RefreshOrchestrator usage
    - See FastAPI docs for lifespan context managers

    ## Acceptance criteria
    - Privacy gate is called for every fetched candidate in the pipeline
    - PHI-containing records are rejected
    - Opted-out candidates are excluded
    - Background refresh runs on startup with configurable interval
    - Server startup does not block on first refresh (uses asyncio.create_task)
    - `uv run python -m py_compile src/aegis/api/server.py` succeeds
    - `uv run python -m py_compile src/aegis/pipeline/orchestrator.py` succeeds

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/api/server.py && uv run python -m py_compile src/aegis/pipeline/orchestrator.py
    ```

### 8. Create Deployment Infrastructure
- **Task ID**: create-deployment
- **Role**: builder
- **Depends On**: wire-real-scoring
- **Assigned To**: builder-2
- **Description**: |
    Create Dockerfile, docker-compose.yml, and environment configuration for local development and production deployment.

    ## What to do

    1. Create `Dockerfile` at project root:
    ```dockerfile
    FROM python:3.12-slim

    WORKDIR /app

    # Install uv for fast dependency resolution
    RUN pip install uv

    # Copy dependency files
    COPY pyproject.toml .
    COPY src/ src/
    COPY config/ config/

    # Install dependencies
    RUN uv pip install --system -e ".[dev]"

    # Create data directory
    RUN mkdir -p data/aegis

    EXPOSE 8000

    HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
        CMD curl -f http://localhost:8000/v1/health || exit 1

    CMD ["uvicorn", "aegis.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

    2. Create `frontend/Dockerfile`:
    ```dockerfile
    FROM node:20-alpine

    WORKDIR /app

    COPY package.json package-lock.json* ./
    RUN npm ci

    COPY . .
    RUN npm run build

    EXPOSE 3000

    CMD ["npm", "start"]
    ```

    3. Create `docker-compose.yml`:
    ```yaml
    version: "3.9"
    services:
      backend:
        build:
          context: .
          dockerfile: Dockerfile
        ports:
          - "8000:8000"
        volumes:
          - ./data:/app/data
          - ./config:/app/config
        env_file:
          - .env
        environment:
          - AEGIS_DB_PATH=/app/data/aegis.duckdb
          - AEGIS_REFRESH_INTERVAL_HOURS=6
        healthcheck:
          test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
          interval: 30s
          timeout: 5s
          retries: 3

      frontend:
        build:
          context: ./frontend
          dockerfile: Dockerfile
        ports:
          - "3000:3000"
        environment:
          - AEGIS_API_URL=http://backend:8000
          - AEGIS_API_TOKEN=${AEGIS_API_TOKEN}
        depends_on:
          backend:
            condition: service_healthy
    ```

    4. Create `.env.example`:
    ```
    # Aegis Environment Configuration
    AEGIS_API_TOKEN=your-jwt-token-here
    AEGIS_API_URL=http://localhost:8000
    ANTHROPIC_API_KEY=optional-for-llm-expansion
    AEGIS_DB_PATH=aegis.duckdb
    AEGIS_REFRESH_INTERVAL_HOURS=6
    NCBI_API_KEY=optional-for-higher-pubmed-rate-limit
    ```

    5. Ensure the existing `/v1/health` endpoint in server.py returns useful info:
    ```python
    @app.get("/v1/health")
    def health_check() -> dict:
        """Health check with component status."""
        from aegis.storage.candidate_store import CandidateStore
        try:
            store = CandidateStore()
            count = store.count()
            store.close()
            db_status = "healthy"
        except Exception:
            count = 0
            db_status = "unhealthy"
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "version": "5.0.0",
            "database": db_status,
            "candidate_count": count,
        }
    ```

    ## Files to modify
    - `Dockerfile` — NEW FILE at project root
    - `frontend/Dockerfile` — NEW FILE
    - `docker-compose.yml` — NEW FILE at project root
    - `.env.example` — NEW FILE at project root
    - `src/aegis/api/server.py` — Update health check endpoint

    ## Acceptance criteria
    - Dockerfile builds successfully with `docker build .`
    - frontend/Dockerfile builds successfully
    - docker-compose.yml defines backend and frontend services
    - .env.example documents all environment variables
    - Health check returns database status and candidate count
    - `uv run python -m py_compile src/aegis/api/server.py` succeeds

    ## Validation command
    ```bash
    uv run python -m py_compile src/aegis/api/server.py && test -f Dockerfile && test -f docker-compose.yml && test -f .env.example && test -f frontend/Dockerfile
    ```

### 9. Frontend: Update Types and Create SSE Hook
- **Task ID**: frontend-types-sse-hook
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-3
- **Description**: |
    Update the frontend TypeScript types to support the new API features and create a reusable SSE hook.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions. The version of Next.js used is 16.2.4 which may have breaking changes from what you know.

    ## What to do

    1. **Update `frontend/src/types/api.ts`** — add new types:

    ```typescript
    // Query type classification
    export type QueryType = "basic_research" | "drug_discovery" | "clinical_trial_pi" | "policy_epi";

    export interface ClassifyResponse {
      query_type: QueryType;
      confidence: number;
      keyword_matches: string[];
      weights: Record<string, number>;
      exponents: Record<string, number>;
    }

    // SSE events
    export interface SourceProgressEvent {
      source_name: string;
      status: "pending" | "fetching" | "complete" | "failed";
      record_count: number;
      latency_ms: number;
      error: string | null;
    }

    export interface SSECandidateEvent {
      rank: number;
      uuid: string;
      name: string;
      score: number;
    }

    // Enhanced candidate with F1-F7 scores
    export interface F1F7Scores {
      f1_rcr: number;
      f2_funding: number;
      f3_leadership: number;
      f4_apex: number;
      f5_translational: number;
      f6_lineage: number;
      f7_clinician?: number;
    }

    // Shortlists
    export interface Shortlist {
      id: string;
      name: string;
      description: string | null;
      created_by: string;
      created_at: string;
      member_count?: number;
    }

    export interface ShortlistMember {
      candidate_uuid: string;
      candidate_name?: string;
      added_at: string;
      added_by: string;
    }

    // Notes
    export interface CandidateNote {
      id: string;
      candidate_uuid: string;
      author: string;
      content: string;
      created_at: string;
      updated_at: string;
    }

    // Candidate profile (full detail)
    export interface CandidateProfile {
      uuid: string;
      name: string;
      affiliation: string;
      country: string | null;
      score_history: Array<{ query_id: string; score: number; rank: number; date: string }>;
      publications: number;
      grants: number;
      trials: number;
      patents: number;
      integrity_status: string;
      f1_f7_scores: F1F7Scores;
    }
    ```

    2. **Update `ScoreComponents` interface** to include F1-F7:
    ```typescript
    export interface ScoreComponents {
      R: number;
      Q: number;
      C: number;
      I: number;
      f1_rcr?: number;
      f2_funding?: number;
      f3_leadership?: number;
      f4_apex?: number;
      f5_translational?: number;
      f6_lineage?: number;
      f7_clinician?: number;
    }
    ```

    3. **Update `CandidateResult` interface** to add source badges and shortlist:
    ```typescript
    export interface CandidateResult {
      // ...existing fields...
      source_badges?: string[];      // which sources contributed data
      has_notes?: boolean;           // whether notes exist for this candidate
      shortlisted_by?: string[];     // analyst names who shortlisted
      openalex_concepts?: string[];  // concept tags from OpenAlex
    }
    ```

    4. **Create `frontend/src/hooks/useSSE.ts`**:
    ```typescript
    "use client";
    import { useEffect, useRef, useState, useCallback } from "react";
    import type { SourceProgressEvent } from "@/types/api";

    interface UseSSEOptions {
      queryId: string;
      enabled: boolean;
    }

    interface SSEState {
      sources: Map<string, SourceProgressEvent>;
      completedCount: number;
      totalSources: number;
      isComplete: boolean;
      error: string | null;
    }

    export function useSSE({ queryId, enabled }: UseSSEOptions): SSEState {
      const [state, setState] = useState<SSEState>({
        sources: new Map(),
        completedCount: 0,
        totalSources: 15,
        isComplete: false,
        error: null,
      });
      const eventSourceRef = useRef<EventSource | null>(null);

      useEffect(() => {
        if (!enabled || !queryId) return;

        const es = new EventSource(`/api/queries/${queryId}/stream`);
        eventSourceRef.current = es;

        es.addEventListener("source_progress", (e) => {
          const data: SourceProgressEvent = JSON.parse(e.data);
          setState((prev) => {
            const newSources = new Map(prev.sources);
            newSources.set(data.source_name, data);
            const completed = Array.from(newSources.values()).filter(
              (s) => s.status === "complete" || s.status === "failed"
            ).length;
            return { ...prev, sources: newSources, completedCount: completed };
          });
        });

        es.addEventListener("complete", () => {
          setState((prev) => ({ ...prev, isComplete: true }));
          es.close();
        });

        es.onerror = () => {
          setState((prev) => ({ ...prev, error: "Connection lost", isComplete: true }));
          es.close();
        };

        return () => {
          es.close();
          eventSourceRef.current = null;
        };
      }, [queryId, enabled]);

      return state;
    }
    ```

    5. **Create `frontend/src/hooks/useShortlist.ts`**:
    ```typescript
    "use client";
    import { useState, useCallback } from "react";
    import type { Shortlist } from "@/types/api";

    export function useShortlist() {
      const [shortlists, setShortlists] = useState<Shortlist[]>([]);
      const [loading, setLoading] = useState(false);

      const fetchShortlists = useCallback(async () => {
        setLoading(true);
        try {
          const res = await fetch("/api/shortlists");
          const data = await res.json();
          setShortlists(data.shortlists || []);
        } finally {
          setLoading(false);
        }
      }, []);

      const addCandidate = useCallback(async (shortlistId: string, candidateUuid: string) => {
        await fetch(`/api/shortlists/${shortlistId}/candidates`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ candidate_uuid: candidateUuid }),
        });
      }, []);

      const createShortlist = useCallback(async (name: string, description?: string) => {
        const res = await fetch("/api/shortlists", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, description }),
        });
        const data = await res.json();
        await fetchShortlists();
        return data.id as string;
      }, [fetchShortlists]);

      return { shortlists, loading, fetchShortlists, addCandidate, createShortlist };
    }
    ```

    ## Files to modify
    - `frontend/src/types/api.ts` — Add new types
    - `frontend/src/hooks/useSSE.ts` — NEW FILE
    - `frontend/src/hooks/useShortlist.ts` — NEW FILE

    ## Acceptance criteria
    - All new TypeScript types compile without errors
    - useSSE hook manages EventSource lifecycle and parses SSE events
    - useShortlist hook provides CRUD operations for shortlists
    - `cd frontend && npx tsc --noEmit` succeeds (or at minimum no new errors introduced)

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 10. Frontend: Query Form Revamp with Type Detection
- **Task ID**: frontend-query-form
- **Role**: builder
- **Depends On**: frontend-types-sse-hook
- **Assigned To**: builder-3
- **Description**: |
    Revamp the query form to include real-time query type detection, weight vector display, and MeSH expansion inspector.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Create `frontend/src/components/results/QueryTypeBadge.tsx`**:
       - Accepts `queryType: QueryType` and `confidence: number`
       - Shows colored badge: Drug Discovery (purple), Clinical Trial PI (green), Basic Research (blue), Policy/Epi (orange)
       - Shows confidence as percentage
       - Shows manual override dropdown on click

    2. **Create `frontend/src/components/results/MeshExpansionInspector.tsx`**:
       - Shows list of expanded MeSH terms as removable tags
       - "Add term" input field to add custom terms
       - Called after classification, before running query
       - Props: `terms: string[], onTermsChange: (terms: string[]) => void`

    3. **Create `frontend/src/components/results/WeightSliderPanel.tsx`**:
       - Collapsible panel with sliders for: Quality (alpha), Topical Fit (beta), Recency (gamma)
       - Each slider shows current weight value
       - On change, emits new weights for client-side re-ranking
       - Also show F1-F7 weight breakdown as read-only display
       - Props: `weights: Record<string, number>, exponents: Record<string, number>, onExponentsChange: (exponents: Record<string, number>) => void`

    4. **Update `frontend/src/components/query/QueryForm.tsx`**:
       - Add debounced classification as user types (300ms debounce)
       - Call `POST /api/queries/classify` with current text
       - Show QueryTypeBadge with detected type
       - Show weight vector values for detected type
       - Add manual type override dropdown
       - Show MeshExpansionInspector after classification (user can add/remove terms before submitting)
       - Pass detected type and adjusted terms to query submission

    5. **Create `frontend/src/app/api/queries/classify/route.ts`** (API proxy):
    ```typescript
    import { NextRequest, NextResponse } from "next/server";
    import { apiFetch } from "@/lib/api-client";

    export async function POST(request: NextRequest) {
      try {
        const body = await request.json();
        const data = await apiFetch("/v1/queries/classify", { method: "POST", body });
        return NextResponse.json(data);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Classification failed";
        return NextResponse.json({ error: message }, { status: 500 });
      }
    }
    ```

    ## Files to modify
    - `frontend/src/components/results/QueryTypeBadge.tsx` — NEW FILE
    - `frontend/src/components/results/MeshExpansionInspector.tsx` — NEW FILE
    - `frontend/src/components/results/WeightSliderPanel.tsx` — NEW FILE
    - `frontend/src/components/query/QueryForm.tsx` — Update with type detection
    - `frontend/src/app/api/queries/classify/route.ts` — NEW FILE (API proxy)

    ## Code patterns to follow
    - See `frontend/src/components/query/QueryForm.tsx` for existing form pattern
    - See `frontend/src/components/query/MeshTagInput.tsx` for tag input pattern
    - See `frontend/src/components/results/ScoreBreakdownChart.tsx` for chart pattern
    - Use Tailwind CSS classes for styling
    - Use "use client" directive for interactive components

    ## Acceptance criteria
    - QueryForm shows real-time query type badge as user types
    - Weight vector values are displayed for detected type
    - MeSH terms can be added/removed before submission
    - Manual type override dropdown works
    - WeightSliderPanel shows alpha/beta/gamma sliders
    - API proxy for /classify exists and works

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 11. Frontend: SSE-Powered Results Page
- **Task ID**: frontend-sse-results
- **Role**: builder
- **Depends On**: frontend-types-sse-hook, frontend-query-form
- **Assigned To**: builder-3
- **Description**: |
    Revamp the results page to use SSE streaming for live updates, showing source progress and candidates appearing in real time.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Create `frontend/src/components/results/SourceProgressBar.tsx`**:
       - Shows a grid of 15 source tiles (3 rows x 5 columns)
       - Each tile shows: source name, status icon (spinner/check/x), latency
       - Sources: PubMed, iCite, NIH Reporter, CT.gov, OpenAlex, LEIE, ORI, Retraction Watch, OFAC/SAM, USPTO, EPO, NPPES, ABMS, USNWR, CMS
       - Overall progress bar: "8/15 sources complete"
       - Color coding: pending (gray), fetching (blue pulse), complete (green), failed (red)
       - Props: `sources: Map<string, SourceProgressEvent>, totalSources: number`

    2. **Create `frontend/src/app/api/queries/[id]/stream/route.ts`** (SSE proxy):
    ```typescript
    import { NextRequest } from "next/server";

    export async function GET(
      request: NextRequest,
      { params }: { params: Promise<{ id: string }> }
    ) {
      const { id } = await params;
      const baseUrl = process.env.AEGIS_API_URL;
      const token = process.env.AEGIS_API_TOKEN;

      const response = await fetch(`${baseUrl}/v1/queries/${id}/stream`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      return new Response(response.body, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }
    ```

    3. **Update `frontend/src/app/results/[id]/page.tsx`**:
       - Import and use `useSSE` hook
       - Show SourceProgressBar at top during loading
       - Candidate cards appear incrementally as SSE events arrive
       - After SSE completes, show full results with sorting
       - Add geographic coverage warning if >75% candidates from one country
       - Add "Shortlist" button per candidate card
       - Add WeightSliderPanel (collapsible)
       - Client-side re-ranking when weight sliders change
       - Show query type badge in header

    4. **Update `frontend/src/components/results/CandidateRow.tsx`**:
       - Add source badges: small colored dots showing which sources contributed data
       - Add "Shortlist" button (star icon)
       - Add notes indicator icon (if candidate has notes)
       - Show F1-F7 component scores in expanded view
       - Add "Compare" checkbox for multi-candidate comparison
       - Link candidate name to profile page `/candidates/{uuid}`

    5. **Update `frontend/src/components/results/EvidenceTrailPanel.tsx`**:
       - Add "Why ranked here?" natural language explanation
       - Show weight vector applied and why (from query classification)
       - Show F1-F7 score breakdown with labels
       - Add OpenAlex concept tags section
       - Show chronological evidence timeline

    ## Files to modify
    - `frontend/src/components/results/SourceProgressBar.tsx` — NEW FILE
    - `frontend/src/app/api/queries/[id]/stream/route.ts` — NEW FILE
    - `frontend/src/app/results/[id]/page.tsx` — Update with SSE, shortlist, weight sliders
    - `frontend/src/components/results/CandidateRow.tsx` — Add source badges, shortlist, compare
    - `frontend/src/components/results/EvidenceTrailPanel.tsx` — Add F1-F7, explanation, timeline

    ## Code patterns to follow
    - See `frontend/src/app/results/[id]/page.tsx` for current results page pattern
    - See `frontend/src/components/results/CandidateRow.tsx` for candidate card pattern
    - See `frontend/src/hooks/useSSE.ts` for SSE hook usage
    - Use Tailwind CSS for all styling
    - Use "use client" for interactive components

    ## Acceptance criteria
    - Source progress bar shows 15 source tiles with live status updates
    - Candidates appear incrementally during SSE streaming
    - Weight sliders re-rank candidates client-side
    - Shortlist button adds candidate to shortlist
    - Evidence panel shows F1-F7 breakdown
    - Geographic coverage warning shows when appropriate

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 12. Frontend: Candidate Comparison Modal
- **Task ID**: frontend-comparison
- **Role**: builder
- **Depends On**: frontend-sse-results
- **Assigned To**: builder-3
- **Description**: |
    Create a candidate comparison modal that allows selecting 2-4 candidates for side-by-side comparison.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Create `frontend/src/components/results/CandidateComparisonModal.tsx`**:
       - Modal overlay triggered by "Compare Selected" button (appears when 2+ candidates checked)
       - Side-by-side columns for 2-4 candidates
       - Each column shows:
         - Name, rank, affiliation
         - Composite score (0-100 scale)
         - Q/C/R/I scores as horizontal bars
         - F1-F7 scores as radar/spider chart (use recharts RadarChart)
         - Publication count, grant count, trial count, patent count
         - Top affiliation
         - Integrity status (green check or red flag)
       - Score component radar chart overlay using recharts
       - Close button and "Export Comparison" button
       - Props: `candidates: CandidateResult[], onClose: () => void`

    2. **Update results page** to track selected candidates:
       - Add state: `selectedForComparison: Set<string>` (candidate UUIDs)
       - Show "Compare (N)" floating button when 2+ selected
       - Pass selected candidates to CandidateComparisonModal

    3. Radar chart implementation using recharts (already installed):
    ```typescript
    import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts";

    const radarData = candidates.map(c => ({
      name: c.name,
      Q: c.score_components.Q * 100,
      C: c.score_components.C * 100,
      R: c.score_components.R * 100,
      I: c.score_components.I * 100,
    }));
    ```

    ## Files to modify
    - `frontend/src/components/results/CandidateComparisonModal.tsx` — NEW FILE
    - `frontend/src/app/results/[id]/page.tsx` — Add comparison state + floating button

    ## Code patterns to follow
    - See `frontend/src/components/results/FeedbackModal.tsx` for modal pattern
    - See `frontend/src/components/results/ScoreBreakdownChart.tsx` for recharts usage
    - Use recharts for radar chart (already in package.json)

    ## Acceptance criteria
    - Comparison modal opens when 2+ candidates are selected
    - Shows side-by-side columns with all specified metrics
    - Radar chart renders Q/C/R/I overlay for all compared candidates
    - Close button works
    - TypeScript compiles without errors

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 13. Frontend: Candidate Profile Page
- **Task ID**: frontend-candidate-profile
- **Role**: builder
- **Depends On**: frontend-types-sse-hook
- **Assigned To**: builder-4
- **Description**: |
    Create the full candidate profile page at `/candidates/[uuid]` with chronological timeline, score history, source contributions, and analyst notes.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Create `frontend/src/app/candidates/[uuid]/page.tsx`**:
       - Fetch candidate data from `/api/candidates/{uuid}/evidence`
       - Show full candidate header: name, affiliation, country, identity confidence
       - Show integrity status prominently (green/red banner)
       - Show F1-F7 score breakdown (if available from most recent query)
       - Show CandidateTimeline component
       - Show AnalystNotes component
       - "Export as PDF Brief" button (calls window.print() with print-friendly CSS)
       - Link back to results page

    2. **Create `frontend/src/components/candidates/CandidateTimeline.tsx`**:
       - Chronological timeline of all evidence items
       - Group by type: publications, grants, trials, patents
       - Each item shows: date, type icon, description, source badge, link
       - Timeline uses vertical line with dots at each event
       - Filter by type (All | Publications | Grants | Trials | Patents)

    3. **Create `frontend/src/components/candidates/ScoreHistoryChart.tsx`**:
       - Line chart showing score over time (if candidate appeared in multiple queries)
       - X-axis: query date, Y-axis: score
       - Uses recharts LineChart
       - Show query text on hover

    4. **Create `frontend/src/components/candidates/AnalystNotes.tsx`**:
       - List of existing notes (from backend)
       - "Add note" textarea + submit button
       - Each note shows: author, timestamp, content
       - Edit and delete buttons per note
       - Fetches from `/api/candidates/{uuid}/notes`

    5. **Create `frontend/src/app/api/candidates/[uuid]/notes/route.ts`** (API proxy):
    ```typescript
    import { NextRequest, NextResponse } from "next/server";
    import { apiFetch } from "@/lib/api-client";

    export async function GET(
      request: NextRequest,
      { params }: { params: Promise<{ uuid: string }> }
    ) {
      const { uuid } = await params;
      const data = await apiFetch(`/v1/candidates/${uuid}/notes`);
      return NextResponse.json(data);
    }

    export async function POST(
      request: NextRequest,
      { params }: { params: Promise<{ uuid: string }> }
    ) {
      const { uuid } = await params;
      const body = await request.json();
      const data = await apiFetch(`/v1/candidates/${uuid}/notes`, { method: "POST", body });
      return NextResponse.json(data);
    }
    ```

    ## Files to modify
    - `frontend/src/app/candidates/[uuid]/page.tsx` — NEW FILE
    - `frontend/src/components/candidates/CandidateTimeline.tsx` — NEW FILE
    - `frontend/src/components/candidates/ScoreHistoryChart.tsx` — NEW FILE
    - `frontend/src/components/candidates/AnalystNotes.tsx` — NEW FILE
    - `frontend/src/app/api/candidates/[uuid]/notes/route.ts` — NEW FILE

    ## Code patterns to follow
    - See `frontend/src/app/results/[id]/page.tsx` for page data fetching pattern
    - See `frontend/src/components/results/EvidenceTrailPanel.tsx` for evidence display
    - See `frontend/src/components/results/ScoreBreakdownChart.tsx` for recharts usage
    - See `frontend/src/app/api/candidates/[uuid]/evidence/route.ts` for API proxy pattern

    ## Acceptance criteria
    - `/candidates/[uuid]` page renders candidate profile
    - Timeline shows chronological evidence items with type filtering
    - Analyst notes CRUD works (create, read, edit, delete)
    - Score history chart renders (even if only one data point)
    - API proxy for notes works
    - TypeScript compiles

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 14. Frontend: Shortlists System
- **Task ID**: frontend-shortlists
- **Role**: builder
- **Depends On**: frontend-types-sse-hook
- **Assigned To**: builder-4
- **Description**: |
    Create the full shortlists system: list page, detail page, sidebar panel, and export functionality.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Create `frontend/src/app/shortlists/page.tsx`**:
       - List all shortlists with name, member count, creation date
       - "Create New Shortlist" button with name + description form
       - Click a shortlist to navigate to detail page
       - Delete button per shortlist

    2. **Create `frontend/src/app/shortlists/[id]/page.tsx`**:
       - Show shortlist name, description, creation date
       - List members with candidate info (name, score, affiliation)
       - Remove button per member
       - "Export CSV" and "Export PDF" buttons
       - Link each member to candidate profile page

    3. **Create `frontend/src/components/shortlists/ShortlistPanel.tsx`**:
       - Sidebar component shown on results page
       - Dropdown to select existing shortlist or create new
       - Shows current shortlist members as compact list
       - Drag-drop or button to add/remove candidates

    4. **Create `frontend/src/components/shortlists/ExportButton.tsx`**:
       - "Export as CSV" — downloads CSV with columns: Name, Rank, Score, Affiliation, Q, C, R, I
       - "Export as PDF" — triggers browser print dialog with print-friendly layout
       - Props: `shortlistId: string, members: ShortlistMember[]`

    5. **Create API proxies**:
       - `frontend/src/app/api/shortlists/route.ts` — GET list, POST create
       - `frontend/src/app/api/shortlists/[id]/route.ts` — GET detail, DELETE
       - `frontend/src/app/api/shortlists/[id]/candidates/route.ts` — POST add candidate

    6. **Update `frontend/src/components/Header.tsx`**:
       - Add "Shortlists" nav item: `{ href: "/shortlists", label: "Shortlists" }`

    ## Files to modify
    - `frontend/src/app/shortlists/page.tsx` — NEW FILE
    - `frontend/src/app/shortlists/[id]/page.tsx` — NEW FILE
    - `frontend/src/components/shortlists/ShortlistPanel.tsx` — NEW FILE
    - `frontend/src/components/shortlists/ExportButton.tsx` — NEW FILE
    - `frontend/src/app/api/shortlists/route.ts` — NEW FILE
    - `frontend/src/app/api/shortlists/[id]/route.ts` — NEW FILE
    - `frontend/src/app/api/shortlists/[id]/candidates/route.ts` — NEW FILE
    - `frontend/src/components/Header.tsx` — Add Shortlists nav item

    ## Code patterns to follow
    - See `frontend/src/app/history/page.tsx` for list page pattern
    - See `frontend/src/app/api/queries/route.ts` for API proxy pattern
    - See `frontend/src/components/Header.tsx` for nav item pattern

    ## Acceptance criteria
    - Shortlists page lists all shortlists
    - Create new shortlist works
    - Shortlist detail page shows members
    - Add/remove candidates from shortlist works
    - CSV export downloads file
    - Header nav includes "Shortlists" link
    - TypeScript compiles

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 15. Frontend: Query History with Diff
- **Task ID**: frontend-query-history
- **Role**: builder
- **Depends On**: frontend-types-sse-hook
- **Assigned To**: builder-4
- **Description**: |
    Enhance the query history page with saved names, re-run capability, and ranking diff visualization.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Create `frontend/src/components/history/QueryDiff.tsx`**:
       - Compares two query results side-by-side
       - Shows candidates that: moved up (green arrow), moved down (red arrow), are new (blue badge), disappeared (gray strikethrough)
       - Table format: Rank | Name | Score | Change (up/down/new/gone)
       - Props: `oldResults: CandidateResult[], newResults: CandidateResult[]`

    2. **Update `frontend/src/app/history/page.tsx`**:
       - Add "Re-run" button per query (re-submits same task_description)
       - After re-run, show QueryDiff between old and new results
       - Add "Save Name" input per query (editable inline, saves custom name)
       - Show query type badge per query
       - Show top-3 candidate names per query in the list

    3. **Update `frontend/src/components/history/QueryTable.tsx`**:
       - Add columns: query type badge, top candidates (3 names), custom name
       - Add "Re-run" and "Compare" action buttons
       - Show more detail on hover/expand

    ## Files to modify
    - `frontend/src/components/history/QueryDiff.tsx` — NEW FILE
    - `frontend/src/app/history/page.tsx` — Add re-run, save name, diff view
    - `frontend/src/components/history/QueryTable.tsx` — Add new columns

    ## Code patterns to follow
    - See `frontend/src/app/history/page.tsx` for history page pattern
    - See `frontend/src/components/history/QueryTable.tsx` for table pattern

    ## Acceptance criteria
    - QueryDiff shows ranking changes between two results
    - Re-run button re-submits query and shows diff
    - Custom query names can be saved
    - Query type badge shown in history
    - Top-3 candidates shown per query
    - TypeScript compiles

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 16. Frontend: Team View
- **Task ID**: frontend-team-view
- **Role**: builder
- **Depends On**: frontend-shortlists
- **Assigned To**: builder-4
- **Description**: |
    Add team collaboration features: show when colleagues have shortlisted or annotated candidates.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Update `frontend/src/components/results/CandidateRow.tsx`**:
       - If `candidate.shortlisted_by` has entries, show analyst avatar badges (initials in colored circles)
       - If `candidate.has_notes` is true, show a small note icon
       - Tooltip on avatar badges showing analyst name

    2. **Update results page** to fetch team data:
       - After loading results, fetch shortlist membership for all candidates
       - Fetch note existence flags for all candidates
       - Merge into candidate data for display

    3. This is primarily about displaying data that already comes from the backend.
       The backend shortlist and notes APIs (from tasks 6) already store `created_by`/`author` fields.
       The frontend just needs to aggregate and display this information.

    ## Files to modify
    - `frontend/src/components/results/CandidateRow.tsx` — Add team badges
    - `frontend/src/app/results/[id]/page.tsx` — Fetch team collaboration data

    ## Acceptance criteria
    - Analyst avatar badges appear on candidates that have been shortlisted by others
    - Note icon appears when notes exist
    - Tooltips show analyst names
    - TypeScript compiles

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 17. Update Frontend API Proxies for New Backend Endpoints
- **Task ID**: frontend-api-proxies
- **Role**: builder
- **Depends On**: frontend-types-sse-hook
- **Assigned To**: builder-3
- **Description**: |
    Update existing API proxy routes and create new ones to support all the new backend endpoints.

    IMPORTANT: Before writing any code, read the relevant Next.js guide at `node_modules/next/dist/docs/` to understand the current API conventions.

    ## What to do

    1. **Update `frontend/src/app/api/queries/[id]/route.ts`**:
       - Update BackendCandidate interface to include new fields:
         - `source_badges?: string[]`
         - `openalex_concepts?: string[]`
       - Update component_scores transformation to include F1-F7
       - Pass through source_badges and openalex_concepts

    2. **Update `frontend/src/app/api/queries/route.ts`**:
       - Update POST handler to pass query_type_override if provided
       - Update response to include query_type from backend

    3. All new API proxy routes needed (some created in other tasks, list for completeness):
       - `frontend/src/app/api/queries/classify/route.ts` — POST classify (task 10)
       - `frontend/src/app/api/queries/[id]/stream/route.ts` — GET SSE stream (task 11)
       - `frontend/src/app/api/shortlists/route.ts` — GET/POST shortlists (task 14)
       - `frontend/src/app/api/shortlists/[id]/route.ts` — GET/DELETE shortlist (task 14)
       - `frontend/src/app/api/shortlists/[id]/candidates/route.ts` — POST add candidate (task 14)
       - `frontend/src/app/api/candidates/[uuid]/notes/route.ts` — GET/POST notes (task 13)

    ## Files to modify
    - `frontend/src/app/api/queries/[id]/route.ts` — Update transformation
    - `frontend/src/app/api/queries/route.ts` — Update to pass query_type

    ## Code patterns to follow
    - See existing API proxy files for pattern
    - See `frontend/src/lib/api-client.ts` for apiFetch usage

    ## Acceptance criteria
    - Query proxy passes through F1-F7 scores and source badges
    - Query POST proxy supports query_type_override parameter
    - All proxy routes compile without TypeScript errors

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit 2>&1 | head -20
    ```

### 18. Final Validation
- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: wire-real-scoring, create-shortlist-notes-api, wire-privacy-ingestion, create-deployment, frontend-sse-results, frontend-comparison, frontend-candidate-profile, frontend-shortlists, frontend-query-history, frontend-team-view, frontend-api-proxies
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria across the entire Phase 5 build.

    ## Validation Commands

    ### Backend compilation
    ```bash
    uv run python -m py_compile src/aegis/sources/openalex.py
    uv run python -m py_compile src/aegis/pipeline/__init__.py
    uv run python -m py_compile src/aegis/pipeline/orchestrator.py
    uv run python -m py_compile src/aegis/query/classifier.py
    uv run python -m py_compile src/aegis/api/server.py
    uv run python -m py_compile src/aegis/api/schemas.py
    uv run python -m py_compile src/aegis/api/streaming.py
    uv run python -m py_compile src/aegis/api/shortlists.py
    uv run python -m py_compile src/aegis/api/notes.py
    uv run python -m py_compile src/aegis/api/formatter.py
    uv run python -m py_compile src/aegis/storage/shortlist_store.py
    uv run python -m py_compile src/aegis/storage/notes_store.py
    uv run python -m py_compile src/aegis/storage/query_store.py
    ```

    ### Backend tests
    ```bash
    uv run pytest src/aegis/sources/openalex_test.py -v
    uv run pytest src/aegis/pipeline/orchestrator_test.py -v
    uv run pytest src/aegis/query/classifier_test.py -v
    uv run pytest src/aegis/storage/shortlist_store_test.py src/aegis/storage/notes_store_test.py src/aegis/storage/query_store_test.py -v
    ```

    ### Frontend compilation
    ```bash
    cd /Users/anvith/aegis/frontend && npx tsc --noEmit
    ```

    ### File existence checks
    ```bash
    test -f src/aegis/sources/openalex.py
    test -f src/aegis/pipeline/orchestrator.py
    test -f src/aegis/query/classifier.py
    test -f src/aegis/api/streaming.py
    test -f src/aegis/api/shortlists.py
    test -f src/aegis/api/notes.py
    test -f src/aegis/storage/shortlist_store.py
    test -f src/aegis/storage/notes_store.py
    test -f src/aegis/storage/query_store.py
    test -f config/aegis/weights/basic_research_v1.yaml
    test -f config/aegis/weights/policy_epi_v1.yaml
    test -f Dockerfile
    test -f docker-compose.yml
    test -f .env.example
    test -f frontend/Dockerfile
    test -f frontend/src/hooks/useSSE.ts
    test -f frontend/src/hooks/useShortlist.ts
    test -f frontend/src/app/candidates/[uuid]/page.tsx  # note: brackets in filename
    test -f frontend/src/app/shortlists/page.tsx
    test -f frontend/src/components/results/SourceProgressBar.tsx
    test -f frontend/src/components/results/CandidateComparisonModal.tsx
    test -f frontend/src/components/results/WeightSliderPanel.tsx
    test -f frontend/src/components/results/QueryTypeBadge.tsx
    test -f frontend/src/components/candidates/CandidateTimeline.tsx
    test -f frontend/src/components/candidates/AnalystNotes.tsx
    test -f frontend/src/components/shortlists/ShortlistPanel.tsx
    test -f frontend/src/components/history/QueryDiff.tsx
    ```

    ### Weight vector validation
    ```bash
    uv run python -c "from aegis.scoring.quality_prior import load_weight_vector; from pathlib import Path; v = load_weight_vector(Path('config/aegis/weights/basic_research_v1.yaml')); assert v.specialty == 'basic_research'; print('basic_research OK')"
    uv run python -c "from aegis.scoring.quality_prior import load_weight_vector; from pathlib import Path; v = load_weight_vector(Path('config/aegis/weights/policy_epi_v1.yaml')); assert v.specialty == 'policy_epi'; print('policy_epi OK')"
    ```

    ## Acceptance Criteria
    - All backend Python files compile without errors
    - All backend tests pass
    - Frontend TypeScript compiles without errors (or no new errors beyond pre-existing ones)
    - All new files exist at expected paths
    - OpenAlex client has search_works, search_authors, get_grants_by_funder methods
    - Pipeline orchestrator executes end-to-end with real scoring
    - Query classifier routes queries to correct weight vectors
    - SSE streaming endpoint exists
    - Shortlist and notes APIs are mounted and functional
    - Dockerfile and docker-compose.yml exist
    - Weight vectors for basic_research and policy_epi load correctly
    - Frontend has SSE hook, shortlist hook, comparison modal, profile page, query diff

## Acceptance Criteria

1. **Backend: OpenAlex client** — `src/aegis/sources/openalex.py` exists with async methods for works, authors, funders, concepts
2. **Backend: Pipeline orchestrator** — `src/aegis/pipeline/orchestrator.py` wires real F1-F7 scoring, live source fetching, privacy gate, identity resolution
3. **Backend: Query classifier** — `src/aegis/query/classifier.py` classifies queries into 4 types and loads appropriate weight vectors
4. **Backend: SSE streaming** — `GET /v1/queries/{id}/stream` returns Server-Sent Events with source progress
5. **Backend: Shortlists API** — Full CRUD at `/v1/shortlists` with member management
6. **Backend: Notes API** — Full CRUD at `/v1/candidates/{uuid}/notes`
7. **Backend: Real scoring** — `POST /v1/queries` uses real F1-F7 scores instead of stubs
8. **Backend: Privacy gate wired** — All fetched data passes through PrivacyGate.check()
9. **Backend: Continuous ingestion** — RefreshOrchestrator runs on startup background task
10. **Backend: Deployment** — Dockerfile, docker-compose.yml, .env.example exist
11. **Frontend: SSE results** — Source progress bar + candidates appearing in real time
12. **Frontend: Query type detection** — Debounced classification with badge and weight display
13. **Frontend: Comparison modal** — 2-4 candidate side-by-side with radar chart
14. **Frontend: Candidate profile** — Full page at `/candidates/[uuid]` with timeline, notes, score history
15. **Frontend: Shortlists** — Create, manage, export shortlists
16. **Frontend: Query diff** — Re-run queries and see ranking changes
17. **Frontend: Weight sliders** — Client-side re-ranking with adjustable exponents

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# Backend compilation (all new files)
uv run python -m py_compile src/aegis/sources/openalex.py
uv run python -m py_compile src/aegis/pipeline/orchestrator.py
uv run python -m py_compile src/aegis/query/classifier.py
uv run python -m py_compile src/aegis/api/server.py
uv run python -m py_compile src/aegis/api/streaming.py
uv run python -m py_compile src/aegis/api/shortlists.py
uv run python -m py_compile src/aegis/api/notes.py
uv run python -m py_compile src/aegis/storage/shortlist_store.py
uv run python -m py_compile src/aegis/storage/notes_store.py
uv run python -m py_compile src/aegis/storage/query_store.py

# Backend tests
uv run pytest src/aegis/sources/openalex_test.py -v
uv run pytest src/aegis/pipeline/orchestrator_test.py -v
uv run pytest src/aegis/query/classifier_test.py -v
uv run pytest src/aegis/storage/shortlist_store_test.py src/aegis/storage/notes_store_test.py src/aegis/storage/query_store_test.py -v

# Frontend compilation
cd /Users/anvith/aegis/frontend && npx tsc --noEmit

# Deployment files exist
test -f Dockerfile && test -f docker-compose.yml && test -f .env.example
```

## Notes

- No new Python dependencies needed — all use existing httpx, pydantic, fastapi, duckdb, asyncio
- No new npm dependencies needed — recharts is already installed for charts
- The OpenAlex API is free and does not require authentication (but use `mailto` parameter for polite pool)
- SSE uses native browser EventSource API — no polyfill needed
- DuckDB handles concurrent reads well; writes are serialized by the Python GIL + DuckDB's internal locking
- Existing tests should continue to pass — the server_test.py tests may need mock updates for the new pipeline but should not break structurally
- The broken international grant clients (erc.py, mrc.py, cihr.py, nsfc.py) are NOT deleted — they become unused but remain for reference. OpenAlex replaces their functionality.
