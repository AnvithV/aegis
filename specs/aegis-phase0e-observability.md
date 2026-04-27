# Plan: Phase 0e — Observability

> **Status:** Complete -- all acceptance criteria verified, all tests passing, mypy clean, ruff clean.
> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase0e-observability.md` — do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build the observability layer for Aegis Phase 0: coverage diagnostics dashboard, identity-linkage confidence reporting, ingestion freshness and lag metrics, source-API failure rate dashboards, and per-source artifact count drift alerts. This layer provides visibility into the health and quality of the data pipeline built in Phases 0a–0d, ensuring coverage mandates (program overview §12), refresh cadence promises (§13), and data quality thresholds are monitored and enforced.

All 5 observability tasks are independent — two builders can work on them in parallel with no inter-task dependencies.

## Objective

When this plan is complete:
- Per-source coverage diagnostics report % of candidates with strong-key, probabilistic linkage, per-source artifacts, and thin-record flags — with counts and percentiles, not just averages
- Linkage confidence is surfaced as a top-level field on every candidate and API response; candidates below 0.5 are held out of rankings
- Per-source ingestion freshness metrics emit in Prometheus exposition format: time since last pull, publication-to-ingestion lag, gap counts
- Per-API call health metrics track success/failure, latency percentiles, and rate-limit hits with HTTP error vs parse error distinction
- Per-source artifact count drift alerts trigger on >30% day-over-day drops using 14-day rolling z-score baseline

## Relevant Files

- `src/aegis/observability/coverage.py` — Coverage diagnostics
- `src/aegis/observability/coverage_dashboard.html` — Static HTML coverage report
- `src/aegis/observability/linkage_report.py` — Linkage confidence reporting
- `src/aegis/observability/freshness.py` — Ingestion freshness metrics
- `src/aegis/observability/api_health.py` — Source-API failure rate metrics
- `src/aegis/observability/drift.py` — Artifact count drift detection
- `ops/aegis/api_alerts.yaml` — API health alert rules
- `ops/aegis/drift_alerts.yaml` — Drift detection alert rules
- `src/aegis/storage/candidate_store.py` — Candidate store from Phase 0a (import, do not modify)
- `src/aegis/sources/cursor.py` — Cursor manager from Phase 0b (import, do not modify)
- `pyproject.toml` — prometheus-client already in dependencies

### New Files

- `src/aegis/observability/coverage.py`
- `src/aegis/observability/coverage_dashboard.html`
- `src/aegis/observability/coverage_test.py`
- `src/aegis/observability/linkage_report.py`
- `src/aegis/observability/linkage_test.py`
- `src/aegis/observability/freshness.py`
- `src/aegis/observability/freshness_test.py`
- `src/aegis/observability/api_health.py`
- `src/aegis/observability/api_health_test.py`
- `src/aegis/observability/drift.py`
- `src/aegis/observability/drift_test.py`
- `ops/aegis/api_alerts.yaml`
- `ops/aegis/drift_alerts.yaml`

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Coverage diagnostics dashboard, linkage confidence reporting
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Ingestion freshness metrics, API health dashboards, drift alerts
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

### 1. Coverage Diagnostics Dashboard

- **Task ID**: coverage-dashboard
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Build per-source coverage diagnostics for the NSCLC translational seed cohort: percentage of candidates with strong-key, probabilistic linkage, per-source artifacts, and thin-record flags. Coverage is a first-class output per program overview §12.

    ## What to do

    1. Create `src/aegis/observability/coverage.py` with:

       - `CoverageMetrics` — frozen Pydantic BaseModel:
         - `total_candidates: int`
         - `strong_key_pct: float` (% with ORCID or eRA Commons)
         - `probabilistic_linkage_pct: float` (% with confident probabilistic link, ≥0.7)
         - `per_source_pct: dict[str, float]` (% with artifacts from each source: pubmed, reporter, ctgov)
         - `thin_record_pct: float` (% with <3 artifacts total)
         - `linkage_confidence_p5: float` (5th percentile linkage confidence)
         - `linkage_confidence_p50: float` (50th percentile)
         - `linkage_confidence_p95: float` (95th percentile)

       - `CoverageDiagnostics`:
         - `__init__(self, store: CandidateStore)`
         - `compute(self, cohort_candidates: list[str] | None = None) -> CoverageMetrics`:
           1. Load all candidates (or filtered by cohort list)
           2. Compute all percentages and percentiles
           3. Report counts AND percentiles, not just averages (the 5th-percentile linkage-confidence is more informative than the mean)
         - `generate_html_report(self, metrics: CoverageMetrics) -> str`:
           Returns static HTML with per-source breakdowns, histograms of linkage confidence, and thin-record list
         - `save_report(self, metrics: CoverageMetrics, path: str = "src/aegis/observability/coverage_dashboard.html") -> None`:
           Writes the HTML report to disk
         - `compare(self, current: CoverageMetrics, previous: CoverageMetrics) -> dict[str, float]`:
           Returns delta dict for drift tracking between runs

    2. Create `src/aegis/observability/coverage_dashboard.html` — a template HTML file that gets populated by `generate_html_report`. Include:
       - Summary table with all metrics
       - Per-source artifact coverage bar chart (simple HTML/CSS, no JS framework needed)
       - Linkage confidence distribution (histogram rendered as HTML table)

    3. Create `src/aegis/observability/coverage_test.py` with:

       - `test_compute_all_metrics`: Create 10 candidates with varying attributes, compute metrics, assert all fields populated
       - `test_strong_key_percentage`: 4 of 10 candidates have ORCID → assert strong_key_pct ≈ 40%
       - `test_thin_record_detection`: 2 of 10 candidates have <3 artifacts → assert thin_record_pct ≈ 20%
       - `test_percentiles_correct`: Create candidates with known linkage confidences, assert p5/p50/p95 correct
       - `test_html_report_generated`: Generate report, assert non-empty HTML string with expected sections
       - `test_compare_detects_drift`: Compare two metrics objects with different values, assert deltas correct
       - `test_regression_strong_key_coverage`: Assert strong-key coverage ≥40% on fixture cohort (realistic ceiling)

    4. Update `src/aegis/observability/__init__.py` to export `CoverageDiagnostics`, `CoverageMetrics`

    ## Files to create
    - `src/aegis/observability/coverage.py`
    - `src/aegis/observability/coverage_dashboard.html`
    - `src/aegis/observability/coverage_test.py`

    ## Files to modify
    - `src/aegis/observability/__init__.py` — add exports

    ## Code patterns to follow
    - Import `CandidateStore` from `aegis.storage`
    - Pydantic v2 frozen BaseModel
    - `from __future__ import annotations`
    - `statistics.quantiles()` for percentile computation
    - Simple HTML generation (f-strings or template strings, no Jinja2 dependency needed)

    ## Acceptance criteria
    - Dashboard renders for seed cohort with all per-source breakdowns
    - Reports counts AND percentiles, not just averages
    - Strong-key coverage regression test asserts ≥40% on cohort
    - HTML report is re-runnable on every ingestion pass
    - Historical reports persist for drift tracking
    - All tests pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/coverage_test.py -v && uv run mypy src/aegis/observability/coverage.py && uv run ruff check src/aegis/observability/coverage.py
    ```

