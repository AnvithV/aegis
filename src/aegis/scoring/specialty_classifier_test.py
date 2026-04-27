"""Tests for specialty classifier."""

from __future__ import annotations

import pytest

from aegis.scoring.specialty_classifier import (
    AMBIGUITY_THRESHOLD,
    ArtifactMixFeatures,
    Specialty,
    SpecialtyClassifier,
    SpecialtyDistribution,
)


def test_specialty_enum() -> None:
    assert Specialty.translational == "translational"
    assert Specialty.drug_discovery == "drug_discovery"
    assert Specialty.clinician == "clinician"
    assert len(Specialty) == 3


def test_rule_based_clinician() -> None:
    clf = SpecialtyClassifier()
    features = ArtifactMixFeatures(
        total_papers=10,
        has_npi=True,
        has_abms_certification=True,
    )
    result = clf.classify(features)
    assert result.predicted_specialty == Specialty.clinician
    assert result.confidence == 0.7
    assert not result.is_ambiguous


def test_rule_based_drug_discovery() -> None:
    clf = SpecialtyClassifier()
    features = ArtifactMixFeatures(
        total_papers=2,
        total_patents=10,
        lead_inventor_count=5,
    )
    result = clf.classify(features)
    assert result.predicted_specialty == Specialty.drug_discovery
    assert result.confidence == 0.7
    assert not result.is_ambiguous


def test_rule_based_translational() -> None:
    clf = SpecialtyClassifier()
    features = ArtifactMixFeatures(
        total_papers=20,
        mean_rcr=3.5,
        total_grants=5,
    )
    result = clf.classify(features)
    assert result.predicted_specialty == Specialty.translational
    assert result.confidence == 0.6
    assert not result.is_ambiguous


def test_ambiguity_flag() -> None:
    """Translational default has confidence=0.6, equal to threshold, so not ambiguous."""
    clf = SpecialtyClassifier()
    features = ArtifactMixFeatures(total_papers=1)
    result = clf.classify(features)
    assert result.confidence == pytest.approx(AMBIGUITY_THRESHOLD)
    assert not result.is_ambiguous


def _make_synthetic_data(
    n_per_class: int,
) -> list[tuple[ArtifactMixFeatures, str]]:
    """Generate synthetic training data for all three classes."""
    data: list[tuple[ArtifactMixFeatures, str]] = []

    for _ in range(n_per_class):
        data.append((
            ArtifactMixFeatures(
                total_papers=30,
                last_author_rate=0.4,
                mean_rcr=3.0,
                rcr_above_2=15,
                total_grants=5,
                r01_equivalent_count=2,
            ),
            Specialty.translational,
        ))

    for _ in range(n_per_class):
        data.append((
            ArtifactMixFeatures(
                total_papers=5,
                total_patents=20,
                lead_inventor_count=10,
            ),
            Specialty.drug_discovery,
        ))

    for _ in range(n_per_class):
        data.append((
            ArtifactMixFeatures(
                total_papers=8,
                total_trials=5,
                has_npi=True,
                has_abms_certification=True,
                has_hospital_affiliation=True,
                procedure_volume=200,
            ),
            Specialty.clinician,
        ))

    return data


def test_train_and_classify() -> None:
    clf = SpecialtyClassifier()
    training_data = _make_synthetic_data(30)
    clf.train(training_data)

    # Translational profile
    result = clf.classify(
        ArtifactMixFeatures(
            total_papers=25,
            last_author_rate=0.3,
            mean_rcr=2.5,
            rcr_above_2=10,
            total_grants=4,
            r01_equivalent_count=1,
        )
    )
    assert result.predicted_specialty == Specialty.translational

    # Drug discovery profile
    result = clf.classify(
        ArtifactMixFeatures(
            total_papers=3,
            total_patents=15,
            lead_inventor_count=8,
        )
    )
    assert result.predicted_specialty == Specialty.drug_discovery

    # Clinician profile
    result = clf.classify(
        ArtifactMixFeatures(
            total_papers=5,
            has_npi=True,
            has_abms_certification=True,
            has_hospital_affiliation=True,
            procedure_volume=150,
        )
    )
    assert result.predicted_specialty == Specialty.clinician


def test_batch_classify() -> None:
    clf = SpecialtyClassifier()
    features_list = [
        ArtifactMixFeatures(total_papers=20, mean_rcr=3.0),
        ArtifactMixFeatures(total_patents=15, total_papers=2),
        ArtifactMixFeatures(has_npi=True),
    ]
    results = clf.classify_batch(features_list)
    assert len(results) == 3
    assert all(isinstance(r, SpecialtyDistribution) for r in results)


def test_feature_vector_extraction() -> None:
    features = ArtifactMixFeatures(
        total_papers=10,
        last_author_rate=0.5,
        mean_rcr=2.0,
        rcr_above_2=5,
        total_patents=3,
        lead_inventor_count=1,
        total_grants=2,
        r01_equivalent_count=1,
        total_trials=1,
        phase3_trials=0,
        has_npi=True,
        has_abms_certification=False,
        has_hospital_affiliation=True,
        procedure_volume=50,
    )
    vec = SpecialtyClassifier._extract_feature_vector(features)
    assert len(vec) == 18
    assert all(isinstance(v, float) for v in vec)


def test_probability_distribution_sums_to_1() -> None:
    clf = SpecialtyClassifier()
    features = ArtifactMixFeatures(total_papers=10, has_npi=True)
    result = clf.classify(features)
    total = sum(result.probabilities.values())
    assert total == pytest.approx(1.0, abs=0.01)


def test_specialty_distribution_model() -> None:
    dist = SpecialtyDistribution(
        candidate_uuid="test-uuid",
        probabilities={
            Specialty.translational: 0.5,
            Specialty.drug_discovery: 0.3,
            Specialty.clinician: 0.2,
        },
        predicted_specialty=Specialty.translational,
        confidence=0.5,
        is_ambiguous=True,
    )
    assert dist.candidate_uuid == "test-uuid"
    assert dist.is_ambiguous
    assert dist.confidence == 0.5

    # Frozen model
    with pytest.raises(Exception):  # noqa: B017
        dist.confidence = 0.9  # type: ignore[misc]
