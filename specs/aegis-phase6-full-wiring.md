# Aegis Phase 6 — Full System Wiring (Production Ready)

> **Status:** COMPLETE (2026-04-28)

## Context

All the hard ML/infrastructure work is done. Four gaps remain before Aegis is end-to-end
production-ready:

1. **Live ingestion** — pipeline fetches records but discards them; DB stays empty → 0 results
2. **Feedback loop** — `feedback_router` not mounted; `FeedbackModal` sends 3 of 6+ required fields
3. **Weight relearning** — `SteadyStateRefitter.run()` exists but no API or scheduler trigger
4. **HITL review queue** — standalone FastAPI app, not accessible via main server or frontend

All four close together. No new ML or data-science work needed — only wiring.

---

## What Is Already Built (Do Not Rebuild)

| Component | Location | Status |
|-----------|----------|--------|
| F1–F7 scoring + ranking | `src/aegis/scoring/` | ✅ wired in pipeline |
| Query type classifier | `src/aegis/query/classifier.py` | ✅ wired |
| SSE streaming | `src/aegis/api/streaming.py` | ✅ wired |
| Shortlists & notes | `src/aegis/api/shortlists.py`, `notes.py` | ✅ wired |
| Privacy gate | `src/aegis/privacy/` | ✅ wired |
| Bootstrap variance bands | `src/aegis/scoring/variance.py` | ✅ wired |
| Integrity hard gate | `src/aegis/integrity/hard_gate.py` | ✅ wired |
| Query history store | `src/aegis/storage/query_store.py` | ✅ wired |
| Candidate store + migrations | `src/aegis/storage/candidate_store.py` | ✅ wired |
| Probabilistic linker | `src/aegis/identity/probabilistic.py` | built, **not called** |
| HITL review queue | `src/aegis/identity/review_queue.py` | built, **not mounted** |
| Feedback endpoint | `src/aegis/api/feedback.py` | built, **not mounted** |
| Plackett-Luce fitter | `src/aegis/learning/plackett_luce.py` | built, **not triggered** |
| SteadyStateRefitter | `src/aegis/learning/refit_steady_state.py` | built, **not triggered** |
| ColdStartGuard | `src/aegis/learning/cold_start_guard.py` | built, **not triggered** |
| WeightSliderPanel | `frontend/src/components/results/WeightSliderPanel.tsx` | built, read-only |
| FeedbackModal | `frontend/src/components/results/FeedbackModal.tsx` | built, incomplete payload |
| Frontend feedback proxy | `frontend/src/app/api/feedback/tasks/[taskId]/outcomes/route.ts` | ✅ wired |

---

## Files

| Action | Path |
|--------|------|
| NEW | `src/aegis/ingestion/converters.py` |
| NEW | `src/aegis/ingestion/record_ingester.py` |
| NEW | `src/aegis/ingestion/converters_test.py` |
| NEW | `src/aegis/ingestion/record_ingester_test.py` |
| NEW | `src/aegis/api/refit.py` |
| NEW | `src/aegis/api/hitl.py` |
| NEW | `frontend/src/app/api/refit/trigger/route.ts` |
| NEW | `frontend/src/app/api/refit/status/route.ts` |
| NEW | `frontend/src/app/api/hitl/next/route.ts` |
| NEW | `frontend/src/app/api/hitl/[itemId]/decide/route.ts` |
| NEW | `frontend/src/app/api/hitl/stats/route.ts` |
| EDIT | `src/aegis/ingestion/__init__.py` |
| EDIT | `src/aegis/pipeline/orchestrator.py` |
| EDIT | `src/aegis/api/server.py` |
| EDIT | `frontend/src/components/results/FeedbackModal.tsx` |
| EDIT | `frontend/src/app/results/[id]/page.tsx` |

---

## Part 1 — Live Ingestion Pipeline

### Step 1 — `src/aegis/ingestion/converters.py` (NEW)

Four pure functions, one per source. No I/O, no side effects — easy to test.

