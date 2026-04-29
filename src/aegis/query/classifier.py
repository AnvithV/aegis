"""Query type classifier: routes queries to appropriate weight vectors."""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aegis.scoring.quality_prior import WeightVector, load_weight_vector

logger = logging.getLogger(__name__)


class QueryType(StrEnum):
    basic_research = "basic_research"
    drug_discovery = "drug_discovery"
    clinical_trial_pi = "clinical_trial_pi"
    policy_epi = "policy_epi"


QUERY_TYPE_TO_WEIGHT_FILE: dict[str, str] = {
    QueryType.basic_research: "config/aegis/weights/basic_research_v1.yaml",
    QueryType.drug_discovery: "config/aegis/weights/drug_discovery_v1.yaml",
    QueryType.clinical_trial_pi: "config/aegis/weights/clinician_v1.yaml",
    QueryType.policy_epi: "config/aegis/weights/policy_epi_v1.yaml",
}

_DRUG_DISCOVERY_KEYWORDS = frozenset({
    "drug", "compound", "inhibitor", "agonist", "antagonist", "pharmacol",
    "medicinal chemistry", "target", "binding", "ic50", "ec50", "adme",
    "toxicology", "formulation", "bioavailability", "lead optimization",
    "hit-to-lead", "scaffold", "sar", "structure-activity",
})

_CLINICAL_TRIAL_KEYWORDS = frozenset({
    "clinical trial", "trial investigator", "principal investigator",
    "phase 1", "phase 2", "phase 3", "phase i", "phase ii", "phase iii",
    "enrollment", "randomized", "placebo", "endpoint", "irb",
    "site investigator", "clinical study", "protocol",
})

_POLICY_EPI_KEYWORDS = frozenset({
    "epidemiology", "population health", "public health", "policy",
    "health economics", "surveillance", "outbreak", "vaccine coverage",
    "health equity", "social determinants", "disparity", "mortality rate",
    "incidence", "prevalence", "cohort study", "case-control",
})


class ClassificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_type: str
    confidence: float
    keyword_matches: list[str]
    weight_vector: WeightVector


class QueryClassifier:
    """Classify query text into a query type and load the matching weight vector."""

    def classify(self, query: str) -> ClassificationResult:
        query_lower = query.lower()

        scores: dict[str, tuple[float, list[str]]] = {}
        for qt, keywords in [
            (QueryType.drug_discovery, _DRUG_DISCOVERY_KEYWORDS),
            (QueryType.clinical_trial_pi, _CLINICAL_TRIAL_KEYWORDS),
            (QueryType.policy_epi, _POLICY_EPI_KEYWORDS),
        ]:
            matches = [kw for kw in keywords if kw in query_lower]
            scores[qt] = (len(matches), matches)

        best_type = QueryType.basic_research
        best_score = 0.0
        best_matches: list[str] = []
        for qt, (score, matches) in scores.items():
            if score > best_score:
                best_type = QueryType(qt)
                best_score = score
                best_matches = matches

        confidence = 0.5 if best_score == 0 else min(0.5 + best_score * 0.1, 0.95)

        weight_file = QUERY_TYPE_TO_WEIGHT_FILE.get(
            best_type, QUERY_TYPE_TO_WEIGHT_FILE[QueryType.basic_research]
        )
        weight_vector = load_weight_vector(Path(weight_file))

        return ClassificationResult(
            query_type=best_type,
            confidence=round(confidence, 3),
            keyword_matches=best_matches,
            weight_vector=weight_vector,
        )
