"""R(c,q) Recency scoring — time-decayed sum over MeSH-overlapping artifacts."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

# ── defaults ────────────────────────────────────────────────────────────
DEFAULT_HALF_LIFE_YEARS: float = 3.0
PREPRINT_DISCOUNT: float = 0.6
DEFAULT_SQUASH_SCALE: float = 3.0


@dataclass
class RecencyArtifact:
    """A single publication artifact with metadata for recency scoring."""

    publication_date: date
    role_weight: float
    type_weight: float
    is_preprint: bool
    mesh_descriptors: set[str] = field(default_factory=set)


class Recency:
    """Compute R(c,q): recency score for a candidate w.r.t. a query."""

    def compute(
        self,
        candidate_artifacts: list[RecencyArtifact],
        query_mesh: set[str],
        reference_date: date,
        half_life_years: float = DEFAULT_HALF_LIFE_YEARS,
        squash_scale: float = DEFAULT_SQUASH_SCALE,
    ) -> float:
        """Return R(c,q) in [0, 1].

        Only artifacts with at least one MeSH descriptor overlapping the
        query contribute.  Each relevant artifact's contribution is
        weighted by role, evidence-type, preprint discount and exponential
        time-decay.  The raw accumulator A is squashed via
        ``1 - exp(-A / squash_scale)`` to produce a smooth saturation
        curve.
        """
        if not candidate_artifacts or not query_mesh:
            return 0.0

        tau = half_life_years / math.log(2)

        accumulator = 0.0
        for art in candidate_artifacts:
            # Only count artifacts with MeSH overlap
            if not art.mesh_descriptors & query_mesh:
                continue

            delta_years = _year_delta(art.publication_date, reference_date)
            decay = math.exp(-delta_years / tau)

            preprint_factor = PREPRINT_DISCOUNT if art.is_preprint else 1.0

            accumulator += (
                art.role_weight
                * art.type_weight
                * preprint_factor
                * decay
            )

        score = 1.0 - math.exp(-accumulator / squash_scale)
        return max(0.0, min(1.0, score))


def _year_delta(pub_date: date, reference_date: date) -> float:
    """Return the number of years between *pub_date* and *reference_date*."""
    return (reference_date - pub_date).days / 365.25
