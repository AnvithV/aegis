"""Cross-population identity merge for unifying candidates across populations."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

AUTO_MERGE_THRESHOLD = 0.95
REVIEW_THRESHOLD = 0.5


class MergeCandidate(BaseModel):
    """A candidate appearing across multiple populations."""

    model_config = ConfigDict(frozen=True)

    uuid: str
    name_variants: list[str]
    strong_keys: dict[str, str]
    populations: list[str]
    specialty_distribution: dict[str, float]
    artifact_sources: dict[str, int]


class MergeResult(BaseModel):
    """Result of merging two candidate records."""

    model_config = ConfigDict(frozen=True)

    merged_uuid: str
    source_uuids: list[str]
    confidence: float
    merge_type: str  # "strong_key" | "probabilistic" | "review_needed"
    matching_keys: list[str]
    populations_merged: list[str]


class CrossPopulationMerger:
    """Merge candidates across translational, drug-discovery, clinician populations."""

    def __init__(self) -> None:
        self._candidates: list[MergeCandidate] = []
        self._merge_log: list[MergeResult] = []

    def add_candidate(self, candidate: MergeCandidate) -> None:
        """Register a candidate for merge consideration."""
        self._candidates.append(candidate)

    def find_merge_candidates(
        self, candidate: MergeCandidate, population: str
    ) -> list[tuple[MergeCandidate, float, str]]:
        """Find potential matches for a candidate, sorted by confidence desc.

        Returns list of (match, confidence, merge_type) tuples with
        confidence >= REVIEW_THRESHOLD.
        """
        matches: list[tuple[MergeCandidate, float, str]] = []
        for existing in self._candidates:
            if existing.uuid == candidate.uuid:
                continue
            confidence, merge_type, matching_keys = (
                self._compute_merge_confidence(candidate, existing)
            )
            if confidence >= REVIEW_THRESHOLD:
                matches.append((existing, confidence, merge_type))
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def merge(
        self,
        primary: MergeCandidate,
        secondary: MergeCandidate,
        confidence: float,
        merge_type: str,
    ) -> MergeResult:
        """Execute merge: primary UUID is retained.

        Populations and specialty_distributions are merged (max for overlapping).
        """
        all_populations = list(
            dict.fromkeys([*primary.populations, *secondary.populations])
        )

        # Merge specialty distributions: take max for overlapping specialties
        merged_dist = dict(primary.specialty_distribution)
        for spec, prob in secondary.specialty_distribution.items():
            merged_dist[spec] = max(merged_dist.get(spec, 0.0), prob)

        # Determine matching keys
        matching_keys: list[str] = []
        for key_type, key_value in primary.strong_keys.items():
            if secondary.strong_keys.get(key_type) == key_value:
                matching_keys.append(key_type)

        result = MergeResult(
            merged_uuid=primary.uuid,
            source_uuids=[primary.uuid, secondary.uuid],
            confidence=confidence,
            merge_type=merge_type,
            matching_keys=matching_keys,
            populations_merged=all_populations,
        )
        self._merge_log.append(result)

        logger.info(
            "Merged %s <- %s (confidence=%.3f, type=%s, keys=%s)",
            primary.uuid,
            secondary.uuid,
            confidence,
            merge_type,
            matching_keys,
        )
        return result

    def get_merge_log(self) -> list[MergeResult]:
        """Return all merge operations performed."""
        return list(self._merge_log)

    @staticmethod
    def _compute_merge_confidence(
        a: MergeCandidate, b: MergeCandidate
    ) -> tuple[float, str, list[str]]:
        """Compute merge confidence between two candidates.

        Strong-key match (ORCID, NPI, patent_inventor_id):
            confidence = min(0.95 + 0.02 * len(matching_keys), 1.0)

        Name-based match:
            confidence = min(0.5 + 0.15 * name_overlap, 0.9)
        """
        strong_key_types = {"orcid", "npi", "patent_inventor_id"}
        matching_keys: list[str] = []

        for key_type in strong_key_types:
            a_val = a.strong_keys.get(key_type)
            b_val = b.strong_keys.get(key_type)
            if a_val is not None and b_val is not None and a_val == b_val:
                matching_keys.append(key_type)

        if matching_keys:
            confidence = min(0.95 + 0.02 * len(matching_keys), 1.0)
            return confidence, "strong_key", matching_keys

        # Name-based matching
        a_names = {n.lower() for n in a.name_variants}
        b_names = {n.lower() for n in b.name_variants}
        if a_names and b_names:
            intersection = len(a_names & b_names)
            if intersection > 0:
                confidence = min(0.5 + 0.15 * intersection, 0.9)
                merge_type = (
                    "probabilistic"
                    if confidence >= AUTO_MERGE_THRESHOLD
                    else "review_needed"
                )
                return confidence, merge_type, []

        return 0.0, "review_needed", []
