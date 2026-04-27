"""Plackett-Luce weight fitter: learn exponents from pairwise judgments."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict
from scipy.optimize import minimize  # type: ignore[import-untyped]

from aegis.scoring.quality_prior import WeightVector

logger = logging.getLogger(__name__)

_EPS = 1e-12

# Default exponent bounds
_DEFAULT_BOUNDS: dict[str, tuple[float, float]] = {
    "alpha": (0.3, 1.2),
    "beta": (0.5, 1.5),
    "gamma": (0.1, 0.8),
}

# Default initial exponents
_DEFAULT_INITIAL: tuple[float, float, float] = (0.7, 1.0, 0.4)


class FittedWeights(BaseModel):
    """Result of Plackett-Luce exponent fitting."""

    model_config = ConfigDict(frozen=True)

    alpha: float
    beta: float
    gamma: float
    family_weights: dict[str, float]
    alpha_ci: tuple[float, float]
    beta_ci: tuple[float, float]
    gamma_ci: tuple[float, float]
    n_judgments: int
    converged: bool
    log_likelihood: float


@dataclass
class JudgmentRecord:
    """A pairwise judgment record for fitting.

    Component names: quality_prior, topical_fit, recency.
    """

    winner_scores: dict[str, float]
    loser_scores: dict[str, float]


def _compute_score(
    *,
    scores: dict[str, float],
    alpha: float,
    beta: float,
    gamma: float,
) -> float:
    """Compute S(c) = Q(c)^alpha * T(c)^beta * R(c)^gamma."""
    q = max(scores.get("quality_prior", 0.0), _EPS)
    t = max(scores.get("topical_fit", 0.0), _EPS)
    r = max(scores.get("recency", 0.0), _EPS)
    return float(q**alpha * t**beta * r**gamma)


class PlackettLuceFitter:
    """Fit Plackett-Luce model exponents from pairwise judgments."""

    def __init__(
        self,
        *,
        exponent_bounds: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        bounds = exponent_bounds or _DEFAULT_BOUNDS
        self._bounds = {
            "alpha": bounds.get("alpha", _DEFAULT_BOUNDS["alpha"]),
            "beta": bounds.get("beta", _DEFAULT_BOUNDS["beta"]),
            "gamma": bounds.get("gamma", _DEFAULT_BOUNDS["gamma"]),
        }

    def _neg_log_likelihood(
        self,
        params: NDArray[np.float64],
        judgments: list[JudgmentRecord],
    ) -> float:
        """Compute negative log-likelihood for optimization."""
        alpha, beta, gamma = float(params[0]), float(params[1]), float(params[2])
        nll = 0.0
        for j in judgments:
            s_winner = _compute_score(
                scores=j.winner_scores,
                alpha=alpha,
                beta=beta,
                gamma=gamma,
            )
            s_loser = _compute_score(
                scores=j.loser_scores,
                alpha=alpha,
                beta=beta,
                gamma=gamma,
            )
            prob = s_winner / (s_winner + s_loser + _EPS)
            nll -= np.log(prob + _EPS)
        return float(nll)

    def fit(
        self,
        *,
        judgments: list[JudgmentRecord],
        initial_weights: WeightVector | None = None,
    ) -> FittedWeights:
        """Fit exponents from pairwise judgments.

        Uses L-BFGS-B optimization on the Plackett-Luce log-likelihood.
        """
        n = len(judgments)

        # Handle empty judgments
        if n == 0:
            a0, b0, g0 = _DEFAULT_INITIAL
            return FittedWeights(
                alpha=a0,
                beta=b0,
                gamma=g0,
                family_weights={},
                alpha_ci=(a0, a0),
                beta_ci=(b0, b0),
                gamma_ci=(g0, g0),
                n_judgments=0,
                converged=True,
                log_likelihood=0.0,
            )

        # Initial point
        if initial_weights is not None:
            x0 = np.array([
                initial_weights.exponents.get("alpha", _DEFAULT_INITIAL[0]),
                initial_weights.exponents.get("beta", _DEFAULT_INITIAL[1]),
                initial_weights.exponents.get("gamma", _DEFAULT_INITIAL[2]),
            ])
        else:
            x0 = np.array(_DEFAULT_INITIAL)

        bounds_list = [
            self._bounds["alpha"],
            self._bounds["beta"],
            self._bounds["gamma"],
        ]

        result = minimize(
            self._neg_log_likelihood,
            x0,
            args=(judgments,),
            method="L-BFGS-B",
            bounds=bounds_list,
        )

        alpha = float(result.x[0])
        beta = float(result.x[1])
        gamma = float(result.x[2])
        converged: bool = bool(result.success)
        log_likelihood = -float(result.fun)

        # Confidence intervals from inverse Hessian
        alpha_ci = self._compute_ci(
            value=alpha,
            hess_inv=result.get("hess_inv"),
            index=0,
            bound=self._bounds["alpha"],
        )
        beta_ci = self._compute_ci(
            value=beta,
            hess_inv=result.get("hess_inv"),
            index=1,
            bound=self._bounds["beta"],
        )
        gamma_ci = self._compute_ci(
            value=gamma,
            hess_inv=result.get("hess_inv"),
            index=2,
            bound=self._bounds["gamma"],
        )

        # Family weights from initial_weights or empty
        family_weights: dict[str, float] = {}
        if initial_weights is not None:
            family_weights = dict(initial_weights.weights)

        return FittedWeights(
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            family_weights=family_weights,
            alpha_ci=alpha_ci,
            beta_ci=beta_ci,
            gamma_ci=gamma_ci,
            n_judgments=n,
            converged=converged,
            log_likelihood=log_likelihood,
        )

    @staticmethod
    def _compute_ci(
        *,
        value: float,
        hess_inv: Any,
        index: int,
        bound: tuple[float, float],
    ) -> tuple[float, float]:
        """Compute 95% CI from inverse Hessian diagonal."""
        try:
            if hess_inv is not None:
                # L-BFGS-B returns LbfgsInvHessProduct
                h_diag = np.diag(hess_inv.todense())
                se = float(np.sqrt(max(h_diag[index], 0.0)))
                lo = max(value - 1.96 * se, bound[0])
                hi = min(value + 1.96 * se, bound[1])
                return (lo, hi)
        except (AttributeError, IndexError, ValueError):
            pass
        return (value, value)
