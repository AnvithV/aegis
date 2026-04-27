---
title: Aegis Phase 3 — Production
description: Promote Aegis from internal scoring engine to a production system — continuous-update pipeline, customer-facing query API with auth + rate limiting + audit trails, downstream-task-quality feedback loop, geographic broadening (EPO, ERC, MRC, CIHR, KAKEN, NSFC), and contestability workflow.
---

# Aegis Phase 3 — Production

For AI: Execute this plan using the executing-plans skill. Mark tasks complete as you go. Stop and verify after each task.

**Created:** 2026-04-24
**Status:** Draft (gated on Phase 2 exit)
**Location:** docs/plans/aegis/phase-3-production.md
**Duration target:** Ongoing (initial 16 weeks for cutover; steady-state thereafter)
**Inherits from:** specs/aegis/00-program-overview.md
**Depends on:** docs/plans/aegis/phase-2-multi-population.md (must be closed)

## Overview

Phase 3 is the cutover from "working internally" to "running in production with paying customers." The scoring math, integrity gate, and multi-population coverage are all in place from Phases 0–2. Phase 3 adds the operational surface required for a Scale-AI-grade product: a customer-facing API, continuous (not batch) ingestion of integrity-critical sources, geographic broadening to fix the US-bias the program overview §15 explicitly calls out, the downstream-task-quality feedback loop that closes the weight-learning cycle, and the contestability workflow that lets candidates correct their own evidence trails.

Phase 3 produces six outcomes:

1. Event-driven, push-triggered ingestion for integrity sources (license actions, ORI, OFAC/SAM, Retraction Watch) with sub-day latency. These sources cannot be allowed to lag.
2. Daily preprint ingestion (bioRxiv, medRxiv) — the recency-critical input for fast-moving subdomains.
3. Customer-facing query API with authentication, rate limiting, evidence-trail responses, audit logging, and the contestability endpoint.
4. LLM-backed query expansion service (constrained-generation pattern from program overview §10) replacing Phase 1's MetaMap-only path.
5. Steady-state weight-relearning loop using downstream task-quality (Fleiss κ, customer accept rate) as ground truth, feeding back into the Plackett–Luce fitter from Phase 1.
6. Geographic broadening: EPO patents (full coverage, not just the Phase 2 EU subset), ERC, Horizon Europe, MRC (UK), CIHR (Canada), JST/KAKEN (Japan), NSFC (China). Per-region coverage diagnostics ensure ranking results are not silently US-biased.

## Prerequisites

- Phase 2 closed: all three populations live, archetypes 1–4 hit predicted outcomes, specialty classifier accurate, cross-population identity merging precise.
- Production infrastructure provisioned: deployment environment (cloud or on-prem), secrets management, observability stack (metrics + logging + tracing), database scaling story decided.
- Customer pilot identified — at least one paying customer or anchor partner running real labeling tasks against Aegis output, providing the downstream-quality signal needed for Task 1.7.
- Legal/compliance review of public APIs and customer-facing terms completed; LinkedIn-handling decision finalized (program overview §15: official APIs, licensed enrichment vendors, or candidate self-link only).

## Core Production Tasks

### Task 1.1: Event-driven integrity-source ingestion

**Description:** Replace polling-based integrity ingestion with event-driven where supported. Retraction Watch publishes RSS/Atom feeds; ORI publishes new findings on a federal register feed; OFAC/SAM offer change-data feeds; many state medical boards publish RSS or have monitorable bulletin pages. Sub-source ingestion latency target: <6 hours from publication to integrity-gate update. Sources without push: high-frequency polling at 15-minute intervals during business hours.

**Files:**
- `src/aegis/ingestion/event_driven/retraction_watch.py`
- `src/aegis/ingestion/event_driven/ori_register.py`
- `src/aegis/ingestion/event_driven/ofac_sam.py`
- `src/aegis/ingestion/event_driven/state_boards/`
- `src/aegis/ingestion/event_dispatcher.py`.

**Implementation Notes:**
- Use a small message bus (Redis Streams or NATS) internally so any source feed can publish to a common ingestion topic.
- On every integrity-source event, the affected candidate's `I(c)` is recomputed and a recompute is scheduled for any active query touching them.
- Sub-day SLA is non-negotiable for the hard-gate sources.

**Verification:**
- Synthetic Retraction Watch event reaches the gate in <30 minutes end-to-end.
- Daily SLO report: 99th-pct integrity-source latency <6h.

