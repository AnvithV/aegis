# Aegis — Walkthrough Narrative

> **Format:** Talk track + written reference. Each section is ~2–5 minutes of conversation.
> **Audience:** Mixed technical + product/strategy panel.
> **Demo URL:** https://aegis-frontend-rho.vercel.app
> **Demo query to run live:** "KRAS G12C inhibitor drug discovery for lung cancer"

---

## Act 1 — The Hook: Why I Didn't Start With LinkedIn (2 min)

> *Open with the reframe. This immediately signals first-principles thinking.*

The brief said LinkedIn. I want to explain why I started there and immediately moved somewhere else — because that decision drove every architectural choice downstream.

LinkedIn is the right first instinct for most talent searches. But for MDs and PhDs in translational and biomedical fields, LinkedIn is actually a **weak signal source** for three reasons:

1. **Coverage is sparse.** The researchers who matter most — the ones running NIH R01s, leading Phase 2 trials, filing patents — often don't maintain LinkedIn profiles. Their professional identity lives in PubMed author records, NIH Reporter grant databases, and ClinicalTrials.gov investigator rosters.

2. **Signal quality is low.** A LinkedIn profile is self-reported. A PubMed record is peer-reviewed and indexed by the National Library of Medicine. An NIH Reporter grant is federal funding data. A ClinicalTrials.gov PI entry is a legal regulatory record. These are objectively higher-quality signals for assessing scientific expertise than a self-written bio.

3. **Scraping is brittle.** Any pipeline built on LinkedIn scraping has a 6-month half-life before rate limits, ToS changes, or layout updates break it. The public biomedical APIs I used — NCBI E-utilities, NIH Reporter API v2, ClinicalTrials.gov API v2, OpenAlex — are stable, rate-limit-friendly, and explicitly designed for programmatic access.

So I built **Aegis**: a multi-source expert discovery and ranking engine that treats the five major public biomedical databases as its primary data layer, with LinkedIn as a future enrichment step, not the foundation.

---

## Act 2 — Problem Decomposition: What This Actually Requires (5 min)

> *Walk through the three hard sub-problems. This hits "clarity and reasoning behind methodology."*

To be direct about scope: Aegis IS the candidate discovery pipeline. It replaces a LinkedIn scraper with four higher-signal public data sources — PubMed, NIH Reporter, ClinicalTrials.gov, and OpenAlex — and returns a ranked, deduplicated candidate pool with contact emails from a natural language query. LinkedIn scraping is designed as an enrichment layer (see Act 6), not the foundation.

Expert discovery for scientific talent has three genuinely hard sub-problems that you don't encounter in standard recruiting:

### Hard Problem 1 — Multi-Source Identity Resolution

A single researcher appears differently across every database:

- **PubMed**: "J.A. Smith" at "Harvard"
- **NIH Reporter**: "John Smith" at "Harvard Medical School, Department of Medicine"
- **ClinicalTrials.gov**: "John A. Smith MD" at "Mass General Brigham"
- **OpenAlex**: "J. Smith" with an ORCID

These are the same person. Naive exact-match deduplication creates thousands of spurious duplicates. Naive fuzzy matching merges people who share common names.

Aegis uses a **two-tier identity resolver** modeled on the Fellegi-Sunter probabilistic record linkage framework:
- **Tier 1 (exact):** If an ORCID or eRA Commons ID is present, that's a confident match.
- **Tier 2 (probabilistic):** Weight five features — name similarity, institution similarity (ROR-normalized), co-author overlap, MeSH descriptor Jaccard, and time continuity — to produce a linkage score from 0 to 1.
  - Score ≥ 0.95 → auto-merge
  - Score 0.50–0.95 → flag for human review (the HITL queue)
  - Score < 0.50 → treat as distinct person

The asymmetry matters: a false positive merge (saying two different people are the same) corrupts every downstream score permanently. A false negative (saying the same person is two people) just slightly inflates the candidate count. You bias toward caution.

### Hard Problem 2 — Multi-Dimensional Expert Quality

