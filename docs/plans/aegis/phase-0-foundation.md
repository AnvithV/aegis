---
title: Aegis Phase 0 — Foundation
description: Identity resolution, public-source ingestion (PubMed, NIH RePORTER, ClinicalTrials.gov), and seed-cohort assembly for the NSCLC translational specialty, including worked-example validation against the four archetypes in the program overview.
---

# Aegis Phase 0 — Foundation

For AI: Execute this plan using the executing-plans skill. Mark tasks complete as you go. Stop and verify after each task.

**Created:** 2026-04-24
**Status:** Draft (ready for /build_v2)
**Location:** docs/plans/aegis/phase-0-foundation.md
**Duration target:** 4 weeks
**Inherits from:** specs/aegis/00-program-overview.md

## Overview

Phase 0 builds the data substrate Aegis depends on. It does **not** implement scoring (that is Phase 1) and does **not** add patents or clinicians (Phase 2). Phase 0 produces three outcomes:

1. A working ingestion pipeline against three public APIs — PubMed E-utilities, NIH RePORTER, ClinicalTrials.gov — with rate-limit-safe, cursor-based, incremental refresh.
2. A two-tier identity-resolution layer (ORCID-keyed + probabilistic Fellegi–Sunter) that produces unified candidate records for the NSCLC translational seed cohort, with a first-class linkage-confidence field.
3. A worked-example validation harness that demonstrates the seed cohort surfaces the four archetypes from the program overview (§11), proving the pipeline produces the data substrate Phase 1 scoring will consume.

Phase 0 is deliberately scoped to one specialty (NSCLC translational research) so that scope, evaluation, and expected coverage are concrete. Generalization to clinicians and drug-discovery R&D is Phase 2.

## Prerequisites

- `specs/aegis/00-program-overview.md` is current. Sections referenced: §3 taxonomy, §4 source map, §5 identity resolution, §6 messy-data strategy, §11 worked examples.
- Stack: Python 3.11+ (§18). Working directory and package layout established at Phase 0 kickoff.
- Public-API access registrations completed: NCBI E-utilities API key, NIH RePORTER (no key required), CT.gov v2 (no key required), ORCID public API client ID, ROR (no key required).
- Compute baseline: single workstation or modest cloud VM is sufficient for Phase 0 cohort scale (target: ~5,000 NSCLC translational candidates after seed expansion).

## Core Foundation Tasks

### Task 1.1: PubMed E-utilities ingestion harness

**Description:** Build a typed client that wraps NCBI E-utilities (esearch, efetch, elink, espell) for PubMed and PubMed Central, returning structured records: PMID, title, abstract, MeSH descriptor list with major-topic flag, qualifier list, author list with affiliations and ORCID where present, journal NLM ID, MEDLINE-indexing status, publication date, and article type. The client must respect E-utilities rate limits (3 req/sec without key, 10 with key), back off on 429/503, persist a resumable cursor by EDAT (entry date), and log every request for replay.

**Files:**
- `src/aegis/sources/pubmed.py` — client, record types, retry policy.
- `src/aegis/sources/pubmed_test.py` — tests against fixture XML responses.

**Implementation Notes:**
- Use `Bio.Entrez` from biopython for the underlying transport, but wrap it in a typed layer; do not leak `Entrez.read` dictionaries upward.
- MeSH descriptors must preserve the major-topic asterisk and the qualifier (e.g., `Lung Neoplasms*/drug therapy`); both are scoring inputs in Phase 1.
- Persist raw XML payloads alongside parsed records; we re-parse rather than re-fetch on schema changes.
- Cursor checkpoint at end of every batch; idempotent resumption is required.

**Verification:**
- Round-trip 200 known NSCLC PMIDs through the client; assert MeSH list and authorship match a held-out manual reference.
- Rate-limit compliance: integration test that runs 100 requests and asserts no 429.
- Cursor: kill mid-ingest, restart, confirm zero duplicate records and zero missed records.

