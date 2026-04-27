# Plan: Phase 1c — Audit Harness, Plackett-Luce Weight Learning, Score Variance, and Error Handling

> **Status:** COMPLETE (2026-04-26)
> All 12 tasks completed. 365/366 tests passing (1 pre-existing failure in cohort/audit_test.py). Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-26
> **Team:** phase1c-audit-learning-20260426-1430

### Test Results
- Full suite — 365/366 PASSED (1 pre-existing failure: `cohort/audit_test.py::test_daily_summary`)
- `audit/harness_test.py` — 10/10 PASSED
- `learning/plackett_luce_test.py` — 6/6 PASSED
- `learning/refit_scheduler_test.py` — 5/5 PASSED
- `learning/cold_start_guard_test.py` — 5/5 PASSED
- `scoring/variance_test.py` — 6/6 PASSED
- `scoring/score_collapse_test.py` — 8/8 PASSED
- `scoring/specialty_flag_test.py` — 7/7 PASSED
- `integrity/contestability_test.py` — 6/6 PASSED
- mypy strict — 15 source files, no issues
- ruff check — all checks passed
- Import checks — audit OK, learning OK, scoring OK, integrity OK

### Acceptance Criteria Verification
- [x] Full test suite >= 319/320 — VERIFIED (365 passed, 1 failed; the 1 failure is pre-existing in `cohort/audit_test.py::test_daily_summary`, not in Phase 1c code)
- [x] Test counts meet minimums — VERIFIED (harness: 10 >= 10, PL: 6 >= 6, refit: 5 >= 5, cold-start: 5 >= 5, variance: 6 >= 6, contestability: 6 >= 6, score-collapse: 8 >= 8, specialty-flag: 7 >= 7)
- [x] PL fitter recovers parameters within +/-0.15 — VERIFIED (`test_fit_recovers_known_exponents` asserts `pytest.approx(true, abs=0.15)` for alpha, beta, gamma; test passes)
- [x] Bootstrap CI brackets truth >= 90% — VERIFIED (`test_bootstrap_ci_brackets_truth` asserts `bracketed / len(candidates) >= 0.9`; test passes)
- [x] Cold-start guard blocks wide CIs — VERIFIED (`test_blocks_wide_ci` confirms CI half-width 0.3 > threshold 0.2 triggers block; `test_blocks_unconverged` and `test_blocks_few_judgments` also pass)
- [x] Contestability is append-only — VERIFIED (`test_append_only` in contestability_test.py passes; storage uses JSONL append pattern)
- [x] Score-collapse detects all-below-floor — VERIFIED (`test_all_below_floor` confirms scores [0.01, 0.02, 0.03] below floor 0.05 triggers collapse; 8/8 tests pass)
- [x] All __init__.py exports updated — VERIFIED (audit: AuditHarness, JudgmentStore, PairSampler; learning: PlackettLuceFitter, RefitScheduler, ColdStartGuard; scoring: Bootstrap, ScoreCollapseHandler, SpecialtyAmbiguityFlagger; integrity: ContestabilityStore)
- [x] mypy strict passes, ruff passes — VERIFIED (mypy: 15 files, 0 issues; ruff: all checks passed)
- [x] docs/design/scoring.md updated — VERIFIED (file updated 2026-04-26 with Phase 1c sections: Plackett-Luce, bootstrap, cold-start, contestability, score-collapse, specialty-ambiguity, ADRs)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `src/aegis/audit/__init__.py` | Created | Yes |
| `src/aegis/audit/harness.py` | Created | Yes |
| `src/aegis/audit/storage.py` | Created | Yes |
| `src/aegis/audit/harness_test.py` | Created | Yes |
| `src/aegis/learning/__init__.py` | Created | Yes |
| `src/aegis/learning/plackett_luce.py` | Created | Yes |
| `src/aegis/learning/plackett_luce_test.py` | Created | Yes |
| `src/aegis/learning/refit_scheduler.py` | Created | Yes |
| `src/aegis/learning/refit_scheduler_test.py` | Created | Yes |
| `src/aegis/learning/cold_start_guard.py` | Created | Yes |
| `src/aegis/learning/cold_start_guard_test.py` | Created | Yes |
| `src/aegis/scoring/variance.py` | Created | Yes |
| `src/aegis/scoring/variance_test.py` | Created | Yes |
| `src/aegis/scoring/score_collapse.py` | Created | Yes |
| `src/aegis/scoring/score_collapse_test.py` | Created | Yes |
| `src/aegis/scoring/specialty_flag.py` | Created | Yes |
| `src/aegis/scoring/specialty_flag_test.py` | Created | Yes |
| `src/aegis/integrity/contestability.py` | Created | Yes |
| `src/aegis/integrity/contestability_test.py` | Created | Yes |
| `src/aegis/scoring/__init__.py` | Modified | Yes |
| `src/aegis/integrity/__init__.py` | Modified | Yes |
| `docs/design/scoring.md` | Modified | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build_v2 specs/aegis-phase1c-audit-learning.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build_v2` command, which deploys team agents to do the work.

## Task Description

Build Phase 1c of the Aegis scoring engine. This phase covers the expert audit harness for collecting pairwise judgments, the Plackett-Luce weight learning pipeline that fits exponents and family weights from those judgments, bootstrap score-variance estimation, and four error-handling / robustness modules (cold-start guard, integrity contestability, score-collapse handling, specialty-ambiguity flag). These seven task areas close out Phase 1 by connecting the ranking engine (Phase 1a + 1b) to a human-in-the-loop learning cycle and adding the defensive error-handling required for production use.

Tasks from the Phase 1 plan (`docs/plans/aegis/phase-1-scoring.md`):
- **Task 1.13**: Pairwise expert audit harness — pair sampling, session management, judgment persistence
- **Task 1.14**: Plackett-Luce weight learning — fit alpha/beta/gamma + family weights from pairwise judgments, versioned output, refit scheduler
- **Task 1.15**: Score-variance bootstrap — offline resampling of weight posteriors, per-candidate score bands
- **Task 3.1**: Cold-start guard — block unstable Plackett-Luce fits, retain default exponents when CIs are too wide
- **Task 3.2**: Integrity false-positive contestability — CLI-driven override with append-only audit trail
- **Task 3.3**: Score-collapse handling — fallback MeSH expansion when all candidates score below floor
- **Task 3.4**: Specialty-ambiguity flag — rule-based confidence flag, observability only in Phase 1

## Objective

When this plan is complete:
1. The audit harness can present informative candidate pairs to expert reviewers and persist their pairwise judgments.
2. The Plackett-Luce fitter can recover alpha, beta, gamma and per-family weights from collected judgments, with a refit scheduler that writes new versioned weight configs.
3. Bootstrap variance estimation produces per-candidate score bands that surface in ranked output.
4. Four error-handling guards are operational: cold-start guard blocks unstable weight deployments, contestability allows integrity false-positive overrides with audit trail, score-collapse detection triggers MeSH fallback expansion, and specialty-ambiguity flags candidates with low classifier confidence.
5. All new code passes mypy strict + ruff, and the existing 319/320 test baseline is preserved.

## Problem Statement

Phase 1a and 1b built the scoring pipeline (F1-F6 quality prior, integrity gate, topical fit, recency, end-to-end ranking), but the exponents (alpha, beta, gamma) and family weights are hardcoded cold-start priors. There is no mechanism to: (a) collect expert feedback on ranking quality, (b) learn optimal weights from that feedback, (c) estimate confidence/variance in scores, or (d) handle edge cases like insufficient training data, integrity false positives, empty result sets, or ambiguous specialty assignments. Phase 1c closes these gaps.

## Solution Approach

1. **Audit harness** (Task 1.13): A `PairSampler` selects informative pairs (biased toward close-scoring candidates), a `SessionManager` handles reviewer fatigue limits, and a `JudgmentStore` persists judgments in an append-only JSON-lines file. No real web UI in Phase 1 -- the "UI" is a data-layer abstraction that a future web frontend will consume. Inter-reviewer agreement (Cohen's kappa) is computed when overlapping pairs exist.

2. **Plackett-Luce fitter** (Task 1.14): Implements the Plackett-Luce log-likelihood using `scipy.optimize.minimize` (L-BFGS-B with box constraints matching `exponent_bounds` from the YAML config). Fits alpha, beta, gamma and optionally per-family weights. Outputs `FittedWeights` with confidence intervals from the inverse Hessian. A `RefitScheduler` tracks cadence (weekly cold-start, monthly steady-state) and writes new versioned YAML to `config/aegis/weights/translational_v{N}.yaml`.

3. **Score-variance bootstrap** (Task 1.15): Resamples weight vectors from the posterior (multivariate normal centered on fitted weights, covariance from inverse Hessian), re-ranks K times, and produces per-candidate `ScoreBand(low, high)`. Runs offline nightly, cached per cohort-day.

4. **Cold-start guard** (Task 3.1): Checks CI half-width on alpha/beta/gamma from the Plackett-Luce fit. If any exceeds threshold (default 0.2), blocks weight deployment and surfaces "cold-start prior" metadata in `RankedList`.

5. **Integrity contestability** (Task 3.2): A CLI-driven override system with an append-only JSONL audit trail. Each override record contains reviewer ID, timestamp, candidate UUID, justification, and action (override / revoke). The integrity gate checks this store before evaluating rules.

6. **Score-collapse handling** (Task 3.3): Detects when all candidates in a query result score below a configurable floor (default 0.05). Falls back to one-level MeSH rollup expansion, retries scoring, and emits a `low_confidence_ranking` flag. A second collapse returns the cohort's top-K with the flag.

7. **Specialty-ambiguity flag** (Task 3.4): Rule-based classifier that computes specialty confidence from artifact-mix heuristics. Flags candidates below 0.6 confidence as `specialty_ambiguous`. Phase 1 is observability only -- the flag does not change scoring.

## Relevant Files

### Existing Files (read, import from, or modify)
- `src/aegis/scoring/rank.py` — `Ranker` class, `CandidateScoreInput` dataclass. Score-collapse handler and bootstrap variance will integrate here.
- `src/aegis/scoring/result_format.py` — `RankedList`, `RankedCandidate`, `ComponentBreakdown` Pydantic models. May need `score_band` and `metadata` extensions.
- `src/aegis/scoring/quality_prior.py` — `WeightVector`, `QualityPrior`, `load_weight_vector()`. The Plackett-Luce fitter writes new `WeightVector` YAML files.
- `src/aegis/scoring/__init__.py` — Package exports. Must add new public classes.
- `src/aegis/integrity/__init__.py` — Package exports. Must add contestability.
- `src/aegis/integrity/hard_gate.py` — `HardGate` class. Contestability overrides integrate here.
- `src/aegis/scoring/candidate_vector.py` — `SparseVector`, `QueryVectorBuilder`. Score-collapse uses `QueryVectorBuilder` for MeSH rollup.
- `config/aegis/weights/translational_v1.yaml` — Current weight config. Plackett-Luce writes v2, v3, etc.
- `pyproject.toml` — Dependencies. scipy and numpy already present; no new deps needed.

### New Files
- `src/aegis/audit/__init__.py` — Audit package exports.
- `src/aegis/audit/harness.py` — `AuditHarness`, `PairSampler`, `PairwisePrompt`, `PairwiseJudgment`.
- `src/aegis/audit/storage.py` — `JudgmentStore` (append-only JSONL persistence).
- `src/aegis/audit/harness_test.py` — Tests for audit harness.
- `src/aegis/learning/__init__.py` — Learning package exports.
- `src/aegis/learning/plackett_luce.py` — `PlackettLuceFitter`, `FittedWeights`.
- `src/aegis/learning/refit_scheduler.py` — `RefitScheduler` (cadence tracking, version bumping).
- `src/aegis/learning/plackett_luce_test.py` — Tests for Plackett-Luce fitter.
- `src/aegis/scoring/variance.py` — `Bootstrap`, `ScoreBand`.
- `src/aegis/scoring/variance_test.py` — Tests for bootstrap variance.
- `src/aegis/learning/cold_start_guard.py` — `ColdStartGuard`.
- `src/aegis/learning/cold_start_guard_test.py` — Tests for cold-start guard.
- `src/aegis/integrity/contestability.py` — `ContestabilityStore`, `OverrideRecord`.
- `src/aegis/integrity/contestability_test.py` — Tests for contestability.
- `src/aegis/scoring/score_collapse.py` — `ScoreCollapseHandler`.
- `src/aegis/scoring/score_collapse_test.py` — Tests for score-collapse.
- `src/aegis/scoring/specialty_flag.py` — `SpecialtyAmbiguityFlagger`.
- `src/aegis/scoring/specialty_flag_test.py` — Tests for specialty-ambiguity flag.

## Implementation Phases

### Phase 1: Foundation (Audit + Storage)
Build the audit harness data models, pair sampler, judgment storage, and the audit package structure. These are prerequisites for the Plackett-Luce fitter.

### Phase 2: Core Implementation (PL Fitter + Bootstrap + Guards)
Build the Plackett-Luce fitter, refit scheduler, bootstrap variance estimator, and cold-start guard. These form the learning loop core.

### Phase 3: Error Handling + Integration
Build the contestability system, score-collapse handler, specialty-ambiguity flag, and update package __init__ files to export all new public classes.

## Team Orchestration

- The `/build_v2` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build_v2` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- **`Assigned To` is enforced**: `/build_v2` injects each agent's name into their standing orders. Agents only claim tasks where `Assigned To` matches their own name. Every task MUST have an `Assigned To`.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Audit harness, judgment storage, Plackett-Luce fitter, refit scheduler, cold-start guard (the learning pipeline)
  - Agent Type: builder