"Who is the best expert?" has no single answer — it depends entirely on what you need them for.

A **medicinal chemist for drug discovery** and a **clinical trial PI** and a **basic research collaborator** are all "biomedical experts," but the evidence that makes each one excellent is completely different.

Aegis computes seven orthogonal evidence dimensions (F1–F7) for every candidate:

| Dimension | What it captures |
|-----------|-----------------|
| **F1 — Publication Impact** | NIH Relative Citation Ratio — field-normalized citation impact via iCite |
| **F2 — Funding Track** | Grant funding mass (NIH R01s, career awards) |
| **F3 — Leadership** | PI credits, editorial roles, society leadership |
| **F4 — Apex Recognition** | NAS/NAM/HHMI/Lasker membership |
| **F5 — Translational Bridge** | Patents filed, ChEMBL compounds, cross-domain activity |
| **F6 — Scientific Breadth** | Unique MeSH descriptors across all publications — breadth of research domain coverage |
| **F7 — Clinician-Specific** | Board certification, hospital tier, trial enrollment history |

These feed into a **multiplicative ranking formula** (not additive):

```
Score(c, q) = Integrity(c) × Quality(c)^α × TopicalFit(c, q)^β × Recency(c, q)^γ
```

The exponents α, β, γ are calibrated priors (α=0.7, β=1.0, γ=0.4) — chosen so topical relevance has linear influence while quality and recency are compressed, preventing high-quality candidates from completely overriding relevance. The Plackett-Luce refit loop (already built) will refine these per customer from actual ranking decisions. The multiplicative form means a candidate with zero integrity (LEIE exclusion, research misconduct finding) is hard-zeroed regardless of their quality score. A candidate who is brilliant but completely off-topic still ranks low because topical fit is in the exponent.

### Hard Problem 3 — Population-Specific Weighting

The same F1–F7 dimensions are computed for every candidate. But what you *weight* them changes by use case.

Drug discovery weights F5 (translational bridge) at 50% — because a researcher who has published on KRAS but never linked their work to a patent or clinical compound is less valuable than one who has.

Clinical trial PI weighting puts F7 (clinician-specific) and F3 (leadership) at 25% each — because what you need there is someone who has run trials and has institutional standing, not necessarily the highest-citation publication record.

These are stored as versioned YAML weight vectors. The query classifier auto-detects which vector to apply from your free-text query. You can override it.

---

## Act 2b — Working With Messy, Semi-Structured Data (4 min)

> *This directly addresses the first evaluation criterion. Make it concrete.*

Every source returns data in a different shape, with different levels of completeness, and with domain-specific quirks. Here are the five most interesting examples:

### 1. Name variants across sources (the hardest one)

The same researcher appears as:
- `"J.A. Smith"` in PubMed author metadata
- `"Smith, John A"` in NIH Reporter PI fields
- `"John A. Smith, MD"` in ClinicalTrials.gov officials
- `"J. Smith"` in OpenAlex with an ORCID attached

There's no universal ID. The pipeline normalizes all names via token-set fuzzy matching (using `thefuzz`), uses ORCID and eRA Commons ID as strong keys when available, and falls back to `SHA-256(normalized_name + affiliation_prefix)` as a deterministic UUID when no strong key is present.

### 2. Affiliation string drift

A researcher's institution field changes over their career and across databases. "MSKCC", "Memorial Sloan-Kettering Cancer Center", and "Sloan Kettering Institute" are the same place. The `RorResolver` handles this via fuzzy matching against a curated `ror_aliases.yaml` covering the top-50 biomedical institutions — because the ROR API itself doesn't reliably resolve abbreviations and historical name variants.

### 3. ClinicalTrials.gov conditions field

CT.gov studies list conditions in freetext (`"KRAS G12C Mutant Non-Small Cell Lung Cancer"`) or as a `derivedSection.conditionMeshList`. About 40% of studies have no structured MeSH data at all — just the freetext string. The converter falls back to `conditions_freetext` and passes it raw as a `mesh_descriptor`, accepting lower precision in exchange for not silently dropping those candidates.