**Design Assertions:**
- Module exports `PubMedClient` with method `search_and_fetch(query: str, since: date) -> Iterator[PubMedRecord]`.
- `PubMedRecord` is a frozen dataclass with required fields: `pmid`, `mesh_descriptors: list[MeshDescriptor]`, `authors: list[AuthorAffiliation]`, `medline_indexed: bool`.

### Task 1.2: NIH RePORTER ingestion harness

**Description:** Build a typed client for NIH RePORTER's v2 API, returning grants by PI, including project number (R01/U01/P01/DP1/etc.), eRA Commons ID of all PIs and contact PI, total cost, fiscal year, project terms, RCDC (Research, Condition, and Disease Categorization) categories, organization name with ROR-normalizable affiliation, and grant-status history. Pagination, incremental refresh by award_notice_date, and retry on 5xx are required.

**Files:**
- `src/aegis/sources/reporter.py` — client and grant record types.
- `src/aegis/sources/reporter_test.py` — fixture tests.

**Implementation Notes:**
- The eRA Commons ID is the cross-walk to PubMed's NIH PMC author-manuscript submissions; preserve it on every grant record.
- Multi-PI grants exist; capture all PIs with their roles, do not collapse to contact PI.
- RCDC categories are NIH-curated topic tags that complement MeSH for grant-side topic vectors; preserve them verbatim.
- Foundation grants (HHMI, BWF, etc.) are not in RePORTER and are out of scope for Phase 0; stubbed for Phase 1.

**Verification:**
- Pull all R01s with NSCLC RCDC for a fiscal year; assert count is within ±5% of the published RePORTER UI number.
- Confirm eRA Commons IDs are populated for ≥99% of records.

**Design Assertions:**
- Module exports `ReporterClient.fetch_grants_by_topic(rcdc_terms: list[str], since_fy: int) -> Iterator[GrantRecord]`.
- `GrantRecord` exposes `pis: list[GrantPI]` where `GrantPI.era_id: str` is required.

### Task 1.3: ClinicalTrials.gov v2 ingestion harness

**Description:** Build a typed client for ClinicalTrials.gov's v2 (REST/JSON) API, returning study records with NCT ID, conditions (MeSH and free-text), interventions, phase, study type, sponsor, lead investigator, sub-investigators with affiliations, status history, and study-design fields needed downstream (e.g., randomization, masking). Incremental refresh by `LastUpdatePostDate`.

**Files:**
- `src/aegis/sources/ctgov.py` — client and study record types.
- `src/aegis/sources/ctgov_test.py` — fixture tests.

**Implementation Notes:**
- CT.gov data is sponsor-self-reported; treat affiliations as best-effort and feed them through the ROR normalizer (Task 1.4) rather than trusting strings.
- The role distinction between "Principal Investigator," "Sub-Investigator," and "Study Chair" matters for `w_role` in `v_c`; preserve verbatim.
- Many studies list multiple PIs across sites; capture all and link by site.

**Verification:**
- Pull NSCLC + immunotherapy active trials and confirm count matches the CT.gov UI within ±2%.
- Confirm Phase 2/3 PI roles are present on ≥95% of fetched records.

**Design Assertions:**
- Module exports `CtgovClient.fetch_studies_by_condition(mesh_terms: list[str]) -> Iterator[StudyRecord]`.
- `StudyRecord.investigators: list[InvestigatorRole]` with `role: Literal["PI","Sub-I","Study Chair"]`.

### Task 1.4: ROR-normalized affiliation resolver

**Description:** Build a service that takes raw affiliation strings (from PubMed, RePORTER, CT.gov) and returns a normalized `RorOrg` record with ROR ID, canonical name, parent/child relationships, country, and a confidence score. The resolver uses the public ROR data dump (refreshed monthly) for offline matching, with fuzzy string match + abbreviation expansion ("MGH" → "Massachusetts General Hospital") and a small handcrafted alias list for the ~50 most common biomed institutions.

**Files:**
- `src/aegis/identity/ror.py` — resolver implementation.
- `src/aegis/identity/ror_aliases.yaml` — handcrafted alias list.
- `src/aegis/identity/ror_test.py` — fixture tests.