### 2. Identity-Linkage Confidence Reporting

- **Task ID**: linkage-reporting
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Surface linkage confidence as a top-level field on every candidate record and on every API response. Below 0.7, flag in evidence trails. Below 0.5, hold out of rankings and queue for HITL review. Produce a daily report of confidence shifts.

    ## What to do

    1. Create `src/aegis/observability/linkage_report.py` with:

       - `LinkageThresholds` — frozen Pydantic BaseModel:
         - `flag_threshold: float = 0.7` (below this, flag as "low-confidence linkage" in evidence trail)
         - `holdout_threshold: float = 0.5` (below this, hold out of rankings, queue for HITL)

       - `ConfidenceShift` — frozen Pydantic BaseModel:
         - `candidate_uuid: str`
         - `previous_confidence: float`
         - `current_confidence: float`
         - `delta: float`
         - `crossed_threshold: str | None` (e.g., "dropped_below_flag", "dropped_below_holdout", "recovered_above_flag")

       - `LinkageReporter`:
         - `__init__(self, store: CandidateStore, thresholds: LinkageThresholds | None = None)`
         - `classify_candidate(self, candidate_uuid: str) -> str`:
           Returns `"confident"` (≥0.7), `"low_confidence"` (0.5–0.7), or `"holdout"` (<0.5)
         - `get_holdouts(self) -> list[str]`:
           Returns candidate UUIDs with confidence < holdout_threshold
         - `get_flagged(self) -> list[str]`:
           Returns candidate UUIDs with confidence < flag_threshold but ≥ holdout_threshold
         - `daily_shift_report(self, previous_snapshot: dict[str, float]) -> list[ConfidenceShift]`:
           Compare current confidences to previous snapshot, return candidates whose confidence shifted by >0.1
         - `save_snapshot(self, path: str) -> dict[str, float]`:
           Save current confidence snapshot as JSON for next comparison

    2. Ensure linkage_confidence is already a top-level field on `Candidate` (it is, from Phase 0a schema). Add a note in the reporter that API responses MUST include this field.

    3. Create `src/aegis/observability/linkage_test.py` with:

       - `test_classify_confident`: Candidate with confidence 0.85 → "confident"
       - `test_classify_low_confidence`: Confidence 0.6 → "low_confidence"
       - `test_classify_holdout`: Confidence 0.3 → "holdout"
       - `test_get_holdouts`: 2 of 5 candidates below 0.5, assert holdouts list has 2
       - `test_get_flagged`: 1 of 5 between 0.5 and 0.7, assert flagged list has 1
       - `test_daily_shift_report`: Set previous snapshot, change 2 candidates' confidence by >0.1, assert 2 shifts reported
       - `test_threshold_crossing_detected`: Candidate drops from 0.75 to 0.45, assert `crossed_threshold="dropped_below_holdout"`

    4. Update `src/aegis/observability/__init__.py` to export `LinkageReporter`, `LinkageThresholds`, `ConfidenceShift`

    ## Files to create
    - `src/aegis/observability/linkage_report.py`
    - `src/aegis/observability/linkage_test.py`

    ## Files to modify
    - `src/aegis/observability/__init__.py` — add exports

    ## Code patterns to follow
    - Import `CandidateStore` from `aegis.storage`
    - Pydantic v2 frozen BaseModel
    - `from __future__ import annotations`
    - JSON for snapshot persistence

    ## Acceptance criteria
    - Linkage confidence is classified into confident/low_confidence/holdout
    - Below 0.5 candidates are held out of rankings
    - Below 0.7 candidates are flagged in evidence trails
    - Daily shift report detects >0.1 confidence changes
    - Threshold crossings are identified
    - All tests pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/linkage_test.py -v && uv run mypy src/aegis/observability/linkage_report.py && uv run ruff check src/aegis/observability/linkage_report.py
    ```

### 3. Ingestion Freshness and Lag Metrics

- **Task ID**: freshness-metrics
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Emit per-source ingestion freshness metrics in Prometheus exposition format: time since last successful pull, lag between artifact publication date and ingestion date, and gap counts (artifacts referenced but not yet ingested).

    ## What to do

    1. Create `src/aegis/observability/freshness.py` with:

       - `FreshnessMetrics`:
         - `__init__(self, cursor_manager: CursorManager | None = None)`:
           Initialize Prometheus metrics using `prometheus_client`:
           - `aegis_ingestion_last_success_seconds` — Gauge, labels: `["source"]` — seconds since last successful pull
           - `aegis_ingestion_lag_seconds` — Histogram, labels: `["source"]` — publication-to-ingestion lag in seconds
           - `aegis_ingestion_gap_count` — Gauge, labels: `["source"]` — count of referenced but un-ingested artifacts
           - `aegis_ingestion_records_total` — Counter, labels: `["source"]` — total records ingested per source

         - `record_success(self, source: str) -> None`:
           Update `last_success_seconds` gauge for the source
         - `record_lag(self, source: str, publication_date: datetime, ingestion_date: datetime) -> None`:
           Observe the lag into the histogram
         - `record_gap(self, source: str, gap_count: int) -> None`:
           Set the gap gauge for the source
         - `record_ingested(self, source: str, count: int) -> None`:
           Increment the counter

         - `get_freshness_summary(self) -> dict[str, dict[str, float]]`:
           Returns `{source: {"last_success_age_s": ..., "avg_lag_s": ..., "gap_count": ..., "total_ingested": ...}}`

         - `expose_metrics(self) -> str`:
           Returns Prometheus exposition format text (using `prometheus_client.generate_latest()`)

       - Per-source SLOs documented as part of metric descriptions:
         - PubMed: refresh within 24h of new EDAT
         - RePORTER: refresh within 48h of new award_notice_date
         - CT.gov: refresh within 24h of new LastUpdatePostDate

    2. Create `src/aegis/observability/freshness_test.py` with:

       - `test_record_success_updates_gauge`: Record a success, assert gauge value is recent (< 10 seconds ago)
       - `test_record_lag_observes_histogram`: Record a lag of 3600s, assert histogram has 1 observation
       - `test_record_gap_updates_gauge`: Set gap count to 5, assert gauge reads 5
       - `test_expose_metrics_prometheus_format`: Call expose_metrics, assert output contains `aegis_ingestion_` metric names
       - `test_freshness_summary`: Record data for 3 sources, get summary, assert all 3 present
       - `test_freshness_lag_increases_on_pause`: Record a success, wait (simulate), assert freshness age increases

    3. Update `src/aegis/observability/__init__.py` to export `FreshnessMetrics`

    ## Files to create
    - `src/aegis/observability/freshness.py`
    - `src/aegis/observability/freshness_test.py`

    ## Files to modify
    - `src/aegis/observability/__init__.py` — add exports

    ## Code patterns to follow
    - `prometheus_client` for metrics (already in deps: `prometheus-client>=0.20`)
    - Prometheus naming convention: `aegis_ingestion_*`
    - Labels: `["source"]` for per-source metrics
    - `from __future__ import annotations`
    - Pydantic v2 frozen BaseModel where applicable

    ## Acceptance criteria
    - Metrics emitted in Prometheus exposition format
    - Per-source freshness, lag, gaps, and total counts tracked
    - Metrics populate within 10 minutes of an ingestion run (tested with synthetic data)
    - SLOs documented per source
    - All tests pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/freshness_test.py -v && uv run mypy src/aegis/observability/freshness.py && uv run ruff check src/aegis/observability/freshness.py
    ```

