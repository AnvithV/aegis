"""Tests for result formatter with evidence trails and variance bands."""

from __future__ import annotations

from datetime import UTC, datetime

from aegis.api.formatter import ResultFormatter, _build_artifact_link
from aegis.api.schemas import ExpansionInfo, StalenessWarning
from aegis.scoring.result_format import (
    ComponentBreakdown,
    ContributingArtifact,
    RankedCandidate,
    RankedList,
)
from aegis.scoring.variance import ScoreBand


def _make_breakdown(score: float = 0.8) -> ComponentBreakdown:
    return ComponentBreakdown(
        integrity_score=1.0,
        quality_prior=0.9,
        quality_prior_powered=0.93,
        topical_fit=0.8,
        topical_fit_powered=0.8,
        recency=0.7,
        recency_powered=0.84,
        final_score=score,
    )


def _make_candidate(rank: int, uuid: str = "") -> RankedCandidate:
    cid = uuid or f"uuid-{rank}"
    return RankedCandidate(
        rank=rank,
        candidate_uuid=cid,
        candidate_name=f"Dr. Test {rank}",
        linkage_confidence=0.95,
        score=0.9 - rank * 0.05,
        breakdown=_make_breakdown(0.9 - rank * 0.05),
        top_artifacts=[
            ContributingArtifact(
                artifact_type="pmid",
                identifier=f"1234567{rank}",
                title=f"Paper {rank}",
                contribution_score=0.3,
            )
        ],
        evidence_trail=[f"PubMed: 1234567{rank}"],
    )


def _make_ranked_list(n: int = 2) -> RankedList:
    return RankedList(
        query_mesh_terms=["Neoplasms"],
        cohort_size=100,
        result_count=n,
        candidates=[_make_candidate(i + 1) for i in range(n)],
        excluded_count=5,
        weight_version=1,
        exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
        metadata={},
    )


def _make_expansion_info() -> ExpansionInfo:
    return ExpansionInfo(
        original_query="JAK2 inhibitors",
        expanded_mesh_terms=["Neoplasms", "Protein Kinases"],
        expansion_method="llm",
    )


def test_build_artifact_link_pmid() -> None:
    link = _build_artifact_link("pmid", "12345678", "Test Paper", 0.3)
    assert link.url == "https://pubmed.ncbi.nlm.nih.gov/12345678"


def test_build_artifact_link_nct() -> None:
    link = _build_artifact_link("nct_id", "NCT00000001", "Trial", 0.2)
    assert "clinicaltrials.gov" in link.url


def test_build_artifact_link_unknown_type() -> None:
    link = _build_artifact_link("other", "xyz", "Unknown", 0.1)
    assert "crossref.org" in link.url


def test_format_basic() -> None:
    formatter = ResultFormatter()
    ranked = _make_ranked_list(2)
    response = formatter.format(
        ranked=ranked, expansion_info=_make_expansion_info()
    )
    assert len(response.candidates) == 2
    assert response.query_id != ""
    assert response.weight_version == 1


def test_format_with_variance_bands() -> None:
    formatter = ResultFormatter()
    ranked = _make_ranked_list(2)
    bands = {
        "uuid-1": ScoreBand(low=0.7, high=0.95, median=0.85, n_samples=200),
    }
    response = formatter.format(
        ranked=ranked,
        expansion_info=_make_expansion_info(),
        variance_bands=bands,
    )
    assert response.candidates[0].variance_band is not None
    assert response.candidates[0].variance_band.low == 0.7
    assert response.candidates[1].variance_band is None


def test_format_with_integrity_disclosures() -> None:
    formatter = ResultFormatter()
    ranked = _make_ranked_list(2)
    discounts = {
        "uuid-1": [
            {
                "discount_type": "predatory_load",
                "factor": 0.8,
                "detail": "predatory load 0.15",
            }
        ],
    }
    response = formatter.format(
        ranked=ranked,
        expansion_info=_make_expansion_info(),
        soft_discounts=discounts,
    )
    assert len(response.candidates[0].integrity_disclosures) == 1
    assert response.candidates[0].integrity_disclosures[0].factor == 0.8


def test_format_with_staleness_warnings() -> None:
    formatter = ResultFormatter()
    ranked = _make_ranked_list(1)
    now = datetime.now(UTC)
    warnings = [
        StalenessWarning(
            source="retraction_watch",
            last_updated=now,
            sla_hours=6.0,
            message="Data may be stale",
        )
    ]
    response = formatter.format(
        ranked=ranked,
        expansion_info=_make_expansion_info(),
        staleness_warnings=warnings,
    )
    assert len(response.staleness_warnings) == 1
    assert response.staleness_warnings[0].source == "retraction_watch"


def test_format_snapshot_shape() -> None:
    formatter = ResultFormatter()
    ranked = _make_ranked_list(1)
    response = formatter.format(
        ranked=ranked, expansion_info=_make_expansion_info()
    )
    json_str = response.model_dump_json()
    for key in [
        "query_id",
        "candidates",
        "expansion_info",
        "weight_version",
        "integrity_rule_version",
    ]:
        assert key in json_str


def test_format_empty_ranked_list() -> None:
    formatter = ResultFormatter()
    ranked = RankedList(
        query_mesh_terms=[],
        cohort_size=0,
        result_count=0,
        candidates=[],
        excluded_count=0,
        weight_version=1,
        exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
        metadata={},
    )
    response = formatter.format(
        ranked=ranked, expansion_info=_make_expansion_info()
    )
    assert response.candidates == []


def test_format_preserves_rank_order() -> None:
    formatter = ResultFormatter()
    ranked = _make_ranked_list(5)
    response = formatter.format(
        ranked=ranked, expansion_info=_make_expansion_info()
    )
    ranks = [c.rank for c in response.candidates]
    assert ranks == [1, 2, 3, 4, 5]
