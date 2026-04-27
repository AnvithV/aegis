"""Tests for customer dispute workflow."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis.api.customer_disputes import (
    DisputeCategory,
    DisputeQueue,
    DisputeStatus,
    DisputeSubmission,
)


@pytest.fixture()
def queue(tmp_path: Path) -> Generator[DisputeQueue]:
    db_path = str(tmp_path / "dispute_test.duckdb")
    q = DisputeQueue(db_path=db_path)
    yield q
    q.close()


def _submit_default(
    q: DisputeQueue,
    *,
    customer_id: str = "customer-1",
    candidate_uuid: str = "cand-1",
    category: DisputeCategory = DisputeCategory.low_quality_output,
) -> DisputeSubmission:
    return q.submit(
        customer_id=customer_id,
        candidate_uuid=candidate_uuid,
        category=category,
        description="Candidate produced low-quality labels on our annotation task.",
        evidence={"task_id": "task-123", "quality_score": 0.3},
    )


def test_submit_dispute(queue: DisputeQueue) -> None:
    sub = _submit_default(queue)
    assert sub.status == DisputeStatus.submitted
    assert sub.dispute_id is not None


def test_next_for_review(queue: DisputeQueue) -> None:
    sub1 = _submit_default(queue, candidate_uuid="cand-1")
    _submit_default(queue, candidate_uuid="cand-2")
    item = queue.next_for_review()
    assert item is not None
    assert item.dispute_id == sub1.dispute_id
    assert item.status == DisputeStatus.under_review


def test_decide_confirmed(queue: DisputeQueue) -> None:
    sub = _submit_default(queue)
    queue.next_for_review()
    decision = queue.decide(
        dispute_id=sub.dispute_id,
        admin_id="admin-1",
        confirmed=True,
        reasoning="Verified low quality",
    )
    assert decision.confirmed is True
    assert decision.feedback_weight == 1.0
    updated = queue.get_submission(sub.dispute_id)
    assert updated is not None
    assert updated.status == DisputeStatus.confirmed


def test_decide_rejected(queue: DisputeQueue) -> None:
    sub = _submit_default(queue)
    decision = queue.decide(
        dispute_id=sub.dispute_id,
        admin_id="admin-1",
        confirmed=False,
        reasoning="Quality was acceptable",
    )
    assert decision.confirmed is False
    assert decision.feedback_weight == 0.0
    updated = queue.get_submission(sub.dispute_id)
    assert updated is not None
    assert updated.status == DisputeStatus.rejected


def test_generate_feedback_confirmed(queue: DisputeQueue) -> None:
    sub = _submit_default(queue, category=DisputeCategory.low_quality_output)
    queue.decide(
        dispute_id=sub.dispute_id,
        admin_id="admin-1",
        confirmed=True,
        reasoning="Verified",
    )
    fb = queue.generate_feedback(sub.dispute_id)
    assert fb is not None
    assert fb.feedback_weight == 1.0
    assert fb.direction == "downweight"


def test_generate_feedback_rejected_returns_none(queue: DisputeQueue) -> None:
    sub = _submit_default(queue)
    queue.decide(
        dispute_id=sub.dispute_id,
        admin_id="admin-1",
        confirmed=False,
        reasoning="Rejected",
    )
    fb = queue.generate_feedback(sub.dispute_id)
    assert fb is None


def test_get_all_feedback(queue: DisputeQueue) -> None:
    for i in range(3):
        sub = _submit_default(queue, candidate_uuid=f"cand-{i}")
        if i < 2:
            queue.decide(
                dispute_id=sub.dispute_id,
                admin_id="admin-1",
                confirmed=True,
                reasoning="OK",
            )
        else:
            queue.decide(
                dispute_id=sub.dispute_id,
                admin_id="admin-1",
                confirmed=False,
                reasoning="Rejected",
            )
    feedback = queue.get_all_feedback()
    assert len(feedback) == 2


def test_get_by_customer(queue: DisputeQueue) -> None:
    _submit_default(queue, customer_id="customer-a", candidate_uuid="cand-1")
    _submit_default(queue, customer_id="customer-a", candidate_uuid="cand-2")
    _submit_default(queue, customer_id="customer-b", candidate_uuid="cand-3")
    result = queue.get_by_customer("customer-a")
    assert len(result) == 2


def test_get_by_candidate(queue: DisputeQueue) -> None:
    _submit_default(queue, customer_id="customer-a", candidate_uuid="cand-1")
    _submit_default(queue, customer_id="customer-b", candidate_uuid="cand-1")
    _submit_default(queue, customer_id="customer-c", candidate_uuid="cand-2")
    result = queue.get_by_candidate("cand-1")
    assert len(result) == 2


def test_pending_count(queue: DisputeQueue) -> None:
    for i in range(5):
        sub = _submit_default(queue, candidate_uuid=f"cand-{i}")
        if i < 2:
            queue.decide(
                dispute_id=sub.dispute_id,
                admin_id="admin-1",
                confirmed=True,
                reasoning="OK",
            )
    assert queue.pending_count() == 3


def test_stats(queue: DisputeQueue) -> None:
    for i in range(5):
        sub = _submit_default(queue, candidate_uuid=f"cand-{i}")
        if i < 2:
            queue.decide(
                dispute_id=sub.dispute_id,
                admin_id="admin-1",
                confirmed=True,
                reasoning="OK",
            )
        elif i == 2:
            queue.decide(
                dispute_id=sub.dispute_id,
                admin_id="admin-1",
                confirmed=False,
                reasoning="Rejected",
            )
    stats = queue.get_stats()
    assert stats.total_confirmed == 2
    assert stats.total_rejected == 1
    assert stats.confirmation_rate == pytest.approx(2 / 3)


def test_empty_queue(queue: DisputeQueue) -> None:
    assert queue.next_for_review() is None
    assert queue.pending_count() == 0


def test_dispute_submission_model() -> None:
    sub = DisputeSubmission(
        dispute_id="abc123",
        customer_id="customer-1",
        candidate_uuid="cand-1",
        query_id=None,
        category=DisputeCategory.low_quality_output,
        description="Test",
        evidence={},
        submitted_at=datetime.now(tz=UTC),
        status=DisputeStatus.submitted,
    )
    with pytest.raises(Exception):  # noqa: B017
        sub.dispute_id = "xyz"


def test_feedback_direction_integrity(queue: DisputeQueue) -> None:
    sub = _submit_default(queue, category=DisputeCategory.integrity_concern)
    queue.decide(
        dispute_id=sub.dispute_id,
        admin_id="admin-1",
        confirmed=True,
        reasoning="Integrity issue verified",
    )
    fb = queue.generate_feedback(sub.dispute_id)
    assert fb is not None
    assert fb.direction == "flag"