### 4. NIH Reporter PI field

Reporter returns PI names as a list of strings: `["SMITH, JOHN A (contact)", "DOE, JANE B"]`. The `(contact)` marker indicates the primary PI; co-investigators have no such marker. The converter extracts the contact PI, strips the marker, and normalizes name order from `LAST, FIRST MIDDLE` to `First Last` — because every other source uses `First Last` format.

### 5. OpenAlex authorship positions

OpenAlex encodes author position as `"first"`, `"middle"`, or `"last"` — but this is only populated in ~60% of records. For the other 40%, the converter falls back to the final element in the `authorships` array (senior author heuristic). When ORCID is present in OpenAlex but not in PubMed for the same paper, the merge step enriches the PubMed candidate with the ORCID — effectively backfilling a strong key after the fact.

---

## Act 2c — Feature Engineering Walkthrough (4 min)

> *This is the second evaluation criterion and the most commonly underprepared section. Walk through the raw → feature → score chain end to end.*

The core question: how does a raw API response become a ranked score? Here's the chain for three key features.

### F1 — Publication Impact (RCR)

**Raw data:** PubMed `efetch` returns a list of PMID strings per author.

**Feature engineering:**
1. Collect all PMIDs across all sources for this candidate.
2. Batch-query the **iCite API** with those PMIDs to get Relative Citation Ratio (RCR) per paper. RCR is NIH's field-normalized citation metric — a paper with RCR=2.0 has twice the citation impact of the average paper in its field and year.
3. Compute `mean_rcr` across all papers. Normalize: `F1_raw = min(1.0, mean_rcr / 5.0)`. A researcher with average papers at RCR 1.0 scores 0.2; one with landmark papers at RCR 5.0+ scores 1.0.
4. Percentile-rank within the current query's candidate cohort. This is critical: a score of F1=0.8 means this candidate is in the 80th percentile of the researchers Aegis found for *this specific query* — not globally.

**Why this matters vs. raw pub count:** A researcher with 200 papers in low-impact journals is worse than one with 10 papers in *Nature Medicine*. Raw counts reward volume; RCR rewards impact.

### F3 — Leadership Signal

**Raw data:** Heterogeneous text across three sources:
- PubMed evidence trail: `"Published 'KRAS inhibitor...' (PMID:33521700)"` — no leadership signal
- NIH Reporter evidence trail: `"Principal Investigator on NIH R01CA...: 'KRAS inhibitor development' ($450K)"` — explicit PI credit
- CT.gov evidence trail: `"PI on NCT04303780: Phase 2 study of... (Phase 2, RECRUITING)"` — PI role

**Feature engineering:**
1. Scan the evidence trail for leadership markers: `"Principal Investigator"`, `"PI on"`, `"Lead"`, `"Primary Investigator"`.
2. Count hits: `leadership_hits = count(matches)`.
3. Normalize: `F3_raw = min(1.0, leadership_hits / 3.0)`. Three or more PI credits → max score.
4. Before this fix, Reporter evidence trails were just `"NIH R01CA123456 ($450K)"` — zero topic words AND zero leadership markers. Adding `project_title` to the `GrantRecord` model fixed both problems in one change.

### Topical Fit (query-dependent)

**Raw data:** Candidate's aggregated `evidence_trail` text + `mesh_descriptors` set.

**Feature engineering:**
1. Tokenize the query into words longer than 3 characters: `{"kras", "g12c", "inhibitor", "drug", "discovery", "lung", "cancer"}`.
2. Build a single search text per candidate: concatenate name variants + MeSH descriptor strings + evidence trail items, lowercase.
3. `topical_fit = count(query_words found in text) / count(query_words)`

This is intentionally simple — an earlier version double-weighted MeSH hits, which systematically favored PubMed candidates (whose records carry NLM-curated MeSH terms) over NIH Reporter and CT.gov candidates (whose records carry RCDC categories and freetext conditions). The plain word-coverage formula treats all sources equally and lets the evidence trail do the work.

