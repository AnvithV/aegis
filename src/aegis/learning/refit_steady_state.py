"""Steady-state weight relearning: weekly refits from mixed data sources."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from aegis.learning.cold_start_guard import ColdStartGuard, GuardVerdict
from aegis.learning.downstream_quality import DownstreamQualityStore
from aegis.learning.plackett_luce import (
    FittedWeights,
    JudgmentRecord,
    PlackettLuceFitter,
)
from aegis.scoring.quality_prior import WeightVector

logger = logging.getLogger(__name__)


class DeploymentDecision(BaseModel):
    """Deployment gating decision for a refit cycle."""

    model_config = ConfigDict(frozen=True)

    action: str  # "auto_deploy", "manual_gate", "blocked"
    reason: str
    max_exponent_delta: float
    threshold: float


class SourceBreakdown(BaseModel):
    """Breakdown of data sources used in a refit cycle."""

    model_config = ConfigDict(frozen=True)

    audit_panel_count: int
    downstream_count: int
    downstream_weight_multiplier: float
    total_effective_count: int


class SpecialtyCoverage(BaseModel):
    """Per-specialty data coverage metrics."""

    model_config = ConfigDict(frozen=True)

    specialty: str
    judgment_count: int
    downstream_outcome_count: int
    has_sufficient_data: bool


class RefitReport(BaseModel):
    """Full report from a steady-state refit cycle."""

    model_config = ConfigDict(frozen=True)

    version: int
    specialty: str
    timestamp: datetime
    prior_exponents: dict[str, float]
    new_exponents: dict[str, float]
    exponent_deltas: dict[str, float]
    prior_ci: dict[str, tuple[float, float]]
    new_ci: dict[str, tuple[float, float]]
    source_breakdown: SourceBreakdown
    specialty_coverage: list[SpecialtyCoverage]
    deployment_decision: DeploymentDecision
    guard_verdict: GuardVerdict
    fitted_weights: FittedWeights


class SteadyStateConfig(BaseModel):
    """Configuration for the steady-state refitter."""

    model_config = ConfigDict(frozen=True)

    auto_deploy_threshold: float = 0.05
    min_downstream_count: int = 50
    downstream_weight_multiplier: float = 1.5
    min_judgments_per_specialty: int = 20
    ci_threshold: float = 0.2


class SteadyStateRefitter:
    """Steady-state weight relearning with mixed data sources."""

    def __init__(
        self,
        *,
        weights_dir: Path,
        audit_judgments_path: Path,
        downstream_store_path: Path,
        config: SteadyStateConfig | None = None,
    ) -> None:
        self._weights_dir = weights_dir
        self._config = config or SteadyStateConfig()
        self._audit_judgments_path = audit_judgments_path
        self._downstream_store = DownstreamQualityStore(
            storage_path=downstream_store_path,
        )

    def _load_audit_judgments(self) -> list[JudgmentRecord]:
        """Load pre-converted JudgmentRecord objects from audit JSONL."""
        records: list[JudgmentRecord] = []
        if self._audit_judgments_path.exists():
            with open(self._audit_judgments_path, encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped:
                        data = json.loads(stripped)
                        records.append(
                            JudgmentRecord(
                                winner_scores=data["winner_scores"],
                                loser_scores=data["loser_scores"],
                            )
                        )
        return records

    def _merge_judgments(
        self,
        *,
        audit: list[JudgmentRecord],
        downstream: list[JudgmentRecord],
    ) -> tuple[list[JudgmentRecord], SourceBreakdown]:
        """Merge audit-panel and downstream-derived judgments.

        Oversamples downstream if count >= min_downstream_count.
        """
        multiplier = 1.0
        if len(downstream) >= self._config.min_downstream_count:
            multiplier = self._config.downstream_weight_multiplier

        # Oversample downstream by repeating
        effective_downstream: list[JudgmentRecord] = []
        repeat_count = max(1, round(multiplier))
        for _ in range(repeat_count):
            effective_downstream.extend(downstream)

        merged = list(audit) + effective_downstream

        breakdown = SourceBreakdown(
            audit_panel_count=len(audit),
            downstream_count=len(downstream),
            downstream_weight_multiplier=multiplier,
            total_effective_count=len(merged),
        )
        return merged, breakdown

    def _compute_deployment_decision(
        self,
        *,
        prior_exponents: dict[str, float],
        new_exponents: dict[str, float],
    ) -> DeploymentDecision:
        """Compare prior and new exponents to determine deployment action."""
        deltas: dict[str, float] = {}
        for key in prior_exponents:
            deltas[key] = abs(
                new_exponents.get(key, 0.0) - prior_exponents[key]
            )

        max_delta = max(deltas.values()) if deltas else 0.0

        thr = self._config.auto_deploy_threshold
        if max_delta < thr:
            return DeploymentDecision(
                action="auto_deploy",
                reason=f"all exponent deltas below threshold ({max_delta:.4f} < {thr})",
                max_exponent_delta=max_delta,
                threshold=thr,
            )
        return DeploymentDecision(
            action="manual_gate",
            reason=f"exponent delta {max_delta:.4f} >= threshold {thr}",
            max_exponent_delta=max_delta,
            threshold=thr,
        )

    def _find_next_version(self, *, specialty: str) -> int:
        """Find the next version number for a specialty."""
        max_version = 0
        for path in self._weights_dir.glob(f"{specialty}_v*.yaml"):
            stem = path.stem  # e.g. "translational_v3"
            parts = stem.rsplit("_v", maxsplit=1)
            if len(parts) == 2:
                try:
                    version = int(parts[1])
                    max_version = max(max_version, version)
                except ValueError:
                    pass
        return max_version + 1

    def _write_weight_yaml(
        self,
        *,
        specialty: str,
        version: int,
        current_weights: WeightVector,
        fitted: FittedWeights,
        staging: bool = False,
    ) -> Path:
        """Write a weight YAML file to the weights directory or staging."""
        data = {
            "version": version,
            "specialty": specialty,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "weights": dict(current_weights.weights),
            "exponents": {
                "alpha": round(fitted.alpha, 4),
                "beta": round(fitted.beta, 4),
                "gamma": round(fitted.gamma, 4),
            },
            "exponent_bounds": {
                k: list(v)
                for k, v in current_weights.exponent_bounds.items()
            },
        }

        if staging:
            output_dir = self._weights_dir / "staging"
            filename = f"{specialty}_v{version}_pending.yaml"
        else:
            output_dir = self._weights_dir
            filename = f"{specialty}_v{version}.yaml"

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False)

        return output_path

    def run(
        self,
        *,
        specialty: str,
        current_weights: WeightVector,
    ) -> RefitReport:
        """Run one steady-state refit cycle.

        Orchestrates: load judgments, merge, fit, evaluate, gate, write.
        """
        # 1. Load audit-panel judgments
        audit_judgments = self._load_audit_judgments()

        # 2. Load downstream-derived judgments
        downstream_judgments = self._downstream_store.derive_pairwise_judgments(
            specialty=specialty,
        )

        # 3. Merge with source weighting
        merged, source_breakdown = self._merge_judgments(
            audit=audit_judgments,
            downstream=downstream_judgments,
        )

        # 4. Create fitter with bounds from current weights
        bounds = {
            k: (v[0], v[1])
            for k, v in current_weights.exponent_bounds.items()
        }
        fitter = PlackettLuceFitter(exponent_bounds=bounds)

        # 5. Fit using merged judgments
        fitted = fitter.fit(
            judgments=merged,
            initial_weights=current_weights,
        )

        # 6. Evaluate fit stability via ColdStartGuard
        guard = ColdStartGuard(ci_threshold=self._config.ci_threshold)
        guard_verdict = guard.evaluate(fitted=fitted)

        # Prior exponents
        prior_exponents = {
            "alpha": current_weights.exponents.get("alpha", 0.7),
            "beta": current_weights.exponents.get("beta", 1.0),
            "gamma": current_weights.exponents.get("gamma", 0.4),
        }

        # New exponents
        new_exponents = {
            "alpha": fitted.alpha,
            "beta": fitted.beta,
            "gamma": fitted.gamma,
        }

        # Exponent deltas
        exponent_deltas = {
            k: abs(new_exponents[k] - prior_exponents[k])
            for k in prior_exponents
        }

        # Prior CIs (use point estimate as CI if not available)
        prior_ci: dict[str, tuple[float, float]] = {
            "alpha": (prior_exponents["alpha"], prior_exponents["alpha"]),
            "beta": (prior_exponents["beta"], prior_exponents["beta"]),
            "gamma": (prior_exponents["gamma"], prior_exponents["gamma"]),
        }

        # New CIs
        new_ci: dict[str, tuple[float, float]] = {
            "alpha": fitted.alpha_ci,
            "beta": fitted.beta_ci,
            "gamma": fitted.gamma_ci,
        }

        # 7. Compute deployment decision
        deployment_decision = self._compute_deployment_decision(
            prior_exponents=prior_exponents,
            new_exponents=new_exponents,
        )

        # Override to "blocked" if guard rejects
        if not guard_verdict.allow_deployment:
            deployment_decision = DeploymentDecision(
                action="blocked",
                reason=f"cold-start guard: {guard_verdict.reason}",
                max_exponent_delta=deployment_decision.max_exponent_delta,
                threshold=deployment_decision.threshold,
            )

        # Version bumping
        new_version = self._find_next_version(specialty=specialty)

        # 8-10. Write YAML based on decision
        if deployment_decision.action == "auto_deploy":
            self._write_weight_yaml(
                specialty=specialty,
                version=new_version,
                current_weights=current_weights,
                fitted=fitted,
                staging=False,
            )
        elif deployment_decision.action == "manual_gate":
            self._write_weight_yaml(
                specialty=specialty,
                version=new_version,
                current_weights=current_weights,
                fitted=fitted,
                staging=True,
            )
        # "blocked" => do not write

        # Specialty coverage
        downstream_outcomes = self._downstream_store.by_specialty(
            specialty=specialty,
        )
        coverage = SpecialtyCoverage(
            specialty=specialty,
            judgment_count=len(merged),
            downstream_outcome_count=len(downstream_outcomes),
            has_sufficient_data=(
                len(merged) >= self._config.min_judgments_per_specialty
            ),
        )

        return RefitReport(
            version=new_version,
            specialty=specialty,
            timestamp=datetime.now(),
            prior_exponents=prior_exponents,
            new_exponents=new_exponents,
            exponent_deltas=exponent_deltas,
            prior_ci=prior_ci,
            new_ci=new_ci,
            source_breakdown=source_breakdown,
            specialty_coverage=[coverage],
            deployment_decision=deployment_decision,
            guard_verdict=guard_verdict,
            fitted_weights=fitted,
        )
