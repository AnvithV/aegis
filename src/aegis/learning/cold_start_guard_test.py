"""Tests for the cold-start guard."""

from __future__ import annotations

import pytest

from aegis.learning.cold_start_guard import ColdStartGuard
from aegis.learning.plackett_luce import FittedWeights


def _make_fitted(
    *,
    alpha_ci: tuple[float, float] = (0.7, 0.8),
    beta_ci: tuple[float, float] = (0.9, 1.1),
    gamma_ci: tuple[float, float] = (0.35, 0.45),
    converged: bool = True,
    n_judgments: int = 100,
) -> FittedWeights:
    """Create a test FittedWeights."""
    return FittedWeights(
        alpha=0.75,
        beta=1.0,
        gamma=0.4,
        family_weights={},
        alpha_ci=alpha_ci,
        beta_ci=beta_ci,
        gamma_ci=gamma_ci,
        n_judgments=n_judgments,
        converged=converged,
        log_likelihood=-50.0,
    )


class TestColdStartGuard:
    """Tests for ColdStartGuard."""

    def test_blocks_wide_ci(self) -> None:
        """alpha_ci=(0.3, 0.9) -> half-width 0.3 > 0.2 -> blocked."""
        guard = ColdStartGuard(ci_threshold=0.2)
        fitted = _make_fitted(alpha_ci=(0.3, 0.9))
        verdict = guard.evaluate(fitted=fitted)

        assert verdict.allow_deployment is False
        assert "alpha" in verdict.reason
        assert verdict.ci_half_widths["alpha"] == pytest.approx(0.3)

    def test_allows_narrow_ci(self) -> None:
        """All CIs narrow -> allowed."""
        guard = ColdStartGuard(ci_threshold=0.2)
        fitted = _make_fitted(
            alpha_ci=(0.7, 0.8),
            beta_ci=(0.95, 1.05),
            gamma_ci=(0.38, 0.42),
        )
        verdict = guard.evaluate(fitted=fitted)

        assert verdict.allow_deployment is True
        assert verdict.reason == "all checks passed"

    def test_blocks_unconverged(self) -> None:
        """converged=False -> blocked."""
        guard = ColdStartGuard()
        fitted = _make_fitted(converged=False)
        verdict = guard.evaluate(fitted=fitted)

        assert verdict.allow_deployment is False
        assert "converge" in verdict.reason

    def test_blocks_few_judgments(self) -> None:
        """n_judgments=10 -> blocked."""
        guard = ColdStartGuard()
        fitted = _make_fitted(n_judgments=10)
        verdict = guard.evaluate(fitted=fitted)

        assert verdict.allow_deployment is False
        assert "insufficient" in verdict.reason

    def test_custom_threshold(self) -> None:
        """threshold=0.5 allows wider CIs."""
        guard = ColdStartGuard(ci_threshold=0.5)
        fitted = _make_fitted(alpha_ci=(0.3, 0.9))  # half-width 0.3
        verdict = guard.evaluate(fitted=fitted)

        assert verdict.allow_deployment is True
        assert verdict.threshold == 0.5
