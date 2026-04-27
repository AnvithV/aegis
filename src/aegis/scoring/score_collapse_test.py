"""Tests for score-collapse detection and MeSH expansion."""

from __future__ import annotations

from aegis.scoring.score_collapse import CollapseResult, ScoreCollapseHandler


def test_no_collapse() -> None:
    h = ScoreCollapseHandler()
    assert h.check_collapse([0.3, 0.5, 0.8]) is False


def test_all_below_floor() -> None:
    h = ScoreCollapseHandler()
    assert h.check_collapse([0.01, 0.02, 0.03]) is True


def test_empty_scores() -> None:
    h = ScoreCollapseHandler()
    assert h.check_collapse([]) is True


def test_custom_floor() -> None:
    h = ScoreCollapseHandler(floor=0.1)
    assert h.check_collapse([0.08, 0.09]) is True


def test_expand_mesh() -> None:
    h = ScoreCollapseHandler()
    expanded = h.expand_mesh(["D002289", "D008175"])
    assert "D009369" in expanded  # parent
    assert "D002289" in expanded  # original
    assert "D008175" in expanded  # original
    assert len(expanded) == len(set(expanded))  # deduplicated


def test_handle_collapse_returns_expanded() -> None:
    h = ScoreCollapseHandler()
    result = h.handle_collapse([0.01, 0.02], ["D002289", "D008175"])
    assert isinstance(result, CollapseResult)
    assert result.collapsed is True
    assert result.flag == "low_confidence_ranking"
    assert result.retry_count == 1
    assert "D009369" in result.expanded_mesh_terms


def test_make_cohort_fallback() -> None:
    h = ScoreCollapseHandler()
    result = h.make_cohort_fallback()
    assert result.collapsed is True
    assert result.flag == "cohort_fallback"
    assert result.retry_count == 2
    assert result.expanded_mesh_terms == []


def test_single_score_above_floor() -> None:
    h = ScoreCollapseHandler()
    assert h.check_collapse([0.01, 0.06]) is False