- Builder
  - Name: builder-2
  - Role: Bootstrap variance, score-collapse handler, specialty-ambiguity flag, integrity contestability (scoring robustness + error handling)
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

### 1. Create Audit Package with Judgment Models and Storage
- **Task ID**: audit-storage
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the audit package and the judgment persistence layer.

    ## What to do

    1. Create `src/aegis/audit/__init__.py` with package docstring and exports (to be populated after all audit modules are built).
    2. Create `src/aegis/audit/storage.py` with:
       - `PairwiseJudgment` frozen Pydantic model:
         ```python
         class PairwiseJudgment(BaseModel):
             model_config = ConfigDict(frozen=True)
             judgment_id: str           # UUID
             reviewer_id: str
             query_mesh_terms: list[str]
             candidate_a_uuid: str
             candidate_b_uuid: str
             winner_uuid: str           # which candidate the reviewer chose
             timestamp: datetime
             evidence_shown: dict[str, str]  # summary of what reviewer saw
             session_id: str
         ```
       - `JudgmentStore` class:
         - `__init__(self, storage_path: Path)` — path to a JSONL file.
         - `append(self, judgment: PairwiseJudgment) -> None` — append-only write. Open file in append mode, write `judgment.model_dump_json()` + newline, flush.
         - `load_all(self) -> list[PairwiseJudgment]` — read all judgments from the JSONL file. Return empty list if file does not exist.
         - `count(self) -> int` — return the number of stored judgments.
         - `by_reviewer(self, reviewer_id: str) -> list[PairwiseJudgment]` — filter judgments by reviewer.

    3. Create `src/aegis/audit/harness_test.py` (storage portion) with tests:
       - `test_append_and_load` — append 3 judgments, load all, verify count and content.
       - `test_empty_file` — load from nonexistent path returns empty list.
       - `test_by_reviewer` — filter by reviewer_id.
       - Use `tmp_path` pytest fixture for file paths.

    ## Files to modify
    - `src/aegis/audit/__init__.py` — CREATE. Start with minimal exports; will be updated in task `update-init-exports`.
    - `src/aegis/audit/storage.py` — CREATE as described above.
    - `src/aegis/audit/harness_test.py` — CREATE with storage tests (harness tests added in next task).

    ## Code patterns to follow
    - All Pydantic models use `from __future__ import annotations`, `from pydantic import BaseModel, ConfigDict`, and `model_config = ConfigDict(frozen=True)`. See `src/aegis/scoring/result_format.py:8` for the canonical example.
    - JSONL append pattern: open with mode `"a"`, write `model.model_dump_json() + "\n"`, flush. This matches the append-only audit philosophy from `docs/plans/aegis/phase-1-scoring.md` Task 3.2.
    - Use `logging.getLogger(__name__)` for any log messages. See `src/aegis/integrity/soft_discounts.py:13`.
    - Every file starts with `from __future__ import annotations`.
    - Use keyword-only arguments for methods with multiple parameters (see `HardGate.evaluate` at `src/aegis/integrity/hard_gate.py:86`).

    ## Acceptance criteria
    - `src/aegis/audit/storage.py` exists and exports `PairwiseJudgment` and `JudgmentStore`.
    - `PairwiseJudgment` is a frozen Pydantic model with all fields listed above.
    - `JudgmentStore.append` writes to JSONL; `load_all` reads back correctly.
    - 3+ tests pass in `src/aegis/audit/harness_test.py` covering storage.
    - `mypy --strict src/aegis/audit/storage.py` passes.
    - `ruff check src/aegis/audit/storage.py` passes.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/audit/harness_test.py -x -q && python -m mypy --strict src/aegis/audit/storage.py && ruff check src/aegis/audit/storage.py
    ```

### 2. Build Audit Harness with Pair Sampling
- **Task ID**: audit-harness
- **Role**: builder
- **Depends On**: audit-storage
- **Assigned To**: builder-1
- **Description**: |
    Build the audit harness that samples informative candidate pairs and manages review sessions.

    ## What to do

    1. Create `src/aegis/audit/harness.py` with:

       - `PairwisePrompt` frozen Pydantic model:
         ```python
         class PairwisePrompt(BaseModel):
             model_config = ConfigDict(frozen=True)
             prompt_id: str             # UUID
             query_mesh_terms: list[str]
             candidate_a_uuid: str
             candidate_a_name: str
             candidate_a_evidence: dict[str, str]  # top artifacts, component scores (NOT system rank)
             candidate_b_uuid: str
             candidate_b_name: str
             candidate_b_evidence: dict[str, str]
         ```

       - `PairSampler` class:
         - `__init__(self, *, rng_seed: int | None = None)` — optional random seed for reproducibility.
         - `sample_pairs(self, candidates: list[ScoredCandidate], query_mesh: list[str], n_pairs: int, existing_judgments: list[PairwiseJudgment] | None = None) -> list[PairwisePrompt]`:
           - `ScoredCandidate` is a simple dataclass:
             ```python
             @dataclass
             class ScoredCandidate:
                 uuid: str
                 name: str
                 score: float
                 evidence: dict[str, str]
             ```
           - **Active-learning bias**: Sort candidates by score. For each pair, prefer candidates with close scores (informative pairs) over random pairs. Implementation: divide candidates into score-sorted buckets; sample adjacent-bucket pairs with probability proportional to `1 / (1 + |score_a - score_b|)`. Normalize probabilities and sample without replacement.
           - Exclude pairs already judged (check `existing_judgments`).
           - Return up to `n_pairs` prompts, each with a fresh UUID for `prompt_id`.

       - `SessionManager` class:
         - `__init__(self, *, max_pairs_per_session: int = 20, cooldown_minutes: int = 60)` — reviewer fatigue limits.
         - `can_continue(self, reviewer_id: str, session_judgments: int, session_start: datetime) -> bool` — returns False if session has exceeded `max_pairs_per_session` or if cooldown not elapsed since last session.
         - `record_session_end(self, reviewer_id: str, timestamp: datetime) -> None` — records when a session ended, for cooldown tracking.
         - Internal state: `dict[str, datetime]` mapping reviewer_id to last session end time.

       - `AuditHarness` class (facade):
         - `__init__(self, *, store: JudgmentStore, sampler: PairSampler, session_mgr: SessionManager)`.
         - `next_pair(self, reviewer_id: str, candidates: list[ScoredCandidate], query_mesh: list[str]) -> PairwisePrompt | None` — returns the next pair for this reviewer, or None if session limit reached. Calls `sampler.sample_pairs` with `n_pairs=1` and the reviewer's existing judgments.
         - `submit_judgment(self, judgment: PairwiseJudgment) -> None` — delegates to `store.append`.
         - `inter_reviewer_kappa(self) -> float | None` — compute Cohen's kappa on overlapping pairs (same candidate pair judged by 2+ reviewers). Return None if no overlapping pairs exist. Use the standard kappa formula: `kappa = (p_o - p_e) / (1 - p_e)` where `p_o` is observed agreement and `p_e` is expected agreement under random assignment.

    2. Add tests to `src/aegis/audit/harness_test.py`:
       - `test_pair_sampler_returns_prompts` — 5 candidates, sample 3 pairs, verify 3 PairwisePrompt objects returned.
       - `test_pair_sampler_active_learning_bias` — verify that sampled pairs tend to have closer scores than a random baseline. Generate 20 candidates with evenly spaced scores, sample 50 pairs over multiple calls. Compute mean score-difference of sampled pairs vs. all-pairs mean. Assert sampled mean is smaller.
       - `test_pair_sampler_excludes_existing` — provide 2 existing judgments, verify those pairs are not re-sampled.
       - `test_session_manager_limit` — verify `can_continue` returns False after max_pairs.
       - `test_session_manager_cooldown` — verify cooldown enforcement.
       - `test_audit_harness_next_pair` — end-to-end: create harness, call next_pair, verify prompt returned.
       - `test_inter_reviewer_kappa` — create 2 reviewers judging the same 5 pairs with 80% agreement, verify kappa > 0.

    ## Files to modify
    - `src/aegis/audit/harness.py` — CREATE as described above.
    - `src/aegis/audit/harness_test.py` — ADD harness tests alongside existing storage tests.

    ## Code patterns to follow
    - Use `uuid.uuid4().hex` for generating unique IDs. Import `uuid` from stdlib.
    - Use `import random` for sampling; accept optional `rng_seed` for reproducibility using `random.Random(seed)`.
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - Dataclasses for simple mutable containers (see `CandidateScoreInput` at `src/aegis/scoring/rank.py:22`).
    - Keyword-only arguments: `def __init__(self, *, store: ..., sampler: ...)`.
    - `from __future__ import annotations` at top of every file.

    ## Acceptance criteria
    - `AuditHarness.next_pair` returns a `PairwisePrompt` or None.
    - `PairSampler.sample_pairs` implements active-learning bias (closer-scoring pairs preferred).
    - `SessionManager` enforces per-session pair limits and cooldown.
    - `AuditHarness.inter_reviewer_kappa` returns a float or None.
    - 7+ tests pass in harness_test.py.
    - mypy strict passes on `src/aegis/audit/harness.py`.
    - ruff passes on `src/aegis/audit/harness.py`.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/audit/harness_test.py -x -q && python -m mypy --strict src/aegis/audit/harness.py && ruff check src/aegis/audit/harness.py
    ```

