# Plan: Phase 3e — Privacy, Ethics, and Contestability

> **Status**: COMPLETE -- built 2026-04-27
> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase3e-privacy-contestability.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build the privacy enforcement, ethics layer, and contestability workflow for Aegis Phase 3. This sub-spec covers four tasks from the Phase 3 master plan:

- **Task 1.10** (audit-log API): `GET /v1/candidates/{uuid}/evidence` with ORCID OAuth and NPI access control. Self-views return full detail, customer-views are scoped, admin-views return full. Access requests themselves are audit-logged.
- **Task 1.11** (contestability endpoint and workflow): `POST /v1/candidates/{uuid}/contests`. Candidate-verified via ORCID/NPI. Submissions enter the HITL review queue with elevated priority. Reviewer decisions update the candidate record append-only. 5-day median SLA, 14-day p95.
- **Task 1.12** (privacy and ethics enforcement): PHI/HIPAA scanner on data entering Aegis, demographic-feature blocklist stripping gender/race/citizenship/age at ingestion, candidate opt-out enforcement. PHI scanner uses pattern matching plus LLM classifier for unstructured fields. False-positives preferred over false-negatives. Bypassing any of the three is an alertable event.
- **Task 3.4** (customer dispute workflow): `POST /v1/disputes` from the customer side. Admin queue review. Confirmed disputes feed back as highest-confidence ground truth for weight relearning.

## Objective

When this plan is complete:
1. A candidate evidence trail API at `src/aegis/api/candidate_view.py` serves `GET /v1/candidates/{uuid}/evidence` with three access tiers (self, customer, admin), verified via ORCID OAuth or NPI-based proof, with every access request audit-logged.
2. A contestability endpoint at `src/aegis/api/contestability.py` serves `POST /v1/candidates/{uuid}/contests` for candidate-initiated corrections, routing submissions to the HITL review queue with elevated priority and enforcing an append-only decision trail.
3. A PHI scanner at `src/aegis/privacy/phi_scanner.py` detects PHI/HIPAA-sensitive data via regex patterns plus an LLM classifier for unstructured fields, rejecting data and alerting on hits (false-positives preferred over false-negatives).
4. A demographic blocklist at `src/aegis/privacy/demographic_blocklist.py` strips gender, race, citizenship, and age fields at ingestion time.
5. A candidate opt-out system at `src/aegis/privacy/opt_out.py` enforces opted-out candidates being removed from cohort and excluded from query results.
6. A privacy gate at `src/aegis/privacy/gate.py` composes all three privacy checks (PHI scanner, demographic blocklist, opt-out) into a single ingestion gate, with alerting when any check is bypassed.
7. A customer dispute workflow at `src/aegis/api/customer_disputes.py` serves `POST /v1/disputes` with admin queue review, where confirmed disputes feed back as highest-confidence ground truth for weight relearning.
8. All modules pass mypy strict, ruff lint, and have comprehensive unit tests.

## Problem Statement

Aegis ranks candidates using publicly available data, but production deployment requires three guarantees: (1) candidates can inspect and correct their own evidence trails, (2) no PHI or prohibited demographic data enters the system, and (3) both candidates and customers have structured dispute mechanisms whose outcomes feed back into ranking quality. Without these, Aegis violates its own ethics policy (program overview section 15), exposes legal risk from PHI handling, and lacks the contestability mechanism that anchors candidate trust. The audit-log API, contestability endpoint, privacy enforcement, and customer dispute workflow are all production prerequisites.

## Solution Approach

1. **Access-controlled evidence trail first**: Build the candidate view API with three access tiers (self/customer/admin). Self-authentication uses ORCID OAuth tokens or NPI-based signed proof. Customer authentication reuses the existing JWT from Phase 3b. Admin uses a separate admin JWT. Every access request is logged to the existing audit log from Phase 3b.

2. **Contestability workflow**: Build on the existing `ContestabilityStore` (append-only JSONL at `src/aegis/integrity/contestability.py`) and the `ReviewQueue` (DuckDB-backed HITL queue at `src/aegis/identity/review_queue.py`). The new endpoint accepts structured correction requests from verified candidates, creates a contestability-typed review item with elevated priority in the queue, and routes reviewer decisions back to the ContestabilityStore.

3. **Privacy enforcement layer**: Three independent runtime gates: (a) PHI scanner using regex patterns for SSNs, DOBs, MRNs, phone numbers, addresses plus an LLM classifier for unstructured text fields, (b) demographic blocklist that strips prohibited fields at ingestion, (c) opt-out enforcement that excludes opted-out candidates from all query results. All three compose into a single privacy gate. Bypassing any gate triggers an alert.

4. **Customer dispute workflow**: Customer-facing dispute endpoint reuses the JWT auth from Phase 3b. Disputes land in an admin review queue (new DuckDB table, following the ReviewQueue pattern). Confirmed disputes are tagged as highest-confidence ground truth and exposed to the Plackett-Luce weight relearning pipeline from Phase 1c.

## Relevant Files

### Existing Files (read-only context, do not modify unless noted)

- `src/aegis/identity/review_queue.py` -- `ReviewQueue`, `ReviewItem`, `ReviewDecision` -- DuckDB-backed HITL review queue pattern to follow for contestability and dispute queues
- `src/aegis/identity/review_queue_test.py` -- Test patterns for review queue
- `src/aegis/identity/review_ui/app.py` -- FastAPI router pattern for review endpoints
- `src/aegis/integrity/contestability.py` -- `ContestabilityStore`, `OverrideRecord`, `OverrideAction` -- Append-only JSONL pattern for integrity overrides
- `src/aegis/integrity/hard_gate.py` -- `HardGate`, `HardGateResult` -- Integrity gate that consumes contestability overrides
- `src/aegis/integrity/soft_discounts.py` -- `SoftDiscounts`, `SoftDiscountResult`, `DiscountType`
- `src/aegis/api/auth.py` -- JWT authentication module with `CustomerClaims`, `TokenPayload`, `get_current_customer`, `create_token` (from Phase 3b)
- `src/aegis/api/audit_log.py` -- `AuditLog`, `AuditEntry` -- Append-only JSONL audit logging (from Phase 3b)
- `src/aegis/api/schemas.py` -- Request/response Pydantic models (from Phase 3b)
- `src/aegis/api/server.py` -- FastAPI application factory `create_app()` (from Phase 3b)
- `src/aegis/storage/schema.py` -- `Candidate`, `StrongKeyType`, `AffiliationSpan`, `MeshDescriptor`, `ArtifactRefBundle`
- `src/aegis/storage/candidate_store.py` -- `CandidateStore` DuckDB-backed API
- `src/aegis/learning/plackett_luce.py` -- `PlackettLuceFitter` for weight relearning
- `src/aegis/learning/refit_scheduler.py` -- `RefitScheduler` for triggering refits
- `src/aegis/observability/freshness.py` -- `FreshnessMetrics` pattern for monitoring
- `pyproject.toml` -- Project configuration

### New Files

- `src/aegis/privacy/__init__.py` -- Privacy package init
- `src/aegis/privacy/phi_scanner.py` -- PHI/HIPAA detection via patterns + LLM classifier
- `src/aegis/privacy/phi_scanner_test.py` -- Tests for PHI scanner
- `src/aegis/privacy/demographic_blocklist.py` -- Demographic field stripping at ingestion
- `src/aegis/privacy/demographic_blocklist_test.py` -- Tests for demographic blocklist
- `src/aegis/privacy/opt_out.py` -- Candidate opt-out enforcement
- `src/aegis/privacy/opt_out_test.py` -- Tests for opt-out
- `src/aegis/privacy/gate.py` -- Composed privacy gate (PHI + demographics + opt-out)
- `src/aegis/privacy/gate_test.py` -- Tests for privacy gate
- `src/aegis/api/candidate_view.py` -- Audit-log API with access-controlled evidence trail
- `src/aegis/api/candidate_view_test.py` -- Tests for candidate view API
- `src/aegis/api/contestability.py` -- Contestability endpoint and workflow
- `src/aegis/api/contestability_test.py` -- Tests for contestability
- `src/aegis/api/customer_disputes.py` -- Customer dispute workflow
- `src/aegis/api/customer_disputes_test.py` -- Tests for customer disputes

## Implementation Phases

### Phase 1: Foundation
- Create privacy package scaffold
- Build PHI scanner (pattern matching + LLM classifier stub)
- Build demographic blocklist
- Build opt-out enforcement
- Build composed privacy gate

### Phase 2: Core Implementation
- Build candidate evidence trail API with access control
- Build contestability endpoint and workflow
- Build customer dispute workflow