This is what made the Reporter fix so high-impact: before adding `project_title`, every NIH-funded researcher had evidence trail `"NIH R01CA123456 ($450K)"` — none of those words overlap with "KRAS G12C inhibitor drug discovery." `T(c,q)^β` at `β=1.0` → `0^1.0 = 0`, zeroing the entire composite score. Adding the grant title fixed that in one model change.

---

## Act 2d — LLMs in the Pipeline (2 min)

> *Addresses the "use LLMs to classify domain expertise, summarize profiles" bonus.*

LLMs and a keyword classifier do two different jobs in Aegis. It's worth being precise about which does what.

**What Claude does: query expansion into MeSH vocabulary**
The raw query `"KRAS G12C inhibitor drug discovery for lung cancer"` is sent to Claude via the Anthropic tool-use API with a system prompt: *"You are a biomedical query expansion assistant. Only use exact MeSH descriptor headings from the NLM vocabulary."* Claude returns a structured tool-call response: `["Proto-Oncogene Proteins p21(ras)", "Antineoplastic Agents", "Lung Neoplasms", "Neoplasms"]`. These become the search terms passed to ClinicalTrials.gov and NIH Reporter. Without this step, the pipeline would pass raw natural language to APIs expecting controlled vocabulary — and CT.gov would return essentially nothing. If Claude is unavailable (no API key), a MetaMap stub hits the NLM MeSH Lookup API; if that fails, it falls back to title-casing words from the query. Three-tier degradation.

**What a keyword classifier does: query type routing**
Query type routing — which scoring weight vector to use — is a pure keyword classifier, not an LLM. It scans the lowercased query against three frozensets (drug discovery, clinical trial PI, policy/epi). On `"KRAS G12C inhibitor drug discovery for lung cancer"` it matches "drug" and "inhibitor" → 2 hits → confidence `0.5 + 2×0.1 = 0.70` → drug discovery weight vector. This is intentionally simple: the routing decision happens before the pipeline runs, needs to be fast, and the keyword sets are interpretable and easy to extend. An LLM would add latency and a dependency for a classification task where the decision boundary is well-defined.

**What's not yet LLM-powered — and the design for it:**
Profile summarization is the obvious next layer. The architecture for it is: after ranking, take the top-K candidates' evidence trails and pass them through Claude to generate a 2–3 sentence expert summary: *"Dr. Smith is a translational oncologist with 45 publications in RAS biology (mean RCR 3.2), PI on 3 NIH R01 grants totaling $1.8M, and currently leading a Phase 2 KRAS G12C trial at MGH. Primary expertise: KRAS inhibitor development, NSCLC, and ADMET optimization."* The evidence trail already has all the inputs; the LLM call is a presentation layer, not a data layer. This would be a 1-day add.

---

## Act 3 — Live Demo (7 min)

> *Switch to the browser. Go through each step deliberately.*

**URL:** https://aegis-frontend-rho.vercel.app

### Step 1 — Submit a query

Type: `"KRAS G12C inhibitor drug discovery for lung cancer"`

Point out:
- As you type, the **query type badge** auto-classifies in real time: `Drug Discovery — 70%` (matches keywords "drug" + "inhibitor" → 2 hits → `0.5 + 2×0.1 = 0.7`)
- The **MeSH expansion** panel appears showing the terms Claude extracted: `["Neoplasms", "Proto-Oncogene Proteins p21(ras)", "Antineoplastic Agents", "Lung Neoplasms"]`
- These are the exact terms passed to ClinicalTrials.gov and NIH Reporter — not the raw query text
- The Weight Configuration panel shows F5 Translational at 50%

Hit **Submit**.

### Step 2 — Jobs page / SSE streaming

The system returns HTTP 202 immediately and redirects to `/jobs/{job_id}`.

Point out:
- **Four source cards** appear one by one in real time via Server-Sent Events as each source completes
- This is real async parallel execution — PubMed, NIH Reporter, CT.gov, and OpenAlex running simultaneously via `asyncio.gather`
- The streaming was a genuine engineering challenge: two bugs had to be fixed — a race condition where fast sources emitted events before the browser SSE connection opened (fixed by pre-creating the event queue), and a Vercel proxy timeout that cut the stream mid-pipeline (fixed with `maxDuration = 300`)

