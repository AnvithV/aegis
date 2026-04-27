# Plan: Phase 2c — Weight Vectors + F7 Clinician Score + CPC Caching

> **Status:** COMPLETE (2026-04-26)
> All 7 tasks completed. 31/31 Phase 2c tests passing + 8/8 existing scoring tests passing. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-26
> **Team:** weight-vectors-20260426-2245

### Test Results
- `src/aegis/scoring/f7_clinician_test.py` — 15/15 PASSED
- `src/aegis/taxonomy/cpc_xwalk_cache_test.py` — 8/8 PASSED
- `src/aegis/scoring/weight_integration_test.py` — 8/8 PASSED
- `src/aegis/scoring/quality_prior_test.py` (existing) — 8/8 PASSED

### Validation Commands
- `uv run pytest ... -v` (Phase 2c tests) — **PASS** (31/31 in 0.16s)
- `uv run mypy` (4 new modules) — **PASS** ("Success: no issues found in 4 source files")
- `uv run ruff check` (4 new modules) — **PASS** ("All checks passed!")
- `uv run pytest quality_prior_test.py -v` (existing tests) — **PASS** (8/8 in 0.13s)

### Acceptance Criteria Verification
- [x] `config/aegis/weights/drug_discovery_v1.yaml` exists with weights (F1 .15, F2 .05, F3 .15, F4 .05, F5 .50, F6 .10) summing to 1.0 — VERIFIED (file exists, weights confirmed from YAML: 0.15+0.05+0.15+0.05+0.50+0.10=1.00)
- [x] `config/aegis/weights/clinician_v1.yaml` exists with weights (F1 .15, F2 .10, F3 .25, F4 .05, F5 .15, F6 .05, F7 .25) summing to 1.0 — VERIFIED (file exists, 7 families, 0.15+0.10+0.25+0.05+0.15+0.05+0.25=1.00)
- [x] `F7Computer` at `src/aegis/scoring/f7_clinician.py` computes clinician-specific score with sub-components: board certification, license, hospital tier, trial PI, procedure volume — VERIFIED (class F7Computer at line 65, all 5 sub-components present with weights summing to 1.0)
- [x] `QualityPrior` correctly handles both 6-family and 7-family weight vectors — VERIFIED (test_quality_prior_6_families and test_quality_prior_7_families both pass)
- [x] Drug-discovery: F5-dominant candidate scores higher than F2-dominant under drug-discovery weights — VERIFIED (test_quality_prior_drug_discovery_f5_dominant passes)
- [x] Clinician: high F7 meaningfully impacts Q(c) under clinician weights — VERIFIED (test_quality_prior_clinician_f7_matters passes)
- [x] `CpcXwalkCache` provides warm lookup p99 < 1ms on 1000 cached entries — VERIFIED (test_warm_cache_performance passes, class at line 41 of cpc_xwalk_cache.py)
- [x] Cache version-keyed invalidation works — VERIFIED (test_version_isolation and test_invalidate_version both pass)
- [x] All new tests pass — VERIFIED (31/31 passed)
- [x] mypy strict mode passes on all new modules — VERIFIED ("Success: no issues found in 4 source files")
- [x] ruff lint passes on all new modules — VERIFIED ("All checks passed!")
- [x] Existing Phase 1 scoring tests unbroken — VERIFIED (quality_prior_test.py: 8/8 passed)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `config/aegis/weights/drug_discovery_v1.yaml` | Created | Yes |
| `config/aegis/weights/clinician_v1.yaml` | Created | Yes |
| `src/aegis/scoring/drug_discovery_weights.py` | Created | Yes |
| `src/aegis/scoring/clinician_weights.py` | Created | Yes |
| `src/aegis/scoring/f7_clinician.py` | Created | Yes |
| `src/aegis/scoring/f7_clinician_test.py` | Created | Yes |
| `src/aegis/taxonomy/cpc_xwalk_cache.py` | Created | Yes |
| `src/aegis/taxonomy/cpc_xwalk_cache_test.py` | Created | Yes |
| `src/aegis/scoring/weight_integration_test.py` | Created | Yes |
| `src/aegis/scoring/__init__.py` | Modified | Yes (exports: F7Computer, F7Score, load_drug_discovery_weights, load_clinician_weights) |
| `src/aegis/taxonomy/__init__.py` | Modified | Yes (exports: CpcXwalkCache, CacheStats) |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase2c-weight-vectors.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Implement the drug-discovery weight vector, the clinician weight vector with the new F7 clinician-specific score family, and CPC cross-walk caching. This sub-spec wires the new population-specific weight vectors into the existing `QualityPrior` composition layer and creates the F7 scoring module that synthesizes ABMS board certification, state medical board license status, hospital tier, clinical-trial PI roles, and procedure-volume proxies into a percentile-calibrated clinician score.

This plan covers Phase 2 tasks: **1.10** (drug-discovery weight vector), **1.11** (clinician weight vector + F7), and **4.3** (CPC cross-walk caching).

## Objective

When this plan is complete:
1. A drug-discovery weight vector `drug_discovery_v1.yaml` exists with weights `(F1 .15, F2 .05, F3 .15, F4 .05, F5 .50, F6 .10)` and is registered in the weight-version system.
2. A clinician weight vector `clinician_v1.yaml` exists with weights `(F1 .15, F2 .10, F3 .25, F4 .05, F5 .15, F6 .05)` plus F7 = 0.25.
3. An `F7Computer` at `src/aegis/scoring/f7_clinician.py` computes the clinician-specific F7 score from ABMS certification, license status, hospital tier, clinical-trial PI roles, and procedure-volume proxies.
4. The `QualityPrior` composition correctly handles 6-family (translational/drug-discovery) and 7-family (clinician) weight vectors.
5. A CPC cross-walk cache at `src/aegis/taxonomy/cpc_xwalk_cache.py` provides SQLite-backed caching with p99 < 1ms warm lookups and quarterly version-bump invalidation.
6. All modules pass mypy strict, ruff lint, and have unit tests.

