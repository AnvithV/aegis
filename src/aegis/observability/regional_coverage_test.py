"""Tests for regional coverage diagnostics (no DuckDB, mock-based)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from aegis.observability.regional_coverage import (
    RegionalCoverageDashboard,
    build_regional_caveat,
)
from aegis.sources.non_us_grants import Region
from aegis.storage.schema import (
    AffiliationSpan,
    ArtifactRefBundle,
    Candidate,
)


def _make_candidate(
    uuid: str,
    country: str | None,
    linkage_confidence: float = 0.9,
    pmids: list[str] | None = None,
    grant_ids: list[str] | None = None,
) -> Candidate:
    """Build a mock Candidate with a single affiliation."""
    return Candidate(
        uuid=uuid,
        strong_keys={},
        name_variants=["Test Person"],
        affiliations=[
            AffiliationSpan(
                ror_id=None,
                canonical_name="Test Institution",
                raw_string="Test Institution",
                country=country,
                confidence=1.0,
                start_date=date(2020, 1, 1),
                end_date=date(2024, 1, 1),
            ),
        ],
        artifact_refs=ArtifactRefBundle(
            pmids=pmids or ["12345"],
            nct_ids=[],
            grant_ids=grant_ids or [],
            patent_ids=[],
        ),
        linkage_confidence=linkage_confidence,
        evidence_trail=[],
        last_updated_per_source={},
        mesh_descriptors=[],
    )


def _mock_store(candidates: list[Candidate]) -> MagicMock:
    """Create a mock CandidateStore with given candidates."""
    store = MagicMock()
    store.list_by_cohort.return_value = candidates
    store.get_by_uuid.side_effect = lambda uid: next(
        (c for c in candidates if c.uuid == uid), None
    )
    return store


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_compute_basic() -> None:
    """Per-region counts and percentages are computed correctly."""
    candidates = [
        _make_candidate("1", "US"),
        _make_candidate("2", "US"),
        _make_candidate("3", "GB"),
        _make_candidate("4", "JP"),
        _make_candidate("5", "CN"),
    ]
    store = _mock_store(candidates)
    dashboard = RegionalCoverageDashboard(store)
    metrics = dashboard.compute()

    assert metrics.total_candidates == 5
    assert metrics.per_region_count[Region.US.value] == 2
    assert metrics.per_region_count[Region.UK.value] == 1
    assert metrics.per_region_count[Region.JAPAN.value] == 1
    assert metrics.per_region_count[Region.CHINA.value] == 1


def test_non_us_ratio() -> None:
    """Non-US ratio is computed correctly."""
    candidates = [
        _make_candidate("1", "US"),
        _make_candidate("2", "US"),
        _make_candidate("3", "GB"),
        _make_candidate("4", "FR"),
        _make_candidate("5", "JP"),
    ]
    store = _mock_store(candidates)
    dashboard = RegionalCoverageDashboard(store)
    metrics = dashboard.compute()

    assert metrics.non_us_ratio == 0.6  # 3 out of 5 are non-US


def test_geographic_bias_detection() -> None:
    """Cohort with >75% US triggers is_geographically_biased=True."""
    candidates = [
        _make_candidate("1", "US"),
        _make_candidate("2", "US"),
        _make_candidate("3", "US"),
        _make_candidate("4", "US"),
        _make_candidate("5", "GB"),
    ]
    store = _mock_store(candidates)
    dashboard = RegionalCoverageDashboard(store)
    metrics = dashboard.compute()

    assert metrics.is_geographically_biased is True
    assert metrics.dominant_region == Region.US.value
    assert metrics.dominant_region_pct == 80.0


def test_regional_caveat_text() -> None:
    """Caveat text is set when biased."""
    candidates = [
        _make_candidate(str(i), "US") for i in range(8)
    ] + [
        _make_candidate("9", "GB"),
    ]
    store = _mock_store(candidates)
    dashboard = RegionalCoverageDashboard(store)
    metrics = dashboard.compute()

    assert metrics.is_geographically_biased is True
    assert metrics.regional_caveat is not None
    assert ">75%" in metrics.regional_caveat
    assert Region.US.value in metrics.regional_caveat


def test_no_caveat_when_balanced() -> None:
    """No caveat when cohort is geographically balanced."""
    candidates = [
        _make_candidate("1", "US"),
        _make_candidate("2", "US"),
        _make_candidate("3", "GB"),
        _make_candidate("4", "FR"),
        _make_candidate("5", "JP"),
        _make_candidate("6", "CN"),
        _make_candidate("7", "CA"),
        _make_candidate("8", "BR"),
    ]
    store = _mock_store(candidates)
    dashboard = RegionalCoverageDashboard(store)
    metrics = dashboard.compute()

    assert metrics.is_geographically_biased is False
    assert metrics.regional_caveat is None


def test_build_regional_caveat() -> None:
    """build_regional_caveat produces correct format."""
    caveat = build_regional_caveat("US", 82.5)
    assert ">75%" in caveat
    assert "US" in caveat
    assert "82.5%" in caveat
    assert "regional weighting" in caveat


def test_empty_cohort() -> None:
    """Empty cohort returns zeros."""
    store = _mock_store([])
    dashboard = RegionalCoverageDashboard(store)
    metrics = dashboard.compute()

    assert metrics.total_candidates == 0
    assert metrics.non_us_ratio == 0.0
    assert metrics.is_geographically_biased is False
    assert metrics.regional_caveat is None


def test_china_coverage_caveat() -> None:
    """Chinese candidates trigger NSFC coverage caveat."""
    candidates = [
        _make_candidate("1", "CN"),
        _make_candidate("2", "US"),
    ]
    store = _mock_store(candidates)
    dashboard = RegionalCoverageDashboard(store)
    metrics = dashboard.compute()

    assert len(metrics.coverage_caveats) > 0
    assert any("NSFC" in c for c in metrics.coverage_caveats)
