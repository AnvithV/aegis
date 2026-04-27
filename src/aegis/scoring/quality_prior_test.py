"""Tests for quality prior Q(c) composition and percentile calibration."""

from __future__ import annotations

import math
from pathlib import Path

from aegis.scoring.quality_prior import (
    QualityPrior,
    QualityScore,
    WeightVector,
    load_weight_vector,
)

_YAML_PATH = Path("config/aegis/weights/translational_v1.yaml")

_SIMPLE_WEIGHTS = WeightVector(
    version=1,
    specialty="test",
    weights={"f1_rcr": 0.5, "f2_funding": 0.5},
    exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
    exponent_bounds={},
)

_FULL_WEIGHTS = WeightVector(
    version=1,
    specialty="translational",
    weights={
        "f1_rcr": 0.35,
        "f2_funding": 0.25,
        "f3_leadership": 0.20,
        "f4_apex": 0.05,
        "f5_translational": 0.10,
        "f6_lineage": 0.05,
    },
    exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
    exponent_bounds={},
)


def test_load_weight_vector() -> None:
    """Load from YAML, verify weights sum to 1.0."""
    wv = load_weight_vector(_YAML_PATH)

    assert wv.version == 1
    assert wv.specialty == "translational"
    assert abs(sum(wv.weights.values()) - 1.0) < 0.001
    assert "f1_rcr" in wv.weights
    assert "alpha" in wv.exponents


def test_compute_raw_basic() -> None:
    """Known component percentiles produce expected Q(c) value."""
    qp = QualityPrior(_SIMPLE_WEIGHTS)
    components = {"f1_rcr": 0.8, "f2_funding": 0.6}

    raw = qp.compute_raw(components)

    # Q(c) = 0.8^0.5 * 0.6^0.5 = sqrt(0.48)
    expected = math.exp(0.5 * math.log(0.8) + 0.5 * math.log(0.6))
    assert abs(raw - expected) < 1e-9


def test_compute_raw_all_ones() -> None:
    """All percentiles = 1.0 gives Q(c) = 1.0."""
    qp = QualityPrior(_FULL_WEIGHTS)
    components = {k: 1.0 for k in _FULL_WEIGHTS.weights}

    raw = qp.compute_raw(components)

    assert abs(raw - 1.0) < 1e-9


def test_compute_raw_all_zeros() -> None:
    """All percentiles near 0 gives Q(c) near 0."""
    qp = QualityPrior(_FULL_WEIGHTS)
    components = {k: 0.0 for k in _FULL_WEIGHTS.weights}

    raw = qp.compute_raw(components)

    # With clamping at 1e-6, should be very small
    assert raw < 1e-5


def test_percentile_distribution_uniform() -> None:
    """100 candidates with linearly spaced components produce
    approximately uniform Q(c) percentiles."""
    qp = QualityPrior(_SIMPLE_WEIGHTS)

    candidates: list[tuple[str, dict[str, float]]] = []
    for i in range(100):
        val = (i + 1) / 101  # avoid exact 0 or 1
        candidates.append(
            (f"C{i}", {"f1_rcr": val, "f2_funding": val})
        )

    results = qp.compute_percentiles(candidates)

    assert len(results) == 100
    pcts = sorted(results[f"C{i}"].percentile for i in range(100))

    # Should span approximately [0, 1]
    assert pcts[0] < 0.02
    assert pcts[-1] > 0.98
    # Monotonically increasing
    for i in range(1, len(pcts)):
        assert pcts[i] > pcts[i - 1]


def test_reweight_invariance() -> None:
    """Scaling all weights by a constant preserves percentile ordering."""
    base_wv = _SIMPLE_WEIGHTS

    candidates: list[tuple[str, dict[str, float]]] = [
        ("A", {"f1_rcr": 0.9, "f2_funding": 0.3}),
        ("B", {"f1_rcr": 0.5, "f2_funding": 0.5}),
        ("C", {"f1_rcr": 0.2, "f2_funding": 0.8}),
    ]

    qp_base = QualityPrior(base_wv)
    base_results = qp_base.compute_percentiles(candidates)
    base_order = sorted(
        base_results, key=lambda k: base_results[k].percentile
    )

    for scale in (0.5, 2.0):
        scaled_wv = WeightVector(
            version=base_wv.version,
            specialty=base_wv.specialty,
            weights={
                k: v * scale for k, v in base_wv.weights.items()
            },
            exponents=base_wv.exponents,
            exponent_bounds={},
        )
        qp_scaled = QualityPrior(scaled_wv)
        scaled_results = qp_scaled.compute_percentiles(candidates)
        scaled_order = sorted(
            scaled_results,
            key=lambda k: scaled_results[k].percentile,
        )
        assert base_order == scaled_order


def test_geometric_mean_punishes_spiky() -> None:
    """A balanced candidate scores higher than a spiky one."""
    qp = QualityPrior(_SIMPLE_WEIGHTS)

    # Balanced: both at 0.5 -> geometric mean = 0.5
    balanced = qp.compute_raw({"f1_rcr": 0.5, "f2_funding": 0.5})

    # Spiky: one high, one low -> geometric mean < arithmetic mean
    spiky = qp.compute_raw({"f1_rcr": 0.9, "f2_funding": 0.1})

    # Geometric mean penalizes imbalance:
    # balanced = sqrt(0.5 * 0.5) = 0.5
    # spiky = sqrt(0.9 * 0.1) = sqrt(0.09) ~ 0.3
    assert balanced > spiky


def test_weight_version_propagated() -> None:
    """QualityScore.weight_version matches the loaded config version."""
    wv = WeightVector(
        version=42,
        specialty="test",
        weights={"f1_rcr": 1.0},
        exponents={"alpha": 0.7},
        exponent_bounds={},
    )
    qp = QualityPrior(wv)

    results = qp.compute_percentiles(
        [("X", {"f1_rcr": 0.5})]
    )

    assert isinstance(results["X"], QualityScore)
    assert results["X"].weight_version == 42
