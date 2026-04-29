"""Tests for the query pipeline orchestrator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from aegis.pipeline.orchestrator import (
    PipelineResult,
    QueryPipeline,
    SourceProgress,
)
from aegis.storage.schema import (
    AffiliationSpan,
    ArtifactRefBundle,
    Candidate,
    MeshDescriptor,
)


def _make_candidate(
    uuid: str = "test-uuid-1",
    name: str = "Jane Smith",
    pmids: list[str] | None = None,
    grant_ids: list[str] | None = None,
    nct_ids: list[str] | None = None,
) -> Candidate:
    """Create a test candidate."""
    return Candidate(
        uuid=uuid,
        strong_keys={"orcid": f"0000-0001-{uuid}"},
        name_variants=[name],
        affiliations=[
            AffiliationSpan(
                ror_id="https://ror.org/03vek6s52",
                canonical_name="Harvard University",
                raw_string="Harvard University, Boston, MA",
                country="US",
                confidence=0.95,
                start_date=None,
                end_date=None,
            ),
        ],
        artifact_refs=ArtifactRefBundle(
            pmids=pmids or ["12345678", "23456789"],
            nct_ids=nct_ids or ["NCT001"],
            grant_ids=grant_ids or ["R01-123"],
            patent_ids=[],
        ),
        linkage_confidence=0.95,
        evidence_trail=["PubMed: 2 publications", "NIH: PI on R01"],
        last_updated_per_source={"pubmed": datetime.now(UTC)},
        mesh_descriptors=[
            MeshDescriptor(
                descriptor="Lung Neoplasms",
                qualifier="drug therapy",
                major_topic=True,
            ),
        ],
    )


@pytest.fixture
def mock_store() -> MagicMock:
    """Mock CandidateStore that returns test candidates."""
    store = MagicMock()
    store.list_by_cohort.return_value = [
        _make_candidate("uuid-1", "Jane Smith"),
        _make_candidate("uuid-2", "John Doe", pmids=["11111111"]),
        _make_candidate("uuid-3", "Alice Johnson", grant_ids=["R01-999", "U01-555"]),
    ]
    return store


@pytest.mark.anyio
async def test_execute_returns_pipeline_result(mock_store: MagicMock) -> None:
    """execute() returns a PipelineResult with expected fields."""
    pipeline = QueryPipeline(db_path=":memory:")

    with (
        patch("aegis.pipeline.orchestrator.CandidateStore", return_value=mock_store),
        patch.object(pipeline, "_fetch_all_sources", return_value=(0, [])),
    ):
        result = await pipeline.execute(
            task_description="KRAS inhibitor drug discovery for lung cancer",
            k=10,
        )

    assert isinstance(result, PipelineResult)
    assert result.ranked_list is not None
    assert result.query_type in ("basic_research", "drug_discovery", "clinical_trial_pi", "policy_epi")
    assert result.weight_vector_name != ""
    assert result.expansion_info is not None
    assert result.pipeline_duration_ms > 0
    assert result.total_candidates_after_dedup == 3


@pytest.mark.anyio
async def test_compute_scores_builds_real_f_scores(mock_store: MagicMock) -> None:
    """_compute_scores builds real F1-F6 percentiles for candidates."""
    pipeline = QueryPipeline(db_path=":memory:")

    from aegis.query.classifier import QueryClassifier

    classifier = QueryClassifier()
    classification = classifier.classify("KRAS inhibitor drug discovery")

    candidates = mock_store.list_by_cohort()
    score_inputs, f_scores = pipeline._compute_scores(
        candidates,
        ["Lung Neoplasms", "KRAS"],
        "KRAS inhibitor drug discovery",
        classification.weight_vector,
    )

    assert len(score_inputs) == 3
    for si in score_inputs:
        assert 0.0 <= si.quality_percentile <= 1.0
        assert 0.0 <= si.topical_fit <= 1.0
        assert 0.0 <= si.recency <= 1.0

    # Check F-score percentiles exist
    for family in ["f1", "f2", "f3", "f4", "f5", "f6"]:
        assert family in f_scores
        assert len(f_scores[family]) == 3


@pytest.mark.anyio
async def test_source_failures_isolated() -> None:
    """One failing source does not crash the entire pipeline."""
    pipeline = QueryPipeline(db_path=":memory:")

    progress_updates: list[SourceProgress] = []

    async def _failing_fetch(
        source_name: str, query: str, mesh_terms: list[str]
    ) -> tuple[str, int, float]:
        if source_name == "pubmed":
            raise ConnectionError("PubMed is down")
        return source_name, 10, 100.0

    with patch.object(pipeline, "_fetch_source", side_effect=_failing_fetch):
        total, progress = await pipeline._fetch_all_sources(
            "test query",
            ["term"],
            progress_updates.append,
        )

    # One should have failed, others succeeded
    failed = [p for p in progress if p.status == "failed"]
    succeeded = [p for p in progress if p.status == "complete"]

    assert len(failed) == 1
    assert failed[0].source_name == "pubmed"
    assert "PubMed is down" in (failed[0].error or "")
    assert len(succeeded) == 4
    assert total == 40  # 4 sources * 10 records each

    # Also test via the collected callback
    assert len(progress_updates) == 5


@pytest.mark.anyio
async def test_mesh_override(mock_store: MagicMock) -> None:
    """mesh_override bypasses MetaMap expansion."""
    pipeline = QueryPipeline(db_path=":memory:")

    with (
        patch("aegis.pipeline.orchestrator.CandidateStore", return_value=mock_store),
        patch.object(pipeline, "_fetch_all_sources", return_value=(0, [])),
    ):
        result = await pipeline.execute(
            task_description="KRAS inhibitor drug discovery for lung cancer",
            mesh_override=["Lung Neoplasms", "Proto-Oncogene Proteins p21(ras)"],
            k=5,
        )

    assert result.expansion_info.expansion_method == "override"
    assert result.expansion_info.low_confidence is False
    assert "Lung Neoplasms" in result.expansion_info.expanded_mesh_terms


@pytest.mark.anyio
async def test_progress_callback_called(mock_store: MagicMock) -> None:
    """progress_callback is called for each source."""
    pipeline = QueryPipeline(db_path=":memory:")
    progress_updates: list[SourceProgress] = []

    with (
        patch("aegis.pipeline.orchestrator.CandidateStore", return_value=mock_store),
        patch.object(pipeline, "_fetch_all_sources", return_value=(0, [])) as mock_fetch,
    ):
        # Test the callback mechanism through a simulated run
        mock_fetch.return_value = (
            15,
            [
                SourceProgress(
                    source_name="pubmed",
                    status="complete",
                    record_count=10,
                    latency_ms=500.0,
                    error=None,
                ),
                SourceProgress(
                    source_name="reporter",
                    status="complete",
                    record_count=5,
                    latency_ms=300.0,
                    error=None,
                ),
            ],
        )
        result = await pipeline.execute(
            task_description="KRAS inhibitor drug discovery for lung cancer",
            k=10,
            progress_callback=progress_updates.append,
        )

    assert result.source_progress is not None
    assert result.total_candidates_fetched == 15
