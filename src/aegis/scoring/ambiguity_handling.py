"""Ambiguity handling for specialty classification.

When classifier confidence falls below the ambiguity threshold (0.6),
score the candidate under the top-2 specialty weight vectors and report
dual-rank results.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

AMBIGUITY_THRESHOLD: float = 0.6


class DualRankResult(BaseModel):
    """Dual-rank result for a potentially ambiguous candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    is_ambiguous: bool
    primary_specialty: str
    primary_rank_percentile: float
    secondary_specialty: str | None
    secondary_rank_percentile: float | None
    confidence: float
    recommendation: str


class AmbiguityHandler:
    """Handle ambiguous specialty classifications with dual-ranking."""

    def __init__(self, threshold: float = AMBIGUITY_THRESHOLD) -> None:
        self._threshold = threshold

    def evaluate(
        self,
        candidate_uuid: str,
        specialty_probabilities: dict[str, float],
        score_under_specialty: dict[str, float],
    ) -> DualRankResult:
        """Evaluate a candidate for specialty ambiguity.

        Args:
            candidate_uuid: Unique identifier for the candidate.
            specialty_probabilities: Mapping of specialty -> probability
                from the classifier.
            score_under_specialty: Mapping of specialty -> rank percentile
                when scored under that specialty's weight vector.

        Returns:
            DualRankResult with single or dual ranking.
        """
        if not specialty_probabilities:
            logger.warning(
                "No specialty probabilities for candidate %s; "
                "defaulting to translational",
                candidate_uuid,
            )
            return DualRankResult(
                candidate_uuid=candidate_uuid,
                is_ambiguous=True,
                primary_specialty="translational",
                primary_rank_percentile=score_under_specialty.get(
                    "translational", 0.0
                ),
                secondary_specialty=None,
                secondary_rank_percentile=None,
                confidence=0.0,
                recommendation=(
                    "No classification data; defaulting to translational"
                ),
            )

        sorted_specs = sorted(
            specialty_probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        primary_spec, primary_prob = sorted_specs[0]
        primary_rank = score_under_specialty.get(primary_spec, 0.0)

        if primary_prob >= self._threshold:
            logger.debug(
                "Candidate %s: high-confidence %s (%.2f)",
                candidate_uuid,
                primary_spec,
                primary_prob,
            )
            return DualRankResult(
                candidate_uuid=candidate_uuid,
                is_ambiguous=False,
                primary_specialty=primary_spec,
                primary_rank_percentile=primary_rank,
                secondary_specialty=None,
                secondary_rank_percentile=None,
                confidence=primary_prob,
                recommendation=f"High-confidence {primary_spec} classification",
            )

        secondary_spec = sorted_specs[1][0] if len(sorted_specs) > 1 else None
        secondary_rank = (
            score_under_specialty.get(secondary_spec, 0.0)
            if secondary_spec is not None
            else None
        )

        logger.info(
            "Candidate %s: ambiguous (%.2f confidence); "
            "dual-ranking under %s and %s",
            candidate_uuid,
            primary_prob,
            primary_spec,
            secondary_spec,
        )

        return DualRankResult(
            candidate_uuid=candidate_uuid,
            is_ambiguous=True,
            primary_specialty=primary_spec,
            primary_rank_percentile=primary_rank,
            secondary_specialty=secondary_spec,
            secondary_rank_percentile=secondary_rank,
            confidence=primary_prob,
            recommendation=(
                f"Ambiguous ({primary_prob:.2f} confidence); "
                f"ranked under both {primary_spec} and {secondary_spec}"
            ),
        )
