"""LLM-based retraction-notice triage classifier."""

from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class RetractionSeverity(StrEnum):
    """Severity categories for retraction notices."""

    fabrication = "fabrication"
    falsification = "falsification"
    honest_error = "honest_error"
    duplicate_publication = "duplicate_publication"
    no_statement = "no_statement"
    unclassifiable = "unclassifiable"


class TriageResult(BaseModel):
    """Result of classifying a retraction notice."""

    model_config = ConfigDict(frozen=True)

    pmid: str
    retraction_notice_text: str
    severity: RetractionSeverity
    confidence: float
    reasoning: str
    grounded: bool


SEVERITY_DISCOUNT_MAP: dict[RetractionSeverity, float] = {
    RetractionSeverity.fabrication: 0.0,
    RetractionSeverity.falsification: 0.0,
    RetractionSeverity.honest_error: 0.85,
    RetractionSeverity.duplicate_publication: 0.7,
    RetractionSeverity.no_statement: 0.6,
    RetractionSeverity.unclassifiable: 0.7,
}

# Keyword patterns for heuristic fallback (Phase 1).
_KEYWORD_MAP: list[tuple[RetractionSeverity, list[str]]] = [
    (
        RetractionSeverity.fabrication,
        ["fabricat", "made up"],
    ),
    (
        RetractionSeverity.falsification,
        ["falsif", "manipulat", "image manipulation"],
    ),
    (
        RetractionSeverity.honest_error,
        ["honest error", "inadvertent"],
    ),
    (
        RetractionSeverity.duplicate_publication,
        ["overlapping publication"],
    ),
]


class LLMTriageClassifier:
    """Classify retraction notices into severity buckets.

    Phase 1: keyword-based heuristic fallback when LLM is
    unavailable. Phase 2 will add real LLM integration.
    """

    def classify(
        self,
        *,
        pmid: str = "",
        retraction_notice_text: str = "",
    ) -> TriageResult:
        """Classify a single retraction notice."""
        text_lower = retraction_notice_text.lower()

        for severity, keywords in _KEYWORD_MAP:
            for kw in keywords:
                if kw in text_lower:
                    return TriageResult(
                        pmid=pmid,
                        retraction_notice_text=(
                            retraction_notice_text
                        ),
                        severity=severity,
                        confidence=0.8,
                        reasoning=f"keyword match: '{kw}'",
                        grounded=True,
                    )

        # No keyword match — check for empty/missing text
        if not retraction_notice_text.strip():
            return TriageResult(
                pmid=pmid,
                retraction_notice_text=retraction_notice_text,
                severity=RetractionSeverity.no_statement,
                confidence=0.9,
                reasoning="no retraction notice text provided",
                grounded=True,
            )

        return TriageResult(
            pmid=pmid,
            retraction_notice_text=retraction_notice_text,
            severity=RetractionSeverity.unclassifiable,
            confidence=0.5,
            reasoning="no keyword match found",
            grounded=True,
        )

    def classify_batch(
        self,
        notices: list[dict[str, str]],
    ) -> list[TriageResult]:
        """Classify a batch of retraction notices.

        Each dict should have keys: pmid, retraction_notice_text.
        """
        return [
            self.classify(
                pmid=n.get("pmid", ""),
                retraction_notice_text=n.get(
                    "retraction_notice_text", ""
                ),
            )
            for n in notices
        ]
