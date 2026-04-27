"""Rule-based specialty-ambiguity flagger for observability.

This module flags candidates whose artifact portfolio spans multiple
specialties, indicating potential ambiguity in specialty assignment.
Phase 1: observability only — does not affect scoring.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

AMBIGUITY_THRESHOLD: float = 0.6


class SpecialtyFlagResult(BaseModel):
    """Result of specialty-ambiguity analysis for a single candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    specialty_confidence: float
    is_ambiguous: bool
    artifact_mix: dict[str, float]
    reason: str


class SpecialtyAmbiguityFlagger:
    """Flag candidates with ambiguous specialty based on artifact ratios.

    Observability only in Phase 1 — does not affect candidate scores.
    """

    def __init__(self, *, threshold: float = AMBIGUITY_THRESHOLD) -> None:
        self._threshold = threshold

    def flag(
        self,
        *,
        candidate_uuid: str,
        n_papers_in_specialty: int,
        n_papers_total: int,
        n_trials_in_specialty: int,
        n_trials_total: int,
        n_grants_in_specialty: int,
        n_grants_total: int,
    ) -> SpecialtyFlagResult:
        """Evaluate specialty ambiguity from artifact counts.

        Weighted confidence = 0.5 * paper_ratio + 0.3 * trial_ratio
                            + 0.2 * grant_ratio.
        """
        paper_ratio = n_papers_in_specialty / max(n_papers_total, 1)
        trial_ratio = n_trials_in_specialty / max(n_trials_total, 1)
        grant_ratio = n_grants_in_specialty / max(n_grants_total, 1)

        confidence = (
            0.5 * paper_ratio + 0.3 * trial_ratio + 0.2 * grant_ratio
        )
        is_ambiguous = confidence < self._threshold

        artifact_mix = {
            "paper_ratio": paper_ratio,
            "trial_ratio": trial_ratio,
            "grant_ratio": grant_ratio,
        }

        if is_ambiguous:
            reason = (
                f"Low specialty confidence ({confidence:.2f} < "
                f"{self._threshold}): artifact mix suggests "
                f"cross-specialty portfolio"
            )
        else:
            reason = (
                f"Specialty confidence adequate "
                f"({confidence:.2f} >= {self._threshold})"
            )

        return SpecialtyFlagResult(
            candidate_uuid=candidate_uuid,
            specialty_confidence=confidence,
            is_ambiguous=is_ambiguous,
            artifact_mix=artifact_mix,
            reason=reason,
        )
