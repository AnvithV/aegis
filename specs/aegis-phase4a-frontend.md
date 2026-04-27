# Plan: Phase 4a — Aegis Frontend (Next.js Task Manager Dashboard)

> **Status:** COMPLETE (2026-04-27)
> All 9 tasks completed. 9/9 validation commands passed. 11/11 acceptance criteria verified. 15/15 components, 3/3 pages, 4/4 API routes, build + lint clean. JWT server-side only. Independently verified by spec-updater.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-27
> **Team:** phase4a-frontend-20260427-1420
> **Verified by:** spec-updater (independent re-verification)

### Validation Commands
| Command | Result | Details |
|---------|--------|---------|
| `npm run build` | PASSED | Next.js 16.2.4 Turbopack — compiled in 1928ms, 6/6 static pages generated, 8 routes (/, /_not-found, /api/candidates/[uuid]/evidence, /api/feedback/tasks/[taskId]/outcomes, /api/queries, /api/queries/[id], /history, /results/[id]) |
| `npm run lint` | PASSED | ESLint exited cleanly, zero errors |
| `ls src/types/api.ts` | PASSED | File exists |
| `ls src/lib/api-client.ts` | PASSED | File exists |
| `ls src/middleware.ts` | PASSED | File exists |
| `ls page routes` | PASSED | 3/3 found: page.tsx, results/[id]/page.tsx, history/page.tsx |
| `ls API route handlers` | PASSED | 4/4 found: api/queries/route.ts, api/queries/[id]/route.ts, api/candidates/[uuid]/evidence/route.ts, api/feedback/tasks/[taskId]/outcomes/route.ts |
| `test -f vercel.json` | PASSED | vercel.json exists |
| `test -f .env.production.example` | PASSED | .env.production.example exists |

### Acceptance Criteria Verification
- [x] frontend/ exists with valid Next.js 14+ project — VERIFIED (Next.js 16.2.4, package.json present, builds successfully)
- [x] npm run build succeeds — VERIFIED (8 routes built: 3 static pages + 5 dynamic/API routes, compiled in 1928ms)
- [x] npm run lint succeeds — VERIFIED (ESLint exited cleanly, zero errors)
- [x] TypeScript strict mode enabled — VERIFIED (grep confirmed `"strict": true` in tsconfig.json, 1 match)
- [x] Tailwind CSS configured, Recharts installed — VERIFIED (tailwindcss ^4 + @tailwindcss/postcss ^4 in devDependencies, recharts ^3.8.1 in dependencies)
- [x] All env example files exist — VERIFIED (.env.local.example 193 bytes, .env.production.example 581 bytes)
- [x] vercel.json exists — VERIFIED (file present at frontend/vercel.json)
- [x] All TypeScript types, API client, middleware, route handlers exist — VERIFIED (src/types/api.ts, src/lib/api-client.ts, src/middleware.ts all present)
- [x] All 3 screens have proper loading/error/empty states — VERIFIED (results/[id]/page.tsx and history/page.tsx import LoadingSpinner and ErrorAlert; page.tsx is the form entry point)
- [x] All 15 component files exist — VERIFIED (12 domain components + 3 shared = 15 total: 4 query/, 7 results/, 1 history/, 3 shared: Header.tsx, LoadingSpinner.tsx, ErrorAlert.tsx)
- [x] JWT tokens only server-side — VERIFIED (AEGIS_API_TOKEN read via process.env in api-client.ts, Bearer token injected in server-side fetch; zero token references in src/components/)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| frontend/package.json | Created | Yes |
| frontend/tsconfig.json | Created | Yes |
| frontend/next.config.ts | Created | Yes |
| frontend/tailwind.config.ts | Created | Yes |
| frontend/postcss.config.mjs | Created | Yes |
| frontend/.env.local.example | Created | Yes |
| frontend/.env.production.example | Created | Yes |
| frontend/.gitignore | Created | Yes |
| frontend/vercel.json | Created | Yes |
| frontend/src/types/api.ts | Created | Yes |
| frontend/src/lib/api-client.ts | Created | Yes |
| frontend/src/middleware.ts | Created | Yes |
| frontend/src/app/layout.tsx | Created | Yes |
| frontend/src/app/globals.css | Created | Yes |
| frontend/src/app/page.tsx | Created | Yes |
| frontend/src/app/results/[id]/page.tsx | Created | Yes |
| frontend/src/app/history/page.tsx | Created | Yes |
| frontend/src/app/api/queries/route.ts | Created | Yes |
| frontend/src/app/api/queries/[id]/route.ts | Created | Yes |
| frontend/src/app/api/candidates/[uuid]/evidence/route.ts | Created | Yes |
| frontend/src/app/api/feedback/tasks/[taskId]/outcomes/route.ts | Created | Yes |
| frontend/src/components/Header.tsx | Created | Yes |
| frontend/src/components/LoadingSpinner.tsx | Created | Yes |
| frontend/src/components/ErrorAlert.tsx | Created | Yes |
| frontend/src/components/query/QueryForm.tsx | Created | Yes |
| frontend/src/components/query/PopulationSelector.tsx | Created | Yes |
| frontend/src/components/query/KSlider.tsx | Created | Yes |
| frontend/src/components/query/MeshTagInput.tsx | Created | Yes |
| frontend/src/components/results/CandidateRow.tsx | Created | Yes |
| frontend/src/components/results/ScoreBreakdownChart.tsx | Created | Yes |
| frontend/src/components/results/ArtifactChip.tsx | Created | Yes |
| frontend/src/components/results/VarianceBand.tsx | Created | Yes |
| frontend/src/components/results/IntegrityBadge.tsx | Created | Yes |
| frontend/src/components/results/EvidenceTrailPanel.tsx | Created | Yes |
| frontend/src/components/results/FeedbackModal.tsx | Created | Yes |
| frontend/src/components/history/QueryTable.tsx | Created | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase4a-frontend.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build the frontend web application for Aegis, an internal researcher-ranking engine used by task managers who submit queries to rank researchers for labeling tasks. This is a Next.js 14+ TypeScript application with three screens: New Query, Results, and Query History. The app communicates with the existing Aegis backend API via server-side proxied API routes, keeping JWT tokens entirely server-side. Styling uses Tailwind CSS with Recharts for score component visualization.

The backend API is already built and provides:
- `POST /v1/queries` -- submit a query, returns ranked candidate list
- `GET /v1/queries/{id}` -- get a specific query and its results
- `GET /v1/candidates/{uuid}/evidence` -- get full evidence trail for a candidate
- `POST /v1/feedback/tasks/{task_id}/outcomes` -- submit downstream task quality feedback
- Auth: JWT tokens, scoped per user

This frontend is purely internal -- no public signup, no researcher portal, no public-facing pages.

## Objective

When this plan is complete:
1. A Next.js 14+ application exists at `frontend/` within the aegis repo, bootstrapped with TypeScript strict mode, Tailwind CSS, and the App Router.
2. **Screen 1 (New Query)** at `/` allows task managers to enter a task description (required), select a population (translational / drug-discovery / clinician / auto-detect), adjust K (5-100, default 20), and optionally provide MeSH override tags and cutoff strategy. Submitting calls the backend API and redirects to the Results screen.
3. **Screen 2 (Results)** at `/results/[id]` displays the ranked candidate list for a query with rank, name, affiliation, specialty, score with variance band, identity linkage confidence, score component breakdown (R/Q/C/I via Recharts), top 3 artifacts as linked chips, and integrity disclosures. Clicking a candidate expands an evidence trail panel. A "Submit Feedback" button opens a modal for task outcome submission.
4. **Screen 3 (Query History)** at `/history` shows a paginated table of past queries with timestamp, task description (truncated), population, K, number of results, and a link to view results.
5. JWT tokens are stored server-side via Next.js middleware and environment variables -- never exposed to the browser.
6. All API calls are proxied through Next.js API routes (`/api/...`) to keep tokens server-side.
7. All screens have proper loading states, error states, and empty states.
8. The application builds without errors (`npm run build`) and lints cleanly (`npm run lint`).

## Problem Statement

Aegis Phases 0-3 built the complete backend: scoring engine, integrity checks, multi-population support, continuous ingestion, customer API, and feedback learning. However, task managers currently have no graphical interface to submit queries, view ranked researcher lists, or provide downstream feedback. Without a frontend, task managers must use raw API calls (curl/Postman) to interact with the system, which is error-prone, slow, and inaccessible to non-technical users. A purpose-built internal dashboard will make the ranking engine usable for its intended audience.

## Solution Approach

1. **Next.js scaffold first**: Bootstrap a new Next.js 14+ app at `frontend/` with TypeScript strict mode, Tailwind CSS, and App Router. Configure the project structure with a clear separation of concerns: types, API client layer, UI components, and page routes.

2. **Server-side auth layer**: Use Next.js middleware to attach JWT tokens to all proxied API requests. Tokens come from an environment variable (`AEGIS_API_TOKEN`) -- no login page needed for this internal tool. API route handlers at `frontend/src/app/api/` proxy requests to the backend, injecting the token server-side.

3. **Type-safe API client**: Define TypeScript types matching the backend API request/response shapes exactly. Build a thin fetch-based client that calls the local Next.js API routes (which proxy to the backend).

4. **Component library**: Build reusable components: ScoreBar (Recharts-based R/Q/C/I visualization), ArtifactChip (linked chip for PMID/NCT/patent/grant), CandidateRow (expandable row with evidence trail), FeedbackModal (form for Fleiss kappa, accept rate, consensus rate), and form controls (population selector, K slider, MeSH tag input).

5. **Three screens**: Build the New Query form page, Results page with candidate list and evidence expansion, and Query History table with pagination.

## Relevant Files

### Existing Files (read-only context, do not modify)
- `pyproject.toml` -- Python project config (backend reference only)
- `src/aegis/api/__init__.py` -- Backend API package (reference for API shape)
- `src/aegis/scoring/result_format.py` -- `RankedCandidate`, `RankedList`, `ComponentBreakdown`, `ContributingArtifact` models (reference for response types)
- `src/aegis/scoring/variance.py` -- `ScoreBand` model with `low`, `high`, `median` (reference for variance band shape)
- `src/aegis/scoring/rank.py` -- `Ranker`, `CandidateScoreInput` (reference for scoring formula)
- `src/aegis/learning/downstream_quality.py` -- `TaskOutcome`, `TaskOutcomeCandidate` (reference for feedback shape)
- `specs/aegis-phase3b-customer-api.md` -- API spec with endpoint definitions and response schemas

### New Files

