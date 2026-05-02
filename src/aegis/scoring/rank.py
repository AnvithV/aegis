"""End-to-end Rank(c,q) wiring: I(c) * Q(c)^alpha * T(c,q)^beta * R(c,q)^gamma."""

from __future__ import annotations

from dataclasses import dataclass, field

from aegis.scoring.result_format import (
    ComponentBreakdown,
    ContributingArtifact,
    RankedCandidate,
    RankedList,
)

# Default exponents
DEFAULT_ALPHA: float = 0.7
DEFAULT_BETA: float = 1.0
DEFAULT_GAMMA: float = 0.4

MAX_TOP_ARTIFACTS: int = 3


@dataclass
class CandidateScoreInput:
    """Input data for scoring a single candidate."""

    candidate_uuid: str
    candidate_name: str
    linkage_confidence: float
    integrity_score: float
    quality_percentile: float
    topical_fit: float
    recency: float
    top_artifacts: list[ContributingArtifact] = field(
        default_factory=list,
    )
    evidence_trail: list[str] = field(default_factory=list)
    contact_email: str | None = None
    is_hard_zero: bool = False


class Ranker:
    """Score and rank candidates via the full Rank(c,q) formula."""

    def __init__(
        self,
        *,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        gamma: float = DEFAULT_GAMMA,
        weight_version: int = 1,
    ) -> None:
        self._alpha = alpha
        self._beta = beta
        self._gamma = gamma
        self._weight_version = weight_version

    def rank(
        self,
        query_mesh_terms: list[str],
        candidates: list[CandidateScoreInput],
        k: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> RankedList:
        """Score, filter, sort, and return the top-k candidates."""
        scored: list[tuple[float, ComponentBreakdown, CandidateScoreInput]] = (
            []
        )
        excluded = 0

        for c in candidates:
            if c.is_hard_zero or c.integrity_score == 0.0:
                excluded += 1
                continue

            q_powered = _safe_pow(c.quality_percentile, self._alpha)
            t_powered = _safe_pow(c.topical_fit, self._beta)
            r_powered = _safe_pow(c.recency, self._gamma)

            final = c.integrity_score * q_powered * t_powered * r_powered

            breakdown = ComponentBreakdown(
                integrity_score=round(c.integrity_score, 8),
                quality_prior=round(c.quality_percentile, 8),
                quality_prior_powered=round(q_powered, 8),
                topical_fit=round(c.topical_fit, 8),
                topical_fit_powered=round(t_powered, 8),
                recency=round(c.recency, 8),
                recency_powered=round(r_powered, 8),
                final_score=round(final, 8),
            )
            scored.append((final, breakdown, c))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Apply top-k limit
        if k is not None:
            scored = scored[:k]

        ranked_candidates: list[RankedCandidate] = []
        for rank_idx, (score, breakdown, c) in enumerate(scored, start=1):
            ranked_candidates.append(
                RankedCandidate(
                    rank=rank_idx,
                    candidate_uuid=c.candidate_uuid,
                    candidate_name=c.candidate_name,
                    linkage_confidence=c.linkage_confidence,
                    score=round(score, 8),
                    breakdown=breakdown,
                    top_artifacts=c.top_artifacts[:MAX_TOP_ARTIFACTS],
                    evidence_trail=c.evidence_trail,
                    contact_email=c.contact_email,
                )
            )

        return RankedList(
            query_mesh_terms=query_mesh_terms,
            cohort_size=len(candidates),
            result_count=len(ranked_candidates),
            candidates=ranked_candidates,
            excluded_count=excluded,
            weight_version=self._weight_version,
            exponents={
                "alpha": self._alpha,
                "beta": self._beta,
                "gamma": self._gamma,
            },
            metadata=metadata or {},
        )


def _safe_pow(base: float, exp: float) -> float:
    """Raise *base* to *exp*, treating non-positive base as 0."""
    if base <= 0.0:
        return 0.0
    result: float = base**exp
    return result