### Phase 3: Integration & Polish
- Wire new endpoints into FastAPI server
- Run full validation suite
- Update design documentation

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Privacy enforcement layer -- PHI scanner, demographic blocklist, opt-out, composed privacy gate
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: API endpoints -- candidate evidence trail, contestability endpoint, customer disputes, server wiring
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Design Updater
  - Name: design-updater
  - Role: Updates docs/design/privacy.md and docs/design/api.md with code-aligned design decisions after build completes
  - Agent Type: design-updater

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build_v2`.
- Task descriptions must be **exhaustive** -- agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Every task MUST have an `Assigned To` matching a name in Team Members. This is enforced -- tasks without a valid `Assigned To` will not be claimed.
- Start with foundational work, then core implementation, then validation.

### 1. Privacy Package Scaffold and PHI Scanner

- **Task ID**: phi-scanner
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the privacy package and build the PHI/HIPAA scanner that detects protected health information in data entering Aegis. The scanner uses pattern matching for structured fields (SSNs, DOBs, MRNs, phone numbers, addresses) plus an LLM classifier for unstructured text. False-positives are preferred over false-negatives. Any PHI detected rejects the data and triggers an alert.

    ## What to do

    1. Create `src/aegis/privacy/__init__.py`:
       ```python
       """Aegis privacy -- PHI scanning, demographic blocklist, and opt-out enforcement."""

       from __future__ import annotations
       ```

    2. Create `src/aegis/privacy/phi_scanner.py`:

       ```python
       """PHI/HIPAA scanner for data entering Aegis.

       Detects protected health information using:
       1. Regex pattern matching for structured PHI (SSN, DOB, MRN, phone, address)
       2. LLM classifier for unstructured text fields (abstracts, notes)

       Design principle: false-positives preferred over false-negatives.
       Any PHI detection REJECTS the data and triggers an alert.
       """

       from __future__ import annotations

       import logging
       import re
       from datetime import UTC, datetime
       from enum import StrEnum

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Enums:**

       a) `PHIType` (StrEnum):
          - `ssn = "ssn"`
          - `date_of_birth = "date_of_birth"`
          - `medical_record_number = "medical_record_number"`
          - `phone_number = "phone_number"`
          - `street_address = "street_address"`
          - `email_address = "email_address"`
          - `patient_name_context = "patient_name_context"` -- Name appearing in clinical/patient context
          - `unstructured_phi = "unstructured_phi"` -- Detected by LLM in unstructured text

       **Models:**

       a) `PHIDetection` (Pydantic BaseModel, frozen):
          - `phi_type: PHIType`
          - `field_name: str` -- Which field the PHI was found in
          - `matched_text: str` -- The text that matched (redacted for logging: first 3 chars + "***")
          - `confidence: float` -- 0-1, pattern matches are 1.0, LLM detections vary
          - `pattern_name: str | None` -- Name of regex pattern that matched, or "llm_classifier"

       b) `ScanResult` (Pydantic BaseModel, frozen):
          - `contains_phi: bool`
          - `detections: list[PHIDetection]`
          - `fields_scanned: int`
          - `scanned_at: datetime`
          - `alert_triggered: bool` -- True if PHI found (always matches contains_phi)

       c) `ScannerStats` (Pydantic BaseModel, frozen):
          - `total_scans: int`
          - `total_phi_detected: int`
          - `total_fields_scanned: int`
          - `detection_rate: float`
          - `by_type: dict[str, int]` -- Count per PHIType

       **Constants -- regex patterns:**

       ```python
       _PHI_PATTERNS: dict[str, tuple[str, PHIType]] = {
           "ssn_dashed": (r"\b\d{3}-\d{2}-\d{4}\b", PHIType.ssn),
           "ssn_nodash": (r"\b\d{9}\b", PHIType.ssn),
           "dob_mmddyyyy": (r"\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b", PHIType.date_of_birth),
           "dob_iso": (r"\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b", PHIType.date_of_birth),
           "mrn_pattern": (r"\bMRN[\s:#-]*\d{5,12}\b", PHIType.medical_record_number),
           "phone_us": (r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", PHIType.phone_number),
           "email": (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", PHIType.email_address),
           "street_address": (r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s+){1,3}(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Lane|Ln|Way|Court|Ct)\b", PHIType.street_address),
       }
       ```

       IMPORTANT: The `dob_iso` pattern will match date strings like "2024-01-15". In biomedical data, publication dates are common and NOT PHI. To reduce false positives on dates while still preferring false positives over false negatives: only flag dates that appear in fields whose name contains "birth", "dob", "patient", "personal", or "demographic". For all other fields, only flag dates if they appear alongside other PHI indicators (SSN, MRN, phone). Implement this logic in `_check_field` by accepting a `field_name` parameter and checking it against a set of sensitive field name substrings: `_SENSITIVE_FIELD_NAMES = {"birth", "dob", "patient", "personal", "demographic", "ssn", "mrn"}`.

       For the `ssn_nodash` pattern (bare 9-digit numbers), add context filtering: only flag if the field name contains "ssn", "social", "tax", or "identifier", OR if the surrounding text within 20 characters contains "SSN", "social security", or "tax id" (case-insensitive). This reduces false positives from PMIDs and other numeric identifiers.

       **Class: `LLMPHIClassifier`**

       ```python
       class LLMPHIClassifier:
           """LLM-based PHI classifier for unstructured text.

           Uses an LLM to detect PHI in free-text fields like abstracts,
           notes, and descriptions. Stub implementation for initial build;
           production uses Anthropic tool-use classification.
           """

           def __init__(self) -> None:
               self._enabled = False  # Disabled by default; enable in production

           def classify(self, text: str, field_name: str) -> list[PHIDetection]:
               """Classify unstructured text for PHI content.

               Stub: returns empty list. Production implementation would:
               1. Call Anthropic API with tool-use for structured PHI detection
               2. Parse tool response for PHI categories
               3. Return PHIDetection list with confidence scores

               When enabled, scans for:
               - Patient names in clinical context
               - Medical record references
               - Treatment/diagnosis details tied to identifiable individuals
               - Any other HIPAA-defined PHI categories
               """
               if not self._enabled:
                   return []

               # Production implementation placeholder:
               # client = Anthropic()
               # response = client.messages.create(
               #     model="claude-sonnet-4-20250514",
               #     tools=[_phi_detection_tool_schema()],
               #     ...
               # )
               return []

           def enable(self) -> None:
               """Enable LLM classification (requires API key)."""
               self._enabled = True

           @property
           def is_enabled(self) -> bool:
               return self._enabled
       ```

       **Class: `PHIScanner`**

       ```python
       class PHIScanner:
           """Scan data fields for PHI/HIPAA-sensitive content.

           Combines regex pattern matching for structured PHI with LLM
           classification for unstructured text. Rejects data containing
           PHI and triggers alerts.
           """

           def __init__(
               self,
               *,
               llm_classifier: LLMPHIClassifier | None = None,
               alert_callback: Any | None = None,
           ) -> None:
               self._llm = llm_classifier or LLMPHIClassifier()
               self._alert_callback = alert_callback  # Callable[[ScanResult], None]
               self._compiled_patterns: dict[str, tuple[re.Pattern[str], PHIType]] = {
                   name: (re.compile(pattern, re.IGNORECASE), phi_type)
                   for name, (pattern, phi_type) in _PHI_PATTERNS.items()
               }
               self._total_scans = 0
               self._total_phi = 0
               self._total_fields = 0
               self._by_type: dict[str, int] = {}
       ```

       **Methods:**

       a) `_redact(self, text: str) -> str`:
          - Return first 3 chars + "***" for logging. If text shorter than 3 chars, return "***".

       b) `_check_field(self, field_name: str, value: str) -> list[PHIDetection]`:
          - Run each compiled regex pattern against the value.
          - For `dob_iso` and `dob_mmddyyyy`: only flag if field_name (lowercased) contains any substring from `_SENSITIVE_FIELD_NAMES`.
          - For `ssn_nodash`: only flag if field_name (lowercased) contains "ssn", "social", "tax", or "identifier", OR if the text within 20 characters of the match contains "SSN", "social security", or "tax id" (case-insensitive).
          - For all other patterns: flag on any match.
          - Return list of PHIDetection with confidence=1.0 for pattern matches.

       c) `_check_unstructured(self, field_name: str, value: str) -> list[PHIDetection]`:
          - If value length > 50 chars (likely unstructured text): call LLM classifier.
          - Return LLM detections.

       d) `scan(self, data: dict[str, str]) -> ScanResult`:
          - For each field in data: run `_check_field` and `_check_unstructured`.
          - Aggregate all detections.
          - Set `contains_phi = len(detections) > 0`.
          - Set `alert_triggered = contains_phi`.
          - If alert_triggered and self._alert_callback: call callback.
          - Update stats.
          - Return ScanResult.

       e) `scan_single(self, field_name: str, value: str) -> list[PHIDetection]`:
          - Convenience: scan a single field. Returns list of detections.

       f) `get_stats(self) -> ScannerStats`:
          - Return current stats.

       Use `from typing import Any` for the alert_callback type hint.

    3. Create `src/aegis/privacy/phi_scanner_test.py` with tests:

       a) `test_detect_ssn_dashed`: Scan {"ssn_field": "123-45-6789"}. Verify contains_phi=True, detection type=ssn.

       b) `test_detect_ssn_no_context_ignored`: Scan {"notes": "123456789"}. 9-digit number in generic field should NOT be flagged (context filter). Verify contains_phi=False.

       c) `test_detect_ssn_in_ssn_field`: Scan {"ssn_number": "123456789"}. Field name contains "ssn" so should be flagged. Verify contains_phi=True.

       d) `test_detect_phone`: Scan {"contact": "(555) 123-4567"}. Verify detection type=phone_number.

       e) `test_detect_email`: Scan {"email_field": "patient@hospital.com"}. Verify detection type=email_address.

       f) `test_detect_mrn`: Scan {"record": "MRN: 12345678"}. Verify detection type=medical_record_number.

       g) `test_date_in_publication_field_not_flagged`: Scan {"publication_date": "2024-01-15"}. Publication date in non-sensitive field should NOT be flagged. Verify contains_phi=False.

       h) `test_date_in_dob_field_flagged`: Scan {"date_of_birth": "01/15/1990"}. DOB in sensitive field should be flagged. Verify contains_phi=True.

       i) `test_clean_data_no_phi`: Scan {"name": "Jane Smith", "affiliation": "Harvard Medical School", "pmid": "12345678"}. No PHI patterns. Verify contains_phi=False, detections empty.

       j) `test_multiple_phi_in_one_record`: Scan {"ssn_field": "123-45-6789", "contact": "(555) 123-4567", "email_field": "patient@hospital.com"}. Verify 3 detections.

       k) `test_redact_long_text`: PHIScanner instance. Call _redact("123-45-6789"). Verify returns "123***".

       l) `test_redact_short_text`: Call _redact("ab"). Verify returns "***".

       m) `test_alert_callback_called`: Create scanner with mock callback. Scan PHI data. Verify callback was called with ScanResult.

       n) `test_stats_tracking`: Scan 3 records (2 with PHI, 1 clean). Verify stats: total_scans=3, total_phi_detected=2.

       o) `test_llm_classifier_disabled_by_default`: Create LLMPHIClassifier(). Verify is_enabled=False. classify() returns empty list.

       p) `test_scan_result_model`: Create ScanResult with all fields. Verify frozen.

       Use `from __future__ import annotations`, `import pytest`, `from unittest.mock import MagicMock`.

    ## Files to create
    - `src/aegis/privacy/__init__.py`
    - `src/aegis/privacy/phi_scanner.py`
    - `src/aegis/privacy/phi_scanner_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `StrEnum` for enumerations (same pattern as `StrongKeyType` in `src/aegis/storage/schema.py` and `DiscountType` in `src/aegis/integrity/soft_discounts.py`)
    - Logger at module level: `logger = logging.getLogger(__name__)`
    - Test files colocated with source (same pattern as `src/aegis/identity/review_queue_test.py`)
    - Compiled regex patterns stored as class attributes for performance

    ## Acceptance criteria
    - `src/aegis/privacy/__init__.py` exists and is importable
    - `src/aegis/privacy/phi_scanner.py` exports PHIScanner, PHIDetection, ScanResult, PHIType, LLMPHIClassifier, ScannerStats
    - SSN (dashed) detected in any field
    - SSN (no dash, 9-digit) only detected in SSN-named fields or with SSN context
    - Dates only flagged in sensitive-named fields (birth, dob, patient, etc.)
    - Phone, email, MRN detected
    - Clean biomedical data (names, affiliations, PMIDs) passes without false positives
    - Alert callback invoked on PHI detection
    - LLM classifier disabled by default (stub)
    - All 16 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/phi_scanner_test.py -v && uv run mypy src/aegis/privacy/phi_scanner.py && uv run ruff check src/aegis/privacy/phi_scanner.py src/aegis/privacy/__init__.py
    ```

### 2. Demographic Blocklist