**Implementation Notes:**
- ROR offers parent/child hierarchies (e.g., "Mass General Brigham" parent of "Massachusetts General Hospital"); preserve the full ancestry chain on each match.
- Cache resolutions; affiliation strings are highly repetitive across artifacts.
- Below 0.7 confidence, return the candidate match plus a flag — do not silently overwrite.

**Verification:**
- Resolve 500 hand-labeled affiliation strings (mix of US/EU/Asia institutions) with ≥97% top-1 accuracy.
- Confirm parent-org resolution for hospital → academic-medical-center mappings.

**Design Assertions:**
- Module exports `RorResolver.resolve(affiliation_string: str) -> RorMatch` with `RorMatch.confidence: float ∈ [0, 1]`.

### Task 1.5: Identity resolution — Tier 1 (strong key)

**Description:** Implement direct identity resolution using ORCID, eRA Commons ID, and (for Phase 2) NPI as primary keys. For each artifact ingested, attempt strong-key lookup before falling back to probabilistic. ORCID resolves PubMed + ORCID-linked grants in one hop; eRA Commons resolves NIH PMC submissions; NPI is stubbed for Phase 0.

**Files:**
- `src/aegis/identity/strong_key.py` — resolver.
- `src/aegis/identity/strong_key_test.py` — tests.

**Implementation Notes:**
- ORCID public API allows lookup by full ORCID iD and reverse search by name + affiliation; we use both directions.
- Cache ORCID profiles; refresh on monthly cadence.
- Maintain a `(strong_key_type, strong_key_value) → candidate_uuid` mapping table; this is the spine of the candidate registry.

**Verification:**
- For 200 NSCLC translational PIs with known ORCIDs, confirm 100% link to the same `candidate_uuid` across PubMed, RePORTER, and CT.gov.
- ORCID coverage diagnostic: report % of seed-cohort artifacts with strong key.

**Design Assertions:**
- Module exports `StrongKeyResolver.resolve(artifact: AnyArtifact) -> Optional[CandidateRef]`.
- A `CandidateRegistry` table stores `(strong_key_type, strong_key_value, candidate_uuid)` with unique constraint.

### Task 1.6: Identity resolution — Tier 2 (probabilistic)

**Description:** Implement Fellegi–Sunter probabilistic record linkage for artifacts lacking a strong key. Features: full name + initials variants, ROR-normalized affiliation history, co-author graph overlap, MeSH topic overlap (Jaccard), time continuity. Train match thresholds on the strong-key-known subset (these provide labeled positive pairs "for free").

**Files:**
- `src/aegis/identity/probabilistic.py` — linker, feature extractors.
- `src/aegis/identity/probabilistic_train.py` — threshold training.
- `src/aegis/identity/probabilistic_test.py` — tests.

**Implementation Notes:**
- Use `splink` or `recordlinkage` library for the underlying scoring; do not implement Fellegi–Sunter from scratch.
- Output a confidence ∈ [0, 1] per match; the system uses three thresholds: auto-link (≥0.95), auto-reject (≤0.5), HITL-review (between).
- Co-author graph requires Phase-0 graph state; build incrementally as ingestion proceeds.

**Verification:**
- Held-out test: hide ORCID for 500 strong-key-known authors; rerun probabilistic linker; assert ≥95% recovery to correct `candidate_uuid` at auto-link threshold.
- HITL-queue size: <8% of borderline cases on the seed cohort.

**Design Assertions:**
- Module exports `ProbabilisticLinker.link(artifact: AnyArtifact, registry: CandidateRegistry) -> LinkResult` where `LinkResult.confidence: float` and `LinkResult.action: Literal["auto-link","review","reject"]`.

### Task 1.7: Human-in-the-loop linkage review queue

**Description:** Stand up a review queue for borderline probabilistic matches. The queue presents a side-by-side view of evidence (artifacts, affiliations, co-authors, MeSH overlap) for the candidate-pair under review and allows a reviewer to confirm, reject, or split. Reviewer decisions feed back into the linker as additional labeled training data.

