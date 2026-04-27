---
title: Aegis Phase 1 — Scoring
description: Full quality prior, integrity gate, topical-fit and recency computation, end-to-end ranking with default exponents, and bootstrap pairwise expert audit + weight learning loop. Operates on the NSCLC translational cohort produced by Phase 0.
---

# Aegis Phase 1 — Scoring

For AI: Execute this plan using the executing-plans skill. Mark tasks complete as you go. Stop and verify after each task.

**Created:** 2026-04-24
**Status:** Draft (gated on Phase 0 exit)
**Location:** docs/plans/aegis/phase-1-scoring.md
**Duration target:** 8 weeks
**Inherits from:** specs/aegis/00-program-overview.md
**Depends on:** docs/plans/aegis/phase-0-foundation.md (must be closed)

## Overview

Phase 1 turns the candidate substrate Phase 0 produced into a working ranking engine. By the end of Phase 1, Aegis can answer a query on the NSCLC translational cohort with a calibrated, evidence-backed ranked list. Phase 1 explicitly does **not** add new populations (Phase 2) and does **not** expose a customer-facing API (Phase 3); it builds the math, the validation panel, and the weight-learning loop.

Phase 1 produces five outcomes:

1. The full quality prior `Q(c)` across all six families (F1–F6) for the translational specialty, calibrated as percentile-within-cohort.
2. The integrity gate `I(c)` with both hard zeros and soft discounts wired against Retraction Watch, ORI, OFAC/SAM, and predatory-venue triangulation.
3. The topical-fit `T(c, q)` and recency `R(c, q)` computations with deterministic MeSH-vector math.
4. End-to-end `Rank(c, q)` with default exponents, validated against archetypes 1, 2, and 4 from the program overview §11.
5. A bootstrap pairwise expert audit panel that produces labeled rankings, fed into a Plackett–Luce learner that updates exponents and family weights.

## Prerequisites

- Phase 0 closed: archetype harness passes for Dr. A and Dr. B; cohort coverage ≥80% recall on NSCLC apex list; probabilistic linker recovery ≥95%.
- `specs/aegis/00-program-overview.md` sections referenced: §7 feature engineering, §8 integrity gate, §9 scoring math, §10 LLM placement, §11 archetypes.
- Expert audit panel recruited: 5–10 senior MD/PhDs in NSCLC translational research who have agreed to perform pairwise judgments. Recruitment is an external dependency; phase plan tasks assume the panel is in place.

## Core Scoring Tasks

### Task 1.1: F1 — RCR aggregation (field-normalized impact)

**Description:** Implement the F1 sub-score: aggregate iCite Relative Citation Ratio across each candidate's PubMed publications, weighted by author position (last/corresponding = 1.0, first = 0.7, middle = 0.3), and produce both mean and 90th-percentile statistics. Aggregation excludes editorials, letters, and corrections per article-type. Final F1 sub-score is the percentile rank within the candidate's specialty cohort of a composite of mean RCR and top-RCR (90th pct), computed in log space to avoid heavy-tail distortion.

**Files:**
- `src/aegis/scoring/f1_rcr.py`
- `src/aegis/scoring/f1_rcr_test.py`
- `src/aegis/sources/icite.py` — iCite RCR ingestion (NIH provides bulk dump).

**Implementation Notes:**
- iCite ships RCR as part of each PMID record; ingest the bulk file monthly rather than per-paper API calls.
- Author-position weighting requires authorship order from PubMed — already in `PubMedRecord` from Phase 0.
- A candidate with <10 RCR-eligible papers gets a low-confidence flag on F1 and falls back to a less-discriminating prior; do not score on tiny denominators.

**Verification:**
- F1 distribution on the cohort is approximately uniform in [0, 1] (percentile-by-construction).
- Top-10 candidates by F1 overlap ≥60% with NCCN guideline contributors (sanity check).

**Design Assertions:**
- Module exports `F1Computer.score(candidate: Candidate) -> F1Score` with fields `mean_rcr_log: float`, `top_rcr_log: float`, `percentile: float ∈ [0, 1]`, `low_confidence: bool`.

