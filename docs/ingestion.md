# Aegis Ingestion Pipeline

## One-paragraph summary

When you submit a query on the Aegis frontend, the system translates your natural-language description into a set of MeSH (Medical Subject Heading) terms, classifies what *kind* of expertise you are looking for, then simultaneously reaches out to four public biomedical databases — PubMed, NIH Reporter, ClinicalTrials.gov, and OpenAlex. Every person returned by those databases is converted into a standardised `Candidate` record and merged with anyone already known (deduplication). Each candidate is then scored across six evidence dimensions (F1–F7), ranked by a weighted formula, and the top-K results are returned. The whole thing runs asynchronously in the background so the page does not hang while you wait.

---

## Part 1 — The Query Form: What Every Control Does

### Task Description *(required)*

The free-text box. Write a plain-English description of the expertise you need — e.g., *"KRAS G12C inhibitor medicinal chemist with ADMET experience"* or *"clinical trial PI for Phase 2 pancreatic cancer immunotherapy"*. This text drives three things simultaneously:

1. **MeSH expansion** — the text is sent to Claude (or MetaMap as a fallback) to produce a list of formal NLM MeSH descriptor terms. These terms are what actually get passed to CT.gov and NIH Reporter searches.
2. **Query classification** — the same text is keyword-scanned to choose a scoring weight vector (see below).
3. **Topical fit scoring** — later in the pipeline, every candidate's evidence trail and MeSH descriptors are matched against both the raw query words *and* the expanded MeSH terms to produce a relevance score.

As soon as you type more than five characters the form silently fires a `POST /api/queries/classify` call and shows a live preview of what the system thinks your query type is.

---

### Query Type Badge *(auto-detected, overridable)*

A small badge appears to the right of the task description label showing the detected query type and a confidence percentage. Four types exist:

| Type | What it means | Dominant weight |
|------|---------------|-----------------|
| **Basic Research** | Bench scientists, publication-heavy academics | F1 RCR (40%) |
| **Drug Discovery** | Medicinal chemists, structural biologists, DMPK/ADMET | F5 Translational (50%) |
| **Clinical Trial PI** | Investigators who run trials, enrolled patients | F3 Leadership + F7 Clinician (25% each) |
| **Policy / Epi** | Epidemiologists, public-health researchers | F1 + F3 Leadership balanced |

Detection is keyword-based: the classifier scans the lowercased query for curated word sets (`inhibitor`, `ic50`, `sar` → drug discovery; `phase 2`, `randomized`, `irb` → clinical trial PI; `incidence`, `prevalence`, `social determinants` → policy/epi). If nothing matches, it defaults to basic research with 50% confidence.

You can click the badge to override the detected type. This does two things: it changes which weight vector is used when your query is submitted, and it updates the F-score weight display live in the Weight Configuration panel.

---

### Expanded MeSH Terms Panel *(appears after typing)*

Once classification runs, this panel shows the MeSH terms the system has already expanded your query into. These are the terms that will be fed to CT.gov and NIH Reporter. You can:

- **Remove a term** by clicking the × on its chip — useful if the expansion grabbed something off-topic.
- **Add a term** by typing in the input and pressing Enter — useful if you know the exact MeSH heading you want.

Any edits here become the `mesh_override` sent with the query. If this panel has terms in it, the pipeline skips LLM/MetaMap expansion entirely and uses exactly what you provided.

---

### Weight Configuration Panel *(collapsed by default)*

Expand this to see two sections:

**Exponents (α, β, γ)** — These are the powers in the ranking formula:

```
Score(c) = Integrity(c) × Quality(c)^α × TopicalFit(c,q)^β × Recency(c)^γ
```

| Slider | What it amplifies | Default per type |
|--------|-------------------|-----------------|
| **Quality (α)** | How strongly a candidate's publication/funding quality lifts their score | 0.7–0.8 |
| **Topical Fit (β)** | How strongly matching the query terms lifts their score | 1.0 (all types) |
| **Recency (γ)** | How strongly recent activity lifts their score | 0.3–0.5 |

Raising α above 1.0 makes the ranking more "winner takes all" by quality. Setting it close to 0 makes quality nearly irrelevant and lets topical fit dominate. Raising γ past 1.0 strongly penalises researchers who have not published or received grants recently.