**Files:**
- `src/aegis/identity/review_queue.py` — queue logic.
- `src/aegis/identity/review_ui/` — minimal local web UI (Phase 0 stub; full UI in Phase 3).
- `src/aegis/identity/review_queue_test.py` — tests.

**Implementation Notes:**
- Phase 0 UI is intentionally minimal: a local Flask/FastAPI page is enough. Phase 3 invests in a real reviewer experience.
- Decisions are append-only and time-stamped; we never overwrite a prior decision, we add a new one and the latest wins.
- Track per-reviewer agreement when ≥2 reviewers exist (Phase 1+).

**Verification:**
- Submit 50 known-decision pairs; reviewer can complete each in <90 seconds median.
- Round-trip: a reviewer decision is reflected in linker output on the next run.

**Design Assertions:**
- Queue exposes `ReviewQueue.next() -> Optional[ReviewItem]` and `ReviewQueue.decide(item, decision)`.

### Task 1.8: NSCLC translational seed-cohort builder

**Description:** Construct the Phase 0 candidate seed pool: every author who appears as last author on a MEDLINE-indexed PubMed paper with MeSH `Carcinoma, Non-Small-Cell Lung` (any qualifier) within the last 10 years, OR is a contact PI on an active NSCLC NIH grant, OR is a PI on an NSCLC trial in CT.gov. Expand by co-author graph two hops with a degree-cap to control fan-out.

**Files:**
- `src/aegis/cohort/nsclc_translational.py` — seed builder.
- `src/aegis/cohort/seed_test.py` — tests.

**Implementation Notes:**
- Two-hop expansion will produce ~5,000 candidates from ~500 seed PIs; cap per-PI fan-out at 50 to prevent celebrity-author effects.
- Track provenance: for each candidate, record which seed source(s) introduced them; this matters for coverage diagnostics.
- Industry-employed NSCLC researchers will surface (correctly) via co-authorship; flag them for Phase 2 reclassification.

**Verification:**
- Cohort size between 3,500 and 6,000 candidates.
- ≥80% recall against the publicly-known NSCLC apex list (top-100 NCCN guideline contributors + ASCO Young Investigators + NIH MERIT awardees in NSCLC) — this is the primary Phase 0 pass-criterion.

**Design Assertions:**
- Module exports `build_nsclc_translational_cohort() -> Cohort` where `Cohort.candidates: list[CandidateUuid]` and `Cohort.provenance: dict[CandidateUuid, list[SeedSource]]`.

### Task 1.9: Candidate-record schema and storage layer

**Description:** Define the unified `Candidate` schema that the identity resolver writes to and that Phase 1 scoring reads from. Schema includes: candidate UUID, strong-key bundle, name variants, affiliation history (ROR-normalized, time-stamped), artifact references (PMIDs, NCT IDs, grant IDs), aggregate features (Phase 1 will fill these), linkage confidence, evidence-trail pointers, and last-updated timestamps per artifact source.

**Files:**
- `src/aegis/storage/schema.py` — pydantic/dataclass schema.
- `src/aegis/storage/candidate_store.py` — read/write API.
- `src/aegis/storage/migrations/001_initial.sql` — DDL.
- `src/aegis/storage/schema_test.py` — tests.

**Implementation Notes:**
- Storage backend for Phase 0: Postgres or DuckDB (single workstation scale). Phase 3 may move to a distributed columnar store; the read/write API must stay stable across that transition.
- Artifact references are by ID, not embedded — artifact bodies live in separate per-source tables. Joins are explicit.
- Linkage confidence is a top-level field on `Candidate`, not buried in metadata.

**Verification:**
- Schema round-trip on 5,000 cohort candidates with no field-truncation.
- Read latency for "fetch full candidate by UUID" <50ms p95 on cohort scale.

**Design Assertions:**
- `Candidate` exports fields: `uuid`, `strong_keys: dict[StrongKeyType, str]`, `name_variants: list[str]`, `affiliations: list[AffiliationSpan]`, `artifact_refs: ArtifactRefBundle`, `linkage_confidence: float`, `last_updated_per_source: dict[str, datetime]`.

### Task 1.10: Worked-example validation harness

