"""Identity-linkage confidence reporting and threshold classification."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from aegis.storage import CandidateStore


class LinkageThresholds(BaseModel):
    """Thresholds for linkage confidence classification."""

    model_config = ConfigDict(frozen=True)

    flag_threshold: float = 0.7
    holdout_threshold: float = 0.5


class ConfidenceShift(BaseModel):
    """Record of a candidate's linkage confidence change between snapshots."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    previous_confidence: float
    current_confidence: float
    delta: float
    crossed_threshold: str | None


class LinkageReporter:
    """Classify candidates by linkage confidence and track shifts."""

    def __init__(
        self,
        store: CandidateStore,
        thresholds: LinkageThresholds | None = None,
    ) -> None:
        self._store = store
        self._thresholds = thresholds or LinkageThresholds()

    def classify_candidate(self, candidate_uuid: str) -> str:
        """Return 'confident', 'low_confidence', or 'holdout'."""
        candidate = self._store.get_by_uuid(candidate_uuid)
        if candidate is None:
            return "holdout"
        return self._classify(candidate.linkage_confidence)

    def _classify(self, confidence: float) -> str:
        if confidence >= self._thresholds.flag_threshold:
            return "confident"
        if confidence >= self._thresholds.holdout_threshold:
            return "low_confidence"
        return "holdout"

    def get_holdouts(self) -> list[str]:
        """Return UUIDs of candidates below the holdout threshold."""
        candidates = self._store.list_by_cohort()
        return [
            c.uuid
            for c in candidates
            if c.linkage_confidence < self._thresholds.holdout_threshold
        ]

    def get_flagged(self) -> list[str]:
        """Return UUIDs below flag_threshold but at or above holdout."""
        candidates = self._store.list_by_cohort()
        return [
            c.uuid
            for c in candidates
            if self._thresholds.holdout_threshold
            <= c.linkage_confidence
            < self._thresholds.flag_threshold
        ]

    def daily_shift_report(
        self,
        previous_snapshot: dict[str, float],
    ) -> list[ConfidenceShift]:
        """Compare current store confidences against a previous snapshot."""
        candidates = self._store.list_by_cohort()
        shifts: list[ConfidenceShift] = []
        for c in candidates:
            prev = previous_snapshot.get(c.uuid)
            if prev is None:
                continue
            delta = round(c.linkage_confidence - prev, 6)
            if delta == 0.0:
                continue
            crossed = self._detect_crossing(prev, c.linkage_confidence)
            shifts.append(
                ConfidenceShift(
                    candidate_uuid=c.uuid,
                    previous_confidence=prev,
                    current_confidence=c.linkage_confidence,
                    delta=delta,
                    crossed_threshold=crossed,
                )
            )
        return shifts

    def _detect_crossing(
        self, prev: float, curr: float
    ) -> str | None:
        """Detect if a threshold boundary was crossed."""
        flag = self._thresholds.flag_threshold
        holdout = self._thresholds.holdout_threshold
        for name, threshold in [
            ("flag", flag),
            ("holdout", holdout),
        ]:
            if (prev < threshold <= curr) or (
                curr < threshold <= prev
            ):
                return name
        return None

    def save_snapshot(self, path: str) -> dict[str, float]:
        """Persist current confidences as JSON and return the dict."""
        candidates = self._store.list_by_cohort()
        snapshot = {
            c.uuid: c.linkage_confidence for c in candidates
        }
        with open(path, "w") as f:
            json.dump(snapshot, f, indent=2)
        return snapshot
