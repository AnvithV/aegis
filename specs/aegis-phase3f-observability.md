# Plan: Phase 3f — Observability & Governance Layer

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase3f-observability.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build the observability and governance layer for Aegis Phase 3. This sub-spec covers four tasks from the Phase 3 master plan (`docs/plans/aegis/phase-3-production.md`):

- **Task 2.1** (query latency SLO monitoring): Define and monitor query-latency SLO -- <500ms p95, <1500ms p99, success rate >=99.9%. Per-customer and per-cohort breakdown. SLO budget tracking over rolling 30-day windows. Paging on budget breach.

- **Task 2.2** (per-customer task-quality tracking): Track downstream task quality per customer over time. Fleiss kappa and accept rate trends per customer. Aggregate metrics only -- no per-task PHI. Customer-side dashboard exposed via API.

- **Task 2.3** (refresh-cadence SLA tracking): Per-source compliance against SLAs from the program overview (codified in `src/aegis/observability/freshness.py:SOURCE_SLOS`). Hard-gate sources (retraction_watch, ori, ofac, sam, state_board_*) page on-call immediately on breach. Non-hard-gate sources weekly summary. Synthetic stuck-source test to validate alerting.

- **Task 2.5** (weight-drift over time): Track alpha/beta/gamma and per-family weights across weekly refits. Per-specialty time series. Annotations for major events (new source ingested, customer pilot started). Sudden jumps signal data-quality issues.

## Objective

When this plan is complete:
1. A `QuerySloMonitor` at `src/aegis/observability/query_slo.py` records per-request latency and success/failure with customer and cohort labels, computes rolling p95/p99/success-rate against SLO targets, tracks SLO error-budget consumption over 30-day windows, and emits Prometheus metrics + alerts on budget breach.
2. A `CustomerQualityTracker` at `src/aegis/observability/customer_quality.py` ingests aggregate task-quality metrics (Fleiss kappa, accept rate) per customer over time, persists time-series snapshots in DuckDB, computes trend slopes, and exposes a summary via a JSON-serializable API response model.
3. A `RefreshSlaTracker` at `src/aegis/observability/refresh_sla.py` checks per-source compliance against the SLO thresholds in `SOURCE_SLOS`, classifies sources as hard-gate or non-hard-gate, produces immediate page-level alerts for hard-gate breaches and weekly summary reports for non-hard-gate breaches, and includes a synthetic stuck-source test.
4. A `WeightDriftTracker` at `src/aegis/observability/weight_drift.py` loads weight history from versioned YAML files across all specialties, computes per-parameter time series, supports event annotations (new source, customer pilot), detects sudden jumps, and generates trend reports.
5. Prometheus alert rules at `ops/aegis/phase3f_alerts.yaml` cover all four subsystems.
6. `src/aegis/observability/__init__.py` exports all new public symbols.
7. All modules pass mypy strict + ruff lint and have comprehensive unit tests.

## Problem Statement

Phase 1d built foundational observability: score-distribution dashboards, apex recall regression, audit consistency, integrity-gate hit-rate, and weight stability (point-in-time comparison). Phase 2e added multi-population-specific observability (specialty distribution, clinician coverage, signal balance, merge accuracy, reassignment metrics). However, Phase 3 introduces a customer-facing API, a downstream-quality feedback loop, and steady-state weight relearning that create new observability needs:

1. **Query latency**: The API has a contractual SLO (<500ms p95, <1500ms p99, >=99.9% success). Phase 1's `tests/perf/test_query_latency.py` is a one-shot benchmark, not continuous monitoring. There is no per-customer or per-cohort latency breakdown, no SLO budget tracking, and no paging on breach.

2. **Customer quality**: Downstream task-quality data (Fleiss kappa, accept rate) flows in via the feedback endpoint (Phase 3c), but there is no per-customer trend tracking. Without trends, we cannot detect whether a customer's task quality is degrading over time or compare across customers.

3. **Refresh cadence**: `FreshnessMetrics` in `src/aegis/observability/freshness.py` tracks per-source freshness and exposes Prometheus metrics, but has no alerting logic for SLA breaches -- it only records the current state. There is no distinction between hard-gate sources (which need immediate paging) and non-hard-gate sources (which need weekly summary). There is no synthetic stuck-source test.

4. **Weight drift**: Phase 1d's `WeightStabilityTracker` compares exactly two consecutive weight versions. Phase 3 needs a longitudinal view across 6+ months of weekly refits, per-specialty, with event annotations and jump detection. This is a time-series problem, not a point comparison.

## Solution Approach

1. **QuerySloMonitor** (Task 2.1): A Prometheus-instrumented class following the pattern of `FreshnessMetrics` and `ApiHealthMetrics`. Records per-request latency as a Histogram with `customer` and `cohort` labels. Computes p95, p99, and success rate from in-memory rolling windows. Tracks SLO error-budget consumption: the fraction of a 30-day budget already consumed. Exposes Prometheus gauges and produces `SloStatusReport` snapshots for the alerting layer. The approach follows the existing `CollectorRegistry` pattern exactly.

2. **CustomerQualityTracker** (Task 2.2): A DuckDB-backed tracker following the `DriftDetector` and `ScoreDistributionMonitor` pattern. Stores per-customer aggregate quality snapshots (Fleiss kappa, accept rate, sample count) with timestamps. Computes trend slopes via simple linear regression on the last N data points. Exposes a `CustomerQualityReport` Pydantic model suitable for JSON serialization and API response. No per-task PHI -- only aggregate metrics per customer per time window.

3. **RefreshSlaTracker** (Task 2.3): Wraps the existing `SOURCE_SLOS` dict from `freshness.py` and adds classification of sources into hard-gate vs non-hard-gate (using the `IntegritySource` enum from `src/aegis/ingestion/event_dispatcher.py`). On each check cycle, compares current source age against SLA threshold. For hard-gate breaches, emits a critical Prometheus metric and produces an `SlaBreachAlert`. For non-hard-gate breaches, accumulates into a `WeeklySlaSummary`. A synthetic stuck-source test verifies the alerting pipeline fires correctly.

4. **WeightDriftTracker** (Task 2.5): A DuckDB-backed tracker that stores per-refit weight snapshots (version, specialty, parameter name, value, refit_date). Loads history from existing `config/aegis/weights/` YAML files on initialization. Supports `record_annotation(date, event_description)` for major events. Computes per-parameter time series and detects sudden jumps (>25% relative change between consecutive refits, inheriting the threshold from `WeightStabilityTracker`). Generates a `WeightDriftReport` with per-specialty time series and jump alerts.

## Relevant Files

### Existing Files (read, import from, or extend)

- `src/aegis/observability/__init__.py` -- Package exports. Must add new public classes from all four new modules.
- `src/aegis/observability/freshness.py` -- `FreshnessMetrics`, `SOURCE_SLOS` dict. Pattern for Prometheus metric naming and registry usage. `RefreshSlaTracker` reads `SOURCE_SLOS` directly.
- `src/aegis/observability/api_health.py` -- `ApiHealthMetrics`. Pattern for Prometheus Histogram/Counter with labels. `QuerySloMonitor` follows the same structure.
- `src/aegis/observability/drift.py` -- `DriftDetector`, `DriftAlert`, `DriftConfig`. Pattern for DuckDB-backed daily tracking with anomaly alerting. `WeightDriftTracker` follows this pattern.
- `src/aegis/observability/score_dist.py` -- `ScoreDistributionMonitor`. Pattern for DuckDB table creation, upsert, snapshot retrieval. `CustomerQualityTracker` follows this pattern.
- `src/aegis/observability/weight_stability.py` -- `WeightStabilityTracker`, `WeightShift`, `StabilityReport`. `WeightDriftTracker` reuses the per-parameter comparison logic and extends it to time-series tracking.
- `src/aegis/observability/coverage.py` -- `CoverageDiagnostics`. Pattern for HTML report generation with inline CSS.
- `src/aegis/observability/integrity_dashboard.py` -- `IntegrityDashboard`, `DailySummary`, `SpikeAlert`. Pattern for DuckDB event tracking with spike detection.
- `src/aegis/ingestion/event_dispatcher.py` -- `IntegritySource` enum. Used by `RefreshSlaTracker` to classify hard-gate sources.
- `src/aegis/scoring/quality_prior.py` -- `WeightVector`, `load_weight_vector()`. Used by `WeightDriftTracker` to load weight history from YAML.
- `src/aegis/learning/refit_scheduler.py` -- `RefitScheduler`, `RefitResult`. Context for understanding when refits happen and what outputs they produce.
- `src/aegis/api/schemas.py` -- `QueryRequest`, `QueryResponse`, `CandidateResult`. Used by `QuerySloMonitor` to understand the request/response shapes.
- `config/aegis/weights/translational_v1.yaml` -- Weight YAML format. `WeightDriftTracker` reads all weight files.
- `config/aegis/weights/drug_discovery_v1.yaml` -- Drug-discovery weight vector.
- `config/aegis/weights/clinician_v1.yaml` -- Clinician weight vector.
- `ops/aegis/drift_alerts.yaml` -- Prometheus alert rule pattern.
- `ops/aegis/score_dist_alerts.yaml` -- Prometheus alert rule pattern with multiple rules in one group.
- `pyproject.toml` -- Dependencies. `prometheus-client`, `duckdb`, `pydantic`, `scipy`, `numpy` already present.
- `docs/design/scoring.md` -- Design document. Must be updated by design-updater task.

