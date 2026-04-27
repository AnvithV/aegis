"""Cold-start guard: blocks deployment of unstable Plackett-Luce fits."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from aegis.learning.plackett_luce import FittedWeights

logger = logging.getLogger(__name__)

_MIN_JUDGMENTS = 20


class GuardVerdict(BaseModel):
    """Result of cold-start guard evaluation."""

    model_config = ConfigDict(frozen=True)

    allow_deployment: bool
    reason: str
    ci_half_widths: dict[str, float]
    threshold: float


class ColdStartGuard:
    """Block deployment of unstable Plackett-Luce fits."""

    def __init__(self, *, ci_threshold: float = 0.2) -> None:
        self._threshold = ci_threshold

    def evaluate(self, *, fitted: FittedWeights) -> GuardVerdict:
        """Evaluate whether the fitted weights are stable enough to deploy."""
        alpha_hw = (fitted.alpha_ci[1] - fitted.alpha_ci[0]) / 2.0
        beta_hw = (fitted.beta_ci[1] - fitted.beta_ci[0]) / 2.0
        gamma_hw = (fitted.gamma_ci[1] - fitted.gamma_ci[0]) / 2.0

        ci_half_widths = {
            "alpha": alpha_hw,
            "beta": beta_hw,
            "gamma": gamma_hw,
        }

        # Check convergence
        if not fitted.converged:
            return GuardVerdict(
                allow_deployment=False,
                reason="fit did not converge",
                ci_half_widths=ci_half_widths,
                threshold=self._threshold,
            )

        # Check minimum judgments
        if fitted.n_judgments < _MIN_JUDGMENTS:
            return GuardVerdict(
                allow_deployment=False,
                reason=f"insufficient judgments (N < {_MIN_JUDGMENTS})",
                ci_half_widths=ci_half_widths,
                threshold=self._threshold,
            )

        # Check CI widths
        wide_params: list[str] = []
        for name, hw in ci_half_widths.items():
            if hw > self._threshold:
                wide_params.append(name)

        if wide_params:
            return GuardVerdict(
                allow_deployment=False,
                reason=(
                    f"CI too wide for: {', '.join(wide_params)}"
                ),
                ci_half_widths=ci_half_widths,
                threshold=self._threshold,
            )

        return GuardVerdict(
            allow_deployment=True,
            reason="all checks passed",
            ci_half_widths=ci_half_widths,
            threshold=self._threshold,
        )