### Step 3 — Results

Click **View Results →**.

Point out:
- Each candidate card shows **score components**: Q (quality prior), T (topical fit), R (recency)
- The **score bands** (thin bars behind the main score) show bootstrap variance — a wide band means this candidate's rank is sensitive to how you weight the exponents. A narrow band means they rank consistently.
- Candidates with published contact emails show a **clickable mailto link** directly on the card — extracted from PubMed corresponding author affiliation fields at ingestion time (~40% per-paper hit rate, ~85%+ per-candidate for active publishers with multiple PMIDs)
- Click a candidate — show the **evidence trail**: "Published 'KRAS G12C...' (PMID:33521700, 2021-01-15)", "Principal Investigator on NIH R01CA...: 'KRAS inhibitor development' ($450K)", "PI on NCT04303780: Phase 2, RECRUITING"

### Step 4 — Shortlisting and HITL

Show the **Shortlist** button — adds to `/shortlists`.
Show the **HITL review queue** — the identity resolution cases where the system wasn't confident enough to auto-merge. A human decides: same person or different?

These decisions feed back into the probabilistic linker's calibration over time.

---

## Act 4 — Engineering Depth: The Interesting Problems (5 min)

> *This is the section where technical interviewers lean in.*

### The PubMed dominance bug

Early in the build, results were completely dominated by PubMed candidates regardless of query. The root cause was subtle: `candidate_store.list_by_cohort(None)` was fetching ALL candidates ever ingested — not just those discovered in the current query. Researchers who had appeared in previous queries had accumulated PMIDs across multiple runs, inflating their F1 percentile relative to newcomers.

Fix: `RecordIngester` now maintains an `ingested_uuids` set scoped to each pipeline run. Scoring only operates on candidates from the current query.

### The Reporter topical fit collapse

NIH Reporter candidates had `topical_fit = 0` across the board. Why? The evidence trail for Reporter records was just `"NIH R01CA123456 ($450K)"` — no topic words. With the beta exponent at 1.0, `T(c,q)^β = 0^1 = 0`, zeroing the entire composite score for every grant-funded researcher.

Fix: Added `project_title` to `GrantRecord`. Evidence trail is now `"Principal Investigator on NIH R01CA123456: 'KRAS inhibitor development in NSCLC' ($450K)"` — title words now participate in topical fit scoring.

### The scoring formula choice

The formula `Score = I × Q^α × T^β × R^γ` is multiplicative for a reason. An additive formula would let a candidate with great publications but zero topical relevance still rank well by accumulating partial credit. The multiplicative form creates a natural `AND` logic: you need quality *and* relevance *and* recency *and* integrity. Any one factor near zero pulls the whole score toward zero.

The bootstrap variance bands (200 Monte Carlo samples over the exponent space) solve a real problem: when a panel disagrees on which candidate to hire, it's often because they're implicitly using different weights. Showing the variance band lets you say "this candidate ranks #3 regardless of how you weight the exponents — that's a stable recommendation" vs. "this one flips between #2 and #12 depending on how much you weight recency — the panel should discuss that explicitly."

### Why DuckDB

Columnar analytics for percentile ranking over 600+ candidates, join-heavy MeSH lookups, and fast cohort scans made DuckDB significantly faster than SQLite for the scoring pipeline. The accepted tradeoff is single-writer concurrency: safe for one machine, needs to change before horizontal scaling.

---

## Act 5 — Honest Gaps (3 min)

> *This section builds the most trust. Don't skip it.*

There are things that don't fully work yet that I want to name:

**1. The orchestrator uses inline scoring, not the formal F1–F7 modules.**
The `src/aegis/scoring/` directory has proper `FxComputer` classes with author-position weighting (F1), grant-type tiers and dollar amounts (F2), last-author rate and editorial roles (F3), diminishing-returns apex scoring (F4), FDA submission + trial phase weighting (F5), mentorship lineage (F6), and board certification + hospital tier (F7). The orchestrator reimplements all of these inline with much cruder formulas — grant count instead of grant quality, string-matching "Principal Investigator" instead of structured role data, MeSH tag count instead of lineage. Wiring the formal modules in is the single highest-impact improvement to ranking quality.