- **Task ID**: demographic-blocklist
- **Role**: builder
- **Depends On**: phi-scanner
- **Assigned To**: builder-1
- **Description**: |
    Build the demographic-feature blocklist that strips prohibited fields (gender, race, citizenship, age) at ingestion time. This enforces the program overview section 15 ethics policy: demographic features that could introduce bias must never enter the scoring pipeline.

    ## What to do

    1. Create `src/aegis/privacy/demographic_blocklist.py`:

       ```python
       """Demographic feature blocklist: strips prohibited fields at ingestion.

       Per program overview section 15, these demographic features must never
       enter the scoring pipeline:
       - Gender / sex
       - Race / ethnicity
       - Citizenship / nationality / immigration status
       - Age / date of birth (as a standalone field; publication dates are allowed)

       Fields are stripped at ingestion. Any attempt to bypass triggers an alert.
       """

       from __future__ import annotations

       import logging
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Constants:**

       ```python
       # Blocklisted field name substrings (case-insensitive matching).
       # If a field name contains any of these substrings, it is stripped.
       _BLOCKED_SUBSTRINGS: frozenset[str] = frozenset({
           "gender", "sex",
           "race", "ethnicity", "ethnic",
           "citizenship", "nationality", "immigration", "visa",
           "age", "date_of_birth", "dob", "birth_date", "birthdate",
       })

       # Exact field names that are blocked (case-insensitive).
       # These catch short names that substring matching might miss.
       _BLOCKED_EXACT: frozenset[str] = frozenset({
           "sex", "age", "dob", "race",
       })

       # Field names that are ALLOWED even if they contain a blocked substring.
       # Example: "dosage" contains "age", "page" contains "age".
       _ALLOWLIST_SUBSTRINGS: frozenset[str] = frozenset({
           "dosage", "page", "passage", "stage", "storage", "usage",
           "average", "coverage", "leverage", "lineage", "percentage",
           "voltage", "shortage", "manage", "message", "package",
           "image", "language", "damage", "garbage", "baggage",
           "sextet",  # edge case: musical term
       })
       ```

       **Models:**

       a) `BlocklistResult` (Pydantic BaseModel, frozen):
          - `original_field_count: int`
          - `stripped_field_count: int`
          - `stripped_fields: list[str]` -- Names of fields that were removed
          - `remaining_fields: list[str]` -- Names of fields that passed
          - `cleaned_data: dict[str, str]` -- Data with blocked fields removed
          - `timestamp: datetime`

       b) `BlocklistStats` (Pydantic BaseModel, frozen):
          - `total_records_processed: int`
          - `total_fields_stripped: int`
          - `stripped_by_field: dict[str, int]` -- Count per stripped field name

       **Class: `DemographicBlocklist`**

       ```python
       class DemographicBlocklist:
           """Strip prohibited demographic fields from ingestion data.

           Matching is case-insensitive. A field is blocked if:
           1. Its lowercased name exactly matches a blocked name, OR
           2. Its lowercased name contains a blocked substring AND is NOT
              in the allowlist (to avoid false positives like "dosage").
           """

           def __init__(
               self,
               *,
               extra_blocked: frozenset[str] | None = None,
               alert_callback: Any | None = None,
           ) -> None:
               self._blocked_substrings = _BLOCKED_SUBSTRINGS | (extra_blocked or frozenset())
               self._alert_callback = alert_callback
               self._total_records = 0
               self._total_stripped = 0
               self._stripped_by_field: dict[str, int] = {}
       ```

       **Methods:**

       a) `is_blocked(self, field_name: str) -> bool`:
          - Lowercase the field name.
          - If it exactly matches an entry in `_BLOCKED_EXACT`: return True.
          - If the lowercased name matches any entry in `_ALLOWLIST_SUBSTRINGS` (check if lowercased name is in allowlist): return False.
          - If the lowercased name contains any substring from `_blocked_substrings`: return True.
          - Otherwise: return False.

       b) `strip(self, data: dict[str, str]) -> BlocklistResult`:
          - For each field: check `is_blocked(field_name)`.
          - Build cleaned_data with only non-blocked fields.
          - If any fields stripped and alert_callback: call callback with stripped field names.
          - Update stats.
          - Return BlocklistResult.

       c) `get_stats(self) -> BlocklistStats`:
          - Return current stats.

       Use `from typing import Any` for the alert_callback type hint.

    2. Create `src/aegis/privacy/demographic_blocklist_test.py` with tests:

       a) `test_block_gender`: is_blocked("gender") returns True. is_blocked("Gender") returns True.

       b) `test_block_race`: is_blocked("race") returns True. is_blocked("ethnicity") returns True.

       c) `test_block_citizenship`: is_blocked("citizenship_status") returns True.

       d) `test_block_age_exact`: is_blocked("age") returns True.

       e) `test_allow_dosage`: is_blocked("dosage") returns False. The word "dosage" contains "age" but is allowlisted.

       f) `test_allow_coverage`: is_blocked("coverage") returns False.

       g) `test_allow_lineage`: is_blocked("lineage") returns False. Important: "lineage" is a legitimate biomedical field.

       h) `test_strip_removes_blocked_fields`: Strip {"name": "Jane", "gender": "F", "affiliation": "Harvard", "race": "Asian"}. Verify cleaned_data has only "name" and "affiliation". stripped_fields contains "gender" and "race".

       i) `test_strip_preserves_clean_data`: Strip {"name": "Jane", "pmid": "12345", "affiliation": "MIT"}. All fields preserved. stripped_field_count=0.

       j) `test_strip_case_insensitive`: Strip {"Gender": "M", "RACE": "White"}. Both stripped.

       k) `test_extra_blocked_fields`: Create blocklist with extra_blocked=frozenset({"religion"}). is_blocked("religion") returns True.

       l) `test_alert_callback_on_strip`: Create blocklist with mock callback. Strip data with blocked field. Verify callback called.

       m) `test_stats_tracking`: Process 3 records. Verify stats accurate.

       n) `test_blocklist_result_model`: Create BlocklistResult with all fields. Verify frozen.

       Use `from __future__ import annotations`, `import pytest`, `from unittest.mock import MagicMock`.

    ## Files to create
    - `src/aegis/privacy/demographic_blocklist.py`
    - `src/aegis/privacy/demographic_blocklist_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `frozenset` for immutable constant sets
    - Logger at module level
    - Case-insensitive matching throughout

    ## Acceptance criteria
    - Gender, race, citizenship, age fields blocked
    - Allowlist prevents false positives (dosage, coverage, lineage, etc.)
    - Extra blocked fields configurable
    - Alert callback on strip
    - Stats tracking accurate
    - All 14 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/demographic_blocklist_test.py -v && uv run mypy src/aegis/privacy/demographic_blocklist.py && uv run ruff check src/aegis/privacy/demographic_blocklist.py
    ```

### 3. Candidate Opt-Out Enforcement

- **Task ID**: opt-out
- **Role**: builder
- **Depends On**: phi-scanner
- **Assigned To**: builder-1
- **Description**: |
    Build the candidate opt-out system. Opted-out candidates are removed from the active cohort and excluded from all query results until they re-opt-in. Opt-out is reversible by the candidate but defaults to permanent until reversed. Bypassing opt-out enforcement is an alertable event.

    ## What to do

    1. Create `src/aegis/privacy/opt_out.py`:

       ```python
       """Candidate opt-out enforcement.

       Opted-out candidates are excluded from the active cohort and from
       all query results. Opt-out is reversible by the candidate.
       Defaults to permanent until explicitly reversed.
       Bypassing opt-out is an alertable event.
       """

       from __future__ import annotations

       import json
       import logging
       import uuid as _uuid
       from datetime import UTC, datetime
       from enum import StrEnum
       from pathlib import Path
       from typing import Any

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Enums:**

       a) `OptOutAction` (StrEnum):
          - `opt_out = "opt_out"`
          - `opt_in = "opt_in"` -- Re-opt-in (reversal)

       **Models:**

       a) `OptOutRecord` (Pydantic BaseModel, frozen):
          - `record_id: str`
          - `candidate_uuid: str`
          - `action: OptOutAction`
          - `reason: str | None` -- Optional reason from the candidate
          - `verified_via: str` -- "orcid", "npi", "admin"
          - `timestamp: datetime`

       b) `OptOutStatus` (Pydantic BaseModel, frozen):
          - `candidate_uuid: str`
          - `is_opted_out: bool`
          - `last_action: OptOutAction | None`
          - `last_action_at: datetime | None`
          - `history_count: int`

       c) `OptOutStats` (Pydantic BaseModel, frozen):
          - `total_opted_out: int`
          - `total_opt_in_reversals: int`
          - `current_opted_out_count: int`

       **Class: `OptOutStore`**

       Follow the exact append-only JSONL pattern from `src/aegis/integrity/contestability.py`:

       ```python
       class OptOutStore:
           """Append-only JSONL store for candidate opt-out records.

           Follows the ContestabilityStore pattern: append-only writes,
           latest action determines current state.
           """

           def __init__(
               self,
               *,
               storage_path: Path,
               alert_callback: Any | None = None,
           ) -> None:
               self._path = storage_path
               self._alert_callback = alert_callback
       ```

       **Methods:**

       a) `opt_out(self, *, candidate_uuid: str, verified_via: str, reason: str | None = None) -> OptOutRecord`:
          - Create record with action=opt_out. Append to JSONL. Return record.

       b) `opt_in(self, *, candidate_uuid: str, verified_via: str, reason: str | None = None) -> OptOutRecord`:
          - Create record with action=opt_in. Append to JSONL. Return record.

       c) `is_opted_out(self, candidate_uuid: str) -> bool`:
          - Load history for candidate. Return True if latest action is opt_out.

       d) `get_status(self, candidate_uuid: str) -> OptOutStatus`:
          - Return full status including history count.

       e) `get_all_opted_out(self) -> set[str]`:
          - Return set of all candidate UUIDs currently opted out.
          - Load all records, for each candidate track latest action, return those whose latest is opt_out.

       f) `filter_candidates(self, candidate_uuids: list[str]) -> list[str]`:
          - Filter a list of candidate UUIDs, removing any that are opted out.
          - If any opted-out candidate was in the input and no filtering happened (i.e., bypass), call alert_callback.
          - Return filtered list.

       g) `get_history(self, candidate_uuid: str) -> list[OptOutRecord]`:
          - Return all records for a candidate in chronological order.

       h) `load_all(self) -> list[OptOutRecord]`:
          - Load all records from JSONL (same pattern as ContestabilityStore.load_all).

       i) `get_stats(self) -> OptOutStats`:
          - Return aggregate stats.

    2. Create `src/aegis/privacy/opt_out_test.py` with tests:

       a) `test_opt_out(tmp_path)`: Create store. Opt out candidate. is_opted_out returns True.

       b) `test_opt_in_reversal(tmp_path)`: Opt out then opt in. is_opted_out returns False.

       c) `test_default_not_opted_out(tmp_path)`: No records for candidate. is_opted_out returns False.

       d) `test_get_all_opted_out(tmp_path)`: Opt out 3 candidates, opt in 1. get_all_opted_out returns 2.

       e) `test_filter_candidates(tmp_path)`: Opt out "cand-2". filter_candidates(["cand-1", "cand-2", "cand-3"]) returns ["cand-1", "cand-3"].

       f) `test_get_status(tmp_path)`: Opt out, then opt in. get_status shows is_opted_out=False, history_count=2.

       g) `test_get_history(tmp_path)`: Opt out, opt in, opt out again. History has 3 records in order.

       h) `test_append_only_persistence(tmp_path)`: Create store, opt out. Create new store with same path. is_opted_out still True.

       i) `test_opt_out_record_model`: Create OptOutRecord with all fields. Verify frozen.

       j) `test_stats(tmp_path)`: Opt out 3, opt in 1. Stats: current_opted_out_count=2, total_opt_in_reversals=1.

       Use `from __future__ import annotations`, `import pytest`.

    ## Files to create
    - `src/aegis/privacy/opt_out.py`
    - `src/aegis/privacy/opt_out_test.py`

    ## Code patterns to follow
    - Exact append-only JSONL pattern from `src/aegis/integrity/contestability.py`
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `StrEnum` for enumerations
    - Logger at module level
    - `uuid.uuid4().hex` for record IDs (same as ContestabilityStore)

    ## Acceptance criteria
    - Opt-out persisted in append-only JSONL
    - Opt-in reversal works
    - get_all_opted_out returns correct set
    - filter_candidates removes opted-out candidates
    - History preserved chronologically
    - Persistence across store instances
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/opt_out_test.py -v && uv run mypy src/aegis/privacy/opt_out.py && uv run ruff check src/aegis/privacy/opt_out.py
    ```

### 4. Composed Privacy Gate

- **Task ID**: privacy-gate
- **Role**: builder
- **Depends On**: phi-scanner, demographic-blocklist, opt-out
- **Assigned To**: builder-1
- **Description**: |
    Build the composed privacy gate that chains PHI scanner, demographic blocklist, and opt-out enforcement into a single ingestion gate. Bypassing any of the three checks is an alertable event. This is the single entry point for all data entering Aegis.

    ## What to do

    1. Create `src/aegis/privacy/gate.py`:

       ```python
       """Composed privacy gate: single entry point for all data entering Aegis.

       Chains three runtime checks:
       1. PHI/HIPAA scanner -- rejects data containing protected health information
       2. Demographic blocklist -- strips prohibited demographic fields
       3. Opt-out enforcement -- excludes opted-out candidates from results

       Bypassing ANY check is an alertable event. The gate logs all decisions
       for auditability.
       """

       from __future__ import annotations

       import logging
       from datetime import UTC, datetime
       from enum import StrEnum
       from typing import Any

       from pydantic import BaseModel, ConfigDict

       from aegis.privacy.demographic_blocklist import BlocklistResult, DemographicBlocklist
       from aegis.privacy.opt_out import OptOutStore
       from aegis.privacy.phi_scanner import PHIScanner, ScanResult

       logger = logging.getLogger(__name__)
       ```

       **Enums:**

       a) `GateDecision` (StrEnum):
          - `allowed = "allowed"` -- Data passed all checks
          - `rejected_phi = "rejected_phi"` -- Rejected due to PHI detection
          - `stripped = "stripped"` -- Allowed after stripping demographic fields
          - `excluded_opt_out = "excluded_opt_out"` -- Candidate is opted out

       **Models:**

       a) `GateResult` (Pydantic BaseModel, frozen):
          - `decision: GateDecision`
          - `candidate_uuid: str | None` -- Set if opt-out check was relevant
          - `phi_scan: ScanResult | None` -- PHI scan result
          - `blocklist_result: BlocklistResult | None` -- Demographic strip result
          - `opted_out: bool`
          - `cleaned_data: dict[str, str] | None` -- Data after demographic stripping (None if rejected)
          - `timestamp: datetime`
          - `alerts: list[str]` -- Any alerts triggered

       b) `GateStats` (Pydantic BaseModel, frozen):
          - `total_checked: int`
          - `total_allowed: int`
          - `total_rejected_phi: int`
          - `total_stripped: int`
          - `total_excluded_opt_out: int`
          - `bypass_alerts: int`

       **Class: `PrivacyGate`**

       ```python
       class PrivacyGate:
           """Composed privacy gate for data entering Aegis.

           All data must pass through this gate before entering the scoring
           pipeline. The gate is fail-closed: any error in the checks
           results in rejection rather than silent admission.
           """

           def __init__(
               self,
               *,
               phi_scanner: PHIScanner,
               blocklist: DemographicBlocklist,
               opt_out_store: OptOutStore,
               alert_callback: Any | None = None,
           ) -> None:
               self._phi = phi_scanner
               self._blocklist = blocklist
               self._opt_out = opt_out_store
               self._alert_callback = alert_callback
               self._total_checked = 0
               self._total_allowed = 0
               self._total_rejected_phi = 0
               self._total_stripped = 0
               self._total_excluded_opt_out = 0
               self._bypass_alerts = 0
       ```

       **Methods:**

       a) `check(self, *, data: dict[str, str], candidate_uuid: str | None = None) -> GateResult`:
          - Step 1: PHI scan. If PHI found: return rejected_phi immediately.
          - Step 2: Demographic blocklist strip. Strip prohibited fields.
          - Step 3: If candidate_uuid provided, check opt-out. If opted out: return excluded_opt_out.
          - If data passes all checks: return allowed (or stripped if any fields were removed).
          - Update stats.
          - Return GateResult with all check results populated.

       b) `check_bypass_alert(self, *, reason: str) -> None`:
          - Called when a bypass is detected (e.g., data entered without going through the gate).
          - Increment bypass_alerts counter.
          - Log error: "PRIVACY GATE BYPASS: {reason}".
          - If alert_callback: call it.

       c) `get_stats(self) -> GateStats`:
          - Return current stats.

    2. Create `src/aegis/privacy/gate_test.py` with tests:

       a) `test_clean_data_allowed(tmp_path)`: Data with no PHI, no demographic fields, no opted-out candidate. Decision=allowed.

       b) `test_phi_rejected(tmp_path)`: Data with SSN. Decision=rejected_phi. cleaned_data is None.

       c) `test_demographic_stripped(tmp_path)`: Data with gender field. Decision=stripped. cleaned_data has gender removed.

       d) `test_opted_out_excluded(tmp_path)`: Candidate is opted out. Decision=excluded_opt_out.

       e) `test_phi_takes_priority(tmp_path)`: Data with both PHI and demographic fields. Decision=rejected_phi (PHI check runs first).

       f) `test_strip_then_allow(tmp_path)`: Data with demographic field but no PHI. After strip: decision=stripped, cleaned_data has the field removed but other fields present.

       g) `test_bypass_alert(tmp_path)`: Call check_bypass_alert. Verify bypass_alerts incremented. Verify alert_callback called.

       h) `test_stats(tmp_path)`: Process 4 records: 1 clean, 1 PHI, 1 demographic, 1 opt-out. Verify stats.

       i) `test_gate_result_model`: Create GateResult with all fields. Verify frozen.

       j) `test_fail_closed_on_error(tmp_path)`: Create gate with a PHI scanner that raises an exception (mock). The gate should catch the error and reject rather than allow. (Implement this by wrapping the scan call in try/except in the check method, returning rejected_phi on error with an alert.)

       For each test, create the gate components:
       ```python
       from aegis.privacy.phi_scanner import PHIScanner
       from aegis.privacy.demographic_blocklist import DemographicBlocklist
       from aegis.privacy.opt_out import OptOutStore

       scanner = PHIScanner()
       blocklist = DemographicBlocklist()
       opt_out_store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
       gate = PrivacyGate(
           phi_scanner=scanner,
           blocklist=blocklist,
           opt_out_store=opt_out_store,
       )
       ```

    ## Files to create
    - `src/aegis/privacy/gate.py`
    - `src/aegis/privacy/gate_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - Fail-closed: errors result in rejection, not silent admission
    - Logger at module level

    ## Acceptance criteria
    - Clean data passes gate
    - PHI data rejected (takes priority over other checks)
    - Demographic fields stripped
    - Opted-out candidates excluded
    - Bypass alert mechanism works
    - Fail-closed on errors
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/gate_test.py -v && uv run mypy src/aegis/privacy/gate.py && uv run ruff check src/aegis/privacy/gate.py
    ```

### 5. Candidate Evidence Trail API (Audit-Log API)

- **Task ID**: candidate-evidence-api
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the candidate evidence trail API: `GET /v1/candidates/{uuid}/evidence`. This endpoint returns a structured view of every artifact, score component, integrity decision, and linkage decision affecting a candidate. Access control has three tiers: self-view (full detail, verified via ORCID OAuth or NPI), customer-view (scoped to their access), admin-view (full detail). Every access request is itself audit-logged.

    This implements Phase 3 master plan Task 1.10.

    ## What to do

    1. Create `src/aegis/api/candidate_view.py`:

       ```python
       """Candidate evidence trail API with access-controlled views.

       GET /v1/candidates/{uuid}/evidence

       Access tiers:
       - Self-view (ORCID/NPI verified): full detail -- all artifacts, all scores,
         all integrity decisions, all linkage decisions
       - Customer-view (JWT): scoped to artifacts and scores relevant to queries
         the customer has made
       - Admin-view: full detail (same as self)

       Every access request is audit-logged regardless of tier.
       Implements program overview section 15 candidate-transparency promise.
       """

       from __future__ import annotations

       import logging
       import uuid as _uuid
       from datetime import UTC, datetime
       from enum import StrEnum
       from typing import Any

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Enums:**

       a) `AccessTier` (StrEnum):
          - `self_view = "self_view"` -- Candidate viewing their own data
          - `customer_view = "customer_view"` -- Customer with JWT
          - `admin_view = "admin_view"` -- Admin with elevated JWT

       b) `VerificationMethod` (StrEnum):
          - `orcid_oauth = "orcid_oauth"`
          - `npi_proof = "npi_proof"`
          - `jwt_customer = "jwt_customer"`
          - `jwt_admin = "jwt_admin"`

       **Models:**

       a) `AccessRequest` (Pydantic BaseModel, frozen):
          - `request_id: str`
          - `candidate_uuid: str`
          - `requester_id: str` -- ORCID, NPI, or customer_id
          - `access_tier: AccessTier`
          - `verification_method: VerificationMethod`
          - `timestamp: datetime`
          - `granted: bool`
          - `denial_reason: str | None`

       b) `ArtifactEvidence` (Pydantic BaseModel, frozen):
          - `artifact_type: str` -- "pmid", "nct_id", "patent_id", "grant_id"
          - `identifier: str`
          - `title: str | None`
          - `contribution_to_score: float | None` -- How much this artifact contributed
          - `source: str` -- Which data source provided it
          - `linked_at: datetime | None`

       c) `ScoreEvidence` (Pydantic BaseModel, frozen):
          - `component: str` -- "quality_prior", "topical_fit", "recency", "integrity"
          - `value: float`
          - `detail: str` -- Human-readable explanation
          - `factors: dict[str, float]` -- Sub-factor breakdown (e.g., F1-F6 for quality_prior)

       d) `IntegrityEvidence` (Pydantic BaseModel, frozen):
          - `gate_result: str` -- "passed", "hard_zero", "soft_discount"
          - `checks_evaluated: int`
          - `discounts: list[dict[str, Any]]` -- Soft discount details
          - `overrides: list[dict[str, Any]]` -- Contestability override history

       e) `LinkageEvidence` (Pydantic BaseModel, frozen):
          - `confidence: float`
          - `strong_keys: dict[str, str]` -- ORCID, NPI, etc.
          - `linked_artifacts_count: int`
          - `name_variants: list[str]`

       f) `CandidateEvidenceTrail` (Pydantic BaseModel, frozen):
          - `candidate_uuid: str`
          - `candidate_name: str`
          - `access_tier: AccessTier`
          - `artifacts: list[ArtifactEvidence]`
          - `scores: list[ScoreEvidence]`
          - `integrity: IntegrityEvidence`
          - `linkage: LinkageEvidence`
          - `affiliation_history: list[dict[str, Any]]`
          - `opt_out_status: bool`
          - `contestability_history: list[dict[str, Any]]`
          - `generated_at: datetime`

       g) `ScopedEvidenceTrail` (Pydantic BaseModel, frozen):
          - `candidate_uuid: str`
          - `candidate_name: str`
          - `access_tier: AccessTier`
          - `artifacts: list[ArtifactEvidence]` -- Limited to relevant ones
          - `scores: list[ScoreEvidence]` -- Limited to aggregate
          - `integrity_status: str` -- "passed" or "discounted" (no details)
          - `linkage_confidence: float` -- Just the number, no detail
          - `generated_at: datetime`

       **Class: `CandidateViewService`**

       ```python
       class CandidateViewService:
           """Service for generating candidate evidence trails with access control.

           Generates full or scoped evidence trails based on the requester's
           access tier. All access requests are audit-logged.
           """

           def __init__(
               self,
               *,
               audit_log_path: Path | None = None,
           ) -> None:
               self._access_log: list[AccessRequest] = []
               self._audit_log_path = audit_log_path
       ```

       Add `from pathlib import Path` to imports.

       **Methods:**

       a) `verify_self_access(self, *, candidate_uuid: str, orcid: str | None = None, npi: str | None = None, candidate_strong_keys: dict[str, str] | None = None) -> AccessRequest`:
          - Verify that the requester is the candidate themselves.
          - If orcid provided: check if orcid matches candidate_strong_keys.get("orcid"). If match: grant self_view, method=orcid_oauth.
          - If npi provided: check if npi matches candidate_strong_keys.get("npi"). If match: grant self_view, method=npi_proof.
          - If neither matches or neither provided: deny with reason "Verification failed: ORCID/NPI does not match candidate record".
          - Log the access request.
          - Return AccessRequest.

       b) `verify_customer_access(self, *, candidate_uuid: str, customer_id: str) -> AccessRequest`:
          - Always grant customer_view (scoped). Customer JWT already verified by auth middleware.
          - Log the access request.
          - Return AccessRequest.

       c) `verify_admin_access(self, *, candidate_uuid: str, admin_id: str) -> AccessRequest`:
          - Always grant admin_view. Admin JWT already verified by auth middleware.
          - Log the access request.
          - Return AccessRequest.

       d) `build_full_trail(self, *, candidate_uuid: str, candidate_name: str, artifacts: list[ArtifactEvidence] | None = None, scores: list[ScoreEvidence] | None = None, integrity: IntegrityEvidence | None = None, linkage: LinkageEvidence | None = None, affiliation_history: list[dict[str, Any]] | None = None, opt_out_status: bool = False, contestability_history: list[dict[str, Any]] | None = None, access_tier: AccessTier = AccessTier.self_view) -> CandidateEvidenceTrail`:
          - Build full evidence trail with all details.

       e) `build_scoped_trail(self, *, candidate_uuid: str, candidate_name: str, artifacts: list[ArtifactEvidence] | None = None, scores: list[ScoreEvidence] | None = None, integrity_status: str = "passed", linkage_confidence: float = 0.0) -> ScopedEvidenceTrail`:
          - Build scoped (customer-view) evidence trail with limited details.

       f) `get_access_log(self) -> list[AccessRequest]`:
          - Return all access requests logged.

       g) `_log_access(self, request: AccessRequest) -> None`:
          - Append to in-memory log.
          - If audit_log_path set: append to JSONL file (same pattern as ContestabilityStore).
          - Log at INFO level: "Evidence access: {tier} for {uuid} by {requester_id} - {granted}".

    2. Create `src/aegis/api/candidate_view_test.py` with tests:

       a) `test_self_access_orcid_match`: Verify with matching ORCID. Granted=True, tier=self_view.

       b) `test_self_access_npi_match`: Verify with matching NPI. Granted=True, tier=self_view.

       c) `test_self_access_denied_no_match`: Verify with non-matching ORCID. Granted=False.

       d) `test_self_access_denied_no_credentials`: Verify with neither ORCID nor NPI. Granted=False.

       e) `test_customer_access_always_granted`: Verify customer access. Granted=True, tier=customer_view.

       f) `test_admin_access_always_granted`: Verify admin access. Granted=True, tier=admin_view.

       g) `test_build_full_trail`: Build full trail with artifacts, scores, integrity, linkage. Verify all fields populated.

       h) `test_build_scoped_trail`: Build scoped trail. Verify limited fields (no integrity details, no linkage details).

       i) `test_access_log_recorded`: Make 3 access requests. get_access_log() returns 3 entries.

       j) `test_access_log_persisted(tmp_path)`: Create service with audit_log_path. Make request. Verify JSONL file written.

       k) `test_access_request_model`: Create AccessRequest with all fields. Verify frozen.

       l) `test_full_trail_model`: Create CandidateEvidenceTrail with all fields. Verify frozen.

       Use `from __future__ import annotations`, `import pytest`.

    ## Files to create
    - `src/aegis/api/candidate_view.py`
    - `src/aegis/api/candidate_view_test.py`

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - Append-only JSONL for access logs (same as `src/aegis/integrity/contestability.py`)
    - `StrEnum` for enumerations
    - Logger at module level
    - Access control: verify first, build trail second

    ## Acceptance criteria
    - Self-view access granted with matching ORCID or NPI
    - Self-view access denied with non-matching credentials
    - Customer-view always granted (scoped)
    - Admin-view always granted (full)
    - Full trail includes all detail (artifacts, scores, integrity, linkage, affiliation history, contestability history)
    - Scoped trail has limited detail (no integrity details, no linkage details)
    - Every access request audit-logged
    - JSONL persistence when audit_log_path configured
    - All 12 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/candidate_view_test.py -v && uv run mypy src/aegis/api/candidate_view.py && uv run ruff check src/aegis/api/candidate_view.py
    ```

### 6. Contestability Endpoint and Workflow

- **Task ID**: contestability-endpoint
- **Role**: builder
- **Depends On**: candidate-evidence-api
- **Assigned To**: builder-2
- **Description**: |
    Build the contestability endpoint and workflow: `POST /v1/candidates/{uuid}/contests`. Candidates (verified via ORCID/NPI) can submit corrections to their records. Submissions enter the HITL review queue with elevated priority. Reviewer decisions update the candidate record append-only. SLA targets: 5-day median, 14-day p95.

    This implements Phase 3 master plan Task 1.11.

    ## What to do

    1. Create `src/aegis/api/contestability.py`:

       ```python
       """Contestability endpoint and workflow for candidate-initiated corrections.

       POST /v1/candidates/{uuid}/contests

       Candidates (verified via ORCID or NPI) can submit structured corrections:
       - Affiliation history errors
       - Misattributed artifacts (wrong PMID/NCT/patent linked)
       - Integrity gate false positives (retraction misclassified, etc.)
       - Identity resolution errors (merged with wrong person)

       Submissions enter the HITL review queue with ELEVATED priority.
       Reviewer decisions update the candidate record (append-only).
       SLA targets: 5-day median, 14-day p95 resolution.
       """

       from __future__ import annotations

       import json
       import logging
       import uuid as _uuid
       from datetime import UTC, datetime
       from enum import StrEnum
       from pathlib import Path
       from typing import Any

       import duckdb
       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Enums:**

       a) `ContestCategory` (StrEnum):
          - `affiliation_error = "affiliation_error"`
          - `artifact_misattribution = "artifact_misattribution"`
          - `integrity_false_positive = "integrity_false_positive"`
          - `identity_error = "identity_error"`
          - `score_dispute = "score_dispute"`
          - `other = "other"`

       b) `ContestStatus` (StrEnum):
          - `submitted = "submitted"`
          - `in_review = "in_review"`
          - `resolved_accepted = "resolved_accepted"`
          - `resolved_rejected = "resolved_rejected"`

       c) `ContestPriority` (StrEnum):
          - `normal = "normal"` -- Standard review items
          - `elevated = "elevated"` -- Contestability items get elevated priority
          - `urgent = "urgent"` -- Admin-escalated

       **Models:**

       a) `ContestSubmission` (Pydantic BaseModel, frozen):
          - `contest_id: str`
          - `candidate_uuid: str`
          - `category: ContestCategory`
          - `description: str` -- Free-text explanation from candidate
          - `evidence: dict[str, Any]` -- Supporting evidence (artifact IDs, correct values, etc.)
          - `verified_via: str` -- "orcid" or "npi"
          - `requester_id: str` -- ORCID or NPI of the submitter
          - `submitted_at: datetime`
          - `status: ContestStatus`
          - `priority: ContestPriority`

       b) `ContestDecision` (Pydantic BaseModel, frozen):
          - `decision_id: str`
          - `contest_id: str`
          - `reviewer_id: str`
          - `accepted: bool`
          - `reasoning: str`
          - `actions_taken: list[str]` -- e.g., ["updated affiliation", "removed artifact link"]
          - `decided_at: datetime`

       c) `ContestSummary` (Pydantic BaseModel, frozen):
          - `contest_id: str`
          - `candidate_uuid: str`
          - `category: ContestCategory`
          - `status: ContestStatus`
          - `submitted_at: datetime`
          - `resolved_at: datetime | None`
          - `resolution_days: float | None` -- Business days from submission to resolution

       d) `ContestStats` (Pydantic BaseModel, frozen):
          - `total_submitted: int`
          - `total_in_review: int`
          - `total_resolved: int`
          - `total_accepted: int`
          - `total_rejected: int`
          - `median_resolution_days: float | None`
          - `p95_resolution_days: float | None`

       **Class: `ContestabilityQueue`**

       Follow the DuckDB-backed queue pattern from `src/aegis/identity/review_queue.py`:

       ```python
       _CONTEST_DDL = """
       CREATE TABLE IF NOT EXISTS contest_submissions (
           contest_id TEXT PRIMARY KEY,
           candidate_uuid TEXT NOT NULL,
           category TEXT NOT NULL,
           description TEXT NOT NULL,
           evidence JSON NOT NULL,
           verified_via TEXT NOT NULL,
           requester_id TEXT NOT NULL,
           submitted_at TIMESTAMP NOT NULL,
           status TEXT NOT NULL DEFAULT 'submitted',
           priority TEXT NOT NULL DEFAULT 'elevated'
       );

       CREATE TABLE IF NOT EXISTS contest_decisions (
           decision_id TEXT PRIMARY KEY,
           contest_id TEXT NOT NULL REFERENCES contest_submissions(contest_id),
           reviewer_id TEXT NOT NULL,
           accepted BOOLEAN NOT NULL,
           reasoning TEXT NOT NULL,
           actions_taken JSON NOT NULL,
           decided_at TIMESTAMP NOT NULL DEFAULT current_timestamp
       );
       """

       class ContestabilityQueue:
           """DuckDB-backed queue for candidate contestability requests.

           Follows the ReviewQueue pattern from src/aegis/identity/review_queue.py.
           Contestability items have ELEVATED priority by default.
           """

           def __init__(self, db_path: str = "aegis.duckdb") -> None:
               self._conn = duckdb.connect(db_path)
               self._conn.execute(_CONTEST_DDL)
       ```

       **Methods:**

       a) `submit(self, *, candidate_uuid: str, category: ContestCategory, description: str, evidence: dict[str, Any], verified_via: str, requester_id: str) -> ContestSubmission`:
          - Generate contest_id = uuid4 hex.
          - Insert into contest_submissions with status=submitted, priority=elevated.
          - Return ContestSubmission.

       b) `next_for_review(self) -> ContestSubmission | None`:
          - Return oldest unresolved submission.
          - ORDER BY: priority DESC (urgent > elevated > normal), submitted_at ASC.
          - Update status to in_review.
          - Return None if queue empty.

       c) `decide(self, *, contest_id: str, reviewer_id: str, accepted: bool, reasoning: str, actions_taken: list[str] | None = None) -> ContestDecision`:
          - Generate decision_id = uuid4 hex.
          - Insert into contest_decisions.
          - Update submission status to resolved_accepted or resolved_rejected.
          - Return ContestDecision.

       d) `get_submission(self, contest_id: str) -> ContestSubmission | None`:
          - Look up by contest_id.

       e) `get_by_candidate(self, candidate_uuid: str) -> list[ContestSummary]`:
          - Return all submissions for a candidate with resolution info.

       f) `get_decisions(self, contest_id: str) -> list[ContestDecision]`:
          - Return all decisions for a contest (append-only: can have multiple).

       g) `pending_count(self) -> int`:
          - Count of submitted + in_review items.

       h) `get_stats(self) -> ContestStats`:
          - Aggregate stats. For median/p95 resolution days: compute from resolved items.
          - Use `statistics` module for median. For p95: sort resolution days and take 95th percentile.
          - If no resolved items: median and p95 are None.

       i) `close(self) -> None`:
          - Close DuckDB connection.

       Add `import statistics` to imports.

    2. Create `src/aegis/api/contestability_test.py` with tests:

       a) `test_submit_contest(tmp_path)`: Submit a contest. Verify returned submission has elevated priority, status=submitted.

       b) `test_next_for_review(tmp_path)`: Submit 2 contests. next_for_review returns oldest. Status changes to in_review.

       c) `test_decide_accepted(tmp_path)`: Submit, start review, decide accepted. Verify status=resolved_accepted.

       d) `test_decide_rejected(tmp_path)`: Submit, decide rejected. Verify status=resolved_rejected.

       e) `test_get_by_candidate(tmp_path)`: Submit 3 contests for 2 candidates. get_by_candidate returns correct subset.

       f) `test_pending_count(tmp_path)`: Submit 5, decide 2. pending_count returns 3.

       g) `test_priority_ordering(tmp_path)`: Submit 2 contests: one normal priority (manually update after insert), one elevated. next_for_review returns elevated first.

       h) `test_append_only_decisions(tmp_path)`: Decide same contest twice (e.g., first reject, then accept on re-review). get_decisions returns both.

       i) `test_stats(tmp_path)`: Submit 5, resolve 3 (2 accepted, 1 rejected). Verify stats.

       j) `test_contest_submission_model`: Create ContestSubmission. Verify frozen.

       k) `test_get_submission(tmp_path)`: Submit then get_submission by ID. Verify matches.

       l) `test_empty_queue(tmp_path)`: next_for_review on empty queue returns None. pending_count returns 0.

       For each test, use a fixture:
       ```python
       @pytest.fixture()
       def queue(tmp_path: Path) -> Generator[ContestabilityQueue]:
           db_path = str(tmp_path / "contest_test.duckdb")
           q = ContestabilityQueue(db_path=db_path)
           yield q
           q.close()
       ```

       Use `from __future__ import annotations`, `import pytest`, `from collections.abc import Generator`, `from pathlib import Path`.

    ## Files to create
    - `src/aegis/api/contestability.py`
    - `src/aegis/api/contestability_test.py`

    ## Code patterns to follow
    - DuckDB-backed queue pattern from `src/aegis/identity/review_queue.py`
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `StrEnum` for enumerations
    - `uuid.uuid4().hex` for IDs
    - `json.dumps` for JSON columns in DuckDB
    - Fixture pattern from `src/aegis/identity/review_queue_test.py`
    - Append-only decisions (reviewer decision is final, but multiple decisions are allowed on re-submission)

    ## Acceptance criteria
    - Submissions stored with elevated priority by default
    - FIFO ordering by priority then timestamp
    - Decisions are append-only
    - Status transitions: submitted -> in_review -> resolved_accepted/resolved_rejected
    - Stats include median and p95 resolution days
    - Empty queue handled gracefully
    - All 12 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/contestability_test.py -v && uv run mypy src/aegis/api/contestability.py && uv run ruff check src/aegis/api/contestability.py
    ```

### 7. Customer Dispute Workflow

- **Task ID**: customer-disputes
- **Role**: builder
- **Depends On**: candidate-evidence-api
- **Assigned To**: builder-2
- **Description**: |
    Build the customer dispute workflow: `POST /v1/disputes`. Customers file disputes about ranked candidates (e.g., "candidate X produced low-quality labels"). Disputes enter an admin review queue. Confirmed disputes feed back as highest-confidence ground truth for weight relearning via the Plackett-Luce pipeline.

    This implements Phase 3 master plan Task 3.4.

    ## What to do

    1. Create `src/aegis/api/customer_disputes.py`:

       ```python
       """Customer dispute workflow.

       POST /v1/disputes

       Customers file disputes about ranked candidates ("candidate X who you
       ranked highly produced low-quality labels"). Flow:
       1. Customer submits dispute via API (JWT authenticated)
       2. Dispute enters admin review queue
       3. Admin reviews: candidate evidence trail + customer task-quality data
       4. Admin confirms or rejects with reasoning
       5. CONFIRMED disputes feed back as highest-confidence ground truth
          for weight relearning via the Plackett-Luce pipeline

       Disputes are NOT contestability (candidate-driven). This is customer-driven.
       """

       from __future__ import annotations

       import json
       import logging
       import statistics
       import uuid as _uuid
       from datetime import UTC, datetime
       from enum import StrEnum
       from typing import Any

       import duckdb
       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)
       ```

       **Enums:**

       a) `DisputeCategory` (StrEnum):
          - `low_quality_output = "low_quality_output"` -- Candidate produced poor labels
          - `incorrect_ranking = "incorrect_ranking"` -- Candidate ranked too high/low
          - `missing_expertise = "missing_expertise"` -- Candidate lacked expected specialty
          - `integrity_concern = "integrity_concern"` -- Customer observed integrity issue
          - `other = "other"`

       b) `DisputeStatus` (StrEnum):
          - `submitted = "submitted"`
          - `under_review = "under_review"`
          - `confirmed = "confirmed"` -- Admin confirmed the dispute
          - `rejected = "rejected"` -- Admin rejected the dispute

       **Models:**

       a) `DisputeSubmission` (Pydantic BaseModel, frozen):
          - `dispute_id: str`
          - `customer_id: str`
          - `candidate_uuid: str`
          - `query_id: str | None` -- Which query produced the ranking (for traceability)
          - `category: DisputeCategory`
          - `description: str`
          - `evidence: dict[str, Any]` -- Task outcome data, quality metrics, etc.
          - `submitted_at: datetime`
          - `status: DisputeStatus`

       b) `DisputeDecision` (Pydantic BaseModel, frozen):
          - `decision_id: str`
          - `dispute_id: str`
          - `admin_id: str`
          - `confirmed: bool`
          - `reasoning: str`
          - `feedback_weight: float` -- Confidence weight for relearning (confirmed disputes get 1.0)
          - `decided_at: datetime`

       c) `DisputeFeedback` (Pydantic BaseModel, frozen):
          - `dispute_id: str`
          - `candidate_uuid: str`
          - `query_id: str | None`
          - `category: DisputeCategory`
          - `feedback_weight: float` -- 1.0 for confirmed disputes (highest confidence)
          - `direction: str` -- "downweight" for low_quality/incorrect_ranking, "flag" for integrity_concern
          - `generated_at: datetime`

       d) `DisputeStats` (Pydantic BaseModel, frozen):
          - `total_submitted: int`
          - `total_under_review: int`
          - `total_confirmed: int`
          - `total_rejected: int`
          - `confirmation_rate: float`
          - `median_resolution_days: float | None`
          - `feedback_generated: int` -- Number of disputes that became ground truth

       **Class: `DisputeQueue`**

       Follow the DuckDB-backed queue pattern from `src/aegis/identity/review_queue.py`:

       ```python
       _DISPUTE_DDL = """
       CREATE TABLE IF NOT EXISTS dispute_submissions (
           dispute_id TEXT PRIMARY KEY,
           customer_id TEXT NOT NULL,
           candidate_uuid TEXT NOT NULL,
           query_id TEXT,
           category TEXT NOT NULL,
           description TEXT NOT NULL,
           evidence JSON NOT NULL,
           submitted_at TIMESTAMP NOT NULL,
           status TEXT NOT NULL DEFAULT 'submitted'
       );

       CREATE TABLE IF NOT EXISTS dispute_decisions (
           decision_id TEXT PRIMARY KEY,
           dispute_id TEXT NOT NULL REFERENCES dispute_submissions(dispute_id),
           admin_id TEXT NOT NULL,
           confirmed BOOLEAN NOT NULL,
           reasoning TEXT NOT NULL,
           feedback_weight DOUBLE NOT NULL DEFAULT 1.0,
           decided_at TIMESTAMP NOT NULL DEFAULT current_timestamp
       );
       """

       class DisputeQueue:
           """DuckDB-backed queue for customer disputes.

           Follows the ReviewQueue pattern. Confirmed disputes are converted
           to highest-confidence ground truth for weight relearning.
           """

           def __init__(self, db_path: str = "aegis.duckdb") -> None:
               self._conn = duckdb.connect(db_path)
               self._conn.execute(_DISPUTE_DDL)
       ```

       **Methods:**

       a) `submit(self, *, customer_id: str, candidate_uuid: str, category: DisputeCategory, description: str, evidence: dict[str, Any], query_id: str | None = None) -> DisputeSubmission`:
          - Generate dispute_id = uuid4 hex.
          - Insert into dispute_submissions with status=submitted.
          - Return DisputeSubmission.

       b) `next_for_review(self) -> DisputeSubmission | None`:
          - Return oldest unresolved dispute (status=submitted).
          - Update status to under_review.
          - Return None if queue empty.

       c) `decide(self, *, dispute_id: str, admin_id: str, confirmed: bool, reasoning: str) -> DisputeDecision`:
          - Generate decision_id.
          - Set feedback_weight = 1.0 if confirmed, 0.0 if rejected.
          - Insert into dispute_decisions.
          - Update submission status to confirmed/rejected.
          - Return DisputeDecision.

       d) `generate_feedback(self, dispute_id: str) -> DisputeFeedback | None`:
          - Look up dispute and its latest confirmed decision.
          - If not confirmed: return None.
          - Generate DisputeFeedback:
            - feedback_weight = 1.0 (highest confidence)
            - direction = "downweight" for low_quality_output, incorrect_ranking, missing_expertise
            - direction = "flag" for integrity_concern
            - direction = "review" for other
          - Return DisputeFeedback.

       e) `get_all_feedback(self) -> list[DisputeFeedback]`:
          - Return feedback for ALL confirmed disputes.
          - This is what the weight relearning pipeline consumes.

       f) `get_submission(self, dispute_id: str) -> DisputeSubmission | None`:
          - Look up by dispute_id.

       g) `get_by_customer(self, customer_id: str) -> list[DisputeSubmission]`:
          - Return all disputes for a customer.

       h) `get_by_candidate(self, candidate_uuid: str) -> list[DisputeSubmission]`:
          - Return all disputes about a candidate.

       i) `pending_count(self) -> int`:
          - Count of submitted + under_review items.

       j) `get_stats(self) -> DisputeStats`:
          - Aggregate stats.

       k) `close(self) -> None`:
          - Close DuckDB connection.

    2. Create `src/aegis/api/customer_disputes_test.py` with tests:

       a) `test_submit_dispute(tmp_path)`: Submit a dispute. Verify status=submitted, dispute_id set.

       b) `test_next_for_review(tmp_path)`: Submit 2 disputes. next_for_review returns oldest. Status changes.

       c) `test_decide_confirmed(tmp_path)`: Submit, review, confirm. Verify status=confirmed, feedback_weight=1.0.

       d) `test_decide_rejected(tmp_path)`: Submit, reject. Verify status=rejected, feedback_weight=0.0.

       e) `test_generate_feedback_confirmed(tmp_path)`: Submit, confirm, generate_feedback. Verify DisputeFeedback with weight=1.0 and direction="downweight" for low_quality_output.

       f) `test_generate_feedback_rejected_returns_none(tmp_path)`: Submit, reject, generate_feedback. Returns None.

       g) `test_get_all_feedback(tmp_path)`: Submit 3 disputes, confirm 2, reject 1. get_all_feedback returns 2 items.

       h) `test_get_by_customer(tmp_path)`: Submit disputes for 2 customers. get_by_customer returns correct subset.

       i) `test_get_by_candidate(tmp_path)`: Submit disputes about 2 candidates. get_by_candidate returns correct subset.

       j) `test_pending_count(tmp_path)`: Submit 5, decide 2. pending_count returns 3.

       k) `test_stats(tmp_path)`: Submit 5, confirm 2, reject 1. Verify stats: confirmation_rate = 2/3.

       l) `test_empty_queue(tmp_path)`: next_for_review returns None. pending_count returns 0.

       m) `test_dispute_submission_model`: Create DisputeSubmission. Verify frozen.

       n) `test_feedback_direction_integrity(tmp_path)`: Submit dispute with category=integrity_concern, confirm. generate_feedback returns direction="flag".

       For each test, use a fixture:
       ```python
       @pytest.fixture()
       def queue(tmp_path: Path) -> Generator[DisputeQueue]:
           db_path = str(tmp_path / "dispute_test.duckdb")
           q = DisputeQueue(db_path=db_path)
           yield q
           q.close()
       ```

    ## Files to create
    - `src/aegis/api/customer_disputes.py`
    - `src/aegis/api/customer_disputes_test.py`

    ## Code patterns to follow
    - DuckDB-backed queue pattern from `src/aegis/identity/review_queue.py`
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `StrEnum` for enumerations
    - `uuid.uuid4().hex` for IDs
    - Fixture pattern from `src/aegis/identity/review_queue_test.py`

    ## Acceptance criteria
    - Disputes stored with customer_id and candidate_uuid
    - FIFO ordering for admin review
    - Confirmed disputes generate highest-confidence feedback (weight=1.0)
    - Rejected disputes generate no feedback
    - get_all_feedback returns only confirmed disputes
    - Feedback direction varies by category (downweight vs flag)
    - Stats include confirmation rate and resolution time
    - All 14 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/customer_disputes_test.py -v && uv run mypy src/aegis/api/customer_disputes.py && uv run ruff check src/aegis/api/customer_disputes.py
    ```

