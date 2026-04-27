"""Tests for F5 translational impact sub-score."""

from __future__ import annotations

from aegis.scoring.f5_translational import F5Computer, TranslationalInput


def test_score_raw_full_profile() -> None:
    computer = F5Computer()
    inp = TranslationalInput(
        fda_submission_count=2,
        phase2plus_trial_count=3,
        is_nccn_panel_member=True,
    )
    composite, fda, phase2, nccn, caveat = computer.score_raw(inp)

    # fda: min(2/3, 1) = 0.6667; trial: min(3/5, 1) = 0.6; nccn: 1.0
    # composite = 0.35*0.6667 + 0.40*0.6 + 0.25*1.0 = 0.2333 + 0.24 + 0.25 = 0.7233
    assert 0.72 < composite < 0.73
    assert fda == 2
    assert phase2 == 3
    assert nccn is True
    assert caveat != ""


def test_score_raw_nccn_only() -> None:
    computer = F5Computer()
    inp = TranslationalInput(
        fda_submission_count=0,
        phase2plus_trial_count=0,
        is_nccn_panel_member=True,
    )
    composite, fda, phase2, nccn, _ = computer.score_raw(inp)

    # Only NCCN component: 0.25 * 1.0 = 0.25
    assert abs(composite - 0.25) < 1e-9
    assert fda == 0
    assert phase2 == 0
    assert nccn is True


def test_score_raw_no_signals() -> None:
    computer = F5Computer()
    inp = TranslationalInput(
        fda_submission_count=0,
        phase2plus_trial_count=0,
        is_nccn_panel_member=False,
    )
    composite, _, _, _, _ = computer.score_raw(inp)
    assert composite == 0.0


def test_coverage_caveat_always_present() -> None:
    computer = F5Computer()
    for fda in (0, 2):
        for trials in (0, 3):
            for nccn in (True, False):
                inp = TranslationalInput(fda, trials, nccn)
                _, _, _, _, caveat = computer.score_raw(inp)
                assert "Phase 1" in caveat
                assert "patents excluded" in caveat


def test_compute_percentiles() -> None:
    computer = F5Computer()
    raw_scores: list[tuple[str, float, int, int, bool, str]] = []
    for i in range(25):
        inp = TranslationalInput(
            fda_submission_count=i % 4,
            phase2plus_trial_count=i % 6,
            is_nccn_panel_member=i % 3 == 0,
        )
        composite, fda, phase2, nccn, caveat = computer.score_raw(inp)
        raw_scores.append((f"cand-{i}", composite, fda, phase2, nccn, caveat))

    results = computer.compute_percentiles(raw_scores)
    assert len(results) == 25

    percentiles = [s.percentile for s in results.values()]
    assert min(percentiles) >= 0.0
    assert max(percentiles) <= 1.0

    # Should be evenly spaced midpoints
    assert abs(min(percentiles) - 0.02) < 0.01
    assert abs(max(percentiles) - 0.98) < 0.01


def test_component_capping() -> None:
    computer = F5Computer()
    # FDA > 3 should still cap at 1.0
    inp = TranslationalInput(
        fda_submission_count=10,
        phase2plus_trial_count=0,
        is_nccn_panel_member=False,
    )
    composite, _, _, _, _ = computer.score_raw(inp)

    # fda capped at 1.0: 0.35 * 1.0 = 0.35
    assert abs(composite - 0.35) < 1e-9

    # Trials > 5 should also cap
    inp2 = TranslationalInput(
        fda_submission_count=0,
        phase2plus_trial_count=20,
        is_nccn_panel_member=False,
    )
    composite2, _, _, _, _ = computer.score_raw(inp2)
    assert abs(composite2 - 0.40) < 1e-9