#### Helpers (internal)
```python
def _normalize_orcid(raw: str) -> str:
    return raw.strip().replace("https://orcid.org/", "").replace("http://orcid.org/", "")

def _normalize_name(name: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", name).lower().strip()

def _make_uuid(strong_keys: dict[str, str], name: str, affiliation: str = "") -> str:
    # Priority: orcid > era_commons > sha256(name+affiliation)
    if "orcid" in strong_keys:
        key = f"orcid:{_normalize_orcid(strong_keys['orcid'])}"
    elif "era_commons" in strong_keys:
        key = f"era:{strong_keys['era_commons'].upper()}"
    else:
        key = f"name:{_normalize_name(name)}:{affiliation[:80].lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]
```

#### `pubmed_record_to_candidates(record: PubMedRecord) -> list[Candidate]`
- Senior/last author only (`is_last_author=True`). Fallback: first author.
- ORCID → `strong_keys["orcid"]` normalised.
- `affiliation = author.affiliations[0]` or `""`.
- `linkage_confidence = 0.85` with ORCID, `0.70` without.
- `evidence_trail = [f"Published '{title[:80]}' (PMID:{pmid}, {date})"]`
- `mesh_descriptors = record.mesh_descriptors[:30]`

#### `grant_record_to_candidates(record: GrantRecord) -> list[Candidate]`
- One Candidate per PI in `record.pis`.
- `strong_keys["era_commons"] = pi.era_id.upper()` if `pi.era_id`.
- `strong_keys["orcid"]` if `pi.orcid`.
- `linkage_confidence = 0.93` with eRA Commons, `0.78` without.
- `evidence_trail = [f"NIH {project_number} ({fiscal_year}, ${total_cost:,})"]`
- MeSH from `rcdc_categories[:10]` via `MeshDescriptor`.

