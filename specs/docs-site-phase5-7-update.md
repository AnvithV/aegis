# Plan: Update Aegis Docs Site to Reflect Deployed State

> **Status:** COMPLETE (2026-04-29)
> All 14 tasks completed. npm run build passing. 7/7 acceptance criteria verified. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-29
> **Team:** docs-site-update-20260429-1308

### Test Results
- `npm run build` (website/) — PASSED (static files generated successfully)
- `grep -rn "In Progress" website/docs/` — PASSED (0 matches, exit code 1)
- `grep -rn "KAKEN|NSFC|Horizon Europe" website/docs/data-sources.mdx` — PASSED (0 matches, exit code 1)
- `grep -rn "OpenAlex" website/docs/` — PASSED (14 matches across 6 files)
- `grep "ERC" website/static/images/architecture.svg` — PASSED (0 matches, exit code 1)
- `test -f .../submitting-a-query.mdx && test -f .../monitoring-a-job.mdx && test -f .../reading-results.mdx` — PASSED ("All new files exist")
- `grep -c "using-aegis" website/sidebars.ts` — PASSED (returned 3)

### Acceptance Criteria Verification
- [x] All 8 existing docs pages updated — VERIFIED (roadmap.mdx, data-sources.mdx, overview.mdx, data-pipeline.mdx, scoring.mdx, what-is-aegis.mdx, diagrams.mdx, feedback-loop.mdx all modified with accurate Phase 5-7 content)
- [x] Three new "Using Aegis" pages created — VERIFIED (submitting-a-query.mdx, monitoring-a-job.mdx, reading-results.mdx all exist in website/docs/using-aegis/)
- [x] Sidebar updated with "Using Aegis" category — VERIFIED (3 using-aegis references in sidebars.ts, category positioned between what-is-aegis and How It Works)
- [x] Architecture SVG updated — VERIFIED ("ERC / MRC / CIHR" replaced with "OpenAlex Grants", "bioRxiv / medRxiv" replaced with "OpenAlex Works", no ERC references remain)
- [x] No broken international source references — VERIFIED (grep for KAKEN, NSFC, Horizon Europe in data-sources.mdx returns 0 matches)
- [x] No "In Progress" status — VERIFIED (grep across all docs returns 0 matches; roadmap.mdx has 8 "Complete" entries)
- [x] Site builds successfully — VERIFIED (npm run build completed with "[SUCCESS] Generated static files in build")

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| website/docs/roadmap.mdx | Modified | Yes |
| website/docs/data-sources.mdx | Modified | Yes |
| website/docs/architecture/overview.mdx | Modified | Yes |
| website/docs/how-it-works/data-pipeline.mdx | Modified | Yes |
| website/docs/how-it-works/scoring.mdx | Modified | Yes |
| website/docs/what-is-aegis.mdx | Modified | Yes |
| website/docs/architecture/diagrams.mdx | Modified | Yes |
| website/docs/how-it-works/feedback-loop.mdx | Modified | Yes |
| website/static/images/architecture.svg | Modified | Yes |
| website/sidebars.ts | Modified | Yes |
| website/docs/using-aegis/submitting-a-query.mdx | Created | Yes |
| website/docs/using-aegis/monitoring-a-job.mdx | Created | Yes |
| website/docs/using-aegis/reading-results.mdx | Created | Yes |

### Notes
- Initial build failed due to unescaped curly braces in MDX files (overview.mdx, data-pipeline.mdx, monitoring-a-job.mdx, submitting-a-query.mdx). Fixed by builder agents escaping `{id}` patterns. Build passes after fixes.

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/docs-site-phase5-7-update.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

The Aegis Docusaurus documentation site (`website/`) is out of date. It was written during Phase 4 and reflects a system with only Phases 0-3 complete and Phase 4 in progress. In reality, Phases 0 through 7 are all complete. The docs reference broken international grant sources (ERC, Horizon, MRC, CIHR, KAKEN, NSFC) that have been replaced by OpenAlex. The async jobs system, shortlists, query type classifier, SSE streaming, and numerous frontend pages are not documented at all. The architecture diagram SVG still references the old sources. Three entirely new "Using Aegis" pages need to be created to document the frontend user experience.

This plan updates every outdated page, creates three new pages, fixes the SVG diagram, and updates the sidebar navigation.

## Objective

When this plan is complete:
1. All existing docs pages accurately reflect the deployed system (Phases 0-7 complete, OpenAlex replacing international grant sources, async jobs pipeline, query type classifier, etc.)
2. Three new "Using Aegis" pages document the frontend workflows (submitting a query, monitoring a job, reading results)
3. The architecture SVG diagram is corrected
4. The sidebar includes the new "Using Aegis" section
5. The site builds without errors via `npm run build`

## Problem Statement

The documentation site has not been updated since Phase 4 (the phase that created it). Five additional phases of work have been completed since then, including:
- Phase 5: Production Reality (OpenAlex, real scoring, SSE streaming, query type classifier, shortlists, notes, deployment to Fly.io/Vercel)
- Phase 6: Full Wiring (live ingestion, feedback router, refit API, HITL API, WeightSliderPanel, dotenv)
- Phase 7: Jobs System (async pipeline via POST /v1/queries returning 202, JobStore, /jobs and /jobs/[id] frontend pages, cancel support)

Additionally, six international grant sources (ERC, Horizon Europe, MRC, CIHR, JST/KAKEN, NSFC) are listed as working data sources but their APIs no longer function. They have been replaced by OpenAlex Works and OpenAlex Grants.

## Solution Approach

Split the work across two builders working in parallel:
- **builder-1** handles all existing page rewrites/updates (8 files) plus the SVG fix
- **builder-2** handles all new page creation (3 files) plus the sidebar update

A validator then verifies the site builds and content is accurate.

## Relevant Files

### Existing Files to Modify

- `website/docs/roadmap.mdx` -- Full rewrite: Phase 4 should be Complete, add Phases 5/6/7 with accurate descriptions. Currently says Phase 4 is "In Progress" and has no mention of Phases 5-7.
- `website/docs/data-sources.mdx` -- Remove 6 broken international grant sources (ERC, Horizon, MRC, CIHR, KAKEN, NSFC), add OpenAlex Works and OpenAlex Grants, update geographic coverage section.
- `website/docs/architecture/overview.mdx` -- Add Phase 5, 6, 7 sections. Currently ends at Phase 4 "In Progress".
- `website/docs/how-it-works/data-pipeline.mdx` -- Add OpenAlex source, document async pipeline (POST /v1/queries now returns HTTP 202 immediately), remove references to broken sources.
- `website/docs/how-it-works/scoring.mdx` -- Update F2 description (OpenAlex replaces intl grants), add query type classifier section (basic_research/drug_discovery/clinical_trial_pi/policy_epi), add per-query-type weight vector section.
- `website/docs/what-is-aegis.mdx` -- Add Jobs system and shortlists to "What Aegis Produces" section. Update general descriptions to reflect 7 completed phases.
- `website/docs/architecture/diagrams.mdx` -- Remove placeholder text ("This diagram is a placeholder"), the SVGs are now real.
- `website/docs/how-it-works/feedback-loop.mdx` -- Add refit API endpoint (POST /v1/refit/trigger, GET /v1/refit/status).
- `website/static/images/architecture.svg` -- Replace "ERC / MRC / CIHR" row with "OpenAlex", update "+ 8 more sources" count, update "Next.js . 3 screens" to reflect actual screen count.
- `website/sidebars.ts` -- Add "Using Aegis" category with 3 new pages between "What is Aegis?" and "How It Works".

