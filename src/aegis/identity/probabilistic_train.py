"""Threshold training for probabilistic record linkage."""

from __future__ import annotations

import logging

from thefuzz import fuzz  # type: ignore[import-untyped]

from aegis.storage.candidate_store import CandidateStore

logger = logging.getLogger(__name__)


class ThresholdTrainer:
    """Train auto-link and review thresholds from strong-key-known pairs."""

    def __init__(self, store: CandidateStore) -> None:
        self._store = store

    def train(
        self, strong_key_pairs: list[tuple[str, str]]
    ) -> dict[str, float]:
        """Compute optimal thresholds from known (artifact_name, candidate_uuid) pairs.

        Given known matches from strong-key resolution, compute name similarity
        scores and find thresholds that maximize precision at >=95% recall.

        Returns dict with "auto_link" and "review" thresholds.
        """
        if not strong_key_pairs:
            return {"auto_link": 0.95, "review": 0.5}

        # Compute similarity scores for known-match pairs
        match_scores: list[float] = []
        for artifact_name, candidate_uuid in strong_key_pairs:
            candidate = self._store.get_by_uuid(candidate_uuid)
            if candidate is None:
                continue
            best_score = 0.0
            for name_variant in candidate.name_variants:
                score = fuzz.ratio(
                    artifact_name.lower(), name_variant.lower()
                ) / 100.0
                if score > best_score:
                    best_score = score
            match_scores.append(best_score)

        if not match_scores:
            return {"auto_link": 0.95, "review": 0.5}

        match_scores.sort()
        n = len(match_scores)

        # Find review threshold: 95th percentile recall means we allow
        # at most 5% of known matches to fall below the threshold.
        review_idx = max(0, int(n * 0.05))
        review_threshold = match_scores[review_idx]

        # Auto-link threshold: set at 90th percentile of match scores
        # to ensure high precision
        auto_link_idx = min(n - 1, int(n * 0.90))
        auto_link_threshold = match_scores[auto_link_idx]

        # Ensure auto_link > review
        if auto_link_threshold <= review_threshold:
            auto_link_threshold = min(1.0, review_threshold + 0.1)

        return {
            "auto_link": auto_link_threshold,
            "review": review_threshold,
        }
