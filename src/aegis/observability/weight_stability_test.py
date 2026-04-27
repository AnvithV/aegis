"""Tests for weight-stability tracking."""

from __future__ import annotations

from pathlib import Path

from aegis.observability.weight_stability import (
    StabilityReport,
    WeightShift,
    WeightStabilityTracker,
)
from aegis.scoring.quality_prior import WeightVector


def _make_vector(
    version: int,
    weights: dict[str, float],
    exponents: dict[str, float],
) -> WeightVector:
    return WeightVector(
        version=version,
        specialty="translational",
        weights=weights,
        exponents=exponents,
        exponent_bounds={},
    )


def test_no_shift() -> None:
    """Identical weights produce no threshold violations."""
    tracker = WeightStabilityTracker()
    shift = tracker.compare_weights("weight.f1_rcr", 0.35, 0.35)
    assert isinstance(shift, WeightShift)
    assert shift.absolute_change == 0.0
    assert shift.relative_change_pct == 0.0
    assert shift.exceeds_threshold is False


def test_small_shift() -> None:
    """Small shift stays within threshold."""
    tracker = WeightStabilityTracker(shift_threshold_pct=25.0)
    # 0.35 -> 0.38, relative = 8.57%
    shift = tracker.compare_weights("weight.f1_rcr", 0.35, 0.38)
    assert shift.exceeds_threshold is False
    assert shift.relative_change_pct < 25.0


def test_large_shift_triggers_review() -> None:
    """Large shift exceeds threshold and requires review."""
    tracker = WeightStabilityTracker(shift_threshold_pct=25.0)
    # 0.35 -> 0.10, relative = 71.4%
    shift = tracker.compare_weights("weight.f1_rcr", 0.35, 0.10)
    assert shift.exceeds_threshold is True
    assert shift.relative_change_pct > 25.0


def test_zero_old_value() -> None:
    """Zero old value with significant change flags threshold."""
    tracker = WeightStabilityTracker()
    shift = tracker.compare_weights("weight.new_param", 0.0, 0.05)
    assert shift.exceeds_threshold is True
    assert shift.relative_change_pct == 100.0

    # Zero to near-zero should not flag
    shift2 = tracker.compare_weights(
        "weight.tiny", 0.0, 0.005
    )
    assert shift2.exceeds_threshold is False
    assert shift2.relative_change_pct == 0.0


def test_compare_vectors() -> None:
    """compare_vectors checks all weights and exponents."""
    tracker = WeightStabilityTracker(shift_threshold_pct=25.0)
    old = _make_vector(
        1,
        {"f1_rcr": 0.35, "f2_funding": 0.25},
        {"alpha": 0.7, "beta": 1.0},
    )
    new = _make_vector(
        2,
        {"f1_rcr": 0.35, "f2_funding": 0.10},
        {"alpha": 0.7, "beta": 1.0},
    )
    shifts = tracker.compare_vectors(old, new)
    # 2 weight params + 2 exponent params = 4 shifts
    assert len(shifts) == 4
    fund_shift = [
        s for s in shifts if s.parameter == "weight.f2_funding"
    ][0]
    assert fund_shift.exceeds_threshold is True


def test_review_template_generation() -> None:
    """Review template contains expected Markdown elements."""
    tracker = WeightStabilityTracker()
    old = _make_vector(
        1, {"f1_rcr": 0.35}, {"alpha": 0.7}
    )
    new = _make_vector(
        2, {"f1_rcr": 0.10}, {"alpha": 0.7}
    )
    shifts = tracker.compare_vectors(old, new)
    report = StabilityReport(
        old_version=1,
        new_version=2,
        shifts=shifts,
        requires_review=True,
        auto_deploy_ok=False,
        summary="Review required",
    )
    md = tracker.generate_review_template(report)
    assert "Weight Change Review" in md
    assert "v1 -> v2" in md
    assert "REQUIRES REVIEW" in md
    assert "f1_rcr" in md
    assert "EXCEEDS" in md


def test_check_latest_stability(tmp_path: Path) -> None:
    """check_latest_stability compares two YAML versions."""
    tracker = WeightStabilityTracker(shift_threshold_pct=25.0)

    v1_content = """\
version: 1
specialty: translational
created: "2026-04-25"
weights:
  f1_rcr: 0.35
  f2_funding: 0.25
  f3_leadership: 0.20
  f4_apex: 0.05
  f5_translational: 0.10
  f6_lineage: 0.05
exponents:
  alpha: 0.7
  beta: 1.0
  gamma: 0.4
exponent_bounds:
  alpha: [0.3, 1.2]
  beta: [0.5, 1.5]
  gamma: [0.1, 0.8]
"""

    v2_content = """\
version: 2
specialty: translational
created: "2026-04-26"
weights:
  f1_rcr: 0.30
  f2_funding: 0.25
  f3_leadership: 0.20
  f4_apex: 0.10
  f5_translational: 0.10
  f6_lineage: 0.05
exponents:
  alpha: 0.7
  beta: 1.0
  gamma: 0.4
exponent_bounds:
  alpha: [0.3, 1.2]
  beta: [0.5, 1.5]
  gamma: [0.1, 0.8]
"""

    (tmp_path / "translational_v1.yaml").write_text(v1_content)
    (tmp_path / "translational_v2.yaml").write_text(v2_content)

    report = tracker.check_latest_stability(str(tmp_path))
    assert report is not None
    assert isinstance(report, StabilityReport)
    assert report.old_version == 1
    assert report.new_version == 2

    # f4_apex changed 0.05 -> 0.10 (100% change) -> review
    assert report.requires_review is True
    assert report.auto_deploy_ok is False
    apex_shift = [
        s for s in report.shifts
        if s.parameter == "weight.f4_apex"
    ][0]
    assert apex_shift.exceeds_threshold is True
