"""Tests for contestability endpoint and workflow."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from aegis.api.contestability import (
    ContestabilityQueue,
    ContestCategory,
    ContestPriority,
    ContestStatus,
    ContestSubmission,
)


@pytest.fixture()
def queue(tmp_path: Path) -> Generator[ContestabilityQueue]:
    db_path = str(tmp_path / "contest_test.duckdb")
    q = ContestabilityQueue(db_path=db_path)
    yield q
    q.close()


def _submit_default(
    q: ContestabilityQueue,
    *,
    candidate_uuid: str = "cand-1",
    category: ContestCategory = ContestCategory.affiliation_error,
) -> ContestSubmission:
    return q.submit(
        candidate_uuid=candidate_uuid,
        category=category,
        description="My affiliation history is incorrect and needs correction.",
        evidence={"correct_affiliation": "MIT"},
        verified_via="orcid",
        requester_id="0000-0001-2345-6789",
    )


def test_submit_contest(queue: ContestabilityQueue) -> None:
    sub = _submit_default(queue)
    assert sub.priority == ContestPriority.elevated
    assert sub.status == ContestStatus.submitted
    assert sub.contest_id is not None


def test_next_for_review(queue: ContestabilityQueue) -> None:
    sub1 = _submit_default(queue, candidate_uuid="cand-1")
    _submit_default(queue, candidate_uuid="cand-2")
    item = queue.next_for_review()
    assert item is not None
    assert item.contest_id == sub1.contest_id
    assert item.status == ContestStatus.in_review


def test_decide_accepted(queue: ContestabilityQueue) -> None:
    sub = _submit_default(queue)
    queue.next_for_review()
    decision = queue.decide(
        contest_id=sub.contest_id,
        reviewer_id="reviewer-1",
        accepted=True,
        reasoning="Verified affiliation correction",
        actions_taken=["updated affiliation"],
    )
    assert decision.accepted is True
    updated = queue.get_submission(sub.contest_id)
    assert updated is not None
    assert updated.status == ContestStatus.resolved_accepted


def test_decide_rejected(queue: ContestabilityQueue) -> None:
    sub = _submit_default(queue)
    decision = queue.decide(
        contest_id=sub.contest_id,
        reviewer_id="reviewer-1",
        accepted=False,
        reasoning="Insufficient evidence",
    )
    assert decision.accepted is False
    updated = queue.get_submission(sub.contest_id)
    assert updated is not None
    assert updated.status == ContestStatus.resolved_rejected


def test_get_by_candidate(queue: ContestabilityQueue) -> None:
    _submit_default(queue, candidate_uuid="cand-1")
    _submit_default(queue, candidate_uuid="cand-1")
    _submit_default(queue, candidate_uuid="cand-2")
    summaries = queue.get_by_candidate("cand-1")
    assert len(summaries) == 2


def test_pending_count(queue: ContestabilityQueue) -> None:
    for i in range(5):
        sub = _submit_default(queue, candidate_uuid=f"cand-{i}")
        if i < 2:
            queue.decide(
                contest_id=sub.contest_id,
                reviewer_id="reviewer-1",
                accepted=True,
                reasoning="OK",
            )
    assert queue.pending_count() == 3


def test_priority_ordering(queue: ContestabilityQueue) -> None:
    sub_elevated = _submit_default(queue, candidate_uuid="cand-elevated")
    sub_normal = _submit_default(queue, candidate_uuid="cand-normal")
    # Manually downgrade the second submission to normal priority
    queue._conn.execute(
        "UPDATE contest_submissions SET priority = 'normal' WHERE contest_id = ?",
        [sub_normal.contest_id],
    )
    item = queue.next_for_review()
    assert item is not None
    assert item.contest_id == sub_elevated.contest_id


def test_append_only_decisions(queue: ContestabilityQueue) -> None:
    sub = _submit_default(queue)
    queue.decide(
        contest_id=sub.contest_id,
        reviewer_id="reviewer-1",
        accepted=False,
        reasoning="First review: insufficient evidence",
    )
    queue.decide(
        contest_id=sub.contest_id,
        reviewer_id="reviewer-2",
        accepted=True,
        reasoning="Second review: evidence verified",
    )
    decisions = queue.get_decisions(sub.contest_id)
    assert len(decisions) == 2


def test_stats(queue: ContestabilityQueue) -> None:
    for i in range(5):
        sub = _submit_default(queue, candidate_uuid=f"cand-{i}")
        if i < 2:
            queue.decide(
                contest_id=sub.contest_id,
                reviewer_id="reviewer-1",
                accepted=True,
                reasoning="OK",
            )
        elif i == 2:
            queue.decide(
                contest_id=sub.contest_id,
                reviewer_id="reviewer-1",
                accepted=False,
                reasoning="Rejected",
            )
    stats = queue.get_stats()
    assert stats.total_submitted == 5
    assert stats.total_accepted == 2
    assert stats.total_rejected == 1
    assert stats.total_resolved == 3


def test_contest_submission_model() -> None:
    from datetime import UTC, datetime

    sub = ContestSubmission(
        contest_id="abc123",
        candidate_uuid="cand-1",
        category=ContestCategory.affiliation_error,
        description="Test",
        evidence={},
        verified_via="orcid",
        requester_id="0000-0001-2345-6789",
        submitted_at=datetime.now(tz=UTC),
        status=ContestStatus.submitted,
        priority=ContestPriority.elevated,
    )
    with pytest.raises(Exception):  # noqa: B017
        sub.contest_id = "xyz"


def test_get_submission(queue: ContestabilityQueue) -> None:
    sub = _submit_default(queue)
    fetched = queue.get_submission(sub.contest_id)
    assert fetched is not None
    assert fetched.contest_id == sub.contest_id
    assert fetched.candidate_uuid == "cand-1"


def test_empty_queue(queue: ContestabilityQueue) -> None:
    assert queue.next_for_review() is None
    assert queue.pending_count() == 0