**2. Recency is broken.**
Every converter stamps `last_updated_per_source = datetime.now(UTC)` at ingestion time, so every candidate gets recency ~1.0 regardless of when they last published. A paper from 2003 and a paper from 2025 are indistinguishable. The formal `Recency` class uses actual publication dates with exponential half-life decay — it just needs to be wired in.

**3. NIH Reporter source filtering uses RCDC taxonomy, not MeSH.**
When we pass MeSH terms as RCDC category filters, the API finds no matching category and returns effectively random recent grants. Reporter candidates still flow through — they're just not topically filtered. The fix is a MeSH-to-RCDC crosswalk or switching to Reporter's free-text search mode.

**4. The coauthor overlap feature in identity resolution is a stub.**
The `ProbabilisticLinker` has a 15% weight for co-author overlap in the Fellegi-Sunter score. The current implementation computes Jaccard between the incoming record's coauthor list and the existing candidate's *own name variants* — which almost never produces a non-zero score. When `artifact_coauthors` is empty (which is common), the weight is redistributed to the other four features automatically. So it's not silently wrong — it's just not contributing.

**5. The iCite batch query is capped at 200 PMIDs.**
With 200+ candidates each having multiple papers, the pipeline silently drops RCR scores for PMIDs beyond the cap, causing those candidates to fall back to raw publication count for F1. The fix is to paginate the iCite call.

---

## Act 6 — What I'd Build Next (3 min)

> *Close with vision. Shows you're thinking like a product builder, not just an implementer.*

### Short term (scoring quality)
- **Wire the formal F1–F7 scoring modules** into the orchestrator — the code exists, it just needs to replace the inline formulas. This single change gives us grant-type tiers (R01 vs. R03), author-position weighting, proper recency decay, and structured leadership detection.
- **Fix recency** — use actual publication dates from PubMed/OpenAlex instead of `datetime.now(UTC)`.
- **Prestige slider** — once F2 distinguishes R01 holders from K-award holders, add a slider to the query form that shifts the weight vector along a prestige↔accessible axis. The weight vector infrastructure already supports this.
- **Paginate iCite** — remove the 200-PMID cap so all candidates get RCR enrichment.
- **Fix NIH Reporter RCDC mismatch** with a crosswalk or free-text search mode.

### Medium term (what makes this a real product)
**The feedback loop.**
The HITL queue, feedback modal, and refit API are already built. The missing piece is closing the loop: analyst decisions → Plackett-Luce exponent refit → updated weight vectors. This is what makes the system learn over time — ranking gets better the more it's used.

**LinkedIn as a secondary enrichment layer.**
Once a candidate pool is established from the high-signal public sources, LinkedIn becomes useful for: enriching with current affiliation, identifying who knows whom. Contact info is already handled via PubMed corresponding author extraction (~40% per-paper hit rate, higher per-candidate). The identity linking infrastructure already handles multi-source merging — LinkedIn just becomes one more source.

**Horizontal scale.**
DuckDB single-writer is fine for one machine. The path to scale is either MotherDuck (DuckDB in the cloud) or pg_duckdb (Postgres + DuckDB query engine). The data model doesn't change; the store layer does.

**LLM profile summarization.**
One-day add: pass top-K candidates' evidence trails through Claude to generate structured expert summaries per candidate. The inputs already exist; it's a presentation layer over the existing data model.

---

## Act 6b — Integration Into a Larger Talent System (3 min)

> *Directly addresses the "continuous updates + integration" bonus. Make it concrete.*

Aegis is designed as a standalone microservice that slots into a broader talent stack. Here's the integration surface:

