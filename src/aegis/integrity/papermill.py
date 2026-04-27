"""Paper-mill detection via tortured-phrase analysis."""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Cabanac et al. tortured-phrase dictionary: machine-generated synonyms
# mapped to their standard biomedical terms.
_TORTURED_PHRASES: dict[str, str] = {
    "counterfeit writing": "fake writing",
    "sham composition": "fake writing",
    "neural system": "neural network",
    "profound learning": "deep learning",
    "huge portions": "large samples",
    "counterfeit neural organization": "generative adversarial network",
    "irregular conduct": "abnormal behavior",
    "area of start": "starting point",
    "particular go": "specific run",
    "arbitrary forest": "random forest",
    "help vector machine": "support vector machine",
    "calculated motion": "computational flow",
    "hereditary calculation": "genetic algorithm",
    "calculated complexity": "computational complexity",
    "enormous information": "big data",
    "back brain network": "recurrent neural network",
    "fluffy rationale": "fuzzy logic",
    "component extraction": "feature extraction",
    "property extraction": "feature extraction",
    "information mining": "data mining",
    "straight relapse": "linear regression",
    "calculated relapse": "logistic regression",
    "principal worth disintegration": "singular value decomposition",
}

_TORTURED_PATTERN = re.compile(
    "|".join(re.escape(phrase) for phrase in _TORTURED_PHRASES),
    re.IGNORECASE,
)


class PaperMillSignal(BaseModel):
    """Signal bundle for paper-mill detection on a single paper."""

    model_config = ConfigDict(frozen=True)

    pmid: str
    tortured_phrases_found: list[str]
    tortured_phrase_count: int
    coordinated_authorship_score: float
    suspected_papermill: bool


class PaperMillDetector:
    """Detect paper-mill signals via tortured-phrase scanning.

    A paper is suspected if:
      - tortured_phrase_count >= threshold, OR
      - coordinated_authorship_score > 0.7
    """

    def __init__(
        self, *, phrase_threshold: int = 2
    ) -> None:
        self._threshold = phrase_threshold

    def _scan_text(self, text: str) -> list[str]:
        """Find all tortured phrases in a text."""
        return [
            m.group() for m in _TORTURED_PATTERN.finditer(text)
        ]

    def analyze(
        self,
        *,
        pmid: str = "",
        title: str = "",
        abstract: str = "",
        coordinated_authorship_score: float = 0.0,
    ) -> PaperMillSignal:
        """Analyze a single paper for paper-mill signals."""
        combined = f"{title} {abstract}"
        found = self._scan_text(combined)
        count = len(found)

        suspected = (
            count >= self._threshold
            or coordinated_authorship_score > 0.7
        )

        return PaperMillSignal(
            pmid=pmid,
            tortured_phrases_found=found,
            tortured_phrase_count=count,
            coordinated_authorship_score=(
                coordinated_authorship_score
            ),
            suspected_papermill=suspected,
        )

    def analyze_batch(
        self,
        papers: list[dict[str, str | float]],
    ) -> list[PaperMillSignal]:
        """Analyze a batch of papers for paper-mill signals.

        Each dict should have keys: pmid, title, abstract,
        and optionally coordinated_authorship_score.
        """
        return [
            self.analyze(
                pmid=str(p.get("pmid", "")),
                title=str(p.get("title", "")),
                abstract=str(p.get("abstract", "")),
                coordinated_authorship_score=float(
                    p.get(
                        "coordinated_authorship_score",
                        0.0,
                    )
                ),
            )
            for p in papers
        ]
