"""Tests for specialty-ambiguity flagger."""

from __future__ import annotations

import pytest

from aegis.scoring.specialty_flag import SpecialtyAmbiguityFlagger


def test_high_confidence() -> None:
    f = SpecialtyAmbiguityFlagger()
    result = f.flag(
        candidate_uuid="c1",
        n_papers_in_specialty=50,
        n_papers_total=50,
        n_trials_in_specialty=10,
        n_trials_total=10,
        n_grants_in_specialty=5,
        n_grants_total=5,
    )
    assert result.specialty_confidence == pytest.approx(1.0)
    assert result.is_ambiguous is False


def test_low_confidence() -> None:
    f = SpecialtyAmbiguityFlagger()
    result = f.flag(
        candidate_uuid="c1",
        n_papers_in_specialty=5,
        n_papers_total=50,
        n_trials_in_specialty=1,
        n_trials_total=10,
        n_grants_in_specialty=0,
        n_grants_total=5,
    )
    # 0.5*(5/50) + 0.3*(1/10) + 0.2*(0/5) = 0.05 + 0.03 + 0.0 = 0.08
    assert result.specialty_confidence == pytest.approx(0.08)
    assert result.is_ambiguous is True


def test_threshold_boundary() -> None:
    """At threshold -> not ambiguous (>= comparison)."""
    f = SpecialtyAmbiguityFlagger(threshold=0.5)
    result = f.flag(
        candidate_uuid="c1",
        n_papers_in_specialty=50,
        n_papers_total=100,
        n_trials_in_specialty=5,
        n_trials_total=10,
        n_grants_in_specialty=5,
        n_grants_total=10,
    )
    # 0.5*(50/100) + 0.3*(5/10) + 0.2*(5/10) = 0.25 + 0.15 + 0.10 = 0.50
    assert result.specialty_confidence == pytest.approx(0.5)
    assert result.is_ambiguous is False


def test_zero_total_artifacts() -> None:
    f = SpecialtyAmbiguityFlagger()
    result = f.flag(
        candidate_uuid="c1",
        n_papers_in_specialty=0,
        n_papers_total=0,
        n_trials_in_specialty=0,
        n_trials_total=0,
        n_grants_in_specialty=0,
        n_grants_total=0,
    )
    assert result.specialty_confidence == pytest.approx(0.0)
    assert result.is_ambiguous is True


def test_custom_threshold() -> None:
    f = SpecialtyAmbiguityFlagger(threshold=0.8)
    result = f.flag(
        candidate_uuid="c1",
        n_papers_in_specialty=30,
        n_papers_total=50,
        n_trials_in_specialty=5,
        n_trials_total=10,
        n_grants_in_specialty=3,
        n_grants_total=5,
    )
    # 0.5*(30/50) + 0.3*(5/10) + 0.2*(3/5) = 0.30 + 0.15 + 0.12 = 0.57
    assert result.specialty_confidence == pytest.approx(0.57)
    assert result.is_ambiguous is True  # 0.57 < 0.8


def test_artifact_mix_breakdown() -> None:
    f = SpecialtyAmbiguityFlagger()
    result = f.flag(
        candidate_uuid="c1",
        n_papers_in_specialty=20,
        n_papers_total=40,
        n_trials_in_specialty=3,
        n_trials_total=10,
        n_grants_in_specialty=1,
        n_grants_total=4,
    )
    assert result.artifact_mix["paper_ratio"] == pytest.approx(0.5)
    assert result.artifact_mix["trial_ratio"] == pytest.approx(0.3)
    assert result.artifact_mix["grant_ratio"] == pytest.approx(0.25)


def test_industry_pivot_pattern() -> None:
    """Archetype 2: someone pivoting from industry has sparse academic record."""
    f = SpecialtyAmbiguityFlagger()
    result = f.flag(
        candidate_uuid="industry_pivot",
        n_papers_in_specialty=2,
        n_papers_total=30,
        n_trials_in_specialty=8,
        n_trials_total=10,
        n_grants_in_specialty=0,
        n_grants_total=2,
    )
    # 0.5*(2/30) + 0.3*(8/10) + 0.2*(0/2) = 0.0333 + 0.24 + 0.0 = 0.2733
    assert result.specialty_confidence == pytest.approx(0.2733, abs=0.01)
    assert result.is_ambiguous is True