### API-first design
The backend exposes a clean JWT-authenticated REST API:
- `POST /v1/queries` → returns `{job_id}` immediately (HTTP 202)
- `GET /v1/jobs/{id}` → poll for status + results
- `GET /v1/queries/{id}/stream` → SSE stream for real-time progress
- `GET /v1/candidates/{uuid}` → full candidate profile + evidence trail
- `POST /v1/shortlists` / `GET /v1/shortlists/{id}` → managed candidate pools

Any ATS, CRM, or internal tool can hit these endpoints with a service account JWT. The frontend is one consumer; it's not special.

### ATS/CRM integration pattern
The practical integration is a **push-on-shortlist** pattern:
1. Recruiter runs a query in Aegis, shortlists 10 candidates.
2. Aegis fires a webhook: `POST {ats_webhook_url}` with the shortlist payload.
3. The ATS creates candidate records pre-populated with the evidence trail, score breakdown, and source links.

No manual copy-paste. The candidate UUID is stable across queries — so when the same researcher appears in a future search, the ATS record can be enriched, not duplicated.

### Continuous updates
The pipeline is stateless from the source databases' perspective — every query re-fetches live data. But candidate records accumulate across queries in DuckDB. The design for continuous background refresh is:

1. **Incremental re-ingestion**: a scheduled job (e.g., daily) re-runs the pipeline for the top-N most-shortlisted candidates to pick up new publications, trial registrations, and grant awards.
2. **Change detection**: new artifact refs trigger a recency score update and optionally a webhook notification to the ATS: *"Dr. Smith just published a new KRAS paper — her relevance score for your open trial PI position just increased."*
3. **Opt-out / right-to-be-forgotten**: the `OptOutStore` already exists. Candidates can be permanently excluded from all future queries by UUID.

### The feedback loop as a continuous improvement engine
Every time an analyst accepts or rejects a candidate shortlist, that signal feeds into the Plackett-Luce weight relearner. Over time:
- The weight vectors get calibrated to *this customer's* preferences, not just the generic priors.
- Customers who consistently prefer candidates with high RCR get a higher α exponent.
- Customers who consistently pick recent grant recipients get a higher γ.

This is the flywheel: more usage → better-calibrated weights → better results → more usage.

---

## One-Line Summary

> *If someone asks you to summarize in a sentence:*

"Aegis is a production expert discovery engine that pulls from four public biomedical data sources in parallel (PubMed, NIH Reporter, CT.gov, OpenAlex), resolves researcher identity probabilistically across sources, ranks candidates with a query-type-adaptive scoring formula, and extracts corresponding author contact emails for direct outreach — deployed on Fly.io and Vercel, with a full React frontend and async jobs system."

---

## Appendix — Key Technical Details

| Thing | Detail |
|-------|--------|
| Backend | Python + FastAPI, deployed on Fly.io (sjc, 1 CPU, 512MB) |
| Frontend | Next.js 16 (Turbopack), deployed on Vercel |
| Storage | DuckDB (6 migrations, ~15 tables) |
| Sources | PubMed (NCBI E-utilities), NIH Reporter v2, ClinicalTrials.gov v2, OpenAlex |
| Contact enrichment | PubMed corresponding author email extraction (~40% per-paper, ~85%+ per-candidate) |
| Identity resolution | Fellegi-Sunter: name 35%, affiliation 25%, co-authors 15%, MeSH Jaccard 15%, time continuity 10% |
| Ranking formula | `I(c) × Q(c)^α × T(c,q)^β × R(c,q)^γ` |
| Query expansion | Claude (tool-use) → MetaMap stub → NLM MeSH API fallback |
| Streaming | Server-Sent Events, `asyncio.Queue` per job, `maxDuration=300` on Vercel proxy |
| Auth | JWT (HMAC-SHA256), customer claims, rate limit field |
| Bootstrap variance | 200 Monte Carlo samples over (α, β, γ) space → p10/p50/p90 score bands |
| HITL | Fellegi-Sunter score 0.5–0.95 → review queue → human decision → merge/reject |
| Weight vectors | `basic_research_v1`, `drug_discovery_v1`, `clinical_trial_pi_v1`, `policy_epi_v1`, `translational_v1` |