**Design Assertions:**
- Module exports `IntegrityEventDispatcher.publish(event: IntegrityEvent)`.
- An `IntegrityEvent` schema enumerates source, candidate identifiers, action type, severity.

### Task 1.2: Daily preprint ingestion (bioRxiv / medRxiv)

**Description:** Replace Phase 0's monthly-snapshot preprint ingestion with daily incremental from bioRxiv and medRxiv APIs. Preprints contribute to `R(c, q)` recency at 0.6× peer-reviewed weight (program overview §13). Recency in fast subdomains (chemistry, ML4Health) materially benefits from this.

**Files:**
- `src/aegis/sources/biorxiv.py`
- `src/aegis/sources/medrxiv.py`
- `src/aegis/sources/preprints_test.py`.

**Implementation Notes:**
- Both archives expose JSON APIs with daily endpoints; ingestion is straightforward.
- Preprints lack curated MeSH; we use the LLM coverage-fallback (program overview §10) to propose MeSH tags from abstracts, validated against the ontology.
- When a preprint is later published in a peer-reviewed journal, the system collapses them to one artifact (preprint becomes the "older version") and reweights.

**Verification:**
- Daily ingestion completes in <30 min.
- Preprint-to-publication merge accuracy ≥95% on test set.

**Design Assertions:**
- `BioRxivClient.fetch_daily(date) -> Iterator[PreprintRecord]`.

### Task 1.3: Customer-facing query API

**Description:** Build the customer-facing REST API: POST `/v1/queries` accepting query specification (free-text task description, optional MeSH override, optional cohort filter, optional K, optional cutoff strategy) and returning ranked candidate list with full evidence trails. Authentication via signed API tokens; rate-limited per customer; every request logged with retention budget.

**Files:**
- `src/aegis/api/server.py`
- `src/aegis/api/schemas.py` — request/response shapes.
- `src/aegis/api/auth.py`
- `src/aegis/api/rate_limit.py`
- `src/aegis/api/audit_log.py`
- `tests/api/test_queries.py`.

**Implementation Notes:**
- Use FastAPI with pydantic for the request/response layer.
- API tokens are JWT-signed, scoped per-customer, with optional per-cohort restrictions for tiered customers.
- Audit log entry per request: customer, query, response candidate UUIDs, served version of weights and integrity rules. The version pinning is what makes ranking reproducible across customer-side retries.
- The response shape is fixed by the program overview's per-candidate output spec; we do not customize per-customer.

**Verification:**
- End-to-end query latency <500ms p95 (matches Phase 1 budget).
- Authentication failure modes tested: missing token, wrong scope, expired.

**Design Assertions:**
- API exposes `POST /v1/queries`, `GET /v1/queries/{id}`, `GET /v1/candidates/{uuid}/evidence`.

### Task 1.4: LLM-backed query expansion service

**Description:** Replace Phase 1's MetaMap-only query expansion with the program-overview-§10 pattern: deterministic MetaMap pass first, then LLM expansion constrained to MeSH vocabulary for synonyms, related subtopics, and disambiguation. The LLM call is rate-limited and cost-budgeted per customer; cached aggressively per (raw_query, mesh_version).

**Files:**
- `src/aegis/query/llm_expansion.py`
- `src/aegis/query/cache.py`
- `src/aegis/query/llm_expansion_test.py`.

**Implementation Notes:**
- Constrained-generation: provider's structured-output mode (Anthropic tool use, OpenAI function calling, vLLM grammar constraints) — output JSON schema validated against MeSH ontology before acceptance.
- Reject invalid LLM outputs and fall back to MetaMap-only with a "low-confidence expansion" flag in the response.
- Cost budget per customer is configurable; over-budget returns MetaMap-only with a flag rather than failing.

**Verification:**
- Query "evaluate generative-chemistry outputs for JAK2-targeting kinase inhibitors" expands to includes `Janus Kinase 2`, `Janus Kinase Inhibitors`, `Protein Kinase Inhibitors`, `Drug Design`, etc.
- Adversarial query (gibberish) yields a low-confidence expansion flag.

**Design Assertions:**
- `LlmQueryExpander.expand(raw_query: str) -> ExpandedQuery`.

### Task 1.5: Result formatter with evidence trails and variance bands