### 8. Server Wiring and Integration Tests

- **Task ID**: server-wiring
- **Role**: builder
- **Depends On**: candidate-evidence-api, contestability-endpoint, customer-disputes, privacy-gate
- **Assigned To**: builder-2
- **Description**: |
    Wire the new endpoints into the existing FastAPI server from Phase 3b. Add routes for candidate evidence trail, contestability, and customer disputes. Create integration tests using FastAPI TestClient.

    ## What to do

    1. Create `src/aegis/api/privacy_contestability_router.py`:

       ```python
       """FastAPI router for privacy, contestability, and dispute endpoints.

       Mounts:
       - GET /v1/candidates/{uuid}/evidence -- Candidate evidence trail
       - POST /v1/candidates/{uuid}/contests -- Contestability submissions
       - GET /v1/candidates/{uuid}/contests -- List candidate's contests
       - POST /v1/disputes -- Customer dispute submissions
       - GET /v1/disputes -- List customer's disputes
       """

       from __future__ import annotations

       import logging
       from datetime import UTC, datetime
       from pathlib import Path
       from typing import Any

       from fastapi import APIRouter, Depends, HTTPException, status
       from pydantic import BaseModel, ConfigDict

       from aegis.api.auth import TokenPayload, get_current_customer
       from aegis.api.candidate_view import (
           AccessTier,
           ArtifactEvidence,
           CandidateEvidenceTrail,
           CandidateViewService,
           IntegrityEvidence,
           LinkageEvidence,
           ScoreEvidence,
           ScopedEvidenceTrail,
           VerificationMethod,
       )
       from aegis.api.contestability import (
           ContestabilityQueue,
           ContestCategory,
           ContestSubmission,
           ContestSummary,
       )
       from aegis.api.customer_disputes import (
           DisputeCategory,
           DisputeQueue,
           DisputeSubmission,
       )

       logger = logging.getLogger(__name__)
       ```

       **Request models (defined in this file):**

       a) `EvidenceRequest` (Pydantic BaseModel, frozen):
          - `orcid: str | None = None`
          - `npi: str | None = None`

       b) `ContestRequest` (Pydantic BaseModel):
          - `category: str` -- One of ContestCategory values
          - `description: str` -- Must be >= 20 chars
          - `evidence: dict[str, Any]`
          - `orcid: str | None = None`
          - `npi: str | None = None`
          - Add a field_validator on description rejecting < 20 chars.

       c) `DisputeRequest` (Pydantic BaseModel):
          - `candidate_uuid: str`
          - `query_id: str | None = None`
          - `category: str` -- One of DisputeCategory values
          - `description: str` -- Must be >= 20 chars
          - `evidence: dict[str, Any]`
          - Add a field_validator on description rejecting < 20 chars.

       **Function: `create_privacy_contestability_router`**

       ```python
       def create_privacy_contestability_router(
           *,
           candidate_view_service: CandidateViewService | None = None,
           contest_queue: ContestabilityQueue | None = None,
           dispute_queue: DisputeQueue | None = None,
       ) -> APIRouter:
           """Create the privacy/contestability/dispute router."""
           router = APIRouter()
           _view_service = candidate_view_service or CandidateViewService()
           _contest_queue = contest_queue or ContestabilityQueue()
           _dispute_queue = dispute_queue or DisputeQueue()
       ```

       **Routes:**

       a) `GET /v1/candidates/{uuid}/evidence`:
          - Query params: orcid (optional), npi (optional)
          - Auth: JWT customer token (from get_current_customer dependency)
          - Logic:
            - If orcid or npi provided: attempt self-view verification. If granted: return full trail.
            - Otherwise: return scoped trail (customer-view).
          - Note: For the initial implementation, the trail is built with placeholder data. Full integration with CandidateStore, scoring components, etc. happens at deployment time. The endpoint demonstrates the access control flow and response shape.
          - Return: CandidateEvidenceTrail (full) or ScopedEvidenceTrail (scoped).

       b) `POST /v1/candidates/{uuid}/contests`:
          - Body: ContestRequest
          - Auth: No JWT required for contestability (candidate-facing, not customer-facing). Verification is via ORCID/NPI in the request body.
          - Logic:
            - Validate category is a valid ContestCategory.
            - Require orcid or npi in request body. If neither: return 400 "ORCID or NPI required for verification".
            - Submit to contest queue with verified_via and requester_id.
          - Return: ContestSubmission

       c) `GET /v1/candidates/{uuid}/contests`:
          - Auth: JWT customer token (customer can see contests for candidates they've queried)
          - Return: list of ContestSummary for this candidate.

       d) `POST /v1/disputes`:
          - Body: DisputeRequest
          - Auth: JWT customer token
          - Logic:
            - Validate category is a valid DisputeCategory.
            - Submit to dispute queue with customer_id from JWT.
          - Return: DisputeSubmission

       e) `GET /v1/disputes`:
          - Auth: JWT customer token
          - Return: list of DisputeSubmission for this customer.

       Return the configured router.

    2. Create `src/aegis/api/privacy_contestability_router_test.py`:

       ```python
       """Integration tests for privacy, contestability, and dispute endpoints."""

       from __future__ import annotations

       from pathlib import Path
       from collections.abc import Generator

       import pytest
       from fastapi import FastAPI
       from fastapi.testclient import TestClient

       from aegis.api.auth import CustomerClaims, create_token
       from aegis.api.privacy_contestability_router import (
           create_privacy_contestability_router,
       )
       from aegis.api.candidate_view import CandidateViewService
       from aegis.api.contestability import ContestabilityQueue
       from aegis.api.customer_disputes import DisputeQueue
       ```

       **Fixture:**
       ```python
       @pytest.fixture()
       def app_and_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[FastAPI, str]:
           monkeypatch.setenv("AEGIS_JWT_SECRET", "test-secret")

           view_service = CandidateViewService(audit_log_path=tmp_path / "access.jsonl")
           contest_queue = ContestabilityQueue(db_path=str(tmp_path / "contest.duckdb"))
           dispute_queue = DisputeQueue(db_path=str(tmp_path / "dispute.duckdb"))

           app = FastAPI()
           router = create_privacy_contestability_router(
               candidate_view_service=view_service,
               contest_queue=contest_queue,
               dispute_queue=dispute_queue,
           )
           app.include_router(router)

           token = create_token(
               CustomerClaims(customer_id="test-customer", customer_name="Test Corp"),
               secret="test-secret",
           )

           return app, token
       ```

       **Tests:**

       a) `test_evidence_customer_view(app_and_token)`: GET /v1/candidates/{uuid}/evidence with JWT. Verify 200 with scoped trail (customer_view tier).

       b) `test_evidence_self_view_orcid(app_and_token)`: GET /v1/candidates/{uuid}/evidence?orcid=0000-0001-2345-6789 with JWT. Since no candidate store is connected, self-view will fail verification and fall back to customer view. Verify 200.

       c) `test_submit_contest(app_and_token)`: POST /v1/candidates/{uuid}/contests with valid ContestRequest (orcid provided, category="affiliation_error", description of >= 20 chars). Verify 200 with ContestSubmission in response.

       d) `test_contest_requires_orcid_or_npi(app_and_token)`: POST /v1/candidates/{uuid}/contests without orcid or npi. Verify 400.

       e) `test_contest_short_description(app_and_token)`: POST with description < 20 chars. Verify 422.

       f) `test_list_contests(app_and_token)`: Submit a contest then GET /v1/candidates/{uuid}/contests. Verify list returned.

       g) `test_submit_dispute(app_and_token)`: POST /v1/disputes with valid DisputeRequest. Verify 200 with DisputeSubmission.

       h) `test_dispute_requires_auth(app_and_token)`: POST /v1/disputes without token. Verify 403 (FastAPI HTTPBearer).

       i) `test_list_disputes(app_and_token)`: Submit a dispute then GET /v1/disputes. Verify list includes submitted dispute.

       j) `test_dispute_short_description(app_and_token)`: POST /v1/disputes with description < 20 chars. Verify 422.

       Use `client = TestClient(app)` from the fixture.
       For auth: `headers={"Authorization": f"Bearer {token}"}`.
       For contest endpoint (no JWT required): no auth header needed if the endpoint doesn't require it; but since GET /v1/candidates/{uuid}/contests uses JWT, test accordingly.

    ## Files to create
    - `src/aegis/api/privacy_contestability_router.py`
    - `src/aegis/api/privacy_contestability_router_test.py`

    ## Code patterns to follow
    - FastAPI APIRouter pattern (not standalone app) so it can be mounted in the main server
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - Dependency injection via constructor parameters (same as Phase 3b server.py)
    - TestClient for integration tests (same as Phase 3b server_test.py)
    - monkeypatch for env vars

    ## Acceptance criteria
    - GET /v1/candidates/{uuid}/evidence returns evidence trail with access control
    - POST /v1/candidates/{uuid}/contests accepts verified corrections
    - Contest endpoint requires ORCID or NPI verification
    - POST /v1/disputes accepts customer disputes with JWT auth
    - GET /v1/disputes returns customer's disputes
    - Description validation: minimum 20 characters
    - All 10 tests pass
    - mypy strict passes
    - ruff passes

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/privacy_contestability_router_test.py -v && uv run mypy src/aegis/api/privacy_contestability_router.py && uv run ruff check src/aegis/api/privacy_contestability_router.py
    ```

### 9. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: phi-scanner, demographic-blocklist, opt-out, privacy-gate, candidate-evidence-api, contestability-endpoint, customer-disputes, server-wiring
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the Phase 3e privacy and contestability sub-spec.

    ## Validation Commands

    Run each of these commands. ALL must pass for validation to succeed.

    1. PHI scanner tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/phi_scanner_test.py -v
    ```

    2. Demographic blocklist tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/demographic_blocklist_test.py -v
    ```

    3. Opt-out tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/opt_out_test.py -v
    ```

    4. Privacy gate tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/gate_test.py -v
    ```

    5. Candidate evidence trail tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/candidate_view_test.py -v
    ```

    6. Contestability tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/contestability_test.py -v
    ```

    7. Customer disputes tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/customer_disputes_test.py -v
    ```

    8. Router integration tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/api/privacy_contestability_router_test.py -v
    ```

    9. All Phase 3e tests together:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/phi_scanner_test.py src/aegis/privacy/demographic_blocklist_test.py src/aegis/privacy/opt_out_test.py src/aegis/privacy/gate_test.py src/aegis/api/candidate_view_test.py src/aegis/api/contestability_test.py src/aegis/api/customer_disputes_test.py src/aegis/api/privacy_contestability_router_test.py -v
    ```

    10. mypy strict on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/privacy/phi_scanner.py src/aegis/privacy/demographic_blocklist.py src/aegis/privacy/opt_out.py src/aegis/privacy/gate.py src/aegis/api/candidate_view.py src/aegis/api/contestability.py src/aegis/api/customer_disputes.py src/aegis/api/privacy_contestability_router.py
    ```

    11. ruff lint on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/privacy/ src/aegis/api/candidate_view.py src/aegis/api/contestability.py src/aegis/api/customer_disputes.py src/aegis/api/privacy_contestability_router.py
    ```

    12. Verify privacy package imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.privacy.phi_scanner import PHIScanner, PHIDetection, ScanResult, PHIType
    from aegis.privacy.demographic_blocklist import DemographicBlocklist, BlocklistResult
    from aegis.privacy.opt_out import OptOutStore, OptOutRecord, OptOutAction
    from aegis.privacy.gate import PrivacyGate, GateResult, GateDecision
    from aegis.api.candidate_view import CandidateViewService, CandidateEvidenceTrail, AccessTier
    from aegis.api.contestability import ContestabilityQueue, ContestSubmission, ContestCategory
    from aegis.api.customer_disputes import DisputeQueue, DisputeSubmission, DisputeFeedback
    from aegis.api.privacy_contestability_router import create_privacy_contestability_router
    print('All Phase 3e imports OK')
    "
    ```

    13. Verify design assertions:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.api.candidate_view import CandidateViewService
    from aegis.api.contestability import ContestabilityQueue
    from aegis.api.customer_disputes import DisputeQueue
    from aegis.privacy.gate import PrivacyGate

    # Verify CandidateViewService methods
    assert hasattr(CandidateViewService, 'verify_self_access')
    assert hasattr(CandidateViewService, 'build_full_trail')
    assert hasattr(CandidateViewService, 'build_scoped_trail')

    # Verify ContestabilityQueue methods
    assert hasattr(ContestabilityQueue, 'submit')
    assert hasattr(ContestabilityQueue, 'next_for_review')
    assert hasattr(ContestabilityQueue, 'decide')

    # Verify DisputeQueue methods
    assert hasattr(DisputeQueue, 'submit')
    assert hasattr(DisputeQueue, 'generate_feedback')
    assert hasattr(DisputeQueue, 'get_all_feedback')

    # Verify PrivacyGate methods
    assert hasattr(PrivacyGate, 'check')
    assert hasattr(PrivacyGate, 'check_bypass_alert')

    print('All design assertions OK')
    "
    ```

    14. Verify existing tests unbroken (regression check):
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/identity/review_queue_test.py src/aegis/integrity/contestability_test.py -v
    ```

    ## Acceptance Criteria

    ALL of these must be verified:

    - [ ] `src/aegis/privacy/__init__.py` exists and is importable
    - [ ] PHI scanner detects SSN (dashed), phone, email, MRN patterns
    - [ ] PHI scanner context-filters SSN (no dash) and dates to reduce false positives
    - [ ] PHI scanner LLM classifier disabled by default (stub)
    - [ ] Demographic blocklist strips gender, race, citizenship, age fields
    - [ ] Demographic blocklist allowlist prevents false positives (dosage, coverage, lineage)
    - [ ] Opt-out persisted in append-only JSONL
    - [ ] Opt-in reversal works
    - [ ] Privacy gate chains PHI scan -> demographic strip -> opt-out check
    - [ ] Privacy gate is fail-closed (errors reject, not admit)
    - [ ] Privacy gate bypass alerting works
    - [ ] Candidate evidence trail API has three access tiers (self, customer, admin)
    - [ ] Self-view verified via ORCID or NPI match
    - [ ] Customer-view returns scoped data (less detail)
    - [ ] Every access request audit-logged
    - [ ] Contestability endpoint requires ORCID/NPI verification
    - [ ] Contest submissions get elevated priority in review queue
    - [ ] Contest decisions are append-only
    - [ ] Customer disputes filed via JWT-authenticated API
    - [ ] Confirmed disputes generate highest-confidence feedback (weight=1.0)
    - [ ] Feedback direction varies by category
    - [ ] Router integration tests pass for all endpoints
    - [ ] All PHI scanner tests pass (16 tests)
    - [ ] All demographic blocklist tests pass (14 tests)
    - [ ] All opt-out tests pass (10 tests)
    - [ ] All privacy gate tests pass (10 tests)
    - [ ] All candidate view tests pass (12 tests)
    - [ ] All contestability tests pass (12 tests)
    - [ ] All customer dispute tests pass (14 tests)
    - [ ] All router integration tests pass (10 tests)
    - [ ] mypy strict passes on all new modules
    - [ ] ruff lint passes on all new modules
    - [ ] Existing identity/contestability tests unbroken

### 10. Update Privacy Design Document

- **Task ID**: update-design-privacy
- **Role**: design-updater
- **Depends On**: validate-all
- **Assigned To**: design-updater
- **Description**: |
    Update the living design document for the privacy and contestability domain to reflect
    what was actually built in this plan.

    ## Target Design Doc
    docs/design/privacy.md

    ## Spec File
    specs/aegis-phase3e-privacy-contestability.md

    ## Scope
    New privacy domain: PHI/HIPAA scanning, demographic blocklist, candidate opt-out,
    composed privacy gate, candidate evidence trail API with access control,
    contestability endpoint with HITL review queue integration, and customer dispute
    workflow with weight-relearning feedback. This is the first privacy design doc -- create it.

    ## Prior Decisions to Check
    - Scoring design doc (`docs/design/scoring.md`) -- integrity gate I(c) consumed by evidence trail
    - API design doc (`docs/design/api.md`) if it exists -- JWT auth pattern, FastAPI router pattern
    - ContestabilityStore pattern from `src/aegis/integrity/contestability.py` -- append-only JSONL
    - ReviewQueue pattern from `src/aegis/identity/review_queue.py` -- DuckDB-backed HITL queue
    - Pydantic frozen model pattern from scoring domain

    ## What to Record
    Read git diff HEAD~1 HEAD, then the changed source files, then the existing
    design doc (create if not present). Write a Current Design section describing the privacy
    architecture, component interactions, and key patterns. Append a Design Decision entry
    for each non-trivial architectural choice made in this build:
    - PHI scanner: pattern matching + LLM stub with false-positive-preferred bias
    - Context-aware pattern filtering (dates only flagged in sensitive fields, bare 9-digit numbers need SSN context)
    - Demographic blocklist with allowlist to prevent false positives on biomedical terms (dosage, lineage)
    - Append-only JSONL for opt-out records (same pattern as ContestabilityStore)
    - Composed privacy gate as single ingestion entry point (PHI -> demographic -> opt-out)
    - Fail-closed gate: errors reject, bypass is alertable
    - Three-tier evidence access control (self/customer/admin) with ORCID/NPI verification
    - DuckDB-backed contestability queue with elevated priority for candidate submissions
    - Customer dispute -> confirmed feedback -> highest-confidence ground truth for weight relearning
    - All access requests audit-logged regardless of outcome
    Every claim must cite a file:line from the actual code.

## Acceptance Criteria

- `GET /v1/candidates/{uuid}/evidence` endpoint with three access tiers (self, customer, admin) and ORCID/NPI verification
- `POST /v1/candidates/{uuid}/contests` endpoint with ORCID/NPI verification, elevated priority in review queue, append-only decisions
- PHI/HIPAA scanner at `src/aegis/privacy/phi_scanner.py` with pattern matching + LLM stub, false-positive-preferred
- Demographic blocklist at `src/aegis/privacy/demographic_blocklist.py` strips gender/race/citizenship/age with allowlist for biomedical terms
- Candidate opt-out at `src/aegis/privacy/opt_out.py` with append-only JSONL, reversible opt-in
- Composed privacy gate at `src/aegis/privacy/gate.py` chains all three checks, fail-closed, bypass alerting
- `POST /v1/disputes` endpoint at `src/aegis/api/customer_disputes.py` with admin review queue, confirmed disputes as highest-confidence ground truth
- All new tests pass (98 tests total: 16+14+10+10+12+12+14+10)
- mypy strict passes on all new modules
- ruff lint passes on all new modules
- No existing identity/contestability tests broken

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/privacy/phi_scanner_test.py src/aegis/privacy/demographic_blocklist_test.py src/aegis/privacy/opt_out_test.py src/aegis/privacy/gate_test.py src/aegis/api/candidate_view_test.py src/aegis/api/contestability_test.py src/aegis/api/customer_disputes_test.py src/aegis/api/privacy_contestability_router_test.py -v` -- Run all Phase 3e tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/privacy/phi_scanner.py src/aegis/privacy/demographic_blocklist.py src/aegis/privacy/opt_out.py src/aegis/privacy/gate.py src/aegis/api/candidate_view.py src/aegis/api/contestability.py src/aegis/api/customer_disputes.py src/aegis/api/privacy_contestability_router.py` -- Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/privacy/ src/aegis/api/candidate_view.py src/aegis/api/contestability.py src/aegis/api/customer_disputes.py src/aegis/api/privacy_contestability_router.py` -- Lint all new modules
- `cd /Users/anvith/aegis && uv run pytest src/aegis/identity/review_queue_test.py src/aegis/integrity/contestability_test.py -v` -- Verify existing tests unbroken
- `cd /Users/anvith/aegis && uv run python -c "from aegis.privacy.gate import PrivacyGate; from aegis.api.candidate_view import CandidateViewService; from aegis.api.contestability import ContestabilityQueue; from aegis.api.customer_disputes import DisputeQueue; print('Core imports OK')"` -- Verify core imports

