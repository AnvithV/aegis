"""Patent-vs-paper signal balance dashboard for multi-population scoring."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

PATENT_DOMINANCE_ALERT_THRESHOLD = 0.90


class SignalBalanceMetrics(BaseModel):
    """Frozen snapshot of signal contributions for a single candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    paper_contribution: float
    patent_contribution: float
    trial_contribution: float
    grant_contribution: float
    total_mesh_terms: int


class CohortSignalBalance(BaseModel):
    """Frozen snapshot of signal balance across a cohort."""

    model_config = ConfigDict(frozen=True)

    total_candidates: int
    mean_paper_contribution: float
    mean_patent_contribution: float
    mean_trial_contribution: float
    patent_dominant_count: int
    alert_triggered: bool
    alert_message: str | None


class SignalBalanceDashboard:
    """Compute per-candidate and cohort-level signal balance metrics."""

    def compute_candidate(
        self,
        candidate_uuid: str,
        paper_mesh_count: int,
        patent_mesh_count: int,
        trial_mesh_count: int,
        grant_mesh_count: int,
    ) -> SignalBalanceMetrics:
        """Compute signal contribution proportions for a single candidate."""
        total = (
            paper_mesh_count + patent_mesh_count
            + trial_mesh_count + grant_mesh_count
        )
        safe_total = max(total, 1)

        return SignalBalanceMetrics(
            candidate_uuid=candidate_uuid,
            paper_contribution=round(paper_mesh_count / safe_total, 4),
            patent_contribution=round(patent_mesh_count / safe_total, 4),
            trial_contribution=round(trial_mesh_count / safe_total, 4),
            grant_contribution=round(grant_mesh_count / safe_total, 4),
            total_mesh_terms=total,
        )

    def compute_cohort(
        self, candidates: list[SignalBalanceMetrics]
    ) -> CohortSignalBalance:
        """Compute cohort-level signal balance with patent dominance alerting."""
        total = len(candidates)
        if total == 0:
            return CohortSignalBalance(
                total_candidates=0,
                mean_paper_contribution=0.0,
                mean_patent_contribution=0.0,
                mean_trial_contribution=0.0,
                patent_dominant_count=0,
                alert_triggered=False,
                alert_message=None,
            )

        mean_paper = round(
            sum(c.paper_contribution for c in candidates) / total, 4
        )
        mean_patent = round(
            sum(c.patent_contribution for c in candidates) / total, 4
        )
        mean_trial = round(
            sum(c.trial_contribution for c in candidates) / total, 4
        )

        # Patent dominant = patent contribution > 70%
        patent_dominant_count = sum(
            1 for c in candidates if c.patent_contribution > 0.70
        )

        alert_triggered = mean_patent >= PATENT_DOMINANCE_ALERT_THRESHOLD
        alert_message: str | None = None
        if alert_triggered:
            alert_message = (
                f"Patent signal dominance: mean patent contribution "
                f"{mean_patent:.2%} exceeds threshold "
                f"{PATENT_DOMINANCE_ALERT_THRESHOLD:.2%}"
            )
            logger.warning("Signal balance alert: %s", alert_message)

        return CohortSignalBalance(
            total_candidates=total,
            mean_paper_contribution=mean_paper,
            mean_patent_contribution=mean_patent,
            mean_trial_contribution=mean_trial,
            patent_dominant_count=patent_dominant_count,
            alert_triggered=alert_triggered,
            alert_message=alert_message,
        )
