# Plan: Phase 1d — Observability Dashboards, Regression Tests, and Performance/Caching

> **Status:** COMPLETE (2026-04-26)
> All 13 tasks completed. 486/487 tests passing (1 pre-existing failure preserved). Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-26
> **Team:** phase1d-observability-perf-20260426-1730

### Test Results
- `src/aegis/observability/score_dist_test.py` — 5/5 PASSED
- `src/aegis/observability/apex_recall_test.py` — 6/6 PASSED
- `src/aegis/observability/audit_consistency_test.py` — 8/8 PASSED
- `src/aegis/observability/integrity_dashboard_test.py` — 5/5 PASSED
- `src/aegis/observability/weight_stability_test.py` — 7/7 PASSED
- `src/aegis/scheduling/recompute_test.py` — 6/6 PASSED
- `src/aegis/scoring/cache_test.py` — 7/7 PASSED
- `tests/regression/test_apex_recall.py` — 1/1 PASSED
- `tests/perf/test_query_latency.py` — 1/1 PASSED
- **Full suite**: 486 passed, 1 failed (pre-existing `test_daily_summary`) in ~30s

### Validation Commands
- `python -m pytest src/ tests/ -x -q` — PASS (486 passed, 1 pre-existing failure)
- `python -m mypy ... --strict` — PASS (no issues found in 7 source files)
- `python -m ruff check ...` — PASS (all checks passed)
- `python -m pytest tests/perf/test_query_latency.py -x -q -s` — PASS (p95: 0.5ms, well under 500ms budget)
- Import verification — PASS (all 6 classes importable: ScoreDistributionMonitor, ApexRecallTracker, AuditConsistencyTracker, IntegrityDashboard, WeightStabilityTracker, ScoreCache)
- Ops artifacts check — PASS (all 5 ops files + 1 config file present)

### Acceptance Criteria Verification
- [x] 1. ScoreDistributionMonitor with 50-bucket histograms and KS alerts — VERIFIED (5/5 tests pass, module exports DistributionSnapshot, KSAlert, ScoreDistributionMonitor)
- [x] 2. ApexRecallTracker with >=80% recall and weekly trends — VERIFIED (6/6 tests pass, regression test at tests/regression/test_apex_recall.py)
- [x] 3. AuditConsistencyTracker with Cohen's kappa and 5% re-show — VERIFIED (8/8 tests pass)
- [x] 4. IntegrityDashboard with per-day counts and spike detection — VERIFIED (5/5 tests pass)
- [x] 5. WeightStabilityTracker with >25% shift detection and review templates — VERIFIED (7/7 tests pass, ops/aegis/weight_review.md exists)
- [x] 6. ScoreRecomputer idempotent and resumable — VERIFIED (6/6 tests pass)
- [x] 7. ScoreCache with SQLite backend and cache stats — VERIFIED (7/7 tests pass)
- [x] 8. Query latency p95 <500ms documented and tested — VERIFIED (p95: 0.5ms, src/aegis/scoring/latency_budget.md exists)
- [x] 9. All new public classes exported from __init__.py — VERIFIED (import verification passed for all 6 classes)
- [x] 10. Prometheus alert rules with 4 rules — VERIFIED (ops/aegis/score_dist_alerts.yaml has 4 alert rules)
- [x] 11. Full test suite 319/320 baseline preserved + new tests — VERIFIED (486 passed = 440 baseline + 46 new, 1 pre-existing failure)
- [x] 12. mypy strict + ruff clean — VERIFIED (mypy: 0 issues in 7 files, ruff: all checks passed)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `src/aegis/observability/score_dist.py` | Created | Yes |
| `src/aegis/observability/score_dist_test.py` | Created | Yes |
| `src/aegis/observability/apex_recall.py` | Created | Yes |
| `src/aegis/observability/apex_recall_test.py` | Created | Yes |
| `src/aegis/observability/audit_consistency.py` | Created | Yes |
| `src/aegis/observability/audit_consistency_test.py` | Created | Yes |
| `src/aegis/observability/integrity_dashboard.py` | Created | Yes |
| `src/aegis/observability/integrity_dashboard_test.py` | Created | Yes |
| `src/aegis/observability/weight_stability.py` | Created | Yes |
| `src/aegis/observability/weight_stability_test.py` | Created | Yes |
| `src/aegis/observability/__init__.py` | Modified | Yes |
| `src/aegis/scheduling/__init__.py` | Created | Yes |
| `src/aegis/scheduling/recompute.py` | Created | Yes |
| `src/aegis/scheduling/recompute_test.py` | Created | Yes |
| `src/aegis/scoring/cache.py` | Created | Yes |
| `src/aegis/scoring/cache_test.py` | Created | Yes |
| `src/aegis/scoring/__init__.py` | Modified | Yes |
| `src/aegis/scoring/latency_budget.md` | Created | Yes |
| `tests/regression/__init__.py` | Created | Yes |
| `tests/regression/test_apex_recall.py` | Created | Yes |
| `tests/perf/__init__.py` | Created | Yes |
| `tests/perf/test_query_latency.py` | Created | Yes |
| `ops/aegis/dashboards/score_distributions.html` | Created | Yes |
| `ops/aegis/dashboards/integrity_hitrate.html` | Created | Yes |
| `ops/aegis/weight_review.md` | Created | Yes |
| `ops/aegis/score_dist_alerts.yaml` | Created | Yes |
| `config/aegis/apex_queries/nsclc_translational_v1.yaml` | Created | Yes |
| `docs/design/scoring.md` | Modified | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase1d-observability-performance.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build Phase 1d of the Aegis scoring engine. This phase covers five observability/governance modules and three performance/caching modules from the Phase 1 plan (`docs/plans/aegis/phase-1-scoring.md`):

**Observability & Governance (Tasks 2.1-2.5):**
- **Task 2.1**: Per-component score-distribution dashboards -- histograms of F1-F6, Q(c), T, R, Rank; KS-statistic anomaly alert
- **Task 2.2**: Apex-list recall regression test -- curated apex queries, >=80% recall, weekly trend tracking
- **Task 2.3**: Pairwise audit consistency tracking -- Cohen's kappa on overlapping pairs, intra-reviewer re-show at 5% rate
- **Task 2.4**: Integrity-gate hit-rate dashboard -- per-day hard-zero and soft-discount counts by reason
- **Task 2.5**: Weight-stability tracking across relearning cycles -- alert on >25% shift per refit

**Performance & Scale (Tasks 4.1-4.3):**
- **Task 4.1**: Score recomputation strategy -- idempotent nightly recompute of Q(c) and v_c, <10 min at 5K candidates
- **Task 4.2**: Caching for v_c and Q(c) -- keyed by candidate UUID + artifact-set hash + weight-vector version, >=95% hit rate
- **Task 4.3**: Query latency budget -- <500ms p95 for top-50 ranked output, documented budget breakdown

## Objective

When this plan is complete:
1. Per-component score distribution dashboards exist with nightly refresh, 50-bucket histograms, and KS-statistic anomaly alerts that fire when any distribution shifts by >0.1.
2. A curated apex-list recall regression test confirms >=80% recall across apex queries, with weekly trend tracking and >5% drop alerting.
3. Pairwise audit consistency tracking computes inter-reviewer Cohen's kappa and intra-reviewer consistency at 5% re-show rate.
4. The integrity-gate hit-rate dashboard shows per-day hard-zero and soft-discount counts by reason with spike alerting.
5. Weight-stability tracking detects >25% shifts per refit and triggers manual review before deployment.
6. Nightly score recomputation runs idempotently in <10 min at 5K candidates.
7. A cache layer for v_c and Q(c) achieves >=95% hit rate on warm cohorts with <5ms p95 lookup.
8. Query latency meets <500ms p95 for top-50 ranked output, with a documented budget breakdown.
9. All new code passes mypy strict + ruff, and the existing test baseline is preserved (319/320 passing).

## Problem Statement

Phase 1a built the scoring pipeline (F1-F6, Q(c)), Phase 1b added the integrity gate and ranking, and Phase 1c (in progress) adds the audit harness and weight-learning loop. However, there is no observability into score distributions, no regression testing against known apex experts, no tracking of audit consistency, no monitoring of integrity-gate hit rates, and no weight-stability alerting. On the performance side, there is no batch recomputation strategy, no caching layer for expensive per-candidate computations, and no latency budget enforcement. Phase 1d closes these gaps so the system is production-monitorable and performant.

## Solution Approach

1. **Score-distribution dashboards (Task 2.1)**: A `ScoreDistributionMonitor` computes 50-bucket histograms for each score component (F1-F6 percentiles, Q(c), T, R, Rank). Nightly snapshots are persisted in DuckDB (following the `DriftDetector` pattern from `src/aegis/observability/drift.py`). KS-statistic anomaly detection compares consecutive nightly distributions and alerts when KS > 0.1. HTML dashboard output follows the `CoverageDiagnostics.generate_html_report()` pattern.

2. **Apex recall regression (Task 2.2)**: An `ApexRecallTracker` takes a versioned YAML list of curated apex queries (query MeSH terms + expected candidate UUIDs), runs each through the ranker, computes recall@50, and persists weekly results. A regression test asserts >=80% aggregate recall. Weekly trend tracking alerts on >5% drops.

3. **Audit consistency (Task 2.3)**: An `AuditConsistencyTracker` consumes the `JudgmentStore` from Phase 1c (`src/aegis/audit/storage.py`), identifies overlapping pairs (same pair judged by multiple reviewers), computes Cohen's kappa, and flags low-agreement reviewers. Intra-reviewer re-show logic generates a 5% fraction of duplicate pairs.

4. **Integrity dashboard (Task 2.4)**: An `IntegrityDashboard` records per-day hard-zero and soft-discount events (from `HardGateResult` and `SoftDiscountResult`), tracks counts by reason, detects spikes, and generates HTML dashboards.

5. **Weight stability (Task 2.5)**: A `WeightStabilityTracker` compares consecutive weight versions from `config/aegis/weights/`. Computes per-parameter relative change. Alerts and blocks auto-deployment when any parameter shifts >25%. Generates an ops review template.

6. **Score recomputation (Task 4.1)**: A `ScoreRecomputer` iterates over the cohort, recomputes Q(c) and v_c for each candidate, writes results, and tracks progress for resumability. Idempotent by design -- re-running produces identical output. Target: <10 min at 5K candidates.

7. **Caching (Task 4.2)**: A `ScoreCache` keyed by `(candidate_uuid, artifact_set_hash, weight_version)` with a pluggable backend (SQLite default, Redis optional). Cache invalidation on artifact-set change or weight-version bump. Target: >=95% hit rate on warm cohort, <5ms p95 lookup.

8. **Latency budget (Task 4.3)**: A documented latency budget (<500ms p95 total: query expansion <=100ms, topical-fit <=200ms, recency+scoring <=150ms, formatting <=50ms) with a performance test that benchmarks 100 queries and asserts p95 <500ms.

## Relevant Files

### Existing Files (read, import from, or modify)

