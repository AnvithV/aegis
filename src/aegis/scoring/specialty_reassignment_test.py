"""Tests for dynamic specialty reassignment."""

from __future__ import annotations

import pytest

from aegis.scoring.specialty_classifier import (
    ArtifactMixFeatures,
    Specialty,
    SpecialtyClassifier,
    SpecialtyDistribution,
)
from aegis.scoring.specialty_reassignment import (
    MAJOR_SHIFT_THRESHOLD,
    ReassignmentEntry,
    ReassignmentReport,
    SpecialtyReassigner,
)


def _make_prior(
    specialty: str,
    confidence: float,
    *,
    uuid: str = "candidate-001",
) -> SpecialtyDistribution:
    """Create a prior SpecialtyDistribution for testing."""
    probs = {
        Specialty.translational.value: 0.1,
        Specialty.drug_discovery.value: 0.1,
        Specialty.clinician.value: 0.1,
    }
    probs[specialty] = confidence
    # Normalize remaining
    remaining = 1.0 - confidence
    others = [k for k in probs if k != specialty]
    for k in others:
        probs[k] = remaining / len(others)

    return SpecialtyDistribution(
        candidate_uuid=uuid,
        probabilities=probs,
        predicted_specialty=specialty,
        confidence=confidence,
        is_ambiguous=confidence < 0.6,
    )


def test_reassign_no_change() -> None:
    """When specialty stays the same, reassign_single returns None."""
    clf = SpecialtyClassifier()
    reassigner = SpecialtyReassigner(clf)

    # Translational features → rule-based predicts translational
    features = ArtifactMixFeatures(total_papers=20, mean_rcr=3.0)
    prior = _make_prior(Specialty.translational.value, 0.6)

    result = reassigner.reassign_single(features, prior)
    assert result is None


def test_reassign_specialty_change() -> None:
    """When features now indicate clinician but prior was translational."""
    clf = SpecialtyClassifier()
    reassigner = SpecialtyReassigner(clf)

    # Clinician features (has_npi) → rule-based predicts clinician
    features = ArtifactMixFeatures(
        total_papers=5,
        has_npi=True,
        has_abms_certification=True,
    )
    prior = _make_prior(Specialty.translational.value, 0.6)

    result = reassigner.reassign_single(features, prior)
    assert result is not None
    assert result.previous_specialty == Specialty.translational.value
    assert result.new_specialty == Specialty.clinician.value
    assert result.candidate_uuid == "candidate-001"


def test_major_change_detection() -> None:
    """Large probability shifts should be flagged as major changes."""
    clf = SpecialtyClassifier()
    reassigner = SpecialtyReassigner(clf)

    # Drug discovery features, prior was translational with high confidence
    features = ArtifactMixFeatures(
        total_papers=2,
        total_patents=20,
        lead_inventor_count=10,
    )
    prior = _make_prior(Specialty.translational.value, 0.8)

    result = reassigner.reassign_single(features, prior)
    assert result is not None
    assert result.is_major_change
    assert result.probability_shift >= MAJOR_SHIFT_THRESHOLD


def test_reassign_all_report() -> None:
    """Batch reassignment produces correct report tallies."""
    clf = SpecialtyClassifier()
    reassigner = SpecialtyReassigner(clf)

    candidates: list[tuple[ArtifactMixFeatures, SpecialtyDistribution]] = []

    # 5 stable translational
    for i in range(5):
        features = ArtifactMixFeatures(total_papers=20, mean_rcr=2.5)
        prior = _make_prior(
            Specialty.translational.value, 0.6, uuid=f"stable-{i}"
        )
        candidates.append((features, prior))

    # 3 changing: translational → clinician
    for i in range(3):
        features = ArtifactMixFeatures(
            total_papers=5,
            has_npi=True,
            has_abms_certification=True,
        )
        prior = _make_prior(
            Specialty.translational.value, 0.7, uuid=f"change-{i}"
        )
        candidates.append((features, prior))

    # 2 changing: translational → drug_discovery
    for i in range(2):
        features = ArtifactMixFeatures(
            total_papers=2,
            total_patents=15,
            lead_inventor_count=5,
        )
        prior = _make_prior(
            Specialty.translational.value, 0.7, uuid=f"dd-change-{i}"
        )
        candidates.append((features, prior))

    report = reassigner.reassign_all(candidates)

    assert report.total_candidates == 10
    assert report.stable_count == 5
    assert report.reassigned_count == 5
    assert len(report.entries) == 5
    assert report.run_timestamp  # non-empty


def test_audit_log_artifact_summary() -> None:
    """Reassignment entries should contain artifact mix summary."""
    clf = SpecialtyClassifier()
    reassigner = SpecialtyReassigner(clf)

    features = ArtifactMixFeatures(
        total_papers=5,
        total_patents=3,
        total_grants=2,
        total_trials=1,
        has_npi=True,
    )
    prior = _make_prior(Specialty.drug_discovery.value, 0.7)

    result = reassigner.reassign_single(features, prior)
    assert result is not None
    summary = result.artifact_mix_summary
    assert "total_papers" in summary
    assert "total_patents" in summary
    assert "patent_proportion" in summary
    assert "clinician_indicator" in summary
    assert summary["total_papers"] == 5.0
    assert summary["clinician_indicator"] == 1.0


def test_reassignment_entry_model() -> None:
    """ReassignmentEntry is a frozen Pydantic model."""
    entry = ReassignmentEntry(
        entry_id="test-entry",
        candidate_uuid="test-candidate",
        previous_specialty="translational",
        new_specialty="clinician",
        previous_confidence=0.6,
        new_confidence=0.7,
        probability_shift=0.5,
        is_major_change=True,
        timestamp="2024-01-01T00:00:00+00:00",
        artifact_mix_summary={"total_papers": 10.0},
    )
    assert entry.entry_id == "test-entry"
    assert entry.is_major_change

    with pytest.raises(Exception):  # noqa: B017
        entry.is_major_change = False  # type: ignore[misc]


def test_report_timestamps() -> None:
    """Report should have valid ISO timestamps."""
    clf = SpecialtyClassifier()
    reassigner = SpecialtyReassigner(clf)

    features = ArtifactMixFeatures(
        total_papers=5,
        has_npi=True,
    )
    prior = _make_prior(Specialty.translational.value, 0.6)

    # Create a change to get an entry with timestamp
    result = reassigner.reassign_single(features, prior)
    assert result is not None
    assert "T" in result.timestamp  # ISO format

    report = reassigner.reassign_all([(features, prior)])
    assert "T" in report.run_timestamp
