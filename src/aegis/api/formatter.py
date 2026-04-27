"""Result formatter: converts internal RankedList to customer-facing QueryResponse.

Produces per-candidate output with:
- ROR-normalized affiliation
- Top-3 contributing artifacts with hyperlinks
- Per-component scores
- Identity-linkage confidence
- Score-variance band (from Bootstrap)
- Integrity-gate disclosures (any soft discounts applied; never silent)
- Specialty annotation
- Provenance pointer (served weight-version and integrity-rule version)
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from aegis.api.schemas import (
    ArtifactLink,
    CandidateResult,
    ExpansionInfo,
    IntegrityDisclosure,
    QueryResponse,
    StalenessWarning,
    VarianceBand,
)
from aegis.scoring.result_format import RankedList
from aegis.scoring.variance import ScoreBand

logger = logging.getLogger(__name__)

_ARTIFACT_URL_TEMPLATES: dict[str, str] = {
    "pmid": "https://pubmed.ncbi.nlm.nih.gov/{id}",
    "nct_id": "https://clinicaltrials.gov/study/{id}",
    "patent_id": "https://patents.google.com/patent/{id}",
    "grant_id": "https://reporter.nih.gov/project-details/{id}",
}


def _build_artifact_link(
    artifact_type: str,
    identifier: str,
    title: str,
    contribution_score: float,
) -> ArtifactLink:
    """Build an artifact link with the appropriate URL template."""
    template = _ARTIFACT_URL_TEMPLATES.get(
        artifact_type, "https://search.crossref.org/?q={id}"
    )
    url = template.replace("{id}", identifier)
    return ArtifactLink(
        artifact_type=artifact_type,
        identifier=identifier,
        title=title,
        url=url,
        contribution_score=contribution_score,
    )


def _build_integrity_disclosures(
    discounts: list[dict[str, object]],
) -> list[IntegrityDisclosure]:
    """Convert soft discount dicts to IntegrityDisclosure models."""
    result: list[IntegrityDisclosure] = []
    for d in discounts:
        result.append(
            IntegrityDisclosure(
                discount_type=str(d.get("discount_type", "")),
                factor=float(d.get("factor", 1.0)),  # type: ignore[arg-type]
                detail=str(d.get("detail", "")),
            )
        )
    return result


class ResultFormatter:
    """Format ranked results for customer consumption."""

    def __init__(
        self,
        *,
        integrity_rule_version: str = "1.0.0",
    ) -> None:
        self._integrity_rule_version = integrity_rule_version

    def format(
        self,
        *,
        ranked: RankedList,
        expansion_info: ExpansionInfo,
        variance_bands: dict[str, ScoreBand] | None = None,
        soft_discounts: dict[str, list[dict[str, object]]] | None = None,
        affiliations: dict[str, tuple[str, str | None]] | None = None,
        specialties: dict[str, str] | None = None,
        staleness_warnings: list[StalenessWarning] | None = None,
    ) -> QueryResponse:
        """Format a RankedList into a customer-facing QueryResponse."""
        query_id = uuid.uuid4().hex
        now = datetime.now(UTC)
        candidates: list[CandidateResult] = []

        for rc in ranked.candidates:
            # Build artifact links from top_artifacts
            artifact_links = [
                _build_artifact_link(
                    artifact_type=a.artifact_type,
                    identifier=a.identifier,
                    title=a.title,
                    contribution_score=a.contribution_score,
                )
                for a in rc.top_artifacts[:3]
            ]

            # Variance band
            vb: VarianceBand | None = None
            if variance_bands and rc.candidate_uuid in variance_bands:
                sb = variance_bands[rc.candidate_uuid]
                vb = VarianceBand(low=sb.low, high=sb.high, median=sb.median)

            # Integrity disclosures
            disclosures: list[IntegrityDisclosure] = []
            if soft_discounts and rc.candidate_uuid in soft_discounts:
                disclosures = _build_integrity_disclosures(
                    soft_discounts[rc.candidate_uuid]
                )

            # Affiliation
            aff_name = "Unknown"
            aff_country: str | None = None
            if affiliations and rc.candidate_uuid in affiliations:
                aff_name, aff_country = affiliations[rc.candidate_uuid]

            # Specialty
            specialty: str | None = None
            if specialties and rc.candidate_uuid in specialties:
                specialty = specialties[rc.candidate_uuid]

            # Component scores
            component_scores = {
                "quality_prior": rc.breakdown.quality_prior,
                "topical_fit": rc.breakdown.topical_fit,
                "recency": rc.breakdown.recency,
                "integrity": rc.breakdown.integrity_score,
            }

            candidates.append(
                CandidateResult(
                    rank=rc.rank,
                    candidate_uuid=rc.candidate_uuid,
                    candidate_name=rc.candidate_name,
                    affiliation=aff_name,
                    affiliation_country=aff_country,
                    score=rc.score,
                    component_scores=component_scores,
                    top_artifacts=artifact_links,
                    linkage_confidence=rc.linkage_confidence,
                    variance_band=vb,
                    integrity_disclosures=disclosures,
                    specialty=specialty,
                    evidence_trail=rc.evidence_trail,
                )
            )

        return QueryResponse(
            query_id=query_id,
            timestamp=now,
            candidates=candidates,
            total_candidates_evaluated=ranked.cohort_size,
            excluded_count=ranked.excluded_count,
            expansion_info=expansion_info,
            staleness_warnings=staleness_warnings or [],
            weight_version=ranked.weight_version,
            integrity_rule_version=self._integrity_rule_version,
            metadata=dict(ranked.metadata),
        )