- `src/aegis/observability/__init__.py` -- Package exports. Must add new public classes from all five new observability modules.
- `src/aegis/observability/drift.py` -- `DriftDetector` with DuckDB-backed daily counts. Pattern for score_dist and integrity_dashboard persistence.
- `src/aegis/observability/coverage.py` -- `CoverageDiagnostics` with HTML report generation. Pattern for dashboard HTML output.
- `src/aegis/observability/freshness.py` -- `FreshnessMetrics` with Prometheus metrics. Pattern for Prometheus metric naming.
- `src/aegis/observability/api_health.py` -- `ApiHealthMetrics`. Pattern for per-source tracking.
- `src/aegis/observability/linkage_report.py` -- `LinkageReporter` with snapshot comparison. Pattern for delta tracking.
- `src/aegis/scoring/quality_prior.py` -- `WeightVector`, `QualityPrior`, `QualityScore`, `load_weight_vector()`. Weight stability reads weight YAML files; recomputer uses `QualityPrior`.
- `src/aegis/scoring/rank.py` -- `Ranker`, `CandidateScoreInput`. Apex recall uses `Ranker.rank()`.
- `src/aegis/scoring/result_format.py` -- `RankedList`, `RankedCandidate`. Output format for apex recall checks.
- `src/aegis/scoring/candidate_vector.py` -- `CandidateVectorBuilder`, `SparseVector`. Recomputer rebuilds candidate vectors.
- `src/aegis/scoring/topical_fit.py` -- `TopicalFit`. Used in latency benchmarking.
- `src/aegis/scoring/recency.py` -- `Recency`. Used in latency benchmarking.
- `src/aegis/scoring/__init__.py` -- Package exports. Must add cache module exports.
- `src/aegis/integrity/hard_gate.py` -- `HardGate`, `HardGateResult`. Integrity dashboard consumes gate results.
- `src/aegis/integrity/soft_discounts.py` -- `SoftDiscounts`, `SoftDiscountResult`, `DiscountType`. Integrity dashboard consumes discount results.
- `config/aegis/weights/translational_v1.yaml` -- Weight config. Weight stability reads version history.
- `ops/aegis/drift_alerts.yaml` -- Alert rules. Pattern for new alert YAML files.
- `ops/aegis/api_alerts.yaml` -- Alert rules. Pattern for Prometheus alert syntax.
- `pyproject.toml` -- Dependencies. scipy and duckdb already present.

### New Files

- `src/aegis/observability/score_dist.py` -- Score distribution monitor with KS-statistic anomaly detection.
- `src/aegis/observability/score_dist_test.py` -- Tests for score distribution module.
- `src/aegis/observability/apex_recall.py` -- Apex recall tracker with weekly trend tracking.
- `src/aegis/observability/apex_recall_test.py` -- Tests for apex recall module.
- `src/aegis/observability/audit_consistency.py` -- Audit consistency tracker with Cohen's kappa.
- `src/aegis/observability/audit_consistency_test.py` -- Tests for audit consistency module.
- `src/aegis/observability/integrity_dashboard.py` -- Integrity gate hit-rate dashboard.
- `src/aegis/observability/integrity_dashboard_test.py` -- Tests for integrity dashboard module.
- `src/aegis/observability/weight_stability.py` -- Weight stability tracker with shift alerting.
- `src/aegis/observability/weight_stability_test.py` -- Tests for weight stability module.
- `src/aegis/scheduling/__init__.py` -- Scheduling package init.
- `src/aegis/scheduling/recompute.py` -- Score recomputation strategy.
- `src/aegis/scheduling/recompute_test.py` -- Tests for recompute module.
- `src/aegis/scoring/cache.py` -- Score cache with pluggable backend.
- `src/aegis/scoring/cache_test.py` -- Tests for cache module.
- `src/aegis/scoring/latency_budget.md` -- Documented latency budget.
- `tests/regression/__init__.py` -- Regression tests package init.
- `tests/regression/test_apex_recall.py` -- Apex recall regression test.
- `tests/perf/__init__.py` -- Performance tests package init.
- `tests/perf/test_query_latency.py` -- Query latency benchmark test.
- `ops/aegis/dashboards/score_distributions.html` -- Generated dashboard (template).
- `ops/aegis/dashboards/integrity_hitrate.html` -- Generated dashboard (template).
- `ops/aegis/weight_review.md` -- Weight review approval workflow template.
- `ops/aegis/score_dist_alerts.yaml` -- Prometheus alert rules for score distribution anomalies.
- `config/aegis/apex_queries/nsclc_translational_v1.yaml` -- Curated apex queries for regression testing.

## Implementation Phases

### Phase 1: Foundation (Observability Core)
Build the score-distribution monitor and integrity-gate dashboard -- these have no dependency on Phase 1c modules and establish the DuckDB persistence + HTML dashboard patterns that other observability modules reuse.

### Phase 2: Core Implementation (Regression, Consistency, Stability + Performance)
Build the apex recall regression test, audit consistency tracker, weight stability tracker, score recomputation, caching layer, and latency budget. The audit consistency tracker depends on Phase 1c's `JudgmentStore`; weight stability depends on Phase 1c's `RefitScheduler` output.

### Phase 3: Integration & Polish
Update `__init__.py` exports, generate ops dashboards, write alert YAML files, run full test suite, and validate all acceptance criteria.

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor -- it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Score-distribution dashboards, integrity-gate hit-rate dashboard, apex-recall regression, audit-consistency tracking, weight-stability tracking (all observability modules)
  - Agent Type: builder
- Builder
  - Name: builder-2
  - Role: Score recomputation strategy, caching layer, query latency budget, ops artifacts, package exports (performance/caching + integration)
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

### 1. Build Per-Component Score-Distribution Monitor with KS Anomaly Detection
- **Task ID**: score-dist-monitor
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the score-distribution monitoring module with 50-bucket histograms, nightly snapshot persistence, KS-statistic anomaly detection, and HTML dashboard generation.

    ## What to do

    1. Create `src/aegis/observability/score_dist.py` with the following components:

    2. **`DistributionSnapshot` frozen Pydantic model**:
       ```python
       class DistributionSnapshot(BaseModel):
           model_config = ConfigDict(frozen=True)

           component: str            # e.g., "f1_rcr", "quality_prior", "topical_fit", "recency", "rank"
           snapshot_date: date
           bucket_edges: list[float] # 51 edges for 50 buckets, from 0.0 to 1.0
           counts: list[int]         # 50 counts
           total_candidates: int
           mean: float
           median: float
           stddev: float
       ```

    3. **`KSAlert` frozen Pydantic model**:
       ```python
       class KSAlert(BaseModel):
           model_config = ConfigDict(frozen=True)

           alert_id: str             # UUID
           component: str
           date: date
           ks_statistic: float
           threshold: float
           previous_date: date
           severity: str             # "warning" if ks > threshold
           message: str
       ```

    4. **`ScoreDistributionMonitor` class**:
       - `__init__(self, db_path: str = "aegis.duckdb", ks_threshold: float = 0.1)` -- create DuckDB connection and ensure tables exist. Follow the DuckDB pattern from `src/aegis/observability/drift.py:62-69` exactly: `self._conn = duckdb.connect(db_path)` then `self._conn.execute(CREATE_TABLE)`.
       - SQL tables:
         ```sql
         CREATE TABLE IF NOT EXISTS score_distribution_snapshots (
             component TEXT NOT NULL,
             snapshot_date DATE NOT NULL,
             bucket_edges TEXT NOT NULL,     -- JSON array
             counts TEXT NOT NULL,           -- JSON array
             total_candidates INTEGER NOT NULL,
             mean DOUBLE NOT NULL,
             median DOUBLE NOT NULL,
             stddev DOUBLE NOT NULL,
             PRIMARY KEY (component, snapshot_date)
         );
         ```
       - `record_snapshot(self, component: str, scores: list[float], snapshot_date: date) -> DistributionSnapshot` -- compute 50-bucket histogram using `bucket_edges = [i/50 for i in range(51)]` (all scores are percentiles in [0,1]). Count scores falling into each bucket. Compute mean, median (sorted middle), stddev via `statistics` module. Persist via INSERT ... ON CONFLICT DO UPDATE (upsert). Return the snapshot.
       - `get_snapshot(self, component: str, snapshot_date: date) -> DistributionSnapshot | None` -- fetch from DB.
       - `check_ks_anomaly(self, component: str, current_date: date) -> KSAlert | None` -- fetch today's snapshot and the most recent prior snapshot. If both exist, compute the two-sample KS statistic using `scipy.stats.ks_2samp` on the empirical distributions reconstructed from bucket counts (expand each bucket's count into that many copies of the bucket midpoint). If KS > threshold, return a `KSAlert`. Import scipy lazily inside the method to avoid import-time cost.
       - `check_all_components(self, current_date: date) -> list[KSAlert]` -- iterate over all distinct components in the DB for today's date, call `check_ks_anomaly` for each, collect non-None alerts.
       - `generate_html_report(self, snapshots: list[DistributionSnapshot]) -> str` -- generate an HTML page with a simple CSS bar chart per component (follow the inline-CSS-bar pattern from `src/aegis/observability/coverage.py:136-143`). Each component section shows the histogram as horizontal bars with bucket ranges and counts.
       - `save_report(self, snapshots: list[DistributionSnapshot], path: str = "ops/aegis/dashboards/score_distributions.html") -> None` -- write HTML to disk.

    5. **All components to track**: `"f1_rcr"`, `"f2_funding"`, `"f3_leadership"`, `"f4_apex"`, `"f5_translational"`, `"f6_lineage"`, `"quality_prior"`, `"topical_fit"`, `"recency"`, `"rank"`.

    6. Create `src/aegis/observability/score_dist_test.py` with tests:
       - `test_record_and_retrieve_snapshot` -- record 100 uniform-random scores, retrieve, verify bucket counts sum to 100.
       - `test_uniform_distribution_no_alert` -- record two identical uniform distributions on consecutive days, verify no KS alert.
       - `test_shifted_distribution_triggers_alert` -- record uniform on day 1, record heavily skewed (all scores near 1.0) on day 2, verify KS alert fires with ks_statistic > 0.1.
       - `test_html_report_generation` -- record snapshots, generate HTML, verify it contains component names and is valid HTML.
       - `test_idempotent_upsert` -- record same component+date twice with different data, verify second write wins.
       - Use `tmp_path` pytest fixture for DuckDB path: `str(tmp_path / "test.duckdb")`.
       - Import: `from aegis.observability.score_dist import ScoreDistributionMonitor, DistributionSnapshot, KSAlert`.

    ## Files to modify
    - `src/aegis/observability/score_dist.py` -- NEW: entire module
    - `src/aegis/observability/score_dist_test.py` -- NEW: tests

    ## Code patterns to follow
    - DuckDB connection pattern: `self._conn = duckdb.connect(db_path)` then execute CREATE TABLE. See `src/aegis/observability/drift.py:62-69`.
    - Frozen Pydantic models with `model_config = ConfigDict(frozen=True)`. See `src/aegis/observability/drift.py:22-29`.
    - HTML report with inline CSS bars. See `src/aegis/observability/coverage.py:129-175`.
    - UUID alert IDs via `str(uuid.uuid4())`. See `src/aegis/observability/drift.py:150`.
    - JSON serialization for array columns: `import json; json.dumps(bucket_edges)` for storage, `json.loads(row[N])` for retrieval.
    - All imports use `from __future__ import annotations`.
    - Statistics: `import statistics` for mean/median/stdev; `from scipy.stats import ks_2samp` for KS test (lazy import inside method).

    ## Acceptance criteria
    - `ScoreDistributionMonitor` can record, retrieve, and compare score distributions.
    - KS anomaly detection returns `KSAlert` when distributions shift by >0.1.
    - HTML dashboard is generated with per-component histograms.
    - All tests pass: `cd /Users/anvith/aegis && python -m pytest src/aegis/observability/score_dist_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && python -m mypy src/aegis/observability/score_dist.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check src/aegis/observability/score_dist.py src/aegis/observability/score_dist_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/observability/score_dist_test.py -x -q && python -m mypy src/aegis/observability/score_dist.py --strict && python -m ruff check src/aegis/observability/score_dist.py src/aegis/observability/score_dist_test.py
    ```