### 3. Build Plackett-Luce Fitter
- **Task ID**: plackett-luce-fitter
- **Role**: builder
- **Depends On**: audit-storage
- **Assigned To**: builder-1
- **Description**: |
    Implement the Plackett-Luce weight learning module that fits exponents and family weights from pairwise judgments.

    ## What to do

    1. Create `src/aegis/learning/__init__.py` with minimal exports (to be updated in `update-init-exports`).

    2. Create `src/aegis/learning/plackett_luce.py` with:

       - `FittedWeights` frozen Pydantic model:
         ```python
         class FittedWeights(BaseModel):
             model_config = ConfigDict(frozen=True)
             alpha: float
             beta: float
             gamma: float
             family_weights: dict[str, float]  # f1_rcr -> 0.35, etc.
             alpha_ci: tuple[float, float]      # 95% CI
             beta_ci: tuple[float, float]
             gamma_ci: tuple[float, float]
             n_judgments: int
             converged: bool
             log_likelihood: float
         ```

       - Helper dataclass `JudgmentRecord`:
         ```python
         @dataclass
         class JudgmentRecord:
             winner_scores: dict[str, float]  # component name -> score for winner
             loser_scores: dict[str, float]   # component name -> score for loser
         ```
         Where component names are: `quality_prior`, `topical_fit`, `recency`, and optionally per-family scores (f1_rcr, ..., f6_lineage).

       - `PlackettLuceFitter` class:
         - `__init__(self, *, exponent_bounds: dict[str, tuple[float, float]] | None = None)`:
           - Default bounds: `alpha: (0.3, 1.2), beta: (0.5, 1.5), gamma: (0.1, 0.8)` (matching `config/aegis/weights/translational_v1.yaml` exponent_bounds).
         - `fit(self, judgments: list[JudgmentRecord], initial_weights: WeightVector | None = None) -> FittedWeights`:
           - **Log-likelihood**: For each judgment, the probability that winner beats loser under Plackett-Luce is:
             `P(winner > loser) = S(winner) / (S(winner) + S(loser))`
             where `S(c) = Q(c)^alpha * T(c)^beta * R(c)^gamma`.
             The log-likelihood is `sum(log(P(winner > loser)))` over all judgments.
           - **Optimization**: Use `scipy.optimize.minimize` with method `"L-BFGS-B"` and bounds from `exponent_bounds`.
             Parameters to optimize: `[alpha, beta, gamma]`. (Family-weight optimization is Phase 2; for now, keep family weights fixed from the input WeightVector.)
           - Initial point: from `initial_weights` if provided, else (0.7, 1.0, 0.4).
           - **Confidence intervals**: After optimization, compute the Hessian via `scipy.optimize.approx_fprime` or use the inverse Hessian from the optimizer result (`result.hess_inv`). CIs are `param +/- 1.96 * sqrt(diag(H_inv))`.
           - Clamp CIs to exponent bounds.
           - Set `converged = result.success`.
           - Return `FittedWeights` with the fitted values, CIs, judgment count, convergence flag, and final log-likelihood.

         - `_neg_log_likelihood(self, params: ndarray, judgments: list[JudgmentRecord]) -> float`:
           - Internal method. Extract alpha, beta, gamma from params array.
           - For each judgment, compute S(winner) and S(loser) using the candidate's component scores raised to the respective exponents.
           - Use `quality_prior`, `topical_fit`, `recency` keys from the JudgmentRecord dicts.
           - Sum `-log(S(w) / (S(w) + S(l)))` over all judgments.
           - Add small epsilon (1e-12) inside log to prevent log(0).

    3. Create `src/aegis/learning/plackett_luce_test.py` with:
       - `test_fit_recovers_known_exponents` — Generate 200 synthetic judgments using known alpha=0.8, beta=1.1, gamma=0.5. For each judgment, sample random component scores for two candidates, compute S(c) with known exponents, assign the winner probabilistically. Fit and verify recovered alpha, beta, gamma are within +/-0.15 of ground truth.
       - `test_fit_converges` — Verify `converged` is True on well-behaved data.
       - `test_confidence_intervals` — Verify CIs bracket the true parameters on synthetic data.
       - `test_fit_with_few_judgments` — 10 judgments: verify fit returns (may not converge well, but should not crash).
       - `test_bounds_enforced` — Generate data that would push alpha outside bounds; verify fitted alpha stays within bounds.
       - `test_empty_judgments` — Empty list returns sensible defaults (initial weights, converged=False).

    ## Files to modify
    - `src/aegis/learning/__init__.py` — CREATE with minimal exports.
    - `src/aegis/learning/plackett_luce.py` — CREATE as described.
    - `src/aegis/learning/plackett_luce_test.py` — CREATE as described.

    ## Code patterns to follow
    - Import `from scipy.optimize import minimize` and `import numpy as np`. Both scipy and numpy are already in `pyproject.toml` dependencies.
    - Frozen Pydantic models with `ConfigDict(frozen=True)` for `FittedWeights`.
    - Use `WeightVector` from `aegis.scoring.quality_prior` as the input type for initial weights.
    - Dataclass for `JudgmentRecord` (mutable, simple container). Follow `CandidateScoreInput` pattern at `src/aegis/scoring/rank.py:22`.
    - `from __future__ import annotations` at top of every file.
    - Use `logging.getLogger(__name__)` for logging.
    - Use keyword-only arguments for `__init__`.
    - Use `pytest.approx` for floating-point assertions in tests.
    - Note: `FittedWeights.alpha_ci` etc. should use `tuple[float, float]` — Pydantic supports this.

    ## Acceptance criteria
    - `PlackettLuceFitter.fit` returns `FittedWeights` with alpha, beta, gamma, CIs, convergence flag.
    - On synthetic data with known ground-truth exponents, fit recovers parameters within +/-0.15.
    - Bounds are enforced.
    - 6+ tests pass.
    - mypy strict passes on `src/aegis/learning/plackett_luce.py`.
    - ruff passes.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/learning/plackett_luce_test.py -x -q && python -m mypy --strict src/aegis/learning/plackett_luce.py && ruff check src/aegis/learning/plackett_luce.py
    ```

### 4. Build Refit Scheduler
- **Task ID**: refit-scheduler
- **Role**: builder
- **Depends On**: plackett-luce-fitter
- **Assigned To**: builder-1
- **Description**: |
    Implement the refit scheduler that manages weight version bumping and cadence control.

    ## What to do

    1. Create `src/aegis/learning/refit_scheduler.py` with:

       - `RefitCadence` enum:
         ```python
         class RefitCadence(StrEnum):
             cold_start = "cold_start"    # weekly
             steady_state = "steady_state"  # monthly
         ```

       - `RefitResult` frozen Pydantic model:
         ```python
         class RefitResult(BaseModel):
             model_config = ConfigDict(frozen=True)
             new_version: int
             output_path: str
             fitted_weights: FittedWeights
             cadence: str
             timestamp: datetime
         ```

       - `RefitScheduler` class:
         - `__init__(self, *, weights_dir: Path, current_version: int = 1, cadence: RefitCadence = RefitCadence.cold_start)`.
         - `should_refit(self, last_refit: datetime | None, now: datetime) -> bool`:
           - cold_start cadence: refit if >= 7 days since last refit (or never refitted).
           - steady_state cadence: refit if >= 30 days since last refit.
         - `execute_refit(self, fitter: PlackettLuceFitter, judgments: list[JudgmentRecord], current_weights: WeightVector) -> RefitResult`:
           - Call `fitter.fit(judgments, initial_weights=current_weights)`.
           - Bump version: `new_version = current_weights.version + 1`.
           - Write new YAML to `weights_dir / f"translational_v{new_version}.yaml"`.
           - YAML format must match `config/aegis/weights/translational_v1.yaml`:
             ```yaml
             version: N
             specialty: translational
             created: "YYYY-MM-DD"
             weights:
               f1_rcr: 0.35
               ...
             exponents:
               alpha: <fitted>
               beta: <fitted>
               gamma: <fitted>
             exponent_bounds:
               alpha: [0.3, 1.2]
               beta: [0.5, 1.5]
               gamma: [0.1, 0.8]
             ```
           - Family weights stay fixed from current_weights (Phase 1 only fits exponents).
           - Return `RefitResult`.
         - `rollback(self, weights_dir: Path, target_version: int) -> WeightVector`:
           - Load and return the weight vector from `weights_dir / f"translational_v{target_version}.yaml"` using `load_weight_vector`.
           - Raise `FileNotFoundError` if the version file does not exist.

    2. Add tests to `src/aegis/learning/plackett_luce_test.py` (or create a separate `src/aegis/learning/refit_scheduler_test.py` — prefer the separate file):
       - `test_should_refit_cold_start` — 7+ days since last refit returns True.
       - `test_should_refit_too_soon` — 3 days since last refit in cold_start returns False.
       - `test_should_refit_steady_state` — 30+ days returns True.
       - `test_execute_refit_writes_yaml` — Use tmp_path, verify YAML file is created with bumped version.
       - `test_rollback_loads_version` — Write a YAML, rollback to it, verify loaded WeightVector.
       - Use `tmp_path` pytest fixture for all file operations.

    ## Files to modify
    - `src/aegis/learning/refit_scheduler.py` — CREATE as described.
    - `src/aegis/learning/refit_scheduler_test.py` — CREATE as described.

    ## Code patterns to follow
    - Import `yaml` and use `yaml.safe_dump` for YAML writing. See `src/aegis/scoring/quality_prior.py:9` for yaml import pattern.
    - Use `load_weight_vector` from `aegis.scoring.quality_prior` for rollback.
    - Import `FittedWeights`, `PlackettLuceFitter`, `JudgmentRecord` from `aegis.learning.plackett_luce`.
    - `from __future__ import annotations` at top.
    - Frozen Pydantic models.
    - `StrEnum` for cadence (see `DiscountType` at `src/aegis/integrity/soft_discounts.py:22`).

    ## Acceptance criteria
    - `RefitScheduler.should_refit` returns correct boolean based on cadence and elapsed time.
    - `execute_refit` writes a valid YAML file that `load_weight_vector` can parse.
    - Rollback loads a prior version correctly.
    - 5+ tests pass.
    - mypy strict and ruff pass.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/learning/refit_scheduler_test.py -x -q && python -m mypy --strict src/aegis/learning/refit_scheduler.py && ruff check src/aegis/learning/refit_scheduler.py
    ```

