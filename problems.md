# Aegis — Known Problems & Fixes

## Problem 1: Only PubMed candidates appear in results (2026-04-28)

### Symptom
All queries returned only PubMed-sourced candidates. CT.gov, NIH Reporter, and OpenAlex
candidates were fetched by the pipeline (200 records each) but never appeared in the top-k
ranked output.

### Root Causes

**1. CT.gov MeSH terms always empty**
The CT.gov v2 API does not include `derivedSection.conditionBrowseModule` in default responses.
The converter read `record.conditions_mesh` (sourced from that module) which was always `[]`.
With no mesh descriptors, the topical fit formula gave these candidates a score of ~0.136:

```
topical_fit = (text_hits + mesh_hits * 2) / (len(query_words) + len(query_mesh_set))
            = (2 + 0) / 14  ≈ 0.136
```

_Fix:_ `converters.py / study_record_to_candidates` — fall back to `record.conditions_freetext`
(the plain-text condition names e.g. "Non-Small Cell Lung Cancer") when `conditions_mesh` is empty.

**2. F1 (publication quality) was zero for CT.gov-only candidates**
F1 was computed as `min(1.0, pub_count / 20.0)` where `pub_count = len(artifact_refs.pmids)`.
CT.gov PIs have no PMIDs linked, giving F1 = 0. The final ranker score is
`Q^alpha * C^beta * R^gamma` — with quality_percentile ≈ 0 the entire product collapsed to ~0,
burying CT.gov candidates below every PubMed candidate regardless of topical fit.

_Fix:_ `orchestrator.py / _compute_scores` — F1 now includes NCT IDs as a partial quality signal
for trial leadership (15 trials = max contribution, on top of the existing 20-pub scale):

```python
f1_raw = min(1.0, pub_count / 20.0 + nct_count / 15.0)
```

**3. OpenAlex candidates missing their PMIDs**
Many OpenAlex works have a PubMed ID in their `ids` field
(`ids.pmid = "https://pubmed.ncbi.nlm.nih.gov/XXXXX"`), but the source parser and converter
were not extracting it. This meant OpenAlex candidates got `pmids=[]`, losing F1 credit for
publications they actually had indexed.

_Fix:_ `openalex.py / _parse_work` — extract PMID from `ids.pmid` and store it on `OpenAlexWork`.
`converters.py / openalex_work_to_candidates` — populate `ArtifactRefBundle.pmids` with the PMID
when present, so identity linkage and F1 scoring work correctly.

**4. No identity cross-linking across sources (unresolved)**
A researcher who appears as both a CT.gov PI and a PubMed author is stored as two separate
candidates with different UUIDs because CT.gov investigator records rarely carry an ORCID or
ERA Commons ID. The PubMed version scores well; the CT.gov version scores near zero. They are
never merged by the Fellegi-Sunter linker.

_Status:_ Not fixed. Requires a name+affiliation fuzzy-match pass during ingestion, or
explicit ORCID lookup for CT.gov investigators via the ORCID API.

### Files Changed
| File | Change |
|------|--------|
| `src/aegis/ingestion/converters.py` | CT.gov: fall back to `conditions_freetext` for mesh descriptors |
| `src/aegis/ingestion/converters.py` | OpenAlex: populate `pmids` from `record.pmid` |
| `src/aegis/sources/openalex.py` | Add `pmid` field to `OpenAlexWork`; extract from `ids.pmid` |
| `src/aegis/pipeline/orchestrator.py` | F1: add NCT count as partial quality signal |

---

## Problem 2: GET /v1/queries/{id} returned 0 candidates (2026-04-28)

### Symptom
The results page always showed "No candidates found for this query" even for queries that
had been successfully run and stored in the database.

### Root Cause
`QueryStore.get()` returns the stored row with the key `candidate_scores`. The backend
endpoint `GET /v1/queries/{id}` returned this raw dict directly. The frontend proxy at
`/api/queries/[id]/route.ts` cast the response as `BackendQueryResponse` which expects
a `candidates` key. Since `candidates` was `undefined`, `(data.candidates ?? []).map(...)`
always returned `[]`.

Additionally, the stored `mesh_terms` key did not match the expected `mesh_override` field,
and `population` / `cutoff_strategy` were absent from the response shape.

### Fix
`src/aegis/api/server.py / get_query` — explicitly shape the response to match the frontend
interface:

```python
return {
    "id": query["id"],
    "candidates": query.get("candidate_scores") or [],  # was missing
    "mesh_override": query.get("mesh_terms"),           # was "mesh_terms"
    "population": None,
    "cutoff_strategy": None,
    ...
}
```

### Files Changed
| File | Change |
|------|--------|
| `src/aegis/api/server.py` | Rename `candidate_scores` → `candidates` in `get_query` response |

---

## Problem 3: Production JWT token expired (2026-04-28)

### Symptom
All API calls from both local frontend and Vercel returned `{"detail": "Invalid token"}`.

### Root Cause
The `AEGIS_API_TOKEN` in `frontend/.env.local` was generated with a 24-hour expiry and
had expired 2 days prior. Vercel production had a separate token that was still valid but
was generated against a different `AEGIS_JWT_SECRET` than the one currently loaded by the
local backend.

### Fix
- Regenerated local token using `create_token(..., expiry_hours=8760)` (1 year) via `load_dotenv()`
  to match the backend's active secret.
- Verified Vercel production token was still valid (expires 2027) and `AEGIS_API_URL` was
  correctly set to `https://aegis-backend.fly.dev`.

### Files Changed
| File | Change |
|------|--------|
| `frontend/.env.local` | Replaced expired `AEGIS_API_TOKEN` with 1-year token |