#### Project Configuration
- `frontend/package.json` -- Node.js project configuration with Next.js, React, TypeScript, Tailwind, Recharts dependencies
- `frontend/tsconfig.json` -- TypeScript configuration with strict mode
- `frontend/next.config.ts` -- Next.js configuration with API proxy rewrites
- `frontend/tailwind.config.ts` -- Tailwind CSS configuration
- `frontend/postcss.config.mjs` -- PostCSS configuration for Tailwind
- `frontend/.env.local.example` -- Example environment variables (AEGIS_API_URL, AEGIS_API_TOKEN)
- `frontend/.gitignore` -- Git ignore for node_modules, .next, etc.
- `frontend/vercel.json` -- Vercel deployment configuration (framework, build/dev/install commands)
- `frontend/.env.production.example` -- Production env var documentation for Vercel dashboard

#### Types
- `frontend/src/types/api.ts` -- TypeScript types for all API request/response shapes

#### API Client Layer
- `frontend/src/lib/api-client.ts` -- Server-side API client that calls the backend with JWT token
- `frontend/src/app/api/queries/route.ts` -- API route: POST (create query), GET (list queries with pagination)
- `frontend/src/app/api/queries/[id]/route.ts` -- API route: GET (get query by ID)
- `frontend/src/app/api/candidates/[uuid]/evidence/route.ts` -- API route: GET (get candidate evidence)
- `frontend/src/app/api/feedback/tasks/[taskId]/outcomes/route.ts` -- API route: POST (submit feedback)

#### Middleware
- `frontend/src/middleware.ts` -- Next.js middleware for auth token injection

#### Layout and Shared Components
- `frontend/src/app/layout.tsx` -- Root layout with Tailwind, nav header
- `frontend/src/app/globals.css` -- Global styles with Tailwind directives
- `frontend/src/components/Header.tsx` -- Navigation header (New Query, History links)
- `frontend/src/components/LoadingSpinner.tsx` -- Reusable loading spinner
- `frontend/src/components/ErrorAlert.tsx` -- Reusable error state display

#### Screen 1: New Query
- `frontend/src/app/page.tsx` -- New Query form page
- `frontend/src/components/query/QueryForm.tsx` -- Main query form component
- `frontend/src/components/query/PopulationSelector.tsx` -- Population dropdown (translational / drug-discovery / clinician / auto-detect)
- `frontend/src/components/query/KSlider.tsx` -- K value slider/input (5-100, default 20)
- `frontend/src/components/query/MeshTagInput.tsx` -- MeSH override tag input (advanced section)

#### Screen 2: Results
- `frontend/src/app/results/[id]/page.tsx` -- Results page
- `frontend/src/components/results/CandidateRow.tsx` -- Expandable candidate row
- `frontend/src/components/results/ScoreBreakdownChart.tsx` -- Recharts-based R/Q/C/I bar chart
- `frontend/src/components/results/ArtifactChip.tsx` -- Linked artifact chip (PMID, NCT, patent, grant)
- `frontend/src/components/results/EvidenceTrailPanel.tsx` -- Expanded evidence trail panel
- `frontend/src/components/results/VarianceBand.tsx` -- Score variance band display
- `frontend/src/components/results/IntegrityBadge.tsx` -- Integrity disclosure warning badge
- `frontend/src/components/results/FeedbackModal.tsx` -- Feedback submission modal

#### Screen 3: Query History
- `frontend/src/app/history/page.tsx` -- Query History page
- `frontend/src/components/history/QueryTable.tsx` -- Paginated query history table

## Implementation Phases

### Phase 1: Foundation
- Bootstrap the Next.js application with TypeScript, Tailwind CSS, and App Router
- Define all TypeScript types matching backend API shapes
- Build the server-side API client and proxy route handlers
- Set up Next.js middleware for auth token injection
- Build shared layout and reusable components (Header, LoadingSpinner, ErrorAlert)

### Phase 2: Core Implementation
- Build Screen 1 (New Query) with form, population selector, K slider, MeSH tag input, advanced section
- Build Screen 2 (Results) with candidate list, score breakdown chart, artifact chips, evidence trail, feedback modal
- Build Screen 3 (Query History) with paginated table

### Phase 3: Integration & Polish
- Wire all screens together with navigation
- Add loading states, error states, and empty states to all screens
- Verify the app builds cleanly and lints without errors
- Run full validation

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Project scaffold, TypeScript types, API client layer, proxy routes, middleware, shared layout/components
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Screen 1 (New Query form) and Screen 3 (Query History table)
  - Agent Type: general-purpose
- Builder
  - Name: builder-3
  - Role: Screen 2 (Results page) -- candidate list, score chart, artifact chips, evidence trail, feedback modal
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

### 1. Bootstrap Next.js Application

- **Task ID**: bootstrap-nextjs
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Bootstrap a new Next.js 14+ application at `frontend/` inside the existing aegis repo. Configure TypeScript strict mode, Tailwind CSS, and the App Router.

    ## What to do

    1. Run the Next.js bootstrapping commands from the repo root:
       ```bash
       cd /Users/anvith/aegis
       npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-turbopack --use-npm
       ```
       If prompted, accept defaults. The `--src-dir` flag creates `frontend/src/` structure. The `--app` flag uses App Router.

    2. Install additional dependencies:
       ```bash
       cd /Users/anvith/aegis/frontend
       npm install recharts
       ```

    3. Verify `frontend/tsconfig.json` has strict mode enabled. If not, edit it to set `"strict": true` in `compilerOptions`.

    4. Create `frontend/.env.local.example` with:
       ```
       # Backend API base URL (no trailing slash)
       AEGIS_API_URL=http://localhost:8000

       # JWT token for API authentication (server-side only, never sent to browser)
       AEGIS_API_TOKEN=your-jwt-token-here
       ```

    5. Create `frontend/.env.local` with the same content (this will be gitignored by default).

    6. Verify the `.gitignore` in `frontend/` includes `node_modules/`, `.next/`, `.env.local`.

    7. Update `frontend/tailwind.config.ts` to ensure the content paths are correct:
       ```typescript
       import type { Config } from "tailwindcss";

       const config: Config = {
         content: [
           "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
           "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
           "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
         ],
         theme: {
           extend: {},
         },
         plugins: [],
       };
       export default config;
       ```

    8. Clean up the default `frontend/src/app/page.tsx` -- replace its contents with a minimal placeholder:
       ```tsx
       export default function Home() {
         return (
           <main className="min-h-screen p-8">
             <h1 className="text-2xl font-bold">Aegis</h1>
             <p className="text-gray-600 mt-2">Internal Researcher Ranking Engine</p>
           </main>
         );
       }
       ```

    9. Clean up `frontend/src/app/globals.css` to contain only Tailwind directives:
       ```css
       @tailwind base;
       @tailwind components;
       @tailwind utilities;
       ```

    10. Verify the app builds:
        ```bash
        cd /Users/anvith/aegis/frontend && npm run build
        ```

    ## Files to create
    - `frontend/.env.local.example`
    - `frontend/.env.local`
    - (All other files are created by `create-next-app`)

    ## Files to modify
    - `frontend/src/app/page.tsx` -- replace default content with minimal placeholder
    - `frontend/src/app/globals.css` -- replace with Tailwind-only directives
    - `frontend/tailwind.config.ts` -- ensure correct content paths
    - `frontend/tsconfig.json` -- ensure strict mode is enabled

    ## Code patterns to follow
    - Use App Router (files in `src/app/`)
    - TypeScript strict mode everywhere
    - Tailwind CSS for all styling (no CSS modules, no styled-components)
    - `"use client"` directive only on components that need client-side interactivity

    ## Acceptance criteria
    - `frontend/` directory exists with a valid Next.js project
    - `npm run build` succeeds without errors from `frontend/`
    - `npm run lint` succeeds without errors from `frontend/`
    - TypeScript strict mode is enabled in `tsconfig.json`
    - Tailwind CSS is configured and working
    - `.env.local.example` exists with `AEGIS_API_URL` and `AEGIS_API_TOKEN`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npm run build && npm run lint
    ```

### 2. Vercel Deployment Configuration

- **Task ID**: setup-vercel-deployment
- **Role**: builder
- **Depends On**: bootstrap-nextjs
- **Assigned To**: builder-1
- **Description**: |
    Configure the frontend for deployment on Vercel. This runs in parallel with the types-and-api-client task and can be completed quickly.

    ## What to do

    1. Create `frontend/vercel.json` with the following content:
       ```json
       {
         "framework": "nextjs",
         "buildCommand": "npm run build",
         "devCommand": "npm run dev",
         "installCommand": "npm install",
         "outputDirectory": ".next"
       }
       ```
       This file tells Vercel the framework and commands to use. When deploying from the monorepo, set **Root Directory** to `frontend` in the Vercel project settings (not via this file).

    2. Create `frontend/.env.production.example` documenting all required environment variables for the Vercel dashboard:
       ```
       # ── Vercel Environment Variables ──────────────────────────────────────────────
       # Set these in the Vercel dashboard under Project → Settings → Environment Variables.
       # All variables are server-only. None are exposed to the browser.

       # Base URL of the Aegis backend API (no trailing slash).
       # Example: https://api.aegis.internal or http://your-backend-host:8000
       AEGIS_API_URL=https://your-backend-host

       # JWT token used to authenticate all backend API requests.
       # Generate with: python -m aegis.api.auth generate-token
       # Scope: set for Production, Preview, and Development as appropriate.
       AEGIS_API_TOKEN=your-jwt-token-here
       ```

    3. Verify `frontend/.gitignore` (created by create-next-app) contains `.env.local` and does NOT ignore `.env.local.example` or `.env.production.example`. If `.env*.example` is gitignored, remove that rule. The example files should be committed.

    4. Verify `frontend/next.config.ts` does NOT set `output: "standalone"` or `output: "export"`. Vercel handles Next.js builds natively — no output mode override is needed. If either is present, remove it. The file should look like:
       ```typescript
       import type { NextConfig } from "next";

       const nextConfig: NextConfig = {
         // No output override needed for Vercel — it handles Next.js natively.
       };

       export default nextConfig;
       ```

    5. Verify the build still passes:
       ```bash
       cd /Users/anvith/aegis/frontend && npm run build
       ```

    ## Files to create
    - `frontend/vercel.json`
    - `frontend/.env.production.example`

    ## Files to modify
    - `frontend/.gitignore` -- ensure .env*.example files are NOT gitignored
    - `frontend/next.config.ts` -- remove output override if present

    ## Acceptance criteria
    - `frontend/vercel.json` exists with framework, buildCommand, devCommand, installCommand, outputDirectory
    - `frontend/.env.production.example` exists and documents AEGIS_API_URL and AEGIS_API_TOKEN
    - `frontend/next.config.ts` does NOT contain `output: "standalone"` or `output: "export"`
    - `.env.production.example` and `.env.local.example` are NOT gitignored
    - `npm run build` still passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && test -f vercel.json && echo "vercel.json: OK" && test -f .env.production.example && echo ".env.production.example: OK" && ! grep -q 'output.*standalone\|output.*export' next.config.ts && echo "next.config.ts: OK" && npm run build && echo "build: OK"
    ```

