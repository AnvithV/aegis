"""NPI-PubMed name-match HITL router.

Routes NPI-to-PubMed author linkages through auto-link, review, or
reject paths. NEVER auto-links below 0.95 confidence because NPI
mis-attribution can wrongly hard-zero via state board lookup.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

AUTO_LINK_THRESHOLD: float = 0.95
REVIEW_THRESHOLD: float = 0.5


class NpiPubmedMatch(BaseModel):
    """Result of NPI-to-PubMed author matching."""

    model_config = ConfigDict(frozen=True)

    npi: str
    pubmed_author_name: str
    npi_provider_name: str
    confidence: float
    action: Literal["auto-link", "review", "reject"]
    specialty_match: bool
    address_match: bool
    rejection_signals: list[str]


class NpiPubmedMatcher:
    """Match NPI records to PubMed authors with HITL routing."""

    def match(
        self,
        npi: str,
        npi_name: str,
        npi_specialty: str,
        npi_state: str,
        pubmed_author: str,
        pubmed_affiliation: str,
        pubmed_mesh: list[str],
    ) -> NpiPubmedMatch:
        """Match an NPI record to a PubMed author.

        Confidence formula:
            name_similarity + 0.1 * specialty_match + 0.1 * address_match
        Capped at 1.0. NEVER auto-links below 0.95.
        """
        rejection_signals: list[str] = []

        # Name similarity
        npi_lower = npi_name.lower().strip()
        pub_lower = pubmed_author.lower().strip()

        if npi_lower == pub_lower:
            name_sim = 1.0
        elif npi_lower.split()[-1] == pub_lower.split()[-1]:
            name_sim = 0.7
        else:
            name_sim = 0.3
            rejection_signals.append("name_mismatch")

        # Specialty match (stub — true if both non-empty)
        specialty_match = bool(npi_specialty and pubmed_mesh)
        if not specialty_match:
            rejection_signals.append("specialty_mismatch")

        # Address match: NPI state appears in PubMed affiliation
        address_match = bool(
            npi_state and npi_state.upper() in pubmed_affiliation.upper()
        )
        if not address_match:
            rejection_signals.append("address_mismatch")

        # Confidence: name_sim + bonuses, capped at 1.0
        confidence = min(
            name_sim + 0.1 * float(specialty_match) + 0.1 * float(address_match),
            1.0,
        )

        # Action routing — NEVER auto-link below 0.95
        if confidence >= AUTO_LINK_THRESHOLD:
            action: Literal["auto-link", "review", "reject"] = "auto-link"
        elif confidence >= REVIEW_THRESHOLD:
            action = "review"
        else:
            action = "reject"

        logger.debug(
            "NPI %s -> PubMed '%s': confidence=%.3f action=%s",
            npi,
            pubmed_author,
            confidence,
            action,
        )

        return NpiPubmedMatch(
            npi=npi,
            pubmed_author_name=pubmed_author,
            npi_provider_name=npi_name,
            confidence=confidence,
            action=action,
            specialty_match=specialty_match,
            address_match=address_match,
            rejection_signals=rejection_signals,
        )