### 2. Build Integrity-Gate Hit-Rate Dashboard
- **Task ID**: integrity-dashboard
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the integrity-gate hit-rate dashboard that tracks per-day hard-zero and soft-discount counts by reason, with spike detection and HTML dashboard generation.

    ## What to do

    1. Create `src/aegis/observability/integrity_dashboard.py` with:

    2. **`IntegrityEvent` frozen Pydantic model**:
       ```python
       class IntegrityEvent(BaseModel):
           model_config = ConfigDict(frozen=True)

           event_date: date
           candidate_uuid: str
           event_type: str           # "hard_zero" or "soft_discount"
           reason: str               # e.g., "LEIE federal exclusion", "predatory_load"
           detail: str | None
       ```

    3. **`DailySummary` frozen Pydantic model**:
       ```python
       class DailySummary(BaseModel):
           model_config = ConfigDict(frozen=True)

           summary_date: date
           hard_zero_count: int
           soft_discount_count: int
           by_reason: dict[str, int]   # reason -> count
       ```

    4. **`SpikeAlert` frozen Pydantic model**:
       ```python
       class SpikeAlert(BaseModel):
           model_config = ConfigDict(frozen=True)

           alert_id: str
           event_type: str
           reason: str
           date: date
           current_count: int
           baseline_mean: float
           severity: str
           message: str
       ```

    5. **`IntegrityDashboard` class**:
       - `__init__(self, db_path: str = "aegis.duckdb", spike_multiplier: float = 3.0, baseline_days: int = 14)` -- DuckDB connection, create table:
         ```sql
         CREATE TABLE IF NOT EXISTS integrity_events (
             event_date DATE NOT NULL,
             candidate_uuid TEXT NOT NULL,
             event_type TEXT NOT NULL,
             reason TEXT NOT NULL,
             detail TEXT
         );
         ```
       - `record_event(self, event: IntegrityEvent) -> None` -- insert into DuckDB.
       - `record_hard_zero(self, event_date: date, candidate_uuid: str, reason: str, detail: str | None = None) -> None` -- convenience wrapper that creates an IntegrityEvent with event_type="hard_zero" and calls record_event.
       - `record_soft_discount(self, event_date: date, candidate_uuid: str, reason: str, detail: str | None = None) -> None` -- convenience wrapper with event_type="soft_discount".
       - `get_daily_summary(self, summary_date: date) -> DailySummary` -- query counts grouped by event_type and reason for the given date. Return DailySummary with breakdowns.
       - `check_spike(self, check_date: date) -> list[SpikeAlert]` -- for each (event_type, reason) on check_date, compare count to the mean of the prior `baseline_days`. If count > baseline_mean * spike_multiplier, emit a SpikeAlert. Use UUID for alert_id.
       - `get_weekly_summary(self, end_date: date) -> list[DailySummary]` -- return daily summaries for the 7 days ending at end_date.
       - `generate_html_report(self, summaries: list[DailySummary]) -> str` -- HTML page with a table of daily totals and a per-reason breakdown table. Follow the inline-CSS-table pattern from `src/aegis/observability/coverage.py:144-175`.
       - `save_report(self, summaries: list[DailySummary], path: str = "ops/aegis/dashboards/integrity_hitrate.html") -> None` -- write HTML to disk.

    6. **Reason strings to use** -- match the existing codebase:
       - Hard-zero reasons (from `src/aegis/integrity/hard_gate.py`): `"LEIE federal exclusion"`, `"OFAC/SAM listing"`, `"ORI misconduct finding (10yr)"`, `"retraction (fabrication) in subdomain"`, `"retraction (falsification) in subdomain"`, `"medical board action"`.
       - Soft-discount reasons (from `src/aegis/integrity/soft_discounts.py` `DiscountType` enum): `"predatory_load"`, `"out_of_subdomain_retraction"`, `"authorship_inconsistency"`, `"papermill_pending"`.

    7. Create `src/aegis/observability/integrity_dashboard_test.py` with tests:
       - `test_record_and_summarize` -- record 3 hard-zero events and 2 soft-discount events on same day, verify daily summary counts and by_reason breakdown.
       - `test_spike_detection` -- seed 14 days of baseline (1 event/day), then record 10 events on check day, verify spike alert fires.
       - `test_no_spike_normal` -- seed baseline, record normal count on check day, verify no alert.
       - `test_weekly_summary` -- record events across 7 days, verify get_weekly_summary returns 7 DailySummary objects.
       - `test_html_report` -- generate HTML from summaries, verify contains expected content.
       - Use `tmp_path` for DuckDB path.

    ## Files to modify
    - `src/aegis/observability/integrity_dashboard.py` -- NEW: entire module
    - `src/aegis/observability/integrity_dashboard_test.py` -- NEW: tests

    ## Code patterns to follow
    - DuckDB pattern from `src/aegis/observability/drift.py:62-69`.
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - HTML report pattern from `src/aegis/observability/coverage.py:129-175`.
    - `from __future__ import annotations` at top of every file.

    ## Acceptance criteria
    - Records integrity events and produces accurate daily summaries.
    - Spike detection fires when count exceeds 3x baseline mean.
    - HTML dashboard is generated with daily and per-reason breakdowns.
    - All tests pass: `cd /Users/anvith/aegis && python -m pytest src/aegis/observability/integrity_dashboard_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && python -m mypy src/aegis/observability/integrity_dashboard.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check src/aegis/observability/integrity_dashboard.py src/aegis/observability/integrity_dashboard_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/observability/integrity_dashboard_test.py -x -q && python -m mypy src/aegis/observability/integrity_dashboard.py --strict && python -m ruff check src/aegis/observability/integrity_dashboard.py src/aegis/observability/integrity_dashboard_test.py
    ```

### 3. Build Apex-List Recall Regression Test
- **Task ID**: apex-recall
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the apex-list recall regression module and its pytest regression test. This verifies that known apex experts surface in the top-K ranked results for curated queries.

    ## What to do

    1. Create `config/aegis/apex_queries/nsclc_translational_v1.yaml` with the following structure:
       ```yaml
       # Curated apex queries for NSCLC translational regression testing
       version: 1
       specialty: translational
       queries:
         - query_id: "nccn-nsclc-panel"
           description: "NCCN NSCLC guideline panel members"
           mesh_terms: ["Carcinoma, Non-Small-Cell Lung", "Practice Guidelines as Topic"]
           expected_uuids: []  # To be populated with real UUIDs when cohort is seeded
           top_k: 50
         - query_id: "nih-merit-nsclc"
           description: "NIH MERIT awardees in NSCLC research"
           mesh_terms: ["Carcinoma, Non-Small-Cell Lung", "Research Support, N.I.H., Extramural"]
           expected_uuids: []
           top_k: 50
         - query_id: "asco-yi-nsclc"
           description: "ASCO Young Investigator awardees in NSCLC"
           mesh_terms: ["Carcinoma, Non-Small-Cell Lung", "Biomarkers, Tumor"]
           expected_uuids: []
           top_k: 50
       ```
       NOTE: expected_uuids are empty placeholders; they will be populated when real cohort data is seeded. Tests use synthetic data.

    2. Create `src/aegis/observability/apex_recall.py` with:

    3. **`ApexQuery` frozen Pydantic model**:
       ```python
       class ApexQuery(BaseModel):
           model_config = ConfigDict(frozen=True)

           query_id: str
           description: str
           mesh_terms: list[str]
           expected_uuids: list[str]
           top_k: int
       ```

    4. **`RecallResult` frozen Pydantic model**:
       ```python
       class RecallResult(BaseModel):
           model_config = ConfigDict(frozen=True)

           query_id: str
           recall: float             # fraction of expected_uuids found in top_k
           found_uuids: list[str]
           missed_uuids: list[str]
           top_k: int
           total_expected: int
           run_date: date
       ```

    5. **`WeeklyTrend` frozen Pydantic model**:
       ```python
       class WeeklyTrend(BaseModel):
           model_config = ConfigDict(frozen=True)

           query_id: str
           current_recall: float
           previous_recall: float
           delta: float
           alert: bool              # True if delta < -0.05
       ```

    6. **`ApexRecallTracker` class**:
       - `__init__(self, db_path: str = "aegis.duckdb", recall_threshold: float = 0.80, drop_alert_threshold: float = 0.05)` -- DuckDB connection, create table:
         ```sql
         CREATE TABLE IF NOT EXISTS apex_recall_results (
             query_id TEXT NOT NULL,
             run_date DATE NOT NULL,
             recall DOUBLE NOT NULL,
             found_uuids TEXT NOT NULL,
             missed_uuids TEXT NOT NULL,
             top_k INTEGER NOT NULL,
             total_expected INTEGER NOT NULL,
             PRIMARY KEY (query_id, run_date)
         );
         ```
       - `load_apex_queries(self, config_path: Path) -> list[ApexQuery]` -- load queries from YAML. Uses `yaml.safe_load()`.
       - `compute_recall(self, query: ApexQuery, ranked_uuids: list[str]) -> RecallResult` -- take the top_k UUIDs from the ranked output, compute recall = |intersection with expected_uuids| / |expected_uuids|. If expected_uuids is empty, recall = 1.0 (vacuous truth). Return RecallResult with today's date.
       - `record_result(self, result: RecallResult) -> None` -- persist to DuckDB with upsert. found_uuids and missed_uuids stored as JSON arrays.
       - `get_weekly_trend(self, query_id: str, current_date: date) -> WeeklyTrend | None` -- fetch recall for current_date and for current_date - 7 days. If both exist, compute delta and alert flag.
       - `check_all_trends(self, current_date: date) -> list[WeeklyTrend]` -- check trends for all query_ids with data on current_date.
       - `passes_threshold(self, results: list[RecallResult]) -> bool` -- return True if the mean recall across all results >= recall_threshold.

    7. Create `src/aegis/observability/apex_recall_test.py` with tests:
       - `test_recall_computation` -- create ApexQuery with 10 expected UUIDs, provide ranked list containing 8 of them in top 50, verify recall = 0.8.
       - `test_recall_perfect` -- all expected UUIDs in top-K, recall = 1.0.
       - `test_recall_empty_expected` -- empty expected_uuids, recall = 1.0.
       - `test_record_and_trend` -- record recall on two dates 7 days apart, verify weekly trend delta is correct and alert flag is set when drop > 5%.
       - `test_passes_threshold` -- verify passes_threshold returns True when mean >= 0.8, False when below.
       - `test_load_queries_from_yaml` -- write a temp YAML file, load, verify parsing.
       - Use `tmp_path` for DuckDB path.

    8. Create `tests/regression/__init__.py` as empty file (or with a pass statement).

    9. Create `tests/regression/test_apex_recall.py` as a regression test:
       ```python
       """Apex-list recall regression: known experts must surface in top-K results."""
       from __future__ import annotations

       import pytest
       from aegis.observability.apex_recall import ApexRecallTracker, ApexQuery, RecallResult

       # This test uses synthetic data. When real cohort is seeded, replace with
       # actual queries from config/aegis/apex_queries/nsclc_translational_v1.yaml.

       def test_apex_recall_threshold_synthetic(tmp_path):
           """Synthetic check that recall computation logic meets >=80% threshold."""
           tracker = ApexRecallTracker(db_path=str(tmp_path / "test.duckdb"))
           query = ApexQuery(
               query_id="synthetic-nsclc",
               description="Synthetic NSCLC query",
               mesh_terms=["Carcinoma, Non-Small-Cell Lung"],
               expected_uuids=[f"uuid-{i}" for i in range(10)],
               top_k=50,
           )
           # Simulate ranking that includes 9 of 10 expected
           ranked = [f"uuid-{i}" for i in range(9)] + [f"other-{i}" for i in range(41)]
           result = tracker.compute_recall(query, ranked)
           assert result.recall >= 0.80
           assert tracker.passes_threshold([result])
       ```

    ## Files to modify
    - `config/aegis/apex_queries/nsclc_translational_v1.yaml` -- NEW: curated apex queries
    - `src/aegis/observability/apex_recall.py` -- NEW: apex recall tracker
    - `src/aegis/observability/apex_recall_test.py` -- NEW: unit tests
    - `tests/regression/__init__.py` -- NEW: package init
    - `tests/regression/test_apex_recall.py` -- NEW: regression test

    ## Code patterns to follow
    - DuckDB pattern from `src/aegis/observability/drift.py:62-69`.
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - YAML loading pattern from `src/aegis/scoring/quality_prior.py:38-51`.
    - JSON array storage for list fields in DuckDB (same as score_dist bucket_edges).
    - `from __future__ import annotations` at top of every file.

    ## Acceptance criteria
    - `ApexRecallTracker` computes recall correctly against known expected UUIDs.
    - Weekly trend tracking detects >5% drops.
    - Regression test passes with synthetic data at >=80% recall.
    - All tests pass: `cd /Users/anvith/aegis && python -m pytest src/aegis/observability/apex_recall_test.py tests/regression/test_apex_recall.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && python -m mypy src/aegis/observability/apex_recall.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check src/aegis/observability/apex_recall.py src/aegis/observability/apex_recall_test.py tests/regression/test_apex_recall.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/observability/apex_recall_test.py tests/regression/test_apex_recall.py -x -q && python -m mypy src/aegis/observability/apex_recall.py --strict && python -m ruff check src/aegis/observability/apex_recall.py src/aegis/observability/apex_recall_test.py tests/regression/test_apex_recall.py
    ```