### New Files to Create

- `website/docs/using-aegis/submitting-a-query.mdx` -- New Query form walkthrough
- `website/docs/using-aegis/monitoring-a-job.mdx` -- Jobs list + Job detail page with SSE source grid
- `website/docs/using-aegis/reading-results.mdx` -- Results page, candidate rows, score breakdowns, evidence trail

### Source Files for Reference (read-only, for understanding actual behavior)

- `src/aegis/api/server.py` -- Shows POST /v1/queries returns 202, async pipeline, mounted routers
- `src/aegis/api/jobs.py` -- Shows jobs API endpoints (list, get, cancel)
- `src/aegis/pipeline/orchestrator.py` -- Shows actual 5 sources: pubmed, reporter, ctgov, openalex_works, openalex_grants
- `src/aegis/query/classifier.py` -- Shows 4 query types and keyword matching logic
- `src/aegis/api/refit.py` -- Shows POST /v1/refit/trigger and GET /v1/refit/status
- `frontend/src/components/query/QueryForm.tsx` -- Shows query form with classification, MeSH inspector, weight sliders
- `frontend/src/app/jobs/page.tsx` -- Shows jobs list with 3s polling, status badges, progress bars
- `frontend/src/app/jobs/[id]/page.tsx` -- Shows job detail with SSE source grid, cancel button
- `frontend/src/app/results/[id]/page.tsx` -- Shows results page with weight sliders, comparison modal, feedback
- `frontend/src/components/Header.tsx` -- Shows nav: New Query, Jobs, Query History, Shortlists

## Implementation Phases

### Phase 1: Foundation
Update sidebars.ts and fix the SVG diagram -- these are simple structural changes that unblock the new pages.

### Phase 2: Core Implementation
Parallel work:
- Builder-1 rewrites all 8 existing docs pages plus the SVG
- Builder-2 creates 3 new "Using Aegis" pages plus sidebar update

### Phase 3: Integration & Polish
Validator runs `npm run build` and verifies content accuracy against source code.

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Rewrites all existing docs pages and fixes the architecture SVG
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Creates 3 new "Using Aegis" pages and updates sidebar navigation
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator

## Step by Step Tasks

### 1. Rewrite roadmap.mdx
- **Task ID**: rewrite-roadmap
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Rewrite `website/docs/roadmap.mdx` to reflect all 7 completed phases plus Phase 7 (Jobs System).

    ## What to do
    1. Read `website/docs/roadmap.mdx` to see the current content
    2. Rewrite the file completely with accurate phase information

    ## Files to modify
    - `website/docs/roadmap.mdx` -- Full rewrite

    ## Exact content to write

    The file must keep `sidebar_position: 5` and `title: Roadmap` in its frontmatter.

    ### Phase Status Table
    Update the table to show ALL phases 0-7 as Complete:

    | Phase | Name | Status | Summary |
    |-------|------|--------|---------|
    | 0 | Foundation | Complete | DuckDB schema, PubMed/RePORTER/CT.gov ingestion, two-tier identity resolution, NSCLC seed cohort, archetype validation |
    | 1 | Scoring | Complete | Quality prior (F1-F6), integrity gate, topical fit, recency, end-to-end ranker, audit panel, Plackett-Luce weight learning, observability |
    | 2 | Multi-Population | Complete | Drug-discovery (USPTO/EPO patents, CPC-MeSH, ChEMBL), clinician (NPI, ABMS, state boards, USNWR), F7 clinician score, per-population weight vectors, specialty classifier, cross-population merge |
    | 3 | Production | Complete | FastAPI + JWT auth, event-driven integrity ingestion, LLM query expansion, downstream feedback loop, contestability workflow |
    | 4 | Frontend + Docs | Complete | Next.js frontend (New Query, Results, Query History), Docusaurus documentation site |
    | 5 | Production Reality | Complete | OpenAlex integration replacing international grant sources, real F1-F7 scoring, query type classifier, SSE streaming, shortlists, candidate notes, deployment to Fly.io/Vercel |
    | 6 | Full Wiring | Complete | Live ingestion pipeline, feedback router, refit API, HITL review queue API, WeightSliderPanel with live re-ranking, frontend proxy routes for all new APIs |
    | 7 | Jobs System | Complete | Async pipeline (POST /v1/queries returns HTTP 202), JobStore with DuckDB, /jobs and /jobs/[id] frontend pages with 3-second polling, SSE source progress grid, job cancellation support |

    ### "What Has Been Built" section
    Update to say "spanning 100+ tasks across seven completed phases" (not four). Add bullet points for:
    - **Async job pipeline** that returns immediately and streams source-by-source progress via SSE
    - **Query type classifier** that automatically detects basic_research, drug_discovery, clinical_trial_pi, or policy_epi queries and loads appropriate weight vectors
    - **OpenAlex integration** for global publication and grant coverage, replacing six defunct international grant APIs
    - **Shortlists and candidate notes** for collaborative team review workflows
    - **HITL review queue** for probabilistic identity match decisions

    Remove the "What Is In Progress" section entirely (nothing is in progress).

    ### "What Comes Next" section
    Keep the future work items but remove any reference to Phase 4 being in progress. The planned future areas remain valid: additional populations, deeper geographic coverage, code and dataset artifacts, enhanced feedback signals.

    ### Phase 3 description fix
    In the Phase 3 row, remove "geographic broadening (EPO/ERC/MRC/CIHR/KAKEN/NSFC)" -- these sources are broken. Phase 3 should mention the contestability workflow instead.

    ## Code patterns to follow
    - Use standard Docusaurus MDX frontmatter format
    - Keep the same writing style as the existing doc (professional, technical, factual)
    - Do NOT use emojis

    ## Acceptance criteria
    - All 8 phases listed as Complete
    - No mention of Phase 4 "In Progress"
    - No mention of broken international grant sources (ERC, Horizon, MRC, CIHR, KAKEN, NSFC) in Phase 3 description
    - Phase 5, 6, 7 descriptions match the actual implementations described above
    - "What Is In Progress" section removed

    ## Validation command
    `grep -c "In Progress" website/docs/roadmap.mdx` should return 0
    `grep -c "Complete" website/docs/roadmap.mdx` should return 8 or more