**Description:** Implement a validation harness that loads the four archetypes defined in `specs/aegis/00-program-overview.md` §11 (Dr. A established PI, Dr. B industry pivot, Dr. C industry-only — stubbed for Phase 2, Dr. D integrity outlier — stubbed for Phase 1 integrity gate) as named test fixtures, asserts that Phase 0 ingestion captures the artifacts each archetype depends on, and reports any gaps. This is the primary go/no-go gate for Phase 0.

**Files:**
- `src/aegis/validation/archetypes.py` — fixture definitions.
- `src/aegis/validation/phase0_harness.py` — harness driver.
- `tests/validation/test_phase0_archetypes.py` — assertions.

**Implementation Notes:**
- Archetypes are fictitious but their structural attributes are real: e.g., "Dr. A has ≥40 last-author NSCLC papers in last 10y, mean RCR ≥2.0, ≥1 active R01." We pick a small set of real public PIs that match each archetype's structural profile and use *their* artifacts as the test fixture.
- For Phase 0, only Dr. A and Dr. B (translational pop) are validated; Dr. C and Dr. D are deferred to Phase 2 and Phase 1 respectively.

**Verification:**
- For each in-scope archetype, the harness loads ≥95% of expected artifact types from the cohort store.
- The harness emits a structured report; CI fails the build if any archetype fixture has missing artifacts.

**Design Assertions:**
- `ArchetypeFixture` exposes `expected_artifacts: ArtifactRefBundle` and `assertions: list[Callable[[Candidate], bool]]`.

## Observability and Governance Tasks

### Task 2.1: Coverage diagnostics dashboard

**Description:** Build a per-source coverage diagnostic that reports, for the NSCLC translational seed cohort: % of candidates with strong-key (ORCID/eRA), % with confident probabilistic linkage, % with artifacts from each source, % flagged thin-record. Coverage is a first-class output: the program overview §12 mandates coverage be reported alongside scores.

**Files:**
- `src/aegis/observability/coverage.py`
- `src/aegis/observability/coverage_dashboard.html` (static report).

**Implementation Notes:**
- Report counts and percentiles, not just averages. The 5th-percentile linkage-confidence is more informative than the mean.
- Re-runnable on every ingestion pass; persist historical reports to track drift.

**Verification:**
- Dashboard renders for the seed cohort with all per-source breakdowns.
- A regression test asserts strong-key coverage ≥40% on the cohort (this is the realistic ceiling; 50% is aspirational).

### Task 2.2: Identity-linkage confidence reporting

**Description:** Surface linkage confidence as a top-level field on every candidate record and on every API response. Below 0.7, results are flagged in evidence trails as "low-confidence linkage"; below 0.5, candidate is held out of any ranking response and queued for HITL review.

**Files:**
- `src/aegis/observability/linkage_report.py`
- updates to `src/aegis/storage/candidate_store.py`.

**Implementation Notes:**
- Threshold values are tunable per deployment; defaults documented in the program overview and surfaced as runtime config.
- A daily report enumerates candidates whose confidence has shifted by >0.1 since last report.

**Verification:**
- API response on any candidate includes `linkage_confidence` field.
- Daily report runs without errors on cohort.

### Task 2.3: Ingestion freshness and lag metrics

**Description:** Emit per-source ingestion freshness metrics: time since last successful pull, lag between artifact publication date and ingestion date, gap counts (artifacts referenced by a downstream record but not yet ingested). These metrics gate the refresh-cadence promises in §13 of the program overview.

**Files:**
- `src/aegis/observability/freshness.py`
- Prometheus-format metrics endpoint exposing these counters.

**Implementation Notes:**
- Metrics are emitted in Prometheus exposition format for portability; no scraping infrastructure required for Phase 0, but metrics shape is fixed now to avoid relabeling later.
- Per-source SLOs documented as part of the metric description.

**Verification:**
- Metrics endpoint reachable; values populate within 10 minutes of an ingestion run.
- Synthetic test: pause ingestion, confirm freshness lag increases.

### Task 2.4: Source-API failure rate dashboards

