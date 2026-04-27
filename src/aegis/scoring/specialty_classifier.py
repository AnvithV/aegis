"""ML-based specialty classifier routing candidates to weight vectors."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
from pydantic import BaseModel, ConfigDict
from sklearn.ensemble import GradientBoostingClassifier  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

AMBIGUITY_THRESHOLD: float = 0.6


class Specialty(StrEnum):
    """Population specialty for weight vector routing."""

    translational = "translational"
    drug_discovery = "drug_discovery"
    clinician = "clinician"


class SpecialtyDistribution(BaseModel):
    """Predicted specialty distribution for a single candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    probabilities: dict[str, float]
    predicted_specialty: str
    confidence: float
    is_ambiguous: bool


@dataclass
class ArtifactMixFeatures:
    """Feature set derived from a candidate's artifact portfolio."""

    # Article features
    total_papers: int = 0
    last_author_rate: float = 0.0
    mean_rcr: float = 0.0
    rcr_above_2: int = 0

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

    # Computed proportion fields
    patent_proportion: float = field(init=False, default=0.0)
    grant_proportion: float = field(init=False, default=0.0)
    trial_proportion: float = field(init=False, default=0.0)
    clinician_indicator: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        total = max(
            self.total_papers
            + self.total_patents
            + self.total_grants
            + self.total_trials,
            1,
        )
        self.patent_proportion = self.total_patents / total
        self.grant_proportion = self.total_grants / total
        self.trial_proportion = self.total_trials / total
        self.clinician_indicator = float(
            self.has_npi or self.has_abms_certification
        )


class SpecialtyClassifier:
    """Classify candidates into specialty populations using artifact-mix features."""

    def __init__(self) -> None:
        self._model: GradientBoostingClassifier | None = None
        self._classes: list[str] = []

    @staticmethod
    def _extract_feature_vector(features: ArtifactMixFeatures) -> list[float]:
        """Extract 18 numeric features from artifact mix."""
        total_artifacts = max(
            features.total_papers
            + features.total_patents
            + features.total_grants
            + features.total_trials,
            1,
        )
        return [
            float(features.total_papers),
            features.last_author_rate,
            features.mean_rcr,
            float(features.rcr_above_2),
            float(features.total_patents),
            float(features.lead_inventor_count),
            float(features.total_grants),
            float(features.r01_equivalent_count),
            float(features.total_trials),
            float(features.phase3_trials),
            float(features.has_npi),
            float(features.has_abms_certification),
            float(features.has_hospital_affiliation),
            float(features.procedure_volume),
            features.total_patents / total_artifacts,
            features.total_grants / total_artifacts,
            features.total_trials / total_artifacts,
            float(features.has_npi or features.has_abms_certification),
        ]

    def train(
        self,
        training_data: list[tuple[ArtifactMixFeatures, str]],
    ) -> None:
        """Train the classifier on labeled feature sets."""
        if not training_data:
            msg = "Training data must not be empty"
            raise ValueError(msg)

        x = np.array(
            [self._extract_feature_vector(f) for f, _ in training_data]
        )
        y = np.array([label for _, label in training_data])

        self._model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )
        self._model.fit(x, y)
        self._classes = list(self._model.classes_)
        logger.info(
            "Trained specialty classifier on %d samples, classes=%s",
            len(training_data),
            self._classes,
        )

    def classify(self, features: ArtifactMixFeatures) -> SpecialtyDistribution:
        """Classify a candidate into a specialty population."""
        if self._model is None:
            return self._rule_based_classify(features)

        x = np.array([self._extract_feature_vector(features)])
        proba = self._model.predict_proba(x)[0]
        probabilities = {
            cls: float(p) for cls, p in zip(self._classes, proba, strict=True)
        }
        predicted = max(probabilities, key=lambda k: probabilities[k])
        confidence = probabilities[predicted]

        return SpecialtyDistribution(
            candidate_uuid=str(uuid.uuid4()),
            probabilities=probabilities,
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
        """Fallback rule-based classification when no trained model exists."""
        if features.has_npi or features.has_abms_certification:
            probabilities: dict[str, float] = {
                Specialty.clinician.value: 0.7,
                Specialty.translational.value: 0.2,
                Specialty.drug_discovery.value: 0.1,
            }
            predicted = Specialty.clinician.value
            confidence = 0.7
        elif features.total_patents > features.total_papers:
            probabilities = {
                Specialty.drug_discovery.value: 0.7,
                Specialty.translational.value: 0.2,
                Specialty.clinician.value: 0.1,
            }
            predicted = Specialty.drug_discovery.value
            confidence = 0.7
        else:
            probabilities = {
                Specialty.translational.value: 0.6,
                Specialty.drug_discovery.value: 0.25,
                Specialty.clinician.value: 0.15,
            }
            predicted = Specialty.translational
            confidence = 0.6

        return SpecialtyDistribution(
            candidate_uuid=str(uuid.uuid4()),
            probabilities=probabilities,
            predicted_specialty=predicted,
            confidence=confidence,
            is_ambiguous=confidence < AMBIGUITY_THRESHOLD,
        )
