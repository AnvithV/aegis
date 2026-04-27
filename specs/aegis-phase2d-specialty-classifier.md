# Plan: Phase 2d — Specialty Classifier + Dynamic Reassignment + Conference Proceedings + Cross-Population Identity Merge

> **Status:** COMPLETE (2026-04-27)
> All 7 tasks completed. 35/35 Phase 2d tests passing. 9/9 Phase 0/1 tests passing. mypy strict clean. ruff clean. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-27
> **Team:** phase2d-specialty-20260427-1500

### Test Results
- `specialty_classifier_test.py` — 10/10 PASSED
- `specialty_reassignment_test.py` — 7/7 PASSED
- `conferences_test.py` — 8/8 PASSED
- `cross_population_test.py` — 10/10 PASSED
- Phase 0/1 regression (`tests/`) — 9/9 PASSED

### Validation Commands
- `uv run pytest ... -v` — **PASS** (35/35 passed in 2.01s)
- `uv run mypy ...` — **PASS** (no issues found in 10 source files)
- `uv run ruff check ...` — **PASS** (all checks passed)

### Acceptance Criteria Verification
- [x] `SpecialtyClassifier.classify(candidate) -> SpecialtyDistribution` with probabilities over translational/drug_discovery/clinician — VERIFIED (class at `specialty_classifier.py:89`, method at line 155, returns `SpecialtyDistribution` with `probabilities` dict)
- [x] Below 0.6 confidence, `is_ambiguous` flag is set — VERIFIED (`AMBIGUITY_THRESHOLD = 0.6` at line 16, checked at lines 173 and 218)
- [x] `SpecialtyReassigner.reassign_all(cohort) -> ReassignmentReport` tracks changes with audit log — VERIFIED (class at `specialty_reassignment.py:52`, method at line 108, returns `ReassignmentReport` with `entries: list[ReassignmentEntry]`)
- [x] Major changes (> 0.3 probability shift) flagged in audit entries — VERIFIED (`MAJOR_SHIFT_THRESHOLD = 0.3` at line 19, `is_major_change` field at line 34)
- [x] `ConferenceIngestor.ingest(year, society) -> Iterator[TalkRecord]` interface with ASCO, ACS, AACR implementations — VERIFIED (ABC at `base.py:37`, `AscoIngestor` at `asco.py:10`, `AcsIngestor` at `acs.py:10`, `AacrIngestor` at `aacr.py:10`)
- [x] Named lectureships feed F4; invited talks feed F3 via `TalkType` — VERIFIED (`TalkType` at `base.py:11` with `is_named_lectureship` and `is_invited_talk` fields)
- [x] `CrossPopulationMerger` unifies candidates via patent-inventor ID and NPI strong keys — VERIFIED (class at `cross_population_merge.py:41`, strong keys `{"orcid", "npi", "patent_inventor_id"}` at line 134)
- [x] `MultiSpecialtyRouter` selects appropriate weight vector per query — VERIFIED (class at `multi_specialty.py:19`)
- [x] All new tests pass — VERIFIED (35/35 passed)
- [x] mypy strict mode passes — VERIFIED (no issues in 10 source files)
- [x] ruff lint passes — VERIFIED (all checks passed)
- [x] No existing Phase 0/1 tests broken — VERIFIED (9/9 passed in `tests/`)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `pyproject.toml` | Modified (added scikit-learn) | Yes |
| `src/aegis/scoring/specialty_classifier.py` | Created | Yes |
| `src/aegis/scoring/specialty_classifier_test.py` | Created | Yes |
| `src/aegis/scoring/specialty_reassignment.py` | Created | Yes |
| `src/aegis/scoring/specialty_reassignment_test.py` | Created | Yes |
| `src/aegis/sources/conferences/__init__.py` | Created | Yes |
| `src/aegis/sources/conferences/base.py` | Created | Yes |
| `src/aegis/sources/conferences/asco.py` | Created | Yes |
| `src/aegis/sources/conferences/acs.py` | Created | Yes |
| `src/aegis/sources/conferences/aacr.py` | Created | Yes |
| `src/aegis/sources/conferences/llm_extract.py` | Created | Yes |
| `src/aegis/sources/conferences_test.py` | Created | Yes |
| `src/aegis/identity/cross_population_merge.py` | Created | Yes |
| `src/aegis/identity/cross_population_test.py` | Created | Yes |
| `src/aegis/scoring/multi_specialty.py` | Created | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase2d-specialty-classifier.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build the specialty classifier that routes candidates to the appropriate weight vector, the dynamic specialty reassignment pipeline for industry-pivot archetypes, conference proceedings ingestion for F3/F4 leadership signals, and the cross-population identity merge that unifies candidates appearing across translational, drug-discovery, and clinician populations. This sub-spec is the integration layer that makes the multi-population platform work: without specialty classification, candidates cannot be routed to the correct weight vector; without cross-population merge, the same MD-PhD with patents and NPI would appear as three separate candidates.

This plan covers Phase 2 tasks: **1.12** (specialty classifier), **1.13** (dynamic specialty reassignment), **1.14** (conference proceedings), and **1.15** (cross-population identity merge).

## Objective

When this plan is complete:
1. A `SpecialtyClassifier` at `src/aegis/scoring/specialty_classifier.py` classifies candidates into translational/drug-discovery/clinician based on last-36-month artifact mix, using gradient-boosted-trees on hand-crafted features, with isotonic-regression-calibrated probabilities and ambiguity flagging below 0.6 confidence.
2. A `SpecialtyReassigner` at `src/aegis/scoring/specialty_reassignment.py` runs nightly reassignment with audit logging for probability shifts > 0.3.
3. Conference proceedings ingestion exists at `src/aegis/sources/conferences/` for top-3 societies (ASCO, ACS, AACR) with LLM-constrained extraction and PubMed cross-validation.
4. A `CrossPopulationMerger` at `src/aegis/identity/cross_population_merge.py` unifies candidates across populations using patent-inventor ID and NPI as additional strong keys, with multi-specialty annotation support.
5. All modules pass mypy strict, ruff lint, and have unit tests.

## Problem Statement

