"""Tests for bootstrap score-variance estimation."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.scoring.variance import Bootstrap, BootstrapInput, ScoreBand


def _make_candidates(n: int = 5) -> list[BootstrapInput]:
    return [
        BootstrapInput(
            candidate_uuid=f"c{i}",
            integrity_score=0.5 + 0.1 * i,
            quality_percentile=0.6 + 0.05 * i,
            topical_fit=0.7 + 0.03 * i,
            recency=0.8 + 0.02 * i,
        )
        for i in range(n)
    ]


MEAN = (0.7, 1.0, 0.4)


def test_estimate_returns_bands() -> None:
    cov = np.diag([0.01, 0.01, 0.01])
    bs = Bootstrap(rng_seed=42)
    bands = bs.estimate(_make_candidates(5), MEAN, cov, n_samples=200)

    assert len(bands) == 5
    for uid, band in bands.items():
        assert isinstance(band, ScoreBand)
        assert band.low <= band.median <= band.high
        assert band.n_samples == 200


def test_narrow_cov_narrow_bands() -> None:
    cov = np.diag([1e-8, 1e-8, 1e-8])
    bs = Bootstrap(rng_seed=42)
    bands = bs.estimate(_make_candidates(3), MEAN, cov, n_samples=300)

    for band in bands.values():
        assert band.high - band.low < 0.1


def test_wide_cov_wide_bands() -> None:
    cov = np.diag([0.5, 0.5, 0.5])
    bs = Bootstrap(rng_seed=42)
    bands = bs.estimate(_make_candidates(3), MEAN, cov, n_samples=300)

    # At least one band should be wider than 0.01
    widths = [b.high - b.low for b in bands.values()]
    assert max(widths) > 0.01


def test_bootstrap_ci_brackets_truth() -> None:
    """90%+ of candidates should have true score within [low, high]."""
    alpha, beta, gamma = MEAN
    candidates = _make_candidates(10)
    cov = np.diag([0.02, 0.02, 0.02])

    bs = Bootstrap(rng_seed=42)
    bands = bs.estimate(candidates, MEAN, cov, n_samples=500)

    bracketed = 0
    for c in candidates:
        true_score = (
            c.integrity_score
            * (c.quality_percentile ** alpha)
            * (c.topical_fit ** beta)
            * (c.recency ** gamma)
        )
        band = bands[c.candidate_uuid]
        if band.low <= true_score <= band.high:
            bracketed += 1

    assert bracketed / len(candidates) >= 0.9


def test_zero_integrity_stays_zero() -> None:
    candidates = [
        BootstrapInput(
            candidate_uuid="zero",
            integrity_score=0.0,
            quality_percentile=0.8,
            topical_fit=0.7,
            recency=0.9,
        )
    ]
    cov = np.diag([0.01, 0.01, 0.01])
    bs = Bootstrap(rng_seed=42)
    bands = bs.estimate(candidates, MEAN, cov, n_samples=200)

    band = bands["zero"]
    assert band.low == pytest.approx(0.0)
    assert band.high == pytest.approx(0.0)
    assert band.median == pytest.approx(0.0)
    assert band.n_samples == 200


def test_deterministic_with_seed() -> None:
    cov = np.diag([0.05, 0.05, 0.05])
    candidates = _make_candidates(3)

    bs1 = Bootstrap(rng_seed=123)
    bands1 = bs1.estimate(candidates, MEAN, cov, n_samples=200)

    bs2 = Bootstrap(rng_seed=123)
    bands2 = bs2.estimate(candidates, MEAN, cov, n_samples=200)

    for uid in bands1:
        assert bands1[uid].low == pytest.approx(bands2[uid].low)
        assert bands1[uid].high == pytest.approx(bands2[uid].high)
        assert bands1[uid].median == pytest.approx(bands2[uid].median)