## Notes

- No new dependencies required in `pyproject.toml`. All modules use existing dependencies (pydantic, duckdb, fastapi).
- The PHI scanner LLM classifier is a stub in the initial implementation. Production activation requires an Anthropic API key and explicit `enable()` call. This is intentional: the regex patterns cover the critical structured-field cases, and the LLM layer adds defense-in-depth for unstructured text.
- The `src/aegis/api/` directory already exists from Phase 3b. Builders should not recreate `__init__.py` if it exists.
- The contestability endpoint (`POST /v1/candidates/{uuid}/contests`) is distinct from the existing `ContestabilityStore` in `src/aegis/integrity/contestability.py`. The store handles append-only override records; the new endpoint handles the candidate-facing submission workflow with HITL review queue integration.
- Customer disputes and contestability are intentionally separate. Contestability is candidate-driven (correcting their own record). Disputes are customer-driven (reporting ranking quality issues). They have different trust models and different feedback paths.
- The DuckDB connection pattern from `src/aegis/identity/review_queue.py` should be followed exactly: connection created in `__init__`, DDL executed immediately, `close()` method for cleanup.
- For the `statistics` module used in stats computation: `statistics.median()` for median resolution days, manual percentile calculation for p95 (sort list, take element at index `int(0.95 * len(list))`).