## Problem Statement

Phase 1 scoring operates on a single translational weight vector. Drug-discovery candidates need F5 (translational impact, now including patents) weighted at 0.50 — the dominant signal. Clinician candidates need a wholly new F7 score family that does not exist in Phase 1: board certification, license status, hospital tier, procedure volumes. The existing `QualityPrior` in `quality_prior.py` expects exactly 6 F-families; it must be extended to handle F7. Additionally, the CPC-MeSH cross-walk LLM fallback is too slow for per-patent lookups at bulk scale; a cache layer is needed.

## Solution Approach

1. **Weight configs**: Create two new YAML weight configs alongside the existing `translational_v1.yaml`.
2. **F7 module**: Build `f7_clinician.py` following the same `FNComputer` / `FNScore` pattern as F1-F6.
3. **QualityPrior extension**: The existing geometric-mean composition is weight-key-driven (iterates `weights.keys()`), so it naturally handles any number of families. We just need to ensure F7 is included in clinician weight configs and that the composition layer accepts 7-family inputs.
4. **CPC cache**: SQLite-backed lookup cache with version-keyed invalidation.

## Relevant Files

### Existing Files
- `config/aegis/weights/translational_v1.yaml` — Existing weight config (pattern to follow)
- `src/aegis/scoring/quality_prior.py` — `QualityPrior`, `WeightVector`, `QualityScore`, `load_weight_vector`
- `src/aegis/scoring/f1_rcr.py` through `src/aegis/scoring/f6_lineage.py` — Existing F-score modules (pattern to follow)
- `src/aegis/scoring/__init__.py` — Scoring package exports (will be modified)
- `src/aegis/taxonomy/cpc_mesh_xwalk.py` — CPC-MeSH cross-walk (created in Phase 2a)
- `src/aegis/sources/abms.py` — ABMS certification client (created in Phase 2b)
- `src/aegis/sources/usnwr.py` — Hospital tier (created in Phase 2b)
- `src/aegis/sources/state_medical_boards/registry.py` — State board actions (created in Phase 2b)
- `src/aegis/sources/cms_ppsas.py` — CMS procedure-volume data (created in Phase 2b)
- `src/aegis/storage/schema.py` — `Candidate`, `MeshDescriptor`

### New Files
- `config/aegis/weights/drug_discovery_v1.yaml` — Drug-discovery weight vector
- `config/aegis/weights/clinician_v1.yaml` — Clinician weight vector (includes F7)
- `src/aegis/scoring/drug_discovery_weights.py` — Drug-discovery weight vector loader + validation
- `src/aegis/scoring/clinician_weights.py` — Clinician weight vector loader + validation
- `src/aegis/scoring/f7_clinician.py` — F7 clinician-specific score
- `src/aegis/scoring/f7_clinician_test.py` — F7 tests
- `src/aegis/taxonomy/cpc_xwalk_cache.py` — CPC cross-walk cache
- `src/aegis/taxonomy/cpc_xwalk_cache_test.py` — Cache tests

## Implementation Phases

### Phase 1: Foundation
- Create drug-discovery and clinician weight config YAMLs
- Create weight vector loader/validation modules

### Phase 2: Core Implementation
- Build F7 clinician score module
- Extend QualityPrior to handle 7-family weights
- Build CPC cross-walk cache

### Phase 3: Integration & Polish
- Update scoring package exports
- Verify all F-families compose correctly under each weight vector
- Run full validation suite

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Weight config YAMLs, weight vector loaders, F7 clinician score, QualityPrior extension for 7-family weights
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: CPC cross-walk cache, integration tests
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

### 1. Drug-Discovery Weight Vector Config + Loader

