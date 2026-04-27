# Plan: Phase 2e — Observability + Error Handling

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase2e-observability.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build the Phase 2 observability dashboards and error-handling modules: specialty-distribution dashboard, reassignment-rate tracking, patent-vs-paper signal-balance dashboard, clinician coverage diagnostics, cross-population merge accuracy monitoring, specialty-classifier ambiguity handling, patent inventor disambiguation conflict resolution, NPI-PubMed name-match HITL routing, and conference abstract parsing failure logging. This sub-spec makes the multi-population platform operationally trustworthy by surfacing data quality issues, classification instability, and ingestion failures.

This plan covers Phase 2 tasks: **2.1** (specialty distribution dashboard), **2.2** (reassignment rate/stability), **2.3** (patent-vs-paper signal balance), **2.4** (clinician coverage diagnostics), **2.5** (cross-population merge accuracy), **3.1** (specialty-classifier ambiguity), **3.2** (patent inventor disambiguation failures), **3.3** (NPI-PubMed name-match low confidence), and **3.4** (conference abstract parsing failures).

## Objective

When this plan is complete:
1. A specialty-distribution dashboard shows per-specialty cohort sizes, multi-specialty counts, and reassignment rates.
2. Reassignment-rate tracking detects classifier instability (> 5% churn alerts).
3. Patent-vs-paper signal-balance dashboard shows per-candidate and cohort-level contribution breakdowns.
4. Clinician coverage diagnostics report NPI cross-link rates, ABMS coverage, state-board coverage, hospital-tier mapping, and publication rates with explicit gap-state flagging.
5. Cross-population merge accuracy tracking with precision/recall on held-out test sets.
6. Ambiguity handling scores ambiguous candidates under top-2 weight vectors and reports dual-rank results.
7. Patent inventor disambiguation conflicts surface to HITL queue with patents excluded from `v_c` until resolved.
8. NPI-PubMed name matches between 0.5 and 0.95 confidence route to HITL (never auto-link below 0.95).
9. Conference abstract parsing failures are logged per-source with quarterly failure-rate tracking.
10. All modules pass mypy strict, ruff lint, and have unit tests.

## Problem Statement

Phase 2 introduces significant complexity: three populations, two new taxonomy cross-walks, a specialty classifier, and cross-population identity merge. Without observability, data quality issues (e.g., over-reliance on patents in `v_c`, classifier instability, merge errors) will silently degrade scoring. Without error handling, disambiguation conflicts and parsing failures will either block ingestion or corrupt data. The existing Phase 1 observability (coverage, drift, freshness) covers single-population concerns; Phase 2 needs multi-population-specific monitoring.

## Solution Approach

1. **Observability modules**: Each dashboard/monitor is an independent module in `src/aegis/observability/` following the existing patterns from Phase 0e (coverage, drift, freshness).
2. **Error handling modules**: Each handler is in the appropriate domain package (scoring for ambiguity, identity for disambiguation/matching, sources for parsing failures).
3. **HITL integration**: Reuse the existing `ReviewQueue` from Phase 0c for disambiguation and name-match conflicts.

## Relevant Files

### Existing Files
- `src/aegis/observability/coverage.py` — Phase 0 `CoverageDiagnostics` (pattern to follow)
- `src/aegis/observability/drift.py` — Phase 0 `DriftDetector` (pattern to follow)
- `src/aegis/observability/freshness.py` — Phase 0 `FreshnessMonitor`
- `src/aegis/observability/__init__.py` — Observability package exports
- `src/aegis/identity/review_queue.py` — `ReviewQueue` for HITL
- `src/aegis/identity/probabilistic.py` — `ProbabilisticLinker`
- `src/aegis/scoring/specialty_classifier.py` — `SpecialtyClassifier` (Phase 2d)
- `src/aegis/scoring/specialty_reassignment.py` — `SpecialtyReassigner` (Phase 2d)
- `src/aegis/identity/cross_population_merge.py` — `CrossPopulationMerger` (Phase 2d)

### New Files
- `src/aegis/observability/specialty_dist.py` — Specialty distribution dashboard
- `src/aegis/observability/reassignment_metrics.py` — Reassignment rate tracking
- `src/aegis/observability/signal_balance.py` — Patent-vs-paper signal balance
- `src/aegis/observability/clinician_coverage.py` — Clinician coverage diagnostics
- `src/aegis/observability/merge_accuracy.py` — Cross-population merge accuracy
- `src/aegis/observability/phase2_observability_test.py` — Observability tests
- `src/aegis/scoring/ambiguity_handling.py` — Specialty-classifier ambiguity handling
- `src/aegis/scoring/ambiguity_handling_test.py` — Ambiguity tests
- `src/aegis/identity/patent_conflicts.py` — Patent inventor disambiguation conflicts
- `src/aegis/identity/npi_pubmed_match.py` — NPI-PubMed name-match handler
- `src/aegis/identity/phase2_identity_test.py` — Identity error handling tests
- `src/aegis/sources/conferences/failure_log.py` — Conference parsing failure logger
- `src/aegis/sources/conferences/failure_log_test.py` — Failure log tests
- `tests/regression/test_cross_pop_merge.py` — Cross-population merge regression tests

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Observability dashboards (specialty dist, reassignment metrics, signal balance, clinician coverage, merge accuracy)
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Error handling (ambiguity handling, patent conflicts, NPI-PubMed match, conference failure log, regression tests)
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Spec Updater
  - Name: spec-updater
  - Role: Re-runs validations after build, writes Build Evidence into this spec
  - Agent Type: spec-updater

## Step by Step Tasks

### 1. Specialty Distribution Dashboard + Reassignment Metrics