**Description:** Produce the customer-facing result format: per-candidate name, ROR-normalized affiliation, top-3 contributing artifacts (PMIDs / NCT IDs / patent numbers / grant IDs with hyperlinks), per-component scores, identity-linkage confidence, score-variance band, specialty annotation, integrity-gate disclosures (any soft discounts applied), and provenance pointer to the served weight-version and integrity-rule version.

**Files:**
- `src/aegis/api/formatter.py`
- `src/aegis/api/formatter_test.py`.

**Implementation Notes:**
- The variance band is computed offline (Phase 1 Task 1.15) and looked up here.
- Disclosures: if `I(c) < 1.0`, the result includes which soft discount applied; never silent.
- Provenance lets a customer reproduce the exact ranking days later for compliance review.

**Verification:**
- Snapshot-test on result format; it does not change shape across releases without a versioned migration.

**Design Assertions:**
- `ResultFormatter.format(ranked: RankedList) -> CustomerResponse`.

### Task 1.6: Downstream-task-quality feedback ingestion

**Description:** When a customer routes a labeling task to candidates ranked by Aegis, the resulting label set has measurable quality (inter-rater agreement Fleiss κ, customer-side accept rate, post-hoc consensus rate). Ingest these signals back into Aegis as the steady-state ground truth for weight relearning. The customer publishes outcomes via a feedback endpoint; Aegis maps outcomes to the (query, candidate) pairs that produced them.

**Files:**
- `src/aegis/api/feedback.py`
- `src/aegis/learning/downstream_quality.py`
- `src/aegis/learning/downstream_quality_test.py`.

**Implementation Notes:**
- Feedback endpoint is a POST per task with structured outcome metrics; no PHI accepted (program overview §15).
- The mapping (query, candidate, outcome) feeds into a derived pairwise-judgment dataset that augments the audit-panel data from Phase 1.
- A candidate who consistently produces low-κ outputs in a subdomain receives an implicit downweighting in that subdomain (via weight learning, not via score override).

**Verification:**
- Synthetic feedback loop: feed 100 task outcomes, refit weights, observe expected weight shifts.

**Design Assertions:**
- API exposes `POST /v1/feedback/tasks/{task_id}/outcomes`.

### Task 1.7: Steady-state weight relearning loop

**Description:** Schedule weight relearning weekly using the union of audit-panel pairwise judgments (Phase 1) and downstream-task-quality-derived pairs (Task 1.6). The fitter is the same Plackett–Luce from Phase 1 Task 1.14; the input grows over time. Per-specialty exponents diverge as evidence accumulates. Auto-deploy on small changes; manual gate on large.

**Files:**
- `src/aegis/learning/refit_steady_state.py`
- `src/aegis/learning/refit_scheduler.py` (extend).

**Implementation Notes:**
- Audit-panel data and downstream-quality data weighted in the loss; downstream is the higher-trust source once it's accumulated enough.
- Per-specialty α/β/γ converge to different values; this is expected and desirable.
- Refit logs: every refit cycle writes a report comparing prior vs new weights, per-specialty coverage, and confidence intervals.

**Verification:**
- Weekly refit runs to completion; weight-version table grows monotonically.
- Weight-stability dashboard (Phase 1 Task 2.5) shows expected drift over time.

**Design Assertions:**
- `SteadyStateRefitter.run() -> RefitReport`.

### Task 1.8: Geographic broadening — EPO full coverage and non-US grants

**Description:** Extend ingestion to non-US sources. Patents: full EPO coverage (Phase 2 added EU subset; this completes it) plus WIPO PCT applications. Grants: ERC (European Research Council), Horizon Europe, MRC (UK), CIHR (Canada), JST and KAKEN (Japan), NSFC (China). Each source ingestion follows the typed-client pattern from Phase 0 Tasks 1.1–1.3.

**Files:**
- `src/aegis/sources/wipo.py`
- `src/aegis/sources/erc.py`
- `src/aegis/sources/horizon_europe.py`
- `src/aegis/sources/mrc.py`
- `src/aegis/sources/cihr.py`
- `src/aegis/sources/jst_kaken.py`
- `src/aegis/sources/nsfc.py`
- `tests/sources/test_geographic_broadening.py`.

**Implementation Notes:**
- These sources have wildly different APIs and data quality; expect per-source effort comparable to Phase 0 Task 1.1.
- KAKEN (Japan) is multilingual; identity resolution for Japanese-named researchers requires a transliteration / native-script handling step.
- NSFC (China) data is partially restricted; ingestion is best-effort for public records, with a coverage caveat.