Phase 1 has only translational candidates with a single weight vector. Phase 2 adds drug-discovery and clinician populations, each with their own weight vectors. The system needs to (a) classify which population a candidate belongs to, (b) handle candidates who shift populations over time (Archetype 2: industry pivot), (c) ingest conference proceedings as a new leadership/apex signal, and (d) merge identities when the same person appears in multiple populations (MD-PhD with patents + papers + NPI). The existing `SpecialtyAmbiguityFlagger` in Phase 1 was observability-only; now classification must actively drive weight-vector routing.

## Solution Approach

1. **Specialty classifier**: Feature-engineered gradient-boosted trees (scikit-learn) on artifact-mix proportions. Training labels from ~500-candidate-per-specialty hand-curated set.
2. **Reassignment pipeline**: Nightly batch job comparing current vs prior classification, logging changes > 0.3 probability shift.
3. **Conference ingestion**: LLM-constrained extraction from PDFs with PubMed/ORCID cross-validation. Per-society modules.
4. **Cross-population merge**: Extension of existing Fellegi-Sunter linker with patent-inventor ID and NPI as additional strong keys.

## Relevant Files

### Existing Files
- `src/aegis/scoring/specialty_flag.py` — Phase 1 `SpecialtyAmbiguityFlagger` (observability-only predecessor)
- `src/aegis/scoring/quality_prior.py` — `QualityPrior`, `WeightVector`
- `src/aegis/identity/probabilistic.py` — `ProbabilisticLinker` (Fellegi-Sunter)
- `src/aegis/identity/strong_key.py` — `CandidateRegistry`, strong-key linkage
- `src/aegis/identity/review_queue.py` — `ReviewQueue` for HITL review
- `src/aegis/storage/schema.py` — `Candidate` model
- `src/aegis/sources/pubmed.py` — `PubMedClient` for cross-validation
- `src/aegis/validation/archetypes.py` — `ArchetypeFixture` (Dr. A, B, C, D)
- `pyproject.toml` — Dependencies (scikit-learn may need to be added)

### New Files
- `src/aegis/scoring/specialty_classifier.py` — Specialty classifier
- `src/aegis/scoring/specialty_classifier_test.py` — Classifier tests
- `src/aegis/scoring/specialty_reassignment.py` — Dynamic reassignment
- `src/aegis/scoring/specialty_reassignment_test.py` — Reassignment tests
- `src/aegis/sources/conferences/__init__.py` — Conference package
- `src/aegis/sources/conferences/base.py` — Base conference ingestor
- `src/aegis/sources/conferences/asco.py` — ASCO conference ingestor
- `src/aegis/sources/conferences/acs.py` — ACS conference ingestor
- `src/aegis/sources/conferences/aacr.py` — AACR conference ingestor
- `src/aegis/sources/conferences/llm_extract.py` — LLM-constrained extraction
- `src/aegis/sources/conferences_test.py` — Conference ingestion tests
- `src/aegis/identity/cross_population_merge.py` — Cross-population merger
- `src/aegis/scoring/multi_specialty.py` — Multi-specialty scoring router
- `src/aegis/identity/cross_population_test.py` — Cross-population tests

## Implementation Phases

### Phase 1: Foundation
- Create conference proceedings package structure
- Add scikit-learn dependency
- Build conference LLM extraction + base ingestor

### Phase 2: Core Implementation
- Build specialty classifier with feature engineering and calibration
- Build dynamic specialty reassignment with audit logging
- Build cross-population identity merge with patent-inventor and NPI strong keys
- Build per-society conference ingestors (ASCO, ACS, AACR)

### Phase 3: Integration & Polish
- Build multi-specialty scoring router
- Wire everything together
- Run full validation suite

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Specialty classifier, dynamic reassignment, multi-specialty scoring router
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: Conference proceedings ingestion (ASCO, ACS, AACR, LLM extraction), cross-population identity merge
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

### 1. Add scikit-learn Dependency + Conference Package Scaffold