- **Task ID**: specialty-observability
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the specialty distribution dashboard and reassignment-rate tracking modules.

    ## What to do

    1. Create `src/aegis/observability/specialty_dist.py`:

       ```python
       """Specialty distribution dashboard: cohort composition and multi-specialty tracking."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class SpecialtyDistMetrics(BaseModel):
           """Cohort specialty distribution snapshot."""

           model_config = ConfigDict(frozen=True)

           total_candidates: int
           per_specialty_count: dict[str, int]
           per_specialty_pct: dict[str, float]
           multi_specialty_count: int
           multi_specialty_pct: float
           multi_specialty_distribution: dict[str, float]  # specialty -> avg weight among multi


       class SpecialtyDistDashboard:
           """Compute and report specialty distribution metrics."""

           def compute(
               self,
               candidates: list[dict[str, dict[str, float]]],
           ) -> SpecialtyDistMetrics:
               """Compute specialty distribution from candidate specialty distributions.

               Input: list of {uuid: specialty_distribution} dicts.
               Each specialty_distribution is {specialty: probability}.
               """
               total = len(candidates)
               if total == 0:
                   return SpecialtyDistMetrics(
                       total_candidates=0,
                       per_specialty_count={},
                       per_specialty_pct={},
                       multi_specialty_count=0,
                       multi_specialty_pct=0.0,
                       multi_specialty_distribution={},
                   )

               per_specialty: dict[str, int] = {}
               multi_count = 0
               multi_weights: dict[str, list[float]] = {}

               for candidate_dist in candidates:
                   for _uuid, dist in candidate_dist.items():
                       if not dist:
                           continue
                       # Primary specialty
                       primary = max(dist, key=dist.get)  # type: ignore[arg-type]
                       per_specialty[primary] = per_specialty.get(primary, 0) + 1

                       # Multi-specialty: more than one specialty above 0.2
                       significant = {s: p for s, p in dist.items() if p >= 0.2}
                       if len(significant) > 1:
                           multi_count += 1
                           for s, p in significant.items():
                               if s not in multi_weights:
                                   multi_weights[s] = []
                               multi_weights[s].append(p)

               per_specialty_pct = {
                   s: round(100.0 * c / total, 2)
                   for s, c in per_specialty.items()
               }
               multi_dist = {
                   s: round(sum(ws) / len(ws), 4)
                   for s, ws in multi_weights.items()
               }

               return SpecialtyDistMetrics(
                   total_candidates=total,
                   per_specialty_count=per_specialty,
                   per_specialty_pct=per_specialty_pct,
                   multi_specialty_count=multi_count,
                   multi_specialty_pct=round(100.0 * multi_count / total, 2),
                   multi_specialty_distribution=multi_dist,
               )
       ```

    2. Create `src/aegis/observability/reassignment_metrics.py`:

       ```python
       """Specialty-reassignment rate and stability tracking."""

       from __future__ import annotations

       import logging
       import uuid as _uuid
       from datetime import date

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       CHURN_ALERT_THRESHOLD = 0.05  # 5% reassignment rate


       class ReassignmentRateMetrics(BaseModel):
           """Reassignment rate metrics for a single nightly run."""

           model_config = ConfigDict(frozen=True)

           run_date: date
           total_candidates: int
           reassigned_count: int
           reassignment_rate: float
           major_changes: int
           alert_triggered: bool
           alert_message: str | None


       class ReassignmentAlert(BaseModel):
           """Alert fired when reassignment rate exceeds threshold."""

           model_config = ConfigDict(frozen=True)

           alert_id: str
           run_date: date
           reassignment_rate: float
           threshold: float
           major_changes: int
           message: str


       class ReassignmentMetrics:
           """Track reassignment rates over time and alert on instability."""

           def __init__(
               self,
               churn_threshold: float = CHURN_ALERT_THRESHOLD,
           ) -> None:
               self._threshold = churn_threshold
               self._history: list[ReassignmentRateMetrics] = []

           def record_run(
               self,
               run_date: date,
               total_candidates: int,
               reassigned_count: int,
               major_changes: int,
           ) -> ReassignmentRateMetrics:
               """Record a nightly reassignment run and check for alerts."""
               rate = reassigned_count / max(total_candidates, 1)
               alert = rate > self._threshold
               alert_msg = None
               if alert:
                   alert_msg = (
                       f"Reassignment rate {rate:.1%} exceeds threshold "
                       f"{self._threshold:.1%} ({reassigned_count}/{total_candidates})"
                   )

               metrics = ReassignmentRateMetrics(
                   run_date=run_date,
                   total_candidates=total_candidates,
                   reassigned_count=reassigned_count,
                   reassignment_rate=round(rate, 4),
                   major_changes=major_changes,
                   alert_triggered=alert,
                   alert_message=alert_msg,
               )
               self._history.append(metrics)
               return metrics

           def get_history(self) -> list[ReassignmentRateMetrics]:
               """Return all recorded runs."""
               return list(self._history)

           def check_stability(self, window: int = 7) -> bool:
               """Check if reassignment rates have been stable over the last N runs.

               Stable = all runs below threshold.
               """
               recent = self._history[-window:]
               return all(not m.alert_triggered for m in recent)
       ```

    3. Update `src/aegis/observability/__init__.py` to add exports.

    ## Files to create
    - `src/aegis/observability/specialty_dist.py`
    - `src/aegis/observability/reassignment_metrics.py`

    ## Files to modify
    - `src/aegis/observability/__init__.py` — add exports

    ## Code patterns to follow
    - Follow `src/aegis/observability/coverage.py` and `drift.py` patterns
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - `from __future__ import annotations`
    - Logger at module level

    ## Acceptance criteria
    - Specialty distribution dashboard computes per-specialty counts and multi-specialty rates
    - Reassignment metrics fires alert when rate > 5%
    - Stability check over rolling window
    - mypy and ruff pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/observability/specialty_dist.py src/aegis/observability/reassignment_metrics.py && uv run ruff check src/aegis/observability/specialty_dist.py src/aegis/observability/reassignment_metrics.py
    ```

### 2. Signal Balance + Clinician Coverage + Merge Accuracy

- **Task ID**: signal-coverage-merge
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the patent-vs-paper signal balance dashboard, clinician coverage diagnostics, and cross-population merge accuracy tracking.

    ## What to do

    1. Create `src/aegis/observability/signal_balance.py`:

       ```python
       """Patent-vs-paper signal balance dashboard."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       PATENT_DOMINANCE_ALERT_THRESHOLD = 0.90


       class SignalBalanceMetrics(BaseModel):
           """Signal balance for a single candidate."""

           model_config = ConfigDict(frozen=True)

           candidate_uuid: str
           paper_contribution: float      # Fraction of v_c from papers
           patent_contribution: float     # Fraction of v_c from patents
           trial_contribution: float      # Fraction of v_c from trials
           grant_contribution: float      # Fraction of v_c from grants
           total_mesh_terms: int


       class CohortSignalBalance(BaseModel):
           """Aggregate signal balance across a cohort."""

           model_config = ConfigDict(frozen=True)

           total_candidates: int
           mean_paper_contribution: float
           mean_patent_contribution: float
           mean_trial_contribution: float
           patent_dominant_count: int     # Candidates where patent > 70%
           alert_triggered: bool
           alert_message: str | None


       class SignalBalanceDashboard:
           """Track per-candidate and cohort-level signal source contributions."""

           def compute_candidate(
               self,
               candidate_uuid: str,
               paper_mesh_count: int,
               patent_mesh_count: int,
               trial_mesh_count: int,
               grant_mesh_count: int,
           ) -> SignalBalanceMetrics:
               """Compute signal balance for a single candidate."""
               total = paper_mesh_count + patent_mesh_count + trial_mesh_count + grant_mesh_count
               safe_total = max(total, 1)
               return SignalBalanceMetrics(
                   candidate_uuid=candidate_uuid,
                   paper_contribution=round(paper_mesh_count / safe_total, 4),
                   patent_contribution=round(patent_mesh_count / safe_total, 4),
                   trial_contribution=round(trial_mesh_count / safe_total, 4),
                   grant_contribution=round(grant_mesh_count / safe_total, 4),
                   total_mesh_terms=total,
               )

           def compute_cohort(
               self,
               candidates: list[SignalBalanceMetrics],
           ) -> CohortSignalBalance:
               """Compute aggregate signal balance across a cohort."""
               n = len(candidates)
               if n == 0:
                   return CohortSignalBalance(
                       total_candidates=0,
                       mean_paper_contribution=0.0,
                       mean_patent_contribution=0.0,
                       mean_trial_contribution=0.0,
                       patent_dominant_count=0,
                       alert_triggered=False,
                       alert_message=None,
                   )

               paper_sum = sum(c.paper_contribution for c in candidates)
               patent_sum = sum(c.patent_contribution for c in candidates)
               trial_sum = sum(c.trial_contribution for c in candidates)
               patent_dominant = sum(
                   1 for c in candidates if c.patent_contribution >= 0.7
               )

               mean_patent = patent_sum / n
               alert = mean_patent >= PATENT_DOMINANCE_ALERT_THRESHOLD
               alert_msg = None
               if alert:
                   alert_msg = (
                       f"Patent contribution {mean_patent:.0%} exceeds "
                       f"cohort-level alert threshold ({PATENT_DOMINANCE_ALERT_THRESHOLD:.0%})"
                   )

               return CohortSignalBalance(
                   total_candidates=n,
                   mean_paper_contribution=round(paper_sum / n, 4),
                   mean_patent_contribution=round(mean_patent, 4),
                   mean_trial_contribution=round(trial_sum / n, 4),
                   patent_dominant_count=patent_dominant,
                   alert_triggered=alert,
                   alert_message=alert_msg,
               )
       ```

    2. Create `src/aegis/observability/clinician_coverage.py`:

       ```python
       """Clinician cohort coverage diagnostics."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       # States covered in Phase 2
       COVERED_STATES = frozenset({"CA", "NY", "TX", "FL", "IL", "PA", "OH", "NC", "GA", "MI"})
       GAP_STATES_PHASE2 = frozenset()  # All top-10 targeted


       class ClinicianCoverageMetrics(BaseModel):
           """Coverage diagnostics for the clinician cohort."""

           model_config = ConfigDict(frozen=True)

           total_clinicians: int
           npi_crosslinked_pct: float     # % NPIs linked to a Candidate UUID
           abms_coverage_pct: float       # % with ABMS data
           state_board_coverage_pct: float # % with state board data
           hospital_tier_pct: float       # % with hospital tier mapping
           publication_pct: float         # % with any PubMed publications
           covered_states: list[str]
           gap_states: list[str]          # States not yet covered
           coverage_caveats: list[str]    # List of coverage limitation descriptions


       class ClinicianCoverageDashboard:
           """Compute and report clinician-specific coverage diagnostics."""

           def compute(
               self,
               clinicians: list[dict[str, bool | str | None]],
           ) -> ClinicianCoverageMetrics:
               """Compute coverage from clinician attribute dicts.

               Each dict has keys: has_candidate_uuid, has_abms, has_state_board,
               has_hospital_tier, has_publications, practice_state.
               """
               total = len(clinicians)
               if total == 0:
                   return ClinicianCoverageMetrics(
                       total_clinicians=0,
                       npi_crosslinked_pct=0.0,
                       abms_coverage_pct=0.0,
                       state_board_coverage_pct=0.0,
                       hospital_tier_pct=0.0,
                       publication_pct=0.0,
                       covered_states=sorted(COVERED_STATES),
                       gap_states=[],
                       coverage_caveats=["No clinicians in cohort"],
                   )

               npi_linked = sum(1 for c in clinicians if c.get("has_candidate_uuid"))
               abms = sum(1 for c in clinicians if c.get("has_abms"))
               state_board = sum(1 for c in clinicians if c.get("has_state_board"))
               hospital = sum(1 for c in clinicians if c.get("has_hospital_tier"))
               publications = sum(1 for c in clinicians if c.get("has_publications"))

               # Identify states with clinicians but no board coverage
               all_states = {
                   c.get("practice_state")
                   for c in clinicians
                   if c.get("practice_state")
               }
               gap_states = sorted(
                   s for s in all_states
                   if s not in COVERED_STATES and isinstance(s, str)
               )

               caveats: list[str] = []
               pub_pct = 100.0 * publications / total
               if pub_pct < 30:
                   caveats.append(
                       f"Low publication rate ({pub_pct:.1f}%) — "
                       "many clinicians do not publish; this is expected"
                   )
               if gap_states:
                   caveats.append(
                       f"State board coverage gap: {', '.join(gap_states)} — "
                       "disciplinary data unavailable for these states"
                   )
               board_pct = 100.0 * state_board / total
               if board_pct < 50:
                   caveats.append(
                       f"State board coverage {board_pct:.1f}% — "
                       "10-state Phase 2 coverage is incomplete"
                   )

               return ClinicianCoverageMetrics(
                   total_clinicians=total,
                   npi_crosslinked_pct=round(100.0 * npi_linked / total, 2),
                   abms_coverage_pct=round(100.0 * abms / total, 2),
                   state_board_coverage_pct=round(board_pct, 2),
                   hospital_tier_pct=round(100.0 * hospital / total, 2),
                   publication_pct=round(pub_pct, 2),
                   covered_states=sorted(COVERED_STATES),
                   gap_states=gap_states,
                   coverage_caveats=caveats,
               )
       ```

    3. Create `src/aegis/observability/merge_accuracy.py`:

       ```python
       """Cross-population identity merge accuracy tracking."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       PRECISION_TARGET = 0.99
       RECALL_TARGET = 0.85


       class MergeAccuracyMetrics(BaseModel):
           """Precision and recall for cross-population identity merging."""

           model_config = ConfigDict(frozen=True)

           total_test_cases: int
           true_positives: int
           false_positives: int
           false_negatives: int
           precision: float
           recall: float
           f1_score: float
           meets_precision_target: bool
           meets_recall_target: bool


       class MergeAccuracyTracker:
           """Track merge accuracy against held-out test sets."""

           def evaluate(
               self,
               predictions: list[tuple[str, str, bool]],
               ground_truth: list[tuple[str, str, bool]],
           ) -> MergeAccuracyMetrics:
               """Evaluate merge predictions against ground truth.

               Each tuple: (uuid_a, uuid_b, should_merge).
               """
               pred_set = {(a, b): merge for a, b, merge in predictions}
               truth_set = {(a, b): merge for a, b, merge in ground_truth}

               tp = fp = fn = 0
               for key, should_merge in truth_set.items():
                   predicted = pred_set.get(key, False)
                   if should_merge and predicted:
                       tp += 1
                   elif not should_merge and predicted:
                       fp += 1
                   elif should_merge and not predicted:
                       fn += 1

               precision = tp / max(tp + fp, 1)
               recall = tp / max(tp + fn, 1)
               f1 = (
                   2 * precision * recall / max(precision + recall, 1e-8)
               )

               return MergeAccuracyMetrics(
                   total_test_cases=len(ground_truth),
                   true_positives=tp,
                   false_positives=fp,
                   false_negatives=fn,
                   precision=round(precision, 4),
                   recall=round(recall, 4),
                   f1_score=round(f1, 4),
                   meets_precision_target=precision >= PRECISION_TARGET,
                   meets_recall_target=recall >= RECALL_TARGET,
               )
       ```

    4. Create `src/aegis/observability/phase2_observability_test.py`:
       - `test_specialty_dist_basic`: 10 candidates across 3 specialties, verify counts
       - `test_specialty_dist_multi_specialty`: Candidates with >1 specialty above 0.2
       - `test_reassignment_rate_alert`: Rate above 5% triggers alert
       - `test_reassignment_stability`: 7 stable runs -> stable
       - `test_signal_balance_candidate`: Patent-heavy candidate -> high patent contribution
       - `test_signal_balance_cohort_alert`: Cohort-level patent dominance alert
       - `test_clinician_coverage_basic`: 100 clinicians with varying attributes
       - `test_clinician_gap_states`: Clinicians in uncovered states -> gap flagged
       - `test_clinician_low_publication_caveat`: Low pub rate -> caveat
       - `test_merge_accuracy_perfect`: All correct -> precision=1.0, recall=1.0
       - `test_merge_accuracy_with_errors`: Mix of TP/FP/FN -> correct metrics
       - `test_merge_precision_target`: Verify meets_precision_target flag

    5. Update `src/aegis/observability/__init__.py` with all new exports.

    ## Files to create
    - `src/aegis/observability/specialty_dist.py`
    - `src/aegis/observability/reassignment_metrics.py`
    - `src/aegis/observability/signal_balance.py`
    - `src/aegis/observability/clinician_coverage.py`
    - `src/aegis/observability/merge_accuracy.py`
    - `src/aegis/observability/phase2_observability_test.py`

    ## Files to modify
    - `src/aegis/observability/__init__.py` — add all new exports

    ## Acceptance criteria
    - All 5 observability modules exist and are importable
    - Reassignment alert fires at > 5% churn
    - Clinician coverage flags gap states
    - Merge accuracy tracks precision/recall against targets
    - All tests pass
    - mypy and ruff pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/phase2_observability_test.py -v && uv run mypy src/aegis/observability/specialty_dist.py src/aegis/observability/reassignment_metrics.py src/aegis/observability/signal_balance.py src/aegis/observability/clinician_coverage.py src/aegis/observability/merge_accuracy.py && uv run ruff check src/aegis/observability/
    ```

### 3. Specialty-Classifier Ambiguity Handling

- **Task ID**: ambiguity-handling
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the ambiguity handling module: below 0.6 classifier confidence, score candidates under top-2 specialty weight vectors and report dual-rank results.

    ## What to do

    1. Create `src/aegis/scoring/ambiguity_handling.py`:

       ```python
       """Specialty-classifier ambiguity handling: dual-rank for uncertain candidates."""

       from __future__ import annotations

       import logging

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       AMBIGUITY_THRESHOLD = 0.6


       class DualRankResult(BaseModel):
           """Dual-rank result for an ambiguous candidate."""

           model_config = ConfigDict(frozen=True)

           candidate_uuid: str
           is_ambiguous: bool
           primary_specialty: str
           primary_rank_percentile: float
           secondary_specialty: str | None
           secondary_rank_percentile: float | None
           confidence: float
           recommendation: str            # Human-readable note


       class AmbiguityHandler:
           """Handle specialty-classifier ambiguity.

           Below AMBIGUITY_THRESHOLD: score under top-2 specialty weight vectors.
           Above: single-specialty scoring with ambiguity flag suppressed.
           """

           def __init__(
               self,
               threshold: float = AMBIGUITY_THRESHOLD,
           ) -> None:
               self._threshold = threshold

           def evaluate(
               self,
               candidate_uuid: str,
               specialty_probabilities: dict[str, float],
               score_under_specialty: dict[str, float],
           ) -> DualRankResult:
               """Evaluate ambiguity and produce single or dual rank.

               Args:
                   candidate_uuid: Candidate identifier
                   specialty_probabilities: {specialty: probability} from classifier
                   score_under_specialty: {specialty: Q(c) percentile} pre-computed
               """
               if not specialty_probabilities:
                   return DualRankResult(
                       candidate_uuid=candidate_uuid,
                       is_ambiguous=True,
                       primary_specialty="translational",
                       primary_rank_percentile=0.0,
                       secondary_specialty=None,
                       secondary_rank_percentile=None,
                       confidence=0.0,
                       recommendation="No specialty data available; defaulting to translational",
                   )

               sorted_specs = sorted(
                   specialty_probabilities.items(),
                   key=lambda x: x[1],
                   reverse=True,
               )
               primary_spec, primary_prob = sorted_specs[0]
               primary_score = score_under_specialty.get(primary_spec, 0.0)

               if primary_prob >= self._threshold:
                   return DualRankResult(
                       candidate_uuid=candidate_uuid,
                       is_ambiguous=False,
                       primary_specialty=primary_spec,
                       primary_rank_percentile=round(primary_score, 6),
                       secondary_specialty=None,
                       secondary_rank_percentile=None,
                       confidence=round(primary_prob, 4),
                       recommendation=f"High-confidence {primary_spec} classification",
                   )

               # Ambiguous: provide dual rank
               secondary_spec = sorted_specs[1][0] if len(sorted_specs) > 1 else None
               secondary_score = (
                   score_under_specialty.get(secondary_spec, 0.0)
                   if secondary_spec
                   else None
               )

               return DualRankResult(
                   candidate_uuid=candidate_uuid,
                   is_ambiguous=True,
                   primary_specialty=primary_spec,
                   primary_rank_percentile=round(primary_score, 6),
                   secondary_specialty=secondary_spec,
                   secondary_rank_percentile=(
                       round(secondary_score, 6) if secondary_score is not None else None
                   ),
                   confidence=round(primary_prob, 4),
                   recommendation=(
                       f"Ambiguous ({primary_prob:.0%} confidence); "
                       f"ranked under both {primary_spec} and {secondary_spec}"
                   ),
               )
       ```

    2. Create `src/aegis/scoring/ambiguity_handling_test.py`:
       - `test_high_confidence_single_rank`: Confidence 0.85 -> not ambiguous, single rank
       - `test_low_confidence_dual_rank`: Confidence 0.45 -> ambiguous, dual rank
       - `test_threshold_boundary`: Exactly 0.6 -> not ambiguous
       - `test_empty_probabilities`: No data -> ambiguous, default translational
       - `test_dual_rank_both_scores`: Verify both primary and secondary scores populated
       - `test_recommendation_text`: High confidence -> "High-confidence..." text

    3. Update `src/aegis/scoring/__init__.py` to add exports: `AmbiguityHandler`, `DualRankResult`.

    ## Files to create
    - `src/aegis/scoring/ambiguity_handling.py`
    - `src/aegis/scoring/ambiguity_handling_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` — add ambiguity exports

    ## Acceptance criteria
    - Ambiguous candidate gets dual-rank with both specialties
    - High-confidence candidate gets single-rank
    - Ambiguity flag persists until confidence rises
    - All tests pass
    - mypy and ruff pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/ambiguity_handling_test.py -v && uv run mypy src/aegis/scoring/ambiguity_handling.py && uv run ruff check src/aegis/scoring/ambiguity_handling.py
    ```

### 4. Patent Conflicts + NPI-PubMed Match + Conference Failure Log

- **Task ID**: error-handling
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the patent inventor disambiguation conflict handler, NPI-PubMed name-match HITL router, and conference abstract parsing failure logger.

    ## What to do

    1. Create `src/aegis/identity/patent_conflicts.py`:

       ```python
       """Patent inventor disambiguation conflict resolution."""

       from __future__ import annotations

       import logging
       import uuid as _uuid
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class PatentConflict(BaseModel):
           """A conflict between PatentsView and Fellegi-Sunter disambiguation."""

           model_config = ConfigDict(frozen=True)

           conflict_id: str
           patent_number: str
           inventor_name: str
           patentsview_inventor_id: str
           aegis_candidate_uuid: str | None
           conflict_type: str            # "split" (USPTO splits one) or "merge" (USPTO merges two)
           confidence_gap: float          # Difference between the two systems
           created_at: datetime
           status: str                   # "pending", "resolved", "excluded"


       class PatentConflictHandler:
           """Handle patent inventor disambiguation conflicts.

           When PatentsView and Fellegi-Sunter disagree, the patent is
           excluded from v_c until HITL resolution.
           """

           def __init__(self) -> None:
               self._conflicts: list[PatentConflict] = []

           def report_conflict(
               self,
               patent_number: str,
               inventor_name: str,
               patentsview_id: str,
               aegis_uuid: str | None,
               conflict_type: str,
               confidence_gap: float,
           ) -> PatentConflict:
               """Report a new disambiguation conflict."""
               conflict = PatentConflict(
                   conflict_id=str(_uuid.uuid4()),
                   patent_number=patent_number,
                   inventor_name=inventor_name,
                   patentsview_inventor_id=patentsview_id,
                   aegis_candidate_uuid=aegis_uuid,
                   conflict_type=conflict_type,
                   confidence_gap=round(confidence_gap, 4),
                   created_at=datetime.now(UTC),
                   status="pending",
               )
               self._conflicts.append(conflict)
               logger.info(
                   "Patent conflict reported: %s inventor %s (%s)",
                   patent_number, inventor_name, conflict_type,
               )
               return conflict

           def get_pending(self) -> list[PatentConflict]:
               """Return all pending conflicts for HITL review."""
               return [c for c in self._conflicts if c.status == "pending"]

           def get_excluded_patents(self) -> set[str]:
               """Return patent numbers excluded from v_c due to conflicts."""
               return {
                   c.patent_number for c in self._conflicts
                   if c.status in ("pending", "excluded")
               }

           @property
           def conflict_rate(self) -> float:
               """Fraction of patents with conflicts."""
               if not self._conflicts:
                   return 0.0
               return len(self._conflicts)  # Denominator requires total patent count
       ```

    2. Create `src/aegis/identity/npi_pubmed_match.py`:

       ```python
       """NPI to PubMed author name-match handler with HITL routing."""

       from __future__ import annotations

       import logging
       from typing import Literal

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       # Higher threshold than general linkage because NPI mis-attribution
       # can wrongly hard-zero a candidate via state board lookup
       AUTO_LINK_THRESHOLD = 0.95
       REVIEW_THRESHOLD = 0.5


       class NpiPubmedMatch(BaseModel):
           """Result of NPI-to-PubMed author matching."""

           model_config = ConfigDict(frozen=True)

           npi: str
           pubmed_author_name: str
           npi_provider_name: str
           confidence: float
           action: Literal["auto-link", "review", "reject"]
           specialty_match: bool          # NPI taxonomy matches PubMed MeSH
           address_match: bool            # Practice address ~ affiliation
           rejection_signals: list[str]   # Reasons for low confidence


       class NpiPubmedMatcher:
           """Match NPI records to PubMed authors with strict confidence thresholds.

           NEVER auto-link below 0.95 because NPI mis-attribution can
           wrongly hard-zero a candidate via state medical board action lookup.
           """

           def match(
               self,
               npi: str,
               npi_name: str,
               npi_specialty: str | None,
               npi_state: str | None,
               pubmed_author: str,
               pubmed_affiliation: str | None,
               pubmed_mesh: list[str] | None,
           ) -> NpiPubmedMatch:
               """Match a single NPI to a PubMed author."""
               rejection_signals: list[str] = []

               # Name similarity (basic)
               name_sim = self._name_similarity(npi_name, pubmed_author)

               # Specialty match
               specialty_match = False
               if npi_specialty and pubmed_mesh:
                   specialty_match = self._specialty_matches_mesh(
                       npi_specialty, pubmed_mesh
                   )
               if not specialty_match:
                   rejection_signals.append("specialty_mismatch")

               # Address/affiliation match
               address_match = False
               if npi_state and pubmed_affiliation:
                   address_match = npi_state.upper() in pubmed_affiliation.upper()
               if not address_match:
                   rejection_signals.append("address_mismatch")

               # Compute confidence
               confidence = name_sim
               if specialty_match:
                   confidence += 0.1
               if address_match:
                   confidence += 0.1
               confidence = min(confidence, 1.0)

               # Classify
               if confidence >= AUTO_LINK_THRESHOLD:
                   action: Literal["auto-link", "review", "reject"] = "auto-link"
               elif confidence >= REVIEW_THRESHOLD:
                   action = "review"
               else:
                   action = "reject"

               return NpiPubmedMatch(
                   npi=npi,
                   pubmed_author_name=pubmed_author,
                   npi_provider_name=npi_name,
                   confidence=round(confidence, 4),
                   action=action,
                   specialty_match=specialty_match,
                   address_match=address_match,
                   rejection_signals=rejection_signals,
               )

           @staticmethod
           def _name_similarity(name_a: str, name_b: str) -> float:
               """Simple name similarity (production: use thefuzz)."""
               a = name_a.lower().strip()
               b = name_b.lower().strip()
               if a == b:
                   return 1.0
               # Check last name match
               a_parts = a.split()
               b_parts = b.split()
               if a_parts and b_parts and a_parts[-1] == b_parts[-1]:
                   return 0.7
               return 0.3

           @staticmethod
           def _specialty_matches_mesh(
               taxonomy_code: str, mesh_terms: list[str]
           ) -> bool:
               """Check if NPI taxonomy loosely matches PubMed MeSH terms.

               Stub: production uses NUCC-to-MeSH mapping.
               """
               # Simplified: any non-empty mesh is a weak match
               return bool(mesh_terms)
       ```

    3. Create `src/aegis/sources/conferences/failure_log.py`:

       ```python
       """Conference abstract parsing failure logger."""

       from __future__ import annotations

       import logging
       import uuid as _uuid
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class ParseFailure(BaseModel):
           """A single conference abstract parsing failure."""

           model_config = ConfigDict(frozen=True)

           failure_id: str
           conference: str
           year: int
           source_url: str | None
           error_type: str               # "pdf_extraction", "malformed_html", "timeout", etc.
           error_message: str
           timestamp: datetime


       class ConferenceFailureStats(BaseModel):
           """Per-conference failure rate statistics."""

           model_config = ConfigDict(frozen=True)

           conference: str
           total_attempted: int
           total_failed: int
           failure_rate: float
           most_common_error: str | None


       class ConferenceFailureLog:
           """Log and track conference abstract parsing failures.

           Per-conference success rate tracked for quarterly review.
           Failures do not block ingestion pipeline.
           """

           def __init__(self) -> None:
               self._failures: list[ParseFailure] = []
               self._attempts: dict[str, int] = {}

           def log_failure(
               self,
               conference: str,
               year: int,
               source_url: str | None,
               error_type: str,
               error_message: str,
           ) -> ParseFailure:
               """Log a parsing failure. Pipeline continues."""
               failure = ParseFailure(
                   failure_id=str(_uuid.uuid4()),
                   conference=conference,
                   year=year,
                   source_url=source_url,
                   error_type=error_type,
                   error_message=error_message,
                   timestamp=datetime.now(UTC),
               )
               self._failures.append(failure)
               logger.warning(
                   "Conference parse failure: %s %d — %s: %s",
                   conference, year, error_type, error_message,
               )
               return failure

           def record_attempt(self, conference: str) -> None:
               """Record an ingestion attempt (success or failure)."""
               self._attempts[conference] = self._attempts.get(conference, 0) + 1

           def get_stats(self, conference: str) -> ConferenceFailureStats:
               """Get failure statistics for a conference."""
               conf_failures = [
                   f for f in self._failures if f.conference == conference
               ]
               total_attempted = self._attempts.get(conference, 0)
               total_failed = len(conf_failures)

               # Most common error type
               error_counts: dict[str, int] = {}
               for f in conf_failures:
                   error_counts[f.error_type] = error_counts.get(f.error_type, 0) + 1
               most_common = (
                   max(error_counts, key=error_counts.get)  # type: ignore[arg-type]
                   if error_counts
                   else None
               )

               return ConferenceFailureStats(
                   conference=conference,
                   total_attempted=total_attempted,
                   total_failed=total_failed,
                   failure_rate=(
                       round(total_failed / max(total_attempted, 1), 4)
                   ),
                   most_common_error=most_common,
               )

           def get_all_failures(self) -> list[ParseFailure]:
               """Return all logged failures."""
               return list(self._failures)
       ```

    4. Create `src/aegis/identity/phase2_identity_test.py`:
       - `test_patent_conflict_report`: Report a conflict, verify in pending
       - `test_excluded_patents`: Pending conflicts -> patents excluded from v_c
       - `test_npi_pubmed_auto_link`: High confidence -> auto-link
       - `test_npi_pubmed_review`: Medium confidence -> review
       - `test_npi_pubmed_reject`: Low confidence -> reject
       - `test_npi_pubmed_never_auto_below_095`: Verify 0.94 -> review, not auto-link
       - `test_npi_specialty_mismatch_signal`: Specialty mismatch in rejection_signals

    5. Create `src/aegis/sources/conferences/failure_log_test.py`:
       - `test_log_failure`: Log a failure, verify in list
       - `test_failure_stats`: Log 3 failures of 10 attempts, verify rate = 0.3
       - `test_most_common_error`: Multiple error types, verify most common
       - `test_pipeline_continues`: Logging failure does not raise exception
       - `test_failure_model`: Verify ParseFailure fields

    6. Create `tests/regression/test_cross_pop_merge.py`:
       ```python
       """Regression tests for cross-population identity merge."""

       from __future__ import annotations


       def test_merge_precision_threshold() -> None:
           """Cross-population auto-merge precision target >= 99%."""
           from aegis.observability.merge_accuracy import MergeAccuracyTracker

           tracker = MergeAccuracyTracker()
           # Simulate 100 test cases: 95 true merges, 5 non-merges
           predictions = [(f"a{i}", f"b{i}", True) for i in range(95)]
           predictions += [(f"a{i}", f"b{i}", False) for i in range(95, 100)]
           ground_truth = [(f"a{i}", f"b{i}", True) for i in range(95)]
           ground_truth += [(f"a{i}", f"b{i}", False) for i in range(95, 100)]

           metrics = tracker.evaluate(predictions, ground_truth)
           assert metrics.precision >= 0.99
           assert metrics.meets_precision_target
       ```

    ## Files to create
    - `src/aegis/identity/patent_conflicts.py`
    - `src/aegis/identity/npi_pubmed_match.py`
    - `src/aegis/sources/conferences/failure_log.py`
    - `src/aegis/identity/phase2_identity_test.py`
    - `src/aegis/sources/conferences/failure_log_test.py`
    - `tests/regression/test_cross_pop_merge.py`

    ## Files to modify
    - `src/aegis/identity/__init__.py` — add patent_conflicts and npi_pubmed exports
    - `src/aegis/sources/conferences/__init__.py` — add failure_log exports

    ## Acceptance criteria
    - Patent conflicts surface to HITL; excluded from v_c
    - NPI-PubMed NEVER auto-links below 0.95
    - Conference failure logging does not block pipeline
    - Per-conference failure rate tracking works
    - Regression test for merge precision >= 99%
    - All tests pass
    - mypy and ruff pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/identity/phase2_identity_test.py src/aegis/sources/conferences/failure_log_test.py tests/regression/test_cross_pop_merge.py -v && uv run mypy src/aegis/identity/patent_conflicts.py src/aegis/identity/npi_pubmed_match.py src/aegis/sources/conferences/failure_log.py && uv run ruff check src/aegis/identity/patent_conflicts.py src/aegis/identity/npi_pubmed_match.py src/aegis/sources/conferences/failure_log.py
    ```

### 5. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: specialty-observability, signal-coverage-merge, ambiguity-handling, error-handling
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for Phase 2e.

    ## Validation Commands

    1. Verify all observability imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.observability.specialty_dist import SpecialtyDistDashboard
    from aegis.observability.reassignment_metrics import ReassignmentMetrics
    from aegis.observability.signal_balance import SignalBalanceDashboard
    from aegis.observability.clinician_coverage import ClinicianCoverageDashboard
    from aegis.observability.merge_accuracy import MergeAccuracyTracker
    print('All observability imports OK')
    "
    ```

    2. Verify all error handling imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.scoring.ambiguity_handling import AmbiguityHandler, DualRankResult
    from aegis.identity.patent_conflicts import PatentConflictHandler
    from aegis.identity.npi_pubmed_match import NpiPubmedMatcher
    from aegis.sources.conferences.failure_log import ConferenceFailureLog
    print('All error handling imports OK')
    "
    ```

    3. Run all Phase 2e tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/phase2_observability_test.py src/aegis/scoring/ambiguity_handling_test.py src/aegis/identity/phase2_identity_test.py src/aegis/sources/conferences/failure_log_test.py tests/regression/test_cross_pop_merge.py -v
    ```

    4. Run mypy on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/observability/specialty_dist.py src/aegis/observability/reassignment_metrics.py src/aegis/observability/signal_balance.py src/aegis/observability/clinician_coverage.py src/aegis/observability/merge_accuracy.py src/aegis/scoring/ambiguity_handling.py src/aegis/identity/patent_conflicts.py src/aegis/identity/npi_pubmed_match.py src/aegis/sources/conferences/failure_log.py
    ```

    5. Run ruff on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/observability/ src/aegis/scoring/ambiguity_handling.py src/aegis/identity/patent_conflicts.py src/aegis/identity/npi_pubmed_match.py src/aegis/sources/conferences/failure_log.py
    ```

    6. Verify existing tests still pass:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/coverage_test.py src/aegis/observability/drift_test.py -v
    ```

    ## Acceptance Criteria
    - All 5 observability modules exist and compute metrics
    - Reassignment alert fires at > 5% churn rate
    - Clinician coverage flags gap states and low-publication caveats
    - Merge accuracy tracks precision >= 99% and recall >= 85% targets
    - Ambiguous candidates get dual-rank output
    - High-confidence candidates get single-rank
    - Patent conflicts surface to HITL; excluded patents tracked
    - NPI-PubMed NEVER auto-links below 0.95
    - Conference failures logged without blocking pipeline
    - Per-conference failure rate statistics work
    - Regression test for merge precision passes
    - All new tests pass
    - mypy strict passes
    - ruff passes
    - Existing observability tests unbroken

## Acceptance Criteria

- Specialty distribution dashboard at `src/aegis/observability/specialty_dist.py` shows per-specialty cohort sizes and multi-specialty rates
- Reassignment-rate tracker at `src/aegis/observability/reassignment_metrics.py` alerts when churn > 5%
- Patent-vs-paper signal balance at `src/aegis/observability/signal_balance.py` shows per-candidate and cohort-level contribution breakdown
- Clinician coverage diagnostics at `src/aegis/observability/clinician_coverage.py` reports NPI cross-link rate, ABMS/state-board/hospital-tier coverage, publication rate, and gap-state flags
- Cross-population merge accuracy at `src/aegis/observability/merge_accuracy.py` tracks precision (target >= 99%) and recall (target >= 85%)
- Ambiguity handler at `src/aegis/scoring/ambiguity_handling.py` produces dual-rank for < 0.6 confidence, single-rank for >= 0.6
- Patent conflict handler at `src/aegis/identity/patent_conflicts.py` surfaces conflicts to HITL and excludes patents from `v_c`
- NPI-PubMed matcher at `src/aegis/identity/npi_pubmed_match.py` NEVER auto-links below 0.95 confidence
- Conference failure log at `src/aegis/sources/conferences/failure_log.py` logs without blocking pipeline and tracks per-conference failure rates
- All new tests pass
- mypy strict mode passes
- ruff lint passes
- No existing Phase 0/1 tests broken

## Validation Commands

- `cd /Users/anvith/aegis && uv run pytest src/aegis/observability/phase2_observability_test.py src/aegis/scoring/ambiguity_handling_test.py src/aegis/identity/phase2_identity_test.py src/aegis/sources/conferences/failure_log_test.py tests/regression/test_cross_pop_merge.py -v` — Run all Phase 2e tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/observability/specialty_dist.py src/aegis/observability/reassignment_metrics.py src/aegis/observability/signal_balance.py src/aegis/observability/clinician_coverage.py src/aegis/observability/merge_accuracy.py src/aegis/scoring/ambiguity_handling.py src/aegis/identity/patent_conflicts.py src/aegis/identity/npi_pubmed_match.py src/aegis/sources/conferences/failure_log.py` — Type-check
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/observability/ src/aegis/scoring/ambiguity_handling.py src/aegis/identity/patent_conflicts.py src/aegis/identity/npi_pubmed_match.py src/aegis/sources/conferences/failure_log.py` — Lint

## Notes

- The NPI-PubMed 0.95 auto-link threshold is deliberately higher than the general 0.95 threshold in `probabilistic.py` because NPI mis-attribution at the clinician level can wrongly hard-zero a candidate via state board action lookup — a high-impact error.
- Patent inventor disambiguation conflict rate is expected at ~5%; the handler ensures these don't silently degrade `v_c`.
- Conference parsing failures are heterogeneous (PDF, HTML, timeout); the failure log captures error type to inform prompt-engineering review.
- Clinician coverage dashboard distinguishes "missing data" from "this dimension genuinely doesn't apply" — many clinicians legitimately have zero publications.
- All observability modules follow the same Pydantic-frozen-model + compute-method pattern established in Phase 0e.