## Build Evidence

> Built 2026-04-27

### Test Results

All 98 Phase 3e tests pass:
- PHI scanner: 16/16 passed
- Demographic blocklist: 14/14 passed
- Opt-out: 10/10 passed
- Privacy gate: 10/10 passed
- Candidate evidence trail: 12/12 passed
- Contestability: 12/12 passed
- Customer disputes: 14/14 passed
- Router integration: 10/10 passed

```
uv run pytest src/aegis/privacy/phi_scanner_test.py src/aegis/privacy/demographic_blocklist_test.py src/aegis/privacy/opt_out_test.py src/aegis/privacy/gate_test.py src/aegis/api/candidate_view_test.py src/aegis/api/contestability_test.py src/aegis/api/customer_disputes_test.py src/aegis/api/privacy_contestability_router_test.py -v
# Result: 98 passed
```

### Type Checking

```
uv run mypy src/aegis/privacy/phi_scanner.py src/aegis/privacy/demographic_blocklist.py src/aegis/privacy/opt_out.py src/aegis/privacy/gate.py src/aegis/api/candidate_view.py src/aegis/api/contestability.py src/aegis/api/customer_disputes.py src/aegis/api/privacy_contestability_router.py
# Result: Success: no issues found in 8 source files
```

### Lint

```
uv run ruff check src/aegis/privacy/ src/aegis/api/candidate_view.py src/aegis/api/contestability.py src/aegis/api/customer_disputes.py src/aegis/api/privacy_contestability_router.py
# Result: All checks passed!
```

