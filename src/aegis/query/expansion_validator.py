"""Expansion validator: fail-closed MeSH ontology validation for LLM query expansion.

Validates every LLM-proposed MeSH term against:
1. MeSH descriptor vocabulary (primary check)
2. CPC-to-MeSH crosswalk (secondary)
3. ChEMBL-to-MeSH crosswalk (tertiary)

Any term not found in any vocabulary is REJECTED. This is fail-closed:
we prefer missing a valid expansion over accepting an invented term.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Result of validating a single term."""

    model_config = ConfigDict(frozen=True)

    term: str
    valid: bool
    source: str | None
    normalized: str | None


class ValidationReport(BaseModel):
    """Report for a batch of validated terms."""

    model_config = ConfigDict(frozen=True)

    total_terms: int
    valid_count: int
    rejected_count: int
    valid_terms: list[str]
    rejected_terms: list[str]
    details: list[ValidationResult]
    validated_at: datetime


class ValidatorStats(BaseModel):
    """Cumulative stats for the validator."""

    model_config = ConfigDict(frozen=True)

    total_validations: int
    total_terms_checked: int
    total_rejected: int
    rejection_rate: float


class ExpansionValidator:
    """Fail-closed validator for LLM-expanded MeSH terms.

    Checks proposed terms against the MeSH vocabulary and taxonomy
    crosswalks. Rejects anything not found.
    """

    def __init__(
        self,
        *,
        mesh_descriptors: set[str] | None = None,
        cpc_mesh_terms: set[str] | None = None,
        chembl_mesh_terms: set[str] | None = None,
    ) -> None:
        # Store all vocabulary terms as lowercase for case-insensitive matching
        self._mesh = {t.lower() for t in (mesh_descriptors or set())}
        self._cpc = {t.lower() for t in (cpc_mesh_terms or set())}
        self._chembl = {t.lower() for t in (chembl_mesh_terms or set())}
        self._total_validations = 0
        self._total_terms = 0
        self._total_rejected = 0

    def _normalize_term(self, term: str) -> str:
        """Strip whitespace and title-case the term."""
        return term.strip().title()

    def _check_term(self, term: str) -> ValidationResult:
        """Check a single term against all vocabularies."""
        normalized = self._normalize_term(term)
        lower = normalized.lower()

        if lower in self._mesh:
            return ValidationResult(
                term=term, valid=True, source="mesh", normalized=normalized
            )
        if lower in self._cpc:
            return ValidationResult(
                term=term, valid=True, source="cpc_xwalk", normalized=normalized
            )
        if lower in self._chembl:
            return ValidationResult(
                term=term, valid=True, source="chembl_xwalk", normalized=normalized
            )

        return ValidationResult(
            term=term, valid=False, source=None, normalized=normalized
        )

    def validate(self, terms: list[str]) -> ValidationReport:
        """Validate a batch of terms. Fail-closed: unknown terms are rejected."""
        self._total_validations += 1
        details: list[ValidationResult] = []
        valid_terms: list[str] = []
        rejected_terms: list[str] = []

        for term in terms:
            result = self._check_term(term)
            details.append(result)
            self._total_terms += 1
            if result.valid:
                valid_terms.append(term)
            else:
                rejected_terms.append(term)
                self._total_rejected += 1

        return ValidationReport(
            total_terms=len(terms),
            valid_count=len(valid_terms),
            rejected_count=len(rejected_terms),
            valid_terms=valid_terms,
            rejected_terms=rejected_terms,
            details=details,
            validated_at=datetime.now(UTC),
        )

    def validate_single(self, term: str) -> bool:
        """Convenience: return True if term is valid."""
        result = self._check_term(term)
        self._total_terms += 1
        if not result.valid:
            self._total_rejected += 1
        return result.valid

    def get_stats(self) -> ValidatorStats:
        """Return cumulative validation stats."""
        if self._total_terms > 0:
            rate = self._total_rejected / self._total_terms
        else:
            rate = 0.0
        return ValidatorStats(
            total_validations=self._total_validations,
            total_terms_checked=self._total_terms,
            total_rejected=self._total_rejected,
            rejection_rate=round(rate, 6),
        )