### 5. Build Cold-Start Guard
- **Task ID**: cold-start-guard
- **Role**: builder
- **Depends On**: plackett-luce-fitter
- **Assigned To**: builder-1
- **Description**: |
    Implement the cold-start guard that blocks deployment of unstable Plackett-Luce fits.

    ## What to do

    1. Create `src/aegis/learning/cold_start_guard.py` with:

       - `GuardVerdict` frozen Pydantic model:
         ```python
         class GuardVerdict(BaseModel):
             model_config = ConfigDict(frozen=True)
             allow_deployment: bool
             reason: str
             ci_half_widths: dict[str, float]   # alpha -> 0.15, etc.
             threshold: float
         ```

       - `ColdStartGuard` class:
         - `__init__(self, *, ci_threshold: float = 0.2)` — CI half-width threshold. If any exponent CI half-width exceeds this, block deployment.
         - `evaluate(self, fitted: FittedWeights) -> GuardVerdict`:
           - Compute CI half-width for alpha: `(fitted.alpha_ci[1] - fitted.alpha_ci[0]) / 2`.
           - Same for beta and gamma.
           - If ANY half-width > threshold, return `allow_deployment=False` with reason explaining which parameter(s) are too uncertain.
           - If fit did not converge (`fitted.converged == False`), always block with reason "fit did not converge".
           - If `fitted.n_judgments < 20`, block with reason "insufficient judgments (N < 20)".
           - Otherwise return `allow_deployment=True`.

    2. Create `src/aegis/learning/cold_start_guard_test.py` with:
       - `test_blocks_wide_ci` — FittedWeights with alpha_ci=(0.3, 0.9) -> half-width 0.3 > 0.2 -> blocked.
       - `test_allows_narrow_ci` — FittedWeights with all CIs narrow -> allowed.
       - `test_blocks_unconverged` — converged=False -> blocked regardless of CIs.
       - `test_blocks_few_judgments` — n_judgments=10 -> blocked.
       - `test_custom_threshold` — threshold=0.5 allows wider CIs.

    ## Files to modify
    - `src/aegis/learning/cold_start_guard.py` — CREATE.
    - `src/aegis/learning/cold_start_guard_test.py` — CREATE.

    ## Code patterns to follow
    - Frozen Pydantic model for `GuardVerdict`.
    - Import `FittedWeights` from `aegis.learning.plackett_luce`.
    - `from __future__ import annotations` at top.
    - Keyword-only `__init__`.

    ## Acceptance criteria
    - `ColdStartGuard.evaluate` returns `GuardVerdict` with correct allow/block decision.
    - Wide CIs, non-convergence, and insufficient judgments all trigger blocking.
    - 5 tests pass.
    - mypy strict and ruff pass.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/learning/cold_start_guard_test.py -x -q && python -m mypy --strict src/aegis/learning/cold_start_guard.py && ruff check src/aegis/learning/cold_start_guard.py
    ```

### 6. Build Score-Variance Bootstrap
- **Task ID**: bootstrap-variance
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Implement bootstrap score-variance estimation that produces per-candidate score bands.

    ## What to do

    1. Create `src/aegis/scoring/variance.py` with:

       - `ScoreBand` frozen Pydantic model:
         ```python
         class ScoreBand(BaseModel):
             model_config = ConfigDict(frozen=True)
             low: float
             high: float
             median: float
             n_samples: int
         ```

       - `BootstrapInput` dataclass:
         ```python
         @dataclass
         class BootstrapInput:
             candidate_uuid: str
             integrity_score: float
             quality_percentile: float
             topical_fit: float
             recency: float
         ```

       - `Bootstrap` class:
         - `__init__(self, *, rng_seed: int | None = None)`.
         - `estimate(self, candidates: list[BootstrapInput], weight_mean: tuple[float, float, float], weight_cov: ndarray, n_samples: int = 200) -> dict[str, ScoreBand]`:
           - `weight_mean` is (alpha, beta, gamma) — the fitted exponent means.
           - `weight_cov` is a 3x3 covariance matrix from the Plackett-Luce fit's inverse Hessian.
           - For each of `n_samples` iterations:
             - Sample `(alpha_s, beta_s, gamma_s)` from `np.random.multivariate_normal(weight_mean, weight_cov)`.
             - Clamp sampled exponents to the standard bounds: alpha in [0.3, 1.2], beta in [0.5, 1.5], gamma in [0.1, 0.8].
             - For each candidate, compute `score = I * Q^alpha_s * T^beta_s * R^gamma_s` using the `_safe_pow` pattern from `src/aegis/scoring/rank.py:130` (return 0.0 for non-positive bases).
           - Collect per-candidate score distributions across all samples.
           - For each candidate, compute 2.5th percentile (low), 97.5th percentile (high), and 50th percentile (median) using `np.percentile`.
           - Return dict mapping candidate_uuid to ScoreBand.

    2. Create `src/aegis/scoring/variance_test.py` with:
       - `test_estimate_returns_bands` — 5 candidates, verify all have ScoreBand with low <= median <= high.
       - `test_narrow_cov_narrow_bands` — very small covariance matrix -> score bands should be narrow (high - low < 0.1).
       - `test_wide_cov_wide_bands` — large covariance -> bands should be wider than narrow case.
       - `test_bootstrap_ci_brackets_truth` — Generate candidates, use true exponents as mean with small covariance. Verify 90%+ of candidates have their "true score" within [low, high]. Use 500 samples for stability.
       - `test_zero_integrity_stays_zero` — A candidate with integrity_score=0 should have ScoreBand(0, 0, 0, n).
       - `test_deterministic_with_seed` — Same seed produces same bands.

    ## Files to modify
    - `src/aegis/scoring/variance.py` — CREATE.
    - `src/aegis/scoring/variance_test.py` — CREATE.

    ## Code patterns to follow
    - Use `import numpy as np` and `from numpy.typing import NDArray`. Both numpy and scipy are in `pyproject.toml`.
    - Use `np.random.default_rng(seed)` for reproducible RNG (modern numpy pattern).
    - Frozen Pydantic model for `ScoreBand`.
    - Dataclass for `BootstrapInput` (matches `CandidateScoreInput` style at `src/aegis/scoring/rank.py:22`).
    - `_safe_pow` pattern: `base ** exp if base > 0 else 0.0` (from `src/aegis/scoring/rank.py:130`).
    - `from __future__ import annotations` at top.
    - Keyword-only `__init__`.
    - Use `pytest.approx` for float comparisons.

    ## Acceptance criteria
    - `Bootstrap.estimate` returns dict[str, ScoreBand] with correct keys.
    - ScoreBand.low <= ScoreBand.median <= ScoreBand.high for every candidate.
    - On synthetic data, bootstrap CI brackets ground-truth scores >= 90% of the time.
    - 6 tests pass.
    - mypy strict and ruff pass.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/variance_test.py -x -q && python -m mypy --strict src/aegis/scoring/variance.py && ruff check src/aegis/scoring/variance.py
    ```

