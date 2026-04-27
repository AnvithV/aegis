"""Tests for F2 sub-score: NIH funding and resource-getting."""

from __future__ import annotations

import math

from aegis.scoring.f2_funding import (
    ACTIVE_MULTIPLIER,
    ROLE_WEIGHT_CONTACT_PI,
    ROLE_WEIGHT_MULTI_PI,
    F2Computer,
    GrantInput,
)


def _grant(
    project: str = "5R01CA123456-03",
    activity: str = "R01",
    role: str = "Contact PI",
    cost: int | None = 500_000,
    active: bool = True,
    pi_count: int = 1,
) -> GrantInput:
    return GrantInput(
        project_number=project,
        activity_code=activity,
        pi_role=role,
        total_cost=cost,
        is_active=active,
        pi_count=pi_count,
    )


def test_score_raw_basic() -> None:
    """5 grants with mixed types and roles compute correctly."""
    computer = F2Computer()
    grants = [
        _grant(activity="R01", role="Contact PI", cost=1_000_000),
        _grant(activity="K08", role="Contact PI", cost=200_000),
        _grant(activity="R21", role="Co-I", cost=100_000),
        _grant(activity="U01", role="Multi-PI", cost=800_000, pi_count=2),
        _grant(
            activity="R03",
            role="Contact PI",
            cost=50_000,
            active=False,
        ),
    ]

    cost_log, r01_equiv, count = computer.score_raw(grants)

    assert count == 5
    assert cost_log > 0.0
    assert r01_equiv > 0.0  # R01 + U01 are active R01-equivalents


def test_score_raw_active_vs_expired() -> None:
    """Active R01 counts toward active_r01_equivalent, expired does not."""
    computer = F2Computer()
    active_grant = _grant(activity="R01", active=True, cost=500_000)
    expired_grant = _grant(activity="R01", active=False, cost=500_000)

    _, r01_active, _ = computer.score_raw([active_grant])
    _, r01_expired, _ = computer.score_raw([expired_grant])

    assert r01_active == ROLE_WEIGHT_CONTACT_PI  # 1.0
    assert r01_expired == 0.0  # expired does not count


def test_score_raw_multi_pi_fractional() -> None:
    """Multi-PI grant counted fractionally."""
    computer = F2Computer()
    grant = _grant(
        activity="R01",
        role="Multi-PI",
        cost=900_000,
        pi_count=3,
        active=True,
    )

    cost_log, r01_equiv, count = computer.score_raw([grant])

    assert count == 1
    # R01-equiv: fractional(1/3) * role_weight(0.7)
    expected_r01 = (1.0 / 3) * ROLE_WEIGHT_MULTI_PI
    assert abs(r01_equiv - expected_r01) < 1e-9

    # Cost: 900_000 * role(0.7) * type(1.0) * active(2.0) * frac(1/3)
    expected_cost = 900_000 * 0.7 * 1.0 * ACTIVE_MULTIPLIER * (1.0 / 3)
    assert abs(cost_log - math.log(expected_cost + 1.0)) < 1e-9


def test_score_raw_no_grants() -> None:
    """No grants returns zeros."""
    computer = F2Computer()
    cost_log, r01_equiv, count = computer.score_raw([])

    assert cost_log == 0.0
    assert r01_equiv == 0.0
    assert count == 0


def test_compute_percentiles_distribution() -> None:
    """50 candidates with increasing costs have uniform percentiles."""
    computer = F2Computer()
    raw_scores: list[tuple[str, float, float, int]] = [
        (f"C{i}", float(i), float(i) * 0.1, 5)
        for i in range(50)
    ]

    results = computer.compute_percentiles(raw_scores)

    assert len(results) == 50
    pcts = [results[f"C{i}"].percentile for i in range(50)]

    # Lowest should have low percentile
    assert pcts[0] < 0.03
    # Highest should have high percentile
    assert pcts[49] > 0.97
    # Monotonically increasing
    for i in range(1, len(pcts)):
        assert pcts[i] > pcts[i - 1]


def test_fractional_pi_shares_sum_to_one() -> None:
    """3 PIs on one grant, each gets 1/3 share."""
    computer = F2Computer()

    # Three Contact PIs on same grant
    shares = []
    for _ in range(3):
        grant = _grant(
            activity="R01",
            role="Contact PI",
            cost=900_000,
            pi_count=3,
            active=True,
        )
        _, r01_eq, _ = computer.score_raw([grant])
        shares.append(r01_eq)

    # Each PI gets 1/3 * 1.0 (contact PI weight)
    for s in shares:
        assert abs(s - 1.0 / 3) < 1e-9

    # Sum of shares = 1.0
    assert abs(sum(shares) - 1.0) < 1e-9
