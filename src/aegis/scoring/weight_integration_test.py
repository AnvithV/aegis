"""Integration tests for all weight vectors with QualityPrior."""

from __future__ import annotations

from aegis.scoring.clinician_weights import load_clinician_weights
from aegis.scoring.drug_discovery_weights import load_drug_discovery_weights
from aegis.scoring.quality_prior import QualityPrior, load_weight_vector


def test_translational_weights_load() -> None:
    """Translational v1 weights load and sum to 1.0."""
    wv = load_weight_vector()
    assert abs(sum(wv.weights.values()) - 1.0) < 0.001
    assert wv.specialty == "translational"
    assert len(wv.weights) == 6


def test_drug_discovery_weights_load() -> None:
    """Drug-discovery v1 weights load and sum to 1.0."""
    wv = load_drug_discovery_weights()
    assert abs(sum(wv.weights.values()) - 1.0) < 0.001
    assert wv.specialty == "drug_discovery"
    assert len(wv.weights) == 6
    assert wv.weights["f5_translational"] == 0.50


def test_clinician_weights_load() -> None:
    """Clinician v1 weights load, include F7, and sum to 1.0."""
    wv = load_clinician_weights()
    assert abs(sum(wv.weights.values()) - 1.0) < 0.001
    assert wv.specialty == "clinician"
    assert len(wv.weights) == 7
    assert "f7_clinician" in wv.weights
    assert wv.weights["f7_clinician"] == 0.25


def test_quality_prior_6_families() -> None:
    """QualityPrior computes correctly with 6-family translational weights."""
    wv = load_weight_vector()
    qp = QualityPrior(wv)
    components = {k: 0.5 for k in wv.weights}
    raw = qp.compute_raw(components)
    assert 0.0 < raw < 1.0


def test_quality_prior_7_families() -> None:
    """QualityPrior computes correctly with 7-family clinician weights."""
    wv = load_clinician_weights()
    qp = QualityPrior(wv)
    components = {k: 0.5 for k in wv.weights}
    raw = qp.compute_raw(components)
    assert 0.0 < raw < 1.0


def test_quality_prior_drug_discovery_f5_dominant() -> None:
    """Drug-discovery Q(c): high F5 matters more than high F2."""
    wv = load_drug_discovery_weights()
    qp = QualityPrior(wv)

    # Candidate A: high F5, low F2
    comp_a = {k: 0.5 for k in wv.weights}
    comp_a["f5_translational"] = 0.95
    comp_a["f2_funding"] = 0.1

    # Candidate B: low F5, high F2
    comp_b = {k: 0.5 for k in wv.weights}
    comp_b["f5_translational"] = 0.1
    comp_b["f2_funding"] = 0.95

    raw_a = qp.compute_raw(comp_a)
    raw_b = qp.compute_raw(comp_b)
    assert raw_a > raw_b, (
        "F5-dominant candidate should score higher under drug-discovery weights"
    )


def test_quality_prior_clinician_f7_matters() -> None:
    """Clinician Q(c): high F7 meaningfully impacts score."""
    wv = load_clinician_weights()
    qp = QualityPrior(wv)

    # Candidate A: high F7
    comp_a = {k: 0.5 for k in wv.weights}
    comp_a["f7_clinician"] = 0.95

    # Candidate B: low F7
    comp_b = {k: 0.5 for k in wv.weights}
    comp_b["f7_clinician"] = 0.1

    raw_a = qp.compute_raw(comp_a)
    raw_b = qp.compute_raw(comp_b)
    assert raw_a > raw_b, (
        "High F7 should produce higher Q(c) under clinician weights"
    )


def test_all_weight_vectors_have_exponents() -> None:
    """All weight vectors include alpha, beta, gamma exponents."""
    for loader in [
        load_weight_vector,
        load_drug_discovery_weights,
        load_clinician_weights,
    ]:
        wv = loader()
        assert "alpha" in wv.exponents
        assert "beta" in wv.exponents
        assert "gamma" in wv.exponents