### Import Verification

```
uv run python -c "from aegis.privacy.gate import PrivacyGate; from aegis.api.candidate_view import CandidateViewService; from aegis.api.contestability import ContestabilityQueue; from aegis.api.customer_disputes import DisputeQueue; print('Core imports OK')"
# Result: Core imports OK
```

### Regression

```
uv run pytest src/aegis/identity/review_queue_test.py src/aegis/integrity/contestability_test.py -v
# Result: 14 passed
```

### Acceptance Criteria Verification

- [x] `src/aegis/privacy/__init__.py` exists and is importable
- [x] PHI scanner detects SSN (dashed), phone, email, MRN patterns
- [x] PHI scanner context-filters SSN (no dash) and dates to reduce false positives
- [x] PHI scanner LLM classifier disabled by default (stub)
- [x] Demographic blocklist strips gender, race, citizenship, age fields
- [x] Demographic blocklist allowlist prevents false positives (dosage, coverage, lineage)
- [x] Opt-out persisted in append-only JSONL
- [x] Opt-in reversal works
- [x] Privacy gate chains PHI scan -> demographic strip -> opt-out check
- [x] Privacy gate is fail-closed (errors reject, not admit)
- [x] Privacy gate bypass alerting works
- [x] Candidate evidence trail API has three access tiers (self, customer, admin)
- [x] Self-view verified via ORCID or NPI match
- [x] Customer-view returns scoped data (less detail)
- [x] Every access request audit-logged
- [x] Contestability endpoint requires ORCID/NPI verification
- [x] Contest submissions get elevated priority in review queue
- [x] Contest decisions are append-only
- [x] Customer disputes filed via JWT-authenticated API
- [x] Confirmed disputes generate highest-confidence feedback (weight=1.0)
- [x] Feedback direction varies by category
- [x] Router integration tests pass for all endpoints
- [x] mypy strict passes on all new modules
- [x] ruff lint passes on all new modules
- [x] Existing identity/contestability tests unbroken