**Description:** Track per-API call success/failure, latency p50/p95/p99, and rate-limit-hit counts. Each external API has different failure modes (NCBI E-utilities vs CT.gov vs RePORTER), and we need to distinguish "API outage" from "our parser broke."

**Files:**
- `src/aegis/observability/api_health.py`
- Dashboards and alert rules in `ops/aegis/api_alerts.yaml`.

**Implementation Notes:**
- Distinguish HTTP errors (4xx vs 5xx vs timeout) and parse errors (schema drift) in the metrics.
- Rate-limit-hit counter is critical because NCBI tightened limits historically; we want early signal.

**Verification:**
- Dashboards render synthetic failure rates correctly.
- Alert rules fire on simulated outages.

### Task 2.5: Per-source artifact counts and drift alerts

**Description:** Per-source artifact-count metrics with anomaly detection on day-over-day deltas. A 30% drop in PubMed ingestion volume should page someone before silently degrading the cohort. Includes baselining with a 14-day rolling window and a configurable z-score threshold for alerting.

**Files:**
- `src/aegis/observability/drift.py`
- Alert rules in `ops/aegis/drift_alerts.yaml`.

**Implementation Notes:**
- Drift detection is more important than absolute volume; a healthy ingestion can still drift if upstream changes their data semantics.
- Quarterly review of alert thresholds.

**Verification:**
- Synthetic drift test triggers an alert.
- Baseline computed correctly on 14-day windows of fixture data.

## Error Handling Tasks

### Task 3.1: Affiliation-contradiction handling

**Description:** When LinkedIn or candidate-asserted affiliation contradicts the dated public-artifact affiliation history (the §6 example), record the contradiction in the evidence trail, prefer the artifact-derived value for scoring, and flag the candidate for review only if the contradiction crosses a major-org boundary (e.g., academia vs industry, country boundary). Do not silently overwrite either source.

**Files:**
- `src/aegis/identity/contradictions.py`
- `src/aegis/identity/contradictions_test.py`.

**Implementation Notes:**
- Contradictions are stored in an append-only log keyed by candidate UUID.
- The flag does not block scoring; it surfaces in the evidence trail and dashboards.

**Verification:**
- Synthetic contradiction (LinkedIn 2020-present vs PubMed last affiliation 2015) produces a flagged record without scoring failure.

### Task 3.2: API rate-limit and retry policy

**Description:** Centralized retry policy across all source clients: exponential back-off on 429/503, max-3-retries, separate budget per API. On budget exhaustion, surface the failure in observability and resume on next scheduled run; do not block the entire pipeline.

**Files:**
- `src/aegis/sources/retry.py`
- Tests in each source's test file plus `src/aegis/sources/retry_test.py`.

**Implementation Notes:**
- Per-API retry budget prevents one source's outage from starving others.
- Retry decisions are logged at INFO; budget-exhaustion at WARN.

**Verification:**
- Synthetic 429 storm: client backs off, eventually succeeds, no silent data loss.

### Task 3.3: Artifact deduplication

**Description:** The same artifact often appears in multiple sources (a PubMed paper referenced in a CT.gov study; an NIH grant linked to a PubMed paper). Implement deduplication keyed by canonical artifact ID, with a precedence rule (PubMed canonical for papers; RePORTER canonical for grants; CT.gov canonical for trials). Cross-references are preserved as edges, not duplicates.

**Files:**
- `src/aegis/storage/dedup.py`
- `src/aegis/storage/dedup_test.py`.

**Implementation Notes:**
- Deduplication runs on every ingestion pass; idempotent re-runs are required.
- Cross-reference edges feed the co-author graph and the recency calculation; do not collapse them.

**Verification:**
- Ingest the same paper from PubMed and from CT.gov: one canonical record, one cross-reference edge.

### Task 3.4: Cohort-membership audit log

**Description:** Every addition or removal from the seed cohort writes an audit log entry with reason, source, and timestamp. Coverage regressions ("we lost 200 candidates between yesterday and today") need a forensic trail. The log feeds the drift dashboard (Task 2.5).

**Files:**
- `src/aegis/cohort/audit.py`
- `src/aegis/cohort/audit_test.py`.