### 7. Build Integrity Contestability
- **Task ID**: integrity-contestability
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the CLI-driven integrity false-positive override system with an append-only audit trail.

    ## What to do

    1. Create `src/aegis/integrity/contestability.py` with:

       - `OverrideAction` enum:
         ```python
         class OverrideAction(StrEnum):
             override = "override"    # remove false-positive hard-zero
             revoke = "revoke"        # reinstate the hard-zero
         ```

       - `OverrideRecord` frozen Pydantic model:
         ```python
         class OverrideRecord(BaseModel):
             model_config = ConfigDict(frozen=True)
             record_id: str            # UUID
             candidate_uuid: str
             reviewer_id: str
             action: OverrideAction
             justification: str
             timestamp: datetime
             original_reason: str      # the hard-gate reason being contested
         ```

       - `ContestabilityStore` class:
         - `__init__(self, storage_path: Path)` — path to JSONL file for the audit trail.
         - `add_override(self, *, candidate_uuid: str, reviewer_id: str, action: OverrideAction, justification: str, original_reason: str) -> OverrideRecord`:
           - Create an `OverrideRecord` with a fresh UUID and current timestamp.
           - Append to JSONL file (same pattern as JudgmentStore: open in append mode, write JSON line, flush).
           - Return the record.
         - `is_overridden(self, candidate_uuid: str) -> bool`:
           - Load all records for this candidate.
           - The most recent record determines the state: if action == "override", return True; if "revoke", return False.
           - If no records exist, return False.
         - `get_history(self, candidate_uuid: str) -> list[OverrideRecord]`:
           - Return all records for this candidate, in chronological order.
         - `load_all(self) -> list[OverrideRecord]`:
           - Read all records from the JSONL file. Return empty list if file doesn't exist.

    2. Create `src/aegis/integrity/contestability_test.py` with:
       - `test_add_override_persists` — Add an override, verify it can be loaded back.
       - `test_is_overridden_after_override` — Override a candidate, verify `is_overridden` returns True.
       - `test_is_overridden_after_revoke` — Override then revoke, verify `is_overridden` returns False.
       - `test_append_only` — Override, revoke, override again: verify 3 records in history.
       - `test_nonexistent_candidate` — `is_overridden` returns False for unknown UUID.
       - `test_get_history_chronological` — Multiple records returned in timestamp order.
       - Use `tmp_path` for file storage.

    ## Files to modify
    - `src/aegis/integrity/contestability.py` — CREATE.
    - `src/aegis/integrity/contestability_test.py` — CREATE.

    ## Code patterns to follow
    - JSONL append pattern: same as `JudgmentStore` — open file in `"a"` mode, write `record.model_dump_json() + "\n"`, flush.
    - Frozen Pydantic models with `ConfigDict(frozen=True)`.
    - `StrEnum` for `OverrideAction` (matches `DiscountType` pattern at `src/aegis/integrity/soft_discounts.py:22`).
    - `from __future__ import annotations` at top.
    - Use `uuid.uuid4().hex` for record IDs.
    - Use `datetime.now(tz=timezone.utc)` for timestamps (`from datetime import datetime, timezone`).
    - Use keyword-only arguments for methods.
    - Use `tmp_path` pytest fixture for all file-based tests.

    ## Acceptance criteria
    - `ContestabilityStore` persists overrides as append-only JSONL.
    - `is_overridden` correctly resolves the latest action for a candidate.
    - Override cannot be silently revoked — revocation requires another record.
    - 6+ tests pass.
    - mypy strict and ruff pass.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/integrity/contestability_test.py -x -q && python -m mypy --strict src/aegis/integrity/contestability.py && ruff check src/aegis/integrity/contestability.py
    ```

### 8. Build Score-Collapse Handler
- **Task ID**: score-collapse
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the score-collapse detection and fallback MeSH expansion module.

    ## What to do

    1. Create `src/aegis/scoring/score_collapse.py` with:

       - `CollapseResult` frozen Pydantic model:
         ```python
         class CollapseResult(BaseModel):
             model_config = ConfigDict(frozen=True)
             collapsed: bool
             expanded_mesh_terms: list[str]  # new terms after rollup (empty if not collapsed)
             flag: str                        # "normal", "low_confidence_ranking", "cohort_fallback"
             retry_count: int                 # 0 if no collapse, 1 if first retry, 2 if cohort fallback
         ```

       - `MESH_PARENT_MAP` — a small hardcoded dict mapping example NSCLC-relevant MeSH descriptors to their parent terms for testing. In production, this would be loaded from a MeSH tree file. Example:
         ```python
         MESH_PARENT_MAP: dict[str, str] = {
             "D002289": "D009369",  # Carcinoma, Non-Small-Cell Lung -> Neoplasms
             "D008175": "D009369",  # Lung Neoplasms -> Neoplasms
             "D000074322": "D060890",  # Immune Checkpoint Inhibitors -> Immunotherapy
             # Add 5-10 more mappings relevant for testing
         }
         ```

       - `ScoreCollapseHandler` class:
         - `__init__(self, *, floor: float = 0.05, mesh_parent_map: dict[str, str] | None = None)`.
         - `check_collapse(self, scores: list[float]) -> bool`:
           - Return True if ALL scores are below `floor`.
           - Empty list returns True (no results is a collapse).
         - `expand_mesh(self, mesh_terms: list[str]) -> list[str]`:
           - For each term, look up its parent in `mesh_parent_map`. If found, add the parent to the result.
           - Return the union of original terms + parent terms (deduplicated).
           - If a term has no parent mapping, keep it as-is.
         - `handle_collapse(self, scores: list[float], query_mesh: list[str]) -> CollapseResult`:
           - If not collapsed: return `CollapseResult(collapsed=False, expanded_mesh_terms=[], flag="normal", retry_count=0)`.
           - If collapsed (first time): expand mesh, return `CollapseResult(collapsed=True, expanded_mesh_terms=<expanded>, flag="low_confidence_ranking", retry_count=1)`.
           - The caller is responsible for re-running scoring with the expanded terms and calling `handle_collapse` again if still collapsed.
         - `make_cohort_fallback(self) -> CollapseResult`:
           - Return `CollapseResult(collapsed=True, expanded_mesh_terms=[], flag="cohort_fallback", retry_count=2)`.
           - This signals the caller to return the cohort's top-K regardless of scores.

    2. Create `src/aegis/scoring/score_collapse_test.py` with:
       - `test_no_collapse` — scores [0.3, 0.5, 0.8] -> not collapsed.
       - `test_all_below_floor` — scores [0.01, 0.02, 0.03] -> collapsed.
       - `test_empty_scores` — empty list -> collapsed.
       - `test_custom_floor` — floor=0.1, scores [0.08, 0.09] -> collapsed.
       - `test_expand_mesh` — terms with known parents produce expanded list.
       - `test_handle_collapse_returns_expanded` — collapsed scores produce CollapseResult with expanded terms and flag.
       - `test_make_cohort_fallback` — returns cohort_fallback flag.
       - `test_single_score_above_floor` — scores [0.01, 0.06] with floor=0.05 -> NOT collapsed (not ALL below floor).

    ## Files to modify
    - `src/aegis/scoring/score_collapse.py` — CREATE.
    - `src/aegis/scoring/score_collapse_test.py` — CREATE.

    ## Code patterns to follow
    - Frozen Pydantic model for `CollapseResult`.
    - `from __future__ import annotations` at top.
    - Keyword-only `__init__`.
    - Module-level constants in CAPS (see `DEFAULT_HALF_LIFE_YEARS` at `src/aegis/scoring/recency.py:10`).

    ## Acceptance criteria
    - `ScoreCollapseHandler.check_collapse` correctly detects when all scores are below floor.
    - `expand_mesh` produces parent-expanded MeSH terms.
    - `handle_collapse` returns correct CollapseResult with flag and expanded terms.
    - 8 tests pass.
    - mypy strict and ruff pass.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/score_collapse_test.py -x -q && python -m mypy --strict src/aegis/scoring/score_collapse.py && ruff check src/aegis/scoring/score_collapse.py
    ```