- **Task ID**: drug-discovery-weights
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the drug-discovery weight vector YAML config and a validation module.

    ## What to do

    1. Create `config/aegis/weights/drug_discovery_v1.yaml`:
       ```yaml
       # Drug-discovery specialty weight vector v1
       # Weights sum to 1.0; F5 (translational impact, including patents) is dominant
       # for this population — medicinal chemists, structural biologists, DMPK/ADMET
       version: 1
       specialty: drug_discovery
       created: "2026-04-26"
       weights:
         f1_rcr: 0.15
         f2_funding: 0.05
         f3_leadership: 0.15
         f4_apex: 0.05
         f5_translational: 0.50
         f6_lineage: 0.10
       exponents:
         alpha: 0.7
         beta: 1.0
         gamma: 0.4
       exponent_bounds:
         alpha: [0.3, 1.2]
         beta: [0.5, 1.5]
         gamma: [0.1, 0.8]
       ```

    2. Create `src/aegis/scoring/drug_discovery_weights.py`:

       ```python
       """Drug-discovery weight vector loader and validation."""

       from __future__ import annotations

       from pathlib import Path

       from aegis.scoring.quality_prior import WeightVector, load_weight_vector

       _DEFAULT_PATH = Path("config/aegis/weights/drug_discovery_v1.yaml")

       # Expected weight distribution for drug-discovery population
       _EXPECTED_WEIGHTS = {
           "f1_rcr": 0.15,
           "f2_funding": 0.05,
           "f3_leadership": 0.15,
           "f4_apex": 0.05,
           "f5_translational": 0.50,
           "f6_lineage": 0.10,
       }


       def load_drug_discovery_weights(
           config_path: Path | None = None,
       ) -> WeightVector:
           """Load the drug-discovery weight vector from YAML.

           Validates that weights sum to 1.0 and specialty is 'drug_discovery'.
           """
           wv = load_weight_vector(config_path or _DEFAULT_PATH)
           assert wv.specialty == "drug_discovery", (
               f"Expected specialty 'drug_discovery', got '{wv.specialty}'"
           )
           total = sum(wv.weights.values())
           assert abs(total - 1.0) < 0.001, (
               f"Weights must sum to 1.0, got {total}"
           )
           return wv


       def validate_drug_discovery_weights(wv: WeightVector) -> list[str]:
           """Validate a drug-discovery weight vector against expectations.

           Returns list of warnings (empty if all good).
           """
           warnings: list[str] = []
           if wv.weights.get("f5_translational", 0) < 0.3:
               warnings.append(
                   "F5 (translational) should dominate for drug-discovery "
                   f"(got {wv.weights.get('f5_translational', 0)})"
               )
           if wv.weights.get("f2_funding", 0) > 0.15:
               warnings.append(
                   "F2 (funding) should be low for drug-discovery — "
                   "industry researchers have minimal NIH funding"
               )
           return warnings
       ```

    3. Verify YAML loads correctly and weights sum to 1.0.

    ## Files to create
    - `config/aegis/weights/drug_discovery_v1.yaml`
    - `src/aegis/scoring/drug_discovery_weights.py`

    ## Code patterns to follow
    - YAML format matches `config/aegis/weights/translational_v1.yaml` exactly
    - Uses `load_weight_vector` from `quality_prior.py`
    - `from __future__ import annotations`

    ## Acceptance criteria
    - `config/aegis/weights/drug_discovery_v1.yaml` exists with correct weights
    - Weights sum to 1.0
    - F5 weight is 0.50 (dominant)
    - `load_drug_discovery_weights()` returns a valid `WeightVector`
    - mypy passes: `uv run mypy src/aegis/scoring/drug_discovery_weights.py`
    - ruff passes: `uv run ruff check src/aegis/scoring/drug_discovery_weights.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.scoring.drug_discovery_weights import load_drug_discovery_weights; wv = load_drug_discovery_weights(); assert abs(sum(wv.weights.values()) - 1.0) < 0.001; assert wv.weights['f5_translational'] == 0.50; print('Drug-discovery weights OK')" && uv run mypy src/aegis/scoring/drug_discovery_weights.py && uv run ruff check src/aegis/scoring/drug_discovery_weights.py
    ```

### 2. Clinician Weight Vector Config + Loader

- **Task ID**: clinician-weights
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the clinician weight vector YAML config (with F7) and a validation module.

    ## What to do

    1. Create `config/aegis/weights/clinician_v1.yaml`:
       ```yaml
       # Clinician specialty weight vector v1
       # Weights sum to 1.0; includes F7 (clinician-specific family) at 0.25
       # F3 (leadership) is high because clinical leadership signals are strong
       version: 1
       specialty: clinician
       created: "2026-04-26"
       weights:
         f1_rcr: 0.15
         f2_funding: 0.10
         f3_leadership: 0.25
         f4_apex: 0.05
         f5_translational: 0.15
         f6_lineage: 0.05
         f7_clinician: 0.25
       exponents:
         alpha: 0.7
         beta: 1.0
         gamma: 0.4
       exponent_bounds:
         alpha: [0.3, 1.2]
         beta: [0.5, 1.5]
         gamma: [0.1, 0.8]
       ```

    2. Create `src/aegis/scoring/clinician_weights.py`:

       ```python
       """Clinician weight vector loader and validation."""

       from __future__ import annotations

       from pathlib import Path

       from aegis.scoring.quality_prior import WeightVector, load_weight_vector

       _DEFAULT_PATH = Path("config/aegis/weights/clinician_v1.yaml")


       def load_clinician_weights(
           config_path: Path | None = None,
       ) -> WeightVector:
           """Load the clinician weight vector from YAML.

           Validates that weights sum to 1.0, specialty is 'clinician',
           and F7 is present.
           """
           wv = load_weight_vector(config_path or _DEFAULT_PATH)
           assert wv.specialty == "clinician", (
               f"Expected specialty 'clinician', got '{wv.specialty}'"
           )
           total = sum(wv.weights.values())
           assert abs(total - 1.0) < 0.001, (
               f"Weights must sum to 1.0, got {total}"
           )
           assert "f7_clinician" in wv.weights, (
               "Clinician weight vector must include f7_clinician"
           )
           return wv


       def validate_clinician_weights(wv: WeightVector) -> list[str]:
           """Validate a clinician weight vector against expectations.

           Returns list of warnings (empty if all good).
           """
           warnings: list[str] = []
           if "f7_clinician" not in wv.weights:
               warnings.append("Missing f7_clinician weight")
           elif wv.weights["f7_clinician"] < 0.1:
               warnings.append(
                   f"F7 weight unexpectedly low ({wv.weights['f7_clinician']})"
               )
           if wv.weights.get("f3_leadership", 0) < 0.15:
               warnings.append(
                   "F3 (leadership) should be significant for clinicians"
               )
           return warnings
       ```

    ## Files to create
    - `config/aegis/weights/clinician_v1.yaml`
    - `src/aegis/scoring/clinician_weights.py`

    ## Code patterns to follow
    - YAML format matches `config/aegis/weights/translational_v1.yaml`
    - 7-family weight vector (F1-F7) instead of 6
    - Uses `load_weight_vector` from `quality_prior.py`

    ## Acceptance criteria
    - `config/aegis/weights/clinician_v1.yaml` exists with F7 at 0.25
    - All 7 weights sum to 1.0
    - `load_clinician_weights()` returns `WeightVector` with `f7_clinician` key
    - mypy passes: `uv run mypy src/aegis/scoring/clinician_weights.py`
    - ruff passes: `uv run ruff check src/aegis/scoring/clinician_weights.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.scoring.clinician_weights import load_clinician_weights; wv = load_clinician_weights(); assert abs(sum(wv.weights.values()) - 1.0) < 0.001; assert 'f7_clinician' in wv.weights; assert wv.weights['f7_clinician'] == 0.25; print('Clinician weights OK')" && uv run mypy src/aegis/scoring/clinician_weights.py && uv run ruff check src/aegis/scoring/clinician_weights.py
    ```

