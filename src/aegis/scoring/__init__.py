"""Aegis scoring engine — quality prior, topical fit, recency, and ranking."""

from __future__ import annotations

from aegis.scoring.cache import (
    CachedScore,
    CacheKey,
    CacheStats,
    ScoreCache,
)
from aegis.scoring.clinician_weights import load_clinician_weights
from aegis.scoring.candidate_vector import (
    ArtifactWeight,
    CandidateVectorBuilder,
    QueryVectorBuilder,
    SparseVector,
)
from aegis.scoring.drug_discovery_weights import load_drug_discovery_weights
from aegis.scoring.f1_rcr import F1Computer, F1Score
from aegis.scoring.f2_funding import F2Computer, F2Score
from aegis.scoring.f3_leadership import F3Computer, F3Score
from aegis.scoring.f4_apex import F4Computer, F4Score
from aegis.scoring.f5_translational import F5Computer, F5Score
from aegis.scoring.f6_lineage import F6Computer, F6Score
from aegis.scoring.f7_clinician import F7Computer, F7Score
from aegis.scoring.quality_prior import (
    QualityPrior,
    QualityScore,
    WeightVector,
    load_weight_vector,
)
from aegis.scoring.rank import CandidateScoreInput, Ranker
from aegis.scoring.recency import Recency, RecencyArtifact
from aegis.scoring.result_format import (
    ComponentBreakdown,
    ContributingArtifact,
    RankedCandidate,
    RankedList,
)
from aegis.scoring.score_collapse import CollapseResult, ScoreCollapseHandler
from aegis.scoring.specialty_classifier import (
    ArtifactMixFeatures,
    Specialty,
    SpecialtyClassifier,
    SpecialtyDistribution,
)
from aegis.scoring.multi_specialty import MultiSpecialtyRouter
from aegis.scoring.specialty_reassignment import (
    ReassignmentEntry,
    ReassignmentReport,
    SpecialtyReassigner,
)
from aegis.scoring.specialty_flag import (
    SpecialtyAmbiguityFlagger,
    SpecialtyFlagResult,
)
from aegis.scoring.topical_fit import TopicalFit
from aegis.scoring.variance import Bootstrap, BootstrapInput, ScoreBand

__all__ = [
    "ArtifactWeight",
    "Bootstrap",
    "BootstrapInput",
    "CacheKey",
    "CacheStats",
    "CachedScore",
    "CandidateScoreInput",
    "CandidateVectorBuilder",
    "CollapseResult",
    "ComponentBreakdown",
    "ContributingArtifact",
    "F1Computer",
    "F1Score",
    "F2Computer",
    "F2Score",
    "F3Computer",
    "F3Score",
    "F4Computer",
    "F4Score",
    "F5Computer",
    "F5Score",
    "F6Computer",
    "F6Score",
    "F7Computer",
    "F7Score",
    "QualityPrior",
    "QualityScore",
    "QueryVectorBuilder",
    "Ranker",
    "RankedCandidate",
    "RankedList",
    "Recency",
    "RecencyArtifact",
    "ScoreBand",
    "ScoreCache",
    "ScoreCollapseHandler",
    "Specialty",
    "SpecialtyClassifier",
    "SpecialtyDistribution",
    "SparseVector",
    "ArtifactMixFeatures",
    "SpecialtyAmbiguityFlagger",
    "SpecialtyFlagResult",
    "TopicalFit",
    "WeightVector",
    "MultiSpecialtyRouter",
    "ReassignmentEntry",
    "ReassignmentReport",
    "SpecialtyReassigner",
    "load_clinician_weights",
    "load_drug_discovery_weights",
    "load_weight_vector",
]
