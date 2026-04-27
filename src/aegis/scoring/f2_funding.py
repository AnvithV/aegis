"""F2 sub-score: NIH funding and resource-getting."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict


class F2Score(BaseModel):
    """Result of F2 computation for a single candidate."""

    model_config = ConfigDict(frozen=True)

    total_cost_log: float
    active_r01_equivalent: float
    percentile: float  # percentile within cohort, 0.0-1.0
    grant_count: int


# PI role weights
ROLE_WEIGHT_CONTACT_PI: float = 1.0
ROLE_WEIGHT_MULTI_PI: float = 0.7
ROLE_WEIGHT_CO_I: float = 0.3

# Grant type weights
_GRANT_TYPE_WEIGHT_HIGH: float = 1.0  # R01, U01, P01
_GRANT_TYPE_WEIGHT_K: float = 0.6  # K-series
_GRANT_TYPE_WEIGHT_SMALL: float = 0.4  # R03, R21
_GRANT_TYPE_WEIGHT_OTHER: float = 0.2

# R01-equivalent activity codes
_R01_EQUIVALENT_CODES: frozenset[str] = frozenset(
    {"R01", "U01", "P01"}
)

# Active grant multiplier
ACTIVE_MULTIPLIER: float = 2.0


def _role_weight(pi_role: str) -> float:
    """Map PI role string to weight."""
    role = pi_role.strip().lower()
    if role in ("contact pi", "contact pi/project leader"):
        return ROLE_WEIGHT_CONTACT_PI
    if role in ("multi-pi", "co-pi", "multi-pi/co-pi"):
        return ROLE_WEIGHT_MULTI_PI
    if role in ("co-i", "co-investigator"):
        return ROLE_WEIGHT_CO_I
    return ROLE_WEIGHT_CO_I


def _grant_type_weight(activity_code: str) -> float:
    """Map activity code to grant type weight."""
    code = activity_code.strip().upper()
    if code.startswith(("R01", "U01", "P01")):
        return _GRANT_TYPE_WEIGHT_HIGH
    if code.startswith("K"):
        return _GRANT_TYPE_WEIGHT_K
    if code.startswith(("R03", "R21")):
        return _GRANT_TYPE_WEIGHT_SMALL
    return _GRANT_TYPE_WEIGHT_OTHER


def _is_r01_equivalent(activity_code: str) -> bool:
    """Check if activity code is R01-equivalent."""
    code = activity_code.strip().upper()
    return any(code.startswith(c) for c in _R01_EQUIVALENT_CODES)


@dataclass
class GrantInput:
    """Input grant record for F2 scoring."""

    project_number: str
    activity_code: str
    pi_role: str
    total_cost: int | None
    is_active: bool
    pi_count: int


class F2Computer:
    """Compute F2 sub-score (NIH funding) for candidates."""

    def score_raw(
        self,
        grants: list[GrantInput],
    ) -> tuple[float, float, int]:
        """Compute raw F2 values (before percentile).

        Returns (total_cost_log, active_r01_equivalent, grant_count).
        """
        if not grants:
            return (0.0, 0.0, 0)

        weighted_cost: float = 0.0
        active_r01_equiv: float = 0.0

        for g in grants:
            rw = _role_weight(g.pi_role)
            gw = _grant_type_weight(g.activity_code)
            active_mult = ACTIVE_MULTIPLIER if g.is_active else 1.0
            fractional = 1.0 / max(g.pi_count, 1)

            # Weighted cost contribution
            cost = float(g.total_cost) if g.total_cost else 0.0
            weighted_cost += cost * rw * gw * active_mult * fractional

            # Active R01-equivalent counting
            if _is_r01_equivalent(g.activity_code) and g.is_active:
                active_r01_equiv += fractional * rw

        total_cost_log = math.log(weighted_cost + 1.0)

        return (total_cost_log, active_r01_equiv, len(grants))

    def compute_percentiles(
        self,
        raw_scores: list[tuple[str, float, float, int]],
    ) -> dict[str, F2Score]:
        """Compute percentile rank for each candidate.

        Takes list of (uuid, total_cost_log, active_r01_equiv, grant_count).
        Percentile based on composite: 0.7 * total_cost_log_norm + 0.3 * r01_equiv.
        """
        if not raw_scores:
            return {}

        # Composite for ranking
        composites: list[
            tuple[str, float, float, float, int]
        ] = []
        for uuid, cost_log, r01_eq, count in raw_scores:
            composite = 0.7 * cost_log + 0.3 * r01_eq
            composites.append(
                (uuid, cost_log, r01_eq, composite, count)
            )

        composites.sort(key=lambda x: x[3])

        n = len(composites)
        results: dict[str, F2Score] = {}
        for rank_idx, (
            uuid,
            cost_log,
            r01_eq,
            _comp,
            count,
        ) in enumerate(composites):
            percentile = (rank_idx + 0.5) / n
            results[uuid] = F2Score(
                total_cost_log=round(cost_log, 6),
                active_r01_equivalent=round(r01_eq, 6),
                percentile=round(percentile, 6),
                grant_count=count,
            )

        return results
