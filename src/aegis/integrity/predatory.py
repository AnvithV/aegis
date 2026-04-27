"""Predatory journal classification and publication-load scoring."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class PredatorySignal(BaseModel):
    """Signal bundle for a single paper's predatory-journal assessment."""

    model_config = ConfigDict(frozen=True)

    pmid: str
    journal_nlm_id: str | None
    is_medline_indexed: bool
    is_doaj_listed: bool
    cabells_flagged: bool
    heuristic_flags: list[str]
    is_predatory: bool


class PredatoryClassifier:
    """Triangulate predatory-journal status from multiple signals.

    Rules:
      1. MEDLINE-indexed -> never predatory (highest trust).
      2. Cabells flagged -> predatory.
      3. NOT MEDLINE AND NOT DOAJ AND >=2 heuristic flags -> predatory.
    """

    def classify(
        self,
        *,
        is_medline_indexed: bool,
        is_doaj_listed: bool,
        cabells_flagged: bool,
        heuristic_flags: list[str],
        pmid: str = "",
        journal_nlm_id: str | None = None,
    ) -> PredatorySignal:
        """Classify a paper's journal as predatory or not."""
        if is_medline_indexed:
            is_predatory = False
        elif cabells_flagged:
            is_predatory = True
        elif (
            not is_doaj_listed and len(heuristic_flags) >= 2
        ):
            is_predatory = True
        else:
            is_predatory = False

        return PredatorySignal(
            pmid=pmid,
            journal_nlm_id=journal_nlm_id,
            is_medline_indexed=is_medline_indexed,
            is_doaj_listed=is_doaj_listed,
            cabells_flagged=cabells_flagged,
            heuristic_flags=heuristic_flags,
            is_predatory=is_predatory,
        )


class PredatoryLoadCalculator:
    """Compute fraction of a candidate's papers in predatory journals.

    Weight by author position: last author = 1.0, first = 0.8,
    middle = 0.5.
    """

    _POSITION_WEIGHTS: dict[str, float] = {
        "last": 1.0,
        "first": 0.8,
        "middle": 0.5,
    }

    def compute_load(
        self,
        signals: list[PredatorySignal],
        positions: list[str],
    ) -> float:
        """Compute weighted predatory publication fraction.

        Args:
            signals: Per-paper predatory signals.
            positions: Parallel list of author positions
                       ("first", "middle", "last").

        Returns:
            Weighted fraction in [0.0, 1.0].
        """
        if not signals:
            return 0.0

        total_weight = 0.0
        predatory_weight = 0.0

        for signal, position in zip(signals, positions):
            w = self._POSITION_WEIGHTS.get(position, 0.5)
            total_weight += w
            if signal.is_predatory:
                predatory_weight += w

        if total_weight == 0.0:
            return 0.0

        return predatory_weight / total_weight
