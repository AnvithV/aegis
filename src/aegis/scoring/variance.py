"""Bootstrap score-variance estimation: per-candidate score bands."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict


class ScoreBand(BaseModel):
    """95% bootstrap confidence interval for a candidate score."""

    model_config = ConfigDict(frozen=True)

    low: float
    high: float
    median: float
    n_samples: int


@dataclass
class BootstrapInput:
    """Input data for bootstrap variance estimation."""

    candidate_uuid: str
    integrity_score: float
    quality_percentile: float
    topical_fit: float
    recency: float


# Clamping bounds for sampled exponents
_ALPHA_BOUNDS = (0.3, 1.2)
_BETA_BOUNDS = (0.5, 1.5)
_GAMMA_BOUNDS = (0.1, 0.8)


def _safe_pow(base: float, exp: float) -> float:
    """Raise *base* to *exp*, treating non-positive base as 0."""
    if base <= 0.0:
        return 0.0
    result: float = float(base**exp)
    return result


class Bootstrap:
    """Monte-Carlo bootstrap estimator for candidate score uncertainty."""

    def __init__(self, *, rng_seed: int | None = None) -> None:
        self._rng = np.random.default_rng(rng_seed)

    def estimate(
        self,
        candidates: list[BootstrapInput],
        weight_mean: tuple[float, float, float],
        weight_cov: NDArray[np.float64],
        n_samples: int = 200,
    ) -> dict[str, ScoreBand]:
        """Produce per-candidate score bands via weight resampling.

        Parameters
        ----------
        candidates:
            List of candidate inputs to score.
        weight_mean:
            Central (alpha, beta, gamma) exponents.
        weight_cov:
            3x3 covariance matrix for the exponent distribution.
        n_samples:
            Number of Monte-Carlo draws.

        Returns
        -------
        dict mapping candidate_uuid to ScoreBand.
        """
        # Draw all weight samples at once: shape (n_samples, 3)
        samples: NDArray[np.float64] = self._rng.multivariate_normal(
            mean=list(weight_mean),
            cov=weight_cov,
            size=n_samples,
        )

        # Clamp to bounds
        samples[:, 0] = np.clip(samples[:, 0], *_ALPHA_BOUNDS)
        samples[:, 1] = np.clip(samples[:, 1], *_BETA_BOUNDS)
        samples[:, 2] = np.clip(samples[:, 2], *_GAMMA_BOUNDS)

        result: dict[str, ScoreBand] = {}
        for c in candidates:
            scores = np.empty(n_samples)
            for i in range(n_samples):
                alpha_s = float(samples[i, 0])
                beta_s = float(samples[i, 1])
                gamma_s = float(samples[i, 2])
                scores[i] = (
                    c.integrity_score
                    * _safe_pow(c.quality_percentile, alpha_s)
                    * _safe_pow(c.topical_fit, beta_s)
                    * _safe_pow(c.recency, gamma_s)
                )

            low = float(np.percentile(scores, 2.5))
            high = float(np.percentile(scores, 97.5))
            median = float(np.percentile(scores, 50.0))

            result[c.candidate_uuid] = ScoreBand(
                low=low,
                high=high,
                median=median,
                n_samples=n_samples,
            )

        return result
