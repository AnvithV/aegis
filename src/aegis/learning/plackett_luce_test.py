"""Tests for the Plackett-Luce exponent fitter."""

from __future__ import annotations

import random

import pytest

from aegis.learning.plackett_luce import (
    FittedWeights,
    JudgmentRecord,
    PlackettLuceFitter,
    _compute_score,
)


def _generate_synthetic_judgments(
    *,
    alpha: float,
    beta: float,
    gamma: float,
    n: int,
    seed: int = 42,
) -> list[JudgmentRecord]:
    """Generate synthetic pairwise judgments with known exponents."""
    rng = random.Random(seed)
    judgments: list[JudgmentRecord] = []

    for _ in range(n):
        # Generate random component scores for two candidates
        # Use wide range [0.01, 1.0] so exponents have more leverage
        winner_scores = {
            "quality_prior": rng.uniform(0.01, 1.0),
            "topical_fit": rng.uniform(0.01, 1.0),
            "recency": rng.uniform(0.01, 1.0),
        }
        loser_scores = {
            "quality_prior": rng.uniform(0.01, 1.0),
            "topical_fit": rng.uniform(0.01, 1.0),
            "recency": rng.uniform(0.01, 1.0),
        }

        # Compute true scores
        s_a = _compute_score(
            scores=winner_scores,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )
        s_b = _compute_score(
            scores=loser_scores,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )

        # Probabilistic choice based on true model
        prob_a = s_a / (s_a + s_b)
        if rng.random() < prob_a:
            judgments.append(
                JudgmentRecord(
                    winner_scores=winner_scores,
                    loser_scores=loser_scores,
                )
            )
        else:
            judgments.append(
                JudgmentRecord(
                    winner_scores=loser_scores,
                    loser_scores=winner_scores,
                )
            )

    return judgments


class TestPlackettLuceFitter:
    """Tests for PlackettLuceFitter."""

    def test_fit_recovers_known_exponents(self) -> None:
        """2000 synthetic judgments with known alpha=0.8, beta=1.1, gamma=0.5."""
        true_alpha, true_beta, true_gamma = 0.8, 1.1, 0.5
        judgments = _generate_synthetic_judgments(
            alpha=true_alpha,
            beta=true_beta,
            gamma=true_gamma,
            n=2000,
        )

        fitter = PlackettLuceFitter()
        result = fitter.fit(judgments=judgments)

        assert result.alpha == pytest.approx(true_alpha, abs=0.15)
        assert result.beta == pytest.approx(true_beta, abs=0.15)
        assert result.gamma == pytest.approx(true_gamma, abs=0.15)

    def test_fit_converges(self) -> None:
        """Converged flag is True on well-behaved data."""
        judgments = _generate_synthetic_judgments(
            alpha=0.7,
            beta=1.0,
            gamma=0.4,
            n=100,
        )

        fitter = PlackettLuceFitter()
        result = fitter.fit(judgments=judgments)
        assert result.converged is True

    def test_confidence_intervals(self) -> None:
        """CIs bracket true parameters."""
        true_alpha, true_beta, true_gamma = 0.8, 1.1, 0.5
        judgments = _generate_synthetic_judgments(
            alpha=true_alpha,
            beta=true_beta,
            gamma=true_gamma,
            n=2000,
        )

        fitter = PlackettLuceFitter()
        result = fitter.fit(judgments=judgments)

        assert result.alpha_ci[0] <= true_alpha <= result.alpha_ci[1]
        assert result.beta_ci[0] <= true_beta <= result.beta_ci[1]
        assert result.gamma_ci[0] <= true_gamma <= result.gamma_ci[1]

    def test_fit_with_few_judgments(self) -> None:
        """10 judgments should not crash."""
        judgments = _generate_synthetic_judgments(
            alpha=0.7,
            beta=1.0,
            gamma=0.4,
            n=10,
        )

        fitter = PlackettLuceFitter()
        result = fitter.fit(judgments=judgments)
        assert isinstance(result, FittedWeights)
        assert result.n_judgments == 10

    def test_bounds_enforced(self) -> None:
        """Fitted alpha stays within bounds."""
        judgments = _generate_synthetic_judgments(
            alpha=0.3,  # at lower bound
            beta=1.5,  # at upper bound
            gamma=0.4,
            n=100,
        )

        fitter = PlackettLuceFitter(
            exponent_bounds={
                "alpha": (0.3, 1.2),
                "beta": (0.5, 1.5),
                "gamma": (0.1, 0.8),
            }
        )
        result = fitter.fit(judgments=judgments)

        assert 0.3 <= result.alpha <= 1.2
        assert 0.5 <= result.beta <= 1.5
        assert 0.1 <= result.gamma <= 0.8

    def test_empty_judgments(self) -> None:
        """Empty list returns sensible defaults."""
        fitter = PlackettLuceFitter()
        result = fitter.fit(judgments=[])

        assert result.n_judgments == 0
        assert result.converged is True
        assert result.alpha == pytest.approx(0.7)
        assert result.beta == pytest.approx(1.0)
        assert result.gamma == pytest.approx(0.4)
        assert result.log_likelihood == 0.0