### 2. Update data-sources.mdx
- **Task ID**: update-data-sources
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Update `website/docs/data-sources.mdx` to remove broken international grant sources and add OpenAlex.

    ## What to do
    1. Read `website/docs/data-sources.mdx`
    2. Remove these 6 rows from the Grants table:
       - ERC (European Research Council)
       - Horizon Europe
       - MRC (Medical Research Council)
       - CIHR (Canadian Institutes of Health Research)
       - JST/KAKEN
       - NSFC (National Natural Science Foundation of China)
    3. Add two new rows to the appropriate sections:
       - In a new "Publications & Grants (Global)" section or add to Publications:
         - **OpenAlex Works**: Global scholarly works database covering publications, authors, concepts, and institutions across all disciplines. Provides PMID cross-references, author disambiguation, and institutional affiliations. Refresh Weekly. Populations: Translational, Drug Discovery.
         - **OpenAlex Grants**: Global grant funding data covering major international funders (NIH, ERC, MRC, Wellcome Trust, DFG, and others). Provides funder-investigator-topic relationships. Refresh Weekly. Populations: Translational.
    4. Update the intro paragraph: change "approximately 25 sources" to "approximately 20 sources" (we removed 6 and added 2 via OpenAlex).
    5. Remove bioRxiv and medRxiv rows from the Publications table -- these were planned but are not actually fetched in the deployed pipeline. The deployed pipeline (see `src/aegis/pipeline/orchestrator.py` lines 263-269) only uses: pubmed, reporter, ctgov, openalex_works, openalex_grants.
    6. Update the Geographic Coverage section at the bottom:
       - Remove mention of "EPO, ERC, MRC, CIHR, JST/KAKEN, NSFC" as international sources
       - Replace with: "Aegis achieves international coverage primarily through OpenAlex, which indexes scholarly output from institutions and funders worldwide. PubMed and NIH RePORTER provide US-focused coverage, while ClinicalTrials.gov includes international trial sites. The per-region coverage diagnostics with a 75% bias threshold remain active."
       - Remove the "40%+ non-US candidate coverage" target claim (this was aspirational and based on the now-broken international sources)
    7. Keep the Patents, Clinical, Clinician Credentials, Integrity, and Taxonomy sections exactly as they are -- those sources are designed/planned and the docs accurately describe their intended function even if not all are in the live query pipeline.

    ## Files to modify
    - `website/docs/data-sources.mdx`

    ## Code patterns to follow
    - Keep the same table format (Markdown tables with | delimiters)
    - Keep the same writing style
    - Maintain sidebar_position: 4 and title: Data Sources frontmatter

    ## Acceptance criteria
    - No rows for ERC, Horizon Europe, MRC, CIHR, JST/KAKEN, or NSFC in the Grants table
    - OpenAlex Works and OpenAlex Grants appear as data sources
    - bioRxiv and medRxiv removed (not in deployed pipeline)
    - Geographic coverage section updated to reference OpenAlex
    - Source count updated to approximately 20

    ## Validation command
    `grep -i "ERC\|Horizon Europe\|KAKEN\|NSFC\|CIHR" website/docs/data-sources.mdx | grep -v "OpenAlex"` should return nothing (no standalone references to broken sources)

### 3. Update architecture overview.mdx
- **Task ID**: update-arch-overview
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Update `website/docs/architecture/overview.mdx` to add Phases 5, 6, and 7.

    ## What to do
    1. Read `website/docs/architecture/overview.mdx`
    2. Change the intro line from "five phases" to "eight phases"
    3. Update "Phase 4 -- Frontend (In Progress)" to "Phase 4 -- Frontend + Docs (Complete)"
    4. Add three new sections after Phase 4:

    ### Phase 5 -- Production Reality

    **What it built:** The transition from prototype to production reality. Phase 5 replaced six broken international grant source clients (ERC, Horizon Europe, MRC, CIHR, JST/KAKEN, NSFC) with OpenAlex -- a single unified API covering global publications, authors, concepts, institutions, and funders. It implemented real F1-F7 scoring in the pipeline orchestrator, replacing stub scores with actual computations based on publication counts, grant history, leadership signals, translational output, and MeSH topic breadth. The query type classifier was added to automatically detect four query archetypes (basic_research, drug_discovery, clinical_trial_pi, policy_epi) via keyword matching and route each query to an appropriate weight vector. SSE streaming was implemented so the frontend can display source-by-source progress in real time as the pipeline fetches from each data source. Shortlists and candidate notes were added for collaborative team workflows. The system was deployed to production on Fly.io (backend) and Vercel (frontend).

    **What it unlocked:** Aegis became a deployed, production-grade system with real data flowing through every layer. Task managers could submit queries and receive real rankings backed by live data from PubMed, NIH RePORTER, ClinicalTrials.gov, and OpenAlex -- approximately 360 candidates per query.

    ### Phase 6 -- Full Wiring

    **What it built:** Phase 6 connected every remaining stub and placeholder to live implementations. The ingestion converters were wired into the pipeline orchestrator, so query-time source fetches produce properly structured Candidate records that merge with the DuckDB store via the RecordIngester and ProbabilisticLinker. The feedback router was mounted so POST /v1/feedback/tasks/{id}/outcomes actually processes task quality data. The refit API (POST /v1/refit/trigger, GET /v1/refit/status) was implemented to trigger weight relearning cycles from the API. The HITL review queue API (GET /v1/hitl/next, POST /v1/hitl/{id}/decide, GET /v1/hitl/stats) was implemented for managing probabilistic identity match decisions. The WeightSliderPanel gained a "Reset to trained" button and now drives live client-side re-ranking on the results page. Frontend proxy routes were created for all new backend APIs (refit, HITL, candidates notes).

    **What it unlocked:** Every component of the system -- from data ingestion through scoring, ranking, feedback, and weight relearning -- was connected end-to-end with no remaining stubs. The frontend could access every backend capability through its proxy API routes.

    ### Phase 7 -- Jobs System

    **What it built:** Phase 7 converted the query pipeline from synchronous to asynchronous execution. POST /v1/queries now returns HTTP 202 immediately with `{job_id, status: "in_progress"}` instead of blocking until the pipeline completes. The pipeline runs as an `asyncio.create_task` in the background. A new JobStore (DuckDB table) tracks job lifecycle: id, query_text, status (in_progress/complete/failed/cancelled), created_at, completed_at, duration_ms, source_count, candidate_count. An in-memory task registry enables job cancellation. Three new API endpoints were added: GET /v1/jobs (list), GET /v1/jobs/{id} (detail), POST /v1/jobs/{id}/cancel. The frontend gained a /jobs page with a table showing all jobs with status badges and mini animated progress bars, polling every 3 seconds while any job is in_progress. The /jobs/[id] detail page shows a 5-source SSE progress grid (PubMed, NIH Reporter, CT.gov, OpenAlex Works, OpenAlex Grants), a Cancel button, and a "View Results" link when complete.

    **What it unlocked:** Task managers no longer wait for the full pipeline to complete (which can take 30-60 seconds across 5 source APIs). They submit a query, get redirected to the jobs page, and can monitor real-time progress or start another query immediately.

    5. Remove "In Progress" from the Phase 4 section and update its description to past tense.

    ## Files to modify
    - `website/docs/architecture/overview.mdx`

    ## Code patterns to follow
    - Follow the exact same structure as existing Phase sections: h2 with "Phase N -- Name", then **What it built:** and **What it unlocked:** paragraphs
    - Keep sidebar_position: 1, title: Phase-by-Phase Overview

    ## Acceptance criteria
    - Intro says "eight phases" not "five phases"
    - Phase 4 marked Complete, not In Progress
    - Phase 5, 6, 7 sections present with accurate descriptions
    - No mention of "In Progress" for any phase
    - Writing style consistent with existing sections

    ## Validation command
    `grep -c "In Progress" website/docs/architecture/overview.mdx` should return 0
    `grep "Phase 7" website/docs/architecture/overview.mdx` should find a match