### Task 1.2: F2 — NIH funding & resource-getting

**Description:** Implement the F2 sub-score: aggregate NIH grants per candidate from RePORTER, weighted by role (contact PI = 1.0, multi-PI = 0.7, co-I = 0.3), grant type (R01/U01/P01 = 1.0, K-series = 0.6, R03/R21 = 0.4, others scaled), and total cost. Active-grant signal weighted higher than expired. Sub-score is percentile within specialty cohort over a composite that includes total funding (log) and active-R01-equivalent count.

**Files:**
- `src/aegis/scoring/f2_funding.py`
- `src/aegis/scoring/f2_funding_test.py`.

**Implementation Notes:**
- "Active" = today's date within the project period.
- Foundation grants (HHMI, BWF) are not in RePORTER and remain stubbed; a placeholder field keeps the schema stable.
- Multi-PI grants count fractionally for each PI; do not double-count.

**Verification:**
- Sum of fractional PI shares per grant equals 1.0 ± epsilon across cohort.
- F2 percentile distribution is uniform.

**Design Assertions:**
- Module exports `F2Computer.score(candidate) -> F2Score` with fields `total_cost_log`, `active_r01_equivalent`, `percentile`.

### Task 1.3: F3 — PI / leadership

**Description:** Implement the F3 sub-score: last-author rate on RCR-weighted papers, trial-PI count from CT.gov, corresponding-author rate, and editorial roles (parsed from journal masthead snapshots — Phase 1 stub uses a small handcrafted list of major NSCLC journals). The F3 percentile reflects "this person runs a lab and steers the field," not "this person publishes a lot."

**Files:**
- `src/aegis/scoring/f3_leadership.py`
- `src/aegis/scoring/f3_leadership_test.py`
- `data/aegis/editorial_roles_phase1.yaml` — handcrafted editorial-roles list.

**Implementation Notes:**
- Last-author rate is computed only over papers where the candidate had a clear authorship position (ambiguous middle-author papers excluded).
- Trial-PI count uses Phase 0 CT.gov investigator role; "Study Chair" counts but is weighted at 0.7 vs full PI = 1.0.
- Editorial-roles ingestion at scale is Phase 3+; Phase 1 hardcodes a starter list.

**Verification:**
- Top decile by F3 contains ≥80% of candidates with at least one R01 + one CT.gov PI role (cross-consistency with F2).

**Design Assertions:**
- `F3Computer.score(candidate) -> F3Score` with fields `last_author_rate`, `trial_pi_count`, `corresponding_author_rate`, `editorial_role_flag`, `percentile`.

### Task 1.4: F4 — Apex-tier flag

**Description:** Implement the F4 sub-score by ingesting public rosters: HHMI Investigators, NAS members, NAE members, NAM members, NIH MERIT awardees, Lasker laureates, HHMI Hanna H. Gray Fellows. Each candidate gets a Boolean per roster; F4 sub-score is a small monotonic mapping from the count of memberships to [0, 1]. F4 weight is capped low (0.05) per program overview §16 to prevent famous-PI-overweighting failure.

**Files:**
- `src/aegis/scoring/f4_apex.py`
- `src/aegis/sources/apex_rosters.py` — roster scrapers (these are mostly static HTML or PDFs).
- `src/aegis/scoring/f4_apex_test.py`.

**Implementation Notes:**
- Rosters update annually; ingestion is monthly with a 24-hour staleness budget.
- Identity-link rosters via name + year + institution; require human review for ambiguous matches (small enough that this is feasible).

**Verification:**
- Roster coverage of cohort matches public roster sizes ±2%.
- F4 weight in `Q(c)` composition does not exceed 0.05.

**Design Assertions:**
- `F4Computer.score(candidate) -> F4Score` with `memberships: list[ApexMembership]`, `score: float ∈ [0, 1]`.

### Task 1.5: F5 — Translational impact (Phase 1 subset)

