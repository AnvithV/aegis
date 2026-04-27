"""Soft discount evaluation: multiplicative I(c) factors."""

from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from aegis.integrity.papermill import PaperMillDetector
from aegis.integrity.predatory import PredatoryLoadCalculator

logger = logging.getLogger(__name__)

# Floor constants — no discount can push below these values.
PREDATORY_FLOOR = 0.5
RETRACTION_FLOOR = 0.4
AUTHORSHIP_INCONSISTENCY_FLOOR = 0.85
PAPERMILL_PENDING_FLOOR = 0.7


class DiscountType(StrEnum):
    """Types of soft integrity discounts."""

    predatory_load = "predatory_load"
    out_of_subdomain_retraction = "out_of_subdomain_retraction"
    authorship_inconsistency = "authorship_inconsistency"
    papermill_pending = "papermill_pending"


class SoftDiscount(BaseModel):
    """A single soft discount factor."""

    model_config = ConfigDict(frozen=True)

    discount_type: DiscountType
    factor: float
    floor: float
    detail: str
    evidence: str | None


class SoftDiscountResult(BaseModel):
    """Combined result of all soft discount evaluations."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    discounts: list[SoftDiscount]
    combined_factor: float


class SoftDiscounts:
    """Evaluate soft discount factors for a candidate.

    Discount types:
      1. Predatory-journal load
      2. Out-of-subdomain retractions
      3. Authorship inconsistency (Phase 1 stub)
      4. Paper-mill signals
    """

    def __init__(
        self,
        *,
        predatory_calc: PredatoryLoadCalculator | None = None,
        papermill_detector: PaperMillDetector | None = None,
    ) -> None:
        self._predatory_calc = (
            predatory_calc or PredatoryLoadCalculator()
        )
        self._papermill = (
            papermill_detector or PaperMillDetector()
        )

    def evaluate(
        self,
        *,
        candidate_uuid: str,
        predatory_load: float = 0.0,
        out_of_subdomain_retraction_count: int = 0,
        papermill_suspected: bool = False,
    ) -> SoftDiscountResult:
        """Evaluate all soft discounts and return combined."""
        discounts: list[SoftDiscount] = []

        # 1. Predatory-journal load
        #    Linear: load 0.0 -> factor 1.0, load 1.0 -> FLOOR
        if predatory_load > 0.0:
            raw = 1.0 - predatory_load * (1.0 - PREDATORY_FLOOR)
            factor = max(raw, PREDATORY_FLOOR)
            discounts.append(
                SoftDiscount(
                    discount_type=DiscountType.predatory_load,
                    factor=factor,
                    floor=PREDATORY_FLOOR,
                    detail=(
                        f"predatory load {predatory_load:.2f}"
                    ),
                    evidence=None,
                )
            )

        # 2. Out-of-subdomain retractions
        #    Each retraction reduces by 0.1, floor at RETRACTION_FLOOR
        if out_of_subdomain_retraction_count > 0:
            raw = 1.0 - 0.1 * out_of_subdomain_retraction_count
            factor = max(raw, RETRACTION_FLOOR)
            discounts.append(
                SoftDiscount(
                    discount_type=(
                        DiscountType.out_of_subdomain_retraction
                    ),
                    factor=factor,
                    floor=RETRACTION_FLOOR,
                    detail=(
                        f"{out_of_subdomain_retraction_count}"
                        f" retraction(s)"
                    ),
                    evidence=None,
                )
            )

        # 3. Authorship inconsistency (Phase 1 stub)
        # No discount applied in Phase 1.

        # 4. Paper-mill signals
        if papermill_suspected:
            discounts.append(
                SoftDiscount(
                    discount_type=DiscountType.papermill_pending,
                    factor=PAPERMILL_PENDING_FLOOR,
                    floor=PAPERMILL_PENDING_FLOOR,
                    detail="paper-mill signal detected",
                    evidence=None,
                )
            )

        # Combined factor = product of all individual factors
        combined = 1.0
        for d in discounts:
            combined *= d.factor

        return SoftDiscountResult(
            candidate_uuid=candidate_uuid,
            discounts=discounts,
            combined_factor=combined,
        )