**F-score weights** — Shown as read-only bars derived from the selected weight vector (e.g., drug discovery has F5 Translational at 50%). These are the weights that go into computing a candidate's composite quality percentile before the exponent is applied. They are trained values, not user-adjustable at query time (the "Reset to trained" button restores exponents if you've moved the sliders).

---

### Population Selector *(optional)*

A dropdown with four choices plus Auto-detect:

- **Auto-detect** — system uses the query-type classifier result.
- **Translational** — maps to the drug discovery weight vector.
- **Drug Discovery** — same as above.
- **Clinician** — forces the clinical trial PI weight vector (includes F7).

In practice this mostly duplicates what the query type badge already does. It exists so that a user who knows their target population can force it regardless of the keyword classifier's guess. If left blank, it has no effect.

---

### Number of Results (K) *(slider, 5–100, default 20)*

How many ranked candidates to return. The pipeline always scores all candidates found across all sources; K only affects how many appear in the results list. Setting K high (80–100) is useful for broad exploratory searches. Setting it low (5–10) is useful when you want only the most confident matches and plan to shortlist from there.

---

### Advanced Options *(collapsed by default)*

**MeSH Override Tags** — A tag-input that lets you type raw MeSH terms and add them one at a time. If you've already edited the Expanded MeSH Terms panel above, this is redundant — both feed into `mesh_override` on the submitted request. The distinction is minor: the panel above shows what the classifier *auto-detected*, while this input starts empty and is purely manual. If both have terms, the expanded panel's values win (the form prefers `expandedTerms` over `meshOverride` when both are non-empty).

**Cutoff Strategy** — A text field accepting values like `score_threshold` or `elbow`. Currently stored on the request but not actioned by the pipeline backend — it is a placeholder for a future feature that would automatically trim the tail of low-confidence results rather than returning the full K.

---

## Part 2 — From Submit to Results: Step by Step

### Step 0 — Submit

The form fires `POST /api/queries` (the Next.js proxy route), which forwards to `POST /v1/queries` on the Fly.io backend. The backend immediately:

1. Validates the JWT in the `Authorization: Bearer …` header.
2. Generates a UUID as the `job_id`.
3. Inserts a `jobs` row with `status = "in_progress"` into DuckDB.
4. Schedules `_run_pipeline(job_id, body, customer)` as an asyncio background task.
5. Returns HTTP **202** with `{ "job_id": "…", "status": "in_progress" }`.

The frontend receives the 202, extracts `job_id`, and navigates to `/jobs/{job_id}`. The pipeline is now running asynchronously — the HTTP response was already sent.

---

### Step 1 — Query Expansion

The background pipeline calls `LlmQueryExpander.expand(task_description)`.

**If `mesh_override` was provided** (from the MeSH terms panel): skip expansion entirely, use those terms directly.

**Otherwise:**

1. Try Claude via the Anthropic API using a tool-use call:
   - System prompt: *"You are a biomedical query expansion assistant. Only use exact MeSH descriptor headings from the NLM vocabulary."*
   - Tool schema forces a structured `{ "mesh_terms": [...], "reasoning": "..." }` response.
   - Uses the model specified in `LlmExpansionConfig` (defaults to claude-haiku).
2. If Claude is unavailable or fails (no `ANTHROPIC_API_KEY`, network error, tool parsing error): fall back to **MetaMap stub**.
   - The MetaMap stub extracts candidate terms from the query (individual tokens + two-word bigrams, minus stopwords), then hits the NLM MeSH Lookup API (`id.nlm.nih.gov/mesh/lookup/label`) for each term.
   - If the NLM API also fails or returns nothing: final fallback is title-casing every word in the query that is longer than 3 characters. This produces low-quality terms (confidence 0.3) but keeps the pipeline running.

The result is a list like `["Neoplasms", "Proto-Oncogene Proteins p21(ras)", "Antineoplastic Agents"]`.

---

### Step 2 — Query Classification

`QueryClassifier.classify(task_description)` scans the lowercased query against three keyword frozensets (drug discovery, clinical trial, policy/epi). The type with the most keyword hits wins; ties go to basic research. This determines which YAML weight vector is loaded from `config/aegis/weights/`.

The resulting `WeightVector` object contains:
- `weights` — per F-family coefficients (sum to 1.0)
- `exponents` — default α/β/γ values
- `exponent_bounds` — min/max ranges for the weight slider UI

