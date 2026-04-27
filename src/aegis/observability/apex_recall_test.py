"""Tests for apex-list recall tracking."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from aegis.observability.apex_recall import (
    ApexQuery,
    ApexRecallTracker,
    RecallResult,
)


@pytest.fixture()
def tracker(tmp_path: Path) -> ApexRecallTracker:
    """Create an ApexRecallTracker backed by a temp DuckDB file."""
    db_path = str(tmp_path / "test_apex.duckdb")
    return ApexRecallTracker(db_path=db_path)


def test_recall_computation(tracker: ApexRecallTracker) -> None:
    """Recall computed correctly for partial overlap."""
    expected = ["a", "b", "c", "d"]
    returned = ["a", "b", "e", "f"]
    recall, found, missed = tracker.compute_recall(expected, returned)
    assert recall == 0.5
    assert found == ["a", "b"]
    assert missed == ["c", "d"]


def test_recall_perfect(tracker: ApexRecallTracker) -> None:
    """Perfect recall when all expected UUIDs are returned."""
    expected = ["a", "b", "c"]
    returned = ["a", "b", "c", "d", "e"]
    recall, found, missed = tracker.compute_recall(expected, returned)
    assert recall == 1.0
    assert found == ["a", "b", "c"]
    assert missed == []


def test_recall_empty_expected(tracker: ApexRecallTracker) -> None:
    """Empty expected set returns recall of 1.0."""
    recall, found, missed = tracker.compute_recall([], ["a", "b"])
    assert recall == 1.0
    assert found == []
    assert missed == []


def test_record_and_trend(tracker: ApexRecallTracker) -> None:
    """Recording results and checking trend works correctly."""
    d1 = datetime.date(2024, 6, 8)
    d2 = datetime.date(2024, 6, 15)

    result1 = RecallResult(
        query_id="q1",
        recall=0.90,
        found_uuids=["a", "b"],
        missed_uuids=["c"],
        top_k=50,
        total_expected=3,
        run_date=d1,
    )
    result2 = RecallResult(
        query_id="q1",
        recall=0.80,
        found_uuids=["a", "b"],
        missed_uuids=["c"],
        top_k=50,
        total_expected=3,
        run_date=d2,
    )
    tracker.record_result(result1)
    tracker.record_result(result2)

    trend = tracker.get_weekly_trend("q1", d2, d1)
    assert trend is not None
    assert trend.current_recall == 0.80
    assert trend.previous_recall == 0.90
    assert abs(trend.delta - (-0.10)) < 1e-9
    assert trend.alert is True  # delta < -0.05


def test_passes_threshold(tracker: ApexRecallTracker) -> None:
    """passes_threshold checks mean recall against threshold."""
    d = datetime.date(2024, 6, 15)
    for qid, recall in [("q1", 0.90), ("q2", 0.85), ("q3", 0.70)]:
        tracker.record_result(
            RecallResult(
                query_id=qid,
                recall=recall,
                found_uuids=[],
                missed_uuids=[],
                top_k=50,
                total_expected=0,
                run_date=d,
            )
        )

    # Mean = (0.90 + 0.85 + 0.70) / 3 = 0.8167
    assert tracker.passes_threshold(["q1", "q2", "q3"], d, 0.80)
    # With higher threshold
    assert not tracker.passes_threshold(["q1", "q2", "q3"], d, 0.85)


def test_load_queries_from_yaml(
    tracker: ApexRecallTracker, tmp_path: Path
) -> None:
    """load_apex_queries parses YAML into ApexQuery objects."""
    yaml_content = """\
queries:
  - query_id: test-query-1
    description: "Test query"
    mesh_terms:
      - "Term A"
      - "Term B"
    expected_uuids: ["uuid-1", "uuid-2"]
    top_k: 25
  - query_id: test-query-2
    description: "Another test"
    mesh_terms:
      - "Term C"
    expected_uuids: []
    top_k: 50
"""
    yaml_path = tmp_path / "test_queries.yaml"
    yaml_path.write_text(yaml_content)

    queries = tracker.load_apex_queries(str(yaml_path))
    assert len(queries) == 2
    assert isinstance(queries[0], ApexQuery)
    assert queries[0].query_id == "test-query-1"
    assert queries[0].mesh_terms == ["Term A", "Term B"]
    assert queries[0].expected_uuids == ["uuid-1", "uuid-2"]
    assert queries[0].top_k == 25
    assert queries[1].query_id == "test-query-2"
    assert queries[1].expected_uuids == []
