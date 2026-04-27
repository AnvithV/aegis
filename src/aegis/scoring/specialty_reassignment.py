"""Dynamic specialty reassignment — nightly reclassification with audit logging."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from aegis.scoring.specialty_classifier import (
    ArtifactMixFeatures,
    SpecialtyClassifier,
    SpecialtyDistribution,
)

logger = logging.getLogger(__name__)

MAJOR_SHIFT_THRESHOLD: float = 0.3


class ReassignmentEntry(BaseModel):
    """Single reassignment audit log entry."""

    model_config = ConfigDict(frozen=True)

    entry_id: str
    candidate_uuid: str
    previous_specialty: str
    new_specialty: str
    previous_confidence: float
    new_confidence: float
    probability_shift: float
    is_major_change: bool
    timestamp: str
    artifact_mix_summary: dict[str, float]


class ReassignmentReport(BaseModel):
    """Summary report from a reassignment batch run."""

    model_config = ConfigDict(frozen=True)

    total_candidates: int
    reassigned_count: int
    major_changes: int
    stable_count: int
    entries: list[ReassignmentEntry]
    run_timestamp: str


class SpecialtyReassigner:
    """Re-classify candidates and log significant probability shifts."""

    def __init__(self, classifier: SpecialtyClassifier) -> None:
        self._classifier = classifier

    def reassign_single(
        self,
        features: ArtifactMixFeatures,
        prior: SpecialtyDistribution,
    ) -> ReassignmentEntry | None:
        """Re-classify a single candidate. Returns None if specialty unchanged."""
        new = self._classifier.classify(features)

        if new.predicted_specialty == prior.predicted_specialty:
            return None

        shift = abs(new.confidence - prior.confidence)
        for key in set(new.probabilities) | set(prior.probabilities):
            old_p = prior.probabilities.get(key, 0.0)
            new_p = new.probabilities.get(key, 0.0)
            shift = max(shift, abs(new_p - old_p))

        is_major = shift >= MAJOR_SHIFT_THRESHOLD

        entry = ReassignmentEntry(
            entry_id=str(uuid.uuid4()),
            candidate_uuid=prior.candidate_uuid,
            previous_specialty=prior.predicted_specialty,
            new_specialty=new.predicted_specialty,
            previous_confidence=prior.confidence,
            new_confidence=new.confidence,
            probability_shift=round(shift, 4),
            is_major_change=is_major,
            timestamp=datetime.now(UTC).isoformat(),
            artifact_mix_summary={
                "total_papers": float(features.total_papers),
                "total_patents": float(features.total_patents),
                "total_grants": float(features.total_grants),
                "total_trials": float(features.total_trials),
                "patent_proportion": features.patent_proportion,
                "clinician_indicator": features.clinician_indicator,
            },
        )

        logger.info(
            "Reassigned %s: %s -> %s (shift=%.3f, major=%s)",
            prior.candidate_uuid,
            prior.predicted_specialty,
            new.predicted_specialty,
            shift,
            is_major,
        )

        return entry

    def reassign_all(
        self,
        candidates: list[tuple[ArtifactMixFeatures, SpecialtyDistribution]],
    ) -> ReassignmentReport:
        """Re-classify a batch of candidates and produce a report."""
        entries: list[ReassignmentEntry] = []
        reassigned = 0
        major = 0

        for features, prior in candidates:
            entry = self.reassign_single(features, prior)
            if entry is not None:
                entries.append(entry)
                reassigned += 1
                if entry.is_major_change:
                    major += 1

        total = len(candidates)
        report = ReassignmentReport(
            total_candidates=total,
            reassigned_count=reassigned,
            major_changes=major,
            stable_count=total - reassigned,
            entries=entries,
            run_timestamp=datetime.now(UTC).isoformat(),
        )

        logger.info(
            "Reassignment run: %d total, %d reassigned, %d major, %d stable",
            total,
            reassigned,
            major,
            total - reassigned,
        )

        return report