### 4. Update data-pipeline.mdx
- **Task ID**: update-data-pipeline
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Update `website/docs/how-it-works/data-pipeline.mdx` to add OpenAlex source and document the async pipeline.

    ## What to do
    1. Read `website/docs/how-it-works/data-pipeline.mdx`
    2. Update the intro paragraph: change "approximately 25 sources" to "approximately 20 sources"
    3. Add a new section after "Source Clients" called "Async Query Pipeline":

    ## Async Query Pipeline

    When a task manager submits a query, Aegis does not block the request while fetching from all sources. Instead, POST /v1/queries returns HTTP 202 immediately with a job identifier and status. The pipeline then runs asynchronously in the background, fetching from five sources in parallel:

    1. **PubMed** -- Indexed biomedical publications with MeSH descriptors and author affiliations
    2. **NIH RePORTER** -- US federal research grants with principal investigators and activity codes
    3. **ClinicalTrials.gov** -- Clinical trial registrations with investigator roles and trial phases
    4. **OpenAlex Works** -- Global scholarly works covering publications, authors, concepts, and institutions
    5. **OpenAlex Grants** -- International grant funding data across major global funders

    As each source completes, a Server-Sent Events (SSE) progress update is pushed to any connected frontend client. The frontend displays a real-time source grid showing the status of each source: pending, fetching, complete, or failed -- along with record counts for completed sources.

    Each source fetch is capped at 200 records per source (100 for OpenAlex Grants per funder) to keep query latency manageable. Records are converted into Candidate objects and ingested into the DuckDB store through the RecordIngester, which handles identity resolution via strong-key matching and probabilistic linking.

    A typical query fetches approximately 360 total candidate records across all five sources before deduplication.

    4. In the "Ingestion Cadence" section, update the Daily tier:
       - Remove references to bioRxiv and medRxiv as daily sources (they are not in the deployed pipeline)
       - Or soften to: "Daily ingestion is designed for preprint servers (bioRxiv, medRxiv) when enabled."

    5. In the "Ingestion Cadence" section, update the Weekly tier:
       - Remove "EPO" from the list of weekly sources
       - Add "OpenAlex" to the list of weekly sources

    ## Files to modify
    - `website/docs/how-it-works/data-pipeline.mdx`

    ## Code patterns to follow
    - Keep the same section heading style (h2 headers)
    - Maintain the same explanatory writing style
    - Keep sidebar_position: 1, title: Data Pipeline

    ## Acceptance criteria
    - OpenAlex mentioned as a data source
    - Async pipeline section present explaining HTTP 202 behavior
    - Five source names listed (pubmed, reporter, ctgov, openalex_works, openalex_grants)
    - SSE progress updates mentioned
    - Source count updated to approximately 20

    ## Validation command
    `grep -i "OpenAlex" website/docs/how-it-works/data-pipeline.mdx` should find matches
    `grep "202" website/docs/how-it-works/data-pipeline.mdx` should find a match

### 5. Update scoring.mdx
- **Task ID**: update-scoring
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Update `website/docs/how-it-works/scoring.mdx` to reflect OpenAlex replacing international grants in F2 and add the query type classifier.

    ## What to do
    1. Read `website/docs/how-it-works/scoring.mdx`
    2. Update the F2 description:
       - Current: "Tracks NIH and international grant activity"
       - New: "Tracks grant activity from NIH RePORTER and OpenAlex Grants (which covers major international funders including ERC, Wellcome Trust, DFG, and others), considering total funding, number of active grants, and the progression from early-career to established investigator awards."
    3. Add a new section before "Per-Population Weights" called "Query Type Classifier":

    ## Query Type Classifier

    Before scoring begins, Aegis classifies the incoming query into one of four query types:

    - **basic_research** -- The default type for general translational and biomedical research queries. Used when no strong keyword signal matches another type.
    - **drug_discovery** -- Triggered by keywords related to pharmaceutical development: "inhibitor", "compound", "IC50", "ADME", "lead optimization", "structure-activity", and similar terms.
    - **clinical_trial_pi** -- Triggered by keywords related to clinical trials: "principal investigator", "Phase I/II/III", "randomized", "placebo", "endpoint", "protocol", and similar terms.
    - **policy_epi** -- Triggered by keywords related to epidemiology and public health policy: "epidemiology", "population health", "surveillance", "health equity", "incidence", "prevalence", and similar terms.

    The classifier uses keyword matching against the query text. Each keyword match increases confidence in the detected type. When no keywords match any specialized type, the query defaults to basic_research with 50% confidence.

    Each query type maps to a specific weight vector file that determines the relative importance of scoring components. For example, a drug_discovery query may weight translational output (patents) more heavily, while a clinical_trial_pi query may emphasize the clinician-specific F7 score and leadership roles.

    Weight vector files are stored in `config/aegis/weights/` as YAML files with versioned names (e.g., `basic_research_v1.yaml`, `drug_discovery_v1.yaml`).

    4. Update the "Per-Population Weights" section title to "Per-Population and Per-Query-Type Weights" and add a note that weight vectors are now selected both by population and by query type classification.

    ## Files to modify
    - `website/docs/how-it-works/scoring.mdx`

    ## Code patterns to follow
    - Keep the same h2 section style
    - Keep sidebar_position: 4, title: Scoring

    ## Acceptance criteria
    - F2 description mentions OpenAlex Grants (not just NIH)
    - Query Type Classifier section present with all 4 types listed
    - Weight vector files mentioned by path pattern
    - No mention of broken international grant sources as standalone F2 contributors

    ## Validation command
    `grep "classifier" website/docs/how-it-works/scoring.mdx` should find matches
    `grep "OpenAlex" website/docs/how-it-works/scoring.mdx` should find matches