### 9. Build Specialty-Ambiguity Flag
- **Task ID**: specialty-flag
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the rule-based specialty-ambiguity flagger for observability.

    ## What to do

    1. Create `src/aegis/scoring/specialty_flag.py` with:

       - `SpecialtyFlagResult` frozen Pydantic model:
         ```python
         class SpecialtyFlagResult(BaseModel):
             model_config = ConfigDict(frozen=True)
             candidate_uuid: str
             specialty_confidence: float     # 0.0-1.0
             is_ambiguous: bool              # True if confidence < threshold
             artifact_mix: dict[str, float]  # breakdown: {"papers": 0.6, "trials": 0.2, "grants": 0.2}
             reason: str                     # human-readable explanation
         ```

       - `AMBIGUITY_THRESHOLD: float = 0.6` — module-level constant.

       - `SpecialtyAmbiguityFlagger` class:
         - `__init__(self, *, threshold: float = AMBIGUITY_THRESHOLD)`.
         - `flag(self, *, candidate_uuid: str, n_papers_in_specialty: int, n_papers_total: int, n_trials_in_specialty: int, n_trials_total: int, n_grants_in_specialty: int, n_grants_total: int) -> SpecialtyFlagResult`:
           - **Confidence computation** (rule-based):
             - Paper ratio: `n_papers_in_specialty / max(n_papers_total, 1)`
             - Trial ratio: `n_trials_in_specialty / max(n_trials_total, 1)`
             - Grant ratio: `n_grants_in_specialty / max(n_grants_total, 1)`
             - Weighted confidence: `0.5 * paper_ratio + 0.3 * trial_ratio + 0.2 * grant_ratio`
             - These weights reflect that papers are the strongest signal of specialty focus, followed by trials, then grants.
           - `is_ambiguous = confidence < threshold`.
           - Build artifact_mix dict with the three ratios.
           - If ambiguous, reason = "Specialty confidence {confidence:.2f} below threshold {threshold:.2f}; artifact mix suggests multi-domain activity".
           - If not ambiguous, reason = "Specialty confidence {confidence:.2f} above threshold".
           - Return `SpecialtyFlagResult`.

    2. Create `src/aegis/scoring/specialty_flag_test.py` with:
       - `test_high_confidence` — All artifacts in specialty -> confidence ~1.0, not ambiguous.
       - `test_low_confidence` — Few artifacts in specialty -> ambiguous.
       - `test_threshold_boundary` — confidence exactly at threshold -> not ambiguous (>=, not >).
       - `test_zero_total_artifacts` — All totals 0 -> confidence 0, ambiguous.
       - `test_custom_threshold` — threshold=0.8, moderate mix -> ambiguous.
       - `test_artifact_mix_breakdown` — verify artifact_mix dict contains correct ratios.
       - `test_industry_pivot_pattern` — simulate archetype 2 (Dr. B): few papers in specialty, more trials in different areas -> ambiguous.

    ## Files to modify
    - `src/aegis/scoring/specialty_flag.py` — CREATE.
    - `src/aegis/scoring/specialty_flag_test.py` — CREATE.

    ## Code patterns to follow
    - Frozen Pydantic model for `SpecialtyFlagResult`.
    - `from __future__ import annotations` at top.
    - Module-level constant for threshold (see `_MESH_OVERLAP_THRESHOLD` at `src/aegis/integrity/hard_gate.py:25`).
    - Keyword-only arguments for `flag()` method (see `HardGate.evaluate` at `src/aegis/integrity/hard_gate.py:86`).
    - No scoring effect in Phase 1 — this is purely observability. Document this in the module docstring.

    ## Acceptance criteria
    - `SpecialtyAmbiguityFlagger.flag` returns correct confidence and ambiguity flag.
    - Confidence is a weighted combination of paper/trial/grant specialty ratios.
    - Phase 1 is observability only — flag does not change scores.
    - 7 tests pass.
    - mypy strict and ruff pass.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/specialty_flag_test.py -x -q && python -m mypy --strict src/aegis/scoring/specialty_flag.py && ruff check src/aegis/scoring/specialty_flag.py
    ```

### 10. Update Package __init__ Exports
- **Task ID**: update-init-exports
- **Role**: builder
- **Depends On**: audit-harness, refit-scheduler, cold-start-guard, bootstrap-variance, integrity-contestability, score-collapse, specialty-flag
- **Assigned To**: builder-1
- **Description**: |
    Update all package __init__.py files to export newly created public classes.

    ## What to do

    1. Update `src/aegis/audit/__init__.py` to export:
       ```python
       """Pairwise expert audit harness for collecting reviewer judgments."""

       from aegis.audit.harness import (
           AuditHarness,
           PairSampler,
           PairwisePrompt,
           ScoredCandidate,
           SessionManager,
       )
       from aegis.audit.storage import JudgmentStore, PairwiseJudgment

       __all__ = [
           "AuditHarness",
           "JudgmentStore",
           "PairSampler",
           "PairwiseJudgment",
           "PairwisePrompt",
           "ScoredCandidate",
           "SessionManager",
       ]
       ```

    2. Update `src/aegis/learning/__init__.py` to export:
       ```python
       """Weight learning: Plackett-Luce fitter, refit scheduler, cold-start guard."""

       from aegis.learning.cold_start_guard import ColdStartGuard, GuardVerdict
       from aegis.learning.plackett_luce import (
           FittedWeights,
           JudgmentRecord,
           PlackettLuceFitter,
       )
       from aegis.learning.refit_scheduler import (
           RefitCadence,
           RefitResult,
           RefitScheduler,
       )

       __all__ = [
           "ColdStartGuard",
           "FittedWeights",
           "GuardVerdict",
           "JudgmentRecord",
           "PlackettLuceFitter",
           "RefitCadence",
           "RefitResult",
           "RefitScheduler",
       ]
       ```

    3. Update `src/aegis/scoring/__init__.py` to ADD (do NOT remove existing exports):
       ```python
       from aegis.scoring.score_collapse import CollapseResult, ScoreCollapseHandler
       from aegis.scoring.specialty_flag import SpecialtyAmbiguityFlagger, SpecialtyFlagResult
       from aegis.scoring.variance import Bootstrap, BootstrapInput, ScoreBand
       ```
       And add to `__all__`:
       ```python
       "Bootstrap",
       "BootstrapInput",
       "CollapseResult",
       "ScoreBand",
       "ScoreCollapseHandler",
       "SpecialtyAmbiguityFlagger",
       "SpecialtyFlagResult",
       ```

    4. Update `src/aegis/integrity/__init__.py` to ADD (do NOT remove existing exports):
       ```python
       from aegis.integrity.contestability import (
           ContestabilityStore,
           OverrideAction,
           OverrideRecord,
       )
       ```
       And add to `__all__`:
       ```python
       "ContestabilityStore",
       "OverrideAction",
       "OverrideRecord",
       ```

    5. Verify all imports work by running:
       ```bash
       python -c "from aegis.audit import AuditHarness, JudgmentStore, PairSampler; print('audit OK')"
       python -c "from aegis.learning import PlackettLuceFitter, RefitScheduler, ColdStartGuard; print('learning OK')"
       python -c "from aegis.scoring import Bootstrap, ScoreCollapseHandler, SpecialtyAmbiguityFlagger; print('scoring OK')"
       python -c "from aegis.integrity import ContestabilityStore; print('integrity OK')"
       ```

    ## Files to modify
    - `src/aegis/audit/__init__.py` — UPDATE with full exports.
    - `src/aegis/learning/__init__.py` — UPDATE with full exports.
    - `src/aegis/scoring/__init__.py` — ADD new imports and __all__ entries. Keep ALL existing exports intact.
    - `src/aegis/integrity/__init__.py` — ADD new imports and __all__ entries. Keep ALL existing exports intact.

    ## Code patterns to follow
    - Follow the exact pattern of `src/aegis/scoring/__init__.py` (current contents shown above in Relevant Files). Each import on its own line, sorted alphabetically within the `from` statement. `__all__` list sorted alphabetically.
    - Follow the exact pattern of `src/aegis/integrity/__init__.py` (current contents shown above).
    - `from __future__ import annotations` is NOT used in __init__.py files in this project (check existing files).

    ## Acceptance criteria
    - All 4 __init__.py files export the correct classes.
    - No existing exports removed.
    - All import verification commands succeed.
    - mypy strict passes on all 4 __init__.py files.
    - ruff passes on all 4 files.

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && python -c "from aegis.audit import AuditHarness, JudgmentStore, PairSampler; print('audit OK')" && python -c "from aegis.learning import PlackettLuceFitter, RefitScheduler, ColdStartGuard; print('learning OK')" && python -c "from aegis.scoring import Bootstrap, ScoreCollapseHandler, SpecialtyAmbiguityFlagger; print('scoring OK')" && python -c "from aegis.integrity import ContestabilityStore; print('integrity OK')" && python -m mypy --strict src/aegis/audit/__init__.py src/aegis/learning/__init__.py src/aegis/scoring/__init__.py src/aegis/integrity/__init__.py && ruff check src/aegis/audit/__init__.py src/aegis/learning/__init__.py src/aegis/scoring/__init__.py src/aegis/integrity/__init__.py
    ```