### 3. F7 Clinician Score Module

- **Task ID**: f7-clinician
- **Role**: builder
- **Depends On**: clinician-weights
- **Assigned To**: builder-1
- **Description**: |
    Build the F7 clinician-specific score module: a weighted composition of ABMS board certification, active license status, hospital tier, clinical-trial PI roles, and procedure-volume proxies, percentile-calibrated within the clinician cohort.

    ## What to do

    1. Create `src/aegis/scoring/f7_clinician.py`:

       ```python
       """F7 sub-score: clinician-specific family (board cert, license, hospital tier, trials, volumes)."""

       from __future__ import annotations

       import logging
       from dataclasses import dataclass

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       # F7 sub-component weights (sum to 1.0 within F7)
       _W_BOARD_CERT = 0.30
       _W_LICENSE = 0.15
       _W_HOSPITAL_TIER = 0.25
       _W_TRIAL_PI = 0.15
       _W_PROCEDURE_VOLUME = 0.15


       class F7Score(BaseModel):
           """Result of F7 computation for a single clinician candidate."""

           model_config = ConfigDict(frozen=True)

           board_certification_score: float    # 0.0-1.0
           license_score: float                # 0.0-1.0 (1.0 = active, clean)
           hospital_tier_score: float           # 0.0-1.0 (tier 1 = 1.0)
           trial_pi_score: float               # 0.0-1.0
           procedure_volume_score: float        # 0.0-1.0
           procedure_volume_confidence: float   # 0.0-1.0 (data coverage)
           percentile: float                    # percentile within clinician cohort [0, 1]
           coverage_caveat: str | None


       @dataclass
       class ClinicianInput:
           """Raw inputs for F7 scoring."""

           # Board certification
           is_board_certified: bool
           has_moc: bool                   # Maintenance of Certification
           certification_count: int         # Number of board certifications

           # License
           has_active_license: bool
           has_disciplinary_action: bool
           action_severity: str | None     # "revocation", "suspension", etc.

           # Hospital tier
           hospital_tier: int              # 1, 2, 3, or 0 (unranked)
           specialty_rank: int | None      # Specialty-specific rank if applicable

           # Clinical trials
           trial_pi_count: int             # As PI on clinical trials
           trial_phases: list[int]         # Phases of trials (2, 3, etc.)

           # Procedure volume
           total_procedures: int           # From CMS data
           procedure_volume_available: bool # Whether CMS data exists


       class F7Computer:
           """Compute F7 sub-score (clinician-specific family) for candidates."""

           def score_raw(
               self,
               inp: ClinicianInput,
           ) -> tuple[float, float, float, float, float, float, str | None]:
               """Compute raw F7 component scores (before percentile).

               Returns (board_cert, license, hospital_tier, trial_pi,
                        procedure_volume, volume_confidence, coverage_caveat).
               """
               # Board certification score
               board_cert = 0.0
               if inp.is_board_certified:
                   board_cert = 0.7
                   if inp.has_moc:
                       board_cert = 1.0
                   # Bonus for multiple certifications
                   if inp.certification_count > 1:
                       board_cert = min(board_cert + 0.1 * (inp.certification_count - 1), 1.0)

               # License score
               license_score = 0.0
               if inp.has_active_license:
                   license_score = 1.0
                   if inp.has_disciplinary_action:
                       # Severity-dependent penalty (but not gating — gating is integrity-only)
                       if inp.action_severity in ("revocation", "suspension"):
                           license_score = 0.1
                       elif inp.action_severity in ("restriction", "probation"):
                           license_score = 0.5
                       elif inp.action_severity == "public_reprimand":
                           license_score = 0.7

               # Hospital tier score
               tier_map = {1: 1.0, 2: 0.7, 3: 0.4, 0: 0.2}
               hospital_tier = tier_map.get(inp.hospital_tier, 0.2)
               if inp.specialty_rank is not None and inp.specialty_rank <= 5:
                   hospital_tier = max(hospital_tier, 0.9)

               # Clinical trial PI score
               trial_pi = 0.0
               if inp.trial_pi_count > 0:
                   trial_pi = min(inp.trial_pi_count / 5.0, 1.0)
                   # Bonus for Phase 3+ trials
                   has_late_phase = any(p >= 3 for p in inp.trial_phases)
                   if has_late_phase:
                       trial_pi = min(trial_pi + 0.2, 1.0)

               # Procedure volume score
               volume_confidence = 1.0 if inp.procedure_volume_available else 0.3
               procedure_volume = 0.0
               coverage_caveat: str | None = None
               if inp.procedure_volume_available:
                   # Normalize: top-decile is ~500+ procedures/year for most specialties
                   procedure_volume = min(inp.total_procedures / 500.0, 1.0)
               else:
                   coverage_caveat = (
                       "Procedure volume data unavailable; "
                       "score based on available signals only"
                   )

               return (
                   board_cert,
                   license_score,
                   hospital_tier,
                   trial_pi,
                   procedure_volume,
                   volume_confidence,
                   coverage_caveat,
               )

           def compute_composite(
               self,
               board_cert: float,
               license_score: float,
               hospital_tier: float,
               trial_pi: float,
               procedure_volume: float,
           ) -> float:
               """Compute weighted composite F7 score."""
               return (
                   _W_BOARD_CERT * board_cert
                   + _W_LICENSE * license_score
                   + _W_HOSPITAL_TIER * hospital_tier
                   + _W_TRIAL_PI * trial_pi
                   + _W_PROCEDURE_VOLUME * procedure_volume
               )

           def compute_percentiles(
               self,
               raw_scores: list[tuple[str, float, float, float, float, float, float, str | None]],
           ) -> dict[str, F7Score]:
               """Compute percentile-ranked F7 scores for a clinician cohort.

               Each entry: (uuid, board_cert, license, hospital_tier, trial_pi,
                           procedure_volume, volume_confidence, coverage_caveat).
               """
               if not raw_scores:
                   return {}

               # Compute composites for ranking
               composites: list[tuple[str, float]] = []
               for (
                   uuid, board_cert, license_s, hosp_tier,
                   trial_pi, proc_vol, _vol_conf, _caveat,
               ) in raw_scores:
                   composite = self.compute_composite(
                       board_cert, license_s, hosp_tier, trial_pi, proc_vol
                   )
                   composites.append((uuid, composite))

               # Sort for percentile assignment
               sorted_composites = sorted(composites, key=lambda x: x[1])
               n = len(sorted_composites)
               rank_map: dict[str, float] = {}
               for rank_idx, (uuid, _) in enumerate(sorted_composites):
                   rank_map[uuid] = (rank_idx + 0.5) / n

               # Build result
               result: dict[str, F7Score] = {}
               for (
                   uuid, board_cert, license_s, hosp_tier,
                   trial_pi, proc_vol, vol_conf, caveat,
               ) in raw_scores:
                   result[uuid] = F7Score(
                       board_certification_score=round(board_cert, 4),
                       license_score=round(license_s, 4),
                       hospital_tier_score=round(hosp_tier, 4),
                       trial_pi_score=round(trial_pi, 4),
                       procedure_volume_score=round(proc_vol, 4),
                       procedure_volume_confidence=round(vol_conf, 4),
                       percentile=round(rank_map[uuid], 6),
                       coverage_caveat=caveat,
                   )

               return result
       ```

    2. Create `src/aegis/scoring/f7_clinician_test.py`:
       - `test_board_certified_with_moc`: Board certified + MOC -> score 1.0
       - `test_board_certified_no_moc`: Board certified, no MOC -> score 0.7
       - `test_not_board_certified`: Not certified -> score 0.0
       - `test_multiple_certifications`: 3 certifications -> bonus
       - `test_active_license_clean`: Active license, no actions -> 1.0
       - `test_license_with_suspension`: Active + suspension -> 0.1
       - `test_license_with_probation`: Active + probation -> 0.5
       - `test_hospital_tier_1`: Tier 1 -> 1.0
       - `test_hospital_tier_unranked`: Tier 0 -> 0.2
       - `test_specialty_rank_override`: Specialty rank <= 5 overrides to >= 0.9
       - `test_trial_pi_with_phase3`: PI on Phase 3 trial -> bonus
       - `test_procedure_volume_available`: Volume data -> computed score
       - `test_procedure_volume_missing`: No volume data -> caveat string
       - `test_percentile_uniform`: 100 synthetic clinicians -> approximately uniform percentile distribution
       - `test_composite_weights_sum`: Sub-component weights sum to 1.0

    3. Update `src/aegis/scoring/__init__.py` to add exports: `F7Computer`, `F7Score`.

    ## Files to create
    - `src/aegis/scoring/f7_clinician.py`
    - `src/aegis/scoring/f7_clinician_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` — add F7 exports

    ## Code patterns to follow
    - Follow exact pattern from `src/aegis/scoring/f3_leadership.py` and other F-score modules:
      - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for `F7Score`
      - `@dataclass` for raw input
      - `score_raw()` -> tuple, `compute_percentiles()` -> dict
      - Midpoint percentile: `(rank_idx + 0.5) / n`
    - `from __future__ import annotations`
    - Logger at module level

    ## Acceptance criteria
    - `F7Computer.score(candidate) -> F7Score` pattern works (via score_raw + compute_percentiles)
    - F7 sub-component weights sum to 1.0 (_W_BOARD_CERT + _W_LICENSE + _W_HOSPITAL_TIER + _W_TRIAL_PI + _W_PROCEDURE_VOLUME = 1.0)
    - Board certification scoring: certified+MOC=1.0, certified-no-MOC=0.7, not-certified=0.0
    - Hospital tier: tier1=1.0, tier2=0.7, tier3=0.4, unranked=0.2
    - Percentile distribution approximately uniform on synthetic cohort
    - All tests pass: `uv run pytest src/aegis/scoring/f7_clinician_test.py -v`
    - mypy passes: `uv run mypy src/aegis/scoring/f7_clinician.py`
    - ruff passes: `uv run ruff check src/aegis/scoring/f7_clinician.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f7_clinician_test.py -v && uv run mypy src/aegis/scoring/f7_clinician.py && uv run ruff check src/aegis/scoring/f7_clinician.py
    ```

