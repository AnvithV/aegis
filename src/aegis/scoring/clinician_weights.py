"""Clinician weight vector loader and validation."""

from __future__ import annotations

from pathlib import Path

from aegis.scoring.quality_prior import WeightVector, load_weight_vector

_DEFAULT_PATH = Path("config/aegis/weights/clinician_v1.yaml")


def load_clinician_weights(
    config_path: Path | None = None,
) -> WeightVector:
    """Load the clinician weight vector from YAML.

    Validates that weights sum to 1.0, specialty is 'clinician',
    and F7 is present.
    """
    wv = load_weight_vector(config_path or _DEFAULT_PATH)
    assert wv.specialty == "clinician", (
        f"Expected specialty 'clinician', got '{wv.specialty}'"
    )
    total = sum(wv.weights.values())
    assert abs(total - 1.0) < 0.001, (
        f"Weights must sum to 1.0, got {total}"
    )
    assert "f7_clinician" in wv.weights, (
        "Clinician weight vector must include f7_clinician"
    )
    return wv


def validate_clinician_weights(wv: WeightVector) -> list[str]:
    """Validate a clinician weight vector against expectations.

    Returns list of warnings (empty if all good).
    """
    warnings: list[str] = []
    if "f7_clinician" not in wv.weights:
        warnings.append("Missing f7_clinician weight")
    elif wv.weights["f7_clinician"] < 0.1:
        warnings.append(
            f"F7 weight unexpectedly low ({wv.weights['f7_clinician']})"
        )
    if wv.weights.get("f3_leadership", 0) < 0.15:
        warnings.append(
            "F3 (leadership) should be significant for clinicians"
        )
    return warnings
