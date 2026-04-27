"""Reassignment-rate tracking and churn alerting for candidate specialty changes."""

from __future__ import annotations

import logging
import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

CHURN_ALERT_THRESHOLD = 0.05


class ReassignmentRateMetrics(BaseModel):
    """Frozen snapshot of a single reassignment run."""

    model_config = ConfigDict(frozen=True)

    run_date: date
    total_candidates: int
    reassigned_count: int
    reassignment_rate: float
    major_changes: int
    alert_triggered: bool
    alert_message: str | None


class ReassignmentAlert(BaseModel):
    """Alert emitted when reassignment churn exceeds threshold."""

    model_config = ConfigDict(frozen=True)

    alert_id: str
    run_date: date
    reassignment_rate: float
    threshold: float
    major_changes: int
    message: str


class ReassignmentMetrics:
    """Track reassignment rates across runs and detect churn spikes."""

    def __init__(
        self, churn_threshold: float = CHURN_ALERT_THRESHOLD
    ) -> None:
        self._threshold = churn_threshold
        self._history: list[ReassignmentRateMetrics] = []

    def record_run(
        self,
        run_date: date,
        total_candidates: int,
        reassigned_count: int,
        major_changes: int,
    ) -> ReassignmentRateMetrics:
        """Record a reassignment run and return metrics with optional alert."""
        rate = reassigned_count / max(total_candidates, 1)
        alert_triggered = rate > self._threshold

        alert_message: str | None = None
        if alert_triggered:
            alert = ReassignmentAlert(
                alert_id=str(uuid.uuid4()),
                run_date=run_date,
                reassignment_rate=round(rate, 4),
                threshold=self._threshold,
                major_changes=major_changes,
                message=(
                    f"Reassignment rate {rate:.2%} exceeds threshold "
                    f"{self._threshold:.2%} ({reassigned_count}/{total_candidates} "
                    f"candidates, {major_changes} major changes)"
                ),
            )
            alert_message = alert.message
            logger.warning("Churn alert: %s", alert_message)

        metrics = ReassignmentRateMetrics(
            run_date=run_date,
            total_candidates=total_candidates,
            reassigned_count=reassigned_count,
            reassignment_rate=round(rate, 4),
            major_changes=major_changes,
            alert_triggered=alert_triggered,
            alert_message=alert_message,
        )
        self._history.append(metrics)
        return metrics

    def get_history(self) -> list[ReassignmentRateMetrics]:
        """Return all recorded reassignment runs."""
        return list(self._history)

    def check_stability(self, window: int = 7) -> bool:
        """Check if all recent runs within window are below the churn threshold."""
        recent = self._history[-window:]
        if not recent:
            return True
        return all(r.reassignment_rate <= self._threshold for r in recent)