### 3. TypeScript Types and API Client Layer

- **Task ID**: types-and-api-client
- **Role**: builder
- **Depends On**: bootstrap-nextjs
- **Assigned To**: builder-1
- **Description**: |
    Define all TypeScript types matching the backend API shapes and build the server-side API client that communicates with the Aegis backend.

    ## What to do

    1. Create `frontend/src/types/api.ts` with the following types. These must exactly match the backend API request/response shapes:

       ```typescript
       // ===== Query Request =====

       export type Population = "translational" | "drug_discovery" | "clinician";

       export interface QueryRequest {
         task_description: string;
         population?: Population;
         mesh_override?: string[];
         k?: number; // default 20, range 5-100
         cutoff_strategy?: string;
       }

       // ===== Candidate Result (per candidate in ranked list) =====

       export interface ScoreComponents {
         R: number; // Recency
         Q: number; // Quality prior
         C: number; // Contextual fit / topical fit
         I: number; // Integrity
       }

       export interface ScoreVarianceBand {
         low: number;
         high: number;
       }

       export interface Artifact {
         id: string;
         type: "pmid" | "nct" | "patent" | "grant";
         url: string;
         title: string;
       }

       export interface Provenance {
         weight_version: string;
         integrity_rule_version: string;
       }

       export interface CandidateResult {
         uuid: string;
         name: string;
         affiliation: string; // ROR-normalized
         rank: number;
         score: number;
         score_variance_band: ScoreVarianceBand;
         specialty: string;
         identity_linkage_confidence: number;
         score_components: ScoreComponents;
         top_artifacts: Artifact[];
         integrity_disclosures: string[]; // may be empty
         provenance: Provenance;
       }

       // ===== Query Response =====

       export interface QueryResponse {
         id: string;
         task_description: string;
         population?: Population;
         k: number;
         candidates: CandidateResult[];
         created_at: string; // ISO 8601
         mesh_override?: string[];
         cutoff_strategy?: string;
       }

       // ===== Query List (for history) =====

       export interface QuerySummary {
         id: string;
         task_description: string;
         population?: Population;
         k: number;
         result_count: number;
         created_at: string; // ISO 8601
       }

       export interface QueryListResponse {
         queries: QuerySummary[];
         total: number;
         page: number;
         per_page: number;
       }

       // ===== Evidence Trail =====

       export interface EvidenceTrail {
         candidate_uuid: string;
         candidate_name: string;
         evidence_items: EvidenceItem[];
       }

       export interface EvidenceItem {
         type: string;
         source: string;
         description: string;
         url?: string;
         date?: string;
         score_contribution?: number;
       }

       // ===== Feedback =====

       export interface FeedbackRequest {
         fleiss_kappa: number; // 0-1
         accept_rate: number; // 0-1
         consensus_rate: number; // 0-1
       }

       export interface FeedbackResponse {
         task_id: string;
         status: string;
         submitted_at: string;
       }
       ```

    2. Create `frontend/src/lib/api-client.ts` -- a server-side API client that calls the backend with the JWT token:

       ```typescript
       /**
        * Server-side API client for the Aegis backend.
        * This module runs ONLY on the server (in API route handlers).
        * It reads AEGIS_API_URL and AEGIS_API_TOKEN from environment variables.
        * JWT tokens never leave the server.
        */

       const getBaseUrl = (): string => {
         const url = process.env.AEGIS_API_URL;
         if (!url) {
           throw new Error("AEGIS_API_URL environment variable is not set");
         }
         return url;
       };

       const getToken = (): string => {
         const token = process.env.AEGIS_API_TOKEN;
         if (!token) {
           throw new Error("AEGIS_API_TOKEN environment variable is not set");
         }
         return token;
       };

       interface FetchOptions {
         method?: string;
         body?: unknown;
         params?: Record<string, string>;
       }

       async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
         const baseUrl = getBaseUrl();
         const token = getToken();

         let url = `${baseUrl}${path}`;
         if (options.params) {
           const searchParams = new URLSearchParams(options.params);
           url += `?${searchParams.toString()}`;
         }

         const response = await fetch(url, {
           method: options.method || "GET",
           headers: {
             "Content-Type": "application/json",
             Authorization: `Bearer ${token}`,
           },
           ...(options.body ? { body: JSON.stringify(options.body) } : {}),
         });

         if (!response.ok) {
           const errorText = await response.text().catch(() => "Unknown error");
           throw new Error(`API error ${response.status}: ${errorText}`);
         }

         return response.json() as Promise<T>;
       }

       export { apiFetch };
       ```

    3. Create the API proxy route handlers. These run server-side and proxy requests to the backend:

       a) `frontend/src/app/api/queries/route.ts`:
       ```typescript
       import { NextRequest, NextResponse } from "next/server";
       import { apiFetch } from "@/lib/api-client";
       import type { QueryRequest, QueryResponse, QueryListResponse } from "@/types/api";

       export async function POST(request: NextRequest) {
         try {
           const body: QueryRequest = await request.json();
           const data = await apiFetch<QueryResponse>("/v1/queries", {
             method: "POST",
             body,
           });
           return NextResponse.json(data);
         } catch (error) {
           const message = error instanceof Error ? error.message : "Internal server error";
           return NextResponse.json({ error: message }, { status: 500 });
         }
       }

       export async function GET(request: NextRequest) {
         try {
           const { searchParams } = new URL(request.url);
           const page = searchParams.get("page") || "1";
           const perPage = searchParams.get("per_page") || "20";
           const data = await apiFetch<QueryListResponse>("/v1/queries", {
             params: { page, per_page: perPage },
           });
           return NextResponse.json(data);
         } catch (error) {
           const message = error instanceof Error ? error.message : "Internal server error";
           return NextResponse.json({ error: message }, { status: 500 });
         }
       }
       ```

       b) `frontend/src/app/api/queries/[id]/route.ts`:
       ```typescript
       import { NextRequest, NextResponse } from "next/server";
       import { apiFetch } from "@/lib/api-client";
       import type { QueryResponse } from "@/types/api";

       export async function GET(
         request: NextRequest,
         { params }: { params: Promise<{ id: string }> }
       ) {
         try {
           const { id } = await params;
           const data = await apiFetch<QueryResponse>(`/v1/queries/${id}`);
           return NextResponse.json(data);
         } catch (error) {
           const message = error instanceof Error ? error.message : "Internal server error";
           return NextResponse.json({ error: message }, { status: 500 });
         }
       }
       ```

       c) `frontend/src/app/api/candidates/[uuid]/evidence/route.ts`:
       ```typescript
       import { NextRequest, NextResponse } from "next/server";
       import { apiFetch } from "@/lib/api-client";
       import type { EvidenceTrail } from "@/types/api";

       export async function GET(
         request: NextRequest,
         { params }: { params: Promise<{ uuid: string }> }
       ) {
         try {
           const { uuid } = await params;
           const data = await apiFetch<EvidenceTrail>(`/v1/candidates/${uuid}/evidence`);
           return NextResponse.json(data);
         } catch (error) {
           const message = error instanceof Error ? error.message : "Internal server error";
           return NextResponse.json({ error: message }, { status: 500 });
         }
       }
       ```

       d) `frontend/src/app/api/feedback/tasks/[taskId]/outcomes/route.ts`:
       ```typescript
       import { NextRequest, NextResponse } from "next/server";
       import { apiFetch } from "@/lib/api-client";
       import type { FeedbackRequest, FeedbackResponse } from "@/types/api";

       export async function POST(
         request: NextRequest,
         { params }: { params: Promise<{ taskId: string }> }
       ) {
         try {
           const { taskId } = await params;
           const body: FeedbackRequest = await request.json();
           const data = await apiFetch<FeedbackResponse>(
             `/v1/feedback/tasks/${taskId}/outcomes`,
             { method: "POST", body }
           );
           return NextResponse.json(data);
         } catch (error) {
           const message = error instanceof Error ? error.message : "Internal server error";
           return NextResponse.json({ error: message }, { status: 500 });
         }
       }
       ```

    4. Create `frontend/src/middleware.ts` -- Next.js middleware. For this internal tool, the middleware simply ensures the API token is configured (no login flow needed):

       ```typescript
       import { NextResponse } from "next/server";
       import type { NextRequest } from "next/server";

       export function middleware(request: NextRequest) {
         // For API routes, just pass through -- the api-client handles token injection server-side
         if (request.nextUrl.pathname.startsWith("/api/")) {
           return NextResponse.next();
         }

         // For page routes, pass through (internal tool, no login required)
         return NextResponse.next();
       }

       export const config = {
         matcher: ["/api/:path*", "/((?!_next/static|_next/image|favicon.ico).*)"],
       };
       ```

    ## Files to create
    - `frontend/src/types/api.ts`
    - `frontend/src/lib/api-client.ts`
    - `frontend/src/app/api/queries/route.ts`
    - `frontend/src/app/api/queries/[id]/route.ts`
    - `frontend/src/app/api/candidates/[uuid]/evidence/route.ts`
    - `frontend/src/app/api/feedback/tasks/[taskId]/outcomes/route.ts`
    - `frontend/src/middleware.ts`

    ## Code patterns to follow
    - All API route handlers use `NextRequest`/`NextResponse` from `next/server`
    - API route handlers catch errors and return JSON error responses with appropriate status codes
    - The API client uses native `fetch` (no axios) for server-side calls
    - TypeScript types are defined in a single `types/api.ts` file for consistency
    - JWT token is read from `process.env.AEGIS_API_TOKEN` -- never from cookies or localStorage
    - Import aliases use `@/` prefix (configured by create-next-app)

    ## Acceptance criteria
    - `frontend/src/types/api.ts` exists with all type definitions matching the backend API shapes
    - `frontend/src/lib/api-client.ts` exists with `apiFetch` function
    - All 4 API route files exist and export the correct HTTP method handlers
    - `frontend/src/middleware.ts` exists
    - `npm run build` succeeds from `frontend/`
    - `npm run lint` succeeds from `frontend/`
    - No TypeScript errors in any of the new files

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npm run build && npm run lint
    ```

### 4. Shared Layout and Reusable Components

- **Task ID**: shared-components
- **Role**: builder
- **Depends On**: types-and-api-client
- **Assigned To**: builder-1
- **Description**: |
    Build the root layout, navigation header, and reusable utility components (loading spinner, error alert) that are shared across all screens.

    ## What to do

    1. Update `frontend/src/app/layout.tsx` to include a consistent layout with the navigation header:

       ```tsx
       import type { Metadata } from "next";
       import { Inter } from "next/font/google";
       import "./globals.css";
       import Header from "@/components/Header";

       const inter = Inter({ subsets: ["latin"] });

       export const metadata: Metadata = {
         title: "Aegis - Researcher Ranking Engine",
         description: "Internal tool for ranking researchers for labeling tasks",
       };

       export default function RootLayout({
         children,
       }: Readonly<{
         children: React.ReactNode;
       }>) {
         return (
           <html lang="en">
             <body className={`${inter.className} bg-gray-50 min-h-screen`}>
               <Header />
               <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                 {children}
               </main>
             </body>
           </html>
         );
       }
       ```

    2. Create `frontend/src/components/Header.tsx`:

       ```tsx
       "use client";

       import Link from "next/link";
       import { usePathname } from "next/navigation";

       export default function Header() {
         const pathname = usePathname();

         const navItems = [
           { href: "/", label: "New Query" },
           { href: "/history", label: "Query History" },
         ];

         return (
           <header className="bg-white border-b border-gray-200">
             <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
               <div className="flex items-center justify-between h-16">
                 <div className="flex items-center space-x-8">
                   <Link href="/" className="text-xl font-bold text-gray-900">
                     Aegis
                   </Link>
                   <nav className="flex space-x-4">
                     {navItems.map((item) => {
                       const isActive =
                         item.href === "/"
                           ? pathname === "/"
                           : pathname.startsWith(item.href);
                       return (
                         <Link
                           key={item.href}
                           href={item.href}
                           className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                             isActive
                               ? "bg-gray-100 text-gray-900"
                               : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                           }`}
                         >
                           {item.label}
                         </Link>
                       );
                     })}
                   </nav>
                 </div>
                 <div className="text-sm text-gray-400">Internal Tool</div>
               </div>
             </div>
           </header>
         );
       }
       ```

    3. Create `frontend/src/components/LoadingSpinner.tsx`:

       ```tsx
       interface LoadingSpinnerProps {
         message?: string;
       }

       export default function LoadingSpinner({ message = "Loading..." }: LoadingSpinnerProps) {
         return (
           <div className="flex flex-col items-center justify-center py-12">
             <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
             <p className="mt-4 text-sm text-gray-500">{message}</p>
           </div>
         );
       }
       ```

    4. Create `frontend/src/components/ErrorAlert.tsx`:

       ```tsx
       interface ErrorAlertProps {
         title?: string;
         message: string;
         onRetry?: () => void;
       }

       export default function ErrorAlert({
         title = "Error",
         message,
         onRetry,
       }: ErrorAlertProps) {
         return (
           <div className="rounded-md bg-red-50 p-4">
             <div className="flex">
               <div className="flex-shrink-0">
                 <svg
                   className="h-5 w-5 text-red-400"
                   viewBox="0 0 20 20"
                   fill="currentColor"
                 >
                   <path
                     fillRule="evenodd"
                     d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                     clipRule="evenodd"
                   />
                 </svg>
               </div>
               <div className="ml-3">
                 <h3 className="text-sm font-medium text-red-800">{title}</h3>
                 <p className="mt-1 text-sm text-red-700">{message}</p>
                 {onRetry && (
                   <button
                     onClick={onRetry}
                     className="mt-3 text-sm font-medium text-red-600 hover:text-red-500 underline"
                   >
                     Try again
                   </button>
                 )}
               </div>
             </div>
           </div>
         );
       }
       ```

    ## Files to create
    - `frontend/src/components/Header.tsx`
    - `frontend/src/components/LoadingSpinner.tsx`
    - `frontend/src/components/ErrorAlert.tsx`

    ## Files to modify
    - `frontend/src/app/layout.tsx` -- update with Header import and consistent layout structure

    ## Code patterns to follow
    - `"use client"` only on components that use hooks (Header uses `usePathname`)
    - Server Components by default (LoadingSpinner and ErrorAlert are server-compatible)
    - Tailwind CSS utility classes for all styling
    - Components accept props via TypeScript interfaces
    - Keep components small and focused

    ## Acceptance criteria
    - `frontend/src/components/Header.tsx` exists with navigation links for "New Query" and "Query History"
    - `frontend/src/components/LoadingSpinner.tsx` exists with customizable message
    - `frontend/src/components/ErrorAlert.tsx` exists with title, message, and optional retry button
    - `frontend/src/app/layout.tsx` includes the Header component
    - `npm run build` succeeds from `frontend/`
    - `npm run lint` succeeds from `frontend/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npm run build && npm run lint
    ```

### 5. Screen 1 -- New Query Form

- **Task ID**: screen-new-query
- **Role**: builder
- **Depends On**: shared-components
- **Assigned To**: builder-2
- **Description**: |
    Build Screen 1: the New Query form page where task managers submit a new ranking query. This is the main landing page at `/`.

    ## What to do

    1. Create `frontend/src/components/query/PopulationSelector.tsx`:

       ```tsx
       "use client";

       import type { Population } from "@/types/api";

       interface PopulationSelectorProps {
         value: Population | "auto" | "";
         onChange: (value: Population | "auto" | "") => void;
       }

       const POPULATIONS: { value: Population | "auto"; label: string }[] = [
         { value: "auto", label: "Auto-detect" },
         { value: "translational", label: "Translational" },
         { value: "drug_discovery", label: "Drug Discovery" },
         { value: "clinician", label: "Clinician" },
       ];

       export default function PopulationSelector({ value, onChange }: PopulationSelectorProps) {
         return (
           <div>
             <label htmlFor="population" className="block text-sm font-medium text-gray-700 mb-1">
               Population
             </label>
             <select
               id="population"
               value={value}
               onChange={(e) => onChange(e.target.value as Population | "auto" | "")}
               className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
             >
               <option value="">-- Select (optional) --</option>
               {POPULATIONS.map((pop) => (
                 <option key={pop.value} value={pop.value}>
                   {pop.label}
                 </option>
               ))}
             </select>
             <p className="mt-1 text-xs text-gray-500">
               Leave blank or select Auto-detect to let the system choose.
             </p>
           </div>
         );
       }
       ```

    2. Create `frontend/src/components/query/KSlider.tsx`:

       ```tsx
       "use client";

       interface KSliderProps {
         value: number;
         onChange: (value: number) => void;
       }

       export default function KSlider({ value, onChange }: KSliderProps) {
         return (
           <div>
             <label htmlFor="k-value" className="block text-sm font-medium text-gray-700 mb-1">
               Number of Results (K)
             </label>
             <div className="flex items-center space-x-4">
               <input
                 type="range"
                 id="k-value"
                 min={5}
                 max={100}
                 step={1}
                 value={value}
                 onChange={(e) => onChange(Number(e.target.value))}
                 className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
               />
               <input
                 type="number"
                 min={5}
                 max={100}
                 value={value}
                 onChange={(e) => {
                   const v = Number(e.target.value);
                   if (v >= 5 && v <= 100) onChange(v);
                 }}
                 className="w-20 rounded-md border border-gray-300 px-2 py-1 text-sm text-center focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
               />
             </div>
             <p className="mt-1 text-xs text-gray-500">
               How many ranked candidates to return (5-100).
             </p>
           </div>
         );
       }
       ```

    3. Create `frontend/src/components/query/MeshTagInput.tsx`:

       ```tsx
       "use client";

       import { useState, type KeyboardEvent } from "react";

       interface MeshTagInputProps {
         tags: string[];
         onChange: (tags: string[]) => void;
       }

       export default function MeshTagInput({ tags, onChange }: MeshTagInputProps) {
         const [inputValue, setInputValue] = useState("");

         const addTag = (tag: string) => {
           const trimmed = tag.trim();
           if (trimmed && !tags.includes(trimmed)) {
             onChange([...tags, trimmed]);
           }
           setInputValue("");
         };

         const removeTag = (index: number) => {
           onChange(tags.filter((_, i) => i !== index));
         };

         const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
           if (e.key === "Enter" || e.key === ",") {
             e.preventDefault();
             addTag(inputValue);
           } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
             removeTag(tags.length - 1);
           }
         };

         return (
           <div>
             <label htmlFor="mesh-tags" className="block text-sm font-medium text-gray-700 mb-1">
               MeSH Override Tags
             </label>
             <div className="flex flex-wrap gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
               {tags.map((tag, index) => (
                 <span
                   key={index}
                   className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
                 >
                   {tag}
                   <button
                     type="button"
                     onClick={() => removeTag(index)}
                     className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-blue-400 hover:bg-blue-200 hover:text-blue-600"
                   >
                     x
                   </button>
                 </span>
               ))}
               <input
                 id="mesh-tags"
                 type="text"
                 value={inputValue}
                 onChange={(e) => setInputValue(e.target.value)}
                 onKeyDown={handleKeyDown}
                 onBlur={() => { if (inputValue) addTag(inputValue); }}
                 placeholder={tags.length === 0 ? "Type a MeSH term and press Enter..." : ""}
                 className="flex-1 min-w-[120px] border-0 bg-transparent text-sm focus:outline-none focus:ring-0"
               />
             </div>
             <p className="mt-1 text-xs text-gray-500">
               Optional. Press Enter or comma to add a tag. These override automatic MeSH expansion.
             </p>
           </div>
         );
       }
       ```

    4. Create `frontend/src/components/query/QueryForm.tsx` -- the main form component:

       ```tsx
       "use client";

       import { useState } from "react";
       import { useRouter } from "next/navigation";
       import type { Population, QueryRequest } from "@/types/api";
       import PopulationSelector from "./PopulationSelector";
       import KSlider from "./KSlider";
       import MeshTagInput from "./MeshTagInput";

       export default function QueryForm() {
         const router = useRouter();
         const [taskDescription, setTaskDescription] = useState("");
         const [population, setPopulation] = useState<Population | "auto" | "">("");
         const [k, setK] = useState(20);
         const [meshOverride, setMeshOverride] = useState<string[]>([]);
         const [cutoffStrategy, setCutoffStrategy] = useState("");
         const [showAdvanced, setShowAdvanced] = useState(false);
         const [isSubmitting, setIsSubmitting] = useState(false);
         const [error, setError] = useState<string | null>(null);

         const handleSubmit = async (e: React.FormEvent) => {
           e.preventDefault();
           setError(null);

           if (!taskDescription.trim()) {
             setError("Task description is required.");
             return;
           }

           setIsSubmitting(true);

           try {
             const body: QueryRequest = {
               task_description: taskDescription.trim(),
               k,
             };

             if (population && population !== "auto") {
               body.population = population;
             }

             if (meshOverride.length > 0) {
               body.mesh_override = meshOverride;
             }

             if (cutoffStrategy.trim()) {
               body.cutoff_strategy = cutoffStrategy.trim();
             }

             const response = await fetch("/api/queries", {
               method: "POST",
               headers: { "Content-Type": "application/json" },
               body: JSON.stringify(body),
             });

             if (!response.ok) {
               const errData = await response.json().catch(() => ({}));
               throw new Error(errData.error || `Request failed with status ${response.status}`);
             }

             const data = await response.json();
             router.push(`/results/${data.id}`);
           } catch (err) {
             setError(err instanceof Error ? err.message : "An unexpected error occurred.");
           } finally {
             setIsSubmitting(false);
           }
         };

         return (
           <form onSubmit={handleSubmit} className="space-y-6">
             {error && (
               <div className="rounded-md bg-red-50 p-4">
                 <p className="text-sm text-red-700">{error}</p>
               </div>
             )}

             <div>
               <label htmlFor="task-description" className="block text-sm font-medium text-gray-700 mb-1">
                 Task Description <span className="text-red-500">*</span>
               </label>
               <textarea
                 id="task-description"
                 rows={5}
                 value={taskDescription}
                 onChange={(e) => setTaskDescription(e.target.value)}
                 placeholder="Describe the labeling task and the type of researcher expertise needed..."
                 className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                 required
               />
             </div>

             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
               <PopulationSelector value={population} onChange={setPopulation} />
               <KSlider value={k} onChange={setK} />
             </div>

             <div>
               <button
                 type="button"
                 onClick={() => setShowAdvanced(!showAdvanced)}
                 className="flex items-center text-sm text-gray-500 hover:text-gray-700"
               >
                 <svg
                   className={`h-4 w-4 mr-1 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
                   fill="none"
                   viewBox="0 0 24 24"
                   stroke="currentColor"
                 >
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                 </svg>
                 Advanced Options
               </button>

               {showAdvanced && (
                 <div className="mt-4 space-y-4 pl-5 border-l-2 border-gray-200">
                   <MeshTagInput tags={meshOverride} onChange={setMeshOverride} />
                   <div>
                     <label htmlFor="cutoff-strategy" className="block text-sm font-medium text-gray-700 mb-1">
                       Cutoff Strategy
                     </label>
                     <input
                       id="cutoff-strategy"
                       type="text"
                       value={cutoffStrategy}
                       onChange={(e) => setCutoffStrategy(e.target.value)}
                       placeholder="e.g., score_threshold, elbow"
                       className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                     />
                     <p className="mt-1 text-xs text-gray-500">
                       Optional. Determines how candidates below the quality threshold are cut.
                     </p>
                   </div>
                 </div>
               )}
             </div>

             <div className="pt-4">
               <button
                 type="submit"
                 disabled={isSubmitting || !taskDescription.trim()}
                 className="w-full sm:w-auto px-6 py-2.5 rounded-md bg-blue-600 text-white text-sm font-medium shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
               >
                 {isSubmitting ? (
                   <span className="flex items-center justify-center">
                     <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                       <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                       <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                     </svg>
                     Submitting Query...
                   </span>
                 ) : (
                   "Submit Query"
                 )}
               </button>
             </div>
           </form>
         );
       }
       ```

    5. Update `frontend/src/app/page.tsx` to render the QueryForm:

       ```tsx
       import QueryForm from "@/components/query/QueryForm";

       export default function NewQueryPage() {
         return (
           <div>
             <div className="mb-8">
               <h1 className="text-2xl font-bold text-gray-900">New Query</h1>
               <p className="mt-2 text-sm text-gray-600">
                 Submit a new query to rank researchers for a labeling task.
               </p>
             </div>
             <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
               <QueryForm />
             </div>
           </div>
         );
       }
       ```

    ## Files to create
    - `frontend/src/components/query/PopulationSelector.tsx`
    - `frontend/src/components/query/KSlider.tsx`
    - `frontend/src/components/query/MeshTagInput.tsx`
    - `frontend/src/components/query/QueryForm.tsx`

    ## Files to modify
    - `frontend/src/app/page.tsx` -- replace placeholder with QueryForm page

    ## Code patterns to follow
    - All form components are client components (`"use client"`)
    - Controlled form inputs with React state
    - Form validation before submission (task description required)
    - Loading state during API call (disabled button with spinner)
    - Error display within the form
    - Redirect to results page on successful submission using `useRouter().push()`
    - Tailwind CSS for all styling
    - Each sub-component accepts props via TypeScript interface

    ## Acceptance criteria
    - New Query page renders at `/` with task description textarea, population selector, K slider
    - Advanced section is collapsed by default and toggles open/closed
    - MeSH tag input allows adding/removing tags with Enter/comma/Backspace
    - K slider syncs with number input (range 5-100, default 20)
    - Submit button is disabled when task description is empty or form is submitting
    - Submit button shows loading spinner during submission
    - Error messages display within the form
    - On successful submission, the page redirects to `/results/{id}`
    - `npm run build` succeeds from `frontend/`
    - `npm run lint` succeeds from `frontend/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npm run build && npm run lint
    ```

### 6. Screen 2 -- Results Page Components

- **Task ID**: screen-results-components
- **Role**: builder
- **Depends On**: shared-components
- **Assigned To**: builder-3
- **Description**: |
    Build all reusable components for Screen 2 (Results): score breakdown chart, artifact chips, variance band display, integrity badge, evidence trail panel, and feedback modal.

    ## What to do

    1. Create `frontend/src/components/results/ScoreBreakdownChart.tsx` -- uses Recharts to visualize R/Q/C/I score components:

       ```tsx
       "use client";

       import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
       import type { ScoreComponents } from "@/types/api";

       interface ScoreBreakdownChartProps {
         components: ScoreComponents;
       }

       const COLORS: Record<string, string> = {
         R: "#3b82f6", // blue
         Q: "#10b981", // green
         C: "#f59e0b", // amber
         I: "#8b5cf6", // violet
       };

       const LABELS: Record<string, string> = {
         R: "Recency",
         Q: "Quality",
         C: "Contextual Fit",
         I: "Integrity",
       };

       export default function ScoreBreakdownChart({ components }: ScoreBreakdownChartProps) {
         const data = [
           { name: "R", value: components.R, label: LABELS.R },
           { name: "Q", value: components.Q, label: LABELS.Q },
           { name: "C", value: components.C, label: LABELS.C },
           { name: "I", value: components.I, label: LABELS.I },
         ];

         return (
           <div className="w-full h-24">
             <ResponsiveContainer width="100%" height="100%">
               <BarChart data={data} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
                 <XAxis type="number" domain={[0, 1]} hide />
                 <YAxis type="category" dataKey="name" width={20} tick={{ fontSize: 11 }} />
                 <Tooltip
                   formatter={(value: number, name: string) => [
                     value.toFixed(3),
                     LABELS[name] || name,
                   ]}
                   contentStyle={{ fontSize: 12 }}
                 />
                 <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14}>
                   {data.map((entry) => (
                     <Cell key={entry.name} fill={COLORS[entry.name]} />
                   ))}
                 </Bar>
               </BarChart>
             </ResponsiveContainer>
           </div>
         );
       }
       ```

    2. Create `frontend/src/components/results/ArtifactChip.tsx` -- linked chip for different artifact types:

       ```tsx
       import type { Artifact } from "@/types/api";

       interface ArtifactChipProps {
         artifact: Artifact;
       }

       const TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
         pmid: { bg: "bg-blue-50", text: "text-blue-700", label: "PMID" },
         nct: { bg: "bg-green-50", text: "text-green-700", label: "NCT" },
         patent: { bg: "bg-amber-50", text: "text-amber-700", label: "Patent" },
         grant: { bg: "bg-purple-50", text: "text-purple-700", label: "Grant" },
       };

       function getArtifactUrl(artifact: Artifact): string {
         // Use the URL from the API if provided, otherwise construct from type + id
         if (artifact.url) return artifact.url;

         switch (artifact.type) {
           case "pmid":
             return `https://pubmed.ncbi.nlm.nih.gov/${artifact.id}`;
           case "nct":
             return `https://clinicaltrials.gov/study/${artifact.id}`;
           case "patent":
             return `https://patents.google.com/patent/${artifact.id}`;
           case "grant":
             return `https://reporter.nih.gov/project-details/${artifact.id}`;
           default:
             return "#";
         }
       }

       export default function ArtifactChip({ artifact }: ArtifactChipProps) {
         const style = TYPE_STYLES[artifact.type] || { bg: "bg-gray-50", text: "text-gray-700", label: artifact.type };
         const url = getArtifactUrl(artifact);

         return (
           <a
             href={url}
             target="_blank"
             rel="noopener noreferrer"
             title={artifact.title}
             className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style.bg} ${style.text} hover:opacity-80 transition-opacity`}
           >
             <span className="font-semibold mr-1">{style.label}:</span>
             <span className="truncate max-w-[120px]">{artifact.id}</span>
             <svg className="ml-1 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
             </svg>
           </a>
         );
       }
       ```

    3. Create `frontend/src/components/results/VarianceBand.tsx`:

       ```tsx
       import type { ScoreVarianceBand } from "@/types/api";

       interface VarianceBandProps {
         score: number;
         band: ScoreVarianceBand;
       }

       export default function VarianceBand({ score, band }: VarianceBandProps) {
         return (
           <div className="flex items-center space-x-2">
             <span className="text-sm font-semibold text-gray-900">
               {score.toFixed(3)}
             </span>
             <span className="text-xs text-gray-500">
               [{band.low.toFixed(3)} - {band.high.toFixed(3)}]
             </span>
           </div>
         );
       }
       ```

    4. Create `frontend/src/components/results/IntegrityBadge.tsx`:

       ```tsx
       interface IntegrityBadgeProps {
         disclosures: string[];
       }

       export default function IntegrityBadge({ disclosures }: IntegrityBadgeProps) {
         if (disclosures.length === 0) return null;

         return (
           <div className="mt-1">
             {disclosures.map((disclosure, index) => (
               <span
                 key={index}
                 className="inline-flex items-center rounded-full bg-yellow-50 border border-yellow-200 px-2 py-0.5 text-xs font-medium text-yellow-800 mr-1 mb-1"
                 title={disclosure}
               >
                 <svg className="h-3 w-3 mr-1 text-yellow-500" viewBox="0 0 20 20" fill="currentColor">
                   <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                 </svg>
                 {disclosure}
               </span>
             ))}
           </div>
         );
       }
       ```

    5. Create `frontend/src/components/results/EvidenceTrailPanel.tsx`:

       ```tsx
       "use client";

       import { useEffect, useState } from "react";
       import type { EvidenceTrail } from "@/types/api";
       import LoadingSpinner from "@/components/LoadingSpinner";
       import ErrorAlert from "@/components/ErrorAlert";

       interface EvidenceTrailPanelProps {
         candidateUuid: string;
       }

       export default function EvidenceTrailPanel({ candidateUuid }: EvidenceTrailPanelProps) {
         const [evidence, setEvidence] = useState<EvidenceTrail | null>(null);
         const [loading, setLoading] = useState(true);
         const [error, setError] = useState<string | null>(null);

         useEffect(() => {
           const fetchEvidence = async () => {
             setLoading(true);
             setError(null);
             try {
               const response = await fetch(`/api/candidates/${candidateUuid}/evidence`);
               if (!response.ok) {
                 throw new Error(`Failed to fetch evidence: ${response.status}`);
               }
               const data: EvidenceTrail = await response.json();
               setEvidence(data);
             } catch (err) {
               setError(err instanceof Error ? err.message : "Failed to load evidence trail.");
             } finally {
               setLoading(false);
             }
           };

           fetchEvidence();
         }, [candidateUuid]);

         if (loading) return <LoadingSpinner message="Loading evidence trail..." />;
         if (error) return <ErrorAlert message={error} />;
         if (!evidence) return null;

         return (
           <div className="bg-gray-50 border-t border-gray-200 px-6 py-4">
             <h4 className="text-sm font-semibold text-gray-900 mb-3">
               Evidence Trail for {evidence.candidate_name}
             </h4>
             {evidence.evidence_items.length === 0 ? (
               <p className="text-sm text-gray-500">No evidence items available.</p>
             ) : (
               <div className="space-y-3">
                 {evidence.evidence_items.map((item, index) => (
                   <div key={index} className="flex items-start space-x-3 text-sm">
                     <span className="inline-flex items-center rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700 whitespace-nowrap">
                       {item.type}
                     </span>
                     <div className="flex-1">
                       <p className="text-gray-900">{item.description}</p>
                       <div className="flex items-center space-x-3 mt-1 text-xs text-gray-500">
                         <span>Source: {item.source}</span>
                         {item.date && <span>Date: {item.date}</span>}
                         {item.score_contribution !== undefined && (
                           <span>Contribution: {item.score_contribution.toFixed(3)}</span>
                         )}
                       </div>
                       {item.url && (
                         <a
                           href={item.url}
                           target="_blank"
                           rel="noopener noreferrer"
                           className="text-xs text-blue-600 hover:text-blue-500 mt-1 inline-block"
                         >
                           View source
                         </a>
                       )}
                     </div>
                   </div>
                 ))}
               </div>
             )}
           </div>
         );
       }
       ```

    6. Create `frontend/src/components/results/FeedbackModal.tsx`:

       ```tsx
       "use client";

       import { useState } from "react";
       import type { FeedbackRequest } from "@/types/api";

       interface FeedbackModalProps {
         queryId: string;
         onClose: () => void;
         onSuccess: () => void;
       }

       export default function FeedbackModal({ queryId, onClose, onSuccess }: FeedbackModalProps) {
         const [fleissKappa, setFleissKappa] = useState("");
         const [acceptRate, setAcceptRate] = useState("");
         const [consensusRate, setConsensusRate] = useState("");
         const [isSubmitting, setIsSubmitting] = useState(false);
         const [error, setError] = useState<string | null>(null);

         const validateRange = (value: string, label: string): number => {
           const num = parseFloat(value);
           if (isNaN(num) || num < 0 || num > 1) {
             throw new Error(`${label} must be a number between 0 and 1.`);
           }
           return num;
         };

         const handleSubmit = async (e: React.FormEvent) => {
           e.preventDefault();
           setError(null);

           try {
             const body: FeedbackRequest = {
               fleiss_kappa: validateRange(fleissKappa, "Fleiss Kappa"),
               accept_rate: validateRange(acceptRate, "Accept Rate"),
               consensus_rate: validateRange(consensusRate, "Consensus Rate"),
             };

             setIsSubmitting(true);

             const response = await fetch(`/api/feedback/tasks/${queryId}/outcomes`, {
               method: "POST",
               headers: { "Content-Type": "application/json" },
               body: JSON.stringify(body),
             });

             if (!response.ok) {
               const errData = await response.json().catch(() => ({}));
               throw new Error(errData.error || `Request failed with status ${response.status}`);
             }

             onSuccess();
           } catch (err) {
             setError(err instanceof Error ? err.message : "Failed to submit feedback.");
           } finally {
             setIsSubmitting(false);
           }
         };

         return (
           <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
             <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
               <div className="flex items-center justify-between mb-4">
                 <h3 className="text-lg font-semibold text-gray-900">Submit Feedback</h3>
                 <button
                   onClick={onClose}
                   className="text-gray-400 hover:text-gray-600"
                   aria-label="Close"
                 >
                   <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                   </svg>
                 </button>
               </div>

               <p className="text-sm text-gray-600 mb-4">
                 Submit downstream task quality feedback for this query.
               </p>

               {error && (
                 <div className="rounded-md bg-red-50 p-3 mb-4">
                   <p className="text-sm text-red-700">{error}</p>
                 </div>
               )}

               <form onSubmit={handleSubmit} className="space-y-4">
                 <div>
                   <label htmlFor="fleiss-kappa" className="block text-sm font-medium text-gray-700 mb-1">
                     Fleiss Kappa (0-1)
                   </label>
                   <input
                     id="fleiss-kappa"
                     type="number"
                     step="0.01"
                     min="0"
                     max="1"
                     value={fleissKappa}
                     onChange={(e) => setFleissKappa(e.target.value)}
                     placeholder="0.00"
                     className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                     required
                   />
                   <p className="mt-1 text-xs text-gray-500">Inter-rater agreement on the label set.</p>
                 </div>

                 <div>
                   <label htmlFor="accept-rate" className="block text-sm font-medium text-gray-700 mb-1">
                     Accept Rate (0-1)
                   </label>
                   <input
                     id="accept-rate"
                     type="number"
                     step="0.01"
                     min="0"
                     max="1"
                     value={acceptRate}
                     onChange={(e) => setAcceptRate(e.target.value)}
                     placeholder="0.00"
                     className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                     required
                   />
                   <p className="mt-1 text-xs text-gray-500">Fraction of labels accepted by the customer.</p>
                 </div>

                 <div>
                   <label htmlFor="consensus-rate" className="block text-sm font-medium text-gray-700 mb-1">
                     Consensus Rate (0-1)
                   </label>
                   <input
                     id="consensus-rate"
                     type="number"
                     step="0.01"
                     min="0"
                     max="1"
                     value={consensusRate}
                     onChange={(e) => setConsensusRate(e.target.value)}
                     placeholder="0.00"
                     className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                     required
                   />
                   <p className="mt-1 text-xs text-gray-500">Post-hoc consensus rate.</p>
                 </div>

                 <div className="flex space-x-3 pt-2">
                   <button
                     type="submit"
                     disabled={isSubmitting}
                     className="flex-1 px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                   >
                     {isSubmitting ? "Submitting..." : "Submit Feedback"}
                   </button>
                   <button
                     type="button"
                     onClick={onClose}
                     className="px-4 py-2 rounded-md border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors"
                   >
                     Cancel
                   </button>
                 </div>
               </form>
             </div>
           </div>
         );
       }
       ```

    ## Files to create
    - `frontend/src/components/results/ScoreBreakdownChart.tsx`
    - `frontend/src/components/results/ArtifactChip.tsx`
    - `frontend/src/components/results/VarianceBand.tsx`
    - `frontend/src/components/results/IntegrityBadge.tsx`
    - `frontend/src/components/results/EvidenceTrailPanel.tsx`
    - `frontend/src/components/results/FeedbackModal.tsx`

    ## Code patterns to follow
    - `"use client"` only on components using React hooks or browser APIs (ScoreBreakdownChart, EvidenceTrailPanel, FeedbackModal)
    - ArtifactChip, VarianceBand, IntegrityBadge are server-compatible (no hooks)
    - Recharts components must be wrapped in `"use client"` components
    - All styling via Tailwind CSS utility classes
    - Props defined via TypeScript interfaces
    - Import types from `@/types/api`

    ## Acceptance criteria
    - All 6 component files exist under `frontend/src/components/results/`
    - ScoreBreakdownChart renders a horizontal bar chart with R/Q/C/I bars using Recharts
    - ArtifactChip renders a colored link chip with correct URLs per type (pmid, nct, patent, grant)
    - VarianceBand displays score with [low - high] range
    - IntegrityBadge renders warning badges for each disclosure (returns null if empty)
    - EvidenceTrailPanel fetches and displays evidence on mount
    - FeedbackModal renders a form with fleiss_kappa, accept_rate, consensus_rate fields
    - `npm run build` succeeds from `frontend/`
    - `npm run lint` succeeds from `frontend/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npm run build && npm run lint
    ```

### 7. Screen 2 -- Results Page and Candidate Row

- **Task ID**: screen-results-page
- **Role**: builder
- **Depends On**: screen-results-components
- **Assigned To**: builder-3
- **Description**: |
    Build the Results page at `/results/[id]` and the CandidateRow component. This page displays the ranked candidate list for a query, with expandable evidence trails and a feedback button.

    ## What to do

    1. Create `frontend/src/components/results/CandidateRow.tsx` -- an expandable row showing all candidate details:

       ```tsx
       "use client";

       import { useState } from "react";
       import type { CandidateResult } from "@/types/api";
       import ScoreBreakdownChart from "./ScoreBreakdownChart";
       import ArtifactChip from "./ArtifactChip";
       import VarianceBand from "./VarianceBand";
       import IntegrityBadge from "./IntegrityBadge";
       import EvidenceTrailPanel from "./EvidenceTrailPanel";

       interface CandidateRowProps {
         candidate: CandidateResult;
       }

       export default function CandidateRow({ candidate }: CandidateRowProps) {
         const [isExpanded, setIsExpanded] = useState(false);

         return (
           <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
             <div
               className="px-6 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
               onClick={() => setIsExpanded(!isExpanded)}
             >
               <div className="flex items-start justify-between">
                 <div className="flex items-start space-x-4">
                   {/* Rank badge */}
                   <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">
                     #{candidate.rank}
                   </div>

                   {/* Candidate info */}
                   <div className="min-w-0 flex-1">
                     <div className="flex items-center space-x-2">
                       <h3 className="text-sm font-semibold text-gray-900">{candidate.name}</h3>
                       <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                         {candidate.specialty}
                       </span>
                     </div>
                     <p className="text-sm text-gray-500 mt-0.5">{candidate.affiliation}</p>

                     {/* Identity linkage confidence */}
                     <p className="text-xs text-gray-400 mt-1">
                       Identity confidence: {(candidate.identity_linkage_confidence * 100).toFixed(1)}%
                     </p>

                     {/* Integrity disclosures */}
                     <IntegrityBadge disclosures={candidate.integrity_disclosures} />

                     {/* Top artifacts */}
                     <div className="flex flex-wrap gap-1.5 mt-2">
                       {candidate.top_artifacts.slice(0, 3).map((artifact) => (
                         <ArtifactChip key={artifact.id} artifact={artifact} />
                       ))}
                     </div>
                   </div>
                 </div>

                 {/* Score section */}
                 <div className="flex-shrink-0 ml-4 text-right">
                   <VarianceBand
                     score={candidate.score}
                     band={candidate.score_variance_band}
                   />
                   <div className="mt-2 w-48">
                     <ScoreBreakdownChart components={candidate.score_components} />
                   </div>
                 </div>
               </div>

               {/* Expand indicator */}
               <div className="flex justify-center mt-2">
                 <svg
                   className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                   fill="none"
                   viewBox="0 0 24 24"
                   stroke="currentColor"
                 >
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                 </svg>
               </div>
             </div>

             {/* Evidence trail panel (expanded) */}
             {isExpanded && <EvidenceTrailPanel candidateUuid={candidate.uuid} />}
           </div>
         );
       }
       ```

    2. Create `frontend/src/app/results/[id]/page.tsx` -- the Results page:

       ```tsx
       "use client";

       import { useEffect, useState } from "react";
       import { useParams } from "next/navigation";
       import type { QueryResponse } from "@/types/api";
       import LoadingSpinner from "@/components/LoadingSpinner";
       import ErrorAlert from "@/components/ErrorAlert";
       import CandidateRow from "@/components/results/CandidateRow";
       import FeedbackModal from "@/components/results/FeedbackModal";

       export default function ResultsPage() {
         const params = useParams();
         const queryId = params.id as string;

         const [query, setQuery] = useState<QueryResponse | null>(null);
         const [loading, setLoading] = useState(true);
         const [error, setError] = useState<string | null>(null);
         const [showFeedback, setShowFeedback] = useState(false);
         const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

         const fetchQuery = async () => {
           setLoading(true);
           setError(null);
           try {
             const response = await fetch(`/api/queries/${queryId}`);
             if (!response.ok) {
               throw new Error(`Failed to load query results: ${response.status}`);
             }
             const data: QueryResponse = await response.json();
             setQuery(data);
           } catch (err) {
             setError(err instanceof Error ? err.message : "Failed to load results.");
           } finally {
             setLoading(false);
           }
         };

         useEffect(() => {
           if (queryId) {
             fetchQuery();
           }
         }, [queryId]); // eslint-disable-line react-hooks/exhaustive-deps

         if (loading) return <LoadingSpinner message="Loading results..." />;
         if (error) return <ErrorAlert message={error} onRetry={fetchQuery} />;
         if (!query) return null;

         return (
           <div>
             {/* Query header */}
             <div className="mb-6">
               <div className="flex items-start justify-between">
                 <div>
                   <h1 className="text-2xl font-bold text-gray-900">Query Results</h1>
                   <p className="mt-2 text-sm text-gray-600 max-w-3xl">{query.task_description}</p>
                   <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                     {query.population && (
                       <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 font-medium">
                         {query.population.replace("_", " ")}
                       </span>
                     )}
                     <span>K = {query.k}</span>
                     <span>{query.candidates.length} results</span>
                     <span>{new Date(query.created_at).toLocaleString()}</span>
                   </div>
                 </div>

                 {/* Submit Feedback button */}
                 <div>
                   {feedbackSubmitted ? (
                     <span className="inline-flex items-center rounded-md bg-green-50 px-3 py-2 text-sm font-medium text-green-700">
                       Feedback submitted
                     </span>
                   ) : (
                     <button
                       onClick={() => setShowFeedback(true)}
                       className="px-4 py-2 rounded-md bg-white border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-colors"
                     >
                       Submit Feedback
                     </button>
                   )}
                 </div>
               </div>
             </div>

             {/* Candidate list */}
             {query.candidates.length === 0 ? (
               <div className="text-center py-12">
                 <p className="text-gray-500">No candidates found for this query.</p>
               </div>
             ) : (
               <div className="space-y-3">
                 {query.candidates.map((candidate) => (
                   <CandidateRow key={candidate.uuid} candidate={candidate} />
                 ))}
               </div>
             )}

             {/* Feedback modal */}
             {showFeedback && (
               <FeedbackModal
                 queryId={queryId}
                 onClose={() => setShowFeedback(false)}
                 onSuccess={() => {
                   setShowFeedback(false);
                   setFeedbackSubmitted(true);
                 }}
               />
             )}
           </div>
         );
       }
       ```

    ## Files to create
    - `frontend/src/components/results/CandidateRow.tsx`
    - `frontend/src/app/results/[id]/page.tsx`

    ## Code patterns to follow
    - Client component (`"use client"`) for the page and CandidateRow (both need state)
    - Fetch data in `useEffect` on mount
    - Show LoadingSpinner while loading, ErrorAlert on error, empty state when no results
    - CandidateRow toggles expansion on click, loads evidence trail lazily
    - FeedbackModal opens from button at top of results, closes on success with confirmation
    - All types imported from `@/types/api`
    - API calls go to `/api/queries/[id]` (the local proxy route), NOT directly to the backend

    ## Acceptance criteria
    - Results page renders at `/results/[id]` with query description at top
    - Each candidate row shows: rank number, name, affiliation, specialty, score with variance band, identity confidence, score components chart, top 3 artifact chips, integrity disclosures
    - Clicking a candidate row expands/collapses the evidence trail panel
    - "Submit Feedback" button at top opens the feedback modal
    - After successful feedback submission, button changes to "Feedback submitted"
    - Loading spinner shows while query results load
    - Error state with retry button shows on fetch failure
    - Empty state shows when query has no candidates
    - `npm run build` succeeds from `frontend/`
    - `npm run lint` succeeds from `frontend/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npm run build && npm run lint
    ```

### 8. Screen 3 -- Query History Page

- **Task ID**: screen-query-history
- **Role**: builder
- **Depends On**: shared-components
- **Assigned To**: builder-2
- **Description**: |
    Build Screen 3: the Query History page at `/history` showing a paginated table of past queries.

    ## What to do

    1. Create `frontend/src/components/history/QueryTable.tsx`:

       ```tsx
       "use client";

       import Link from "next/link";
       import type { QuerySummary } from "@/types/api";

       interface QueryTableProps {
         queries: QuerySummary[];
       }

       export default function QueryTable({ queries }: QueryTableProps) {
         if (queries.length === 0) {
           return (
             <div className="text-center py-12">
               <p className="text-gray-500">No queries found. Submit your first query to get started.</p>
               <Link
                 href="/"
                 className="mt-4 inline-flex items-center px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
               >
                 New Query
               </Link>
             </div>
           );
         }

         return (
           <div className="overflow-x-auto">
             <table className="min-w-full divide-y divide-gray-200">
               <thead className="bg-gray-50">
                 <tr>
                   <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                     Timestamp
                   </th>
                   <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                     Task Description
                   </th>
                   <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                     Population
                   </th>
                   <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                     K
                   </th>
                   <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                     Results
                   </th>
                   <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                     Actions
                   </th>
                 </tr>
               </thead>
               <tbody className="bg-white divide-y divide-gray-200">
                 {queries.map((query) => (
                   <tr key={query.id} className="hover:bg-gray-50 transition-colors">
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                       {new Date(query.created_at).toLocaleString()}
                     </td>
                     <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate" title={query.task_description}>
                       {query.task_description}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                       {query.population ? (
                         <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                           {query.population.replace("_", " ")}
                         </span>
                       ) : (
                         <span className="text-gray-400">--</span>
                       )}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                       {query.k}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                       {query.result_count}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                       <Link
                         href={`/results/${query.id}`}
                         className="text-blue-600 hover:text-blue-800 font-medium"
                       >
                         View Results
                       </Link>
                     </td>
                   </tr>
                 ))}
               </tbody>
             </table>
           </div>
         );
       }
       ```

    2. Create `frontend/src/app/history/page.tsx`:

       ```tsx
       "use client";

       import { useEffect, useState } from "react";
       import type { QuerySummary, QueryListResponse } from "@/types/api";
       import LoadingSpinner from "@/components/LoadingSpinner";
       import ErrorAlert from "@/components/ErrorAlert";
       import QueryTable from "@/components/history/QueryTable";

       const PER_PAGE = 20;

       export default function QueryHistoryPage() {
         const [queries, setQueries] = useState<QuerySummary[]>([]);
         const [totalPages, setTotalPages] = useState(1);
         const [currentPage, setCurrentPage] = useState(1);
         const [loading, setLoading] = useState(true);
         const [error, setError] = useState<string | null>(null);

         const fetchQueries = async (page: number) => {
           setLoading(true);
           setError(null);
           try {
             const response = await fetch(
               `/api/queries?page=${page}&per_page=${PER_PAGE}`
             );
             if (!response.ok) {
               throw new Error(`Failed to load query history: ${response.status}`);
             }
             const data: QueryListResponse = await response.json();
             setQueries(data.queries);
             setTotalPages(Math.max(1, Math.ceil(data.total / PER_PAGE)));
             setCurrentPage(page);
           } catch (err) {
             setError(err instanceof Error ? err.message : "Failed to load query history.");
           } finally {
             setLoading(false);
           }
         };

         useEffect(() => {
           fetchQueries(1);
         }, []);

         return (
           <div>
             <div className="mb-6">
               <h1 className="text-2xl font-bold text-gray-900">Query History</h1>
               <p className="mt-2 text-sm text-gray-600">
                 View past queries and their results, newest first.
               </p>
             </div>

             {loading ? (
               <LoadingSpinner message="Loading query history..." />
             ) : error ? (
               <ErrorAlert message={error} onRetry={() => fetchQueries(currentPage)} />
             ) : (
               <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                 <QueryTable queries={queries} />

                 {/* Pagination controls */}
                 {totalPages > 1 && (
                   <div className="flex items-center justify-between px-6 py-3 bg-gray-50 border-t border-gray-200">
                     <button
                       onClick={() => fetchQueries(currentPage - 1)}
                       disabled={currentPage <= 1}
                       className="px-3 py-1 rounded-md border border-gray-300 text-sm text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                     >
                       Previous
                     </button>
                     <span className="text-sm text-gray-600">
                       Page {currentPage} of {totalPages}
                     </span>
                     <button
                       onClick={() => fetchQueries(currentPage + 1)}
                       disabled={currentPage >= totalPages}
                       className="px-3 py-1 rounded-md border border-gray-300 text-sm text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                     >
                       Next
                     </button>
                   </div>
                 )}
               </div>
             )}
           </div>
         );
       }
       ```

    ## Files to create
    - `frontend/src/components/history/QueryTable.tsx`
    - `frontend/src/app/history/page.tsx`

    ## Code patterns to follow
    - Client components (`"use client"`) for both files (they use hooks)
    - Pagination via query params to the `/api/queries` proxy route
    - Show LoadingSpinner while loading, ErrorAlert on error
    - Empty state in QueryTable shows "No queries found" with a link to New Query
    - Task description is truncated in the table with `title` attribute for full text on hover
    - Population is shown as a pill badge; "--" if not set
    - "View Results" link navigates to `/results/{id}`
    - Newest-first ordering (backend is expected to return newest first)
    - Pagination controls at bottom with Previous/Next and page number

    ## Acceptance criteria
    - Query History page renders at `/history` with a table of past queries
    - Table columns: Timestamp, Task Description (truncated), Population, K, Results count, View Results link
    - Clicking "View Results" navigates to `/results/{id}`
    - Pagination controls appear when there are multiple pages
    - Loading spinner shows while data loads
    - Error state shows with retry button on fetch failure
    - Empty state shows when no queries exist, with link to New Query page
    - `npm run build` succeeds from `frontend/`
    - `npm run lint` succeeds from `frontend/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/frontend && npm run build && npm run lint
    ```

### 9. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: screen-new-query, screen-results-page, screen-query-history, setup-vercel-deployment
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria across the entire frontend application.

    ## Validation Commands

    Run these commands in sequence:

    1. Verify project structure exists:
       ```bash
       cd /Users/anvith/aegis/frontend && ls -la package.json tsconfig.json tailwind.config.ts next.config.ts src/types/api.ts src/lib/api-client.ts src/middleware.ts
       ```

    2. Verify all page routes exist:
       ```bash
       ls /Users/anvith/aegis/frontend/src/app/page.tsx /Users/anvith/aegis/frontend/src/app/results/\[id\]/page.tsx /Users/anvith/aegis/frontend/src/app/history/page.tsx
       ```

    3. Verify all API routes exist:
       ```bash
       ls /Users/anvith/aegis/frontend/src/app/api/queries/route.ts /Users/anvith/aegis/frontend/src/app/api/queries/\[id\]/route.ts /Users/anvith/aegis/frontend/src/app/api/candidates/\[uuid\]/evidence/route.ts /Users/anvith/aegis/frontend/src/app/api/feedback/tasks/\[taskId\]/outcomes/route.ts
       ```

    4. Verify all component files exist:
       ```bash
       ls /Users/anvith/aegis/frontend/src/components/Header.tsx /Users/anvith/aegis/frontend/src/components/LoadingSpinner.tsx /Users/anvith/aegis/frontend/src/components/ErrorAlert.tsx /Users/anvith/aegis/frontend/src/components/query/QueryForm.tsx /Users/anvith/aegis/frontend/src/components/query/PopulationSelector.tsx /Users/anvith/aegis/frontend/src/components/query/KSlider.tsx /Users/anvith/aegis/frontend/src/components/query/MeshTagInput.tsx /Users/anvith/aegis/frontend/src/components/results/CandidateRow.tsx /Users/anvith/aegis/frontend/src/components/results/ScoreBreakdownChart.tsx /Users/anvith/aegis/frontend/src/components/results/ArtifactChip.tsx /Users/anvith/aegis/frontend/src/components/results/VarianceBand.tsx /Users/anvith/aegis/frontend/src/components/results/IntegrityBadge.tsx /Users/anvith/aegis/frontend/src/components/results/EvidenceTrailPanel.tsx /Users/anvith/aegis/frontend/src/components/results/FeedbackModal.tsx /Users/anvith/aegis/frontend/src/components/history/QueryTable.tsx
       ```

    5. Verify TypeScript strict mode:
       ```bash
       cd /Users/anvith/aegis/frontend && grep -q '"strict": true' tsconfig.json && echo "TypeScript strict mode: OK" || echo "TypeScript strict mode: MISSING"
       ```

    6. Verify recharts is installed:
       ```bash
       cd /Users/anvith/aegis/frontend && grep -q '"recharts"' package.json && echo "recharts dependency: OK" || echo "recharts dependency: MISSING"
       ```

    7. Verify .env.local.example exists with required vars:
       ```bash
       cd /Users/anvith/aegis/frontend && grep -q 'AEGIS_API_URL' .env.local.example && grep -q 'AEGIS_API_TOKEN' .env.local.example && echo "env vars: OK" || echo "env vars: MISSING"
       ```

    8. Verify Vercel deployment configuration:
       ```bash
       cd /Users/anvith/aegis/frontend && test -f vercel.json && echo "vercel.json: OK" || echo "vercel.json: MISSING"
       test -f .env.production.example && echo ".env.production.example: OK" || echo ".env.production.example: MISSING"
       ! grep -q 'output.*standalone\|output.*export' next.config.ts && echo "next.config.ts output mode: OK" || echo "next.config.ts has invalid output override"
       ```

    9. Run the full build:
       ```bash
       cd /Users/anvith/aegis/frontend && npm run build
       ```

    10. Run linting:
        ```bash
        cd /Users/anvith/aegis/frontend && npm run lint
        ```

    If any validation step fails, create a fix task describing what went wrong and what needs to change.

    ## Acceptance Criteria

    All of the following must be true:
    - `frontend/` directory exists with a valid Next.js 14+ project
    - `npm run build` succeeds without errors
    - `npm run lint` succeeds without errors
    - TypeScript strict mode is enabled
    - `frontend/vercel.json` exists with framework, buildCommand, devCommand, installCommand, outputDirectory
    - `frontend/.env.production.example` exists and documents AEGIS_API_URL and AEGIS_API_TOKEN for the Vercel dashboard
    - `frontend/next.config.ts` does NOT set `output: "standalone"` or `output: "export"`
    - Tailwind CSS is configured
    - Recharts is installed as a dependency
    - `.env.local.example` has AEGIS_API_URL and AEGIS_API_TOKEN
    - `frontend/src/types/api.ts` exists with all type definitions
    - `frontend/src/lib/api-client.ts` exists with server-side API client
    - `frontend/src/middleware.ts` exists
    - All 4 API route handlers exist (queries, queries/[id], candidates/[uuid]/evidence, feedback/tasks/[taskId]/outcomes)
    - Root layout includes Header with navigation
    - Screen 1 (New Query) at `/` has: textarea, population selector, K slider, advanced section (collapsed), MeSH tag input, cutoff strategy, submit button with loading state
    - Screen 2 (Results) at `/results/[id]` has: query description header, ranked candidate list with score breakdown, artifact chips, integrity badges, expandable evidence trail, feedback button and modal
    - Screen 3 (Query History) at `/history` has: paginated table with timestamp, description, population, K, result count, view results link
    - All screens have loading states, error states, and empty states
    - JWT tokens are only used server-side (in api-client.ts), never in client components

## Acceptance Criteria

- `frontend/` directory exists at `/Users/anvith/aegis/frontend/` with a valid Next.js 14+ project
- `npm run build` succeeds without errors from `frontend/`
- `npm run lint` succeeds without errors from `frontend/`
- TypeScript strict mode is enabled in `tsconfig.json`
- Tailwind CSS is configured and working
- Recharts is installed and used for score component visualization
- `.env.local.example` contains `AEGIS_API_URL` and `AEGIS_API_TOKEN`
- All TypeScript types in `src/types/api.ts` match the backend API shapes defined in the prompt
- Server-side API client in `src/lib/api-client.ts` uses `AEGIS_API_TOKEN` from environment variables
- 4 API proxy routes exist for queries, query by ID, candidate evidence, and feedback
- Next.js middleware exists at `src/middleware.ts`
- Screen 1 (New Query) at `/` contains all form elements: textarea (required), population selector, K slider (5-100, default 20), advanced section (collapsed by default) with MeSH tag input and cutoff strategy
- Screen 2 (Results) at `/results/[id]` displays ranked candidate list with all required fields, expandable evidence trail, and feedback modal
- Screen 3 (Query History) at `/history` displays paginated table of past queries with all columns
- All screens have loading states, error states, and empty states
- JWT tokens are never exposed to client-side code (no localStorage, no cookies with token values)
- Header navigation links work for "New Query" and "Query History"
- `frontend/vercel.json` exists with correct Vercel deployment configuration
- `frontend/.env.production.example` documents AEGIS_API_URL and AEGIS_API_TOKEN for the Vercel dashboard
- `frontend/next.config.ts` does NOT set `output: "standalone"` or `output: "export"`

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis/frontend && npm run build` -- Verify the Next.js app builds without errors
- `cd /Users/anvith/aegis/frontend && npm run lint` -- Verify linting passes
- `ls /Users/anvith/aegis/frontend/src/types/api.ts` -- Verify types file exists
- `ls /Users/anvith/aegis/frontend/src/lib/api-client.ts` -- Verify API client exists
- `ls /Users/anvith/aegis/frontend/src/middleware.ts` -- Verify middleware exists
- `ls /Users/anvith/aegis/frontend/src/app/page.tsx /Users/anvith/aegis/frontend/src/app/results/\[id\]/page.tsx /Users/anvith/aegis/frontend/src/app/history/page.tsx` -- Verify all 3 page routes exist
- `ls /Users/anvith/aegis/frontend/src/app/api/queries/route.ts /Users/anvith/aegis/frontend/src/app/api/queries/\[id\]/route.ts` -- Verify API proxy routes exist
- `test -f /Users/anvith/aegis/frontend/vercel.json && echo "vercel.json: OK"` -- Verify Vercel config exists
- `test -f /Users/anvith/aegis/frontend/.env.production.example && echo ".env.production.example: OK"` -- Verify production env docs exist

## Notes

- This is a **new Next.js application** bootstrapped inside the existing Python/aegis repo. It does not modify any Python backend code.
- The backend API is assumed to be running separately. The frontend proxies all API calls through Next.js API routes.
- For local development, set `AEGIS_API_URL=http://localhost:8000` and `AEGIS_API_TOKEN=<your-jwt>` in `frontend/.env.local`.
- No external component library is used (no shadcn/ui, no MUI, no Ant Design). All components are built with plain Tailwind CSS.
- Recharts is the only visualization library. It is used for the score component breakdown bar chart in the Results screen.
- The app uses `npx create-next-app@latest` which will install using npm. Ensure Node.js 18+ is available.
- If `create-next-app` prompts for options interactively, the builder should select: TypeScript (Yes), ESLint (Yes), Tailwind CSS (Yes), `src/` directory (Yes), App Router (Yes), Turbopack (No), import alias `@/*`.
- **Vercel deployment**: In the Vercel dashboard, set the **Root Directory** to `frontend`. The two required env vars are `AEGIS_API_URL` (your backend host) and `AEGIS_API_TOKEN` (a JWT token). Both are server-only and never sent to the browser. Do NOT set `output: "standalone"` in `next.config.ts` — Vercel builds Next.js natively.