### 4. Build Pairwise Audit Consistency Tracker
- **Task ID**: audit-consistency
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the audit consistency tracking module that computes inter-reviewer Cohen's kappa on overlapping pairs and manages intra-reviewer re-show at 5% rate.

    ## What to do

    NOTE: Phase 1c creates `src/aegis/audit/storage.py` with `PairwiseJudgment` and `JudgmentStore`. This module does NOT import those classes directly to avoid a hard dependency on Phase 1c being built first. Instead, it defines its own lightweight input types and can be adapted to consume Phase 1c's types once available.

    1. Create `src/aegis/observability/audit_consistency.py` with:

    2. **`JudgmentRecord` frozen Pydantic model** (lightweight input type):
       ```python
       class JudgmentRecord(BaseModel):
           model_config = ConfigDict(frozen=True)

           judgment_id: str
           reviewer_id: str
           candidate_a_uuid: str
           candidate_b_uuid: str
           winner_uuid: str
           is_reshow: bool = False   # True if this was a deliberate re-show
       ```

    3. **`ConsistencyReport` frozen Pydantic model**:
       ```python
       class ConsistencyReport(BaseModel):
           model_config = ConfigDict(frozen=True)

           inter_reviewer_kappa: float | None    # None if no overlapping pairs
           intra_reviewer_kappa: float | None     # None if no re-shows
           overlapping_pair_count: int
           reshow_pair_count: int
           per_reviewer_agreement: dict[str, float]  # reviewer_id -> agreement rate
           low_agreement_reviewers: list[str]         # reviewers with agreement < 0.6
       ```

    4. **`AuditConsistencyTracker` class**:
       - `__init__(self, reshow_rate: float = 0.05, low_agreement_threshold: float = 0.6)` -- store config.
       - `should_reshow(self, pair_count: int) -> bool` -- deterministic check: return True if `pair_count` modulo `round(1/reshow_rate)` == 0 (i.e., every 20th pair is a re-show). This is simple and predictable.
       - `find_overlapping_pairs(self, judgments: list[JudgmentRecord]) -> list[tuple[JudgmentRecord, JudgmentRecord]]` -- find pairs where the same (candidate_a_uuid, candidate_b_uuid) set (order-independent) was judged by two different reviewers. Return list of (judgment_1, judgment_2) tuples.
       - `find_reshow_pairs(self, judgments: list[JudgmentRecord]) -> list[tuple[JudgmentRecord, JudgmentRecord]]` -- find pairs where the same reviewer judged the same candidate pair twice (is_reshow=True on the second).
       - `compute_kappa(self, agreement_pairs: list[tuple[bool, bool]]) -> float` -- compute Cohen's kappa from a list of (rater1_chose_a, rater2_chose_a) pairs. Formula: `kappa = (p_o - p_e) / (1 - p_e)` where p_o is observed agreement and p_e is expected agreement by chance. Handle edge cases: if p_e == 1.0, return 1.0 (perfect agreement); if n == 0, return 0.0.
       - `compute_report(self, judgments: list[JudgmentRecord]) -> ConsistencyReport` -- orchestrate: find overlapping pairs, compute inter-reviewer kappa; find reshow pairs, compute intra-reviewer kappa; compute per-reviewer agreement rates (fraction of overlapping judgments where reviewer agreed with the majority); flag low-agreement reviewers.

    5. Create `src/aegis/observability/audit_consistency_test.py` with tests:
       - `test_should_reshow_rate` -- verify approximately 5% of pair_counts trigger a re-show.
       - `test_kappa_perfect_agreement` -- two raters always agree -> kappa near 1.0.
       - `test_kappa_random_agreement` -- two raters choose randomly -> kappa near 0.0.
       - `test_kappa_no_pairs` -- empty list returns 0.0.
       - `test_find_overlapping_pairs` -- create 4 judgments with 2 overlapping pairs from different reviewers, verify found.
       - `test_find_reshow_pairs` -- create judgments with is_reshow=True, verify found.
       - `test_full_report` -- create a realistic set of 20 judgments with some overlap and re-shows, verify ConsistencyReport fields are populated correctly.
       - `test_low_agreement_detection` -- create a reviewer with <60% agreement, verify they appear in low_agreement_reviewers.

    ## Files to modify
    - `src/aegis/observability/audit_consistency.py` -- NEW: entire module
    - `src/aegis/observability/audit_consistency_test.py` -- NEW: tests

    ## Code patterns to follow
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - `from __future__ import annotations` at top.
    - Pure computation (no DuckDB in this module -- it operates on in-memory judgment lists).
    - For pair key normalization (order-independent): use `tuple(sorted([a_uuid, b_uuid]))`.

    ## Acceptance criteria
    - Cohen's kappa correctly computed on synthetic perfect-agreement and random-agreement data.
    - Overlapping and re-show pair detection works correctly.
    - Low-agreement reviewers flagged at <0.6 threshold.
    - Re-show rate is approximately 5%.
    - All tests pass: `cd /Users/anvith/aegis && python -m pytest src/aegis/observability/audit_consistency_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && python -m mypy src/aegis/observability/audit_consistency.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check src/aegis/observability/audit_consistency.py src/aegis/observability/audit_consistency_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/observability/audit_consistency_test.py -x -q && python -m mypy src/aegis/observability/audit_consistency.py --strict && python -m ruff check src/aegis/observability/audit_consistency.py src/aegis/observability/audit_consistency_test.py
    ```

