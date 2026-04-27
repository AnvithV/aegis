"""Tests for F6 mentorship lineage sub-score."""

from __future__ import annotations

from aegis.scoring.f6_lineage import F6Computer, LineageInput


def test_score_raw_prolific_mentor() -> None:
    computer = F6Computer()
    inp = LineageInput(
        traceable_trainee_count=8,
        r01_trainee_count=4,
        aft_link_confidence=0.95,
    )
    composite, trainees, r01s, confidence = computer.score_raw(inp)

    # trainee: min(8/10, 1) = 0.8; r01: min(4/5, 1) = 0.8
    # raw = 0.4*0.8 + 0.6*0.8 = 0.32 + 0.48 = 0.80
    # composite = 0.80 * 0.95 = 0.76
    assert 0.759 < composite < 0.761
    assert trainees == 8
    assert r01s == 4
    assert confidence == 0.95


def test_score_raw_no_data() -> None:
    computer = F6Computer()
    inp = LineageInput(
        traceable_trainee_count=0,
        r01_trainee_count=0,
        aft_link_confidence=0.1,
    )
    composite, trainees, r01s, confidence = computer.score_raw(inp)

    assert composite == 0.0
    assert trainees == 0
    assert r01s == 0
    assert confidence == 0.1


def test_score_raw_low_confidence_downweights() -> None:
    computer = F6Computer()

    inp_high = LineageInput(
        traceable_trainee_count=5,
        r01_trainee_count=3,
        aft_link_confidence=0.9,
    )
    composite_high, _, _, _ = computer.score_raw(inp_high)

    inp_low = LineageInput(
        traceable_trainee_count=5,
        r01_trainee_count=3,
        aft_link_confidence=0.3,
    )
    composite_low, _, _, _ = computer.score_raw(inp_low)

    # Same trainee data but lower confidence should give lower composite
    assert composite_low < composite_high
    # Ratio should be proportional to confidence ratio
    assert abs(composite_low / composite_high - 0.3 / 0.9) < 1e-9


def test_compute_percentiles_long_tail() -> None:
    computer = F6Computer()
    raw_scores: list[tuple[str, float, int, int, float]] = []

    # Most candidates have 0-2 trainees (long-tail distribution)
    for i in range(30):
        if i < 20:
            trainees = i % 3  # 0, 1, or 2
            r01s = 0
        elif i < 27:
            trainees = 3 + i % 4
            r01s = 1
        else:
            trainees = 8 + i % 3
            r01s = 3 + i % 3

        inp = LineageInput(trainees, r01s, aft_link_confidence=0.8)
        composite, t_count, r_count, confidence = computer.score_raw(inp)
        raw_scores.append((f"cand-{i}", composite, t_count, r_count, confidence))

    results = computer.compute_percentiles(raw_scores)
    assert len(results) == 30

    percentiles = [s.percentile for s in results.values()]
    assert min(percentiles) >= 0.0
    assert max(percentiles) <= 1.0


def test_r01_component_capping() -> None:
    computer = F6Computer()
    inp = LineageInput(
        traceable_trainee_count=0,
        r01_trainee_count=10,
        aft_link_confidence=1.0,
    )
    composite, _, _, _ = computer.score_raw(inp)

    # r01 capped at 1.0: raw = 0.6 * 1.0 = 0.6; composite = 0.6 * 1.0 = 0.6
    assert abs(composite - 0.6) < 1e-9