If the user overrode the query type via the badge, `query_type_override` is sent in the body and the pipeline uses that type's weight file instead.

---

### Step 3 — Source Fetches (parallel)

`asyncio.gather` launches four coroutines simultaneously. Each runs independently; progress is emitted to the SSE stream as soon as each one finishes (not after all four finish — this was a bug fixed in April 2026, see Part 4).

#### PubMed
- Client: `PubMedClient` using NCBI E-utilities (`esearch` + `efetch`).
- Search term: the raw `task_description` text.
- What it returns: paper records including PMID, title, authors (with ORCID when present), MeSH descriptors, publication date.
- Cap: first 200 records.
- What it produces after conversion: one `Candidate` per **last author** of each paper (senior author heuristic). First author used as fallback if no last-author flag is set. Each candidate gets the paper's PMID in `artifact_refs.pmids` and the paper's MeSH terms as `mesh_descriptors`.

#### NIH Reporter
- Client: `ReporterClient` hitting `api.reporter.nih.gov/v2/projects/search`.
- Search term: the expanded MeSH terms are passed as `spending_categories_desc`.
- **Known mismatch**: NIH Reporter uses its own RCDC (Research, Condition, and Disease Categorization) taxonomy, not MeSH. When MeSH terms are passed as RCDC categories, the API often returns all grants (the full ~2.9M grant corpus) because no category matches — the grants are not wrong, just not filtered by topic. This is a known open issue; the source still contributes candidates but they are topic-agnostic.
- Cap: first 200 records.
- What it produces: one `Candidate` per PI listed on the grant. Each candidate gets the grant's project number in `artifact_refs.grant_ids` and RCDC categories as `mesh_descriptors`.

#### ClinicalTrials.gov
- Client: `CtgovClient` hitting `clinicaltrials.gov/api/v2/studies`.
- Search term: MeSH terms joined as `"term1 OR term2"` passed to `query.cond`.
- What it returns: study records including NCT ID, title, phase, status, overall officials, and site-level contacts.
- Cap: first 200 records.
- What it produces: one `Candidate` per **PI-role investigator** (`PRINCIPAL_INVESTIGATOR` → `PI`). Studies with no PI-flagged official produce zero candidates. Each candidate gets the NCT ID in `artifact_refs.nct_ids`.

#### OpenAlex Works
- Client: `OpenAlexClient` hitting `api.openalex.org/works`.
- Search term: the raw `task_description` as a free-text `search` parameter (most permissive of all four sources).
- Uses the polite pool (adds `mailto` param) allowing 10 req/s.
- What it returns: work records including OpenAlex ID, DOI, PMID (if linked), authorship list with positions and ORCIDs, MeSH terms, cited-by count.
- Cap: first 200 records.
- What it produces: one `Candidate` per **last-position author**. If no last-position author is flagged, falls back to the final element in the authorship list. Each candidate gets the PMID in `artifact_refs.pmids` (if available) and MeSH terms from the work's `mesh` array.

---

### Step 4 — Record Conversion

Each raw API record is converted to a standardised `Candidate` model by a converter function in `src/aegis/ingestion/converters.py`. The `Candidate` schema holds:

- `uuid` — deterministic 32-hex ID derived from the strongest available identifier: ORCID → ERA Commons ID → SHA-256(normalised name + affiliation prefix).
- `strong_keys` — `{"orcid": "…"}` or `{"era_commons": "…"}` when available.
- `name_variants` — list of name forms seen for this person.
- `affiliations` — list of `AffiliationSpan` records (institution, ROR ID if resolvable, country, confidence).
- `artifact_refs` — `{pmids, nct_ids, grant_ids, patent_ids}`.
- `mesh_descriptors` — MeSH terms from the source record.
- `evidence_trail` — human-readable strings like `"Published 'KRAS inhibitor…' (PMID:33521700, 2021-01-15)"` or `"PI on NCT04303780: 'Phase 2 study…' (Phase 2, RECRUITING)"`.
- `linkage_confidence` — how confident we are this is a real, unique person (0.60–0.93 depending on whether strong keys are present).
- `last_updated_per_source` — `{"pubmed": datetime}` etc., used for recency scoring.

---

### Step 5 — Identity Resolution & Deduplication

