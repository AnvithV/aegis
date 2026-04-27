"""Drug-discovery weight vector loader and validation."""

from __future__ import annotations

from pathlib import Path

from aegis.scoring.quality_prior import WeightVector, load_weight_vector

_DEFAULT_PATH = Path("config/aegis/weights/drug_discovery_v1.yaml")

# Expected weight distribution for drug-discovery population
_EXPECTED_WEIGHTS = {
    "f1_rcr": 0.15,
    "f2_funding": 0.05,
    "f3_leadership": 0.15,
    "f4_apex": 0.05,
    "f5_translational": 0.50,
    "f6_lineage": 0.10,
}


def load_drug_discovery_weights(
    config_path: Path | None = None,
) -> WeightVector:
    """Load the drug-discovery weight vector from YAML.

    Validates that weights sum to 1.0 and specialty is 'drug_discovery'.
    """
    wv = load_weight_vector(config_path or _DEFAULT_PATH)
    assert wv.specialty == "drug_discovery", (
        f"Expected specialty 'drug_discovery', got '{wv.specialty}'"
    )
    total = sum(wv.weights.values())
    assert abs(total - 1.0) < 0.001, (
        f"Weights must sum to 1.0, got {total}"
    )
    return wv


def validate_drug_discovery_weights(wv: WeightVector) -> list[str]:
    """Validate a drug-discovery weight vector against expectations.

    Returns list of warnings (empty if all good).
    """
    warnings: list[str] = []
    if wv.weights.get("f5_translational", 0) < 0.3:
        warnings.append(
            "F5 (translational) should dominate for drug-discovery "
            f"(got {wv.weights.get('f5_translational', 0)})"
        )
    if wv.weights.get("f2_funding", 0) > 0.15:
        warnings.append(
            "F2 (funding) should be low for drug-discovery — "
            "industry researchers have minimal NIH funding"
        )
    return warnings