### New Files

- `src/aegis/observability/query_slo.py` -- Query latency SLO monitor with Prometheus metrics, per-customer/cohort breakdown, error-budget tracking.
- `src/aegis/observability/query_slo_test.py` -- Tests for query SLO monitor.
- `src/aegis/observability/customer_quality.py` -- Per-customer task-quality tracking with DuckDB persistence and trend analysis.
- `src/aegis/observability/customer_quality_test.py` -- Tests for customer quality tracker.
- `src/aegis/observability/refresh_sla.py` -- Refresh-cadence SLA tracker with hard-gate/non-hard-gate classification and alerting.
- `src/aegis/observability/refresh_sla_test.py` -- Tests for refresh SLA tracker.
- `src/aegis/observability/weight_drift.py` -- Weight-drift time-series tracker with annotations and jump detection.
- `src/aegis/observability/weight_drift_test.py` -- Tests for weight drift tracker.
- `ops/aegis/phase3f_alerts.yaml` -- Prometheus alert rules for all four Phase 3f subsystems.

## Implementation Phases

### Phase 1: Foundation
Build the query SLO monitor and refresh SLA tracker. These are the most operationally critical (paging on breach) and have no dependency on Phase 3c (feedback loop). They follow the established Prometheus metric patterns directly.

### Phase 2: Core Implementation
Build the customer quality tracker (depends on the feedback data model from Phase 3c, but the tracker itself is standalone -- it accepts aggregate metrics directly) and the weight drift tracker (extends Phase 1d's `WeightStabilityTracker` to time-series).

### Phase 3: Integration & Polish
Update `__init__.py` exports, generate Prometheus alert rules, run full test suite, and validate all acceptance criteria.

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Query SLO monitor (Task 2.1), refresh-cadence SLA tracker (Task 2.3), Prometheus alert rules, package exports
  - Agent Type: builder
- Builder
  - Name: builder-2
  - Role: Per-customer task-quality tracker (Task 2.2), weight-drift tracker (Task 2.5)
  - Agent Type: builder
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Design Updater
  - Name: design-updater
  - Role: Updates docs/design/scoring.md with code-aligned design decisions after build completes
  - Agent Type: design-updater

## Step by Step Tasks

### 1. Build Query Latency SLO Monitor with Prometheus Metrics
- **Task ID**: query-slo-monitor
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the query latency SLO monitor that records per-request latency with customer and cohort labels, computes rolling SLO compliance, tracks error-budget consumption, and emits Prometheus metrics.

    This implements Phase 3 master plan Task 2.1.

    ## What to do

    1. Create `src/aegis/observability/query_slo.py` with the following components:

    2. **`SloTarget` frozen Pydantic model**:
       ```python
       from __future__ import annotations

       import time
       from collections import deque
       from datetime import datetime

       from prometheus_client import (
           CollectorRegistry,
           Counter,
           Gauge,
           Histogram,
           generate_latest,
       )
       from pydantic import BaseModel, ConfigDict


       class SloTarget(BaseModel):
           model_config = ConfigDict(frozen=True)

           p95_ms: float = 500.0         # <500ms p95
           p99_ms: float = 1500.0        # <1500ms p99
           success_rate: float = 0.999   # >=99.9%
           budget_window_days: int = 30  # Rolling 30-day window
       ```

    3. **`SloStatusReport` frozen Pydantic model**:
       ```python
       class SloStatusReport(BaseModel):
           model_config = ConfigDict(frozen=True)

           timestamp: datetime
           total_requests: int
           success_count: int
           failure_count: int
           p95_latency_ms: float
           p99_latency_ms: float
           success_rate: float
           p95_slo_met: bool
           p99_slo_met: bool
           success_rate_slo_met: bool
           error_budget_consumed_pct: float  # 0.0-100.0
           error_budget_remaining_pct: float
       ```

    4. **`CustomerCohortBreakdown` frozen Pydantic model**:
       ```python
       class CustomerCohortBreakdown(BaseModel):
           model_config = ConfigDict(frozen=True)

           customer_id: str
           cohort: str | None
           total_requests: int
           p95_latency_ms: float
           p99_latency_ms: float
           success_rate: float
       ```

    5. **`QuerySloMonitor` class**:
       - `__init__(self, target: SloTarget | None = None, registry: CollectorRegistry | None = None, max_window_size: int = 100_000)` -- store SLO target (default `SloTarget()`), create Prometheus registry, initialize Prometheus metrics, initialize internal tracking structures.
       - Prometheus metrics to create (follow the naming pattern from `src/aegis/observability/api_health.py` and `src/aegis/observability/freshness.py`):
         ```python
         self._latency_histogram = Histogram(
             "aegis_query_latency_seconds",
             "Query latency in seconds",
             ["customer", "cohort"],
             buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 5.0),
             registry=self._registry,
         )
         self._requests_total = Counter(
             "aegis_query_requests_total",
             "Total query requests",
             ["customer", "cohort", "status"],
             registry=self._registry,
         )
         self._p95_gauge = Gauge(
             "aegis_query_p95_latency_ms",
             "Current p95 query latency in milliseconds",
             registry=self._registry,
         )
         self._p99_gauge = Gauge(
             "aegis_query_p99_latency_ms",
             "Current p99 query latency in milliseconds",
             registry=self._registry,
         )
         self._success_rate_gauge = Gauge(
             "aegis_query_success_rate",
             "Current query success rate",
             registry=self._registry,
         )
         self._error_budget_gauge = Gauge(
             "aegis_query_error_budget_consumed_pct",
             "Percentage of error budget consumed in rolling window",
             registry=self._registry,
         )
         ```
       - Internal tracking: `self._latencies: deque[tuple[float, float, str, str | None, bool]] = deque(maxlen=max_window_size)` -- each entry is `(timestamp_epoch, latency_ms, customer_id, cohort, success)`. This deque holds a rolling window of recent requests for computing percentiles.
       - `record_request(self, customer_id: str, cohort: str | None, latency_ms: float, success: bool) -> None`:
         - Record the latency in Prometheus histogram (convert to seconds: `latency_ms / 1000.0`).
         - Increment the requests counter with status "success" or "failure".
         - Append `(time.time(), latency_ms, customer_id, cohort, success)` to `self._latencies`.
         - Update gauges by calling `self._update_gauges()`.
       - `_update_gauges(self) -> None`:
         - Compute p95 and p99 from all latency values in `self._latencies`.
         - Use sorted latencies and index-based percentile computation:
           ```python
           latencies_sorted = sorted(entry[1] for entry in self._latencies)
           n = len(latencies_sorted)
           if n == 0:
               return
           p95_idx = int(0.95 * (n - 1))
           p99_idx = int(0.99 * (n - 1))
           p95 = latencies_sorted[p95_idx]
           p99 = latencies_sorted[p99_idx]
           ```
         - Compute success rate: `success_count / total`.
         - Set gauge values.
       - `get_status_report(self) -> SloStatusReport`:
         - Compute all metrics from the rolling window.
         - Error budget: allowed failures = `(1 - target.success_rate) * total_requests`. Consumed = `actual_failures / allowed_failures * 100`. If allowed_failures == 0 and actual_failures > 0, consumed = 100.0. If total_requests == 0, consumed = 0.0.
         - Return SloStatusReport with all fields populated.
       - `get_customer_breakdown(self) -> list[CustomerCohortBreakdown]`:
         - Group entries in `self._latencies` by `(customer_id, cohort)`.
         - For each group, compute p95, p99, success_rate.
         - Return list of `CustomerCohortBreakdown`.
       - `is_budget_breached(self) -> bool`:
         - Return True if error_budget_consumed_pct >= 100.0.
       - `expose_metrics(self) -> str`:
         - Return `generate_latest(self._registry).decode("utf-8")`.

    6. Create `src/aegis/observability/query_slo_test.py` with tests:
       - `test_record_and_report_basic` -- record 100 requests with 200ms latency, all success. Verify p95 < 500, p99 < 1500, success_rate == 1.0, all SLOs met, budget consumed == 0.
       - `test_p95_breach` -- record 100 requests, 6 with 600ms latency. Verify p95_slo_met is False.
       - `test_p99_breach` -- record 100 requests, 2 with 2000ms latency. Verify p99_slo_met is False.
       - `test_success_rate_breach` -- record 1000 requests, 2 failures. Verify success_rate < 0.999, success_rate_slo_met is False.
       - `test_error_budget_tracking` -- record requests with known failure rate, verify error_budget_consumed_pct matches expected value.
       - `test_customer_cohort_breakdown` -- record requests from 2 customers with different cohorts, verify breakdown returns correct per-customer metrics.
       - `test_prometheus_metrics_exposed` -- record requests, call expose_metrics(), verify Prometheus text contains expected metric names.
       - `test_empty_window` -- call get_status_report() with no requests, verify defaults (0 requests, no breach).
       - Each test creates a fresh `QuerySloMonitor` with `registry=CollectorRegistry()` (follow the pattern from `src/aegis/observability/freshness_test.py:14`).
       - Import: `from aegis.observability.query_slo import QuerySloMonitor, SloTarget, SloStatusReport, CustomerCohortBreakdown`.
       - `from prometheus_client import CollectorRegistry`.
       - `from __future__ import annotations` at top.

    ## Files to modify
    - `src/aegis/observability/query_slo.py` -- NEW: entire module
    - `src/aegis/observability/query_slo_test.py` -- NEW: tests

    ## Code patterns to follow
    - Prometheus metric pattern from `src/aegis/observability/freshness.py` (CollectorRegistry, Gauge, Histogram, Counter, generate_latest).
    - Prometheus metric pattern from `src/aegis/observability/api_health.py` (labels, latency buckets).
    - Frozen Pydantic models with `model_config = ConfigDict(frozen=True)`.
    - `from __future__ import annotations` on every file.
    - Test pattern from `src/aegis/observability/freshness_test.py` (fresh CollectorRegistry per test).

    ## Acceptance criteria
    - `QuerySloMonitor` records per-request latency with customer and cohort labels.
    - p95 and p99 latency computed correctly from rolling window.
    - Success rate computed correctly.
    - Error budget consumption computed correctly (allowed failures = (1 - 0.999) * total).
    - `is_budget_breached()` returns True when budget consumed >= 100%.
    - Per-customer/cohort breakdown computed correctly.
    - Prometheus metrics exposed in valid format.
    - All tests pass: `cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/query_slo_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/query_slo.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/query_slo.py src/aegis/observability/query_slo_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/query_slo_test.py -x -q && uv run python -m mypy src/aegis/observability/query_slo.py --strict && uv run python -m ruff check src/aegis/observability/query_slo.py src/aegis/observability/query_slo_test.py
    ```

### 2. Build Per-Customer Task-Quality Tracker
- **Task ID**: customer-quality-tracker
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the per-customer task-quality tracker that records aggregate downstream task-quality metrics (Fleiss kappa, accept rate) per customer over time, persists in DuckDB, computes trend slopes, and exposes a JSON-serializable API response model.

    This implements Phase 3 master plan Task 2.2.

    ## What to do

    1. Create `src/aegis/observability/customer_quality.py` with the following components:

    2. **`CustomerQualitySnapshot` frozen Pydantic model**:
       ```python
       from __future__ import annotations

       import statistics
       import uuid
       from datetime import date, datetime

       import duckdb
       from pydantic import BaseModel, ConfigDict


       class CustomerQualitySnapshot(BaseModel):
           model_config = ConfigDict(frozen=True)

           customer_id: str
           snapshot_date: date
           fleiss_kappa: float          # Inter-rater agreement
           accept_rate: float           # Customer accept rate [0, 1]
           task_count: int              # Number of tasks in this snapshot period
           total_candidates_evaluated: int
       ```

    3. **`QualityTrend` frozen Pydantic model**:
       ```python
       class QualityTrend(BaseModel):
           model_config = ConfigDict(frozen=True)

           customer_id: str
           kappa_slope: float          # Linear trend slope for kappa over time
           accept_rate_slope: float    # Linear trend slope for accept rate
           data_points: int            # Number of snapshots used
           latest_kappa: float
           latest_accept_rate: float
           kappa_improving: bool       # True if slope > 0
           accept_rate_improving: bool
       ```

    4. **`QualityAlert` frozen Pydantic model**:
       ```python
       class QualityAlert(BaseModel):
           model_config = ConfigDict(frozen=True)

           alert_id: str
           customer_id: str
           alert_type: str             # "kappa_decline" or "accept_rate_decline"
           current_value: float
           previous_value: float
           threshold: float
           severity: str               # "warning" or "critical"
           message: str
       ```

    5. **`CustomerQualityReport` frozen Pydantic model** (JSON-serializable for API exposure):
       ```python
       class CustomerQualityReport(BaseModel):
           model_config = ConfigDict(frozen=True)

           customer_id: str
           generated_at: datetime
           snapshots: list[CustomerQualitySnapshot]
           trend: QualityTrend | None
           alerts: list[QualityAlert]
       ```

    6. **`CustomerQualityTracker` class**:
       - `__init__(self, db_path: str = "aegis.duckdb", kappa_decline_threshold: float = 0.1, accept_rate_decline_threshold: float = 0.05)` -- create DuckDB connection and ensure table exists:
         ```sql
         CREATE TABLE IF NOT EXISTS customer_quality_snapshots (
             customer_id TEXT NOT NULL,
             snapshot_date DATE NOT NULL,
             fleiss_kappa DOUBLE NOT NULL,
             accept_rate DOUBLE NOT NULL,
             task_count INTEGER NOT NULL,
             total_candidates_evaluated INTEGER NOT NULL,
             PRIMARY KEY (customer_id, snapshot_date)
         );
         ```
         Follow the DuckDB connection pattern from `src/aegis/observability/drift.py:67-68`: `self._conn = duckdb.connect(db_path)` then `self._conn.execute(_CREATE_TABLE)`.
       - `record_snapshot(self, snapshot: CustomerQualitySnapshot) -> None` -- upsert into DuckDB (INSERT ... ON CONFLICT DO UPDATE). Follow the upsert pattern from `src/aegis/observability/drift.py:75-82`.
       - `get_snapshots(self, customer_id: str, limit: int = 52) -> list[CustomerQualitySnapshot]` -- fetch the most recent `limit` snapshots for a customer, ordered by snapshot_date DESC. Return as list of `CustomerQualitySnapshot`.
       - `compute_trend(self, customer_id: str, min_points: int = 4) -> QualityTrend | None`:
         - Fetch all snapshots for the customer.
         - If fewer than `min_points` snapshots, return None.
         - Compute linear regression slope for kappa and accept_rate over time.
         - For slope computation, use simple least-squares: convert dates to ordinal numbers, compute slope = (n * sum(x*y) - sum(x) * sum(y)) / (n * sum(x^2) - sum(x)^2). This avoids importing scipy for a simple calculation.
         - Return `QualityTrend`.
       - `check_alerts(self, customer_id: str) -> list[QualityAlert]`:
         - Fetch the two most recent snapshots.
         - If fewer than 2 exist, return empty list.
         - If kappa dropped by more than `kappa_decline_threshold`, emit a QualityAlert with alert_type="kappa_decline".
         - If accept_rate dropped by more than `accept_rate_decline_threshold`, emit a QualityAlert with alert_type="accept_rate_decline".
         - Use `str(uuid.uuid4())` for alert_id.
         - Severity: "critical" if decline > 2x threshold, else "warning".
       - `generate_report(self, customer_id: str) -> CustomerQualityReport`:
         - Fetch snapshots, compute trend, check alerts.
         - Return `CustomerQualityReport` with `generated_at=datetime.now()`.
       - `get_all_customer_ids(self) -> list[str]`:
         - Query: `SELECT DISTINCT customer_id FROM customer_quality_snapshots ORDER BY customer_id`.
       - `get_cross_customer_summary(self) -> list[CustomerQualityReport]`:
         - Generate reports for all customers.

    7. Create `src/aegis/observability/customer_quality_test.py` with tests:
       - `test_record_and_retrieve_snapshot` -- record a snapshot, retrieve it, verify all fields match.
       - `test_upsert_snapshot` -- record same customer+date twice, verify second write wins.
       - `test_trend_computation_positive` -- record 5 snapshots with increasing kappa, verify kappa_slope > 0 and kappa_improving == True.
       - `test_trend_computation_negative` -- record 5 snapshots with decreasing accept_rate, verify accept_rate_slope < 0 and accept_rate_improving == False.
       - `test_trend_insufficient_data` -- record 2 snapshots, verify compute_trend returns None (min_points=4).
       - `test_kappa_decline_alert` -- record 2 snapshots with kappa drop > 0.1, verify alert fires.
       - `test_no_alert_stable` -- record 2 snapshots with similar kappa, verify no alert.
       - `test_critical_severity` -- record a kappa drop > 0.2 (2x threshold), verify severity is "critical".
       - `test_generate_report` -- record 5 snapshots, call generate_report, verify all fields populated.
       - `test_cross_customer_summary` -- record snapshots for 2 customers, verify get_cross_customer_summary returns 2 reports.
       - Use `tmp_path` for DuckDB: `str(tmp_path / "test.duckdb")`.
       - Import: `from aegis.observability.customer_quality import CustomerQualityTracker, CustomerQualitySnapshot, QualityTrend, QualityAlert, CustomerQualityReport`.
       - `from __future__ import annotations` at top.

    ## Files to modify
    - `src/aegis/observability/customer_quality.py` -- NEW: entire module
    - `src/aegis/observability/customer_quality_test.py` -- NEW: tests

    ## Code patterns to follow
    - DuckDB connection pattern: `self._conn = duckdb.connect(db_path)` then `self._conn.execute(CREATE_TABLE)`. See `src/aegis/observability/drift.py:67-68`.
    - DuckDB upsert pattern: `INSERT ... ON CONFLICT ... DO UPDATE SET`. See `src/aegis/observability/drift.py:75-82`.
    - Frozen Pydantic models with `model_config = ConfigDict(frozen=True)`.
    - UUID alert IDs via `str(uuid.uuid4())`. See `src/aegis/observability/drift.py:150`.
    - `from __future__ import annotations` at top of every file.
    - Test DuckDB paths via `tmp_path` fixture.

    ## Acceptance criteria
    - CustomerQualityTracker records, retrieves, and upserts customer quality snapshots.
    - Linear trend slope computed correctly over time series.
    - Quality decline alerts fire when kappa or accept rate drops beyond thresholds.
    - Critical severity assigned when decline > 2x threshold.
    - CustomerQualityReport is JSON-serializable (Pydantic v2 `.model_dump()` / `.model_dump_json()`).
    - All tests pass: `cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/customer_quality_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/customer_quality.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/customer_quality.py src/aegis/observability/customer_quality_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/customer_quality_test.py -x -q && uv run python -m mypy src/aegis/observability/customer_quality.py --strict && uv run python -m ruff check src/aegis/observability/customer_quality.py src/aegis/observability/customer_quality_test.py
    ```

### 3. Build Refresh-Cadence SLA Tracker
- **Task ID**: refresh-sla-tracker
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the refresh-cadence SLA tracker that checks per-source compliance against defined SLAs, distinguishes hard-gate from non-hard-gate sources, produces immediate alerts for hard-gate breaches and weekly summaries for non-hard-gate breaches, and includes a synthetic stuck-source test.

    This implements Phase 3 master plan Task 2.3.

    ## What to do

    1. Create `src/aegis/observability/refresh_sla.py` with the following components:

    2. **Source classification constants and imports**:
       ```python
       from __future__ import annotations

       import time
       import uuid
       from datetime import date, datetime

       from prometheus_client import CollectorRegistry, Gauge, generate_latest
       from pydantic import BaseModel, ConfigDict

       from aegis.observability.freshness import SOURCE_SLOS

       # Hard-gate sources: integrity-critical, page on-call immediately on breach.
       # Derived from IntegritySource enum in src/aegis/ingestion/event_dispatcher.py.
       HARD_GATE_SOURCES: frozenset[str] = frozenset({
           "retraction_watch",
           "ori",
           "ofac",
           "sam",
           "leie",
           "state_board_CA",
           "state_board_FL",
           "state_board_NY",
           "state_board_PA",
           "state_board_TX",
       })
       ```

    3. **`SourceSlaStatus` frozen Pydantic model**:
       ```python
       class SourceSlaStatus(BaseModel):
           model_config = ConfigDict(frozen=True)

           source: str
           sla_seconds: float
           last_success_epoch: float | None  # None if never succeeded
           age_seconds: float | None         # None if never succeeded
           is_compliant: bool
           is_hard_gate: bool
           breach_severity: str | None       # "critical" for hard-gate, "warning" for non-hard-gate, None if compliant
       ```

    4. **`SlaBreachAlert` frozen Pydantic model**:
       ```python
       class SlaBreachAlert(BaseModel):
           model_config = ConfigDict(frozen=True)

           alert_id: str
           source: str
           is_hard_gate: bool
           sla_seconds: float
           age_seconds: float
           overage_seconds: float    # How far past the SLA
           severity: str             # "critical" or "warning"
           page_oncall: bool         # True for hard-gate sources
           message: str
       ```

    5. **`WeeklySlaSummary` frozen Pydantic model**:
       ```python
       class WeeklySlaSummary(BaseModel):
           model_config = ConfigDict(frozen=True)

           summary_date: date
           total_sources: int
           compliant_count: int
           breached_count: int
           hard_gate_breaches: list[SlaBreachAlert]
           non_hard_gate_breaches: list[SlaBreachAlert]
           compliance_rate: float    # compliant / total
       ```

    6. **`RefreshSlaTracker` class**:
       - `__init__(self, registry: CollectorRegistry | None = None)` -- create Prometheus registry and metrics:
         ```python
         self._registry = registry or CollectorRegistry()
         self._sla_compliant = Gauge(
             "aegis_refresh_sla_compliant",
             "Whether the source is within its refresh SLA (1=yes, 0=no)",
             ["source", "is_hard_gate"],
             registry=self._registry,
         )
         self._sla_overage_seconds = Gauge(
             "aegis_refresh_sla_overage_seconds",
             "Seconds past the SLA threshold (0 if compliant)",
             ["source"],
             registry=self._registry,
         )
         self._hard_gate_breach = Gauge(
             "aegis_refresh_hard_gate_breach",
             "1 if a hard-gate source has breached its SLA",
             ["source"],
             registry=self._registry,
         )
         ```
       - Internal: `self._last_success_times: dict[str, float] = {}` -- maps source name to epoch of last successful ingestion.
       - `record_success(self, source: str) -> None`:
         - Store current epoch: `self._last_success_times[source] = time.time()`.
       - `record_success_at(self, source: str, epoch: float) -> None`:
         - For testing: `self._last_success_times[source] = epoch`.
       - `check_source(self, source: str) -> SourceSlaStatus`:
         - Look up SLA from `SOURCE_SLOS`. If source not in `SOURCE_SLOS`, use 24 hours default.
         - Look up last success from `self._last_success_times`. If not present, `last_success_epoch = None`, `age_seconds = None`, `is_compliant = False`.
         - If present, `age_seconds = time.time() - last_success_epoch`. `is_compliant = age_seconds <= sla_seconds`.
         - `is_hard_gate = source in HARD_GATE_SOURCES`.
         - `breach_severity = "critical" if is_hard_gate and not is_compliant else ("warning" if not is_compliant else None)`.
         - Update Prometheus gauges.
         - Return `SourceSlaStatus`.
       - `check_all_sources(self) -> list[SourceSlaStatus]`:
         - Iterate over all sources in `SOURCE_SLOS` (not just those with recorded success -- sources that have never reported success are also tracked as non-compliant).
         - Return list of SourceSlaStatus.
       - `get_breach_alerts(self) -> list[SlaBreachAlert]`:
         - Call `check_all_sources()`.
         - For each non-compliant source, create an `SlaBreachAlert`.
         - `page_oncall = is_hard_gate`.
         - Return list of alerts.
       - `get_weekly_summary(self, summary_date: date | None = None) -> WeeklySlaSummary`:
         - Call `check_all_sources()` to get current status.
         - Partition alerts into hard-gate and non-hard-gate.
         - Compute compliance_rate.
         - Return WeeklySlaSummary.
       - `expose_metrics(self) -> str`:
         - Return `generate_latest(self._registry).decode("utf-8")`.

    7. Create `src/aegis/observability/refresh_sla_test.py` with tests:
       - `test_compliant_source` -- record success for "pubmed" within its SLA, verify is_compliant == True and breach_severity is None.
       - `test_hard_gate_breach` -- set "retraction_watch" last success to 8 hours ago (SLA is 6h), verify is_compliant == False, is_hard_gate == True, breach_severity == "critical".
       - `test_non_hard_gate_breach` -- set "pubmed" last success to 30 hours ago (SLA is 24h), verify is_compliant == False, is_hard_gate == False, breach_severity == "warning".
       - `test_never_reported_source` -- do NOT record success for a source in SOURCE_SLOS, verify is_compliant == False.
       - `test_check_all_sources` -- record success for some sources, verify check_all_sources returns status for all sources in SOURCE_SLOS.
       - `test_breach_alerts_hard_gate_pages` -- create a hard-gate breach, verify page_oncall == True in the alert.
       - `test_weekly_summary` -- create a mix of compliant and breached sources, verify weekly summary has correct counts and compliance rate.
       - `test_prometheus_metrics` -- record success and check sources, verify Prometheus text contains expected metric names and labels.
       - `test_synthetic_stuck_source`:
         This is the synthetic stuck-source test from the Phase 3 master plan.
         ```python
         def test_synthetic_stuck_source() -> None:
             """Synthetic stuck-source test: verify alerting fires for a source
             that has not reported success within its SLA."""
             tracker = RefreshSlaTracker(registry=CollectorRegistry())

             # Simulate "retraction_watch" stuck: last success was 12 hours ago
             # SLA is 6 hours
             stuck_epoch = time.time() - (12 * 3600)
             tracker.record_success_at("retraction_watch", stuck_epoch)

             # All other hard-gate sources are fresh
             for source in HARD_GATE_SOURCES:
                 if source != "retraction_watch":
                     tracker.record_success(source)

             alerts = tracker.get_breach_alerts()
             hard_gate_alerts = [a for a in alerts if a.is_hard_gate and a.source == "retraction_watch"]
             assert len(hard_gate_alerts) == 1
             assert hard_gate_alerts[0].page_oncall is True
             assert hard_gate_alerts[0].severity == "critical"
             assert hard_gate_alerts[0].overage_seconds > 0
         ```
       - Use fresh `CollectorRegistry()` per test.
       - Import: `from aegis.observability.refresh_sla import RefreshSlaTracker, SourceSlaStatus, SlaBreachAlert, WeeklySlaSummary, HARD_GATE_SOURCES`.
       - `from prometheus_client import CollectorRegistry`.
       - `from __future__ import annotations` at top.

    ## Files to modify
    - `src/aegis/observability/refresh_sla.py` -- NEW: entire module
    - `src/aegis/observability/refresh_sla_test.py` -- NEW: tests

    ## Code patterns to follow
    - Prometheus metric pattern from `src/aegis/observability/freshness.py` (CollectorRegistry, Gauge, generate_latest, labels).
    - Import `SOURCE_SLOS` from `aegis.observability.freshness`.
    - Frozen Pydantic models with `model_config = ConfigDict(frozen=True)`.
    - UUID alert IDs via `str(uuid.uuid4())`.
    - `from __future__ import annotations` on every file.

    ## Acceptance criteria
    - RefreshSlaTracker correctly classifies sources as hard-gate or non-hard-gate.
    - Hard-gate SLA breaches produce critical-severity alerts with page_oncall=True.
    - Non-hard-gate breaches produce warning-severity alerts.
    - Sources that have never reported success are tracked as non-compliant.
    - Weekly summary accurately reports compliance rate.
    - Synthetic stuck-source test passes end-to-end.
    - Prometheus metrics exposed with correct labels.
    - All tests pass: `cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/refresh_sla_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/refresh_sla.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/refresh_sla.py src/aegis/observability/refresh_sla_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/refresh_sla_test.py -x -q && uv run python -m mypy src/aegis/observability/refresh_sla.py --strict && uv run python -m ruff check src/aegis/observability/refresh_sla.py src/aegis/observability/refresh_sla_test.py
    ```

### 4. Build Weight-Drift Time-Series Tracker
- **Task ID**: weight-drift-tracker
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the weight-drift tracker that stores per-refit weight snapshots in DuckDB, computes per-parameter time series across specialties, supports event annotations, detects sudden jumps, and generates drift reports.

    This implements Phase 3 master plan Task 2.5.

    ## What to do

    1. Create `src/aegis/observability/weight_drift.py` with the following components:

    2. **Imports and table definition**:
       ```python
       from __future__ import annotations

       import glob as globmod
       import uuid
       from datetime import date, datetime
       from pathlib import Path

       import duckdb
       from pydantic import BaseModel, ConfigDict

       from aegis.scoring.quality_prior import WeightVector, load_weight_vector

       _CREATE_SNAPSHOTS_TABLE = """\
       CREATE TABLE IF NOT EXISTS weight_drift_snapshots (
           specialty TEXT NOT NULL,
           version INTEGER NOT NULL,
           parameter_name TEXT NOT NULL,
           parameter_value DOUBLE NOT NULL,
           refit_date DATE NOT NULL,
           PRIMARY KEY (specialty, version, parameter_name)
       );
       """

       _CREATE_ANNOTATIONS_TABLE = """\
       CREATE TABLE IF NOT EXISTS weight_drift_annotations (
           annotation_id TEXT NOT NULL PRIMARY KEY,
           annotation_date DATE NOT NULL,
           event_description TEXT NOT NULL,
           created_at TEXT NOT NULL
       );
       """
       ```

    3. **`WeightSnapshot` frozen Pydantic model**:
       ```python
       class WeightSnapshot(BaseModel):
           model_config = ConfigDict(frozen=True)

           specialty: str
           version: int
           parameter_name: str       # e.g., "weight.f1_rcr", "exponent.alpha"
           parameter_value: float
           refit_date: date
       ```

    4. **`DriftAnnotation` frozen Pydantic model**:
       ```python
       class DriftAnnotation(BaseModel):
           model_config = ConfigDict(frozen=True)

           annotation_id: str
           annotation_date: date
           event_description: str      # e.g., "EPO patent source ingested", "Customer X pilot started"
       ```

    5. **`JumpAlert` frozen Pydantic model**:
       ```python
       class JumpAlert(BaseModel):
           model_config = ConfigDict(frozen=True)

           alert_id: str
           specialty: str
           parameter_name: str
           old_version: int
           new_version: int
           old_value: float
           new_value: float
           relative_change_pct: float
           severity: str              # "warning" or "critical"
           message: str
       ```

    6. **`ParameterTimeSeries` frozen Pydantic model**:
       ```python
       class ParameterTimeSeries(BaseModel):
           model_config = ConfigDict(frozen=True)

           specialty: str
           parameter_name: str
           versions: list[int]
           values: list[float]
           dates: list[date]
       ```

    7. **`WeightDriftReport` frozen Pydantic model**:
       ```python
       class WeightDriftReport(BaseModel):
           model_config = ConfigDict(frozen=True)

           generated_at: datetime
           specialties: list[str]
           time_series: list[ParameterTimeSeries]
           jump_alerts: list[JumpAlert]
           annotations: list[DriftAnnotation]
       ```

    8. **`WeightDriftTracker` class**:
       - `__init__(self, db_path: str = "aegis.duckdb", jump_threshold_pct: float = 25.0)` -- create DuckDB connection, execute both CREATE TABLE statements. Store threshold.
         Follow the DuckDB pattern from `src/aegis/observability/drift.py:67-68`.
       - `record_snapshot(self, snapshot: WeightSnapshot) -> None` -- upsert into weight_drift_snapshots.
       - `record_weight_vector(self, wv: WeightVector, refit_date: date) -> None`:
         - Extract all parameters from the WeightVector and record each as a snapshot.
         - For family weights: parameter_name = `f"weight.{key}"` for each key in `wv.weights`.
         - For exponents: parameter_name = `f"exponent.{key}"` for each key in `wv.exponents`.
         - Specialty from `wv.specialty`, version from `wv.version`.
       - `load_history_from_dir(self, weights_dir: str = "config/aegis/weights") -> int`:
         - Glob for all `*_v*.yaml` files in the directory.
         - Load each as a WeightVector via `load_weight_vector()`.
         - Record each using `record_weight_vector()`. Use the YAML's `created` field as refit_date if available; otherwise use the file's modified date.
         - Return the number of weight vectors loaded.
         - **IMPORTANT**: For parsing refit_date from the YAML, open the file and use `yaml.safe_load()` to extract the `created` field. If the field is a string, parse with `date.fromisoformat()`. If missing, use `date.today()`.
         - Import yaml: `import yaml  # type: ignore[import-untyped]`
       - `record_annotation(self, annotation_date: date, event_description: str) -> DriftAnnotation`:
         - Create a DriftAnnotation with `annotation_id=str(uuid.uuid4())`, insert into annotations table.
         - Return the annotation.
       - `get_annotations(self) -> list[DriftAnnotation]`:
         - Fetch all annotations ordered by annotation_date.
       - `get_time_series(self, specialty: str, parameter_name: str) -> ParameterTimeSeries | None`:
         - Query snapshots for the given specialty and parameter, ordered by version.
         - If no data, return None.
         - Return `ParameterTimeSeries` with versions, values, and dates.
       - `get_all_time_series(self, specialty: str | None = None) -> list[ParameterTimeSeries]`:
         - If specialty is None, get all specialties from the DB.
         - For each specialty, get all distinct parameter names.
         - For each (specialty, parameter), call `get_time_series()`.
         - Return list of all non-None results.
       - `detect_jumps(self, specialty: str | None = None) -> list[JumpAlert]`:
         - Get all time series (optionally filtered by specialty).
         - For each time series with >= 2 data points, compare consecutive values.
         - If relative change > `jump_threshold_pct`, emit a JumpAlert.
         - Relative change = `abs(new - old) / abs(old) * 100` (handle old == 0 by using `abs(new) > 0.01` as the threshold).
         - severity: "critical" if relative change > 2 * threshold, else "warning".
         - Use `str(uuid.uuid4())` for alert_id.
       - `generate_report(self, specialty: str | None = None) -> WeightDriftReport`:
         - Get all time series, detect jumps, get annotations.
         - Get list of specialties from the DB.
         - Return `WeightDriftReport`.

    9. Create `src/aegis/observability/weight_drift_test.py` with tests:
       - `test_record_and_retrieve_snapshot` -- record a single WeightSnapshot, query it back via get_time_series.
       - `test_record_weight_vector` -- create a WeightVector (matching the format in `config/aegis/weights/translational_v1.yaml`), record it, verify all 9 parameters (6 weights + 3 exponents) are stored. Use:
         ```python
         from aegis.scoring.quality_prior import WeightVector
         wv = WeightVector(
             version=1,
             specialty="translational",
             weights={"f1_rcr": 0.35, "f2_funding": 0.25, "f3_leadership": 0.20, "f4_apex": 0.05, "f5_translational": 0.10, "f6_lineage": 0.05},
             exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
             exponent_bounds={"alpha": [0.3, 1.2], "beta": [0.5, 1.5], "gamma": [0.1, 0.8]},
         )
         ```
       - `test_time_series_ordering` -- record 3 versions, verify time series has versions in ascending order.
       - `test_detect_jump` -- record 2 versions with alpha changing from 0.7 to 1.0 (42.8% relative change), verify a JumpAlert is detected.
       - `test_no_jump_stable` -- record 2 versions with alpha changing from 0.7 to 0.75 (7.1% relative change), verify no jump detected.
       - `test_annotation` -- record an annotation, retrieve it, verify fields.
       - `test_generate_report` -- record 3 versions with one jump, add an annotation, call generate_report, verify all fields populated.
       - `test_load_history_from_dir` -- write 2 weight YAML files to `tmp_path` (using the format from `config/aegis/weights/translational_v1.yaml`), call load_history_from_dir, verify 2 vectors loaded.
         The YAML format:
         ```yaml
         version: 1
         specialty: translational
         created: "2026-04-25"
         weights:
           f1_rcr: 0.35
           f2_funding: 0.25
           f3_leadership: 0.20
           f4_apex: 0.05
           f5_translational: 0.10
           f6_lineage: 0.05
         exponents:
           alpha: 0.7
           beta: 1.0
           gamma: 0.4
         exponent_bounds:
           alpha: [0.3, 1.2]
           beta: [0.5, 1.5]
           gamma: [0.1, 0.8]
         ```
       - `test_multi_specialty_time_series` -- record vectors for both "translational" and "drug_discovery" specialties, verify get_all_time_series returns time series for both.
       - `test_critical_jump_severity` -- record a 60% change (>2x threshold), verify severity is "critical".
       - Use `tmp_path` for DuckDB: `str(tmp_path / "test.duckdb")`.
       - Import: `from aegis.observability.weight_drift import WeightDriftTracker, WeightSnapshot, DriftAnnotation, JumpAlert, ParameterTimeSeries, WeightDriftReport`.
       - `from __future__ import annotations` at top.

    ## Files to modify
    - `src/aegis/observability/weight_drift.py` -- NEW: entire module
    - `src/aegis/observability/weight_drift_test.py` -- NEW: tests

    ## Code patterns to follow
    - DuckDB connection pattern: `self._conn = duckdb.connect(db_path)` then `self._conn.execute(CREATE_TABLE)`. See `src/aegis/observability/drift.py:67-68`.
    - DuckDB upsert pattern: `INSERT ... ON CONFLICT ... DO UPDATE SET`. See `src/aegis/observability/drift.py:75-82`.
    - Weight loading: `from aegis.scoring.quality_prior import WeightVector, load_weight_vector`. See `src/aegis/observability/weight_stability.py:10`.
    - Frozen Pydantic models with `model_config = ConfigDict(frozen=True)`.
    - UUID generation via `str(uuid.uuid4())`.
    - `from __future__ import annotations` on every file.
    - YAML loading: `import yaml; yaml.safe_load(f)` with `# type: ignore[import-untyped]`. See `src/aegis/scoring/quality_prior.py:9`.
    - Glob pattern: `sorted(Path(weights_dir).glob("*_v*.yaml"))`. See `src/aegis/observability/weight_stability.py:124-126`.

    ## Acceptance criteria
    - WeightDriftTracker stores per-refit weight snapshots with specialty, version, parameter, value, and date.
    - record_weight_vector correctly decomposes a WeightVector into individual parameter snapshots.
    - Time series returned in version-ascending order.
    - Jump detection fires when relative change > 25%, with critical severity at > 50%.
    - Annotations stored and retrieved correctly.
    - load_history_from_dir correctly loads YAML weight files and records them.
    - Multi-specialty time series work correctly.
    - WeightDriftReport JSON-serializable.
    - All tests pass: `cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/weight_drift_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/weight_drift.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/weight_drift.py src/aegis/observability/weight_drift_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/weight_drift_test.py -x -q && uv run python -m mypy src/aegis/observability/weight_drift.py --strict && uv run python -m ruff check src/aegis/observability/weight_drift.py src/aegis/observability/weight_drift_test.py
    ```

### 5. Create Prometheus Alert Rules and Update Package Exports
- **Task ID**: alerts-and-exports
- **Role**: builder
- **Depends On**: query-slo-monitor, refresh-sla-tracker
- **Assigned To**: builder-1
- **Description**: |
    Create the Prometheus alert rules YAML for all four Phase 3f subsystems and update the observability package `__init__.py` to export all new public symbols.

    ## What to do

    1. Create `ops/aegis/phase3f_alerts.yaml` following the pattern in `ops/aegis/score_dist_alerts.yaml` and `ops/aegis/drift_alerts.yaml`. The file should contain one Prometheus alert group with rules for all four subsystems:

       ```yaml
       groups:
         - name: aegis-phase3f-observability
           rules:
             # Task 2.1: Query latency SLO
             - alert: AegisQueryP95Breach
               expr: |
                 aegis_query_p95_latency_ms > 500
               for: 5m
               labels:
                 severity: critical
               annotations:
                 summary: "Query p95 latency exceeds 500ms SLO"
                 description: >-
                   Query p95 latency is {{ $value }}ms, exceeding the 500ms
                   SLO target. Check for slow queries, database load, or
                   cache misses.

             - alert: AegisQueryP99Breach
               expr: |
                 aegis_query_p99_latency_ms > 1500
               for: 5m
               labels:
                 severity: critical
               annotations:
                 summary: "Query p99 latency exceeds 1500ms SLO"
                 description: >-
                   Query p99 latency is {{ $value }}ms, exceeding the 1500ms
                   SLO target.

             - alert: AegisQuerySuccessRateLow
               expr: |
                 aegis_query_success_rate < 0.999
               for: 5m
               labels:
                 severity: critical
               annotations:
                 summary: "Query success rate below 99.9%"
                 description: >-
                   Query success rate is {{ $value }}, below the 99.9% SLO
                   target.

             - alert: AegisQueryErrorBudgetExhausted
               expr: |
                 aegis_query_error_budget_consumed_pct >= 100
               for: 1m
               labels:
                 severity: critical
               annotations:
                 summary: "Query error budget exhausted"
                 description: >-
                   The 30-day error budget for query failures has been fully
                   consumed. All query failures from this point directly
                   violate the SLO.

             # Task 2.3: Refresh-cadence SLA
             - alert: AegisHardGateSourceBreach
               expr: |
                 aegis_refresh_hard_gate_breach == 1
               for: 1m
               labels:
                 severity: critical
               annotations:
                 summary: "Hard-gate source {{ $labels.source }} has breached refresh SLA"
                 description: >-
                   Integrity-critical source {{ $labels.source }} has not
                   refreshed within its SLA. This source provides hard-gate
                   data (license actions, retractions, sanctions). Page
                   on-call immediately.

             - alert: AegisRefreshSlaOverage
               expr: |
                 aegis_refresh_sla_overage_seconds > 0
               for: 5m
               labels:
                 severity: warning
               annotations:
                 summary: "Source {{ $labels.source }} past its refresh SLA"
                 description: >-
                   Source {{ $labels.source }} is {{ $value }} seconds past
                   its refresh SLA threshold.
       ```

    2. Update `src/aegis/observability/__init__.py` to add imports and exports for all new modules. The current file imports from these modules:
       - apex_recall, api_health, audit_consistency, clinician_coverage, coverage, drift, freshness, integrity_dashboard, linkage_report, merge_accuracy, reassignment_metrics, score_dist, signal_balance, specialty_dist, weight_stability

       Add imports for the four new modules. Read the current `__init__.py` FIRST, then add:
       ```python
       from aegis.observability.customer_quality import (
           CustomerQualityReport,
           CustomerQualitySnapshot,
           CustomerQualityTracker,
           QualityAlert,
           QualityTrend,
       )
       from aegis.observability.query_slo import (
           CustomerCohortBreakdown,
           QuerySloMonitor,
           SloStatusReport,
           SloTarget,
       )
       from aegis.observability.refresh_sla import (
           RefreshSlaTracker,
           SlaBreachAlert,
           SourceSlaStatus,
           WeeklySlaSummary,
       )
       from aegis.observability.weight_drift import (
           DriftAnnotation,
           JumpAlert,
           ParameterTimeSeries,
           WeightDriftReport,
           WeightDriftTracker,
           WeightSnapshot,
       )
       ```

       Add to `__all__` list (maintain alphabetical order):
       ```python
       "CustomerCohortBreakdown",
       "CustomerQualityReport",
       "CustomerQualitySnapshot",
       "CustomerQualityTracker",
       "DriftAnnotation",
       "JumpAlert",
       "ParameterTimeSeries",
       "QualityAlert",
       "QualityTrend",
       "QuerySloMonitor",
       "RefreshSlaTracker",
       "SlaBreachAlert",
       "SloStatusReport",
       "SloTarget",
       "SourceSlaStatus",
       "WeeklySlaSummary",
       "WeightDriftReport",
       "WeightDriftTracker",
       "WeightSnapshot",
       ```

    ## Files to modify
    - `ops/aegis/phase3f_alerts.yaml` -- NEW: Prometheus alert rules
    - `src/aegis/observability/__init__.py` -- MODIFY: add new imports and exports

    ## Code patterns to follow
    - Alert YAML format from `ops/aegis/score_dist_alerts.yaml` and `ops/aegis/drift_alerts.yaml`.
    - Package exports pattern from the existing `src/aegis/observability/__init__.py` (alphabetical `__all__` list).

    ## Acceptance criteria
    - `ops/aegis/phase3f_alerts.yaml` contains 7 alert rules covering query SLO (4 rules) and refresh SLA (2 rules + 1 error-budget rule).
    - `__init__.py` imports and exports all 19 new public symbols from the 4 new modules.
    - All new symbols are importable: `from aegis.observability import QuerySloMonitor, CustomerQualityTracker, RefreshSlaTracker, WeightDriftTracker`.
    - ruff passes on `__init__.py`: `cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/__init__.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.observability import QuerySloMonitor, SloTarget, SloStatusReport, CustomerCohortBreakdown, CustomerQualityTracker, CustomerQualitySnapshot, QualityTrend, QualityAlert, CustomerQualityReport, RefreshSlaTracker, SourceSlaStatus, SlaBreachAlert, WeeklySlaSummary, WeightDriftTracker, WeightSnapshot, DriftAnnotation, JumpAlert, ParameterTimeSeries, WeightDriftReport; print('All 19 symbols imported successfully')" && uv run python -m ruff check src/aegis/observability/__init__.py && test -f ops/aegis/phase3f_alerts.yaml && echo "Alert rules file exists"
    ```

### 6. Validate All Acceptance Criteria
- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: query-slo-monitor, customer-quality-tracker, refresh-sla-tracker, weight-drift-tracker, alerts-and-exports
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the Phase 3f observability build.

    ## Validation Commands

    Run each command and verify it passes:

    1. **Query SLO monitor tests + lint**:
       ```bash
       cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/query_slo_test.py -x -q
       cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/query_slo.py --strict
       cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/query_slo.py src/aegis/observability/query_slo_test.py
       ```

    2. **Customer quality tracker tests + lint**:
       ```bash
       cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/customer_quality_test.py -x -q
       cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/customer_quality.py --strict
       cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/customer_quality.py src/aegis/observability/customer_quality_test.py
       ```

    3. **Refresh SLA tracker tests + lint**:
       ```bash
       cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/refresh_sla_test.py -x -q
       cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/refresh_sla.py --strict
       cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/refresh_sla.py src/aegis/observability/refresh_sla_test.py
       ```

    4. **Weight drift tracker tests + lint**:
       ```bash
       cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/weight_drift_test.py -x -q
       cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/weight_drift.py --strict
       cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/weight_drift.py src/aegis/observability/weight_drift_test.py
       ```

    5. **Package exports**:
       ```bash
       cd /Users/anvith/aegis && uv run python -c "from aegis.observability import QuerySloMonitor, SloTarget, SloStatusReport, CustomerCohortBreakdown, CustomerQualityTracker, CustomerQualitySnapshot, QualityTrend, QualityAlert, CustomerQualityReport, RefreshSlaTracker, SourceSlaStatus, SlaBreachAlert, WeeklySlaSummary, WeightDriftTracker, WeightSnapshot, DriftAnnotation, JumpAlert, ParameterTimeSeries, WeightDriftReport; print('All 19 symbols imported successfully')"
       ```

    6. **__init__.py lint**:
       ```bash
       cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/__init__.py
       ```

    7. **Alert rules file exists**:
       ```bash
       test -f /Users/anvith/aegis/ops/aegis/phase3f_alerts.yaml && echo "Alert rules file exists"
       ```

    8. **Full test suite (check for regressions)**:
       ```bash
       cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/ -x -q
       ```

    ## Acceptance Criteria

    Verify each of these is true:

    1. **QuerySloMonitor** records per-request latency with customer and cohort labels, computes p95/p99/success-rate, tracks error-budget consumption, exposes Prometheus metrics.
    2. **CustomerQualityTracker** records and retrieves per-customer quality snapshots, computes trend slopes, detects quality declines, generates JSON-serializable reports.
    3. **RefreshSlaTracker** classifies hard-gate vs non-hard-gate sources, pages on-call for hard-gate breaches, produces weekly summaries, passes synthetic stuck-source test.
    4. **WeightDriftTracker** stores per-refit snapshots, computes per-parameter time series, detects jumps > 25%, supports annotations, loads history from YAML files.
    5. **Prometheus alert rules** at `ops/aegis/phase3f_alerts.yaml` contain 7 rules for query SLO and refresh SLA.
    6. **Package exports** -- all 19 new symbols importable from `aegis.observability`.
    7. **All new code** passes mypy strict and ruff lint.
    8. **No regressions** -- all existing observability tests still pass.

    If any validation fails, create a fix task describing the exact failure and assign it to the appropriate builder.

### 7. Update Design Document
- **Task ID**: update-design-scoring
- **Role**: design-updater
- **Depends On**: validate-all
- **Assigned To**: design-updater
- **Description**: |
    Update the living design document for the scoring/observability domain to reflect
    what was actually built in this plan.

    ## Target Design Doc
    docs/design/scoring.md

    ## Spec File
    specs/aegis-phase3f-observability.md

    ## Scope
    Phase 3f adds four new observability modules to `src/aegis/observability/`:
    - `query_slo.py` -- Query latency SLO monitoring with Prometheus metrics, per-customer/cohort breakdown, error-budget tracking
    - `customer_quality.py` -- Per-customer task-quality tracking with DuckDB persistence and trend analysis
    - `refresh_sla.py` -- Refresh-cadence SLA tracking with hard-gate/non-hard-gate classification
    - `weight_drift.py` -- Weight-drift time-series tracking with annotations and jump detection

    Plus alert rules at `ops/aegis/phase3f_alerts.yaml`.

    ## Prior Decisions to Check
    - Phase 1d observability patterns (DuckDB-backed trackers, Prometheus metrics, frozen Pydantic models)
    - Phase 0e observability patterns (FreshnessMetrics, SOURCE_SLOS, ApiHealthMetrics)
    - Phase 2e observability patterns (specialty_dist, clinician_coverage, signal_balance, merge_accuracy, reassignment_metrics)
    - The existing mermaid architecture diagram in the design doc -- add the new modules

    ## What to Record
    Read git diff HEAD~1 HEAD, then the changed source files, then the existing
    design doc. Update Current Design to match the implementation. Append a
    Design Decision entry for each non-trivial architectural choice made in
    this build. Every claim must cite a file:line from the actual code.

    Key decisions to document:
    1. QuerySloMonitor uses in-memory deque for rolling window (not DuckDB) because Prometheus is the persistence layer for metrics and DuckDB adds unnecessary latency to the hot path.
    2. CustomerQualityTracker uses DuckDB because customer quality trends are not time-critical and benefit from SQL-based querying.
    3. RefreshSlaTracker imports SOURCE_SLOS from freshness.py rather than duplicating SLA definitions -- single source of truth.
    4. HARD_GATE_SOURCES is a frozenset constant derived from the IntegritySource enum, not imported directly, to avoid coupling the observability layer to the ingestion layer.
    5. WeightDriftTracker extends the WeightStabilityTracker pattern from Phase 1d to longitudinal time-series, reusing the same 25% jump threshold.

## Acceptance Criteria

All of the following must be true for this plan to be considered complete:

1. `src/aegis/observability/query_slo.py` exists with `QuerySloMonitor` that records latency with customer/cohort labels, computes p95/p99/success-rate from rolling window, tracks error-budget consumption, and exposes Prometheus metrics.
2. `src/aegis/observability/customer_quality.py` exists with `CustomerQualityTracker` that persists per-customer quality snapshots in DuckDB, computes trend slopes, detects declines, and generates JSON-serializable `CustomerQualityReport`.
3. `src/aegis/observability/refresh_sla.py` exists with `RefreshSlaTracker` that classifies hard-gate vs non-hard-gate sources, produces critical alerts for hard-gate breaches, exposes Prometheus metrics, and passes a synthetic stuck-source test.
4. `src/aegis/observability/weight_drift.py` exists with `WeightDriftTracker` that stores per-refit weight snapshots in DuckDB, computes per-parameter time series across specialties, supports event annotations, and detects sudden jumps.
5. `ops/aegis/phase3f_alerts.yaml` contains 7 Prometheus alert rules for query SLO (4 rules) and refresh SLA (2 rules + 1 budget rule).
6. `src/aegis/observability/__init__.py` exports all 19 new public symbols.
7. All new modules pass `uv run python -m mypy --strict` with zero errors.
8. All new modules pass `uv run python -m ruff check` with zero violations.
9. All new test files pass `uv run python -m pytest -x -q` with zero failures.
10. All existing observability tests continue to pass (no regressions).
11. The synthetic stuck-source test in `refresh_sla_test.py` demonstrates that a hard-gate source stuck beyond SLA triggers a critical alert with `page_oncall=True`.

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# Individual module tests
cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/query_slo_test.py -x -q
cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/customer_quality_test.py -x -q
cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/refresh_sla_test.py -x -q
cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/weight_drift_test.py -x -q

# mypy strict on all new modules
cd /Users/anvith/aegis && uv run python -m mypy src/aegis/observability/query_slo.py src/aegis/observability/customer_quality.py src/aegis/observability/refresh_sla.py src/aegis/observability/weight_drift.py --strict

# ruff lint on all new files
cd /Users/anvith/aegis && uv run python -m ruff check src/aegis/observability/query_slo.py src/aegis/observability/query_slo_test.py src/aegis/observability/customer_quality.py src/aegis/observability/customer_quality_test.py src/aegis/observability/refresh_sla.py src/aegis/observability/refresh_sla_test.py src/aegis/observability/weight_drift.py src/aegis/observability/weight_drift_test.py src/aegis/observability/__init__.py

# Package exports
cd /Users/anvith/aegis && uv run python -c "from aegis.observability import QuerySloMonitor, SloTarget, SloStatusReport, CustomerCohortBreakdown, CustomerQualityTracker, CustomerQualitySnapshot, QualityTrend, QualityAlert, CustomerQualityReport, RefreshSlaTracker, SourceSlaStatus, SlaBreachAlert, WeeklySlaSummary, WeightDriftTracker, WeightSnapshot, DriftAnnotation, JumpAlert, ParameterTimeSeries, WeightDriftReport; print('All 19 symbols imported successfully')"

# Alert rules file
test -f /Users/anvith/aegis/ops/aegis/phase3f_alerts.yaml && echo "Alert rules file exists"

# Full observability module regression test
cd /Users/anvith/aegis && uv run python -m pytest src/aegis/observability/ -x -q
```

## Notes

- No new dependencies required. All needed libraries (`prometheus-client`, `duckdb`, `pydantic`, `scipy`, `numpy`, `pyyaml`) are already in `pyproject.toml`.
- The `CustomerQualityTracker` is designed to be called by the feedback API endpoint (Phase 3c Task 1.6) -- but Phase 3c does not need to be built first. The tracker accepts `CustomerQualitySnapshot` objects directly and does not depend on the feedback endpoint existing.
- The `WeightDriftTracker` can load history from existing YAML files on initialization, so it provides immediate value even before the steady-state refit loop (Phase 3c Task 1.7) is running.
- The `RefreshSlaTracker` reads `SOURCE_SLOS` from `freshness.py` -- any new sources added to that dict are automatically tracked. The `HARD_GATE_SOURCES` frozenset must be updated manually when new integrity sources are added.
- All four modules follow the Phase 1d/2e observability pattern: frozen Pydantic models, DuckDB or Prometheus persistence, alert generation, and comprehensive unit tests. This consistency is deliberate.