Every converted `Candidate` is passed to `RecordIngester.ingest()`. The ingester's job is to decide: *is this person already in the database, or are they new?*

**Pass 1 — Strong-key match (exact)**
If the incoming candidate has an ORCID or ERA Commons ID, the ingester looks up that key in the `strong_keys` DuckDB table. A hit means we've seen this person before — the new record is merged into the existing one (artifact refs unioned, evidence trail appended, MeSH terms merged).

**Pass 2 — Probabilistic name+affiliation match (Fellegi-Sunter)**
If no strong key matches, the ingester runs `ProbabilisticLinker.link()` against an in-memory snapshot of all candidates seen so far in this pipeline run. The linker scores five features:

| Feature | Weight | How measured |
|---------|--------|--------------|
| Name similarity | 35% | fuzzy token-set ratio (thefuzz) against all name variants |
| Affiliation similarity | 25% | fuzzy ratio on institution string, optionally ROR-normalised |
| Co-author overlap | 15% | fraction of shared co-author names |
| MeSH overlap | 15% | Jaccard similarity of MeSH descriptor sets |
| Time continuity | 10% | gap in years between last known activity |

A weighted sum ≥ 0.95 triggers **auto-link** (same person, merge). Between 0.50 and 0.95 the pair is flagged for **HITL review** in the human-in-the-loop queue. Below 0.50 the incoming record is treated as a new, distinct person.

**If no match found**: the candidate is inserted as a new row in `candidates`. The in-memory snapshot is updated so the next record in the same pipeline run can match against it.

**Merge semantics** when a match is found:
- Artifact refs, name variants, MeSH descriptors: set-union, capped at configured maximums.
- Evidence trail: append new items, deduplicated, max 20 items.
- `linkage_confidence`: take the maximum.
- `last_updated_per_source`: new timestamps win.

---

### Step 6 — Scoring (F1–F7)

After all sources have been ingested, the pipeline loads every candidate from DuckDB and computes scores.

**Raw F-scores** (computed per candidate, then percentile-ranked within the cohort):

| Score | What it measures | Formula |
|-------|-----------------|---------|
| **F1** | Research output quality | `min(1.0, pmid_count/20 + nct_count/15)` |
| **F2** | Funding track record | `min(1.0, grant_count/5)` |
| **F3** | Leadership signals | Evidence trail mentions of "PI", "lead", "principal" — `min(1.0, hits/3)` |
| **F4** | Apex roster / awards | Evidence trail mentions of "apex", "fellow", "award" — `min(1.0, hits/2)` |
| **F5** | Translational impact | `min(1.0, (trial_count + patent_count)/5)` |
| **F6** | Lineage / breadth | Unique MeSH descriptor count — `min(1.0, unique_mesh/10)` |
| **F7** | Clinician-specific | Only computed when weight vector includes `f7_clinician`; currently a pass-through of F3 for clinician queries |

Raw scores are converted to **within-cohort percentiles** (rank / N). This means a researcher with 5 publications scores higher if the query only found 50 candidates than if it found 5,000.

The per-family percentiles are fed to `QualityPrior.compute_percentiles()`, which weights them according to the selected weight vector and produces a single quality percentile per candidate.

**Topical fit** is computed separately from F-scores. For each candidate:
```
text = name_variants + mesh_descriptor_strings + evidence_trail
hits = count of query words (>3 chars) found in text
mesh_hits = count of expanded MeSH terms matching candidate's mesh_descriptors
topical_fit = min(1.0, (hits + mesh_hits×2) / (query_word_count + mesh_term_count))
```

**Recency** is based on `last_updated_per_source`: days since the most recent source update, decaying linearly over 5 years (1825 days) from 1.0 to 0.1.

---

### Step 7 — Integrity Hard Gate

Each candidate is checked against `HardGateResult`. Currently the gate is stubbed to `is_zero=False` for all candidates (no disqualifications). The structure exists to support future rules (e.g., LEIE exclusion list matches, retraction flags) that would set `is_zero=True` and remove a candidate from ranking entirely.

---

### Step 8 — Ranking

`Ranker.rank()` applies the full formula to every non-zero candidate:

```
Score(c,q) = Integrity(c) × Quality(c)^α × TopicalFit(c,q)^β × Recency(c,q)^γ
```

