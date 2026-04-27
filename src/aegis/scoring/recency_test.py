"""Tests for R(c,q) recency scoring."""

from __future__ import annotations

import math
from datetime import date

import pytest

from aegis.scoring.recency import (
    DEFAULT_HALF_LIFE_YEARS,
    DEFAULT_SQUASH_SCALE,
    PREPRINT_DISCOUNT,
    Recency,
    RecencyArtifact,
)

REF_DATE = date(2026, 4, 25)
QUERY_MESH = {"D001158", "D006333"}  # two arbitrary MeSH descriptors


def _art(
    years_ago: float = 0.0,
    role_weight: float = 1.0,
    type_weight: float = 1.0,
    is_preprint: bool = False,
    mesh: set[str] | None = None,
) -> RecencyArtifact:
    """Helper to build a RecencyArtifact relative to REF_DATE."""
    pub = date.fromordinal(
        REF_DATE.toordinal() - int(years_ago * 365.25)
    )
    return RecencyArtifact(
        publication_date=pub,
        role_weight=role_weight,
        type_weight=type_weight,
        is_preprint=is_preprint,
        mesh_descriptors=mesh if mesh is not None else {"D001158"},
    )


class TestRecency:
    """Suite for Recency.compute."""

    scorer = Recency()

    def test_recent_activity_high_score(self) -> None:
        """A single very recent artifact should produce a meaningful score."""
        arts = [_art(years_ago=0.1)]
        score = self.scorer.compute(arts, QUERY_MESH, REF_DATE)
        assert score > 0.2

    def test_old_activity_low_score(self) -> None:
        """A single artifact from 20 years ago should produce a very low score."""
        arts = [_art(years_ago=20.0)]
        score = self.scorer.compute(arts, QUERY_MESH, REF_DATE)
        assert score < 0.05

    def test_no_relevant_artifacts_returns_zero(self) -> None:
        """Artifacts with no MeSH overlap should yield 0."""
        arts = [_art(mesh={"D999999"})]  # no overlap with QUERY_MESH
        score = self.scorer.compute(arts, QUERY_MESH, REF_DATE)
        assert score == 0.0

    def test_empty_artifacts_returns_zero(self) -> None:
        """An empty artifact list should yield 0."""
        score = self.scorer.compute([], QUERY_MESH, REF_DATE)
        assert score == 0.0

    def test_preprint_discount(self) -> None:
        """A preprint should score lower than an identical non-preprint."""
        arts_pub = [_art(years_ago=1.0, is_preprint=False)]
        arts_pre = [_art(years_ago=1.0, is_preprint=True)]
        score_pub = self.scorer.compute(arts_pub, QUERY_MESH, REF_DATE)
        score_pre = self.scorer.compute(arts_pre, QUERY_MESH, REF_DATE)
        assert score_pre < score_pub
        # Verify the ratio reflects the discount
        # For single artifact: score = 1 - exp(-w/s) vs 1 - exp(-0.6w/s)
        tau = DEFAULT_HALF_LIFE_YEARS / math.log(2)
        decay = math.exp(-1.0 * 365.25 / (tau * 365.25))
        expected_pub = 1.0 - math.exp(-decay / DEFAULT_SQUASH_SCALE)
        expected_pre = 1.0 - math.exp(
            -(decay * PREPRINT_DISCOUNT) / DEFAULT_SQUASH_SCALE
        )
        assert abs(score_pub - expected_pub) < 1e-3
        assert abs(score_pre - expected_pre) < 1e-3

    def test_tunable_half_life(self) -> None:
        """Shorter half-life should penalize older artifacts more."""
        arts = [_art(years_ago=5.0)]
        score_long = self.scorer.compute(
            arts, QUERY_MESH, REF_DATE, half_life_years=10.0
        )
        score_short = self.scorer.compute(
            arts, QUERY_MESH, REF_DATE, half_life_years=1.0
        )
        assert score_long > score_short

    def test_role_weight(self) -> None:
        """Higher role_weight should increase the score."""
        arts_low = [_art(years_ago=1.0, role_weight=0.3)]
        arts_high = [_art(years_ago=1.0, role_weight=1.0)]
        score_low = self.scorer.compute(arts_low, QUERY_MESH, REF_DATE)
        score_high = self.scorer.compute(arts_high, QUERY_MESH, REF_DATE)
        assert score_high > score_low

    def test_squash_saturation(self) -> None:
        """Many recent artifacts should saturate near 1.0."""
        arts = [_art(years_ago=0.5) for _ in range(50)]
        score = self.scorer.compute(arts, QUERY_MESH, REF_DATE)
        assert score > 0.95

    def test_range_clamping(self) -> None:
        """Score should always be in [0, 1]."""
        # Many recent artifacts
        arts = [_art(years_ago=0.1) for _ in range(100)]
        score = self.scorer.compute(arts, QUERY_MESH, REF_DATE)
        assert 0.0 <= score <= 1.0

        # No artifacts
        score_empty = self.scorer.compute([], QUERY_MESH, REF_DATE)
        assert 0.0 <= score_empty <= 1.0

    def test_future_dated_artifacts(self) -> None:
        """An artifact published *after* reference_date should still contribute.

        A negative delta_years means the paper is in the future relative
        to reference_date — the exponential decay becomes a boost (>1),
        but the squash keeps the score in [0, 1].
        """
        arts = [_art(years_ago=-1.0)]  # 1 year in the future
        score = self.scorer.compute(arts, QUERY_MESH, REF_DATE)
        assert 0.0 <= score <= 1.0
        # Future paper should score higher than a same-day paper
        arts_today = [_art(years_ago=0.0)]
        score_today = self.scorer.compute(arts_today, QUERY_MESH, REF_DATE)
        assert score >= score_today
