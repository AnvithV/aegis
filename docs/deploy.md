# Aegis Deployment & Maintenance Guide

## Quick Reference

```bash
# Deploy backend
flyctl deploy --remote-only

# Deploy frontend
cd frontend && vercel --prod --yes

# Tail live backend logs
flyctl logs -a aegis-backend

# List Fly.io secrets
flyctl secrets list -a aegis-backend

# Set a secret
flyctl secrets set KEY=value -a aegis-backend

# SSH into the running machine
flyctl ssh console -a aegis-backend

# Restart the backend (rolling)
flyctl machines restart -a aegis-backend

# Generate a new JWT token for the frontend
uv run python -c "
from aegis.api.auth import create_token, CustomerClaims
print(create_token(CustomerClaims(
    customer_id='frontend',
    customer_name='Aegis UI',
    rate_limit_qps=20,
    llm_budget_cents=10000,
), expiry_hours=8760))  # 1 year
"
```

---

## Environments

| Layer    | Platform  | URL                                      |
|----------|-----------|------------------------------------------|
| Backend  | Fly.io    | https://aegis-backend.fly.dev            |
| Frontend | Vercel    | https://aegis-frontend-rho.vercel.app    |

The Vercel URL `aegis-frontend-rho.vercel.app` is the **stable alias** — it always points to the latest production deployment. Each deploy also gets a unique per-commit URL shown in the `vercel` CLI output.

---

## Backend — Fly.io

### Configuration

- **App name**: `aegis-backend`
- **Region**: `sjc` (San Jose)
- **Machine**: 1 shared CPU, 512 MB RAM
- **Health check**: `GET /v1/health` every 30 s
- **Persistent volume**: `aegis_data` (1 GB encrypted) mounted at `/data`

All configuration lives in `fly.toml` at the repo root.

### Deploying

```bash
# From repo root — builds image remotely on Depot, no local Docker needed
flyctl deploy --remote-only
```

The deploy is a **rolling update**: the old machine is kept alive until the new one passes health checks. If health checks fail, Fly.io automatically rolls back.

After a successful deploy you will always see:

```
WARNING The app is not listening on the expected address…
✔ Machine 28673eec0dd5d8 is now in a good state
```

The warning fires during the brief startup window before uvicorn binds. It is **harmless** — the health check passing immediately after confirms the server is up.

### Secrets

Backend secrets are stored in Fly.io (never in source control):

| Secret              | Purpose                                       |
|---------------------|-----------------------------------------------|
| `AEGIS_JWT_SECRET`  | Signs/verifies all API JWTs                   |
| `ANTHROPIC_API_KEY` | LLM query expansion (falls back to MetaMap if absent) |
| `NCBI_API_KEY`      | PubMed polite pool (10 req/s without key, faster with) |

```bash
# View current secrets (names only, not values)
flyctl secrets list -a aegis-backend

# Add or rotate a secret (triggers an automatic redeploy)
flyctl secrets set ANTHROPIC_API_KEY=sk-ant-... -a aegis-backend

# Remove a secret
flyctl secrets unset SOME_KEY -a aegis-backend
```

Setting a secret **triggers an automatic rolling redeploy** — you do not need to run `flyctl deploy` separately.

### Persistent Volume

The volume `aegis_data` stores `aegis.duckdb` at `/data/aegis.duckdb`. It persists across deploys and restarts.

> ⚠️ **Known gap**: `QueryPipeline`, `CandidateStore`, `JobStore`, and `QueryStore` all default to the relative path `"aegis.duckdb"` (resolving to `/app/aegis.duckdb` inside the container), **not** the `AEGIS_DB_PATH` env var pointing to `/data/aegis.duckdb`. Pipeline data is therefore ephemeral — it is wiped on each deploy. The `/data` volume currently holds only data written by scripts that explicitly use `AEGIS_DB_PATH`. Fixing all stores to read `AEGIS_DB_PATH` is a future task.

```bash
# List volumes
flyctl volumes list -a aegis-backend

# Extend volume size (cannot shrink)
flyctl volumes extend vol_v3gy7l0jky8py614 --size 2 -a aegis-backend
```

### Logs

```bash
# Stream live logs
flyctl logs -a aegis-backend

# Last 100 lines
flyctl logs -a aegis-backend -n 100
```

Key log lines to watch for:

```
INFO  aegis.ingestion.record_ingester  Ingestion [pubmed]: 640 new, 165 merged …
INFO  aegis.ingestion.record_ingester  Ingestion [reporter]: 246 new, 163 merged …
WARNING aegis.sources.*               Source ctgov fetch error after …ms: …
WARNING aegis.api.streaming           SSE queue full for query …
```

### Scaling

```bash
# Check current machine state
flyctl machines list -a aegis-backend

# Scale memory up (e.g., if scoring large candidate sets OOMs)
flyctl machine update 28673eec0dd5d8 --memory 1024 -a aegis-backend

# Scale to 2 machines (note: DuckDB file-mode only supports one writer —
# do not scale beyond 1 without switching to a shared DB first)
flyctl scale count 2 -a aegis-backend   # NOT safe yet — see note above
```

### Rollback

```bash
# List recent image deployments
flyctl releases -a aegis-backend

# Roll back to a specific version
flyctl deploy --image registry.fly.io/aegis-backend:deployment-<id> -a aegis-backend
```

---

## Frontend — Vercel

### Configuration

- **Project**: `aegis-frontend` (team: `anviths-projects-895476ef`)
- **Framework**: Next.js 16 (Turbopack)
- **Build command**: `npm run build`
- **Runtime**: Node.js (server-rendered routes)

### Deploying

```bash
# From the repo root or frontend/ directory
vercel --prod --yes
```