### 6. Update what-is-aegis.mdx
- **Task ID**: update-what-is-aegis
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Update `website/docs/what-is-aegis.mdx` to add Jobs system and shortlists to "What Aegis Produces".

    ## What to do
    1. Read `website/docs/what-is-aegis.mdx`
    2. In the "What Aegis Produces" section, add two new bullet points after the existing four:
       - **A job tracking system** that lets task managers submit queries and immediately move on. Each query runs asynchronously and its progress -- source by source -- is visible in real time through the Jobs dashboard.
       - **Shortlists and notes** for organizing and annotating candidates across team members. Task managers can add candidates to named shortlists, attach analyst notes with structured tags, and share these collections with their team.
    3. In the intro paragraph, change "approximately 25 sources" to "approximately 20 sources"
    4. In the "Three Researcher Populations" > "Translational" section, update "NIH and international grants" to "NIH grants and OpenAlex-indexed international grants"
    5. Keep everything else exactly as-is

    ## Files to modify
    - `website/docs/what-is-aegis.mdx`

    ## Code patterns to follow
    - Keep the same bullet point format with **bold label** followed by description
    - Keep sidebar_position: 1, title: What is Aegis?

    ## Acceptance criteria
    - "A job tracking system" bullet point present in "What Aegis Produces"
    - "Shortlists and notes" bullet point present in "What Aegis Produces"
    - Source count says approximately 20
    - OpenAlex mentioned in Translational section

    ## Validation command
    `grep -i "shortlist" website/docs/what-is-aegis.mdx` should find a match
    `grep -i "job" website/docs/what-is-aegis.mdx` should find matches

### 7. Update diagrams.mdx and architecture SVG
- **Task ID**: update-diagrams
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Fix `website/docs/architecture/diagrams.mdx` and `website/static/images/architecture.svg`.

    ## What to do for diagrams.mdx
    1. Read `website/docs/architecture/diagrams.mdx`
    2. Remove the two placeholder notes that say "*This diagram is a placeholder. The final version will be created in Excalidraw or Figma.*"
    3. The image references `![High-level architecture diagram](/images/architecture.svg)` and `![Data flow diagram](/images/data-flow.svg)` should stay as-is (they already point to the correct files)
    4. Update the intro to reference the correct layer count if needed and mention that the diagrams reflect the deployed architecture

    ## What to do for architecture.svg
    1. Read `website/static/images/architecture.svg`
    2. Find the text element that says "ERC / MRC / CIHR" (line 35 area) and change it to "OpenAlex"
    3. Find the text element that says "+ 8 more sources" (line 59 area) and change it to "+ 6 more sources" (we removed 6 international grant sources and bioRxiv/medRxiv = 8 removed, added 2 OpenAlex = net -6, so from original ~25 showing ~12 in diagram, the "more" count decreases)
       - Actually, let's count what's shown in the SVG: PubMed/iCite, bioRxiv/medRxiv, NIH RePORTER, ERC/MRC/CIHR (changing to OpenAlex), USPTO/EPO/WIPO, ClinicalTrials.gov, NPPES/ABMS, State Med. Boards, Retraction Watch, ORI/OFAC/LEIE, ChEMBL/CPC-MeSH = 11 rows. The remaining sources not shown include: USNWR, CMS Medicare, ICD-10/CPT-MeSH, WIPO PCT (already shown as part of "USPTO/EPO/WIPO"). So change to "+ 5 more sources"
    4. Find the text "Next.js . 3 screens" (line 136 area) and update to "Next.js . 8 screens" (the frontend now has 8 distinct page routes: /, /jobs, /jobs/[id], /results/[id], /history, /shortlists, /shortlists/[id], /candidates/[uuid])
    5. Change the "bioRxiv / medRxiv" row to "OpenAlex Works" since bioRxiv/medRxiv are not in the deployed pipeline but OpenAlex Works is a key source

    ## Files to modify
    - `website/docs/architecture/diagrams.mdx`
    - `website/static/images/architecture.svg`

    ## SVG edit details
    The SVG is a hand-authored SVG with `<text>` elements. Changes are straightforward text replacements:
    - Line 35: `<text x="98" y="201" text-anchor="middle" font-size="11" fill="#333">ERC / MRC / CIHR</text>` -> `<text x="98" y="201" text-anchor="middle" font-size="11" fill="#333">OpenAlex Grants</text>`
    - Line 29: `<text x="98" y="141" text-anchor="middle" font-size="11" fill="#333">bioRxiv / medRxiv</text>` -> `<text x="98" y="141" text-anchor="middle" font-size="11" fill="#333">OpenAlex Works</text>`
    - Line 59: `<text x="98" y="438" text-anchor="middle" font-size="10" fill="#777">+ 8 more sources</text>` -> `<text x="98" y="438" text-anchor="middle" font-size="10" fill="#777">+ 5 more sources</text>`
    - Line 136: `<text x="630" y="452" text-anchor="middle" font-size="10" fill="#555">Next.js · 3 screens</text>` -> `<text x="630" y="452" text-anchor="middle" font-size="10" fill="#555">Next.js · 8 screens</text>`

    ## Code patterns to follow
    - SVG edits are text-only replacements within existing `<text>` elements
    - Do not change any positioning, colors, or structural SVG elements

    ## Acceptance criteria
    - "ERC / MRC / CIHR" no longer appears in the SVG
    - "OpenAlex" appears in the SVG (as "OpenAlex Grants")
    - "OpenAlex Works" appears in the SVG (replacing bioRxiv/medRxiv)
    - Screen count updated to 8
    - Placeholder text removed from diagrams.mdx

    ## Validation command
    `grep "ERC" website/static/images/architecture.svg` should return nothing
    `grep "OpenAlex" website/static/images/architecture.svg` should find matches
    `grep "placeholder" website/docs/architecture/diagrams.mdx` should return nothing

### 8. Update feedback-loop.mdx
- **Task ID**: update-feedback-loop
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Update `website/docs/how-it-works/feedback-loop.mdx` to add the refit API endpoints.

    ## What to do
    1. Read `website/docs/how-it-works/feedback-loop.mdx`
    2. Add a new section after "Weight Relearning" called "Refit API":

    ## Refit API

    Weight relearning can be triggered on demand through the API, in addition to the weekly automated cadence:

    - **POST /v1/refit/trigger** -- Triggers an immediate weight refit cycle for a given specialty. The endpoint loads the latest weight vector YAML file, runs the Plackett-Luce refitter against accumulated audit-panel judgments and downstream-quality-derived pairs, evaluates convergence and stability guards, and returns the result including prior exponents, new exponents, delta values, and the deployment decision (auto_deploy, manual_gate, or blocked).

    - **GET /v1/refit/status** -- Returns the current refit status for a specialty, including the current weight vector version, exponent values, confidence interval half-widths, and the count of pending downstream outcomes awaiting processing.

    These endpoints enable operators to trigger refits when new feedback data has been collected without waiting for the weekly cycle, and to monitor the current state of weight vectors across specialties.

    ## Files to modify
    - `website/docs/how-it-works/feedback-loop.mdx`

    ## Code patterns to follow
    - Keep the same h2 section style
    - Use the same technical writing style (factual, specific)
    - Keep sidebar_position: 5, title: Feedback Loop

    ## Acceptance criteria
    - POST /v1/refit/trigger documented
    - GET /v1/refit/status documented
    - Section placed after Weight Relearning

    ## Validation command
    `grep "refit" website/docs/how-it-works/feedback-loop.mdx` should find matches

