# Privacy, Ethics, and Contestability Design

> **Status**: COMPLETE -- Phase 3e implemented 2026-04-27

## Overview

Aegis privacy enforcement, ethics layer, and contestability workflow. This domain covers four production prerequisites:

1. **PHI/HIPAA scanning** -- Rejects data containing protected health information before it enters the scoring pipeline.
2. **Demographic blocklist** -- Strips prohibited demographic fields (gender, race, citizenship, age) at ingestion.
3. **Candidate opt-out** -- Enforces opted-out candidates being excluded from cohort and query results.
4. **Composed privacy gate** -- Single entry point chaining all three checks, fail-closed on errors.
5. **Candidate evidence trail API** -- Three-tier access-controlled evidence endpoint (self/customer/admin).
6. **Contestability endpoint** -- Candidate-initiated corrections with HITL review queue integration.
7. **Customer dispute workflow** -- Customer-driven disputes feeding back as ground truth for weight relearning.

## Current Design

### Privacy Enforcement Layer

The privacy layer consists of three independent runtime gates composed into a single ingestion checkpoint:

**PHI Scanner** (`src/aegis/privacy/phi_scanner.py`):
- Regex pattern matching for structured PHI: SSN (dashed/undashed), DOB, MRN, phone, email, street address
- LLM classifier stub for unstructured text fields (disabled by default; production activation via `enable()`)
- Context-aware filtering: dates only flagged in sensitive-named fields (birth, dob, patient, personal, demographic); bare 9-digit numbers require SSN field context or surrounding text context
- Design principle: false-positives preferred over false-negatives
- Reference: `src/aegis/privacy/phi_scanner.py:70-105` (pattern definitions), `src/aegis/privacy/phi_scanner.py:193-225` (`_check_field` with context logic)

**Demographic Blocklist** (`src/aegis/privacy/demographic_blocklist.py`):
- Blocks fields containing: gender, sex, race, ethnicity, citizenship, nationality, immigration, visa, age, dob, birthdate
- Allowlist prevents false positives on biomedical terms: dosage, lineage, coverage, stage, etc.
- Matching: exact match on short names (sex, age, dob, race), then allowlist check, then substring match
- Reference: `src/aegis/privacy/demographic_blocklist.py:27-78` (constant definitions), `src/aegis/privacy/demographic_blocklist.py:120-130` (`is_blocked` logic)

**Opt-Out Store** (`src/aegis/privacy/opt_out.py`):
- Append-only JSONL store following `ContestabilityStore` pattern from `src/aegis/integrity/contestability.py`
- Latest action determines current state (opt_out/opt_in are reversible)
- `filter_candidates()` removes opted-out UUIDs from query result lists
- Reference: `src/aegis/privacy/opt_out.py:67-79` (store class), `src/aegis/privacy/opt_out.py:106-109` (`filter_candidates`)

**Composed Privacy Gate** (`src/aegis/privacy/gate.py`):
- Single entry point: PHI scan -> demographic strip -> opt-out check
- Fail-closed: exceptions in any check result in rejection, not silent admission
- Bypass detection: `check_bypass_alert()` logs and alerts on circumvention
- Reference: `src/aegis/privacy/gate.py:82-97` (gate class), `src/aegis/privacy/gate.py:99-158` (`check` method with fail-closed)

### API Layer

**Candidate Evidence Trail** (`src/aegis/api/candidate_view.py`):
- `GET /v1/candidates/{uuid}/evidence`
- Three access tiers: self_view (ORCID/NPI verified), customer_view (JWT scoped), admin_view (full)
- Self-verification: ORCID OAuth token or NPI-based signed proof matched against candidate strong keys
- Full trail: artifacts, scores (F1-F6 breakdown), integrity gate result, linkage evidence, affiliation history, contestability history
- Scoped trail: artifacts, aggregate scores, integrity status string, linkage confidence number only
- Every access request audit-logged to in-memory list + optional JSONL file
- Reference: `src/aegis/api/candidate_view.py:148-175` (verify_self_access), `src/aegis/api/candidate_view.py:218-253` (build_full_trail)

**Contestability Endpoint** (`src/aegis/api/contestability.py`):
- `POST /v1/candidates/{uuid}/contests`
- DuckDB-backed queue following `ReviewQueue` pattern from `src/aegis/identity/review_queue.py`
- Categories: affiliation_error, artifact_misattribution, integrity_false_positive, identity_error, score_dispute, other
- Submissions get ELEVATED priority by default
- Priority ordering: urgent > elevated > normal, then FIFO by submitted_at
- Decisions are append-only (multiple decisions per contest allowed for re-review)
- SLA stats: median and p95 resolution days computed from resolved items
- Reference: `src/aegis/api/contestability.py:131-142` (DDL), `src/aegis/api/contestability.py:159-201` (submit/next_for_review)

