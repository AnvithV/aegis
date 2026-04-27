"""F1 sub-score: RCR aggregation (field-normalized citation impact)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict


class F1Score(BaseModel):
    """Result of F1 computation for a single candidate."""

    model_config = ConfigDict(frozen=True)

    mean_rcr_log: float
    top_rcr_log: float  # 90th percentile RCR in log space
    percentile: float  # percentile within cohort, 0.0-1.0
    low_confidence: bool  # True if <10 RCR-eligible papers
    eligible_paper_count: int


# Author-position weights per program overview
AUTHOR_WEIGHT_LAST: float = 1.0
AUTHOR_WEIGHT_CORRESPONDING: float = 1.0
AUTHOR_WEIGHT_FIRST: float = 0.7
AUTHOR_WEIGHT_MIDDLE: float = 0.3

# Article types to exclude from RCR aggregation
_EXCLUDED_ARTICLE_TYPES: frozenset[str] = frozenset(
    {
        "Editorial",
        "Letter",
        "Published Erratum",
        "Corrected and Republished Article",
        "Comment",
    }
)

_LOW_CONFIDENCE_THRESHOLD: int = 10


@dataclass
class PaperRCR:
    """Intermediate: a single paper's RCR with author-position weight."""

    pmid: str
    rcr: float
    author_weight: float
    article_type: str | None


class F1Computer:
    """Compute F1 sub-score (RCR aggregation) for candidates."""

    def score_raw(
        self,
        paper_rcrs: list[PaperRCR],
    ) -> tuple[float, float, bool, int]:
        """Compute raw F1 values (before percentile).

        Returns (mean_rcr_log, top_rcr_log, low_confidence, eligible_count).
        """
        # Filter out excluded article types
        eligible = [
            p
            for p in paper_rcrs
            if p.article_type not in _EXCLUDED_ARTICLE_TYPES
            and p.rcr > 0
        ]

        if not eligible:
            return (0.0, 0.0, True, 0)

        low_confidence = len(eligible) < _LOW_CONFIDENCE_THRESHOLD

        # Weighted RCR values in log space
        weighted_log_rcrs: list[float] = []
        for p in eligible:
            log_rcr = math.log(p.rcr + 1e-9)  # avoid log(0)
            weighted_log_rcrs.append(log_rcr * p.author_weight)

        mean_rcr_log = sum(weighted_log_rcrs) / len(weighted_log_rcrs)

        # 90th percentile: sort and pick index
        sorted_rcrs = sorted(weighted_log_rcrs)
        idx_90 = int(len(sorted_rcrs) * 0.9)
        idx_90 = min(idx_90, len(sorted_rcrs) - 1)
        top_rcr_log = sorted_rcrs[idx_90]

        return (mean_rcr_log, top_rcr_log, low_confidence, len(eligible))

    def compute_percentiles(
        self,
        raw_scores: list[tuple[str, float, float, bool, int]],
    ) -> dict[str, F1Score]:
        """Compute percentile rank for each candidate.

        Takes list of (uuid, mean_rcr_log, top_rcr_log, low_confidence, count).
        Percentile is based on composite: 0.6 * mean_rcr_log + 0.4 * top_rcr_log.
        """
        if not raw_scores:
            return {}

        # Compute composite for each candidate
        composites: list[
            tuple[str, float, float, float, bool, int]
        ] = []
        for uuid, mean_log, top_log, low_conf, count in raw_scores:
            composite = 0.6 * mean_log + 0.4 * top_log
            composites.append(
                (uuid, mean_log, top_log, composite, low_conf, count)
            )

        # Sort by composite to assign percentiles
        composites.sort(key=lambda x: x[3])

        n = len(composites)
        results: dict[str, F1Score] = {}
        for rank_idx, (
            uuid,
            mean_log,
            top_log,
            _comp,
            low_conf,
            count,
        ) in enumerate(composites):
            percentile = (rank_idx + 0.5) / n  # midpoint percentile
            results[uuid] = F1Score(
                mean_rcr_log=round(mean_log, 6),
                top_rcr_log=round(top_log, 6),
                percentile=round(percentile, 6),
                low_confidence=low_conf,
                eligible_paper_count=count,
            )

        return results