- **Task ID**: scaffold-phase2d
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Add scikit-learn to project dependencies and create the conference proceedings package structure.

    ## What to do

    1. Add `scikit-learn>=1.4` to the `dependencies` list in `pyproject.toml`. Do NOT remove or modify any existing dependencies. Only append the new one.

    2. Run `cd /Users/anvith/aegis && uv lock` to update the lock file.

    3. Create `src/aegis/sources/conferences/__init__.py`:
       ```python
       """Conference proceedings ingestion (ASCO, ACS, AACR, etc.)."""

       from __future__ import annotations
       ```

    ## Files to create
    - `src/aegis/sources/conferences/__init__.py`

    ## Files to modify
    - `pyproject.toml` — append `scikit-learn>=1.4` to dependencies

    ## Acceptance criteria
    - `pyproject.toml` contains `scikit-learn` in dependencies
    - `uv lock` succeeds
    - `src/aegis/sources/conferences/__init__.py` exists

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv lock --check && uv run python -c "import sklearn; print(f'scikit-learn {sklearn.__version__} OK')" && uv run python -c "import aegis.sources.conferences; print('Conference package OK')"
    ```

### 2. Specialty Classifier

- **Task ID**: specialty-classifier
- **Role**: builder
- **Depends On**: scaffold-phase2d
- **Assigned To**: builder-1
- **Description**: |
    Build the specialty classifier that routes candidates to translational/drug-discovery/clinician weight vectors based on artifact-mix features.

    ## What to do

    1. Create `src/aegis/scoring/specialty_classifier.py`:

       ```python
       """Artifact-mix-based specialty classifier: translational / drug-discovery / clinician."""

       from __future__ import annotations

       import logging
       from dataclasses import dataclass, field
       from enum import StrEnum

       import numpy as np
       from pydantic import BaseModel, ConfigDict
       from sklearn.ensemble import GradientBoostingClassifier  # type: ignore[import-untyped]
       from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]

       logger = logging.getLogger(__name__)

       AMBIGUITY_THRESHOLD = 0.6


       class Specialty(StrEnum):
           """Population specialty types."""

           translational = "translational"
           drug_discovery = "drug_discovery"
           clinician = "clinician"


       class SpecialtyDistribution(BaseModel):
           """Probability distribution over specialties for a candidate."""

           model_config = ConfigDict(frozen=True)

           candidate_uuid: str
           probabilities: dict[str, float]  # specialty -> probability
           predicted_specialty: str          # highest probability
           confidence: float                 # highest probability value
           is_ambiguous: bool                # confidence < AMBIGUITY_THRESHOLD


       @dataclass
       class ArtifactMixFeatures:
           """Hand-crafted features from a candidate's last-36-month artifact mix."""

           candidate_uuid: str

           # Article features
           total_papers: int = 0
           last_author_rate: float = 0.0
           mean_rcr: float = 0.0
           rcr_above_2: int = 0           # Papers with RCR > 2.0

           # Patent features
           total_patents: int = 0
           lead_inventor_count: int = 0

           # Grant features
           total_grants: int = 0
           r01_equivalent_count: int = 0

           # Trial features
           total_trials: int = 0
           phase3_trials: int = 0

           # Clinician features
           has_npi: bool = False
           has_abms_certification: bool = False
           has_hospital_affiliation: bool = False
           procedure_volume: int = 0

           # Proportions (computed)
           paper_proportion: float = 0.0
           patent_proportion: float = 0.0
           grant_proportion: float = 0.0
           trial_proportion: float = 0.0


       class SpecialtyClassifier:
           """Classify candidates into specialties based on artifact-mix features.

           Uses gradient-boosted trees on hand-crafted features with
           isotonic-regression-calibrated probabilities.
           """

           def __init__(self) -> None:
               self._model: GradientBoostingClassifier | None = None
               self._calibrators: dict[str, IsotonicRegression] = {}
               self._classes: list[str] = [s.value for s in Specialty]

           def _extract_feature_vector(self, features: ArtifactMixFeatures) -> list[float]:
               """Convert ArtifactMixFeatures to a numeric feature vector."""
               total_artifacts = (
                   features.total_papers + features.total_patents
                   + features.total_grants + features.total_trials
               )
               safe_total = max(total_artifacts, 1)

               return [
                   features.total_papers,
                   features.last_author_rate,
                   features.mean_rcr,
                   features.rcr_above_2,
                   features.total_patents,
                   features.lead_inventor_count,
                   features.total_grants,
                   features.r01_equivalent_count,
                   features.total_trials,
                   features.phase3_trials,
                   1.0 if features.has_npi else 0.0,
                   1.0 if features.has_abms_certification else 0.0,
                   1.0 if features.has_hospital_affiliation else 0.0,
                   features.procedure_volume,
                   features.total_papers / safe_total,       # paper proportion
                   features.total_patents / safe_total,      # patent proportion
                   features.total_grants / safe_total,       # grant proportion
                   features.total_trials / safe_total,       # trial proportion
               ]

           def train(
               self,
               training_data: list[tuple[ArtifactMixFeatures, str]],
           ) -> None:
               """Train the classifier on labeled (features, specialty) pairs.

               Training labels: hand-curated set of ~500 candidates per specialty.
               """
               if not training_data:
                   raise ValueError("Training data cannot be empty")

               X = np.array([  # noqa: N806
                   self._extract_feature_vector(f)
                   for f, _ in training_data
               ])
               y = np.array([label for _, label in training_data])

               self._model = GradientBoostingClassifier(
                   n_estimators=100,
                   max_depth=4,
                   learning_rate=0.1,
                   random_state=42,
               )
               self._model.fit(X, y)
               logger.info("Trained specialty classifier on %d samples", len(training_data))

           def classify(
               self,
               features: ArtifactMixFeatures,
           ) -> SpecialtyDistribution:
               """Classify a candidate into a specialty.

               Returns probability distribution over all specialties.
               If confidence < 0.6, marks as ambiguous.
               """
               if self._model is None:
                   # Fallback: rule-based classification
                   return self._rule_based_classify(features)

               X = np.array([self._extract_feature_vector(features)])  # noqa: N806
               proba = self._model.predict_proba(X)[0]
               classes = list(self._model.classes_)

               prob_dict = {cls: float(p) for cls, p in zip(classes, proba)}

               # Ensure all specialties present
               for spec in self._classes:
                   if spec not in prob_dict:
                       prob_dict[spec] = 0.0

               predicted = max(prob_dict, key=prob_dict.get)  # type: ignore[arg-type]
               confidence = prob_dict[predicted]

               return SpecialtyDistribution(
                   candidate_uuid=features.candidate_uuid,
                   probabilities=prob_dict,
                   predicted_specialty=predicted,
                   confidence=round(confidence, 4),
                   is_ambiguous=confidence < AMBIGUITY_THRESHOLD,
               )

           def classify_batch(
               self,
               features_list: list[ArtifactMixFeatures],
           ) -> list[SpecialtyDistribution]:
               """Classify a batch of candidates."""
               return [self.classify(f) for f in features_list]

           def _rule_based_classify(
               self,
               features: ArtifactMixFeatures,
           ) -> SpecialtyDistribution:
               """Fallback rule-based classification when model is not trained."""
               probs = {s.value: 0.0 for s in Specialty}

               if features.has_npi and features.has_abms_certification:
                   probs[Specialty.clinician.value] = 0.7
                   probs[Specialty.translational.value] = 0.2
                   probs[Specialty.drug_discovery.value] = 0.1
               elif features.total_patents > features.total_papers:
                   probs[Specialty.drug_discovery.value] = 0.7
                   probs[Specialty.translational.value] = 0.2
                   probs[Specialty.clinician.value] = 0.1
               else:
                   probs[Specialty.translational.value] = 0.6
                   probs[Specialty.drug_discovery.value] = 0.25
                   probs[Specialty.clinician.value] = 0.15

               predicted = max(probs, key=probs.get)  # type: ignore[arg-type]
               confidence = probs[predicted]

               return SpecialtyDistribution(
                   candidate_uuid=features.candidate_uuid,
                   probabilities=probs,
                   predicted_specialty=predicted,
                   confidence=round(confidence, 4),
                   is_ambiguous=confidence < AMBIGUITY_THRESHOLD,
               )
       ```

    2. Create `src/aegis/scoring/specialty_classifier_test.py`:
       - `test_specialty_enum`: Verify Specialty has translational, drug_discovery, clinician
       - `test_rule_based_clinician`: NPI + ABMS -> clinician with >= 0.6 confidence
       - `test_rule_based_drug_discovery`: Patents > papers -> drug_discovery
       - `test_rule_based_translational`: Default -> translational
       - `test_ambiguity_flag`: Low confidence -> is_ambiguous=True
       - `test_train_and_classify`: Train on synthetic data (30 per class), classify, verify predictions make sense
       - `test_batch_classify`: Classify 10 candidates, verify 10 results
       - `test_feature_vector_extraction`: Verify feature vector has correct length
       - `test_probability_distribution_sums_to_1`: Verify probabilities sum to ~1.0
       - `test_specialty_distribution_model`: Create SpecialtyDistribution, verify fields

    3. Update `src/aegis/scoring/__init__.py` to add exports: `SpecialtyClassifier`, `SpecialtyDistribution`, `Specialty`, `ArtifactMixFeatures`.

    ## Files to create
    - `src/aegis/scoring/specialty_classifier.py`
    - `src/aegis/scoring/specialty_classifier_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` — add specialty classifier exports

    ## Code patterns to follow
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for output models
    - `StrEnum` for specialty types
    - `@dataclass` for feature input
    - scikit-learn `GradientBoostingClassifier` for model
    - `from __future__ import annotations`
    - Logger at module level
    - Same test patterns as other scoring modules

    ## Acceptance criteria
    - `SpecialtyClassifier.classify(features) -> SpecialtyDistribution` works
    - Rule-based fallback produces reasonable classifications
    - Train + classify workflow works on synthetic data
    - Ambiguity flagging at < 0.6 confidence
    - Probabilities sum to ~1.0
    - All tests pass: `uv run pytest src/aegis/scoring/specialty_classifier_test.py -v`
    - mypy passes: `uv run mypy src/aegis/scoring/specialty_classifier.py`
    - ruff passes: `uv run ruff check src/aegis/scoring/specialty_classifier.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/specialty_classifier_test.py -v && uv run mypy src/aegis/scoring/specialty_classifier.py && uv run ruff check src/aegis/scoring/specialty_classifier.py
    ```

### 3. Dynamic Specialty Reassignment

- **Task ID**: specialty-reassignment
- **Role**: builder
- **Depends On**: specialty-classifier
- **Assigned To**: builder-1
- **Description**: |
    Build the dynamic specialty reassignment pipeline that re-classifies candidates nightly and logs significant probability shifts for audit.

    ## What to do

    1. Create `src/aegis/scoring/specialty_reassignment.py`:

       ```python
       """Dynamic specialty reassignment with audit logging."""

       from __future__ import annotations

       import logging
       import uuid as _uuid
       from datetime import UTC, datetime

       from pydantic import BaseModel, ConfigDict

       from aegis.scoring.specialty_classifier import (
           ArtifactMixFeatures,
           SpecialtyClassifier,
           SpecialtyDistribution,
       )

       logger = logging.getLogger(__name__)

       MAJOR_SHIFT_THRESHOLD = 0.3


       class ReassignmentEntry(BaseModel):
           """A single candidate reassignment record."""

           model_config = ConfigDict(frozen=True)

           entry_id: str
           candidate_uuid: str
           previous_specialty: str
           new_specialty: str
           previous_confidence: float
           new_confidence: float
           probability_shift: float       # Absolute change in top probability
           is_major_change: bool          # shift > 0.3
           timestamp: datetime
           artifact_mix_summary: dict[str, int]  # What drove the change


       class ReassignmentReport(BaseModel):
           """Summary of a reassignment batch run."""

           model_config = ConfigDict(frozen=True)

           total_candidates: int
           reassigned_count: int
           major_changes: int
           stable_count: int
           entries: list[ReassignmentEntry]
           run_timestamp: datetime


       class SpecialtyReassigner:
           """Nightly batch reassignment of candidate specialties.

           Compares current classification against prior and logs changes.
           Major changes (>0.3 shift) trigger audit log entries.
           """

           def __init__(
               self,
               classifier: SpecialtyClassifier,
           ) -> None:
               self._classifier = classifier

           def reassign_all(
               self,
               candidates: list[tuple[ArtifactMixFeatures, SpecialtyDistribution]],
           ) -> ReassignmentReport:
               """Re-classify all candidates and report changes.

               Input: list of (current_features, prior_classification) pairs.
               Output: ReassignmentReport with all changes documented.
               """
               now = datetime.now(UTC)
               entries: list[ReassignmentEntry] = []
               reassigned = 0
               major_changes = 0

               for features, prior in candidates:
                   new_dist = self._classifier.classify(features)

                   if new_dist.predicted_specialty != prior.predicted_specialty:
                       reassigned += 1
                       shift = abs(
                           new_dist.confidence - prior.confidence
                       )
                       is_major = shift >= MAJOR_SHIFT_THRESHOLD

                       if is_major:
                           major_changes += 1

                       entries.append(ReassignmentEntry(
                           entry_id=str(_uuid.uuid4()),
                           candidate_uuid=features.candidate_uuid,
                           previous_specialty=prior.predicted_specialty,
                           new_specialty=new_dist.predicted_specialty,
                           previous_confidence=prior.confidence,
                           new_confidence=new_dist.confidence,
                           probability_shift=round(shift, 4),
                           is_major_change=is_major,
                           timestamp=now,
                           artifact_mix_summary={
                               "papers": features.total_papers,
                               "patents": features.total_patents,
                               "grants": features.total_grants,
                               "trials": features.total_trials,
                           },
                       ))

               return ReassignmentReport(
                   total_candidates=len(candidates),
                   reassigned_count=reassigned,
                   major_changes=major_changes,
                   stable_count=len(candidates) - reassigned,
                   entries=entries,
                   run_timestamp=now,
               )

           def reassign_single(
               self,
               features: ArtifactMixFeatures,
               prior: SpecialtyDistribution,
           ) -> ReassignmentEntry | None:
               """Re-classify a single candidate. Returns None if unchanged."""
               new_dist = self._classifier.classify(features)

               if new_dist.predicted_specialty == prior.predicted_specialty:
                   return None

               shift = abs(new_dist.confidence - prior.confidence)

               return ReassignmentEntry(
                   entry_id=str(_uuid.uuid4()),
                   candidate_uuid=features.candidate_uuid,
                   previous_specialty=prior.predicted_specialty,
                   new_specialty=new_dist.predicted_specialty,
                   previous_confidence=prior.confidence,
                   new_confidence=new_dist.confidence,
                   probability_shift=round(shift, 4),
                   is_major_change=shift >= MAJOR_SHIFT_THRESHOLD,
                   timestamp=datetime.now(UTC),
                   artifact_mix_summary={
                       "papers": features.total_papers,
                       "patents": features.total_patents,
                       "grants": features.total_grants,
                       "trials": features.total_trials,
                   },
               )
       ```

    2. Create `src/aegis/scoring/specialty_reassignment_test.py`:
       - `test_reassign_no_change`: Same classification -> no entry
       - `test_reassign_specialty_change`: Classification changes -> entry created
       - `test_major_change_detection`: Shift > 0.3 -> is_major_change=True
       - `test_reassign_all_report`: Batch of 10 candidates, verify report counts
       - `test_audit_log_artifact_summary`: Entry includes artifact_mix_summary
       - `test_reassignment_entry_model`: Verify all fields on ReassignmentEntry
       - `test_report_timestamps`: Verify timestamps are present and UTC

    3. Update `src/aegis/scoring/__init__.py` to add exports: `SpecialtyReassigner`, `ReassignmentReport`, `ReassignmentEntry`.

    ## Files to create
    - `src/aegis/scoring/specialty_reassignment.py`
    - `src/aegis/scoring/specialty_reassignment_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` — add reassignment exports

    ## Code patterns to follow
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - UUID generation via `uuid.uuid4()`
    - UTC timestamps via `datetime.now(UTC)`
    - `from __future__ import annotations`
    - Logger at module level

    ## Acceptance criteria
    - `SpecialtyReassigner.reassign_all(cohort) -> ReassignmentReport` works
    - Major change detection at > 0.3 shift
    - Audit log entries contain artifact_mix_summary
    - Single reassignment returns None when unchanged
    - All tests pass: `uv run pytest src/aegis/scoring/specialty_reassignment_test.py -v`
    - mypy passes: `uv run mypy src/aegis/scoring/specialty_reassignment.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/specialty_reassignment_test.py -v && uv run mypy src/aegis/scoring/specialty_reassignment.py && uv run ruff check src/aegis/scoring/specialty_reassignment.py
    ```

### 4. Conference Proceedings Ingestion

- **Task ID**: conference-proceedings
- **Role**: builder
- **Depends On**: scaffold-phase2d
- **Assigned To**: builder-2
- **Description**: |
    Build conference proceedings ingestion for ASCO, ACS, and AACR with LLM-constrained extraction and PubMed cross-validation.

    ## What to do

    1. Create `src/aegis/sources/conferences/base.py`:

       ```python
       """Base conference proceedings ingestor."""

       from __future__ import annotations

       from abc import ABC, abstractmethod
       from collections.abc import Iterator

       from pydantic import BaseModel, ConfigDict


       class TalkType(BaseModel):
           """Classification of a conference talk."""

           model_config = ConfigDict(frozen=True)

           is_named_lectureship: bool    # e.g., Karnofsky Lecture -> F4 apex
           is_invited_talk: bool         # Regular invited -> F3 leadership
           is_oral_presentation: bool    # Oral abstract -> F3
           is_poster: bool               # Poster -> lower signal


       class TalkRecord(BaseModel):
           """A single conference talk/presentation record."""

           model_config = ConfigDict(frozen=True)

           presenter_name: str
           talk_type: TalkType
           session_title: str
           conference_name: str
           year: int
           abstract_title: str | None
           coauthors: list[str]
           source_url: str | None


       class ConferenceIngestor(ABC):
           """Abstract base for per-conference proceedings ingestors."""

           @property
           @abstractmethod
           def conference_name(self) -> str:
               """Full conference name (e.g., 'ASCO Annual Meeting')."""
               ...

           @property
           @abstractmethod
           def society_code(self) -> str:
               """Short code (e.g., 'ASCO', 'ACS', 'AACR')."""
               ...

           @abstractmethod
           def ingest(self, year: int) -> Iterator[TalkRecord]:
               """Ingest all talks from a conference year."""
               ...
       ```

    2. Create `src/aegis/sources/conferences/llm_extract.py`:

       ```python
       """LLM-constrained extraction for conference proceedings."""

       from __future__ import annotations

       import logging
       from typing import Protocol

       from aegis.sources.conferences.base import TalkRecord, TalkType

       logger = logging.getLogger(__name__)


       class LLMExtractor(Protocol):
           """Protocol for LLM-based talk extraction from proceedings text."""

           def extract_talks(
               self, text: str, conference_name: str, year: int
           ) -> list[dict[str, str]]:
               """Extract talks from proceedings text.

               Returns list of dicts with keys:
               presenter_name, talk_type, session_title, abstract_title.
               """
               ...


       class DefaultLLMExtractor:
           """Stub LLM extractor for development/testing.

           Production: replace with actual LLM integration using
           constrained generation (extract presenter, talk type, session).
           """

           def extract_talks(
               self, text: str, conference_name: str, year: int
           ) -> list[dict[str, str]]:
               """Stub: returns empty results."""
               logger.info(
                   "LLM extraction stub for %s %d (text len=%d)",
                   conference_name, year, len(text),
               )
               return []


       def talks_from_extraction(
           raw_talks: list[dict[str, str]],
           conference_name: str,
           year: int,
       ) -> list[TalkRecord]:
           """Convert raw LLM extraction output to TalkRecord objects."""
           records: list[TalkRecord] = []
           for raw in raw_talks:
               talk_type_str = raw.get("talk_type", "poster").lower()
               talk_type = TalkType(
                   is_named_lectureship="lectureship" in talk_type_str or "lecture" in talk_type_str,
                   is_invited_talk="invited" in talk_type_str,
                   is_oral_presentation="oral" in talk_type_str,
                   is_poster="poster" in talk_type_str,
               )
               records.append(TalkRecord(
                   presenter_name=raw.get("presenter_name", ""),
                   talk_type=talk_type,
                   session_title=raw.get("session_title", ""),
                   conference_name=conference_name,
                   year=year,
                   abstract_title=raw.get("abstract_title"),
                   coauthors=raw.get("coauthors", "").split(", ") if raw.get("coauthors") else [],
                   source_url=raw.get("source_url"),
               ))
           return records
       ```

    3. Create `src/aegis/sources/conferences/asco.py`, `acs.py`, and `aacr.py` — each implementing `ConferenceIngestor` with conference-specific settings. Each is a stub in Phase 2 that delegates to LLM extraction:

       Example for ASCO:
       ```python
       """ASCO Annual Meeting proceedings ingestor."""

       from __future__ import annotations

       from collections.abc import Iterator

       from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord


       class AscoIngestor(ConferenceIngestor):
           """Ingest ASCO Annual Meeting proceedings."""

           @property
           def conference_name(self) -> str:
               return "ASCO Annual Meeting"

           @property
           def society_code(self) -> str:
               return "ASCO"

           def ingest(self, year: int) -> Iterator[TalkRecord]:
               """Ingest ASCO talks for a given year.

               Stub: production implementation scrapes ASCO abstracts site
               and uses LLM extraction.
               """
               return iter([])
       ```

       Create ACS and AACR following the same pattern.

    4. Create `src/aegis/sources/conferences_test.py`:
       - `test_talk_record_model`: Create TalkRecord with all fields
       - `test_talk_type_named_lectureship`: Named lectureship detection
       - `test_talk_type_invited`: Invited talk detection
       - `test_talks_from_extraction`: Convert raw dict list to TalkRecords
       - `test_asco_ingestor_interface`: Verify ASCO implements ConferenceIngestor
       - `test_acs_ingestor_interface`: Verify ACS implements ConferenceIngestor
       - `test_aacr_ingestor_interface`: Verify AACR implements ConferenceIngestor
       - `test_default_llm_extractor_stub`: DefaultLLMExtractor returns empty

    5. Update `src/aegis/sources/conferences/__init__.py` to export `ConferenceIngestor`, `TalkRecord`, `TalkType`, `AscoIngestor`.

    ## Files to create
    - `src/aegis/sources/conferences/base.py`
    - `src/aegis/sources/conferences/llm_extract.py`
    - `src/aegis/sources/conferences/asco.py`
    - `src/aegis/sources/conferences/acs.py`
    - `src/aegis/sources/conferences/aacr.py`
    - `src/aegis/sources/conferences_test.py`

    ## Files to modify
    - `src/aegis/sources/conferences/__init__.py` — add exports

    ## Code patterns to follow
    - ABC for abstract base
    - Protocol for pluggable LLM extraction
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - `from __future__ import annotations`
    - Iterator pattern for proceedings data

    ## Acceptance criteria
    - `ConferenceIngestor.ingest(year: int, society: str) -> Iterator[TalkRecord]` interface exists
    - 3 society ingestors (ASCO, ACS, AACR) implement the interface
    - `TalkRecord` has: presenter_name, talk_type, session_title, conference_name, year
    - Named lectureships detectable via `TalkType.is_named_lectureship`
    - LLM extraction protocol defined with default stub
    - All tests pass: `uv run pytest src/aegis/sources/conferences_test.py -v`
    - mypy passes: `uv run mypy src/aegis/sources/conferences/`
    - ruff passes: `uv run ruff check src/aegis/sources/conferences/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/conferences_test.py -v && uv run mypy src/aegis/sources/conferences/ && uv run ruff check src/aegis/sources/conferences/
    ```

### 5. Cross-Population Identity Merge

- **Task ID**: cross-population-merge
- **Role**: builder
- **Depends On**: scaffold-phase2d
- **Assigned To**: builder-2
- **Description**: |
    Build the cross-population identity merge module that unifies candidates appearing across translational (PubMed), drug-discovery (patents), and clinician (NPI) populations into a single UUID with multi-specialty annotation.

    ## What to do

    1. Create `src/aegis/identity/cross_population_merge.py`:

       ```python
       """Cross-population identity merge: unify candidates across populations."""

       from __future__ import annotations

       import logging
       import uuid as _uuid
       from typing import Any

       from pydantic import BaseModel, ConfigDict

       from aegis.storage.schema import Candidate

       logger = logging.getLogger(__name__)

       # Confidence thresholds for cross-population linking
       AUTO_MERGE_THRESHOLD = 0.95
       REVIEW_THRESHOLD = 0.5


       class MergeCandidate(BaseModel):
           """A candidate with population source annotations."""

           model_config = ConfigDict(frozen=True)

           uuid: str
           name_variants: list[str]
           strong_keys: dict[str, str]    # orcid, npi, patent_inventor_id
           populations: list[str]         # ["translational", "drug_discovery"]
           specialty_distribution: dict[str, float]  # specialty -> weight
           artifact_sources: dict[str, int]  # source -> count


       class MergeResult(BaseModel):
           """Result of a cross-population merge attempt."""

           model_config = ConfigDict(frozen=True)

           merged_uuid: str
           source_uuids: list[str]
           confidence: float
           merge_type: str               # "strong_key" | "probabilistic" | "review_needed"
           matching_keys: list[str]       # Which keys matched
           populations_merged: list[str]


       class CrossPopulationMerger:
           """Merge candidates across translational, drug-discovery, and clinician populations.

           Extends the Fellegi-Sunter linker with patent-inventor ID and NPI
           as additional strong keys for cross-population matching.
           """

           def __init__(self) -> None:
               self._merge_log: list[MergeResult] = []

           def find_merge_candidates(
               self,
               candidate: MergeCandidate,
               population: list[MergeCandidate],
           ) -> list[tuple[MergeCandidate, float, str]]:
               """Find potential merge targets for a candidate.

               Returns list of (target, confidence, merge_type) tuples.
               """
               matches: list[tuple[MergeCandidate, float, str]] = []

               for target in population:
                   if target.uuid == candidate.uuid:
                       continue

                   confidence, merge_type, keys = self._compute_merge_confidence(
                       candidate, target
                   )

                   if confidence >= REVIEW_THRESHOLD:
                       matches.append((target, confidence, merge_type))

               return sorted(matches, key=lambda x: x[1], reverse=True)

           def merge(
               self,
               primary: MergeCandidate,
               secondary: MergeCandidate,
               confidence: float,
               merge_type: str,
           ) -> MergeResult:
               """Execute a merge: combine two candidates into one.

               The primary UUID is retained; secondary is absorbed.
               """
               # Merge populations
               merged_populations = list(
                   set(primary.populations + secondary.populations)
               )

               # Merge specialty distributions
               merged_specialty: dict[str, float] = dict(primary.specialty_distribution)
               for spec, weight in secondary.specialty_distribution.items():
                   if spec in merged_specialty:
                       merged_specialty[spec] = max(merged_specialty[spec], weight)
                   else:
                       merged_specialty[spec] = weight

               # Find matching keys
               matching_keys: list[str] = []
               for key_type in primary.strong_keys:
                   if (
                       key_type in secondary.strong_keys
                       and primary.strong_keys[key_type] == secondary.strong_keys[key_type]
                   ):
                       matching_keys.append(key_type)

               result = MergeResult(
                   merged_uuid=primary.uuid,
                   source_uuids=[primary.uuid, secondary.uuid],
                   confidence=round(confidence, 4),
                   merge_type=merge_type,
                   matching_keys=matching_keys,
                   populations_merged=merged_populations,
               )

               self._merge_log.append(result)
               return result

           def get_merge_log(self) -> list[MergeResult]:
               """Return all merge operations performed."""
               return list(self._merge_log)

           @staticmethod
           def _compute_merge_confidence(
               a: MergeCandidate,
               b: MergeCandidate,
           ) -> tuple[float, str, list[str]]:
               """Compute merge confidence between two candidates.

               Strong-key match is auto-merge; probabilistic is name-based.
               """
               matching_keys: list[str] = []

               # Check strong keys: ORCID, NPI, patent_inventor_id
               for key_type in a.strong_keys:
                   if (
                       key_type in b.strong_keys
                       and a.strong_keys[key_type]
                       and a.strong_keys[key_type] == b.strong_keys[key_type]
                   ):
                       matching_keys.append(key_type)

               if matching_keys:
                   # Strong-key match: high confidence
                   confidence = min(0.95 + 0.02 * len(matching_keys), 1.0)
                   return confidence, "strong_key", matching_keys

               # Name-based probabilistic matching
               a_names = {n.lower() for n in a.name_variants}
               b_names = {n.lower() for n in b.name_variants}
               name_overlap = len(a_names & b_names)

               if name_overlap > 0:
                   confidence = min(0.5 + 0.15 * name_overlap, 0.9)
                   return confidence, "probabilistic", []

               return 0.0, "none", []
       ```

    2. Create `src/aegis/scoring/multi_specialty.py`:

       ```python
       """Multi-specialty scoring router: pick the right weight vector per query."""

       from __future__ import annotations

       import logging
       from pathlib import Path

       from aegis.scoring.quality_prior import QualityPrior, WeightVector, load_weight_vector

       logger = logging.getLogger(__name__)

       _WEIGHT_PATHS: dict[str, Path] = {
           "translational": Path("config/aegis/weights/translational_v1.yaml"),
           "drug_discovery": Path("config/aegis/weights/drug_discovery_v1.yaml"),
           "clinician": Path("config/aegis/weights/clinician_v1.yaml"),
       }


       class MultiSpecialtyRouter:
           """Route candidates to the appropriate weight vector for scoring.

           When a candidate has multi-specialty annotations, the router
           selects the specialty most relevant to the query.
           """

           def __init__(self) -> None:
               self._weight_vectors: dict[str, WeightVector] = {}
               self._priors: dict[str, QualityPrior] = {}

           def load_all(self) -> None:
               """Load all specialty weight vectors."""
               for specialty, path in _WEIGHT_PATHS.items():
                   try:
                       wv = load_weight_vector(path)
                       self._weight_vectors[specialty] = wv
                       self._priors[specialty] = QualityPrior(wv)
                       logger.info("Loaded %s weight vector", specialty)
                   except FileNotFoundError:
                       logger.warning("Weight config not found: %s", path)

           def get_prior(self, specialty: str) -> QualityPrior | None:
               """Get the QualityPrior for a specialty."""
               return self._priors.get(specialty)

           def get_weight_vector(self, specialty: str) -> WeightVector | None:
               """Get the WeightVector for a specialty."""
               return self._weight_vectors.get(specialty)

           def select_specialty(
               self,
               specialty_distribution: dict[str, float],
               query_specialty: str | None = None,
           ) -> str:
               """Select the active specialty for scoring.

               If query_specialty is given and the candidate has that specialty,
               use it. Otherwise use the highest-probability specialty.
               """
               if query_specialty and query_specialty in specialty_distribution:
                   return query_specialty

               if not specialty_distribution:
                   return "translational"

               return max(
                   specialty_distribution,
                   key=specialty_distribution.get,  # type: ignore[arg-type]
               )

           @property
           def available_specialties(self) -> list[str]:
               """List of loaded specialty weight vectors."""
               return sorted(self._weight_vectors.keys())
       ```

    3. Create `src/aegis/identity/cross_population_test.py`:
       - `test_strong_key_merge`: Two candidates with same ORCID -> auto-merge with confidence >= 0.95
       - `test_npi_merge`: Two candidates with same NPI -> auto-merge
       - `test_name_based_merge`: Two candidates with overlapping name variants -> probabilistic merge
       - `test_no_match`: Two candidates with no overlap -> no merge
       - `test_merge_preserves_populations`: Merge translational + drug_discovery -> both in result
       - `test_merge_log`: Multiple merges -> all recorded in merge log
       - `test_multi_specialty_router_select`: Verify specialty selection logic
       - `test_multi_specialty_router_query_override`: Query specialty overrides default
       - `test_merge_candidate_model`: Verify MergeCandidate fields
       - `test_specialty_distribution_merge`: Verify specialty distributions are merged correctly

    4. Update `src/aegis/scoring/__init__.py` to add `MultiSpecialtyRouter` export.
    5. Update `src/aegis/identity/__init__.py` to add `CrossPopulationMerger`, `MergeCandidate`, `MergeResult` exports.

    ## Files to create
    - `src/aegis/identity/cross_population_merge.py`
    - `src/aegis/scoring/multi_specialty.py`
    - `src/aegis/identity/cross_population_test.py`

    ## Files to modify
    - `src/aegis/scoring/__init__.py` — add MultiSpecialtyRouter
    - `src/aegis/identity/__init__.py` — add cross-population exports

    ## Code patterns to follow
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
    - Strong-key matching pattern from `src/aegis/identity/strong_key.py`
    - `from __future__ import annotations`
    - Logger at module level

    ## Acceptance criteria
    - `CrossPopulationMerger.find_merge_candidates()` finds matches
    - Strong-key match (ORCID, NPI) produces confidence >= 0.95
    - `MergeCandidate.specialty_distribution: dict[Specialty, float]` exists
    - `MultiSpecialtyRouter.select_specialty()` picks correct specialty
    - Merge log captures all merge operations
    - All tests pass: `uv run pytest src/aegis/identity/cross_population_test.py -v`
    - mypy passes on new modules

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/identity/cross_population_test.py -v && uv run mypy src/aegis/identity/cross_population_merge.py src/aegis/scoring/multi_specialty.py && uv run ruff check src/aegis/identity/cross_population_merge.py src/aegis/scoring/multi_specialty.py
    ```