### 9. Update sidebar and create Using Aegis directory
- **Task ID**: update-sidebar
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Update `website/sidebars.ts` to add the "Using Aegis" section and create the directory for new pages.

    ## What to do
    1. Read `website/sidebars.ts`
    2. Create the directory `website/docs/using-aegis/` (use `mkdir -p`)
    3. Update sidebars.ts to add a "Using Aegis" category between "what-is-aegis" and the "How It Works" category:

    ```typescript
    import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

    const sidebars: SidebarsConfig = {
      docsSidebar: [
        'what-is-aegis',
        {
          type: 'category',
          label: 'Using Aegis',
          items: [
            'using-aegis/submitting-a-query',
            'using-aegis/monitoring-a-job',
            'using-aegis/reading-results',
          ],
        },
        {
          type: 'category',
          label: 'How It Works',
          items: [
            'how-it-works/data-pipeline',
            'how-it-works/identity-resolution',
            'how-it-works/integrity-gate',
            'how-it-works/scoring',
            'how-it-works/feedback-loop',
          ],
        },
        {
          type: 'category',
          label: 'System Architecture',
          items: [
            'architecture/overview',
            'architecture/diagrams',
          ],
        },
        'data-sources',
        'roadmap',
      ],
    };

    export default sidebars;
    ```

    ## Files to modify
    - `website/sidebars.ts` -- Add "Using Aegis" category

    ## Acceptance criteria
    - "Using Aegis" category exists in sidebars with 3 items
    - Category appears between 'what-is-aegis' and 'How It Works'
    - All three page IDs match: using-aegis/submitting-a-query, using-aegis/monitoring-a-job, using-aegis/reading-results

    ## Validation command
    `grep "using-aegis" website/sidebars.ts` should find 3 matches (one per page)

### 10. Create submitting-a-query.mdx
- **Task ID**: create-submitting-query
- **Role**: builder
- **Depends On**: update-sidebar
- **Assigned To**: builder-2
- **Description**: |
    Create `website/docs/using-aegis/submitting-a-query.mdx` documenting the New Query form.

    ## What to do
    1. Create the file `website/docs/using-aegis/submitting-a-query.mdx`
    2. Write content based on the actual QueryForm component (read `frontend/src/components/query/QueryForm.tsx` for reference)

    ## Content to write

    The file should have this frontmatter:
    ```
    ---
    sidebar_position: 1
    title: Submitting a Query
    ---
    ```

    Then the following sections:

    ### # Submitting a Query

    Opening paragraph: The New Query page is the starting point for expert discovery in Aegis. Task managers describe the expertise they need in free text, and Aegis handles query expansion, source fetching, scoring, and ranking automatically.

    ### ## The Query Form

    Describe the main form fields:

    **Task Description (required):** A free-text field where the task manager describes the type of researcher expertise needed. For example: "KRAS inhibitor drug discovery for lung cancer" or "RAS oncogene translational research pancreatic cancer." As the user types, the query type classifier runs in the background (debounced at 300ms) and displays a badge indicating the detected query type.

    **Population Selector:** Optional. Choose a specific researcher population (Translational, Drug Discovery, Clinician) or leave as "auto" to let the classifier decide.

    **K Slider:** Controls how many top candidates to return. Default is 20, adjustable via slider.

    ### ## Query Type Classification

    When the task description is at least 5 characters long, Aegis classifies it into one of four types:

    - **basic_research** -- General biomedical and translational research (default)
    - **drug_discovery** -- Pharmaceutical and drug development queries
    - **clinical_trial_pi** -- Clinical trial principal investigator searches
    - **policy_epi** -- Epidemiology and public health policy queries

    The detected type appears as a badge next to the task description field, showing the type name and confidence level. Task managers can click the badge to override the detected type if needed.

    Each type selects a different weight vector that adjusts how scoring components (quality, topical fit, recency) are balanced in the ranking.

    ### ## Advanced Options

    Clicking "Advanced Options" expands additional controls:

    **MeSH Term Inspector:** Shows the MeSH terms that will be used for topical fit scoring. Terms can be added or removed manually.

    **Weight Sliders:** Displays the scoring exponents (alpha, beta, gamma) from the selected weight vector. Task managers can adjust these sliders to re-weight how quality prior, topical fit, and recency contribute to the final ranking.

    **MeSH Override:** Manually specify MeSH descriptors to use instead of the auto-expanded terms.

    **Cutoff Strategy:** Optional field for specifying how candidates below a quality threshold should be filtered (e.g., score_threshold, elbow).

    ### ## What Happens on Submit

    When the form is submitted:

    1. A POST request is sent to /v1/queries with the task description, K value, population, and any MeSH overrides
    2. The backend returns HTTP 202 immediately with a job_id
    3. The frontend redirects to /jobs/{job_id} where the task manager can monitor pipeline progress in real time

    The query does not block -- results are available once the background pipeline completes, typically within 30-60 seconds.

    ## Files to create
    - `website/docs/using-aegis/submitting-a-query.mdx`

    ## Code patterns to follow
    - Use standard Docusaurus MDX format with frontmatter
    - Use h1 for page title, h2 for sections, h3 for subsections
    - Professional technical writing style consistent with existing docs
    - No emojis

    ## Acceptance criteria
    - File exists at website/docs/using-aegis/submitting-a-query.mdx
    - All four query types documented
    - HTTP 202 async behavior explained
    - Advanced options documented (MeSH, weight sliders, cutoff)
    - Frontmatter has sidebar_position: 1

    ## Validation command
    `test -f website/docs/using-aegis/submitting-a-query.mdx && echo "exists"` should print "exists"