### Files Created

- `src/aegis/privacy/__init__.py` -- Privacy package init
- `src/aegis/privacy/phi_scanner.py` -- PHI/HIPAA scanner (patterns + LLM stub)
- `src/aegis/privacy/phi_scanner_test.py` -- 16 tests
- `src/aegis/privacy/demographic_blocklist.py` -- Demographic field stripping
- `src/aegis/privacy/demographic_blocklist_test.py` -- 14 tests
- `src/aegis/privacy/opt_out.py` -- Candidate opt-out enforcement (append-only JSONL)
- `src/aegis/privacy/opt_out_test.py` -- 10 tests
- `src/aegis/privacy/gate.py` -- Composed privacy gate (PHI + demographics + opt-out)
- `src/aegis/privacy/gate_test.py` -- 10 tests
- `src/aegis/api/candidate_view.py` -- Candidate evidence trail API with 3-tier access control
- `src/aegis/api/candidate_view_test.py` -- 12 tests
- `src/aegis/api/contestability.py` -- Contestability endpoint (DuckDB-backed queue)
- `src/aegis/api/contestability_test.py` -- 12 tests
- `src/aegis/api/customer_disputes.py` -- Customer dispute workflow (DuckDB-backed queue)
- `src/aegis/api/customer_disputes_test.py` -- 14 tests
- `src/aegis/api/privacy_contestability_router.py` -- FastAPI router wiring all endpoints
- `src/aegis/api/privacy_contestability_router_test.py` -- 10 tests
- `docs/design/privacy.md` -- Privacy domain design document