### 4. CPC Cross-walk Cache

- **Task ID**: cpc-xwalk-cache
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build a SQLite-backed cache for CPC-to-MeSH cross-walk lookups. The LLM fallback path is too slow for per-patent lookups at bulk scale; this cache provides p99 < 1ms warm lookups with version-keyed invalidation on quarterly cross-walk updates.

    ## What to do

    1. Create `src/aegis/taxonomy/cpc_xwalk_cache.py`:

       ```python
       """CPC cross-walk cache: SQLite-backed caching with version-keyed invalidation."""

       from __future__ import annotations

       import json
       import logging
       import sqlite3
       from pathlib import Path

       from pydantic import BaseModel, ConfigDict

       from aegis.storage.schema import MeshDescriptor

       logger = logging.getLogger(__name__)

       _DEFAULT_CACHE_PATH = Path("data/aegis/cpc_xwalk_cache.db")

       _CREATE_TABLE = """
       CREATE TABLE IF NOT EXISTS cpc_cache (
           cpc_code TEXT NOT NULL,
           version TEXT NOT NULL,
           mesh_json TEXT NOT NULL,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           PRIMARY KEY (cpc_code, version)
       );
       """


       class CacheStats(BaseModel):
           """Cache performance statistics."""

           model_config = ConfigDict(frozen=True)

           total_entries: int
           version: str
           hit_count: int
           miss_count: int
           hit_rate: float


       class CpcXwalkCache:
           """SQLite-backed cache for CPC-to-MeSH cross-walk lookups.

           Cache invalidation: on version bump (quarterly), old entries
           are retained but lookups use the current version only.
           """

           def __init__(
               self,
               cache_path: Path | None = None,
               version: str = "v1",
           ) -> None:
               self._path = cache_path or _DEFAULT_CACHE_PATH
               self._version = version
               self._hits = 0
               self._misses = 0
               self._conn = sqlite3.connect(str(self._path))
               self._conn.execute(_CREATE_TABLE)
               self._conn.execute("PRAGMA journal_mode=WAL")

           def get(
               self, cpc_code: str
           ) -> list[tuple[MeshDescriptor, float]] | None:
               """Look up cached CPC-to-MeSH translation.

               Returns None on cache miss.
               """
               cursor = self._conn.execute(
                   "SELECT mesh_json FROM cpc_cache WHERE cpc_code = ? AND version = ?",
                   (cpc_code, self._version),
               )
               row = cursor.fetchone()
               if row is None:
                   self._misses += 1
                   return None

               self._hits += 1
               return self._deserialize(row[0])

           def put(
               self,
               cpc_code: str,
               mappings: list[tuple[MeshDescriptor, float]],
           ) -> None:
               """Cache a CPC-to-MeSH translation result."""
               mesh_json = self._serialize(mappings)
               self._conn.execute(
                   """
                   INSERT OR REPLACE INTO cpc_cache (cpc_code, version, mesh_json)
                   VALUES (?, ?, ?)
                   """,
                   (cpc_code, self._version, mesh_json),
               )
               self._conn.commit()

           def put_batch(
               self,
               entries: list[tuple[str, list[tuple[MeshDescriptor, float]]]],
           ) -> int:
               """Batch insert cache entries. Returns count inserted."""
               for cpc_code, mappings in entries:
                   mesh_json = self._serialize(mappings)
                   self._conn.execute(
                       """
                       INSERT OR REPLACE INTO cpc_cache (cpc_code, version, mesh_json)
                       VALUES (?, ?, ?)
                       """,
                       (cpc_code, self._version, mesh_json),
                   )
               self._conn.commit()
               return len(entries)

           def invalidate_version(self, old_version: str) -> int:
               """Delete all entries for an old version. Returns count deleted."""
               cursor = self._conn.execute(
                   "DELETE FROM cpc_cache WHERE version = ?",
                   (old_version,),
               )
               self._conn.commit()
               return cursor.rowcount

           def stats(self) -> CacheStats:
               """Return cache performance statistics."""
               cursor = self._conn.execute(
                   "SELECT COUNT(*) FROM cpc_cache WHERE version = ?",
                   (self._version,),
               )
               total = cursor.fetchone()[0]
               total_requests = self._hits + self._misses
               hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
               return CacheStats(
                   total_entries=total,
                   version=self._version,
                   hit_count=self._hits,
                   miss_count=self._misses,
                   hit_rate=round(hit_rate, 4),
               )

           def close(self) -> None:
               """Close the SQLite connection."""
               self._conn.close()

           @staticmethod
           def _serialize(
               mappings: list[tuple[MeshDescriptor, float]],
           ) -> str:
               """Serialize MeSH mappings to JSON string."""
               return json.dumps([
                   {
                       "descriptor": m.descriptor,
                       "qualifier": m.qualifier,
                       "major_topic": m.major_topic,
                       "weight": w,
                   }
                   for m, w in mappings
               ])

           @staticmethod
           def _deserialize(
               mesh_json: str,
           ) -> list[tuple[MeshDescriptor, float]]:
               """Deserialize JSON string to MeSH mappings."""
               data = json.loads(mesh_json)
               return [
                   (
                       MeshDescriptor(
                           descriptor=item["descriptor"],
                           qualifier=item.get("qualifier"),
                           major_topic=item.get("major_topic", False),
                       ),
                       item["weight"],
                   )
                   for item in data
               ]
       ```

    2. Create `src/aegis/taxonomy/cpc_xwalk_cache_test.py`:
       - `test_put_and_get`: Put a CPC mapping, get it back, verify equality
       - `test_cache_miss`: Get a non-existent CPC code, verify returns None
       - `test_version_isolation`: Put with version "v1", get with version "v2" (different cache), verify miss
       - `test_invalidate_version`: Put entries for "v1", invalidate "v1", verify all deleted
       - `test_batch_insert`: Put 100 entries in batch, verify all retrievable
       - `test_cache_stats`: Do 5 hits and 3 misses, verify stats
       - `test_warm_cache_performance`: Put 1000 entries, time 1000 lookups, assert p99 < 1ms (use `time.perf_counter()`)
       - `test_serialization_round_trip`: Serialize/deserialize MeshDescriptor with qualifier and major_topic, verify lossless
       - Use `tmp_path` for SQLite database isolation

    3. Update `src/aegis/taxonomy/__init__.py` to export `CpcXwalkCache`, `CacheStats`.

    ## Files to create
    - `src/aegis/taxonomy/cpc_xwalk_cache.py`
    - `src/aegis/taxonomy/cpc_xwalk_cache_test.py`

    ## Files to modify
    - `src/aegis/taxonomy/__init__.py` — add cache exports

    ## Code patterns to follow
    - SQLite via `sqlite3` (lightweight, local cache — not DuckDB for this use case)
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for stats
    - `MeshDescriptor` from `src/aegis/storage/schema.py`
    - JSON serialization for cache values
    - `from __future__ import annotations`
    - Performance tests: `time.perf_counter()` for timing
    - `tmp_path` for test database isolation

    ## Acceptance criteria
    - `CpcXwalkCache.get(cpc_code)` returns cached result or None
    - `CpcXwalkCache.put(cpc_code, mappings)` stores in cache
    - Version-keyed isolation: different versions don't interfere
    - `invalidate_version()` removes old entries
    - Warm cache lookup p99 < 1ms on 1000 entries
    - Cache hit rate tracking works
    - All tests pass: `uv run pytest src/aegis/taxonomy/cpc_xwalk_cache_test.py -v`
    - mypy passes: `uv run mypy src/aegis/taxonomy/cpc_xwalk_cache.py`
    - ruff passes: `uv run ruff check src/aegis/taxonomy/cpc_xwalk_cache.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/taxonomy/cpc_xwalk_cache_test.py -v && uv run mypy src/aegis/taxonomy/cpc_xwalk_cache.py && uv run ruff check src/aegis/taxonomy/cpc_xwalk_cache.py
    ```