### 11. Create monitoring-a-job.mdx
- **Task ID**: create-monitoring-job
- **Role**: builder
- **Depends On**: update-sidebar
- **Assigned To**: builder-2
- **Description**: |
    Create `website/docs/using-aegis/monitoring-a-job.mdx` documenting the Jobs list and detail pages.

    ## What to do
    1. Create the file `website/docs/using-aegis/monitoring-a-job.mdx`
    2. Write content based on the actual frontend pages (reference `frontend/src/app/jobs/page.tsx` and `frontend/src/app/jobs/[id]/page.tsx`)

    ## Content to write

    Frontmatter:
    ```
    ---
    sidebar_position: 2
    title: Monitoring a Job
    ---
    ```

    ### # Monitoring a Job

    Opening paragraph: After submitting a query, Aegis runs the expert discovery pipeline in the background. The Jobs pages let task managers track progress, monitor source fetching, and navigate to results once complete.

    ### ## Jobs List (/jobs)

    The Jobs page shows a table of all submitted queries with the following columns:

    - **Query** -- The task description text (truncated if long)
    - **Status** -- A color-coded badge: Running (amber with spinner), Complete (green with checkmark), Failed (red with X), or Cancelled (gray)
    - **Started** -- Relative timestamp (e.g., "5m ago", "2h ago")
    - **Duration** -- How long the pipeline took (shown as milliseconds or seconds)
    - **Candidates** -- Number of candidates found (shown after completion)
    - **Actions** -- "View Results" link for completed jobs, "Monitor" link for running jobs

    **Auto-refresh:** While any job has status "in_progress", the page polls the backend every 3 seconds to update the table. When all jobs are complete or failed, polling stops.

    **Progress indicator:** Running jobs display a mini animated progress bar below the status badge.

    **Pagination:** When there are more than 20 jobs, Previous/Next buttons appear at the bottom of the table.

    ### ## Job Detail (/jobs/{id})

    Clicking "Monitor" on a running job (or navigating to /jobs/{id}) shows the job detail page with:

    **Header:** Back link to Jobs list, Cancel button (for running jobs), or "View Results" button (for completed jobs).

    **Query info:** The full task description text, status badge, start time, and candidate count.

    **Source Progress Grid:** A grid of 5 source cards, one for each data source:

    | Source | Label |
    |--------|-------|
    | pubmed | PubMed |
    | reporter | NIH Reporter |
    | ctgov | CT.gov |
    | openalex_works | OpenAlex Works |
    | openalex_grants | OpenAlex Grants |

    Each card shows:
    - The source name
    - Current status (pending, fetching, complete, or failed)
    - Record count when complete (e.g., "142 records")
    - A pulsing progress bar while fetching

    Source progress updates are delivered via Server-Sent Events (SSE). The frontend opens an EventSource connection to /api/queries/{id}/stream and listens for `source_progress` events. When the `complete` event fires, the connection closes and the job data is refreshed.

    ### ## Cancelling a Job

    Running jobs can be cancelled by clicking the Cancel button on the job detail page. This sends a POST to /api/jobs/{id}, which cancels the background asyncio task and updates the job status to "cancelled". The SSE connection is closed and the source grid stops updating.

    ### ## Job Lifecycle

    A job progresses through these statuses:

    1. **in_progress** -- Pipeline is running, sources are being fetched
    2. **complete** -- Pipeline finished successfully, results are available at /results/{id}
    3. **failed** -- Pipeline encountered an error (task manager can resubmit the query)
    4. **cancelled** -- Task manager cancelled the job before completion

    ## Files to create
    - `website/docs/using-aegis/monitoring-a-job.mdx`

    ## Code patterns to follow
    - Use standard Docusaurus MDX format
    - Professional technical writing style
    - No emojis

    ## Acceptance criteria
    - File exists at website/docs/using-aegis/monitoring-a-job.mdx
    - Jobs list page documented with all columns
    - SSE source grid documented with all 5 sources
    - Cancel functionality documented
    - Auto-refresh / 3s polling mentioned
    - Job lifecycle statuses listed
    - Frontmatter has sidebar_position: 2

    ## Validation command
    `test -f website/docs/using-aegis/monitoring-a-job.mdx && echo "exists"` should print "exists"

### 12. Create reading-results.mdx
- **Task ID**: create-reading-results
- **Role**: builder
- **Depends On**: update-sidebar
- **Assigned To**: builder-2
- **Description**: |
    Create `website/docs/using-aegis/reading-results.mdx` documenting the Results page.

    ## What to do
    1. Create the file `website/docs/using-aegis/reading-results.mdx`
    2. Write content based on the actual results page (reference `frontend/src/app/results/[id]/page.tsx`)

    ## Content to write

    Frontmatter:
    ```
    ---
    sidebar_position: 3
    title: Reading Results
    ---
    ```

    ### # Reading Results

    Opening paragraph: The Results page displays ranked candidates for a completed query. Each candidate has a composite score broken down by component, along with evidence trails, integrity flags, and team collaboration features.

    ### ## Results Header

    The top of the page shows:
    - **Query type badge** -- The detected query type (basic_research, drug_discovery, etc.) with confidence level
    - **Task description** -- The original query text
    - **Metadata** -- Population (if specified), K value, result count, and timestamp
    - **Submit Feedback button** -- Opens the feedback modal for providing task quality signals

    ### ## Weight Sliders

    Below the header, the Weight Slider Panel allows task managers to adjust the scoring exponents in real time:

    - **Alpha** -- Controls the weight of the Quality Prior (Q) component
    - **Beta** -- Controls the weight of the Topical Fit (C) component
    - **Gamma** -- Controls the weight of the Recency (R) component

    Adjusting any slider triggers immediate client-side re-ranking of the candidate list without making a new API request. A "Reset to trained" button restores the exponents to their learned values.

    ### ## Candidate List

    Each candidate is displayed as a row showing:
    - **Rank number** -- Position in the current ranking (updates when weight sliders change)
    - **Candidate name** -- Primary name variant from the identity resolution pipeline
    - **Affiliation** -- Current institutional affiliation (if known)
    - **Composite score** -- The overall ranking score
    - **Score components** -- Individual scores for Quality (Q), Topical Fit (C), Recency (R), and Integrity (I)
    - **Identity linkage confidence** -- How confident the system is in the identity resolution for this candidate
    - **Team indicators** -- Whether the candidate is on any shortlist, and whether analyst notes exist

    Candidates can be selected for side-by-side comparison by checking the comparison toggle. When two or more candidates are selected, a floating "Compare" button appears that opens the Candidate Comparison Modal.

    ### ## Evidence Trail

    Expanding a candidate row reveals the evidence trail -- a detailed breakdown of the data supporting their ranking:

    - **Publications** -- PubMed articles with PMIDs and links
    - **iCite scores** -- Relative Citation Ratio (RCR) values for indexed publications, showing whether each paper is above or below the field average of 1.0
    - **Grants** -- NIH Reporter grant IDs with links to project details
    - **Clinical trials** -- ClinicalTrials.gov study IDs with links
    - **Narrative evidence** -- Free-text evidence strings tagged by source

    The evidence trail can be filtered by source tab: All, PubMed, iCite, NIH Grants, Trials, Notes.

    ### ## Geographic Coverage Warning

    When more than 75% of candidates in the results share the same affiliation or country, a yellow warning banner appears at the top of the results. This alerts the task manager that the candidate pool may be geographically skewed and suggests broadening the search scope.

    ### ## Candidate Comparison

    Selecting two or more candidates and clicking "Compare" opens a modal showing the selected candidates side by side with their score components, evidence counts, and key differences highlighted.

    ### ## Feedback Modal

    Clicking "Submit Feedback" opens a modal where task managers can provide quality signals about the ranking results. The feedback includes:
    - **Query specialty** -- The detected or overridden query type
    - **MeSH terms** -- The expanded MeSH terms used for scoring
    - **Per-candidate assessments** -- For each candidate: UUID, rank, quality prior score, topical fit score, and recency score

    This feedback feeds into the downstream task quality pipeline, generating pairwise judgments that improve future weight relearning cycles.

    ## Files to create
    - `website/docs/using-aegis/reading-results.mdx`

    ## Code patterns to follow
    - Use standard Docusaurus MDX format
    - Professional technical writing style
    - No emojis

    ## Acceptance criteria
    - File exists at website/docs/using-aegis/reading-results.mdx
    - Weight sliders documented with all 3 exponents
    - Evidence trail documented with source types
    - Candidate comparison feature documented
    - Feedback modal documented
    - Geographic coverage warning documented
    - Frontmatter has sidebar_position: 3

    ## Validation command
    `test -f website/docs/using-aegis/reading-results.mdx && echo "exists"` should print "exists"

