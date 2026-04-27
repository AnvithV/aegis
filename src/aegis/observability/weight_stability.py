"""Weight-stability tracking between consecutive weight versions."""

from __future__ import annotations

import glob
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aegis.scoring.quality_prior import WeightVector, load_weight_vector


class WeightShift(BaseModel):
    """A single parameter shift between weight versions."""

    model_config = ConfigDict(frozen=True)

    parameter: str
    old_value: float
    new_value: float
    absolute_change: float
    relative_change_pct: float
    exceeds_threshold: bool


class StabilityReport(BaseModel):
    """Report comparing two consecutive weight versions."""

    model_config = ConfigDict(frozen=True)

    old_version: int
    new_version: int
    shifts: list[WeightShift]
    requires_review: bool
    auto_deploy_ok: bool
    summary: str


class WeightStabilityTracker:
    """Compare consecutive weight versions for stability."""

    def __init__(
        self,
        shift_threshold_pct: float = 25.0,
    ) -> None:
        self._shift_threshold_pct = shift_threshold_pct

    def compare_weights(
        self,
        parameter: str,
        old_value: float,
        new_value: float,
    ) -> WeightShift:
        """Compare a single weight parameter between versions."""
        absolute_change = abs(new_value - old_value)

        if abs(old_value) < 1e-10:
            # Handle zero old_value
            relative_change_pct = (
                100.0 if absolute_change > 0.01 else 0.0
            )
        else:
            relative_change_pct = (
                100.0 * absolute_change / abs(old_value)
            )

        exceeds = relative_change_pct > self._shift_threshold_pct

        return WeightShift(
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            absolute_change=round(absolute_change, 6),
            relative_change_pct=round(relative_change_pct, 2),
            exceeds_threshold=exceeds,
        )

    def compare_vectors(
        self,
        old: WeightVector,
        new: WeightVector,
    ) -> list[WeightShift]:
        """Compare all weights and exponents between two WeightVectors."""
        shifts: list[WeightShift] = []

        all_weight_keys = sorted(
            set(old.weights) | set(new.weights)
        )
        for key in all_weight_keys:
            old_val = old.weights.get(key, 0.0)
            new_val = new.weights.get(key, 0.0)
            shifts.append(
                self.compare_weights(
                    f"weight.{key}", old_val, new_val
                )
            )

        all_exp_keys = sorted(
            set(old.exponents) | set(new.exponents)
        )
        for key in all_exp_keys:
            old_val = old.exponents.get(key, 0.0)
            new_val = new.exponents.get(key, 0.0)
            shifts.append(
                self.compare_weights(
                    f"exponent.{key}", old_val, new_val
                )
            )

        return shifts

    def load_version(
        self, config_path: Path
    ) -> WeightVector:
        """Load a weight vector from a YAML config file."""
        return load_weight_vector(config_path)

    def check_latest_stability(
        self,
        weights_dir: str = "config/aegis/weights",
    ) -> StabilityReport | None:
        """Compare the two highest translational_v*.yaml versions."""
        pattern = str(
            Path(weights_dir) / "translational_v*.yaml"
        )
        files = sorted(glob.glob(pattern))

        if len(files) < 2:
            return None

        old_vec = self.load_version(Path(files[-2]))
        new_vec = self.load_version(Path(files[-1]))

        return self._build_report(old_vec, new_vec)

    def _build_report(
        self,
        old_vec: WeightVector,
        new_vec: WeightVector,
    ) -> StabilityReport:
        """Build a stability report from two weight vectors."""
        shifts = self.compare_vectors(old_vec, new_vec)
        requires_review = any(s.exceeds_threshold for s in shifts)
        auto_deploy_ok = not requires_review

        exceeded = [s for s in shifts if s.exceeds_threshold]
        if exceeded:
            names = ", ".join(s.parameter for s in exceeded)
            summary = (
                f"Review required: {len(exceeded)} parameter(s) "
                f"exceed {self._shift_threshold_pct}% threshold: "
                f"{names}"
            )
        else:
            summary = (
                f"All parameters within "
                f"{self._shift_threshold_pct}% threshold. "
                f"Auto-deploy OK."
            )

        return StabilityReport(
            old_version=old_vec.version,
            new_version=new_vec.version,
            shifts=shifts,
            requires_review=requires_review,
            auto_deploy_ok=auto_deploy_ok,
            summary=summary,
        )

    def generate_review_template(
        self,
        report: StabilityReport,
    ) -> str:
        """Generate a Markdown review template for weight changes."""
        rows = ""
        for s in report.shifts:
            flag = " **EXCEEDS**" if s.exceeds_threshold else ""
            rows += (
                f"| {s.parameter} | {s.old_value} | "
                f"{s.new_value} | {s.absolute_change} | "
                f"{s.relative_change_pct}% |{flag}\n"
            )

        return f"""# Weight Change Review

## Version Change: v{report.old_version} -> v{report.new_version}

**Status:** {"REQUIRES REVIEW" if report.requires_review else "Auto-deploy OK"}

{report.summary}

## Parameter Changes

| Parameter | Old | New | Abs Change | Rel Change | Flag |
|-----------|-----|-----|------------|------------|------|
{rows}

## Approval

- [ ] Reviewed by domain expert
- [ ] Backtested on held-out cohort
- [ ] Approved for deployment
"""