#### `study_record_to_candidates(record: StudyRecord) -> list[Candidate]`
- PI-role investigators only (`i.role == "PI"`). Return `[]` if none.
- No strong keys (CT.gov doesn't expose ORCID/eRA).
- `linkage_confidence = 0.72`.
- `evidence_trail = [f"PI on {nct_id}: '{title[:80]}' ({phase}, {status})"]`
- MeSH from `conditions_mesh[:10]`.

#### `openalex_work_to_candidates(record: OpenAlexWork) -> list[Candidate]`
- Last-position authorship only (`authorship.get("position") == "last"`). Fallback: final element.
- ORCID from `authorship.get("orcid") or authorship.get("author_orcid")`.
- `linkage_confidence = 0.85` with ORCID, `0.65` without.
- `evidence_trail = [f"OpenAlex {openalex_id}: '{title[:80]}' ({cited_by_count} citations)"]`
- MeSH from `record.mesh_terms[:10]`.

---

### Step 2 — `src/aegis/ingestion/record_ingester.py` (NEW)

```python
_MAX_EVIDENCE_ITEMS = 20
_MAX_MESH_DESCRIPTORS = 30
_MAX_NAME_VARIANTS = 10
```

#### `_merge_candidates(existing: Candidate, new: Candidate) -> Candidate`
- `uuid` = `existing.uuid` (preserved).
- `artifact_refs` = union of pmids, nct_ids, grant_ids, patent_ids (deduped via `dict.fromkeys`).
- `name_variants` = union (case-insensitive dedup), capped at `_MAX_NAME_VARIANTS`.
- `evidence_trail` = append new items not already in existing set, capped at `_MAX_EVIDENCE_ITEMS`.
- `mesh_descriptors` = union by `descriptor.lower()`, capped at `_MAX_MESH_DESCRIPTORS`.
- `last_updated_per_source` = `{**existing, **new}` (new timestamps win).
- `strong_keys` = `{**existing.strong_keys, **new.strong_keys}` (union).
- `affiliations` = `existing.affiliations or new.affiliations`.
- `linkage_confidence` = `max(existing.linkage_confidence, new.linkage_confidence)`.

#### `class RecordIngester`
```python
def __init__(self, db_path: str = "aegis.duckdb") -> None:
    self._store = CandidateStore(db_path=db_path)
    self._cache: dict[tuple[str, str], str] = {}  # (key_type, key_value) → uuid
    self.new_count = 0
    self.merged_count = 0
    self.error_count = 0
```

**`ingest(candidate: Candidate) -> bool`** — public entry point, never raises:
```python
try:
    return self._ingest_safe(candidate)
except Exception:
    logger.warning("Failed to ingest %s", candidate.uuid, exc_info=True)
    self.error_count += 1
    return False
```

**`_ingest_safe(candidate: Candidate) -> bool`**:
1. `existing_uuid = self._find_existing(candidate.strong_keys)`
2. If found: `existing = self._store.get_by_uuid(existing_uuid)` → merge → upsert → `merged_count += 1` → return `False`
3. Else: upsert candidate → update cache → `new_count += 1` → return `True`

**`_find_existing(strong_keys) -> str | None`**:
- Check in-memory `_cache` first.
- On miss: call `self._store.get_by_strong_key(key_type, key_value)`.
- Update cache on hit. Return uuid or None.

**`_upsert_with_retry(candidate, max_attempts=3)`**:
- Retry loop with `time.sleep(0.1 * (2**attempt))` backoff (100ms, 200ms).
- Re-raises on final attempt.

**`close()`**: calls `self._store.close()`.

**`log_summary(source_name: str)`**: logs `INFO` with new/merged/error counts.

---

### Step 3 — `src/aegis/ingestion/__init__.py` (EDIT)

Append to existing exports (do not remove existing ones):
```python
from aegis.ingestion.converters import (
    pubmed_record_to_candidates,
    grant_record_to_candidates,
    study_record_to_candidates,
    openalex_work_to_candidates,
)
from aegis.ingestion.record_ingester import RecordIngester
```

---

### Step 4 — `src/aegis/pipeline/orchestrator.py` (EDIT)

#### 4a. Add imports
```python
from aegis.ingestion.converters import (
    pubmed_record_to_candidates,
    grant_record_to_candidates,
    study_record_to_candidates,
    openalex_work_to_candidates,
)
from aegis.ingestion.record_ingester import RecordIngester
```

#### 4b. Update `execute()` — create/close ingester around fetch
```python
ingester = RecordIngester(db_path=self._db_path)
try:
    fetched_count, source_progress = await self._fetch_all_sources(
        task_description, mesh_terms, progress_callback, ingester
    )
finally:
    ingester.close()
```

#### 4c. Update `_fetch_all_sources` signature
Add `ingester: RecordIngester` parameter; pass it to each `_fetch_source` call.

#### 4d. Rewrite `_fetch_source` — fix method names + add ingestion

**pubmed** (already correct: `search_and_fetch(query, batch_size=50)`):
```python
ncbi_key = os.environ.get("NCBI_API_KEY")
client = PubMedClient(api_key=ncbi_key)
async for record in client.search_and_fetch(query, batch_size=50):
    for candidate in pubmed_record_to_candidates(record):
        ingester.ingest(candidate)
    count += 1
    if count >= 200:
        break
ingester.log_summary("pubmed")
```

**reporter** (fix: was `client.search(query)` → now `client.fetch_grants_by_topic(rcdc_terms=mesh_terms)`):
```python
client = ReporterClient()
async for record in client.fetch_grants_by_topic(rcdc_terms=mesh_terms):
    for candidate in grant_record_to_candidates(record):
        ingester.ingest(candidate)
    count += 1
    if count >= 200:
        break
ingester.log_summary("reporter")
```

**ctgov** (fix: was `client.search(query)` → now `client.fetch_studies_by_condition(mesh_terms=mesh_terms)`):
```python
client = CtgovClient()
async for record in client.fetch_studies_by_condition(mesh_terms=mesh_terms):
    for candidate in study_record_to_candidates(record):
        ingester.ingest(candidate)
    count += 1
    if count >= 200:
        break
ingester.log_summary("ctgov")
```

**openalex_works** (already correct: `search_works(query, batch_size=200)`):
```python
client = OpenAlexClient()
async for record in client.search_works(query, batch_size=200):
    for candidate in openalex_work_to_candidates(record):
        ingester.ingest(candidate)
    count += 1
    if count >= 200:
        break
ingester.log_summary("openalex_works")
```

**openalex_grants** — keep counting only (returns `NonUsGrantRecord`, no converter; keep as-is for now).

---

### Step 5 — Tests

#### `src/aegis/ingestion/converters_test.py` (NEW)
- `test_pubmed_last_author_only` — paper with last author marked → 1 candidate
- `test_pubmed_fallback_to_first` — no last author → first author extracted
- `test_pubmed_skips_empty_name` — author with empty name → 0 candidates
- `test_pubmed_orcid_normalization` — URL-prefix ORCID → stripped in strong_keys
- `test_pubmed_no_orcid_lower_confidence` — 0.70 without ORCID
- `test_grant_pi_strong_keys` — PI with era_id → era_commons in strong_keys; confidence 0.93
- `test_grant_skips_empty_pi_name` → 0 candidates
- `test_grant_artifact_ref_contains_project_number`
- `test_study_pi_role_only` — PI + Sub-I → only PI; nct_id in artifact_refs
- `test_study_no_pi_returns_empty`
- `test_openalex_last_position` — position=last → extracted
- `test_openalex_fallback_to_last_element` — no last position → final element
- `test_openalex_orcid_extracted` — ORCID normalised in strong_keys
- `test_deterministic_uuid` — same inputs → same 32-char UUID across calls
- `test_normalize_orcid_strips_url`

#### `src/aegis/ingestion/record_ingester_test.py` (NEW)

Use a temp DuckDB file via `tmp_path` fixture.

- `test_ingest_new_candidate` → returns `True`, `new_count == 1`
- `test_ingest_merge_by_orcid` → second ingest same ORCID returns `False`; merged pmids contain both
- `test_merge_evidence_cap` → evidence trail capped at `_MAX_EVIDENCE_ITEMS` (20)
- `test_merge_mesh_cap` → MeSH capped at `_MAX_MESH_DESCRIPTORS` (30)
- `test_merge_name_variants_deduped` → case-insensitive dedup
- `test_merge_strong_keys_unioned` → new strong key added to existing candidate
- `test_ingest_never_raises` → bad/invalid candidate → returns `False`, `error_count == 1`
- `test_cache_prevents_db_lookup` → second ingest of same ORCID uses cache (mock `get_by_strong_key` to assert only called once)

---

## Part 2 — Feedback Loop & Weight Relearning

### Step 6 — Mount `feedback_router` in `src/aegis/api/server.py` (EDIT)

Add to imports:
```python
from aegis.api import feedback as feedback_mod
```

Add to router mounts (alongside shortlists, notes, streaming):
```python
app.include_router(feedback_mod.router)
```

That's it — `feedback_router` uses prefix `/v1/feedback` already defined in `feedback.py`.

---

### Step 7 — Fix `FeedbackModal.tsx` to send full `TaskOutcomeRequest` (EDIT)

**Problem**: modal sends only `{fleiss_kappa, accept_rate, consensus_rate}`.
Backend `TaskOutcomeRequest` also requires: `query_specialty`, `query_mesh_terms`, `candidates[]`.

**Solution**: pass the required context as props from the parent (results page already has all this data).

**Props change**:
```typescript
interface FeedbackModalProps {
  queryId: string;
  isOpen: boolean;
  onClose: () => void;
  // Add:
  querySpecialty: string;
  meshTerms: string[];
  candidates: Array<{
    candidate_uuid: string;
    rank: number;
    quality_prior_score: number;
    topical_fit_score: number;
    recency_score: number;
  }>;
}
```

**Payload change** — replace the current 3-field body with:
```typescript
const body = {
  query_specialty: querySpecialty,
  query_mesh_terms: meshTerms,
  candidates: candidates,
  fleiss_kappa: parseFloat(fleissKappa),
  accept_rate: parseFloat(acceptRate),
  consensus_rate: parseFloat(consensusRate),
};
```

**Parent update** (`frontend/src/app/results/[id]/page.tsx` — EDIT):
Pass the new props to `<FeedbackModal>` from query result data:
- `querySpecialty`: from `result.query_type`
- `meshTerms`: from `result.expansion_info.expanded_mesh_terms`
- `candidates`: map `result.candidates` to the required shape using existing rank, Q, C, R scores

---

### Step 8 — `src/aegis/api/refit.py` (NEW)

```python
router = APIRouter(prefix="/v1/refit", tags=["refit"])

class RefitTriggerResponse(BaseModel):
    status: str            # "started" | "blocked" | "skipped"
    specialty: str
    deployment_decision: str
    new_version: int | None
    prior_exponents: dict[str, float]
    new_exponents: dict[str, float]
    delta: dict[str, float]
    guard_verdict: str     # allow_deployment reason
    message: str

class RefitStatusResponse(BaseModel):
    last_refit_at: str | None
    current_version: int
    specialty: str
    exponents: dict[str, float]
    ci_half_widths: dict[str, float]
    pending_downstream_outcomes: int

@router.post("/trigger", response_model=RefitTriggerResponse)
def trigger_refit(specialty: str = "basic_research") -> RefitTriggerResponse:
    """Manually trigger a weight refit cycle for the given specialty."""
    # 1. Load current WeightVector from config/aegis/weights/{specialty}_v*.yaml
    # 2. Instantiate SteadyStateRefitter with standard paths
    # 3. Call refitter.run(specialty=specialty, current_weights=weight_vector)
    # 4. Return RefitTriggerResponse from RefitReport
    #    - status = "started" if auto_deploy, "blocked" if guard rejected, "skipped" otherwise
    #    - new_version from RefitReport.version
    #    - Include delta, exponents, guard_verdict.reason

@router.get("/status", response_model=RefitStatusResponse)
def get_refit_status(specialty: str = "basic_research") -> RefitStatusResponse:
    """Return current weight version info and pending feedback count."""
    # 1. Load current weight YAML → version, exponents
    # 2. Load DownstreamQualityStore → count records
    # 3. Read last refit timestamp from YAML metadata if present
    # 4. Return RefitStatusResponse
```

**Path constants** (use env vars with defaults):
```python
_WEIGHTS_DIR = Path(os.environ.get("AEGIS_WEIGHTS_DIR", "config/aegis/weights"))
_AUDIT_JUDGMENTS = Path(os.environ.get("AEGIS_AUDIT_JUDGMENTS", "data/aegis/audit_judgments.jsonl"))
_DOWNSTREAM_STORE = Path(os.environ.get("AEGIS_DOWNSTREAM_STORE", "data/aegis/downstream_quality.jsonl"))
```

---

### Step 9 — Mount refit router in `server.py` (EDIT)

```python
from aegis.api import refit as refit_mod
# ...
app.include_router(refit_mod.router)
```

---

### Step 10 — Frontend refit proxy routes (NEW)

#### `frontend/src/app/api/refit/trigger/route.ts`
```typescript
export async function POST(request: NextRequest) {
  const { specialty } = await request.json();
  const data = await apiFetch<RefitTriggerResponse>(
    `/v1/refit/trigger?specialty=${specialty ?? "basic_research"}`,
    { method: "POST" }
  );
  return NextResponse.json(data);
}
```

#### `frontend/src/app/api/refit/status/route.ts`
```typescript
export async function GET(request: NextRequest) {
  const specialty = request.nextUrl.searchParams.get("specialty") ?? "basic_research";
  const data = await apiFetch<RefitStatusResponse>(`/v1/refit/status?specialty=${specialty}`);
  return NextResponse.json(data);
}
```

---

## Part 3 — HITL Review Queue in Main Server

### Step 11 — `src/aegis/api/hitl.py` (NEW)

```python
router = APIRouter(prefix="/v1/hitl", tags=["hitl"])

class DecideRequest(BaseModel):
    decision: Literal["confirm", "reject", "split"]
    reviewer: str = "system"

@router.get("/next")
def get_next_review_item() -> dict[str, Any]:
    """Return oldest pending review item or {"item": null}."""
    queue = ReviewQueue(db_path=_db_path())
    try:
        item = queue.next()
        return {"item": item.model_dump() if item else None}
    finally:
        queue.close()

@router.post("/{item_id}/decide")
def decide_review_item(item_id: str, body: DecideRequest) -> dict[str, str]:
    """Record a confirm/reject/split decision."""
    queue = ReviewQueue(db_path=_db_path())
    try:
        queue.decide(item_id, ReviewDecision(body.decision), reviewer=body.reviewer)
        return {"status": "ok", "item_id": item_id, "decision": body.decision}
    finally:
        queue.close()

@router.get("/stats")
def get_hitl_stats() -> dict[str, int]:
    """Return pending and reviewed counts."""
    queue = ReviewQueue(db_path=_db_path())
    try:
        return {
            "pending": queue.pending_count(),
            "reviewed": len(queue.get_decisions()),
        }
    finally:
        queue.close()
```

`_db_path()` reads `AEGIS_DB_PATH` env var (same as rest of app).

---

### Step 12 — Mount hitl router in `server.py` (EDIT)

```python
from aegis.api import hitl as hitl_mod
# ...
app.include_router(hitl_mod.router)
```

---

### Step 13 — Frontend HITL proxy routes (NEW)

#### `frontend/src/app/api/hitl/next/route.ts`
```typescript
export async function GET() {
  const data = await apiFetch<{ item: ReviewItem | null }>("/v1/hitl/next");
  return NextResponse.json(data);
}
```

#### `frontend/src/app/api/hitl/[itemId]/decide/route.ts`
```typescript
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ itemId: string }> }
) {
  const { itemId } = await params;
  const body = await request.json();
  const data = await apiFetch(`/v1/hitl/${itemId}/decide`, { method: "POST", body });
  return NextResponse.json(data);
}
```

#### `frontend/src/app/api/hitl/stats/route.ts`
```typescript
export async function GET() {
  const data = await apiFetch<{ pending: number; reviewed: number }>("/v1/hitl/stats");
  return NextResponse.json(data);
}
```

---

## Part 4 — Interactive Weight Re-ranking (WeightSliderPanel)

### Step 14 — `frontend/src/app/results/[id]/page.tsx` (EDIT)

**Strategy**: client-side re-ranking using already-available per-candidate F-scores. No new backend
endpoint needed.

Add state for custom exponents:
```typescript
const [customExponents, setCustomExponents] = useState<Record<string, number> | null>(null);
```

Add re-ranking function (uses existing F1-F6 score maps in query result):
```typescript
function rerankCandidates(
  candidates: Candidate[],
  exponents: Record<string, number>,
  result: QueryResult,
): Candidate[] {
  const alpha = exponents["alpha"] ?? result.weight_vector.exponents.alpha;
  const beta  = exponents["beta"]  ?? result.weight_vector.exponents.beta;
  const gamma = exponents["gamma"] ?? result.weight_vector.exponents.gamma;

  return [...candidates].sort((a, b) => {
    const scoreA =
      Math.pow(result.f1_scores[a.uuid] ?? 0.5, alpha) *
      Math.pow(result.f4_scores[a.uuid] ?? 0.5, beta) *   // topical fit proxy
      Math.pow(result.recency_scores?.[a.uuid] ?? 0.5, gamma);
    const scoreB =
      Math.pow(result.f1_scores[b.uuid] ?? 0.5, alpha) *
      Math.pow(result.f4_scores[b.uuid] ?? 0.5, beta) *
      Math.pow(result.recency_scores?.[b.uuid] ?? 0.5, gamma);
    return scoreB - scoreA;
  });
}
```

Pass to `WeightSliderPanel`:
```typescript
<WeightSliderPanel
  weights={result.weight_vector.weights}
  exponents={customExponents ?? result.weight_vector.exponents}
  onExponentsChange={setCustomExponents}
/>
```

Display `rerankCandidates(result.candidates, customExponents, result)` when `customExponents` is set.

### Step 15 — `WeightSliderPanel.tsx` (EDIT)

Add a reset button alongside the existing sliders:
```typescript
<button
  onClick={() => onExponentsChange(defaultExponents)}
  className="text-xs text-slate-400 hover:text-slate-200"
>
  Reset to trained
</button>
```

The `onExponentsChange` callback already exists — no structural change needed.
The parent now consumes it and re-renders the ranked list.

---

## Verification

### 1. Core ingestion test
```bash
uv run pytest src/aegis/ingestion/converters_test.py src/aegis/ingestion/record_ingester_test.py -v
```

### 2. Backend smoke test
```bash
uv run uvicorn aegis.api.server:app --reload --port 8000
# POST /v1/queries — logs should show "Ingestion [pubmed]: X new, Y merged"
# GET /v1/queries/{id} — should return candidates > 0
# GET /v1/refit/status — should return current version + pending count
# POST /v1/refit/trigger?specialty=basic_research — should return report
# GET /v1/hitl/stats — should return {pending: N, reviewed: 0}
# POST /v1/feedback/tasks/{id}/outcomes — should return 201
```

### 3. Frontend smoke test
```bash
cd frontend && npm run dev
# Submit query → candidates appear in results
# Open FeedbackModal → submit all 3 metrics → 201 response
# WeightSliderPanel → drag alpha slider → candidate order updates live
# GET /api/refit/status → returns data
# GET /api/hitl/stats → returns data
```

### 4. Full feedback loop test (manual)
```
1. Submit query → get candidates
2. POST /v1/feedback/tasks/{id}/outcomes with candidate scores
3. POST /v1/refit/trigger?specialty=basic_research
4. Response shows new exponents + deployment_decision
5. GET /v1/refit/status → version bumped
```

---

## Production Readiness Checklist

- [x] Live ingestion from 4 sources (PubMed, Reporter, CT.gov, OpenAlex)
- [x] Strong-key dedup (ORCID, eRA Commons) with in-memory cache
- [x] Merge logic: evidence trail, MeSH, name variants — all bounded
- [x] Retry + exponential backoff on DB write conflicts
- [x] Ingester never raises to caller — errors logged and counted
- [x] NCBI API key passed to PubMedClient
- [x] Correct API method names (fetch_grants_by_topic, fetch_studies_by_condition)
- [x] Feedback endpoint mounted and receiving full TaskOutcomeRequest
- [x] Weight refit triggerable via API (POST /v1/refit/trigger)
- [x] ColdStartGuard gates deployment (CI width, convergence, N >= 20)
- [x] HITL review queue accessible via /v1/hitl/* endpoints
- [x] WeightSliderPanel drives live client-side re-ranking
- [x] All new backend routes return structured Pydantic responses
- [x] All frontend proxy routes use existing `apiFetch` utility
- [x] No new ML components built — only wiring

---

## Build Evidence

Generated by spec-updater on 2026-04-28.

### Validation Command Results

| # | Command | Result | Output |
|---|---------|--------|--------|
| 1 | `uv run pytest src/aegis/ingestion/converters_test.py src/aegis/ingestion/record_ingester_test.py -v` | PASS | 24 passed in 0.89s (16 converter tests + 8 ingester tests) |
| 2 | `uv run python -c "from aegis.api.server import app; from aegis.api.refit import router; from aegis.api.hitl import router; from aegis.ingestion.converters import pubmed_record_to_candidates; print('OK')"` | PASS | `OK` |
| 3 | `uv run python -c "import inspect; from aegis.pipeline.orchestrator import QueryPipeline; src = inspect.getsource(QueryPipeline._fetch_source); assert 'fetch_grants_by_topic' in src; assert 'ingester.ingest' in src; print('OK')"` | PASS | `OK` |
| 4 | `cd frontend && npx tsc --noEmit` | PASS | No errors (clean exit) |

### Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All ingestion tests pass | PASS | 24/24 tests passed: 16 in `converters_test.py`, 8 in `record_ingester_test.py` |
| All Python imports succeed (server, refit, hitl, feedback, converters, ingester) | PASS | Validation command #2 imports all modules and prints `OK` |
| Server routes include /v1/feedback, /v1/refit, /v1/hitl | PASS | Route listing confirms `/v1/feedback/tasks/{task_id}/outcomes`, `/v1/refit/trigger`, `/v1/refit/status`, `/v1/hitl/next`, `/v1/hitl/{item_id}/decide`, `/v1/hitl/stats` |
| Orchestrator uses correct method names and wires ingestion | PASS | Validation command #3 asserts `fetch_grants_by_topic` and `ingester.ingest` present in `_fetch_source` source |
| Frontend TypeScript compiles | PASS | `npx tsc --noEmit` exits cleanly with no errors |
| FeedbackModal sends full TaskOutcomeRequest payload | PASS | `FeedbackModal.tsx` sends `query_specialty`, `query_mesh_terms`, `candidates`, `fleiss_kappa`, `accept_rate`, `consensus_rate` |
| WeightSliderPanel has reset button | PASS | `WeightSliderPanel.tsx` contains "Reset to trained" button calling `onExponentsChange(defaultExponents)` |
| Results page supports interactive re-ranking | PASS | `results/[id]/page.tsx` uses `useMemo` with `exponents` state to client-side re-rank via `score_components.Q/C/R` powered by `setExponents` callback from `WeightSliderPanel` |
