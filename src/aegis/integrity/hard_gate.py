"""Hard-zero integrity gate: I(c) = 0 exclusion rules."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from aegis.integrity.llm_triage import (
    LLMTriageClassifier,
    RetractionSeverity,
)
from aegis.sources.leie import LEIEStore
from aegis.sources.ofac_sam import OFACSAMStore
from aegis.sources.ori import ORIStore
from aegis.sources.retraction_watch import RetractionWatchStore

logger = logging.getLogger(__name__)

_HARD_ZERO_SEVERITIES = frozenset({
    RetractionSeverity.fabrication,
    RetractionSeverity.falsification,
})

_MESH_OVERLAP_THRESHOLD = 0.6


class ArtifactRef(BaseModel):
    """Reference to a source artifact that triggered a gate."""

    model_config = ConfigDict(frozen=True)

    source: str
    identifier: str
    detail: str | None


class HardGateResult(BaseModel):
    """Result of the hard-zero gate evaluation."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    is_zero: bool
    reason: str | None
    artifact_ref: ArtifactRef | None
    rules_evaluated: int


def _jaccard_mesh(
    set_a: set[str], set_b: set[str]
) -> float:
    """Compute Jaccard similarity between two MeSH sets."""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


class HardGate:
    """Evaluate candidates against hard-zero rules.

    Rules evaluated in order (short-circuit on first match):
      1. LEIE federal exclusion
      2. OFAC/SAM listing
      3. ORI misconduct finding within 10 years
      4. Retraction in target subdomain for fabrication/falsification
      5. Medical board action (Phase 1 stub)
    """

    def __init__(
        self,
        *,
        leie_store: LEIEStore,
        ofac_sam_store: OFACSAMStore,
        ori_store: ORIStore,
        retraction_store: RetractionWatchStore,
        triage_classifier: LLMTriageClassifier | None = None,
    ) -> None:
        self._leie = leie_store
        self._ofac_sam = ofac_sam_store
        self._ori = ori_store
        self._retraction = retraction_store
        self._triage = triage_classifier or LLMTriageClassifier()

    def evaluate(
        self,
        *,
        candidate_uuid: str,
        candidate_name: str,
        npi: str | None = None,
        candidate_mesh: set[str] | None = None,
        query_mesh: set[str] | None = None,
        retraction_notices: list[dict[str, str]] | None = None,
    ) -> HardGateResult:
        """Evaluate all hard-zero rules for a candidate."""
        rules = 0

        # Rule 1: LEIE federal exclusion
        rules += 1
        leie_result = self._leie.is_excluded(
            npi=npi, name=candidate_name
        )
        if leie_result is True:
            return HardGateResult(
                candidate_uuid=candidate_uuid,
                is_zero=True,
                reason="LEIE federal exclusion",
                artifact_ref=ArtifactRef(
                    source="LEIE",
                    identifier=npi or candidate_name,
                    detail="active exclusion",
                ),
                rules_evaluated=rules,
            )

        # Rule 2: OFAC/SAM listing
        rules += 1
        if self._ofac_sam.is_listed(candidate_name):
            return HardGateResult(
                candidate_uuid=candidate_uuid,
                is_zero=True,
                reason="OFAC/SAM listing",
                artifact_ref=ArtifactRef(
                    source="OFAC_SAM",
                    identifier=candidate_name,
                    detail="active listing",
                ),
                rules_evaluated=rules,
            )

        # Rule 3: ORI misconduct finding within 10 years
        rules += 1
        if self._ori.has_recent_finding(candidate_name):
            return HardGateResult(
                candidate_uuid=candidate_uuid,
                is_zero=True,
                reason="ORI misconduct finding (10yr)",
                artifact_ref=ArtifactRef(
                    source="ORI",
                    identifier=candidate_name,
                    detail="recent finding",
                ),
                rules_evaluated=rules,
            )

        # Rule 4: Retraction for fabrication/falsification
        #         in target subdomain (MeSH Jaccard >= 0.6)
        rules += 1
        if retraction_notices and candidate_mesh and query_mesh:
            overlap = _jaccard_mesh(candidate_mesh, query_mesh)
            if overlap >= _MESH_OVERLAP_THRESHOLD:
                triage_results = self._triage.classify_batch(
                    retraction_notices
                )
                for tr in triage_results:
                    if tr.severity in _HARD_ZERO_SEVERITIES:
                        return HardGateResult(
                            candidate_uuid=candidate_uuid,
                            is_zero=True,
                            reason=(
                                f"retraction ({tr.severity.value})"
                                f" in subdomain"
                            ),
                            artifact_ref=ArtifactRef(
                                source="retraction_watch",
                                identifier=tr.pmid,
                                detail=tr.severity.value,
                            ),
                            rules_evaluated=rules,
                        )

        # Rule 5: Medical board action (Phase 1 stub)
        rules += 1

        return HardGateResult(
            candidate_uuid=candidate_uuid,
            is_zero=False,
            reason=None,
            artifact_ref=None,
            rules_evaluated=rules,
        )