### 11. Full Validation
- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: audit-harness, refit-scheduler, cold-start-guard, bootstrap-variance, integrity-contestability, score-collapse, specialty-flag, update-init-exports
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria.

    ## Validation Commands

    Run each of these commands and verify they pass:

    ```bash
    # 1. Full test suite — must maintain 319/320 baseline (1 pre-existing failure in cohort/audit_test.py::test_daily_summary)
    cd /Users/anvith/aegis && python -m pytest src/ -x -q

    # 2. New audit tests
    cd /Users/anvith/aegis && python -m pytest src/aegis/audit/harness_test.py -v

    # 3. New learning tests
    cd /Users/anvith/aegis && python -m pytest src/aegis/learning/plackett_luce_test.py -v
    cd /Users/anvith/aegis && python -m pytest src/aegis/learning/refit_scheduler_test.py -v
    cd /Users/anvith/aegis && python -m pytest src/aegis/learning/cold_start_guard_test.py -v

    # 4. New scoring tests
    cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/variance_test.py -v
    cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/score_collapse_test.py -v
    cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/specialty_flag_test.py -v

    # 5. New integrity tests
    cd /Users/anvith/aegis && python -m pytest src/aegis/integrity/contestability_test.py -v

    # 6. mypy strict on all new files
    cd /Users/anvith/aegis && python -m mypy --strict src/aegis/audit/ src/aegis/learning/ src/aegis/scoring/variance.py src/aegis/scoring/score_collapse.py src/aegis/scoring/specialty_flag.py src/aegis/integrity/contestability.py

    # 7. ruff on all new files
    cd /Users/anvith/aegis && ruff check src/aegis/audit/ src/aegis/learning/ src/aegis/scoring/variance.py src/aegis/scoring/score_collapse.py src/aegis/scoring/specialty_flag.py src/aegis/integrity/contestability.py

    # 8. Import verification
    cd /Users/anvith/aegis && python -c "from aegis.audit import AuditHarness, JudgmentStore, PairSampler; print('audit OK')"
    cd /Users/anvith/aegis && python -c "from aegis.learning import PlackettLuceFitter, RefitScheduler, ColdStartGuard; print('learning OK')"
    cd /Users/anvith/aegis && python -c "from aegis.scoring import Bootstrap, ScoreCollapseHandler, SpecialtyAmbiguityFlagger; print('scoring OK')"
    cd /Users/anvith/aegis && python -c "from aegis.integrity import ContestabilityStore; print('integrity OK')"
    ```

    ## Acceptance Criteria

    Verify ALL of the following:

    1. **Test baseline preserved**: Full test suite passes at >= 319/320 (the 1 failure in cohort/audit_test.py::test_daily_summary is pre-existing and out of scope).
    2. **Audit harness**: `AuditHarness.next_pair` returns `PairwisePrompt`; `PairSampler` implements active-learning bias; `JudgmentStore` persists as JSONL; `inter_reviewer_kappa` computes kappa. 7+ harness tests pass.
    3. **Plackett-Luce fitter**: `PlackettLuceFitter.fit` returns `FittedWeights` with CIs; recovers known parameters on synthetic data within +/-0.15; bounds enforced. 6+ tests pass.
    4. **Refit scheduler**: `RefitScheduler.should_refit` respects cadence; `execute_refit` writes valid YAML; rollback loads prior versions. 5+ tests pass.
    5. **Cold-start guard**: `ColdStartGuard.evaluate` blocks wide CIs, non-convergence, and insufficient judgments. 5+ tests pass.
    6. **Bootstrap variance**: `Bootstrap.estimate` returns per-candidate `ScoreBand`; low <= median <= high; CIs bracket truth >= 90%. 6+ tests pass.
    7. **Integrity contestability**: `ContestabilityStore` persists overrides as append-only JSONL; `is_overridden` resolves latest action correctly. 6+ tests pass.
    8. **Score-collapse handler**: `ScoreCollapseHandler` detects all-below-floor; `expand_mesh` adds parent terms; `handle_collapse` returns correct flags. 8+ tests pass.
    9. **Specialty-ambiguity flag**: `SpecialtyAmbiguityFlagger.flag` returns correct confidence and flag; observability only. 7+ tests pass.
    10. **Package exports**: All 4 __init__.py files updated; all import verifications succeed; no existing exports removed.
    11. **Type safety**: mypy strict passes on all new files with zero errors.
    12. **Linting**: ruff passes on all new files.

    If any criterion fails, create a fix task describing exactly what failed and what needs to be fixed, assigned to the appropriate builder.

