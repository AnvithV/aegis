"""Regression test: synthetic apex recall must meet >= 80% threshold."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from aegis.observability.apex_recall import ApexRecallTracker, RecallResult


@pytest.fixture()
def tracker(tmp_path: Path) -> ApexRecallTracker:
    """Create an ApexRecallTracker backed by a temp DuckDB file."""
    db_path = str(tmp_path / "test_regression.duckdb")
    return ApexRecallTracker(db_path=db_path)


def test_synthetic_apex_recall_meets_threshold(
    tracker: ApexRecallTracker,
) -> None:
    """Synthetic queries all achieve >= 80% mean recall."""
    run_date = datetime.date(2024, 6, 15)
    queries = [
        ("nccn-nsclc-panel", ["a", "b", "c", "d", "e"]),
        ("nih-merit-nsclc", ["f", "g", "h"]),
        ("asco-yi-nsclc", ["i", "j", "k", "l"]),
    ]

    for qid, expected in queries:
        # Simulate returning most expected UUIDs (high recall)
        returned = expected[:]  # perfect recall
        recall, found, missed = tracker.compute_recall(
            expected, returned
        )
        tracker.record_result(
            RecallResult(
                query_id=qid,
                recall=recall,
                found_uuids=found,
                missed_uuids=missed,
                top_k=50,
                total_expected=len(expected),
                run_date=run_date,
            )
        )

    query_ids = [q[0] for q in queries]
    assert tracker.passes_threshold(query_ids, run_date, 0.80)