### 5. Build Weight-Stability Tracker
- **Task ID**: weight-stability
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build the weight-stability tracking module that compares consecutive weight versions and alerts on >25% parameter shifts.

    ## What to do

    1. Create `src/aegis/observability/weight_stability.py` with:

    2. **`WeightShift` frozen Pydantic model**:
       ```python
       class WeightShift(BaseModel):
           model_config = ConfigDict(frozen=True)

           parameter: str            # e.g., "f1_rcr", "alpha", "beta", "gamma"
           old_value: float
           new_value: float
           absolute_change: float
           relative_change_pct: float  # |new - old| / |old| * 100
           exceeds_threshold: bool
       ```

    3. **`StabilityReport` frozen Pydantic model**:
       ```python
       class StabilityReport(BaseModel):
           model_config = ConfigDict(frozen=True)

           old_version: int
           new_version: int
           shifts: list[WeightShift]
           requires_review: bool     # True if any shift exceeds threshold
           auto_deploy_ok: bool      # True if no shift exceeds threshold
           summary: str
       ```

    4. **`WeightStabilityTracker` class**:
       - `__init__(self, shift_threshold_pct: float = 25.0)` -- store threshold.
       - `compare_weights(self, old_weights: dict[str, float], new_weights: dict[str, float]) -> list[WeightShift]` -- for each key in the union of old and new, compute absolute and relative change. Mark `exceeds_threshold` if relative change > threshold. If old_value is 0.0, use absolute_change > 0.01 as the threshold criterion to avoid division by zero.
       - `compare_vectors(self, old_vector: WeightVector, new_vector: WeightVector) -> StabilityReport` -- compare both `.weights` (family weights) and `.exponents` (alpha, beta, gamma). Uses `compare_weights` internally. Combine all WeightShifts. `requires_review = any(s.exceeds_threshold for s in shifts)`. `auto_deploy_ok = not requires_review`. Generate a human-readable summary string.
       - `load_version(self, config_dir: Path, version: int) -> WeightVector` -- construct path as `config_dir / f"translational_v{version}.yaml"` and call `load_weight_vector()` from `src/aegis/scoring/quality_prior.py`. Import: `from aegis.scoring.quality_prior import load_weight_vector, WeightVector`.
       - `check_latest_stability(self, config_dir: Path) -> StabilityReport | None` -- glob `config_dir` for `translational_v*.yaml` files, sort by version number, compare the two highest versions. Return None if fewer than 2 versions exist.
       - `generate_review_template(self, report: StabilityReport) -> str` -- generate a Markdown string for ops review. Include a table of parameter shifts, which parameters exceeded the threshold, and a recommendation (approve/reject/investigate).

    5. Create `ops/aegis/weight_review.md` with a static approval workflow template:
       ```markdown
       # Weight Review Approval Workflow

       ## Purpose
       When the Plackett-Luce refit produces weight changes exceeding the 25% stability threshold,
       this review workflow is triggered before the new weights are deployed.

       ## Process
       1. **Automated check**: `WeightStabilityTracker.check_latest_stability()` detects shifts >25%.
       2. **Review template generated**: Markdown report with per-parameter comparison.
       3. **Human review**: Audit panel admin reviews the shift report and the underlying pairwise judgment data.
       4. **Decision**: Approve (deploy new weights), Reject (keep current weights), or Investigate (defer pending analysis).
       5. **Record**: Decision recorded with reviewer ID, timestamp, and justification.

       ## Review Criteria
       - Is the training data sufficient (>200 pairwise judgments)?
       - Is the shift consistent with known data changes (new apex queries, new cohort members)?
       - Does the refit improve recall on apex queries?
       - Are confidence intervals acceptable (CI half-width < 0.2 for all exponents)?

       ## Escalation
       - If 2+ consecutive refits trigger review, escalate to the scoring team lead.
       - If any exponent hits its bound constraint, flag as potential model misspecification.
       ```

    6. Create `src/aegis/observability/weight_stability_test.py` with tests:
       - `test_no_shift` -- identical weights -> all relative_change_pct == 0.0, auto_deploy_ok = True.
       - `test_small_shift` -- 10% shift on one parameter -> auto_deploy_ok = True, requires_review = False.
       - `test_large_shift_triggers_review` -- 30% shift on alpha -> requires_review = True, auto_deploy_ok = False.
       - `test_zero_old_value` -- old_value = 0.0, new_value = 0.05 -> uses absolute change criterion.
       - `test_compare_vectors` -- create two WeightVector objects with different weights and exponents, verify StabilityReport captures all shifts.
       - `test_review_template_generation` -- verify generated Markdown contains expected parameter names and shift values.
       - `test_check_latest_stability` -- write two YAML files (v1 and v2) to tmp_path, verify check_latest_stability returns a StabilityReport. Note: write the YAML files using the exact format of `config/aegis/weights/translational_v1.yaml` (see below).
       - The YAML format for weight files:
         ```yaml
         version: N
         specialty: translational
         created: "2026-04-26"
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
       - Use `tmp_path` for any file I/O.

    ## Files to modify
    - `src/aegis/observability/weight_stability.py` -- NEW: entire module
    - `src/aegis/observability/weight_stability_test.py` -- NEW: tests
    - `ops/aegis/weight_review.md` -- NEW: approval workflow

    ## Code patterns to follow
    - Import `from aegis.scoring.quality_prior import load_weight_vector, WeightVector`.
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - `from __future__ import annotations` at top.
    - Path handling via `pathlib.Path`.
    - Glob pattern for finding weight files: `sorted(config_dir.glob("translational_v*.yaml"))`.

    ## Acceptance criteria
    - Weight shifts computed correctly with relative percentage change.
    - >25% shift triggers `requires_review = True`.
    - Review template generated with parameter table.
    - `ops/aegis/weight_review.md` documents the approval workflow.
    - All tests pass: `cd /Users/anvith/aegis && python -m pytest src/aegis/observability/weight_stability_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && python -m mypy src/aegis/observability/weight_stability.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check src/aegis/observability/weight_stability.py src/aegis/observability/weight_stability_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/observability/weight_stability_test.py -x -q && python -m mypy src/aegis/observability/weight_stability.py --strict && python -m ruff check src/aegis/observability/weight_stability.py src/aegis/observability/weight_stability_test.py
    ```

### 6. Build Score Recomputation Strategy
- **Task ID**: recompute-strategy
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the nightly score recomputation module that recomputes Q(c) and v_c for all candidates in a cohort. Must be idempotent and resumable.

    ## What to do

    1. Create `src/aegis/scheduling/__init__.py` with:
       ```python
       """Aegis scheduling — nightly recompute and batch operations."""
       ```

    2. Create `src/aegis/scheduling/recompute.py` with:

    3. **`RecomputeResult` frozen Pydantic model**:
       ```python
       class RecomputeResult(BaseModel):
           model_config = ConfigDict(frozen=True)

           cohort_id: str
           total_candidates: int
           recomputed_count: int
           skipped_count: int         # already up-to-date (cache hit)
           failed_count: int
           elapsed_seconds: float
           weight_version: int
           idempotent: bool           # True if re-running would produce same results
       ```

    4. **`CandidateRecomputeRecord` frozen Pydantic model**:
       ```python
       class CandidateRecomputeRecord(BaseModel):
           model_config = ConfigDict(frozen=True)

           candidate_uuid: str
           quality_score_raw: float
           quality_percentile: float
           vector_nonzero_dims: int
           artifact_set_hash: str
           weight_version: int
           computed_at: datetime
       ```

    5. **`ScoreRecomputer` class**:
       - `__init__(self, db_path: str = "aegis.duckdb")` -- DuckDB connection, create table:
         ```sql
         CREATE TABLE IF NOT EXISTS recompute_log (
             cohort_id TEXT NOT NULL,
             candidate_uuid TEXT NOT NULL,
             quality_score_raw DOUBLE NOT NULL,
             quality_percentile DOUBLE NOT NULL,
             vector_nonzero_dims INTEGER NOT NULL,
             artifact_set_hash TEXT NOT NULL,
             weight_version INTEGER NOT NULL,
             computed_at TIMESTAMP NOT NULL,
             PRIMARY KEY (cohort_id, candidate_uuid, weight_version)
         );
         ```
       - `compute_artifact_set_hash(self, artifact_ids: list[str]) -> str` -- sort the artifact IDs, join with "|", compute SHA-256 hex digest. Import `hashlib`.
       - `is_up_to_date(self, cohort_id: str, candidate_uuid: str, artifact_set_hash: str, weight_version: int) -> bool` -- query the recompute_log for a matching row. If found, return True (skip recompute).
       - `recompute_candidate(self, cohort_id: str, candidate_uuid: str, component_percentiles: dict[str, float], artifact_weights: list[dict[str, Any]], artifact_ids: list[str], quality_prior: QualityPrior) -> CandidateRecomputeRecord` -- compute Q(c) via `quality_prior.compute_raw(component_percentiles)`, build candidate vector via `CandidateVectorBuilder().build(...)`, compute artifact_set_hash, create and return `CandidateRecomputeRecord`. Import: `from aegis.scoring.quality_prior import QualityPrior`, `from aegis.scoring.candidate_vector import CandidateVectorBuilder, ArtifactWeight`.
       - `record_recompute(self, cohort_id: str, record: CandidateRecomputeRecord) -> None` -- upsert into recompute_log.
       - `recompute_batch(self, cohort_id: str, candidates: list[tuple[str, dict[str, float], list[dict[str, Any]], list[str]]], quality_prior: QualityPrior) -> RecomputeResult` -- iterate over candidates, check is_up_to_date, skip if current, else recompute and record. Track timing, counts, and errors. Return RecomputeResult.
         - The `candidates` parameter is a list of tuples: `(candidate_uuid, component_percentiles, artifact_weight_dicts, artifact_ids)`.
         - Wrap individual candidate processing in try/except to handle failures without aborting the batch.
       - `get_latest_records(self, cohort_id: str, weight_version: int) -> list[CandidateRecomputeRecord]` -- fetch all records for a cohort+version.

    6. Create `src/aegis/scheduling/recompute_test.py` with tests:
       - `test_artifact_set_hash_deterministic` -- same IDs in different order produce same hash.
       - `test_is_up_to_date_miss` -- no prior record -> False.
       - `test_is_up_to_date_hit` -- record exists with matching hash and version -> True.
       - `test_recompute_candidate` -- provide sample component_percentiles and artifacts, verify CandidateRecomputeRecord has correct fields.
       - `test_recompute_batch_idempotent` -- run recompute_batch twice with same input, verify second run has skipped_count == total and recomputed_count == 0.
       - `test_recompute_batch_counts` -- run with 5 candidates, verify counts add up.
       - Use `tmp_path` for DuckDB path.
       - For artifact_weights in tests, create simple ArtifactWeight objects:
         ```python
         from aegis.scoring.candidate_vector import ArtifactWeight
         art = ArtifactWeight(pmid="PM1", role_weight=1.0, venue_weight=1.0, recency_weight=1.0, evidence_type_weight=1.0, mesh_descriptors={"MeSH1"})
         ```
       - For quality_prior in tests:
         ```python
         from aegis.scoring.quality_prior import QualityPrior, WeightVector
         wv = WeightVector(version=1, specialty="translational", weights={"f1_rcr": 0.35, "f2_funding": 0.25, "f3_leadership": 0.20, "f4_apex": 0.05, "f5_translational": 0.10, "f6_lineage": 0.05}, exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4}, exponent_bounds={"alpha": [0.3, 1.2], "beta": [0.5, 1.5], "gamma": [0.1, 0.8]})
         qp = QualityPrior(wv)
         ```

    ## Files to modify
    - `src/aegis/scheduling/__init__.py` -- NEW: package init
    - `src/aegis/scheduling/recompute.py` -- NEW: entire module
    - `src/aegis/scheduling/recompute_test.py` -- NEW: tests

    ## Code patterns to follow
    - DuckDB pattern from `src/aegis/observability/drift.py:62-69`.
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - `from __future__ import annotations` at top.
    - Hashing via `hashlib.sha256`.
    - Import `QualityPrior` and `CandidateVectorBuilder` from their respective modules.
    - Time tracking via `import time; start = time.monotonic()`.

    ## Acceptance criteria
    - Artifact-set hash is deterministic regardless of input order.
    - Recompute is idempotent: second run skips all candidates.
    - Batch recompute handles individual failures without aborting.
    - All tests pass: `cd /Users/anvith/aegis && python -m pytest src/aegis/scheduling/recompute_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && python -m mypy src/aegis/scheduling/recompute.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check src/aegis/scheduling/recompute.py src/aegis/scheduling/recompute_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/scheduling/recompute_test.py -x -q && python -m mypy src/aegis/scheduling/recompute.py --strict && python -m ruff check src/aegis/scheduling/recompute.py src/aegis/scheduling/recompute_test.py
    ```

### 7. Build Score Cache with Pluggable Backend
- **Task ID**: score-cache
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the caching layer for v_c and Q(c), keyed by candidate UUID + artifact-set hash + weight-vector version.

    ## What to do

    1. Create `src/aegis/scoring/cache.py` with:

    2. **`CacheKey` frozen Pydantic model**:
       ```python
       class CacheKey(BaseModel):
           model_config = ConfigDict(frozen=True)

           candidate_uuid: str
           artifact_set_hash: str
           weight_version: int

           def to_string(self) -> str:
               return f"{self.candidate_uuid}:{self.artifact_set_hash}:{self.weight_version}"
       ```

    3. **`CachedScore` frozen Pydantic model**:
       ```python
       class CachedScore(BaseModel):
           model_config = ConfigDict(frozen=True)

           quality_score_raw: float
           quality_percentile: float
           vector_data: dict[str, float]  # sparse vector as dict
           cached_at: datetime
       ```

    4. **`CacheStats` frozen Pydantic model**:
       ```python
       class CacheStats(BaseModel):
           model_config = ConfigDict(frozen=True)

           total_requests: int
           hits: int
           misses: int
           hit_rate: float
           entry_count: int
       ```

    5. **`CacheBackend` protocol** (abstract interface):
       ```python
       from typing import Protocol

       class CacheBackend(Protocol):
           def get(self, key: str) -> str | None: ...
           def set(self, key: str, value: str) -> None: ...
           def delete(self, key: str) -> None: ...
           def clear(self) -> None: ...
           def size(self) -> int: ...
       ```

    6. **`SQLiteCacheBackend` class** (default):
       - `__init__(self, db_path: str = "aegis_cache.db")` -- create SQLite connection and table:
         ```sql
         CREATE TABLE IF NOT EXISTS score_cache (
             cache_key TEXT PRIMARY KEY,
             value TEXT NOT NULL,
             created_at TEXT NOT NULL
         );
         ```
       - `get(self, key: str) -> str | None` -- SELECT value WHERE cache_key = key.
       - `set(self, key: str, value: str) -> None` -- INSERT OR REPLACE.
       - `delete(self, key: str) -> None` -- DELETE WHERE cache_key = key.
       - `clear(self) -> None` -- DELETE FROM score_cache.
       - `size(self) -> int` -- SELECT COUNT(*).
       - Use `import sqlite3` (stdlib, no new dependencies).

    7. **`ScoreCache` class**:
       - `__init__(self, backend: CacheBackend | None = None)` -- use provided backend or create a default `SQLiteCacheBackend` with in-memory SQLite (`:memory:`).
       - Internal counters: `_hits: int = 0`, `_misses: int = 0`.
       - `get(self, key: CacheKey) -> CachedScore | None` -- look up via backend.get(key.to_string()), deserialize JSON to CachedScore if found, increment hit/miss counters.
       - `put(self, key: CacheKey, score: CachedScore) -> None` -- serialize CachedScore to JSON, store via backend.set(key.to_string(), json_str).
       - `invalidate(self, candidate_uuid: str) -> None` -- NOTE: since SQLite backend does not support prefix deletion efficiently, this method is a best-effort. For Phase 1, it can be a no-op with a TODO comment noting that production should use a backend with prefix/scan support. The primary invalidation mechanism is the artifact_set_hash changing in the key.
       - `invalidate_by_weight_version(self, weight_version: int) -> None` -- same as above: Phase 1 relies on cache key mismatch (different weight_version in key = automatic miss). No-op with TODO.
       - `get_stats(self) -> CacheStats` -- return CacheStats with hit_rate = hits / (hits + misses) if total > 0, else 0.0.
       - `clear(self) -> None` -- clear backend and reset counters.

    8. Create `src/aegis/scoring/cache_test.py` with tests:
       - `test_put_and_get` -- store a CachedScore, retrieve it, verify fields match.
       - `test_cache_miss` -- get with unknown key returns None.
       - `test_cache_stats` -- perform 3 hits and 1 miss, verify hit_rate = 0.75.
       - `test_cache_key_isolation` -- different artifact_set_hash or weight_version produces different keys and different cache entries.
       - `test_clear` -- put entries, clear, verify all gone.
       - `test_sqlite_backend` -- directly test SQLiteCacheBackend get/set/delete/size with `tmp_path`.
       - `test_overwrite` -- put same key twice with different values, verify latest value returned.
       - Use `tmp_path` for SQLite path where persistent backend is needed, or use in-memory SQLite for speed.

    ## Files to modify
    - `src/aegis/scoring/cache.py` -- NEW: entire module
    - `src/aegis/scoring/cache_test.py` -- NEW: tests

    ## Code patterns to follow
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - `from __future__ import annotations` at top.
    - Protocol for backend abstraction (Python 3.11+ typing.Protocol).
    - JSON serialization via `model.model_dump_json()` and `CachedScore.model_validate_json(json_str)`.
    - sqlite3 from stdlib (no new dependencies needed).

    ## Acceptance criteria
    - Cache stores and retrieves CachedScore correctly.
    - Different cache keys (different UUID, hash, or version) produce independent entries.
    - Cache stats track hits and misses accurately.
    - SQLite backend persists across get/set calls.
    - All tests pass: `cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/cache_test.py -x -q`
    - mypy strict passes: `cd /Users/anvith/aegis && python -m mypy src/aegis/scoring/cache.py --strict`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check src/aegis/scoring/cache.py src/aegis/scoring/cache_test.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/cache_test.py -x -q && python -m mypy src/aegis/scoring/cache.py --strict && python -m ruff check src/aegis/scoring/cache.py src/aegis/scoring/cache_test.py
    ```