Where α/β/γ come from the weight vector (or from user-adjusted sliders if sent in the request). Candidates are sorted descending by this score and the top K are returned as a `RankedList`.

Each ranked candidate includes a `ComponentBreakdown` showing the individual Q, T, R components so the results UI can display why someone ranked where they did.

---

### Step 9 — Bootstrap Variance Bands

`Bootstrap.estimate()` runs 200 Monte Carlo samples, drawing (α, β, γ) from a multivariate normal distribution centred on the weight vector's defaults, with standard deviation proportional to the `exponent_bounds` range. For each sample it re-ranks all candidates and records each candidate's position.

The output is a `ScoreBand` per candidate: `{ p10, p50, p90 }` — the 10th, 50th, and 90th percentile scores across the 200 samples. A wide band means the candidate's ranking is sensitive to small changes in the weight exponents (uncertain). A narrow band means they rank consistently regardless of which weighting you use.

---

### Step 10 — Privacy Gate

`PrivacyGate` runs each candidate through:
1. `PHIScanner` — scans evidence trail text for patterns matching protected health information (SSN, DOB, direct patient identifiers).
2. `DemographicBlocklist` — rejects candidates flagged in the demographic exclusion list.
3. `OptOutStore` — checks `data/aegis/opt_out.jsonl` for explicit opt-outs by UUID.

Candidates that fail any check are dropped from the final list before the result is written.

---

### Step 11 — Results Written, Job Marked Complete

The ranked list is serialised and written to the `queries` table in DuckDB (via `QueryStore.save()`). The job row is updated to `status = "complete"` with duration and candidate count. A sentinel `None` is pushed to the SSE queue for this job ID, which causes the stream endpoint to emit `event: complete\ndata: {}\n\n` and close the connection.

The frontend receives the `complete` SSE event, calls `fetchJob()` again to get final status, and displays a "View Results →" button linking to `/results/{job_id}`.

---

## Part 3 — Sources Deep-Dive

### What each source contributes to a candidate's evidence

| Source | Artifact ref | MeSH source | Evidence trail text |
|--------|-------------|-------------|---------------------|
| PubMed | `pmids` | Paper's own MeSH terms (precise) | Paper title + PMID + date |
| NIH Reporter | `grant_ids` | RCDC categories (broad, not MeSH) | Grant number + fiscal year + dollar amount |
| CT.gov | `nct_ids` | Study conditions freetext (fallback) or derivedSection meshes | Study title + phase + status |
| OpenAlex | `pmids` (when linked) | Work's `mesh` array | OpenAlex ID + title + citation count |

### Source quirks worth knowing

**PubMed — ORCID coverage is sparse.** Most records have no ORCID in the author metadata. This means most PubMed-sourced candidates are identified by `sha256(normalised_name + affiliation)` — a deterministic UUID that is stable within a session but can diverge across sessions if the affiliation string changes slightly (e.g., "Harvard" vs "Harvard Medical School").

**NIH Reporter — RCDC ≠ MeSH.** The `spending_categories_desc` filter expects category strings like "Cancer" or "Rare Diseases" from the RCDC taxonomy. When the pipeline passes MeSH terms like "Proto-Oncogene Proteins p21(ras)", the API finds no matching category and returns the entire grant corpus (~2.9 million rows). The 200-record cap means the pipeline gets 200 effectively random recent grants. This is a known open issue — Reporter still contributes candidates, they just are not topically filtered.

**CT.gov — PI role coverage is inconsistent.** Many trials list `STUDY_DIRECTOR` or `STUDY_CHAIR` rather than `PRINCIPAL_INVESTIGATOR` in the officials module. The converter only extracts PI-role investigators. Site-level contacts are also extracted but their roles must be in the role map to be included. A substantial fraction of studies produce zero candidates because no PI is flagged.

**OpenAlex — broadest retrieval, most duplicates.** Because it uses free-text search on the raw query (not MeSH terms), OpenAlex casts the widest net and often returns the same people as PubMed (same papers, same authors). After deduplication those records are merged, enriching PubMed candidates with citation counts and ORCIDs when OpenAlex has them.

---

## Part 4 — Design Decisions and Honest History

### Why DuckDB?