**Description:** Implement the F5 sub-score using NSCLC-translational-relevant signals available in Phase 1: FDA submissions linked via sponsor (parsed from CT.gov sponsor + Drugs@FDA cross-reference), drugs reaching Phase 2 (CT.gov derivation), and guideline citations (NCCN guideline panel rosters; ASCO guideline contributors). Patents are deferred to Phase 2; F5 in Phase 1 is the "non-patent translational impact" subset and is documented as such.

**Files:**
- `src/aegis/scoring/f5_translational.py`
- `src/aegis/sources/drugs_fda.py` — Drugs@FDA bulk ingestion.
- `src/aegis/sources/nccn.py` — NCCN guideline panel scraper (NSCLC panel only in Phase 1).
- `src/aegis/scoring/f5_translational_test.py`.

**Implementation Notes:**
- F5 is documented as a partial-coverage score in Phase 1 (no patents); Phase 2 closes the gap. The score reports a `coverage_caveat` field so consumers know.
- NCCN panel rosters are PDF and require manual update; Phase 1 cadence is per-guideline-version (~yearly).

**Verification:**
- Top-decile F5 contains ≥70% of NCCN NSCLC panel members.

**Design Assertions:**
- `F5Computer.score(candidate) -> F5Score` with `fda_submissions`, `phase2plus_drugs`, `nccn_panel_member: bool`, `coverage_caveat: str`, `percentile`.

### Task 1.6: F6 — Mentorship / lineage

**Description:** Implement the F6 sub-score using Academic Family Tree (academictree.org) data: mentor-mentee edges and inferred lineage depth. F6 also tracks "trainees who became R01 PIs" — for each candidate, count the trainees in their tree who later won R01s. Lineage data is incomplete (~30% biomed coverage); F6 is reported with explicit confidence and downweighted when underlying data is sparse.

**Files:**
- `src/aegis/scoring/f6_lineage.py`
- `src/aegis/sources/academic_tree.py` — public AFT data ingestion.
- `src/aegis/scoring/f6_lineage_test.py`.

**Implementation Notes:**
- Cross-reference AFT names with cohort `candidate_uuid` via probabilistic linkage from Phase 0; track linkage confidence.
- Trainee R01 lookup goes back through RePORTER history.

**Verification:**
- F6 distribution shows expected long-tail (most candidates have 0–2 traceable trainees with R01s).
- Top-decile F6 candidates have ≥3 R01-PI trainees with high probability.

**Design Assertions:**
- `F6Computer.score(candidate) -> F6Score` with `traceable_trainee_count`, `r01_trainee_count`, `data_confidence`, `percentile`.

### Task 1.7: `Q(c)` geometric-mean composition + percentile calibration

**Description:** Compose `Q(c) = ∏ F_i(c)^{w_i}` using the translational weight vector `(F1 .35, F2 .25, F3 .20, F4 .05, F5 .10, F6 .05)`. Weights are loaded from a versioned config; the composition function is decoupled from specific weights. After composition, `Q(c)` is converted to **percentile within specialty cohort** for output stability across queries. Percentile recomputation runs nightly.

**Files:**
- `src/aegis/scoring/quality_prior.py`
- `src/aegis/scoring/quality_prior_test.py`
- `config/aegis/weights/translational_v1.yaml`.

**Implementation Notes:**
- Geometric mean punishes spiky candidates; this is desirable per program overview §7.
- Percentile-within-cohort is what consumers see; raw `Q(c)` is internal.
- Weight versioning is critical for the steady-state relearning loop in Task 1.14.

**Verification:**
- `Q(c)` percentile distribution uniform on cohort.
- Reweighting test: scaling all `w_i` by a constant does not change percentile output (geometric-mean property).

**Design Assertions:**
- Module exports `QualityPrior.compute(candidate: Candidate, weight_vector: WeightVector) -> QualityScore`.

### Task 1.8: Integrity gate — hard rules