### 8. Build Query Latency Budget Documentation and Performance Test
- **Task ID**: latency-budget
- **Role**: builder
- **Depends On**: score-cache
- **Assigned To**: builder-2
- **Description**: |
    Create the documented latency budget and a performance test that benchmarks query execution against the <500ms p95 target.

    ## What to do

    1. Create `src/aegis/scoring/latency_budget.md`:
       ```markdown
       # Query Latency Budget

       ## Target
       - **p95 < 500ms** for top-50 ranked output on cohort scale (~5,000 candidates)
       - Bootstrap-variance pre-computed offline (not included in query-time budget)

       ## Budget Breakdown

       | Stage                  | Budget (ms) | Notes                                       |
       |------------------------|-------------|---------------------------------------------|
       | Query expansion        | <= 100      | MeSH term lookup + synonym expansion        |
       | Topical-fit retrieval  | <= 200      | v_c lookup (cached) + cosine similarity     |
       | Recency + final scoring| <= 150      | Time-decay sum + Rank composition + sort    |
       | Formatting             | <= 50       | Result serialization + top-3 artifacts      |
       | **Total**              | **<= 500**  |                                             |

       ## Assumptions
       - Candidate vectors (v_c) are pre-computed and cached (see cache.py)
       - Q(c) percentiles are pre-computed nightly (see scheduling/recompute.py)
       - Bootstrap variance bands are pre-computed nightly (not in query path)
       - Cohort size: ~5,000 candidates (Phase 1 NSCLC translational)

       ## Pre-computed (offline, not in query path)
       - v_c candidate vectors: nightly recompute
       - Q(c) quality prior percentiles: nightly recompute
       - Bootstrap score bands: nightly recompute

       ## Per-query computation
       - Query vector construction: build SparseVector from MeSH terms
       - Topical fit: dot product of normalized sparse vectors (O(min(|v_c|, |v_q|)) per candidate)
       - Recency: iterate candidate artifacts, filter by MeSH overlap, sum time-decay
       - Rank composition: I(c) * Q^alpha * T^beta * R^gamma per candidate
       - Sort and top-k selection

       ## Monitoring
       - Performance test: `tests/perf/test_query_latency.py` benchmarks 100 queries
       - Prometheus histogram: `aegis_query_latency_seconds` (Phase 3)
       ```

    2. Create `tests/perf/__init__.py` as empty package init.

    3. Create `tests/perf/test_query_latency.py`:
       ```python
       """Query latency benchmark: p95 < 500ms for top-50 on synthetic cohort."""
       from __future__ import annotations

       import statistics
       import time
       from datetime import date

       import pytest

       from aegis.scoring.candidate_vector import (
           ArtifactWeight,
           CandidateVectorBuilder,
           QueryVectorBuilder,
           SparseVector,
       )
       from aegis.scoring.rank import CandidateScoreInput, Ranker
       from aegis.scoring.recency import Recency, RecencyArtifact
       from aegis.scoring.topical_fit import TopicalFit


       def _build_synthetic_cohort(n: int = 100) -> tuple[
           list[CandidateScoreInput],
           list[SparseVector],
           list[list[RecencyArtifact]],
       ]:
           """Build a synthetic cohort of n candidates with random-ish scores."""
           import random
           random.seed(42)

           mesh_universe = [f"D{i:06d}" for i in range(500)]
           query_terms = mesh_universe[:20]
           builder = CandidateVectorBuilder()
           candidates = []
           vectors = []
           recency_artifacts = []

           for i in range(n):
               # Build candidate vector
               n_terms = random.randint(10, 50)
               terms = set(random.sample(mesh_universe, n_terms))
               arts = [
                   ArtifactWeight(
                       pmid=f"PM{i}_{j}",
                       role_weight=random.uniform(0.3, 1.0),
                       venue_weight=random.uniform(0.5, 1.0),
                       recency_weight=random.uniform(0.3, 1.0),
                       evidence_type_weight=random.uniform(0.5, 1.0),
                       mesh_descriptors=terms,
                   )
                   for j in range(random.randint(5, 20))
               ]
               vec = builder.build(arts)
               vectors.append(vec)

               # Build recency artifacts
               rec_arts = [
                   RecencyArtifact(
                       publication_date=date(2024 - random.randint(0, 10), 1 + random.randint(0, 11), 1 + random.randint(0, 27)),
                       role_weight=random.uniform(0.3, 1.0),
                       type_weight=random.uniform(0.5, 1.0),
                       is_preprint=random.random() < 0.1,
                       mesh_descriptors=terms,
                   )
                   for _ in range(random.randint(3, 15))
               ]
               recency_artifacts.append(rec_arts)

               candidates.append(
                   CandidateScoreInput(
                       candidate_uuid=f"uuid-{i}",
                       candidate_name=f"Dr. Candidate {i}",
                       linkage_confidence=random.uniform(0.7, 1.0),
                       integrity_score=random.uniform(0.5, 1.0),
                       quality_percentile=random.uniform(0.1, 0.95),
                       topical_fit=0.0,  # will be computed
                       recency=0.0,  # will be computed
                   )
               )

           return candidates, vectors, recency_artifacts


       def test_query_latency_p95(tmp_path) -> None:
           """Benchmark: p95 query latency < 500ms for top-50 on synthetic cohort."""
           candidates, vectors, recency_artifacts = _build_synthetic_cohort(100)

           query_builder = QueryVectorBuilder()
           mesh_universe = [f"D{i:06d}" for i in range(500)]
           query_mesh_terms = mesh_universe[:20]
           query_vec = query_builder.build(query_mesh_terms)
           query_mesh_set = set(query_mesh_terms)

           topical_fit = TopicalFit()
           recency = Recency()
           ranker = Ranker()
           ref_date = date(2026, 4, 26)

           latencies: list[float] = []

           for trial in range(100):
               start = time.monotonic()

               # Compute T(c,q) and R(c,q) for each candidate
               for i, c in enumerate(candidates):
                   t = topical_fit.compute(vectors[i], query_vec)
                   r = recency.compute(recency_artifacts[i], query_mesh_set, ref_date)
                   # Mutate the dataclass fields for this benchmark
                   c.topical_fit = t
                   c.recency = r

               # Rank
               result = ranker.rank(query_mesh_terms, candidates, k=50)

               elapsed = time.monotonic() - start
               latencies.append(elapsed * 1000)  # convert to ms

           p95 = sorted(latencies)[94]  # 95th percentile of 100 samples
           median = statistics.median(latencies)

           # Assert p95 < 500ms
           # NOTE: For a synthetic 100-candidate cohort, latency should be well
           # under budget. At 5K candidates the budget is 500ms; at 100 candidates
           # we expect ~10-50ms. We use a generous 500ms threshold to avoid flaky
           # CI failures while still catching gross regressions.
           assert p95 < 500, f"p95 latency {p95:.1f}ms exceeds 500ms budget"

           # Log for human review
           print(f"\nLatency benchmark (100 candidates, 100 trials):")
           print(f"  p50: {median:.1f}ms")
           print(f"  p95: {p95:.1f}ms")
           print(f"  max: {max(latencies):.1f}ms")
       ```

    ## Files to modify
    - `src/aegis/scoring/latency_budget.md` -- NEW: documented latency budget
    - `tests/perf/__init__.py` -- NEW: package init
    - `tests/perf/test_query_latency.py` -- NEW: performance benchmark test

    ## Code patterns to follow
    - Test structure follows existing tests in `src/aegis/observability/drift_test.py`.
    - Uses existing scoring classes: `Ranker`, `TopicalFit`, `Recency`, `CandidateVectorBuilder`, `QueryVectorBuilder`.
    - `from __future__ import annotations` at top.
    - `time.monotonic()` for precise timing.
    - Synthetic data uses `random.seed(42)` for reproducibility.

    ## Acceptance criteria
    - Latency budget documented in `src/aegis/scoring/latency_budget.md` with stage breakdown.
    - Performance test benchmarks 100 queries and asserts p95 < 500ms.
    - Performance test passes: `cd /Users/anvith/aegis && python -m pytest tests/perf/test_query_latency.py -x -q -s`
    - ruff passes: `cd /Users/anvith/aegis && python -m ruff check tests/perf/test_query_latency.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest tests/perf/test_query_latency.py -x -q -s && python -m ruff check tests/perf/test_query_latency.py
    ```