**Customer Disputes** (`src/aegis/api/customer_disputes.py`):
- `POST /v1/disputes`
- DuckDB-backed admin review queue
- Confirmed disputes generate DisputeFeedback with weight=1.0 (highest confidence ground truth)
- Feedback direction: "downweight" for low_quality/incorrect_ranking/missing_expertise, "flag" for integrity_concern, "review" for other
- `get_all_feedback()` returns all confirmed dispute feedback for consumption by Plackett-Luce weight relearning
- Reference: `src/aegis/api/customer_disputes.py:95-109` (DDL), `src/aegis/api/customer_disputes.py:256-292` (generate_feedback)

**Router** (`src/aegis/api/privacy_contestability_router.py`):
- FastAPI APIRouter with dependency injection for all services
- Contest endpoint does NOT require JWT (candidate-facing; verification via ORCID/NPI in request body)
- Dispute and evidence endpoints require JWT customer token
- Description validation: minimum 20 characters for contest and dispute descriptions
- Reference: `src/aegis/api/privacy_contestability_router.py:87-97` (router factory)

## Design Decisions

### DD-3e-1: False-positive-preferred PHI scanning
**Decision**: PHI scanner uses aggressive pattern matching with context filtering to reduce false positives on publication dates and numeric identifiers, while maintaining a false-positive-preferred bias.
**Rationale**: HIPAA compliance requires catching all PHI. Publication dates (ISO format) are extremely common in biomedical data and would cause unacceptable false positive rates without context filtering. The compromise: dates only flagged in sensitive-named fields, bare 9-digit numbers need SSN context.
**Evidence**: `src/aegis/privacy/phi_scanner.py:97-105` (sensitive field names), `src/aegis/privacy/phi_scanner.py:193-225` (context filtering logic)

### DD-3e-2: Demographic blocklist with biomedical allowlist
**Decision**: Allowlist of biomedical terms (dosage, lineage, coverage, etc.) prevents false positives from the age/sex substring matching.
**Rationale**: "dosage" contains "age", "lineage" is a legitimate biomedical field. Without allowlisting, routine biomedical data would be blocked.
**Evidence**: `src/aegis/privacy/demographic_blocklist.py:61-78` (allowlist), `src/aegis/privacy/demographic_blocklist.py:120-130` (matching order: exact -> allowlist -> substring)

### DD-3e-3: Append-only JSONL for opt-out (same as ContestabilityStore)
**Decision**: Opt-out records stored in append-only JSONL, latest action determines state.
**Rationale**: Consistent with existing ContestabilityStore pattern. Append-only provides full audit trail. No data is ever deleted.
**Evidence**: `src/aegis/privacy/opt_out.py:67-79` (store pattern), `src/aegis/integrity/contestability.py:37-39` (original pattern)

### DD-3e-4: Fail-closed privacy gate
**Decision**: Any exception in PHI scanning, blocklist, or opt-out check results in data rejection, not silent admission.
**Rationale**: Production safety requires that a broken scanner never silently admits PHI. The fail-closed guarantee is tested explicitly.
**Evidence**: `src/aegis/privacy/gate.py:108-125` (try/except with rejection on error), `src/aegis/privacy/gate_test.py` (test_fail_closed_on_error)

### DD-3e-5: Three-tier evidence access control
**Decision**: Self-view (full detail via ORCID/NPI), customer-view (scoped), admin-view (full). Customer gets ScopedEvidenceTrail with limited fields.
**Rationale**: Candidates have a right to inspect their own data (program overview section 15). Customers see only what is relevant to their queries. Admin sees everything for support purposes.
**Evidence**: `src/aegis/api/candidate_view.py:42-55` (access tiers), `src/aegis/api/candidate_view.py:218-253` (full trail), `src/aegis/api/candidate_view.py:255-275` (scoped trail)

### DD-3e-6: DuckDB-backed contestability queue with elevated priority
**Decision**: Contestability items default to ELEVATED priority. Priority ordering: urgent > elevated > normal, then FIFO.
**Rationale**: Candidate-initiated corrections are time-sensitive (5-day median SLA target). Elevated priority ensures they are reviewed before standard review items.
**Evidence**: `src/aegis/api/contestability.py:178-201` (next_for_review with priority ORDER BY)

### DD-3e-7: Confirmed disputes as highest-confidence ground truth
**Decision**: Confirmed customer disputes generate DisputeFeedback with weight=1.0 for the Plackett-Luce weight relearning pipeline.
**Rationale**: A confirmed dispute represents direct empirical evidence from production usage -- the strongest possible signal for ranking quality improvement.
**Evidence**: `src/aegis/api/customer_disputes.py:256-292` (generate_feedback with weight=1.0 and direction logic)

### DD-3e-8: Contestability vs. disputes intentionally separate
**Decision**: Contestability (candidate-driven) and disputes (customer-driven) are separate systems with different trust models and feedback paths.
**Rationale**: Candidates correct their own records (affiliation errors, misattributions). Customers report ranking quality issues. Different verification mechanisms, different review queues, different output paths.
**Evidence**: `src/aegis/api/contestability.py` (ORCID/NPI verification, HITL review), `src/aegis/api/customer_disputes.py` (JWT auth, admin review, weight relearning feedback)
