"""Tests for F4 apex-tier sub-score."""

from __future__ import annotations

import math

from aegis.scoring.f4_apex import F4Computer


def test_score_zero_memberships() -> None:
    computer = F4Computer()
    score, count = computer.score_from_memberships([])
    assert score == 0.0
    assert count == 0


def test_score_one_membership() -> None:
    computer = F4Computer()
    score, count = computer.score_from_memberships(["hhmi_investigator"])
    assert math.isclose(score, 0.4)
    assert count == 1


def test_score_multiple_memberships() -> None:
    computer = F4Computer()
    score, count = computer.score_from_memberships(
        ["hhmi_investigator", "nas_member", "lasker_laureate"]
    )
    assert math.isclose(score, 0.8)
    assert count == 3


def test_score_cap_at_one() -> None:
    computer = F4Computer()
    memberships = [
        "hhmi_investigator",
        "nas_member",
        "nae_member",
        "nam_member",
        "nih_merit",
        "lasker_laureate",
        "hhmi_hanna_gray",
    ]
    score, count = computer.score_from_memberships(memberships)
    assert score <= 1.0
    assert count == 7


def test_monotonic() -> None:
    computer = F4Computer()
    prev_score = -1.0
    for i in range(8):
        memberships = [f"roster_{j}" for j in range(i)]
        score, _ = computer.score_from_memberships(memberships)
        assert score >= prev_score, (
            f"Score decreased: {prev_score} -> {score} at count {i}"
        )
        prev_score = score


def test_compute_percentiles() -> None:
    computer = F4Computer()

    # 20 candidates with varying membership counts
    raw_scores: list[tuple[str, float, int]] = []
    for i in range(20):
        count = i % 5
        memberships = [f"roster_{j}" for j in range(count)]
        score, _ = computer.score_from_memberships(memberships)
        raw_scores.append((f"candidate_{i}", score, count))

    result = computer.compute_percentiles(raw_scores)

    assert len(result) == 20

    # All percentiles in [0, 1]
    for f4 in result.values():
        assert 0.0 <= f4.percentile <= 1.0

    # Verify raw scores preserved
    c0 = result["candidate_0"]
    assert c0.score == 0.0
    assert c0.membership_count == 0

    c1 = result["candidate_1"]
    assert math.isclose(c1.score, 0.4)
    assert c1.membership_count == 1