**Implementation Notes:**
- Append-only; never edited.
- Daily summary email to the cohort steward.

**Verification:**
- Synthetic add/remove produces correct log entries; query by reason works.

## Performance and Scale Tasks

### Task 4.1: Incremental cursor-based ingestion

**Description:** All three source clients (PubMed, RePORTER, CT.gov) must support incremental refresh keyed by a per-source cursor (EDAT, award_notice_date, LastUpdatePostDate). Full re-pulls are only permitted on quarterly schema-change resyncs. Cursors are persisted on every batch.

**Files:**
- `src/aegis/sources/cursor.py`
- Updates to each source client.

**Implementation Notes:**
- Cursor durability is the single most important reliability property of the ingestion layer; every other recovery path depends on it.
- Daily refresh on the seed cohort scale is <30 minutes end-to-end at Phase 0 volume.

**Verification:**
- Full ingestion vs incremental ingestion produce equivalent state on cohort scale.
- Daily incremental run completes in <30 min.

### Task 4.2: Cohort-scoped indexing for downstream phases

**Description:** Build database indexes that make Phase 1 scoring queries fast: per-candidate artifact lookup, per-MeSH-term candidate inverted index, per-year artifact aggregation. Indexes are scoped to the cohort to keep storage modest in Phase 0.

**Files:**
- `src/aegis/storage/indexes.py`
- `src/aegis/storage/migrations/002_indexes.sql`.

**Implementation Notes:**
- Inverted index on MeSH descriptors is the most important; it powers `T(c, q)` lookup in Phase 1.
- Indexes are rebuilt on schema migration; no online migration logic needed at Phase 0 scale.

**Verification:**
- Per-MeSH lookup p95 <100ms on cohort.
- Per-candidate full-record fetch p95 <50ms.

### Task 4.3: Batch-size tuning for source clients

**Description:** Each E-utilities call accepts up to 200 PMIDs (efetch); RePORTER accepts up to 500 records per page; CT.gov v2 supports configurable page sizes. Tune batch sizes per source for throughput while staying within rate-limit budgets, and document the chosen sizes.

**Files:**
- Source client configs.
- `docs/aegis/ingestion-tuning.md` — tuning notes.

**Implementation Notes:**
- Empirical tuning; document the chosen sizes and the reason.
- Avoid pathological batch sizes that cause server-side slowness even within rate limits.

**Verification:**
- Throughput numbers documented for each source.
- No regression in error rate at chosen batch sizes.

## Testing

- Unit tests on every module above; coverage target ≥85% on identity and ingestion modules.
- Integration tests against captured fixtures (no live API calls in CI).
- A nightly job runs a small live-API smoke test (10 records per source) to catch upstream schema drift early.
- Worked-example archetype harness (Task 1.10) is the primary acceptance gate.
- Coverage diagnostics dashboard (Task 2.1) must show ≥80% recall against the NSCLC apex list before Phase 0 is closed.

## Rollback Plan

Phase 0 produces a candidate store and ingestion pipeline; rollback is straightforward because no scoring or customer-facing artifact depends on Phase 0 yet. If Phase 0 produces unacceptable identity-resolution accuracy, isolate the bad linkage decisions to a quarantined namespace, hold them out of the seed cohort, and continue to iterate on the linker. Source-client rollback is per-source: each client can be disabled independently and the remaining sources continue to ingest.

## Self-Audit

- Core foundation tasks: 10
- Observability and governance tasks: 5
- Error handling tasks: 4
- Performance and scale tasks: 3
- Total tasks: 22
- Tasks with explicit file targets: 22
- Tasks with verification steps: 22
- Tasks with design assertions: 10 (core tasks; observability/error/perf tasks have observable behavior assertions in verification rather than struct-level assertions)
- Phase 0 closes when: (1) worked-example archetype harness passes for Dr. A and Dr. B, (2) coverage dashboard reports ≥80% recall against NSCLC apex list, (3) probabilistic-linker held-out test recovers ≥95% of strong-key-known authors at auto-link threshold, (4) end-to-end daily incremental ingestion completes in <30 min.