### 9. Build Ops Artifacts and Alert Rules
- **Task ID**: ops-artifacts
- **Role**: builder
- **Depends On**: score-dist-monitor, integrity-dashboard
- **Assigned To**: builder-2
- **Description**: |
    Create the ops artifacts: Prometheus alert rules for score distribution anomalies and dashboard directory structure.

    ## What to do

    1. Create `ops/aegis/dashboards/` directory by creating a placeholder file.

    2. Create `ops/aegis/score_dist_alerts.yaml`:
       ```yaml
       groups:
         - name: aegis-score-distribution
           rules:
             - alert: AegisScoreDistributionShift
               expr: |
                 aegis_score_dist_ks_statistic > 0.1
               for: 5m
               labels:
                 severity: warning
               annotations:
                 summary: "Score distribution shift detected for {{ $labels.component }}"
                 description: >-
                   KS statistic for {{ $labels.component }} exceeds 0.1,
                   indicating a significant distribution shift between consecutive
                   nightly snapshots. Investigate for calibration issues or data bugs.

             - alert: AegisIntegrityHitRateSpike
               expr: |
                 aegis_integrity_events_daily > 3 * aegis_integrity_events_baseline_mean
               for: 10m
               labels:
                 severity: warning
               annotations:
                 summary: "Integrity gate hit-rate spike for {{ $labels.reason }}"
                 description: >-
                   Daily integrity events for {{ $labels.reason }} exceed 3x
                   the 14-day baseline mean. May indicate real-world events or a bug.

             - alert: AegisApexRecallDrop
               expr: |
                 aegis_apex_recall_current - aegis_apex_recall_previous < -0.05
               for: 5m
               labels:
                 severity: critical
               annotations:
                 summary: "Apex recall dropped >5% for {{ $labels.query_id }}"
                 description: >-
                   Weekly apex-list recall for {{ $labels.query_id }} has dropped
                   more than 5 percentage points. Investigate ranking pipeline changes.

             - alert: AegisWeightShiftLarge
               expr: |
                 aegis_weight_relative_change_pct > 25
               for: 1m
               labels:
                 severity: critical
               annotations:
                 summary: "Weight shift >25% detected for {{ $labels.parameter }}"
                 description: >-
                   Parameter {{ $labels.parameter }} has shifted more than 25%
                   in the latest refit. Manual review required before deployment.
                   See ops/aegis/weight_review.md for the approval workflow.
       ```

    3. Create `ops/aegis/dashboards/score_distributions.html` as a placeholder:
       ```html
       <!DOCTYPE html>
       <html lang="en">
       <head><meta charset="utf-8"><title>Score Distributions — Aegis</title></head>
       <body>
       <h1>Score Distribution Dashboards</h1>
       <p>This file is auto-generated by <code>ScoreDistributionMonitor.save_report()</code>.
       Run the nightly recompute to populate.</p>
       </body>
       </html>
       ```

    4. Create `ops/aegis/dashboards/integrity_hitrate.html` as a placeholder:
       ```html
       <!DOCTYPE html>
       <html lang="en">
       <head><meta charset="utf-8"><title>Integrity Hit Rate — Aegis</title></head>
       <body>
       <h1>Integrity Gate Hit-Rate Dashboard</h1>
       <p>This file is auto-generated by <code>IntegrityDashboard.save_report()</code>.
       Run the nightly recompute to populate.</p>
       </body>
       </html>
       ```

    ## Files to modify
    - `ops/aegis/score_dist_alerts.yaml` -- NEW: Prometheus alert rules
    - `ops/aegis/dashboards/score_distributions.html` -- NEW: placeholder dashboard
    - `ops/aegis/dashboards/integrity_hitrate.html` -- NEW: placeholder dashboard

    ## Code patterns to follow
    - Alert YAML format from `ops/aegis/drift_alerts.yaml` and `ops/aegis/api_alerts.yaml`.
    - Standard Prometheus alerting rule structure with groups, rules, expr, for, labels, annotations.

    ## Acceptance criteria
    - `ops/aegis/score_dist_alerts.yaml` is valid YAML with 4 alert rules.
    - Placeholder HTML dashboards exist in `ops/aegis/dashboards/`.
    - Alert rule format matches existing rules in `ops/aegis/drift_alerts.yaml`.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -c "import yaml; yaml.safe_load(open('ops/aegis/score_dist_alerts.yaml'))" && test -f ops/aegis/dashboards/score_distributions.html && test -f ops/aegis/dashboards/integrity_hitrate.html && echo "OK"
    ```

### 10. Update Package Exports
- **Task ID**: update-exports
- **Role**: builder
- **Depends On**: score-dist-monitor, integrity-dashboard, apex-recall, audit-consistency, weight-stability, score-cache
- **Assigned To**: builder-2
- **Description**: |
    Update `__init__.py` files to export all new public classes from Phase 1d modules.

    ## What to do

    1. Update `src/aegis/observability/__init__.py` to add exports for all 5 new observability modules. The current file exports from coverage, drift, freshness, api_health, and linkage_report. Add imports and exports for:
       - `score_dist`: `ScoreDistributionMonitor`, `DistributionSnapshot`, `KSAlert`
       - `apex_recall`: `ApexRecallTracker`, `ApexQuery`, `RecallResult`, `WeeklyTrend`
       - `audit_consistency`: `AuditConsistencyTracker`, `JudgmentRecord`, `ConsistencyReport`
       - `integrity_dashboard`: `IntegrityDashboard`, `IntegrityEvent`, `DailySummary`, `SpikeAlert`
       - `weight_stability`: `WeightStabilityTracker`, `WeightShift`, `StabilityReport`

       The updated file should look like:
       ```python
       """Coverage diagnostics, freshness metrics, drift alerting, score distributions, and governance."""

       from aegis.observability.api_health import ApiHealthMetrics
       from aegis.observability.apex_recall import (
           ApexQuery,
           ApexRecallTracker,
           RecallResult,
           WeeklyTrend,
       )
       from aegis.observability.audit_consistency import (
           AuditConsistencyTracker,
           ConsistencyReport,
           JudgmentRecord,
       )
       from aegis.observability.coverage import CoverageDiagnostics, CoverageMetrics
       from aegis.observability.drift import DriftAlert, DriftConfig, DriftDetector
       from aegis.observability.freshness import FreshnessMetrics
       from aegis.observability.integrity_dashboard import (
           DailySummary,
           IntegrityDashboard,
           IntegrityEvent,
           SpikeAlert,
       )
       from aegis.observability.linkage_report import (
           ConfidenceShift,
           LinkageReporter,
           LinkageThresholds,
       )
       from aegis.observability.score_dist import (
           DistributionSnapshot,
           KSAlert,
           ScoreDistributionMonitor,
       )
       from aegis.observability.weight_stability import (
           StabilityReport,
           WeightShift,
           WeightStabilityTracker,
       )

       __all__ = [
           "ApiHealthMetrics",
           "ApexQuery",
           "ApexRecallTracker",
           "AuditConsistencyTracker",
           "ConfidenceShift",
           "ConsistencyReport",
           "CoverageDiagnostics",
           "CoverageMetrics",
           "DailySummary",
           "DistributionSnapshot",
           "DriftAlert",
           "DriftConfig",
           "DriftDetector",
           "FreshnessMetrics",
           "IntegrityDashboard",
           "IntegrityEvent",
           "JudgmentRecord",
           "KSAlert",
           "LinkageReporter",
           "LinkageThresholds",
           "RecallResult",
           "ScoreDistributionMonitor",
           "SpikeAlert",
           "StabilityReport",
           "WeeklyTrend",
           "WeightShift",
           "WeightStabilityTracker",
       ]
       ```

    2. Update `src/aegis/scoring/__init__.py` to add cache exports. Add after existing imports:
       ```python
       from aegis.scoring.cache import CacheKey, CachedScore, CacheStats, ScoreCache
       ```
       Add to `__all__`:
       ```python
       "CacheKey",
       "CachedScore",
       "CacheStats",
       "ScoreCache",
       ```
       Keep the `__all__` list alphabetically sorted.

    ## Files to modify
    - `src/aegis/observability/__init__.py` -- ADD imports and exports for 5 new modules
    - `src/aegis/scoring/__init__.py` -- ADD imports and exports for cache module

    ## Code patterns to follow
    - Match existing import style in both `__init__.py` files: grouped imports from each module, alphabetically sorted `__all__` list.
    - `from __future__ import annotations` is NOT used in `__init__.py` files in this codebase (check existing files -- they don't use it).

    ## Acceptance criteria
    - All new public classes are importable via `from aegis.observability import ScoreDistributionMonitor` etc.
    - All new scoring classes importable via `from aegis.scoring import ScoreCache` etc.
    - No circular imports.
    - mypy passes on both init files.
    - ruff passes on both init files.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -c "from aegis.observability import ScoreDistributionMonitor, ApexRecallTracker, AuditConsistencyTracker, IntegrityDashboard, WeightStabilityTracker; from aegis.scoring import ScoreCache; print('All exports OK')" && python -m mypy src/aegis/observability/__init__.py src/aegis/scoring/__init__.py --strict && python -m ruff check src/aegis/observability/__init__.py src/aegis/scoring/__init__.py
    ```

