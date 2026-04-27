"""Tests for F3 leadership sub-score."""

from __future__ import annotations

import math

from aegis.scoring.f3_leadership import F3Computer, LeadershipInput


def test_score_raw_established_pi() -> None:
    computer = F3Computer()
    inp = LeadershipInput(
        total_papers=100,
        last_author_papers=60,
        corresponding_author_papers=55,
        trial_pi_roles=4,
        trial_chair_roles=2,
        has_editorial_role=True,
    )
    lar, tpi, car, erf = computer.score_raw(inp)
    assert math.isclose(lar, 0.6)
    assert math.isclose(tpi, 4 * 1.0 + 2 * 0.7)  # 5.4
    assert math.isclose(car, 0.55)
    assert erf is True


def test_score_raw_early_career() -> None:
    computer = F3Computer()
    inp = LeadershipInput(
        total_papers=15,
        last_author_papers=2,
        corresponding_author_papers=3,
        trial_pi_roles=0,
        trial_chair_roles=0,
        has_editorial_role=False,
    )
    lar, tpi, car, erf = computer.score_raw(inp)
    assert math.isclose(lar, 2 / 15)
    assert math.isclose(tpi, 0.0)
    assert math.isclose(car, 3 / 15)
    assert erf is False


def test_score_raw_study_chair_weighted() -> None:
    computer = F3Computer()
    inp = LeadershipInput(
        total_papers=50,
        last_author_papers=20,
        corresponding_author_papers=18,
        trial_pi_roles=0,
        trial_chair_roles=3,
        has_editorial_role=False,
    )
    _, tpi, _, _ = computer.score_raw(inp)
    assert math.isclose(tpi, 3 * 0.7)  # 2.1


def test_score_raw_no_papers() -> None:
    computer = F3Computer()
    inp = LeadershipInput(
        total_papers=0,
        last_author_papers=0,
        corresponding_author_papers=0,
        trial_pi_roles=0,
        trial_chair_roles=0,
        has_editorial_role=False,
    )
    lar, tpi, car, erf = computer.score_raw(inp)
    assert lar == 0.0
    assert tpi == 0.0
    assert car == 0.0
    assert erf is False


def test_editorial_role_flag() -> None:
    computer = F3Computer()
    inp_with = LeadershipInput(
        total_papers=50,
        last_author_papers=20,
        corresponding_author_papers=15,
        trial_pi_roles=1,
        trial_chair_roles=0,
        has_editorial_role=True,
    )
    _, _, _, erf = computer.score_raw(inp_with)
    assert erf is True

    inp_without = LeadershipInput(
        total_papers=50,
        last_author_papers=20,
        corresponding_author_papers=15,
        trial_pi_roles=1,
        trial_chair_roles=0,
        has_editorial_role=False,
    )
    _, _, _, erf = computer.score_raw(inp_without)
    assert erf is False


def test_compute_percentiles() -> None:
    computer = F3Computer()

    # Generate 30 candidates with varying leadership profiles
    raw_scores: list[tuple[str, float, float, float, bool]] = []
    for i in range(30):
        lar = i / 30  # increasing last-author rate
        tpi = float(i % 6)  # 0-5 trial PI count
        car = (30 - i) / 60  # decreasing corresponding-author rate
        erf = i >= 25  # top 5 have editorial roles
        raw_scores.append((f"candidate_{i}", lar, tpi, car, erf))

    result = computer.compute_percentiles(raw_scores)

    assert len(result) == 30

    # All percentiles in [0, 1]
    for score in result.values():
        assert 0.0 <= score.percentile <= 1.0

    # Exactly one candidate at percentile 0.0 and one at 1.0
    percentiles = [s.percentile for s in result.values()]
    assert min(percentiles) == 0.0
    assert max(percentiles) == 1.0

    # Verify that raw values are preserved
    c0 = result["candidate_0"]
    assert math.isclose(c0.last_author_rate, 0.0)
    assert math.isclose(c0.trial_pi_count, 0.0)
    assert c0.editorial_role_flag is False