The original design evaluated Postgres, SQLite, and DuckDB. DuckDB was chosen because the scoring and ranking steps involve columnar analytics (percentile calculations over 600+ candidates, join-heavy MeSH lookups), which DuckDB handles significantly faster than row-oriented SQLite. The tradeoff accepted was single-writer concurrency: DuckDB's file mode allows multiple readers but only one writer at a time. This is fine for a single-machine deployment but will need to change if the backend is ever scaled horizontally (see `deploy.md` known gotcha #10).

### Why async ingestion with a shared ingester?

An early design ran each source in a separate process and had them write to DuckDB concurrently. This immediately hit DuckDB's write-lock constraint — sources would fail with serialisation errors under contention. The current design runs all four source coroutines on the same asyncio event loop sharing a single `RecordIngester` instance (and therefore a single DuckDB connection). Because asyncio is single-threaded, only one coroutine is active at any `await` — in practice there is no actual concurrency on the DuckDB write path, just interleaving on the HTTP-fetch awaits.

### Why probabilistic linking instead of exact deduplication?

Biomedical researcher names are notoriously ambiguous across databases. A person may appear as "J. Smith", "John Smith", "John D. Smith", and "J.D. Smith" across PubMed, Reporter, and CT.gov, and each database uses a different affiliation string. Exact-match deduplication on name alone creates thousands of spurious duplicates. The Fellegi-Sunter approach — weighting name similarity, affiliation, co-author overlap, MeSH overlap, and time continuity — was chosen because it handles the messiness of real-world biomedical identity. The 0.95 auto-link threshold is intentionally conservative to avoid merging different people; anything below that threshold goes to the HITL queue for human review.

### Why was `openalex_grants` removed?

`openalex_grants` was added to supplement the international grant data lost when ERC/MRC/CIHR/KAKEN direct APIs stopped working. It used OpenAlex's `grants.funder` filter to find works associated with specific funders. Two bugs were present simultaneously: (1) the orchestrator loop fetched records into `_record` but never called `ingester.ingest()` — zero candidates were ever written to the DB; (2) the `grants.funder` filter in OpenAlex returns very few works because grant metadata is only present on a small fraction of works. The source was removed rather than fixed because it provided no incremental value over `openalex_works`, which already finds the same researchers through publication search.

### Why did source progress cards not show all sources?

There were two independent bugs:

**Bug 1 — Batch emission.** `asyncio.gather` collected all four source results, *then* the loop called `progress_callback` once per source in sequence. From the browser's perspective all four cards appeared at the same instant at the end of the pipeline run — or not at all if the SSE connection had already closed. Fixed by moving the callback call inside each source's coroutine so it fires the moment that source finishes.

**Bug 2 — SSE queue race condition.** `push_event()` silently discarded events when no SSE subscriber had connected yet (the queue didn't exist). The pipeline starts immediately after the HTTP 202 is returned. If a fast source (e.g., OpenAlex fetching one page in ~1 second) completed before the browser opened the EventSource connection (~2–3 seconds of page navigation), its event was lost. Fixed by having `push_event` pre-create the queue unconditionally so events are buffered even before the browser subscribes.

**Bug 3 — Vercel proxy timeout.** The SSE proxy route in Next.js had no `maxDuration` export. Vercel serverless functions time out after 10–60 seconds depending on plan tier. A pipeline that takes 90 seconds would cause the proxy to close the connection mid-stream, triggering the frontend's `error` SSE handler which closed the EventSource without reconnecting or calling `fetchJob()`. Fixed by adding `export const maxDuration = 300` to the stream route.

### Why does scoring favour PubMed candidates?

The scoring is not source-agnostic by design — it measures *evidence quality*, and PubMed provides the richest evidence signals. A PubMed candidate has: (a) a paper title in their evidence trail that contains query-relevant words (high topical fit); (b) proper NLM MeSH terms as mesh descriptors that match the expanded query terms (high topical fit multiplier); (c) citation count available via iCite (F1 signal). NIH Reporter candidates have grant dollars and RCDC categories; CT.gov candidates have trial titles. These signals are less textually aligned with the query. The intent is that cross-source merging compensates: if a researcher appears in both PubMed and Reporter, their merged record has both publications *and* grants, scoring higher on both F1 and F2. The places where this breaks down are for researchers who appear only in Reporter or only in CT.gov — they will tend to rank lower than equally qualified researchers who have publication records, because the topical fit calculation is heavily text-driven.