**Description:** Implement the hard-zero integrity rules: ingestion of state medical board actions (Phase 1: federation of major-state APIs only), HHS-OIG exclusion list (LEIE), OFAC/SAM, ORI misconduct findings, Retraction Watch DB. Hard zero applies on: license revocation/suspension, federal exclusion, ORI finding within 10 years, retraction in target subdomain for fabrication/falsification (subdomain match via MeSH overlap).

**Files:**
- `src/aegis/integrity/hard_gate.py`
- `src/aegis/sources/leie.py`
- `src/aegis/sources/ofac_sam.py`
- `src/aegis/sources/ori.py`
- `src/aegis/sources/retraction_watch.py`
- `src/aegis/integrity/hard_gate_test.py`.

**Implementation Notes:**
- Subdomain-retraction match uses MeSH overlap ≥0.6 between retracted paper and the query (or, in Phase 1, the cohort's defining MeSH set).
- Hard-zero decisions are logged with the source artifact ID (LEIE entry, ORI finding URL, retraction notice URL); auditability is required.
- Misclassification of "honest error" retractions vs "fabrication/falsification" goes through LLM negative-signal triage (Task 1.9).

**Verification:**
- Synthetic test: planted candidate with ORI finding gets `I(c) = 0`.
- Archetype 4 from §11 gets `I(c) = 0`.

**Design Assertions:**
- `HardGate.evaluate(candidate, target_subdomain: MeshSet) -> HardGateResult` with `is_zero: bool`, `reason: Optional[str]`, `artifact_ref: Optional[ArtifactRef]`.

### Task 1.9: Integrity gate — soft discounts

**Description:** Implement soft discounts: predatory-journal load (Cabells + DOAJ + MEDLINE-indexing triangulation), retractions-outside-subdomain proportional discount, authorship-inconsistency flag, paper-mill signals (Cabanac tortured-phrase detection on titles + abstracts; coordinated-author network density). LLM is used to classify retraction notice text into severity buckets ("fabrication," "honest error," "duplicate publication," "no statement"); LLM output is constrained to the closed enum.

**Files:**
- `src/aegis/integrity/soft_discounts.py`
- `src/aegis/integrity/predatory.py`
- `src/aegis/integrity/papermill.py`
- `src/aegis/integrity/llm_triage.py`
- `src/aegis/integrity/soft_discounts_test.py`.

**Implementation Notes:**
- Cabells is a paid product; if access is unavailable, fall back to non-MEDLINE-indexed + non-DOAJ + heuristic flags. Document the fallback's coverage caveat.
- Discount caps from §8: retraction floor 0.4, predatory floor 0.5, authorship-inconsistency 0.85, paper-mill pending 0.7.
- LLM triage uses a low-temperature constrained-generation pattern; ungrounded outputs are rejected.

**Verification:**
- Archetype 4 from §11 receives the expected predatory-load discount and (combined with hard gate) excludes correctly.
- LLM triage on 50 hand-labeled retraction notices ≥90% agreement with reviewer.

**Design Assertions:**
- `SoftDiscounts.evaluate(candidate, target_subdomain) -> list[SoftDiscount]`.

### Task 1.10: `T(c, q)` topical fit

**Description:** Implement the topical-fit cosine: take the candidate topic vector `v_c` (from Phase 0 artifact-aggregation in §3, recomputed nightly) and the query MeSH vector `v_q` (built per-query, see Task 1.11 sibling code), L2-normalize both, return cosine similarity ∈ [0, 1]. The candidate vector construction is the most subtle piece: per-artifact weights `(w_role · w_venue · w_recency · w_evidence_type)` from §3.

**Files:**
- `src/aegis/scoring/topical_fit.py`
- `src/aegis/scoring/candidate_vector.py`
- `src/aegis/scoring/topical_fit_test.py`.

**Implementation Notes:**
- Per-artifact RCR weighting (used in `w_venue` for papers) is critical: predatory-journal papers contribute ~0 to `v_c` because their RCR is near-floor.
- Candidate vector caching: recompute on artifact-set change, not per-query.
- Sparse-vector representation; do not allocate dense 30K-vectors.

**Verification:**
- Archetype 1 from §11 (Dr. A on PD-L1 NSCLC query) yields `T ≈ 0.78` (within 0.05 tolerance).
- Archetype 4 (Dr. D) — `v_c` is downweighted by predatory load and yields `T < 0.5`.

**Design Assertions:**
- `TopicalFit.compute(candidate_vector, query_vector) -> float ∈ [0, 1]`.

### Task 1.11: `R(c, q)` recency

**Description:** Implement the recency score: sum over candidate's artifacts whose MeSH overlaps the query, of `w_role · w_type · exp(−Δt/τ)`, with default half-life 3 years. Squash via `1 − exp(−A/s)` for a smooth [0, 1] output. Tunable τ per query (chemistry queries can request shorter half-life). Preprints from bioRxiv/medRxiv contribute at 0.6× the peer-reviewed weight.

**Files:**
- `src/aegis/scoring/recency.py`
- `src/aegis/scoring/recency_test.py`.

**Implementation Notes:**
- bioRxiv/medRxiv ingestion is Phase 3 daily; Phase 1 uses Phase 0's monthly-snapshot ingestion as a placeholder. Document the gap.
- Recency must handle the "industry pivot" archetype: Dr. B's recent activity is patents (Phase 2), so Phase 1 R(c, q) for Dr. B will under-score. This is acknowledged in archetype 2's expected scoring under Phase 1.

**Verification:**
- Archetype 1 (Dr. A) yields `R ≈ 0.85`.
- A candidate with no artifacts in the last 5 years yields `R < 0.1`.

**Design Assertions:**
- `Recency.compute(candidate, query: QueryVector, half_life_years: float = 3.0) -> float ∈ [0, 1]`.

### Task 1.12: End-to-end `Rank(c, q)` wiring

**Description:** Wire the full scoring identity: `Rank(c, q) = I(c) · Q(c)^α · T(c, q)^β · R(c, q)^γ` with default exponents α=0.7, β=1.0, γ=0.4 from §9. Produce a ranked output with per-component breakdown, top-3 contributing artifacts per candidate, evidence-trail pointers, and identity-linkage confidence. Hard-zero candidates are excluded from output but retained in audit logs.

**Files:**
- `src/aegis/scoring/rank.py`
- `src/aegis/scoring/result_format.py`
- `src/aegis/scoring/rank_test.py`.

**Implementation Notes:**
- Exponents are loaded from versioned config; default is the cold-start prior.
- Output schema is fixed in this task (Phase 3 surfaces it via API but does not change shape).
- Bootstrap variance (Task 1.15) is computed lazily — not on every query.

**Verification:**
- End-to-end smoke: query "PD-L1 NSCLC biomarker stratification" returns Dr. A in top 5 percentile.
- Archetype 4 (Dr. D) absent from output (hard-zero excluded).

**Design Assertions:**
- `Ranker.rank(query: ParsedQuery, cohort: Cohort, k: int) -> RankedList`.

### Task 1.13: Pairwise expert audit harness

**Description:** Build the audit collection harness that presents an expert reviewer (panel from Prerequisites) with a query plus two candidates and collects pairwise judgments ("for query Q, A more relevant than B?"). Includes session management, rate limiting per reviewer (audit fatigue is real), reviewer-anonymity option, and persistence of every judgment with full evidence shown to the reviewer.

**Files:**
- `src/aegis/audit/harness.py`
- `src/aegis/audit/ui/` — local web UI for reviewers.
- `src/aegis/audit/storage.py`.

**Implementation Notes:**
- Pairs are sampled with active-learning bias toward informative pairs (close `Rank` scores) rather than uniform random; this concentrates labeling effort.
- Reviewer sees the same evidence the system used: top-3 artifacts, MeSH overlap, per-component scores, but NOT the system's predicted ranking — to avoid anchoring.
- Inter-reviewer agreement (Cohen's κ) is computed when overlapping pairs exist.

**Verification:**
- 5 reviewers complete 100 pairs each on the seed cohort within 8 hours total.
- κ ≥ 0.6 across reviewers on overlap.

**Design Assertions:**
- `AuditHarness.next_pair(reviewer: ReviewerId) -> PairwisePrompt`.

### Task 1.14: Plackett–Luce weight learning

**Description:** Fit α, β, γ and per-family weights using collected pairwise judgments via Plackett–Luce / Bradley–Terry. Output is an updated `WeightVector` and exponents with confidence intervals. Refit happens on a schedule (weekly during cold start, monthly steady state) and on demand. Weight updates are versioned; the live system can rollback to a prior version without losing the audit data.

**Files:**
- `src/aegis/learning/plackett_luce.py`
- `src/aegis/learning/refit_scheduler.py`
- `src/aegis/learning/plackett_luce_test.py`.

**Implementation Notes:**
- Use `choix` or implement a small Plackett–Luce log-likelihood with `scipy.optimize`.
- Constrain exponents to reasonable ranges (α ∈ [0.3, 1.2], β ∈ [0.5, 1.5], γ ∈ [0.1, 0.8]) to prevent pathological fits on small data.
- Refit results land in `config/aegis/weights/translational_v{N}.yaml` with provenance.

**Verification:**
- On synthetic data with known ground-truth weights, refit recovers parameters within ±10%.
- Refit on real audit data converges and produces weight CIs.

**Design Assertions:**
- Module exports `PlackettLuceFitter.fit(judgments: list[PairwiseJudgment]) -> FittedWeights`.

### Task 1.15: Score-variance bootstrap

**Description:** Estimate per-candidate score variance via bootstrap resampling of the weight vector (resample from posterior over weights given audit data) and re-rank K times. The resulting distribution per candidate gives a variance band that surfaces in the output as `score_band: (low, high)`. Two adjacent candidates whose bands overlap by >50% are treated as tied for cutoff purposes.

**Files:**
- `src/aegis/scoring/variance.py`
- `src/aegis/scoring/variance_test.py`.

**Implementation Notes:**
- Bootstrap is expensive; we run it offline nightly per cohort, not per query.
- Cache the resampled weight vectors and reuse across queries on the same day.

**Verification:**
- On synthetic data, bootstrap CI brackets ground-truth rank ≥90% of the time.
- Variance bands are present on every output.

**Design Assertions:**
- `Bootstrap.estimate(query, cohort, n_samples: int = 200) -> dict[CandidateUuid, ScoreBand]`.

## Observability and Governance Tasks

### Task 2.1: Per-component score-distribution dashboards

**Description:** Dashboards showing distributions of F1–F6, `Q(c)`, `T(c, q)`, `R(c, q)`, and `Rank(c, q)` across the cohort. Distributions inform whether percentile calibration is working (should be uniform) and whether any component is stuck at the floor or ceiling (a bug signal). Refreshed nightly.

**Files:**
- `src/aegis/observability/score_dist.py`
- Dashboard HTML/JSON in `ops/aegis/dashboards/`.

**Implementation Notes:**
- Histograms with 50 buckets; not just summary stats.
- Anomaly detection: alert if any component's distribution shifts by KS-statistic > 0.1 across nightly runs.

**Verification:**
- Initial run produces uniform percentile distributions.
- Synthetic shift triggers anomaly alert.

### Task 2.2: Apex-list recall regression test

**Description:** Continuous regression test: for each curated apex query (NCCN NSCLC panelist queries, NIH MERIT NSCLC awardee queries, ASCO Young Investigator NSCLC queries), confirm the known apex experts surface in the top-K results. Recall threshold per query, with weekly trend tracking.

**Files:**
- `src/aegis/observability/apex_recall.py`
- `tests/regression/test_apex_recall.py`.

**Implementation Notes:**
- Apex queries are versioned; we don't add/remove them silently because a regression in one query is meaningful.
- Top-K = 50 default.

**Verification:**
- Initial pass: ≥80% recall across apex queries.
- Regression: any drop >5% in a week pages the on-call.

### Task 2.3: Pairwise audit consistency tracking

**Description:** Track inter-reviewer Cohen's κ on overlapping pairs and intra-reviewer consistency on repeated pairs (a small fraction of pairs are deliberately re-shown to the same reviewer to detect drift). Surface low-agreement reviewers for retraining.

**Files:**
- `src/aegis/observability/audit_consistency.py`
- Dashboards.

**Implementation Notes:**
- Re-show fraction set to 5%; tunable.
- Privacy: aggregate statistics across reviewers, but per-reviewer detail visible only to audit-panel admin.

**Verification:**
- Re-show pairs detected and tracked.
- κ computation on synthetic disagreement returns expected values.

### Task 2.4: Integrity-gate hit-rate dashboard

**Description:** Per-day counts of hard-zero exclusions and soft-discount applications, broken down by reason (license revocation, ORI, OFAC, retraction subdomain, predatory load, etc.). False-positive monitoring: any sudden spike in exclusions indicates either real-world events or a bug; we want to distinguish.

**Files:**
- `src/aegis/observability/integrity_dashboard.py`.

**Implementation Notes:**
- Per-reason time series; weekly summaries.
- Contestability hooks (Phase 3) feed back as "false-positive corrections" with audit trail.

**Verification:**
- Synthetic spike triggers alert; per-reason breakdown is correct.

### Task 2.5: Weight-stability tracking across relearning cycles

**Description:** Track how α, β, γ, and per-family weights move across refit cycles. Large jumps (e.g., a family weight changing >25% in one refit) trigger a manual review before the new weights are deployed.

**Files:**
- `src/aegis/observability/weight_stability.py`
- Approval workflow in `ops/aegis/weight_review.md`.

**Implementation Notes:**
- Auto-deploy on small changes; manual gate on large.
- The audit panel can trigger an immediate refit if they see ranking drift.

**Verification:**
- Synthetic large-jump in fit triggers review gate.
- Stable refit auto-deploys correctly.

## Error Handling Tasks

### Task 3.1: Insufficient pairwise data — fallback to default exponents

**Description:** When pairwise judgments are too few or too unbalanced for stable Plackett–Luce fit (CI on α, β, γ exceeds threshold), retain default exponents and surface "weights are still in cold-start prior" in `Rank` output metadata. Block auto-deployment of unstable fits.

**Files:**
- `src/aegis/learning/cold_start_guard.py`.

**Implementation Notes:**
- Threshold: CI half-width on α > 0.2 means the fit is too uncertain.
- Surfacing the metadata in output means downstream consumers know not to over-trust the rankings.

**Verification:**
- Synthetic small-data fit triggers cold-start retention.

### Task 3.2: Integrity false-positive contestability

**Description:** A candidate erroneously hard-zeroed must have a documented contestability path: an audit-panel admin can review the integrity-source artifact and override with a recorded justification. Override is per-candidate, time-stamped, and survives recomputation.

**Files:**
- `src/aegis/integrity/contestability.py`
- Admin UI hook (Phase 3 builds the full UI; Phase 1 is a CLI-driven override).

**Implementation Notes:**
- Override record is append-only with reviewer ID, timestamp, justification.
- Override cannot be silently revoked; revocation requires another override entry.

**Verification:**
- Synthetic erroneous hard-zero gets overridden via CLI; subsequent ranking includes the candidate.

### Task 3.3: Score-collapse handling

**Description:** If all candidates score < a floor (e.g., 0.05), the query expansion or topic-vector construction likely failed. Detect this case, fall back to broader MeSH expansion (rollup one level), and emit a "low-confidence ranking" flag in the result. Never return an empty list silently.

**Files:**
- `src/aegis/scoring/score_collapse.py`.

**Implementation Notes:**
- Floor is configurable; default 0.05.
- Fallback expansion is a single retry; a second collapse returns the cohort's specialty top-K with the flag set.

**Verification:**
- Synthetic mis-expanded query triggers fallback and emits flag.

### Task 3.4: Specialty-classifier ambiguity handling

**Description:** Phase 1 cohort is single-specialty (translational), but the classifier still assigns confidence; below 0.6 confidence, flag the candidate as "specialty-ambiguous" and surface in the evidence trail. In Phase 2 this becomes the trigger for dynamic reassignment; in Phase 1 it is observability only.

**Files:**
- `src/aegis/scoring/specialty_flag.py`.

**Implementation Notes:**
- Phase 1 specialty classifier is rule-based (artifact-mix); Phase 2 introduces ML-based.
- Flag does not change scoring in Phase 1.

**Verification:**
- Industry-pivot candidate (archetype 2 stub) gets ambiguous flag.

## Performance and Scale Tasks

### Task 4.1: Score recomputation strategy

**Description:** `Q(c)` and `v_c` are recomputed nightly per cohort; per-query `T`, `R`, and final `Rank` are computed on demand. Recomputation must be idempotent and resumable. At Phase 1 cohort scale (~5,000 candidates), full recompute takes <10 minutes on a workstation.

**Files:**
- `src/aegis/scheduling/recompute.py`.

**Implementation Notes:**
- Driven by a simple cron; Phase 3 introduces a real scheduler.
- Cohort-scoped; multi-cohort scheduling is Phase 2.

**Verification:**
- Full recompute completes in <10 min.

### Task 4.2: Caching for `v_c` and `Q(c)`

**Description:** Cache candidate vectors and quality priors keyed by candidate UUID + artifact-set hash + weight-vector version. Cache invalidation on artifact-set change or weight-version bump. Cache hit rate target ≥95% on warm cohort.

**Files:**
- `src/aegis/scoring/cache.py`.

**Implementation Notes:**
- Cache backend: local SQLite or Redis; abstracted behind a small interface.
- Artifact-set hash is over the sorted artifact-ID list per candidate.

**Verification:**
- Warm-cache lookup p95 <5ms.

### Task 4.3: Query latency budget

**Description:** Phase 1 query latency target: <500ms p95 for top-50 ranked output on cohort scale, with bootstrap-variance pre-computed offline. Latency budget breakdown: query expansion ≤100ms, topical-fit retrieval ≤200ms, recency + final scoring ≤150ms, formatting ≤50ms.

**Files:**
- `src/aegis/scoring/latency_budget.md` — documented budget.
- Latency assertions in `tests/perf/test_query_latency.py`.

**Implementation Notes:**
- Pre-compute everything that doesn't depend on the query; only `T`, `R`, and final composition are per-query.
- Latency budget is the contract Phase 3's API will rely on.

**Verification:**
- 100-query benchmark: p95 <500ms.

## Testing

- Unit tests on every scoring module; coverage target ≥90% on `scoring/` and `integrity/`.
- Synthetic-data tests for Plackett–Luce fitter (recovers known parameters).
- Archetype regression: Dr. A and Dr. D from §11 hit expected scoring outcomes (Dr. A in top 1%, Dr. D excluded).
- Apex-list recall regression at ≥80% across all curated apex queries.
- Inter-reviewer κ ≥ 0.6 from initial audit panel before refit is trusted.

## Rollback Plan

Phase 1 changes are versioned: weight vectors, exponents, and integrity-gate rules each have a version number, and the scoring pipeline can pin to any version. Rollback to cold-start exponents is a single config flip. Hard-zero rules can be disabled selectively (e.g., revert ORI rule but keep license rule). The audit-panel data is preserved across rollbacks; only the fitted weights change.

## Self-Audit

- Core scoring tasks: 15
- Observability and governance tasks: 5
- Error handling tasks: 4
- Performance and scale tasks: 3
- Total tasks: 27
- Tasks with explicit file targets: 27
- Tasks with verification steps: 27
- Tasks with design assertions: 15 (core tasks)
- Phase 1 closes when: (1) end-to-end `Rank(c, q)` produces archetype-1 in top 1%, archetype-4 excluded; (2) apex-recall regression ≥80%; (3) audit panel produces ≥500 pairwise judgments; (4) Plackett–Luce refit converges with stable CIs; (5) per-component dashboards live and showing uniform percentile distributions.