### 4. Source-API Failure Rate Dashboards

- **Task ID**: api-health-dashboard
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Track per-API call success/failure, latency percentiles, and rate-limit hits. Distinguish HTTP errors (4xx/5xx/timeout) from parse errors (schema drift). Create alert rules.

    ## What to do

    1. Create `src/aegis/observability/api_health.py` with:

       - `ApiHealthMetrics`:
         - `__init__(self)`:
           Initialize Prometheus metrics:
           - `aegis_api_requests_total` — Counter, labels: `["source", "status"]` where status is `"success"`, `"http_4xx"`, `"http_5xx"`, `"timeout"`, `"parse_error"`
           - `aegis_api_latency_seconds` — Histogram, labels: `["source"]` — request latency with buckets: [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
           - `aegis_api_rate_limit_hits_total` — Counter, labels: `["source"]` — 429 responses specifically
           - `aegis_api_parse_errors_total` — Counter, labels: `["source"]` — schema drift / parsing failures

         - `record_request(self, source: str, status: str, latency_seconds: float) -> None`:
           Increment request counter and observe latency
         - `record_rate_limit_hit(self, source: str) -> None`:
           Increment rate-limit counter
         - `record_parse_error(self, source: str, error_detail: str) -> None`:
           Increment parse error counter, log the detail

         - `get_health_summary(self) -> dict[str, dict[str, Any]]`:
           Returns per-source summary: `{source: {"total_requests": ..., "success_rate": ..., "p50_latency": ..., "p95_latency": ..., "p99_latency": ..., "rate_limit_hits": ..., "parse_errors": ...}}`

         - `expose_metrics(self) -> str`:
           Returns Prometheus exposition format text

    2. Create `ops/aegis/api_alerts.yaml`:
       ```yaml
       # API Health Alert Rules for Aegis ingestion pipeline
       groups:
         - name: aegis_api_health
           rules:
             - alert: AegisApiHighErrorRate
               expr: rate(aegis_api_requests_total{status=~"http_5xx|timeout"}[5m]) / rate(aegis_api_requests_total[5m]) > 0.1
               for: 10m
               labels:
                 severity: warning
               annotations:
                 summary: "High error rate on {{ $labels.source }} API"
                 description: "{{ $labels.source }} has >10% error rate over 5 minutes"

             - alert: AegisApiRateLimited
               expr: increase(aegis_api_rate_limit_hits_total[5m]) > 10
               for: 5m
               labels:
                 severity: warning
               annotations:
                 summary: "Rate limiting detected on {{ $labels.source }}"
                 description: "{{ $labels.source }} hit rate limits >10 times in 5 minutes"

             - alert: AegisApiSchemaBreak
               expr: increase(aegis_api_parse_errors_total[1h]) > 5
               for: 15m
               labels:
                 severity: critical
               annotations:
                 summary: "Schema drift detected on {{ $labels.source }}"
                 description: "{{ $labels.source }} has >5 parse errors in 1 hour — possible upstream schema change"

             - alert: AegisApiHighLatency
               expr: histogram_quantile(0.95, rate(aegis_api_latency_seconds_bucket[5m])) > 5
               for: 10m
               labels:
                 severity: warning
               annotations:
                 summary: "High p95 latency on {{ $labels.source }} API"
                 description: "{{ $labels.source }} p95 latency exceeds 5 seconds"
       ```

    3. Create `src/aegis/observability/api_health_test.py` with:

       - `test_record_success`: Record a successful request, assert counter incremented
       - `test_record_http_error`: Record 5xx, assert status="http_5xx" counter
       - `test_record_parse_error`: Record parse error, assert parse_error counter incremented
       - `test_record_rate_limit`: Record rate limit hit, assert rate_limit counter incremented
       - `test_latency_histogram`: Record 10 requests with varying latencies, assert histogram populated
       - `test_health_summary`: Record mixed requests across 3 sources, get summary, assert all sources present
       - `test_prometheus_format`: Expose metrics, assert valid Prometheus format with expected metric names
       - `test_http_vs_parse_distinction`: Record HTTP 500 and parse error separately, assert distinct counters

    4. Update `src/aegis/observability/__init__.py` to export `ApiHealthMetrics`

    ## Files to create
    - `src/aegis/observability/api_health.py`
    - `src/aegis/observability/api_health_test.py`
    - `ops/aegis/api_alerts.yaml`

    ## Files to modify
    - `src/aegis/observability/__init__.py` — add exports

    ## Code patterns to follow
    - `prometheus_client` for metrics
    - Prometheus naming convention: `aegis_api_*`
    - Labels: `["source", "status"]` for request counts
    - Alert rules in Prometheus alerting format (YAML)
    - `from __future__ import annotations`

    ## Acceptance criteria
    - Per-API success/failure, latency, rate-limit, and parse-error metrics tracked
    - HTTP errors distinguished from parse errors in metrics
    - Alert rules cover: high error rate, rate limiting, schema drift, high latency
    - Metrics expose in Prometheus format
    - All tests pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/api_health_test.py -v && uv run mypy src/aegis/observability/api_health.py && uv run ruff check src/aegis/observability/api_health.py && ls -la /Users/anvith/aegis/ops/aegis/api_alerts.yaml
    ```

### 5. Per-Source Artifact Count Drift Alerts

- **Task ID**: drift-alerts
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Implement per-source artifact-count drift detection with anomaly detection on day-over-day deltas. A 30% drop in ingestion volume should trigger an alert. Uses a 14-day rolling window baseline with configurable z-score threshold.

    ## What to do

    1. Create `src/aegis/observability/drift.py` with:

       - `DriftConfig` — frozen Pydantic BaseModel:
         - `window_days: int = 14` (rolling baseline window)
         - `z_score_threshold: float = 2.0` (alert threshold)
         - `min_drop_pct: float = 0.3` (30% drop triggers alert regardless of z-score)

       - `DailyCount` — frozen Pydantic BaseModel:
         - `source: str`
         - `date: date`
         - `artifact_count: int`

       - `DriftAlert` — frozen Pydantic BaseModel:
         - `alert_id: str` (UUID)
         - `source: str`
         - `date: date`
         - `current_count: int`
         - `baseline_mean: float`
         - `baseline_stddev: float`
         - `z_score: float`
         - `drop_pct: float`
         - `severity: str` (e.g., "warning", "critical")
         - `message: str`

       - `DriftDetector`:
         - `__init__(self, db_path: str = "aegis.duckdb", config: DriftConfig | None = None)`:
           Initialize with DuckDB for daily count persistence
         - `record_daily_count(self, source: str, date: date, count: int) -> None`:
           Persist daily artifact count
         - `check_drift(self, source: str, date: date) -> DriftAlert | None`:
           1. Load last `window_days` daily counts for this source
           2. Compute baseline mean and stddev
           3. Compute z-score for today's count: `z = (mean - count) / stddev` (negative = drop)
           4. Compute drop_pct: `(mean - count) / mean`
           5. If z_score > threshold OR drop_pct > min_drop_pct → create and return DriftAlert
           6. Otherwise return None
         - `check_all_sources(self, date: date) -> list[DriftAlert]`:
           Check drift for all sources with recorded data
         - `get_baseline(self, source: str, end_date: date) -> tuple[float, float]`:
           Returns (mean, stddev) of daily counts over the rolling window

       - Daily counts DDL:
         ```sql
         CREATE TABLE IF NOT EXISTS daily_artifact_counts (
             source TEXT NOT NULL,
             date DATE NOT NULL,
             artifact_count INTEGER NOT NULL,
             PRIMARY KEY (source, date)
         );
         ```

    2. Create `ops/aegis/drift_alerts.yaml`:
       ```yaml
       # Drift Alert Rules for Aegis ingestion pipeline
       groups:
         - name: aegis_drift
           rules:
             - alert: AegisIngestionDrop
               expr: aegis_drift_drop_pct > 0.3
               for: 0m
               labels:
                 severity: critical
               annotations:
                 summary: "Ingestion volume drop >30% on {{ $labels.source }}"
                 description: "{{ $labels.source }} daily artifact count dropped {{ $value }}% vs 14-day baseline"

             - alert: AegisIngestionAnomaly
               expr: aegis_drift_z_score > 2.0
               for: 0m
               labels:
                 severity: warning
               annotations:
                 summary: "Ingestion volume anomaly on {{ $labels.source }}"
                 description: "{{ $labels.source }} daily count z-score {{ $value }} exceeds threshold"
       ```

    3. Create `src/aegis/observability/drift_test.py` with:

       - `test_baseline_computation`: Record 14 days of data (100 ± 10 per day), compute baseline, assert mean ≈ 100 and stddev ≈ 10
       - `test_no_drift_normal_variation`: Today's count is 95 (within normal range), assert no alert
       - `test_drift_30pct_drop`: Today's count is 60 (40% drop from mean of 100), assert alert with severity "critical"
       - `test_drift_z_score_alert`: Today's count is 3 stddev below mean, assert alert
       - `test_no_data_no_alert`: No historical data for a source, assert no alert (graceful handling)
       - `test_multiple_sources`: Record data for 3 sources, one has drift, assert only 1 alert
       - `test_idempotent_daily_record`: Record same source+date twice, assert latest count wins (upsert)

    4. Update `src/aegis/observability/__init__.py` to export `DriftDetector`, `DriftAlert`, `DriftConfig`

    ## Files to create
    - `src/aegis/observability/drift.py`
    - `src/aegis/observability/drift_test.py`
    - `ops/aegis/drift_alerts.yaml`

    ## Files to modify
    - `src/aegis/observability/__init__.py` — add exports

    ## Code patterns to follow
    - DuckDB for daily count persistence
    - `statistics.mean()` and `statistics.stdev()` for baseline computation
    - Pydantic v2 frozen BaseModel
    - `from __future__ import annotations`
    - `tmp_path` fixture for test isolation

    ## Acceptance criteria
    - 14-day rolling baseline computed correctly
    - 30% drop triggers critical alert
    - Z-score > 2.0 triggers warning alert
    - Graceful handling when insufficient historical data
    - Alert rules defined in Prometheus format
    - All tests pass

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/drift_test.py -v && uv run mypy src/aegis/observability/drift.py && uv run ruff check src/aegis/observability/drift.py && ls -la /Users/anvith/aegis/ops/aegis/drift_alerts.yaml
    ```

### 6. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: coverage-dashboard, linkage-reporting, freshness-metrics, api-health-dashboard, drift-alerts
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the observability layer.

    ## Validation Commands

    1. Verify all observability modules import:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.observability.coverage import CoverageDiagnostics, CoverageMetrics
    from aegis.observability.linkage_report import LinkageReporter, LinkageThresholds, ConfidenceShift
    from aegis.observability.freshness import FreshnessMetrics
    from aegis.observability.api_health import ApiHealthMetrics
    from aegis.observability.drift import DriftDetector, DriftAlert, DriftConfig
    print('All observability modules import OK')
    "
    ```

    2. Run all observability tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/observability/ -v
    ```

    3. Run mypy on observability module:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/observability/
    ```

    4. Run ruff on observability module:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/observability/
    ```

    5. Verify alert rule files exist:
    ```bash
    ls -la /Users/anvith/aegis/ops/aegis/api_alerts.yaml
    ls -la /Users/anvith/aegis/ops/aegis/drift_alerts.yaml
    ```

    6. Verify coverage dashboard HTML template exists:
    ```bash
    ls -la /Users/anvith/aegis/src/aegis/observability/coverage_dashboard.html
    ```

    7. Verify Prometheus metrics format:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.observability.freshness import FreshnessMetrics
    fm = FreshnessMetrics()
    fm.record_success('pubmed')
    output = fm.expose_metrics()
    assert 'aegis_ingestion_last_success_seconds' in output, 'Missing freshness metric'
    print('Prometheus format OK')
    "
    ```

    ## Acceptance Criteria
    - All 5 observability modules import without errors
    - All tests pass
    - mypy strict mode passes
    - ruff passes
    - Alert rule files exist
    - Prometheus metrics expose correctly

## Acceptance Criteria

- Coverage diagnostics report per-source breakdowns with counts AND percentiles
- Strong-key coverage regression test gates at ≥40%
- Linkage confidence surfaced on every candidate; <0.5 held out of rankings; <0.7 flagged
- Daily confidence-shift report detects >0.1 changes
- Ingestion freshness metrics emit in Prometheus exposition format with per-source SLOs
- API health metrics distinguish HTTP errors from parse errors (schema drift)
- API alert rules cover: high error rate, rate limiting, schema drift, high latency
- Drift detection uses 14-day rolling z-score baseline
- 30% artifact-count drop triggers critical alert
- All observability tests pass: `uv run pytest src/aegis/observability/ -v`
- mypy strict mode passes: `uv run mypy src/aegis/observability/`
- ruff passes: `uv run ruff check src/aegis/observability/`

## Validation Commands

- `cd /Users/anvith/aegis && uv run pytest src/aegis/observability/ -v` — Run all observability tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/observability/` — Type-check observability module
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/observability/` — Lint observability module
- `cd /Users/anvith/aegis && uv run python -c "from aegis.observability.coverage import CoverageDiagnostics; print('OK')"` — Verify coverage import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.observability.linkage_report import LinkageReporter; print('OK')"` — Verify linkage import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.observability.freshness import FreshnessMetrics; print('OK')"` — Verify freshness import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.observability.api_health import ApiHealthMetrics; print('OK')"` — Verify API health import
- `cd /Users/anvith/aegis && uv run python -c "from aegis.observability.drift import DriftDetector; print('OK')"` — Verify drift import

## Notes

- All 5 observability tasks are independent — two builders work in parallel with no inter-task dependencies.
- Prometheus metrics shape is fixed now to avoid relabeling later, even though no scraping infrastructure is needed for Phase 0.
- Coverage is a first-class output per program overview §12 — it must be reported alongside scores.
- The 5th-percentile linkage confidence is more informative than the mean — always report percentiles.
- Threshold values for linkage confidence are tunable per deployment; defaults are documented in the program overview.
- Drift detection is more important than absolute volume — a healthy ingestion can still drift if upstream changes data semantics.
- Quarterly review of alert thresholds is recommended (not automated in Phase 0).
- Rate-limit-hit counter is critical because NCBI has tightened limits historically; early signal prevents data loss.

## Build Evidence

**Date**: 2026-04-25
**Spec Updater**: spec-updater

### Validation Commands

| Command | Result |
|---------|--------|
| `uv run pytest src/aegis/observability/ -v` | PASS -- 37 tests passed in 0.65s |
| `uv run mypy src/aegis/observability/` | PASS -- no issues found in 11 source files |
| `uv run ruff check src/aegis/observability/` | PASS -- All checks passed |
| `ls -la ops/aegis/api_alerts.yaml` | PASS -- file exists (1828 bytes) |
| `ls -la ops/aegis/drift_alerts.yaml` | PASS -- file exists (1084 bytes) |
| `ls -la src/aegis/observability/coverage_dashboard.html` | PASS -- file exists (1213 bytes) |

### Test Breakdown

| Test File | Tests | Result |
|-----------|-------|--------|
| `api_health_test.py` | 8 | PASS |
| `coverage_test.py` | 7 | PASS |
| `drift_test.py` | 7 | PASS |
| `freshness_test.py` | 6 | PASS |
| `linkage_test.py` | 9 | PASS |
| **Total** | **37** | **PASS** |

### Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Coverage diagnostics report per-source breakdowns with counts AND percentiles | PASS | `CoverageMetrics` fields include `per_source_pct`, `linkage_confidence_p5`, `linkage_confidence_p50`, `linkage_confidence_p95` |
| Strong-key coverage regression test gates at >=40% | PASS | `test_regression_strong_key_coverage` in coverage_test.py asserts >=40% |
| Linkage confidence surfaced on every candidate; <0.5 held out; <0.7 flagged | PASS | `LinkageThresholds(flag_threshold=0.7, holdout_threshold=0.5)`; classify_candidate returns "confident"/"low_confidence"/"holdout" |
| Daily confidence-shift report detects >0.1 changes | PASS | `test_daily_shift_report` and `test_threshold_crossing_detected` pass |
| Ingestion freshness metrics emit in Prometheus exposition format | PASS | `expose_metrics()` returns valid Prometheus text with `aegis_ingestion_last_success_seconds`, `aegis_ingestion_lag_seconds`, `aegis_ingestion_gap_count`, `aegis_ingestion_records_total` |
| API health metrics distinguish HTTP errors from parse errors | PASS | Separate counters: `aegis_api_requests_total{status="http_5xx"}` vs `aegis_api_parse_errors_total`; `test_http_vs_parse_distinction` passes |
| API alert rules cover: high error rate, rate limiting, schema drift, high latency | PASS | `ops/aegis/api_alerts.yaml` contains: AegisApiHighErrorRate, AegisApiRateLimited, AegisApiSchemaBreak, AegisApiHighLatency |
| Drift detection uses 14-day rolling z-score baseline | PASS | `DriftConfig(window_days=14, z_score_threshold=2.0)`; `test_baseline_computation` passes |
| 30% artifact-count drop triggers critical alert | PASS | `DriftConfig(min_drop_pct=0.3)`; `test_drift_30pct_drop` passes with severity "critical" |
| All tests pass, mypy clean, ruff clean | PASS | 37/37 tests pass, mypy 0 issues, ruff all checks passed |
