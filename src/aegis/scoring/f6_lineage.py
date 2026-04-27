"""F6 sub-score: mentorship lineage using Academic Family Tree data."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict


class F6Score(BaseModel):
    """Result of F6 computation for a single candidate."""

    model_config = ConfigDict(frozen=True)

    traceable_trainee_count: int
    r01_trainee_count: int  # trainees in tree who later won R01s
    data_confidence: float  # based on AFT coverage (0.0-1.0)
    percentile: float  # percentile within cohort [0, 1]


@dataclass
class LineageInput:
    """Raw inputs for F6 scoring."""

    traceable_trainee_count: int
    r01_trainee_count: int
    aft_link_confidence: float  # linkage confidence from AFT to cohort candidate


class F6Computer:
    """Compute F6 sub-score (mentorship lineage) for candidates."""

    def score_raw(
        self,
        inp: LineageInput,
    ) -> tuple[float, int, int, float]:
        """Compute raw F6 values (before percentile).

        Returns (composite, traceable_count, r01_count, data_confidence).
        """
        trainee_component = min(inp.traceable_trainee_count / 10.0, 1.0)
        r01_component = min(inp.r01_trainee_count / 5.0, 1.0)

        raw_composite = 0.4 * trainee_component + 0.6 * r01_component
        composite = raw_composite * inp.aft_link_confidence

        return (
            composite,
            inp.traceable_trainee_count,
            inp.r01_trainee_count,
            inp.aft_link_confidence,
        )

    def compute_percentiles(
        self,
        raw_scores: list[tuple[str, float, int, int, float]],
    ) -> dict[str, F6Score]:
        """Compute percentile rank for each candidate.

        Takes list of (uuid, composite, traceable_count, r01_count, data_confidence).
        """
        if not raw_scores:
            return {}

        # Sort by composite to assign percentiles
        sorted_scores = sorted(raw_scores, key=lambda x: x[1])

        n = len(sorted_scores)
        results: dict[str, F6Score] = {}
        for rank_idx, (
            uuid,
            _composite,
            traceable_count,
            r01_count,
            data_confidence,
        ) in enumerate(sorted_scores):
            percentile = (rank_idx + 0.5) / n  # midpoint percentile
            results[uuid] = F6Score(
                traceable_trainee_count=traceable_count,
                r01_trainee_count=r01_count,
                data_confidence=round(data_confidence, 6),
                percentile=round(percentile, 6),
            )

        return results