### 12. Update Design Document
- **Task ID**: update-design-scoring
- **Role**: design-updater
- **Depends On**: validate-all
- **Assigned To**: design-updater
- **Description**: |
    Update the living design document for the scoring domain to reflect
    what was actually built in Phase 1c.

    ## Target Design Doc
    docs/design/scoring.md

    ## Spec File
    specs/aegis-phase1c-audit-learning.md

    ## Scope
    This build adds: (1) audit harness with pair sampling and judgment storage, (2) Plackett-Luce weight learning with refit scheduler, (3) bootstrap score-variance estimation, (4) cold-start guard, (5) integrity contestability, (6) score-collapse handling, (7) specialty-ambiguity flag.

    New packages: `src/aegis/audit/`, `src/aegis/learning/`.
    New modules in existing packages: `src/aegis/scoring/variance.py`, `src/aegis/scoring/score_collapse.py`, `src/aegis/scoring/specialty_flag.py`, `src/aegis/integrity/contestability.py`.

    ## Prior Decisions to Check
    - "Versioned Weight Configuration via YAML" (2026-04-26) — the refit scheduler now writes new version files. Verify this decision still holds and document the new versioning workflow.
    - "In-Memory Source Stores for Phase 1" — the audit judgment store and contestability store use JSONL files, not in-memory stores. Document this new pattern choice.
    - "Geometric-Mean Composition for Q(c)" — the Plackett-Luce fitter optimizes the exponents in the Rank formula, not the geometric-mean weights. Document the distinction clearly.

    ## What to Record
    Read `git diff HEAD~1 HEAD`, then the changed source files, then the existing
    design doc. Update Current Design to match the implementation:
    - Add the audit, learning, and new scoring/integrity modules to the Architecture diagram.
    - Add new files to the Key Files table.
    - Add new patterns (JSONL append-only stores, active-learning pair sampling, scipy L-BFGS-B optimization, bootstrap resampling).
    - Update the Data Flow section with the learning loop.
    - Append Design Decision entries for each non-trivial architectural choice:
      - Plackett-Luce vs Bradley-Terry for weight learning
      - JSONL vs database for audit trail persistence
      - Active-learning bias for pair sampling
      - Multivariate normal posterior approximation for bootstrap
      - Rule-based specialty classifier (Phase 1)
      - Append-only override pattern for contestability
    - Every claim must cite a `file:line` from the actual code.

## Acceptance Criteria

1. Full test suite passes at >= 319/320 (pre-existing failure in `cohort/audit_test.py::test_daily_summary` is out of scope).
2. All 7 new test files pass with the specified minimum test counts:
   - `harness_test.py`: 10+ tests (3 storage + 7 harness)
   - `plackett_luce_test.py`: 6+ tests
   - `refit_scheduler_test.py`: 5+ tests
   - `cold_start_guard_test.py`: 5+ tests
   - `variance_test.py`: 6+ tests
   - `contestability_test.py`: 6+ tests
   - `score_collapse_test.py`: 8+ tests
   - `specialty_flag_test.py`: 7+ tests
3. Plackett-Luce fitter recovers known parameters within +/-0.15 on synthetic data.
4. Bootstrap CI brackets ground-truth scores >= 90% of the time.
5. Cold-start guard blocks deployment when CI half-width > threshold.
6. Contestability overrides are append-only and correctly resolve latest action.
7. Score-collapse handler detects all-below-floor and produces expanded MeSH terms.
8. All 4 package `__init__.py` files updated with new exports; no existing exports removed.
9. `mypy --strict` passes on all new files.
10. `ruff check` passes on all new files.
11. `docs/design/scoring.md` updated with Phase 1c additions.

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# Full test suite (baseline: 319/320, 1 pre-existing failure)
cd /Users/anvith/aegis && python -m pytest src/ -x -q

# All new test files individually
cd /Users/anvith/aegis && python -m pytest src/aegis/audit/harness_test.py -v
cd /Users/anvith/aegis && python -m pytest src/aegis/learning/plackett_luce_test.py -v
cd /Users/anvith/aegis && python -m pytest src/aegis/learning/refit_scheduler_test.py -v
cd /Users/anvith/aegis && python -m pytest src/aegis/learning/cold_start_guard_test.py -v
cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/variance_test.py -v
cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/score_collapse_test.py -v
cd /Users/anvith/aegis && python -m pytest src/aegis/scoring/specialty_flag_test.py -v
cd /Users/anvith/aegis && python -m pytest src/aegis/integrity/contestability_test.py -v

# mypy strict on all new files
cd /Users/anvith/aegis && python -m mypy --strict src/aegis/audit/ src/aegis/learning/ src/aegis/scoring/variance.py src/aegis/scoring/score_collapse.py src/aegis/scoring/specialty_flag.py src/aegis/integrity/contestability.py

# ruff on all new files
cd /Users/anvith/aegis && ruff check src/aegis/audit/ src/aegis/learning/ src/aegis/scoring/variance.py src/aegis/scoring/score_collapse.py src/aegis/scoring/specialty_flag.py src/aegis/integrity/contestability.py

# Import verification
cd /Users/anvith/aegis && python -c "from aegis.audit import AuditHarness, JudgmentStore, PairSampler; print('audit OK')"
cd /Users/anvith/aegis && python -c "from aegis.learning import PlackettLuceFitter, RefitScheduler, ColdStartGuard; print('learning OK')"
cd /Users/anvith/aegis && python -c "from aegis.scoring import Bootstrap, ScoreCollapseHandler, SpecialtyAmbiguityFlagger; print('scoring OK')"
cd /Users/anvith/aegis && python -c "from aegis.integrity import ContestabilityStore; print('integrity OK')"
```

## Notes

- **No new dependencies needed**: scipy and numpy are already in `pyproject.toml`.
- **No web UI in Phase 1**: Task 1.13 mentions a local web UI for reviewers (`src/aegis/audit/ui/`). In Phase 1, we build the data layer only. The UI directory is deferred to Phase 2/3. The `AuditHarness` and `PairSampler` provide the API that a future UI will consume.
- **Family weight learning deferred**: The Plackett-Luce fitter in Phase 1 only fits the three exponents (alpha, beta, gamma). Per-family weight optimization (f1_rcr through f6_lineage weights) is deferred to Phase 2 when more judgment data is available.
- **JSONL as persistence**: Both the audit judgment store and the contestability override store use JSONL files rather than a database. This is consistent with the Phase 1 philosophy of simple, auditable storage. Phase 3 will migrate to a proper database.
- **MeSH parent map**: The score-collapse handler uses a hardcoded MeSH parent map for Phase 1. In production, this would be loaded from the full MeSH tree hierarchy file. The hardcoded map is sufficient for testing the collapse-and-expand logic.
