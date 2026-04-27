"""Tests for coverage diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aegis.observability.coverage import CoverageDiagnostics, CoverageMetrics
from aegis.storage.schema import ArtifactRefBundle, Candidate


def _make_candidate(
    uuid: str,
    strong_keys: dict[str, str] | None = None,
    pmids: list[str] | None = None,
    nct_ids: list[str] | None = None,
    grant_ids: list[str] | None = None,
    linkage_confidence: float = 0.8,
) -> Candidate:
    return Candidate(
        uuid=uuid,
        strong_keys=strong_keys or {},
        name_variants=["Test Person"],
        affiliations=[],
        artifact_refs=ArtifactRefBundle(
            pmids=pmids or [],
            nct_ids=nct_ids or [],
            grant_ids=grant_ids or [],
        ),
        linkage_confidence=linkage_confidence,
        evidence_trail=[],
        last_updated_per_source={},
        mesh_descriptors=[],
    )


def _mock_store(candidates: list[Candidate]) -> MagicMock:
    store = MagicMock()
    store.list_by_cohort.return_value = candidates
    store.get_by_uuid.side_effect = lambda u: next(
        (c for c in candidates if c.uuid == u), None
    )
    return store


class TestComputeAllMetrics:
    def test_compute_all_metrics(self) -> None:
        candidates = [
            _make_candidate(
                "a",
                strong_keys={"orcid": "0000-0001"},
                pmids=["1", "2"],
                nct_ids=["NCT1"],
                grant_ids=["G1"],
                linkage_confidence=0.9,
            ),
            _make_candidate(
                "b",
                strong_keys={"era_commons": "ERA1"},
                pmids=["3"],
                linkage_confidence=0.75,
            ),
            _make_candidate(
                "c",
                pmids=["4"],
                linkage_confidence=0.4,
            ),
            _make_candidate(
                "d",
                strong_keys={"orcid": "0000-0002"},
                pmids=["5", "6", "7"],
                nct_ids=["NCT2"],
                grant_ids=["G2"],
                linkage_confidence=0.85,
            ),
        ]
        store = _mock_store(candidates)
        diag = CoverageDiagnostics(store)
        metrics = diag.compute()

        assert metrics.total_candidates == 4
        assert metrics.strong_key_pct == 75.0
        assert metrics.probabilistic_linkage_pct == 75.0
        assert metrics.per_source_pct["pubmed"] == 100.0
        assert metrics.thin_record_pct > 0


class TestStrongKeyPercentage:
    def test_strong_key_percentage(self) -> None:
        candidates = [
            _make_candidate("a", strong_keys={"orcid": "0000-0001"}),
            _make_candidate("b"),
            _make_candidate("c"),
            _make_candidate("d", strong_keys={"era_commons": "ERA1"}),
        ]
        store = _mock_store(candidates)
        diag = CoverageDiagnostics(store)
        metrics = diag.compute()
        assert metrics.strong_key_pct == 50.0


class TestThinRecordDetection:
    def test_thin_record_detection(self) -> None:
        candidates = [
            _make_candidate("a", pmids=["1"]),  # 1 artifact => thin
            _make_candidate("b", pmids=["1", "2"], nct_ids=["N1"]),  # 3 => not thin
            _make_candidate("c"),  # 0 artifacts => thin
        ]
        store = _mock_store(candidates)
        diag = CoverageDiagnostics(store)
        metrics = diag.compute()
        # 2 of 3 candidates are thin
        assert metrics.thin_record_pct == pytest.approx(66.67, abs=0.01)


class TestPercentilesCorrect:
    def test_percentiles_correct(self) -> None:
        # 20 candidates with linearly spaced confidences
        candidates = [
            _make_candidate(
                str(i), linkage_confidence=round(i / 19, 4)
            )
            for i in range(20)
        ]
        store = _mock_store(candidates)
        diag = CoverageDiagnostics(store)
        metrics = diag.compute()

        # p5 should be close to 0.05, p50 close to 0.5, p95 close to 0.95
        assert metrics.linkage_confidence_p5 < 0.15
        assert 0.35 < metrics.linkage_confidence_p50 < 0.65
        assert metrics.linkage_confidence_p95 > 0.85


class TestHtmlReportGenerated:
    def test_html_report_generated(self) -> None:
        candidates = [
            _make_candidate("a", pmids=["1", "2", "3"]),
        ]
        store = _mock_store(candidates)
        diag = CoverageDiagnostics(store)
        metrics = diag.compute()
        html = diag.generate_html_report(metrics)

        assert "<!DOCTYPE html>" in html
        assert "Coverage Diagnostics" in html
        assert "pubmed" in html


class TestCompareDetectsDrift:
    def test_compare_detects_drift(self) -> None:
        prev = CoverageMetrics(
            total_candidates=100,
            strong_key_pct=60.0,
            probabilistic_linkage_pct=70.0,
            per_source_pct={"pubmed": 80.0, "reporter": 50.0, "ctgov": 30.0},
            thin_record_pct=20.0,
            linkage_confidence_p5=0.3,
            linkage_confidence_p50=0.6,
            linkage_confidence_p95=0.9,
        )
        curr = CoverageMetrics(
            total_candidates=110,
            strong_key_pct=65.0,
            probabilistic_linkage_pct=72.0,
            per_source_pct={"pubmed": 85.0, "reporter": 48.0, "ctgov": 35.0},
            thin_record_pct=18.0,
            linkage_confidence_p5=0.32,
            linkage_confidence_p50=0.62,
            linkage_confidence_p95=0.92,
        )
        store = _mock_store([])
        diag = CoverageDiagnostics(store)
        deltas = diag.compare(curr, prev)

        assert deltas["strong_key_pct"] == 5.0
        assert deltas["probabilistic_linkage_pct"] == 2.0
        assert deltas["thin_record_pct"] == -2.0
        assert deltas["per_source_pubmed"] == 5.0
        assert deltas["per_source_reporter"] == -2.0


class TestRegressionStrongKeyCoverage:
    def test_regression_strong_key_coverage(self) -> None:
        """Regression guard: strong_key_pct must handle 0 candidates."""
        store = _mock_store([])
        diag = CoverageDiagnostics(store)
        metrics = diag.compute()
        assert metrics.total_candidates == 0
        assert metrics.strong_key_pct == 0.0