### 13. Validate all changes
- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: rewrite-roadmap, update-data-sources, update-arch-overview, update-data-pipeline, update-scoring, update-what-is-aegis, update-diagrams, update-feedback-loop, update-sidebar, create-submitting-query, create-monitoring-job, create-reading-results
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria.

    ## Validation Commands

    First, verify all files exist:
    ```bash
    test -f website/docs/using-aegis/submitting-a-query.mdx && echo "submitting-a-query.mdx exists"
    test -f website/docs/using-aegis/monitoring-a-job.mdx && echo "monitoring-a-job.mdx exists"
    test -f website/docs/using-aegis/reading-results.mdx && echo "reading-results.mdx exists"
    ```

    Check for stale content in modified files:
    ```bash
    # No "In Progress" in roadmap
    grep -c "In Progress" website/docs/roadmap.mdx && echo "FAIL: roadmap still has In Progress" || echo "PASS: roadmap has no In Progress"

    # No broken intl sources in data-sources
    grep -i "KAKEN\|NSFC\|Horizon Europe" website/docs/data-sources.mdx && echo "FAIL: data-sources still has broken sources" || echo "PASS: data-sources clean"

    # No "In Progress" in architecture overview
    grep -c "In Progress" website/docs/architecture/overview.mdx && echo "FAIL: overview still has In Progress" || echo "PASS: overview clean"

    # Phase 7 in architecture overview
    grep "Phase 7" website/docs/architecture/overview.mdx && echo "PASS: Phase 7 present" || echo "FAIL: Phase 7 missing"

    # OpenAlex in data pipeline
    grep -i "OpenAlex" website/docs/how-it-works/data-pipeline.mdx && echo "PASS: OpenAlex in pipeline" || echo "FAIL: OpenAlex missing from pipeline"

    # HTTP 202 in data pipeline
    grep "202" website/docs/how-it-works/data-pipeline.mdx && echo "PASS: 202 in pipeline" || echo "FAIL: 202 missing from pipeline"

    # Query classifier in scoring
    grep -i "classifier" website/docs/how-it-works/scoring.mdx && echo "PASS: classifier in scoring" || echo "FAIL: classifier missing from scoring"

    # OpenAlex in scoring
    grep -i "OpenAlex" website/docs/how-it-works/scoring.mdx && echo "PASS: OpenAlex in scoring" || echo "FAIL: OpenAlex missing from scoring"

    # Shortlist in what-is-aegis
    grep -i "shortlist" website/docs/what-is-aegis.mdx && echo "PASS: shortlist present" || echo "FAIL: shortlist missing"

    # No ERC in SVG
    grep "ERC" website/static/images/architecture.svg && echo "FAIL: SVG still has ERC" || echo "PASS: SVG has no ERC"

    # OpenAlex in SVG
    grep "OpenAlex" website/static/images/architecture.svg && echo "PASS: OpenAlex in SVG" || echo "FAIL: OpenAlex missing from SVG"

    # No placeholder in diagrams
    grep -i "placeholder" website/docs/architecture/diagrams.mdx && echo "FAIL: placeholder still present" || echo "PASS: no placeholder"

    # Refit in feedback loop
    grep "refit" website/docs/how-it-works/feedback-loop.mdx && echo "PASS: refit in feedback" || echo "FAIL: refit missing"

    # Sidebar has using-aegis
    grep -c "using-aegis" website/sidebars.ts | xargs -I{} test {} -eq 3 && echo "PASS: 3 using-aegis refs" || echo "FAIL: wrong using-aegis count in sidebar"
    ```

    Build the docs site to ensure no broken links or build errors:
    ```bash
    cd website && npm run build
    ```

    ## Acceptance Criteria
    - All 3 new files exist in website/docs/using-aegis/
    - No "In Progress" text in roadmap.mdx or overview.mdx
    - No references to broken international grant sources (ERC, Horizon, KAKEN, NSFC) in data-sources.mdx
    - OpenAlex appears in data-sources.mdx, data-pipeline.mdx, scoring.mdx, and architecture.svg
    - Phase 7 documented in roadmap.mdx and overview.mdx
    - Query type classifier documented in scoring.mdx
    - Refit API documented in feedback-loop.mdx
    - Shortlists and jobs documented in what-is-aegis.mdx
    - SVG diagram updated (no ERC, shows OpenAlex)
    - Placeholder text removed from diagrams.mdx
    - Sidebar has "Using Aegis" category with 3 pages
    - `npm run build` succeeds in website/ directory

## Acceptance Criteria

1. All 8 existing docs pages updated with accurate content reflecting Phases 0-7
2. Three new "Using Aegis" pages created (submitting-a-query, monitoring-a-job, reading-results)
3. Sidebar updated with "Using Aegis" category between "What is Aegis?" and "How It Works"
4. Architecture SVG updated: "ERC / MRC / CIHR" replaced with "OpenAlex Grants", "bioRxiv / medRxiv" replaced with "OpenAlex Works"
5. No references to broken international grant sources (ERC, Horizon Europe, MRC, CIHR, KAKEN, NSFC) as working data sources
6. No "In Progress" status for any phase
7. Docusaurus site builds successfully with `npm run build`

## Validation Commands

Execute these commands to validate the task is complete:

- `cd website && npm run build` -- Verify the Docusaurus site builds without errors
- `grep -rn "In Progress" website/docs/` -- Should return nothing (no phases are in progress)
- `grep -rn "KAKEN\|NSFC\|Horizon Europe" website/docs/data-sources.mdx` -- Should return nothing (broken sources removed)
- `grep -rn "OpenAlex" website/docs/` -- Should find multiple matches across several files
- `grep "ERC" website/static/images/architecture.svg` -- Should return nothing
- `test -f website/docs/using-aegis/submitting-a-query.mdx && test -f website/docs/using-aegis/monitoring-a-job.mdx && test -f website/docs/using-aegis/reading-results.mdx && echo "All new files exist"` -- Should print confirmation
- `grep -c "using-aegis" website/sidebars.ts` -- Should return 3

## Notes

- The Docusaurus site is at `website/` and uses TypeScript config (`docusaurus.config.ts`)
- `onBrokenLinks: 'throw'` is set in config, so the build will fail if any internal links are broken -- this is a good validation gate
- The site builds with `npm run build` from the `website/` directory
- No new npm packages are needed
- The ERC and MRC rows can still appear in the Grants section as a historical note or as "planned" sources if the builder prefers, but they should NOT appear as working/active data sources in the main pipeline documentation. The cleaner approach is to remove them from the Grants table entirely since they are not functional.
- bioRxiv/medRxiv should be removed from the data-sources table and any mention as actively-fetched sources since `src/aegis/pipeline/orchestrator.py` only fetches from 5 sources: pubmed, reporter, ctgov, openalex_works, openalex_grants