### 5. Weight Vector Integration Tests

- **Task ID**: weight-integration-tests
- **Role**: builder
- **Depends On**: drug-discovery-weights, clinician-weights, f7-clinician, cpc-xwalk-cache
- **Assigned To**: builder-2
- **Description**: |
    Create integration tests verifying that all three weight vectors (translational, drug-discovery, clinician) work correctly with QualityPrior, and that the 7-family clinician composition includes F7.

    ## What to do

    1. Create `src/aegis/scoring/weight_integration_test.py`:

       ```python
       """Integration tests for all weight vectors with QualityPrior."""

       from __future__ import annotations

       from aegis.scoring.quality_prior import QualityPrior, load_weight_vector
       from aegis.scoring.drug_discovery_weights import load_drug_discovery_weights
       from aegis.scoring.clinician_weights import load_clinician_weights


       def test_translational_weights_load() -> None:
           """Translational v1 weights load and sum to 1.0."""
           wv = load_weight_vector()
           assert abs(sum(wv.weights.values()) - 1.0) < 0.001
           assert wv.specialty == "translational"
           assert len(wv.weights) == 6


       def test_drug_discovery_weights_load() -> None:
           """Drug-discovery v1 weights load and sum to 1.0."""
           wv = load_drug_discovery_weights()
           assert abs(sum(wv.weights.values()) - 1.0) < 0.001
           assert wv.specialty == "drug_discovery"
           assert len(wv.weights) == 6
           assert wv.weights["f5_translational"] == 0.50


       def test_clinician_weights_load() -> None:
           """Clinician v1 weights load, include F7, and sum to 1.0."""
           wv = load_clinician_weights()
           assert abs(sum(wv.weights.values()) - 1.0) < 0.001
           assert wv.specialty == "clinician"
           assert len(wv.weights) == 7
           assert "f7_clinician" in wv.weights
           assert wv.weights["f7_clinician"] == 0.25


       def test_quality_prior_6_families() -> None:
           """QualityPrior computes correctly with 6-family translational weights."""
           wv = load_weight_vector()
           qp = QualityPrior(wv)
           components = {k: 0.5 for k in wv.weights}
           raw = qp.compute_raw(components)
           assert 0.0 < raw < 1.0


       def test_quality_prior_7_families() -> None:
           """QualityPrior computes correctly with 7-family clinician weights."""
           wv = load_clinician_weights()
           qp = QualityPrior(wv)
           components = {k: 0.5 for k in wv.weights}
           raw = qp.compute_raw(components)
           assert 0.0 < raw < 1.0


       def test_quality_prior_drug_discovery_f5_dominant() -> None:
           """Drug-discovery Q(c): high F5 matters more than high F2."""
           wv = load_drug_discovery_weights()
           qp = QualityPrior(wv)

           # Candidate A: high F5, low F2
           comp_a = {k: 0.5 for k in wv.weights}
           comp_a["f5_translational"] = 0.95
           comp_a["f2_funding"] = 0.1

           # Candidate B: low F5, high F2
           comp_b = {k: 0.5 for k in wv.weights}
           comp_b["f5_translational"] = 0.1
           comp_b["f2_funding"] = 0.95

           raw_a = qp.compute_raw(comp_a)
           raw_b = qp.compute_raw(comp_b)
           assert raw_a > raw_b, "F5-dominant candidate should score higher under drug-discovery weights"


       def test_quality_prior_clinician_f7_matters() -> None:
           """Clinician Q(c): high F7 meaningfully impacts score."""
           wv = load_clinician_weights()
           qp = QualityPrior(wv)

           # Candidate A: high F7
           comp_a = {k: 0.5 for k in wv.weights}
           comp_a["f7_clinician"] = 0.95

           # Candidate B: low F7
           comp_b = {k: 0.5 for k in wv.weights}
           comp_b["f7_clinician"] = 0.1

           raw_a = qp.compute_raw(comp_a)
           raw_b = qp.compute_raw(comp_b)
           assert raw_a > raw_b, "High F7 should produce higher Q(c) under clinician weights"


       def test_all_weight_vectors_have_exponents() -> None:
           """All weight vectors include alpha, beta, gamma exponents."""
           for loader in [load_weight_vector, load_drug_discovery_weights, load_clinician_weights]:
               wv = loader()
               assert "alpha" in wv.exponents
               assert "beta" in wv.exponents
               assert "gamma" in wv.exponents
       ```

    2. Update `src/aegis/scoring/__init__.py` to add new exports if not already present:
       - `load_drug_discovery_weights` from `drug_discovery_weights`
       - `load_clinician_weights` from `clinician_weights`

    ## Files to create
    - `src/aegis/scoring/weight_integration_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` — add weight loader exports

    ## Code patterns to follow
    - Test patterns from `src/aegis/scoring/quality_prior_test.py`
    - Direct function calls, no mocking needed (tests use real YAML files)

    ## Acceptance criteria
    - All 3 weight vectors load successfully
    - QualityPrior works with both 6-family and 7-family inputs
    - Drug-discovery: F5-dominant candidate scores higher than F2-dominant
    - Clinician: high F7 meaningfully impacts Q(c)
    - All tests pass: `uv run pytest src/aegis/scoring/weight_integration_test.py -v`
    - mypy passes on integration test file

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/weight_integration_test.py -v
    ```

### 6. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: drug-discovery-weights, clinician-weights, f7-clinician, cpc-xwalk-cache, weight-integration-tests
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for Phase 2c.

    ## Validation Commands

    1. Verify weight configs exist and are valid:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    import yaml
    for f in ['translational_v1', 'drug_discovery_v1', 'clinician_v1']:
        d = yaml.safe_load(open(f'config/aegis/weights/{f}.yaml'))
        w = d['weights']
        total = sum(w.values())
        assert abs(total - 1.0) < 0.001, f'{f}: weights sum to {total}'
        print(f'{f}: {len(w)} families, sum={total:.3f} OK')
    "
    ```

    2. Verify F7 module:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.scoring.f7_clinician import F7Computer, F7Score; print('F7 imports OK')"
    ```

    3. Verify CPC cache:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.taxonomy.cpc_xwalk_cache import CpcXwalkCache, CacheStats; print('CPC cache imports OK')"
    ```

    4. Verify weight loaders:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.scoring.drug_discovery_weights import load_drug_discovery_weights
    from aegis.scoring.clinician_weights import load_clinician_weights
    dd = load_drug_discovery_weights()
    cl = load_clinician_weights()
    assert dd.weights['f5_translational'] == 0.50
    assert 'f7_clinician' in cl.weights
    assert cl.weights['f7_clinician'] == 0.25
    print('Weight loaders OK')
    "
    ```

    5. Run all Phase 2c tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f7_clinician_test.py src/aegis/taxonomy/cpc_xwalk_cache_test.py src/aegis/scoring/weight_integration_test.py -v
    ```

    6. Run mypy on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/scoring/drug_discovery_weights.py src/aegis/scoring/clinician_weights.py src/aegis/scoring/f7_clinician.py src/aegis/taxonomy/cpc_xwalk_cache.py
    ```

    7. Run ruff on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/scoring/drug_discovery_weights.py src/aegis/scoring/clinician_weights.py src/aegis/scoring/f7_clinician.py src/aegis/taxonomy/cpc_xwalk_cache.py
    ```

    8. Verify existing scoring tests still pass:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/quality_prior_test.py -v
    ```

    ## Acceptance Criteria
    - Drug-discovery weight vector: F5=0.50, sum=1.0, 6 families
    - Clinician weight vector: F7=0.25, sum=1.0, 7 families
    - F7Computer exists with score_raw + compute_percentiles
    - F7 sub-component weights sum to 1.0
    - QualityPrior works with both 6 and 7 family inputs
    - CPC cache p99 < 1ms warm lookup
    - All new tests pass
    - mypy strict passes
    - ruff passes
    - Existing scoring tests unbroken

## Acceptance Criteria

- `config/aegis/weights/drug_discovery_v1.yaml` exists with weights `(F1 .15, F2 .05, F3 .15, F4 .05, F5 .50, F6 .10)` summing to 1.0
- `config/aegis/weights/clinician_v1.yaml` exists with weights `(F1 .15, F2 .10, F3 .25, F4 .05, F5 .15, F6 .05, F7 .25)` summing to 1.0
- `F7Computer` at `src/aegis/scoring/f7_clinician.py` computes clinician-specific score with sub-components: board certification, license, hospital tier, trial PI, procedure volume
- `QualityPrior` correctly handles both 6-family and 7-family weight vectors
- Drug-discovery: F5-dominant candidate scores higher than F2-dominant under drug-discovery weights
- Clinician: high F7 meaningfully impacts Q(c) under clinician weights
- `CpcXwalkCache` provides warm lookup p99 < 1ms on 1000 cached entries
- Cache version-keyed invalidation works
- All new tests pass
- mypy strict mode passes on all new modules
- ruff lint passes on all new modules
- Existing Phase 1 scoring tests unbroken

## Validation Commands

- `cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/f7_clinician_test.py src/aegis/taxonomy/cpc_xwalk_cache_test.py src/aegis/scoring/weight_integration_test.py -v` — Run all Phase 2c tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/scoring/drug_discovery_weights.py src/aegis/scoring/clinician_weights.py src/aegis/scoring/f7_clinician.py src/aegis/taxonomy/cpc_xwalk_cache.py` — Type-check new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/scoring/drug_discovery_weights.py src/aegis/scoring/clinician_weights.py src/aegis/scoring/f7_clinician.py src/aegis/taxonomy/cpc_xwalk_cache.py` — Lint new modules
- `cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/quality_prior_test.py -v` — Verify existing scoring tests

## Notes

- The existing `QualityPrior.compute_raw()` iterates `self._weights.weights.items()` — it already handles arbitrary numbers of F-families, so no code change is needed in `quality_prior.py` itself. The 7-family support comes naturally from the YAML config.
- F7 is the ONLY place hospital tier feeds into scoring; F1-F6 are population-agnostic.
- A licensed but not-board-certified clinician scores lower on F7 but is NOT gated out — gating is integrity-only (hard gate).
- Procedure-volume proxies are noisy; the `coverage_caveat` field on F7Score reports when data is unavailable.
- CPC cache backend is SQLite for local development; production may migrate to Redis. The interface (`get/put/invalidate_version`) is backend-agnostic.