**Verification:**
- Each source ingestion completes a full historical pull within budget.
- Coverage report shows non-US share of cohort rising from ~15% (Phase 2) to ~40%+ (Phase 3 target).

**Design Assertions:**
- Each source exports a typed client mirroring the Phase 0 pattern.

### Task 1.9: Per-region coverage diagnostics

**Description:** Coverage diagnostics broken down by region (US, EU, UK, Canada, Japan, China, RoW). Each region reports identity-resolution coverage, source coverage, and per-population breakdown. Customer query responses include a region-coverage caveat when results are weighted toward under-covered regions.

**Files:**
- `src/aegis/observability/regional_coverage.py`
- Dashboards.

**Implementation Notes:**
- Region is derived from ROR-normalized affiliation history; current primary affiliation drives the region tag.
- Caveat surfaces in API responses so customers know whether a "global top-50" is actually globally representative.

**Verification:**
- Regional breakdown matches expected ratios on cohort.
- Caveat surfaces when query results are >75% from one region.

### Task 1.10: Audit-log API (candidate evidence trail)

**Description:** Public-to-the-candidate audit-log API: `GET /v1/candidates/{uuid}/evidence` returns a structured view of every artifact, every score component, every integrity decision, every linkage decision affecting that candidate. Required for the program overview §15 candidate-transparency promise.

**Files:**
- `src/aegis/api/candidate_view.py`
- `src/aegis/api/candidate_view_test.py`.

**Implementation Notes:**
- Access control: candidate-self-views (verified via ORCID OAuth or NPI-based signed proof), customer-views (limited per their access scope), admin-views (full).
- Self-views return full detail; customer-views are scoped.
- Access requests themselves are audit-logged.

**Verification:**
- Self-view round-trip works for a verified ORCID identity.
- Customer-view returns only scoped data.

**Design Assertions:**
- API exposes `GET /v1/candidates/{uuid}/evidence` with pluggable access-control policy.

### Task 1.11: Contestability endpoint and workflow

**Description:** Implement the candidate-contestability flow: a candidate (verified via ORCID/NPI) can submit a correction (e.g., "this affiliation history is wrong" or "this retraction was misclassified"). Submissions enter the HITL review queue with elevated priority; reviewer decisions update the candidate record (always append-only) and feed back into the linker / integrity gate.

**Files:**
- `src/aegis/api/contestability.py`
- `src/aegis/identity/contestability_handler.py`
- `tests/api/test_contestability.py`.

**Implementation Notes:**
- Contestability is *required* by the §15 ethics policy; the lack of one was a documented risk in the program overview.
- Reviewer SLA: 5 business days median, 14 days p95.
- Disagreement resolution: reviewer decision is final, candidate can re-submit with new evidence.

**Verification:**
- Synthetic correction submitted via API → reaches review queue → reviewer decides → candidate record updated → query results reflect the change.

**Design Assertions:**
- API exposes `POST /v1/candidates/{uuid}/contests`.

### Task 1.12: Privacy and ethics enforcement

**Description:** Codify the §15 ethics policy as runtime checks: PHI/HIPAA scanner on any data attempting to enter Aegis (rejected; alerts on hit), demographic-feature blocklist (gender/race/citizenship/age fields are stripped at ingestion), candidate-opt-out enforcement (opted-out candidates removed from cohort and excluded from query results until they re-opt-in).

**Files:**
- `src/aegis/privacy/phi_scanner.py`
- `src/aegis/privacy/demographic_blocklist.py`
- `src/aegis/privacy/opt_out.py`.

**Implementation Notes:**
- PHI scanner uses pattern matching plus an LLM classifier for unstructured fields; false-positives prefer over false-negatives.
- Opt-out is reversible by candidate but defaults to permanent until reversed.
- All three are runtime gates; bypassing them is an alertable event.

**Verification:**
- Synthetic PHI in an artifact → rejected; alerted.
- Opted-out candidate absent from query results.

## Observability and Governance Tasks

### Task 2.1: Query latency SLO monitoring

**Description:** Define and monitor query-latency SLO: <500ms p95, <1500ms p99, success rate ≥99.9%. Monitoring is per-customer and per-cohort; SLO breaches trigger paging.

**Files:**
- `src/aegis/observability/query_slo.py`
- Dashboards and alert rules.