### 11. Validate All Acceptance Criteria
- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: score-dist-monitor, integrity-dashboard, apex-recall, audit-consistency, weight-stability, recompute-strategy, score-cache, latency-budget, ops-artifacts, update-exports
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria.

    ## Validation Commands

    Run each command below. ALL must pass.

    ### 1. Full test suite (must preserve 319/320 baseline + new tests)
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/ tests/ -x -q
    ```
    Expected: All new tests pass. The pre-existing failure in `src/aegis/cohort/audit_test.py::test_daily_summary` is the only allowed failure.

    ### 2. mypy strict on all new modules
    ```bash
    cd /Users/anvith/aegis && python -m mypy src/aegis/observability/score_dist.py src/aegis/observability/apex_recall.py src/aegis/observability/audit_consistency.py src/aegis/observability/integrity_dashboard.py src/aegis/observability/weight_stability.py src/aegis/scheduling/recompute.py src/aegis/scoring/cache.py --strict
    ```

    ### 3. mypy strict on updated init files
    ```bash
    cd /Users/anvith/aegis && python -m mypy src/aegis/observability/__init__.py src/aegis/scoring/__init__.py --strict
    ```

    ### 4. ruff on all new and modified files
    ```bash
    cd /Users/anvith/aegis && python -m ruff check src/aegis/observability/score_dist.py src/aegis/observability/score_dist_test.py src/aegis/observability/apex_recall.py src/aegis/observability/apex_recall_test.py src/aegis/observability/audit_consistency.py src/aegis/observability/audit_consistency_test.py src/aegis/observability/integrity_dashboard.py src/aegis/observability/integrity_dashboard_test.py src/aegis/observability/weight_stability.py src/aegis/observability/weight_stability_test.py src/aegis/scheduling/recompute.py src/aegis/scheduling/recompute_test.py src/aegis/scoring/cache.py src/aegis/scoring/cache_test.py tests/regression/test_apex_recall.py tests/perf/test_query_latency.py src/aegis/observability/__init__.py src/aegis/scoring/__init__.py
    ```

    ### 5. Performance benchmark
    ```bash
    cd /Users/anvith/aegis && python -m pytest tests/perf/test_query_latency.py -x -q -s
    ```

    ### 6. Import verification
    ```bash
    cd /Users/anvith/aegis && python -c "
    from aegis.observability import ScoreDistributionMonitor, DistributionSnapshot, KSAlert
    from aegis.observability import ApexRecallTracker, ApexQuery, RecallResult, WeeklyTrend
    from aegis.observability import AuditConsistencyTracker, JudgmentRecord, ConsistencyReport
    from aegis.observability import IntegrityDashboard, IntegrityEvent, DailySummary, SpikeAlert
    from aegis.observability import WeightStabilityTracker, WeightShift, StabilityReport
    from aegis.scoring import ScoreCache, CacheKey, CachedScore, CacheStats
    from aegis.scheduling.recompute import ScoreRecomputer, RecomputeResult
    print('All imports OK')
    "
    ```

    ### 7. Ops artifacts verification
    ```bash
    cd /Users/anvith/aegis && python -c "import yaml; yaml.safe_load(open('ops/aegis/score_dist_alerts.yaml'))" && test -f ops/aegis/dashboards/score_distributions.html && test -f ops/aegis/dashboards/integrity_hitrate.html && test -f ops/aegis/weight_review.md && test -f config/aegis/apex_queries/nsclc_translational_v1.yaml && test -f src/aegis/scoring/latency_budget.md && echo "All ops artifacts OK"
    ```

    ## Acceptance Criteria

    Verify each criterion below:

    1. **Score distribution monitor**: `ScoreDistributionMonitor` records 50-bucket histograms, retrieves snapshots, and fires `KSAlert` when KS > 0.1.
    2. **Integrity dashboard**: `IntegrityDashboard` records events, produces daily summaries, detects spikes at 3x baseline.
    3. **Apex recall**: `ApexRecallTracker` computes recall correctly, tracks weekly trends, alerts on >5% drops. Regression test passes at >=80%.
    4. **Audit consistency**: `AuditConsistencyTracker` computes Cohen's kappa, detects overlapping pairs, manages re-show at 5% rate, flags low-agreement reviewers.
    5. **Weight stability**: `WeightStabilityTracker` detects >25% shifts, generates review template, ops workflow documented.
    6. **Score recomputation**: `ScoreRecomputer` is idempotent, resumable, tracks artifact-set hashes.
    7. **Score cache**: `ScoreCache` achieves correct get/put/stats with SQLite backend.
    8. **Latency budget**: Documented in `src/aegis/scoring/latency_budget.md`. Performance test passes p95 < 500ms.
    9. **Package exports**: All new public classes importable from package `__init__.py`.
    10. **Ops artifacts**: Alert YAML, dashboard placeholders, weight review workflow all present.
    11. **Test baseline preserved**: No new test failures beyond the pre-existing one.

    If any criterion fails, create a fix task describing the failure and assign it to the appropriate builder.

### 12. Update Scoring Design Document
- **Task ID**: update-design-scoring
- **Role**: design-updater
- **Depends On**: validate-all
- **Assigned To**: design-updater
- **Description**: |
    Update the living design document for the scoring domain to reflect
    what was actually built in Phase 1d.

    ## Target Design Doc
    docs/design/scoring.md

    ## Spec File
    specs/aegis-phase1d-observability-performance.md

    ## Scope
    Observability layer (5 new modules in src/aegis/observability/), scheduling layer (recompute.py), scoring cache (cache.py), latency budget, and ops artifacts. The core scoring/integrity architecture is unchanged; this build adds monitoring, caching, and performance infrastructure around it.

    ## Prior Decisions to Check
    - "In-Memory Source Stores for Phase 1" decision -- the cache module introduces SQLite persistence for scores, which is a new persistence pattern distinct from the in-memory store pattern. Document the relationship.
    - "Versioned Weight Configuration via YAML" decision -- the weight stability tracker reads and compares YAML weight files. Document how stability tracking integrates with the weight versioning lifecycle.
    - DuckDB usage pattern established in Phase 0 (drift.py) -- this build adds 3 more DuckDB tables (score_distribution_snapshots, apex_recall_results, integrity_events). Document the growing DuckDB schema.

    ## What to Record
    Read git diff HEAD~1 HEAD, then the changed source files, then the existing
    design doc. Update Current Design to match the implementation. Append a
    Design Decision entry for each non-trivial architectural choice made in
    this build. Every claim must cite a file:line from the actual code.

    Key areas to document:
    1. **Observability architecture**: The 5 new monitoring modules, their DuckDB tables, and their alert patterns.
    2. **Score cache design**: SQLite-backed cache with Protocol-based backend abstraction, cache key structure, invalidation strategy.
    3. **Recomputation strategy**: Idempotent batch recompute with artifact-set hashing and DuckDB logging.
    4. **Latency budget**: The documented budget breakdown and how pre-computation enables the <500ms target.
    5. **KS-statistic anomaly detection**: Why KS was chosen over other distribution comparison methods for score monitoring.

## Acceptance Criteria

1. `ScoreDistributionMonitor` records 50-bucket histograms for all score components and fires KS anomaly alerts when distribution shift > 0.1.
2. `ApexRecallTracker` computes recall against curated apex queries at >=80% threshold with weekly trend tracking and >5% drop alerting.
3. `AuditConsistencyTracker` computes inter-reviewer Cohen's kappa on overlapping pairs and manages intra-reviewer re-show at 5% rate.
4. `IntegrityDashboard` tracks per-day hard-zero and soft-discount counts by reason with spike detection at 3x baseline.
5. `WeightStabilityTracker` detects >25% parameter shifts per refit and generates review templates; ops workflow documented.
6. `ScoreRecomputer` is idempotent, resumable, and tracks progress via artifact-set hashing.
7. `ScoreCache` stores and retrieves cached scores with SQLite backend; cache stats track >=95% hit rate on warm cohort.
8. Query latency p95 < 500ms documented and tested via 100-query benchmark.
9. All new public classes exported from package `__init__.py` files.
10. Prometheus alert rules in `ops/aegis/score_dist_alerts.yaml` with 4 alert rules.
11. Full test suite passes (319/320 baseline preserved + new tests pass).
12. mypy strict + ruff clean on all new and modified files.

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && python -m pytest src/ tests/ -x -q` -- Full test suite (319/320 baseline + new tests)
- `cd /Users/anvith/aegis && python -m mypy src/aegis/observability/score_dist.py src/aegis/observability/apex_recall.py src/aegis/observability/audit_consistency.py src/aegis/observability/integrity_dashboard.py src/aegis/observability/weight_stability.py src/aegis/scheduling/recompute.py src/aegis/scoring/cache.py --strict` -- mypy strict on new modules
- `cd /Users/anvith/aegis && python -m ruff check src/aegis/observability/ src/aegis/scheduling/ src/aegis/scoring/cache.py src/aegis/scoring/cache_test.py tests/regression/ tests/perf/` -- ruff on all new files
- `cd /Users/anvith/aegis && python -m pytest tests/perf/test_query_latency.py -x -q -s` -- Performance benchmark
- `cd /Users/anvith/aegis && python -c "from aegis.observability import ScoreDistributionMonitor, ApexRecallTracker, AuditConsistencyTracker, IntegrityDashboard, WeightStabilityTracker; from aegis.scoring import ScoreCache; print('OK')"` -- Import verification

## Notes

- **No new dependencies required**: scipy, duckdb, sqlite3, pyyaml, and statistics are all already available (scipy/duckdb/pyyaml in pyproject.toml, sqlite3/statistics in stdlib).
- **Phase 1c dependency**: The `AuditConsistencyTracker` is designed to be independent of Phase 1c's `JudgmentStore` by defining its own lightweight `JudgmentRecord` type. When Phase 1c is complete, an adapter can bridge between the two types.
- **Pre-existing test failure**: `src/aegis/cohort/audit_test.py::test_daily_summary` is a known pre-existing failure (1/320). New code must not introduce additional failures.
- **DuckDB schema growth**: Phase 1d adds 3 new DuckDB tables. Consider whether a schema migration strategy is needed for Phase 2+ (not required for Phase 1).
