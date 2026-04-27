"""Tests for F7 clinician-specific score module."""

from __future__ import annotations

import random
import uuid as uuid_mod

import pytest

from aegis.scoring.f7_clinician import (
    ClinicianInput,
    F7Computer,
    _W_BOARD_CERT,
    _W_HOSPITAL_TIER,
    _W_LICENSE,
    _W_PROCEDURE_VOLUME,
    _W_TRIAL_PI,
)


def _make_input(**overrides: object) -> ClinicianInput:
    """Create a ClinicianInput with sensible defaults, overriding as needed."""
    defaults: dict[str, object] = {
        "is_board_certified": True,
        "has_moc": True,
        "certification_count": 1,
        "has_active_license": True,
        "has_disciplinary_action": False,
        "action_severity": None,
        "hospital_tier": 1,
        "specialty_rank": None,
        "trial_pi_count": 0,
        "trial_phases": [],
        "total_procedures": 0,
        "procedure_volume_available": False,
    }
    defaults.update(overrides)
    return ClinicianInput(**defaults)  # type: ignore[arg-type]


class TestBoardCertification:
    def test_board_certified_with_moc(self) -> None:
        computer = F7Computer()
        inp = _make_input(is_board_certified=True, has_moc=True, certification_count=1)
        board_cert, *_ = computer.score_raw(inp)
        assert board_cert == 1.0

    def test_board_certified_no_moc(self) -> None:
        computer = F7Computer()
        inp = _make_input(is_board_certified=True, has_moc=False, certification_count=1)
        board_cert, *_ = computer.score_raw(inp)
        assert board_cert == 0.7

    def test_not_board_certified(self) -> None:
        computer = F7Computer()
        inp = _make_input(is_board_certified=False, has_moc=False, certification_count=0)
        board_cert, *_ = computer.score_raw(inp)
        assert board_cert == 0.0

    def test_multiple_certifications(self) -> None:
        computer = F7Computer()
        inp = _make_input(
            is_board_certified=True, has_moc=False, certification_count=3,
        )
        board_cert, *_ = computer.score_raw(inp)
        # 0.7 base + 0.1 * 2 = 0.9
        assert board_cert == pytest.approx(0.9)


class TestLicense:
    def test_active_license_clean(self) -> None:
        computer = F7Computer()
        inp = _make_input(has_active_license=True, has_disciplinary_action=False)
        _, license_score, *_ = computer.score_raw(inp)
        assert license_score == 1.0

    def test_license_with_suspension(self) -> None:
        computer = F7Computer()
        inp = _make_input(
            has_active_license=True,
            has_disciplinary_action=True,
            action_severity="suspension",
        )
        _, license_score, *_ = computer.score_raw(inp)
        assert license_score == 0.1

    def test_license_with_probation(self) -> None:
        computer = F7Computer()
        inp = _make_input(
            has_active_license=True,
            has_disciplinary_action=True,
            action_severity="probation",
        )
        _, license_score, *_ = computer.score_raw(inp)
        assert license_score == 0.5


class TestHospitalTier:
    def test_hospital_tier_1(self) -> None:
        computer = F7Computer()
        inp = _make_input(hospital_tier=1)
        _, _, hospital_tier, *_ = computer.score_raw(inp)
        assert hospital_tier == 1.0

    def test_hospital_tier_unranked(self) -> None:
        computer = F7Computer()
        inp = _make_input(hospital_tier=0)
        _, _, hospital_tier, *_ = computer.score_raw(inp)
        assert hospital_tier == 0.2

    def test_specialty_rank_override(self) -> None:
        computer = F7Computer()
        inp = _make_input(hospital_tier=3, specialty_rank=3)
        _, _, hospital_tier, *_ = computer.score_raw(inp)
        # specialty_rank <= 5 overrides to >= 0.9
        assert hospital_tier >= 0.9


class TestTrialPI:
    def test_trial_pi_with_phase3(self) -> None:
        computer = F7Computer()
        inp = _make_input(trial_pi_count=2, trial_phases=[2, 3])
        _, _, _, trial_pi, *_ = computer.score_raw(inp)
        # 2/5 = 0.4, + 0.2 bonus = 0.6
        assert trial_pi == pytest.approx(0.6)


class TestProcedureVolume:
    def test_procedure_volume_available(self) -> None:
        computer = F7Computer()
        inp = _make_input(
            total_procedures=250, procedure_volume_available=True,
        )
        _, _, _, _, proc_vol, vol_conf, caveat = computer.score_raw(inp)
        assert proc_vol == 250.0 / 500.0
        assert vol_conf == 1.0
        assert caveat is None

    def test_procedure_volume_missing(self) -> None:
        computer = F7Computer()
        inp = _make_input(procedure_volume_available=False)
        _, _, _, _, proc_vol, vol_conf, caveat = computer.score_raw(inp)
        assert proc_vol == 0.0
        assert vol_conf == 0.3
        assert caveat is not None
        assert "unavailable" in caveat


class TestPercentile:
    def test_percentile_uniform(self) -> None:
        """100 synthetic clinicians should have approximately uniform percentile distribution."""
        computer = F7Computer()
        rng = random.Random(42)

        raw_scores: list[tuple[str, float, float, float, float, float, float, str | None]] = []
        for _ in range(100):
            uid = str(uuid_mod.uuid4())
            inp = _make_input(
                is_board_certified=rng.choice([True, False]),
                has_moc=rng.choice([True, False]),
                certification_count=rng.randint(0, 3),
                has_active_license=True,
                has_disciplinary_action=False,
                hospital_tier=rng.choice([0, 1, 2, 3]),
                trial_pi_count=rng.randint(0, 5),
                trial_phases=[rng.randint(1, 4) for _ in range(rng.randint(0, 3))],
                total_procedures=rng.randint(0, 600),
                procedure_volume_available=rng.choice([True, False]),
            )
            scores = computer.score_raw(inp)
            raw_scores.append((uid, *scores))

        results = computer.compute_percentiles(raw_scores)
        assert len(results) == 100

        percentiles = sorted(r.percentile for r in results.values())
        # First percentile should be near 0, last near 1
        assert percentiles[0] < 0.1
        assert percentiles[-1] > 0.9
        # Median should be near 0.5
        median = percentiles[50]
        assert 0.3 < median < 0.7


class TestCompositeWeights:
    def test_composite_weights_sum(self) -> None:
        total = _W_BOARD_CERT + _W_LICENSE + _W_HOSPITAL_TIER + _W_TRIAL_PI + _W_PROCEDURE_VOLUME
        assert abs(total - 1.0) < 0.001
