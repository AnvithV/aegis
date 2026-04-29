"""Weight refit API: trigger and status endpoints."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from aegis.scoring.quality_prior import WeightVector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/refit", tags=["refit"])

_WEIGHTS_DIR = Path(os.environ.get("AEGIS_WEIGHTS_DIR", "config/aegis/weights"))
_AUDIT_JUDGMENTS = Path(
    os.environ.get("AEGIS_AUDIT_JUDGMENTS", "data/aegis/audit_judgments.jsonl")
)
_DOWNSTREAM_STORE = Path(
    os.environ.get("AEGIS_DOWNSTREAM_STORE", "data/aegis/downstream_quality.jsonl")
)


class RefitTriggerResponse(BaseModel):
    """Response from triggering a weight refit cycle."""

    model_config = ConfigDict(frozen=True)

    status: str  # "completed" | "blocked" | "error"
    specialty: str
    deployment_decision: str
    new_version: int | None
    prior_exponents: dict[str, float]
    new_exponents: dict[str, float]
    delta: dict[str, float]
    guard_verdict: str
    message: str


class RefitStatusResponse(BaseModel):
    """Current refit status for a specialty."""

    model_config = ConfigDict(frozen=True)

    last_refit_at: str | None
    current_version: int
    specialty: str
    exponents: dict[str, float]
    ci_half_widths: dict[str, float]
    pending_downstream_outcomes: int


def _find_latest_weight_yaml(specialty: str) -> tuple[Path, int]:
    """Find the highest-version weight YAML for a specialty.

    Returns (path, version).
    """
    max_version = 0
    best_path: Path | None = None
    for path in _WEIGHTS_DIR.glob(f"{specialty}_v*.yaml"):
        match = re.search(r"_v(\d+)\.yaml$", path.name)
        if match:
            version = int(match.group(1))
            if version > max_version:
                max_version = version
                best_path = path
    if best_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"No weight file found for specialty '{specialty}'",
        )
    return best_path, max_version


def _load_weight_vector(path: Path) -> WeightVector:
    """Load a WeightVector from a YAML file."""
    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return WeightVector(
        version=data.get("version", 1),
        specialty=data.get("specialty", "unknown"),
        weights=data.get("weights", {}),
        exponents=data.get("exponents", {}),
        exponent_bounds=data.get("exponent_bounds", {}),
    )


@router.post("/trigger")
def trigger_refit(specialty: str = "basic_research") -> RefitTriggerResponse:
    """Trigger a weight refit cycle for the given specialty."""
    try:
        path, version = _find_latest_weight_yaml(specialty)
        weight_vector = _load_weight_vector(path)

        # Ensure data files exist
        _AUDIT_JUDGMENTS.parent.mkdir(parents=True, exist_ok=True)
        if not _AUDIT_JUDGMENTS.exists():
            _AUDIT_JUDGMENTS.touch()

        _DOWNSTREAM_STORE.parent.mkdir(parents=True, exist_ok=True)
        if not _DOWNSTREAM_STORE.exists():
            _DOWNSTREAM_STORE.touch()

        from aegis.learning.refit_steady_state import SteadyStateRefitter

        refitter = SteadyStateRefitter(
            weights_dir=_WEIGHTS_DIR,
            audit_judgments_path=_AUDIT_JUDGMENTS,
            downstream_store_path=_DOWNSTREAM_STORE,
        )

        report = refitter.run(specialty=specialty, current_weights=weight_vector)

        action = report.deployment_decision.action
        if action == "auto_deploy":
            status_str = "completed"
        elif action == "manual_gate":
            status_str = "completed"
        else:
            status_str = "blocked"

        return RefitTriggerResponse(
            status=status_str,
            specialty=report.specialty,
            deployment_decision=action,
            new_version=report.version,
            prior_exponents=report.prior_exponents,
            new_exponents=report.new_exponents,
            delta=report.exponent_deltas,
            guard_verdict=report.guard_verdict.reason,
            message=report.deployment_decision.reason,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Refit trigger failed for specialty=%s", specialty)
        return RefitTriggerResponse(
            status="error",
            specialty=specialty,
            deployment_decision="error",
            new_version=None,
            prior_exponents={},
            new_exponents={},
            delta={},
            guard_verdict="error",
            message=str(exc),
        )


@router.get("/status")
def get_refit_status(specialty: str = "basic_research") -> RefitStatusResponse:
    """Get current refit status for the given specialty."""
    path, version = _find_latest_weight_yaml(specialty)

    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)

    exponents = data.get("exponents", {})
    last_refit_at = data.get("last_refit") or data.get("timestamp") or data.get("created")

    pending = 0
    if _DOWNSTREAM_STORE.exists():
        pending = _DOWNSTREAM_STORE.read_text(encoding="utf-8").count("\n")

    return RefitStatusResponse(
        last_refit_at=str(last_refit_at) if last_refit_at else None,
        current_version=version,
        specialty=data.get("specialty", specialty),
        exponents=exponents,
        ci_half_widths={},
        pending_downstream_outcomes=pending,
    )
