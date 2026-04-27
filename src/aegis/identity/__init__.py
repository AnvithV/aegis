"""Identity resolution — strong-key and probabilistic linkage."""

from aegis.identity.contradictions import (
    ContradictionHandler,
    ContradictionRecord,
)
from aegis.identity.cross_population_merge import (
    CrossPopulationMerger,
    MergeCandidate,
    MergeResult,
)
from aegis.identity.probabilistic import LinkResult, ProbabilisticLinker
from aegis.identity.review_queue import ReviewDecision, ReviewItem, ReviewQueue
from aegis.identity.ror import RorMatch, RorResolver
from aegis.identity.strong_key import (
    CandidateRef,
    CandidateRegistry,
    StrongKeyResolver,
)

__all__ = [
    "CandidateRef",
    "CandidateRegistry",
    "ContradictionHandler",
    "ContradictionRecord",
    "CrossPopulationMerger",
    "MergeCandidate",
    "MergeResult",
    "LinkResult",
    "ProbabilisticLinker",
    "ReviewDecision",
    "ReviewItem",
    "ReviewQueue",
    "RorMatch",
    "RorResolver",
    "StrongKeyResolver",
]