**Implementation Notes:**
- SLO budget tracking; consuming the budget is allowed but tracked.
- Per-cohort breakdown distinguishes "drug-discovery slow" from "translational slow."

**Verification:**
- Dashboards render; alerts fire on synthetic latency spike.

### Task 2.2: Per-customer task-quality tracking

**Description:** Track downstream task quality per customer over time. Customer A consistently producing higher-κ output than customer B at the same query distribution may indicate customer A's task instructions are clearer; we surface this for both customers' improvement.

**Files:**
- `src/aegis/observability/customer_quality.py`.

**Implementation Notes:**
- Aggregate metrics, no per-task PHI.
- Customer-side dashboard exposed via the API.

**Verification:**
- Per-customer trend visible in dashboard.

### Task 2.3: Refresh-cadence SLA tracking

**Description:** Each source has a defined refresh-cadence SLA from program overview §13. Track per-source compliance and surface breaches. Hard-gate sources (license actions, ORI, OFAC, retractions) have the strictest SLAs.

**Files:**
- `src/aegis/observability/refresh_sla.py`.

**Implementation Notes:**
- SLA breaches on hard-gate sources page on-call immediately; non-hard-gate breaches are weekly summary.
- SLA targets versioned; changes are deliberate.

**Verification:**
- Synthetic stuck source triggers correct severity alert.

### Task 2.4: Geographic-coverage tracking

**Description:** Per-region coverage tracked over time as new sources come online. The non-US ratio of the cohort and the per-region linkage-confidence distribution are key metrics. Goal: cohort non-US ratio reaches 40%+ steady state.

**Files:**
- `src/aegis/observability/geographic_tracking.py`.

**Implementation Notes:**
- Trends over time, not just snapshots; geographic broadening is a gradual investment.
- Per-region weight-fitting gaps highlighted (we may need region-specific exponents eventually).

**Verification:**
- Trend graph populates; threshold alert when ratio regresses.

### Task 2.5: Weight-drift over time

**Description:** Track how α, β, γ and per-family weights move across weekly refits over 6+ months of operation. Long-horizon drift signals genuine evidence accumulation; sudden jumps signal data-quality issues with the feedback ingestion.

**Files:**
- `src/aegis/observability/weight_history.py`.

**Implementation Notes:**
- Per-specialty time series for each weight.
- Annotations on the chart for major events (new source ingested, customer pilot started).

**Verification:**
- Chart populates over the first 4 weeks of Phase 3 with expected smooth trends.

## Error Handling Tasks

### Task 3.1: Query-API rate-limit and abuse handling

**Description:** Per-customer rate limits enforced at the API edge with token-bucket; over-budget returns 429 with a `Retry-After`. Abuse patterns (e.g., scraping the candidate database via repeated queries) trigger automated throttling and an admin alert.

**Files:**
- `src/aegis/api/rate_limit.py` (extend).
- `src/aegis/api/abuse_detection.py`.

**Implementation Notes:**
- Detection is conservative; false-positives (real customer traffic) are not silently throttled, they are surfaced for manual review.
- Customer can request rate-limit increases via support.

**Verification:**
- Synthetic burst triggers 429.
- Synthetic scraping pattern triggers admin alert.

### Task 3.2: LLM hallucination detection in query expansion

**Description:** Even with constrained generation, LLMs occasionally produce malformed or out-of-vocabulary outputs. Validate every LLM expansion against the MeSH ontology and the system's CPC + ChEMBL cross-walks; reject outputs containing invented terms; fall back to MetaMap-only and flag the response.

**Files:**
- `src/aegis/query/expansion_validator.py`.

**Implementation Notes:**
- Validator is fail-closed: anything not in the ontology is rejected, not "guessed."
- Per-day metric tracks rejection rate; high rejection rate signals a model regression.

**Verification:**
- Synthetic invented-term LLM output → rejected; metric increments.

### Task 3.3: Stale-data circuit breaker