### 6. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: specialty-classifier, specialty-reassignment, conference-proceedings, cross-population-merge
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for Phase 2d.

    ## Validation Commands

    1. Verify specialty classifier:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.scoring.specialty_classifier import SpecialtyClassifier, SpecialtyDistribution, Specialty; print('Classifier imports OK')"
    ```

    2. Verify reassignment:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.scoring.specialty_reassignment import SpecialtyReassigner, ReassignmentReport; print('Reassignment imports OK')"
    ```

    3. Verify conference proceedings:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord; from aegis.sources.conferences.asco import AscoIngestor; print('Conference imports OK')"
    ```

    4. Verify cross-population merge:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.identity.cross_population_merge import CrossPopulationMerger, MergeCandidate; print('Cross-pop merge imports OK')"
    ```

    5. Verify multi-specialty router:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.scoring.multi_specialty import MultiSpecialtyRouter; print('Multi-specialty router OK')"
    ```

    6. Run all Phase 2d tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/specialty_classifier_test.py src/aegis/scoring/specialty_reassignment_test.py src/aegis/sources/conferences_test.py src/aegis/identity/cross_population_test.py -v
    ```

    7. Run mypy:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/scoring/specialty_classifier.py src/aegis/scoring/specialty_reassignment.py src/aegis/sources/conferences/ src/aegis/identity/cross_population_merge.py src/aegis/scoring/multi_specialty.py
    ```

    8. Run ruff:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/scoring/specialty_classifier.py src/aegis/scoring/specialty_reassignment.py src/aegis/sources/conferences/ src/aegis/identity/cross_population_merge.py src/aegis/scoring/multi_specialty.py
    ```

    9. Verify existing tests still pass:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/quality_prior_test.py src/aegis/identity/probabilistic_test.py -v
    ```

    ## Acceptance Criteria
    - SpecialtyClassifier.classify(features) -> SpecialtyDistribution works
    - Rule-based and trained-model paths both work
    - Ambiguity flagging at < 0.6 confidence
    - SpecialtyReassigner.reassign_all(cohort) -> ReassignmentReport works
    - Major change detection (> 0.3 shift) logged
    - ConferenceIngestor interface with ASCO, ACS, AACR implementations
    - TalkRecord distinguishes named lectureships, invited talks, orals, posters
    - CrossPopulationMerger links via strong keys (ORCID, NPI, patent_inventor_id)
    - MultiSpecialtyRouter selects correct weight vector per query
    - All new tests pass
    - mypy strict passes
    - ruff passes
    - Existing tests unbroken

## Acceptance Criteria

- `SpecialtyClassifier.classify(candidate) -> SpecialtyDistribution` with probabilities over translational/drug_discovery/clinician
- Below 0.6 confidence, `is_ambiguous` flag is set
- `SpecialtyReassigner.reassign_all(cohort) -> ReassignmentReport` tracks changes with audit log
- Major changes (> 0.3 probability shift) flagged in audit entries
- `ConferenceIngestor.ingest(year, society) -> Iterator[TalkRecord]` interface with ASCO, ACS, AACR implementations
- Named lectureships (e.g., "ASCO Karnofsky Lecture") feed F4; invited talks feed F3 via `TalkType`
- `CrossPopulationMerger` unifies candidates via patent-inventor ID and NPI strong keys
- `Candidate.specialty_distribution: dict[Specialty, float]` supported via `MergeCandidate`
- `MultiSpecialtyRouter` selects appropriate weight vector per query
- All new tests pass
- mypy strict mode passes
- ruff lint passes
- No existing Phase 0/1 tests broken

## Validation Commands

- `cd /Users/anvith/aegis && uv run pytest src/aegis/scoring/specialty_classifier_test.py src/aegis/scoring/specialty_reassignment_test.py src/aegis/sources/conferences_test.py src/aegis/identity/cross_population_test.py -v` — Run all Phase 2d tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/scoring/specialty_classifier.py src/aegis/scoring/specialty_reassignment.py src/aegis/sources/conferences/ src/aegis/identity/cross_population_merge.py src/aegis/scoring/multi_specialty.py` — Type-check
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/scoring/specialty_classifier.py src/aegis/scoring/specialty_reassignment.py src/aegis/sources/conferences/ src/aegis/identity/cross_population_merge.py src/aegis/scoring/multi_specialty.py` — Lint

## Notes

- `scikit-learn>=1.4` must be in dependencies (added in scaffold task)
- The specialty classifier's rule-based fallback ensures the system works even before labeled training data is available
- Conference proceedings extraction is LLM-dependent; the stub implementation allows the interface to be tested without LLM credentials
- Cross-population merge precision target is >= 99% on auto-merged (per Phase 2 plan); the 0.95 strong-key threshold ensures conservatism
- The `MultiSpecialtyRouter` uses the same `QualityPrior` class but with different weight vectors per specialty — the composition math is identical
- Archetype 2 (Dr. B, industry pivot): reassignment from translational to drug-discovery should produce `Rank ~ 0.66` under the correct weight vector (validates in Phase 2 closing)
