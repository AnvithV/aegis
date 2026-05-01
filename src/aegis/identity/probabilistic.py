"""Probabilistic record linkage using Fellegi-Sunter-inspired feature scoring."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from thefuzz import fuzz  # type: ignore[import-untyped]

from aegis.identity.ror import RorResolver
from aegis.identity.strong_key import CandidateRegistry
from aegis.storage.candidate_store import CandidateStore

logger = logging.getLogger(__name__)

# Default feature weights.
_WEIGHT_NAME = 0.35
_WEIGHT_AFFILIATION = 0.25
_WEIGHT_COAUTHOR = 0.15
_WEIGHT_MESH = 0.15
_WEIGHT_TIME = 0.10

# Default thresholds.
_DEFAULT_THRESHOLDS: dict[str, float] = {
    "auto_link": 0.75,
    "review": 0.5,
}


class LinkResult(BaseModel):
    """Result of probabilistic record linkage."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str | None
    confidence: float
    action: Literal["auto-link", "review", "reject"]
    feature_scores: dict[str, float]


class ProbabilisticLinker:
    """Fellegi-Sunter-inspired probabilistic record linker."""

    def __init__(
        self,
        store: CandidateStore,
        ror_resolver: RorResolver,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        self._store = store
        self._ror_resolver = ror_resolver
        self._thresholds = thresholds or dict(_DEFAULT_THRESHOLDS)

    def link(
        self,
        artifact_features: dict[str, Any],
        registry: CandidateRegistry,
        *,
        candidates: list[Any] | None = None,
    ) -> LinkResult:
        """Link an artifact to the best matching candidate.

        artifact_features keys:
          - name: str (full name)
          - name_variants: list[str] (alternative name forms)
          - affiliation: str (raw affiliation string)
          - coauthors: list[str] (co-author names)
          - mesh_terms: list[str] (MeSH descriptors)
          - year: int | None (publication year)

        Pass ``candidates`` to avoid a DB scan (e.g. when the caller
        maintains an in-memory snapshot of the candidate store).
        """
        if candidates is None:
            candidates = self._store.list_by_cohort()
        if not candidates:
            return LinkResult(
                candidate_uuid=None,
                confidence=0.0,
                action="reject",
                feature_scores={
                    "name_similarity": 0.0,
                    "affiliation_similarity": 0.0,
                    "coauthor_overlap": 0.0,
                    "mesh_overlap": 0.0,
                    "time_continuity": 0.0,
                },
            )

        best_confidence = 0.0
        best_uuid: str | None = None
        best_features: dict[str, float] = {}

        artifact_name: str = artifact_features.get("name", "")
        artifact_variants: list[str] = artifact_features.get(
            "name_variants", []
        )
        if artifact_name and artifact_name not in artifact_variants:
            artifact_variants = [artifact_name, *artifact_variants]

        artifact_affiliation: str = artifact_features.get(
            "affiliation", ""
        )
        artifact_coauthors: list[str] = artifact_features.get(
            "coauthors", []
        )
        artifact_mesh: list[str] = artifact_features.get(
            "mesh_terms", []
        )
        artifact_year: int | None = artifact_features.get("year")

        # Resolve artifact affiliation to ROR
        artifact_ror = self._ror_resolver.resolve(artifact_affiliation)

        for candidate in candidates:
            features = self._compute_features(
                artifact_variants=artifact_variants,
                artifact_ror_id=artifact_ror.ror_id if artifact_ror else None,
                artifact_ror_parent=(
                    artifact_ror.parent_ror_id if artifact_ror else None
                ),
                artifact_coauthors=artifact_coauthors,
                artifact_mesh=artifact_mesh,
                artifact_year=artifact_year,
                candidate=candidate,
            )

            confidence = self._weighted_score(
                features,
                has_coauthors=bool(artifact_coauthors),
                has_mesh=bool(artifact_mesh) and bool(candidate.mesh_descriptors),
            )

            if confidence > best_confidence:
                best_confidence = confidence
                best_uuid = candidate.uuid
                best_features = features

        if not best_features:
            best_features = {
                "name_similarity": 0.0,
                "affiliation_similarity": 0.0,
                "coauthor_overlap": 0.0,
                "mesh_overlap": 0.0,
                "time_continuity": 0.0,
            }

        action = self._classify(best_confidence)
        if action == "reject":
            best_uuid = None

        return LinkResult(
            candidate_uuid=best_uuid,
            confidence=best_confidence,
            action=action,
            feature_scores=best_features,
        )

    def link_batch(
        self,
        artifacts: list[dict[str, Any]],
        registry: CandidateRegistry,
    ) -> list[LinkResult]:
        """Link a batch of artifacts."""
        return [self.link(a, registry) for a in artifacts]

    def _compute_features(
        self,
        *,
        artifact_variants: list[str],
        artifact_ror_id: str | None,
        artifact_ror_parent: str | None,
        artifact_coauthors: list[str],
        artifact_mesh: list[str],
        artifact_year: int | None,
        candidate: Any,
    ) -> dict[str, float]:
        """Compute per-feature similarity scores."""
        name_sim = self._name_similarity(
            artifact_variants, candidate.name_variants
        )
        aff_sim = self._affiliation_similarity(
            artifact_ror_id, artifact_ror_parent, candidate
        )
        coauthor_sim = self._coauthor_overlap(
            artifact_coauthors, candidate
        )
        mesh_sim = self._mesh_overlap(artifact_mesh, candidate)
        time_sim = self._time_continuity(artifact_year, candidate)

        return {
            "name_similarity": name_sim,
            "affiliation_similarity": aff_sim,
            "coauthor_overlap": coauthor_sim,
            "mesh_overlap": mesh_sim,
            "time_continuity": time_sim,
        }

    @staticmethod
    def _name_similarity(
        artifact_variants: list[str],
        candidate_variants: list[str],
    ) -> float:
        """Best fuzzy match across all name variant pairs."""
        if not artifact_variants or not candidate_variants:
            return 0.0
        best = 0
        for a_name in artifact_variants:
            for c_name in candidate_variants:
                score = fuzz.ratio(a_name.lower(), c_name.lower())
                if score > best:
                    best = score
        return best / 100.0

    def _affiliation_similarity(
        self,
        artifact_ror_id: str | None,
        artifact_ror_parent: str | None,
        candidate: Any,
    ) -> float:
        """ROR-based affiliation similarity."""
        if artifact_ror_id is None:
            return 0.0

        for aff in candidate.affiliations:
            if aff.ror_id == artifact_ror_id:
                return 1.0

        # Check parent org match
        if artifact_ror_parent is not None:
            for aff in candidate.affiliations:
                if aff.ror_id == artifact_ror_parent:
                    return 0.5

        # Dynamically resolve candidate affiliation strings and compare ROR IDs.
        # Handles the common case where aff.ror_id was not set at ingest time
        # (e.g. PubMed candidates whose affiliations weren't ROR-resolved).
        for aff in candidate.affiliations:
            resolved = self._ror_resolver.resolve(aff.canonical_name)
            if resolved:
                if resolved.ror_id == artifact_ror_id:
                    return 1.0
                if (
                    resolved.parent_ror_id == artifact_ror_id
                    or resolved.ror_id == artifact_ror_parent
                ):
                    return 0.5

        return 0.0

    @staticmethod
    def _coauthor_overlap(
        artifact_coauthors: list[str],
        candidate: Any,
    ) -> float:
        """Jaccard similarity of co-author name sets."""
        if not artifact_coauthors:
            return 0.0
        # Gather candidate's co-author evidence from evidence_trail
        # For Phase 0: use name variants as a proxy
        artifact_set = {n.lower() for n in artifact_coauthors}
        candidate_set = {n.lower() for n in candidate.name_variants}

        # In a full implementation, we'd have co-author data.
        # For now, check if any artifact coauthors match candidate names.
        intersection = artifact_set & candidate_set
        union = artifact_set | candidate_set
        if not union:
            return 0.0
        return len(intersection) / len(union)

    @staticmethod
    def _mesh_overlap(
        artifact_mesh: list[str],
        candidate: Any,
    ) -> float:
        """Jaccard similarity of MeSH descriptor sets."""
        if not artifact_mesh or not candidate.mesh_descriptors:
            return 0.0
        artifact_set = {m.lower() for m in artifact_mesh}
        candidate_set = {
            d.descriptor.lower() for d in candidate.mesh_descriptors
        }
        intersection = artifact_set & candidate_set
        union = artifact_set | candidate_set
        if not union:
            return 0.0
        return len(intersection) / len(union)

    @staticmethod
    def _time_continuity(
        artifact_year: int | None,
        candidate: Any,
    ) -> float:
        """Score based on publication year proximity to candidate's active years."""
        if artifact_year is None:
            return 0.5  # neutral when unknown

        if not candidate.affiliations:
            return 0.5

        # Find candidate's active year range from affiliations
        years: list[int] = []
        for aff in candidate.affiliations:
            if aff.start_date is not None:
                years.append(aff.start_date.year)
            if aff.end_date is not None:
                years.append(aff.end_date.year)

        if not years:
            return 0.5

        min_year = min(years)
        max_year = max(years)

        if min_year <= artifact_year <= max_year:
            return 1.0

        # Decay based on distance from active range
        distance = min(
            abs(artifact_year - min_year),
            abs(artifact_year - max_year),
        )
        # Score decays to 0 at 20 years distance
        return max(0.0, 1.0 - distance / 20.0)

    @staticmethod
    def _weighted_score(
        features: dict[str, float],
        *,
        has_coauthors: bool,
        has_mesh: bool,
    ) -> float:
        """Compute weighted confidence, redistributing absent feature weight.

        When co-author or MeSH data is absent from the artifact, the weight
        for those features is redistributed proportionally to the present
        features so that a perfect match on available signals can still
        reach 1.0.
        """
        weights: dict[str, float] = {
            "name_similarity": _WEIGHT_NAME,
            "affiliation_similarity": _WEIGHT_AFFILIATION,
            "coauthor_overlap": _WEIGHT_COAUTHOR,
            "mesh_overlap": _WEIGHT_MESH,
            "time_continuity": _WEIGHT_TIME,
        }
        # Zero out absent features and redistribute their weight
        if not has_coauthors:
            weights["coauthor_overlap"] = 0.0
        if not has_mesh:
            weights["mesh_overlap"] = 0.0

        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0

        score = 0.0
        for key, weight in weights.items():
            score += (weight / total_weight) * features[key]
        return score

    def _classify(
        self, confidence: float
    ) -> Literal["auto-link", "review", "reject"]:
        """Classify based on thresholds."""
        if confidence >= self._thresholds["auto_link"]:
            return "auto-link"
        if confidence >= self._thresholds["review"]:
            return "review"
        return "reject"