**Description:** When a hard-gate source has lagged beyond its SLA (e.g., Retraction Watch hasn't updated in 48h), open a circuit breaker that adds a "stale integrity data" caveat to API responses for affected populations. Better to disclose than silently serve potentially-wrong rankings.

**Files:**
- `src/aegis/api/staleness.py`.

**Implementation Notes:**
- Circuit-breaker thresholds are per-source.
- Caveat is informational, does not block responses.

**Verification:**
- Synthetic source-lag triggers caveat; restoration clears it.

### Task 3.4: Customer dispute workflow (between contestability and rate limits)

**Description:** Customer-side disputes (e.g., "candidate X who you ranked highly produced low-quality labels") follow a structured workflow: customer files via API, dispute lands in admin queue, admin reviews evidence (the candidate's evidence trail + the customer's task-quality data), and either confirms (feeds back as a downstream-quality signal) or rejects (with reasoning).

**Files:**
- `src/aegis/api/customer_disputes.py`.

**Implementation Notes:**
- Disputes are not contestability — that's candidate-driven; this is customer-driven.
- Confirmed disputes are highest-confidence ground-truth feedback for weight relearning.

**Verification:**
- End-to-end synthetic dispute flow.

## Performance and Scale Tasks

### Task 4.1: Query throughput SLO

**Description:** Production target throughput: 100 queries/second sustained, 500 qps peak, with the latency SLO above. This requires per-cohort caching, query-expansion caching, and read-replica scaling on the candidate store.

**Files:**
- `src/aegis/api/scaling.md` — design notes.
- Load-test harness in `tests/perf/test_throughput.py`.

**Implementation Notes:**
- Cohort-level caching of `Q(c)` and `v_c` computed offline; per-query cost is the topical-fit retrieval and final composition.
- Read replicas for the candidate store; writes are infrequent (nightly recompute).

**Verification:**
- Load test sustains 100 qps for 1 hour with latency SLO held.

### Task 4.2: Refresh pipeline parallelism

**Description:** With ~25 distinct sources active in Phase 3, the refresh pipeline must parallelize across sources and within source. Per-source workers with backpressure; aggregate ingestion completes within 6 hours (the daily refresh budget) at full Phase 3 source coverage.

**Files:**
- `src/aegis/ingestion/orchestrator.py`.

**Implementation Notes:**
- Use a worker-pool pattern with per-source rate limiters.
- Failure isolation: one source's outage cannot cascade.

**Verification:**
- Daily full-refresh completes in <6h.

### Task 4.3: LLM cost monitoring

**Description:** LLM calls (query expansion, profile summarization, integrity-triage, MeSH-fallback) have non-trivial per-call cost. Track and alert on per-customer LLM spend; cap aggressively per-customer with graceful degradation (fall back to MetaMap and flag the response).

**Files:**
- `src/aegis/observability/llm_cost.py`.

**Implementation Notes:**
- Per-customer cost budgets configurable.
- Caching aggressive; cache hit rate ≥95% on warmed query population.

**Verification:**
- Cost dashboard renders; budget overage triggers fallback.

## Testing

- Production-ready integration tests covering the full API surface.
- Load tests sustained at 100 qps for 1h with SLO held.
- Chaos engineering drills: source outage, LLM provider outage, database failover — Aegis degrades gracefully and responses carry caveats.
- Apex-recall regression broadened to all populations and all regions; targets ≥80% (translational), ≥70% (drug-discovery), ≥70% (clinician), ≥60% (non-US, with explicit ramp).
- End-to-end customer pilot: at least one customer running ≥1,000 real queries over a 4-week window with downstream-quality feedback flowing.

## Rollback Plan

Phase 3 deploys can be rolled back per surface: API can fall back to a prior version while keeping Phase 2 internal capabilities; weight version pinning lets the system serve last-known-good rankings while a refit is investigated; integrity-source ingestion can be paused per-source without taking the gate offline (the gate just stops getting fresh data, with caveats surfaced). The customer-facing API is versioned (`/v1/`); a `/v2/` introduces breaking changes only with documented migration windows.

## Self-Audit

- Core production tasks: 12
- Observability and governance tasks: 5
- Error handling tasks: 4
- Performance and scale tasks: 3
- Total tasks: 24
- Tasks with explicit file targets: 24
- Tasks with verification steps: 24
- Tasks with design assertions: 12 (core tasks)
- Phase 3 closes when: (1) customer-facing API live, authenticated, audit-logged; (2) integrity-source latency SLO of <6h held over 4 weeks; (3) downstream-quality feedback flowing from at least one customer pilot; (4) cohort non-US ratio ≥40%; (5) load test sustains 100 qps for 1h with SLO; (6) candidate contestability flow round-trips end-to-end; (7) per-component dashboards (query SLO, refresh SLA, weight drift, regional coverage, LLM cost) all live and producing data.
