"""Integrity: predatory-journal, paper-mill, and retraction scoring."""

from aegis.integrity.contestability import (
    ContestabilityStore,
    OverrideAction,
    OverrideRecord,
)
from aegis.integrity.hard_gate import ArtifactRef, HardGate, HardGateResult
from aegis.integrity.llm_triage import (
    SEVERITY_DISCOUNT_MAP,
    LLMTriageClassifier,
    RetractionSeverity,
    TriageResult,
)
from aegis.integrity.papermill import PaperMillDetector, PaperMillSignal
from aegis.integrity.predatory import (
    PredatoryClassifier,
    PredatoryLoadCalculator,
    PredatorySignal,
)
from aegis.integrity.soft_discounts import (
    DiscountType,
    SoftDiscount,
    SoftDiscountResult,
    SoftDiscounts,
)

__all__ = [
    "ArtifactRef",
    "ContestabilityStore",
    "DiscountType",
    "HardGate",
    "HardGateResult",
    "LLMTriageClassifier",
    "OverrideAction",
    "OverrideRecord",
    "PaperMillDetector",
    "PaperMillSignal",
    "PredatoryClassifier",
    "PredatoryLoadCalculator",
    "PredatorySignal",
    "RetractionSeverity",
    "SEVERITY_DISCOUNT_MAP",
    "SoftDiscount",
    "SoftDiscountResult",
    "SoftDiscounts",
    "TriageResult",
]