Vercel automatically picks up `.vercel/project.json` to identify the project. Each deploy gets a unique URL; the stable alias `aegis-frontend-rho.vercel.app` is updated automatically.

### Environment Variables

The frontend reads two server-only env vars (never sent to the browser):

| Variable         | Value                             | Where set          |
|------------------|-----------------------------------|--------------------|
| `AEGIS_API_URL`  | `https://aegis-backend.fly.dev`   | `frontend/.env.local` (local) / Vercel dashboard (prod) |
| `AEGIS_API_TOKEN`| A long-lived JWT                  | Same               |

For **local development**, copy the example:

```bash
cp frontend/.env.local.example frontend/.env.local
# Then fill in AEGIS_API_URL and AEGIS_API_TOKEN
```

For **production**, set these in the Vercel dashboard:
_Project → Settings → Environment Variables → Production_

Or via CLI:

```bash
vercel env add AEGIS_API_TOKEN production
```

### Rotating the Frontend JWT Token

The token in `AEGIS_API_TOKEN` authenticates every frontend → backend call. It expires after 1 year (8760 hours). When it expires all queries will return 401.

```bash
# Generate a fresh 1-year token (run from repo root with uv)
uv run python -c "
from aegis.api.auth import create_token, CustomerClaims
print(create_token(CustomerClaims(
    customer_id='frontend',
    customer_name='Aegis UI',
    rate_limit_qps=20,
    llm_budget_cents=10000,
), expiry_hours=8760))
"
```

Then update it:

```bash
# Update in Vercel (triggers an automatic redeploy)
vercel env rm AEGIS_API_TOKEN production
vercel env add AEGIS_API_TOKEN production   # paste the new token when prompted

# Update in your local .env.local manually
```

### SSE Streaming Timeout

The query progress stream (`GET /api/queries/[id]/stream`) proxies an SSE connection from the browser through Vercel to the Fly.io backend. The pipeline can take 60–120 s. The route is configured with:

```typescript
export const maxDuration = 300; // in route.ts
```

If you ever see source progress cards not appearing or showing stale data, check:
1. `maxDuration` is still set in `frontend/src/app/api/queries/[id]/stream/route.ts`
2. The Vercel plan supports long-running functions (Pro plan supports up to 300 s)

### Rollback

```bash
# List recent deployments
vercel ls aegis-frontend --prod

# Redeploy a specific deployment URL
vercel redeploy <deployment-url>

# Or promote a previous deployment to production
vercel alias set <old-deployment-url> aegis-frontend-rho.vercel.app
```

---

## Local Development

```bash
# 1. Start backend (hot-reload, port 8000)
uv run uvicorn aegis.api.server:app --reload --port 8000

# 2. Start frontend (port 3000)
cd frontend && npm run dev
```

Make sure `frontend/.env.local` points to `http://localhost:8000` and has a valid `AEGIS_API_TOKEN` signed with the local dev secret (`aegis-dev-secret-change-in-production` by default).

### Running a test query locally

```bash
uv run python -c "
import asyncio
from aegis.pipeline.orchestrator import QueryPipeline

async def main():
    p = QueryPipeline(db_path='/tmp/test.duckdb')
    result = await p.execute(task_description='KRAS lung cancer', k=10)
    for sp in result.source_progress:
        print(f'{sp.source_name}: {sp.status} — {sp.record_count} records')
    print(f'Ranked: {len(result.ranked_list.candidates)} candidates')

asyncio.run(main())
"
```

Expected output (all four sources):
```
pubmed: complete — 200 records
reporter: complete — 200 records
ctgov: complete — 200 records
openalex_works: complete — 200 records
Ranked: 10 candidates
```

### Seeding the database

```bash
# Seed with real KRAS researchers (NIH Reporter + PubMed + iCite + CT.gov)
uv run python scripts/seed_real_kras.py

# See available source flags
uv run python scripts/seed_real_kras.py --list-sources
```

---

## Known Gotchas & History

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 1 | Fly.io warning "not listening on expected address" | Harmless | Fires during the few seconds before uvicorn binds; health check passes immediately after |
| 2 | `openalex_grants` source | **Removed** | Was fetching records but never ingesting them; `grants.funder` filter also returned near-zero results. Removed from pipeline in April 2026 |
| 3 | Source progress cards all appearing at once | **Fixed** | `progress_callback` was called after `asyncio.gather` waited for all sources; now fires per-source as it completes |
| 4 | SSE events dropped before client connects | **Fixed** | `push_event` now pre-creates the queue so early events are buffered, not silently dropped |
| 5 | Vercel SSE proxy timing out | **Fixed** | Added `export const maxDuration = 300` to the stream proxy route |
| 6 | Pipeline DB path not using `/data` volume | **Open** | All stores default to `"aegis.duckdb"` (ephemeral `/app/`) instead of `AEGIS_DB_PATH=/data/aegis.duckdb` |
| 7 | NIH Reporter receives MeSH terms as RCDC categories | Expected | Reporter `spending_categories_desc` gets the expanded MeSH terms; RCDC ≠ MeSH but the API returns all grants when no category matches, so records still flow through |
| 8 | JWT in `frontend/.env.local` | Manual rotation | 1-year expiry; see "Rotating the Frontend JWT Token" above |
| 9 | LLM expansion falls back to MetaMap | Expected | If `ANTHROPIC_API_KEY` is absent or the Claude call fails, MetaMap uses word-splitting heuristics (lower quality MeSH terms but still functional) |
| 10 | DuckDB single-writer constraint | **Open** | Scaling to >1 Fly.io machine will cause write conflicts; do not scale beyond 1 until stores are migrated to a shared DB (Postgres + pg_duckdb or motherduck) |
