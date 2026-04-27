"""Tests for the HITL linkage review queue."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest
from fastapi.testclient import TestClient

from aegis.identity.probabilistic import LinkResult
from aegis.identity.review_queue import ReviewDecision, ReviewItem, ReviewQueue


def _make_link_result(
    *, confidence: float = 0.75, candidate_uuid: str = "cand-001"
) -> LinkResult:
    action: Literal["auto-link", "review", "reject"]
    if confidence >= 0.95:
        action = "auto-link"
    elif confidence >= 0.5:
        action = "review"
    else:
        action = "reject"
    return LinkResult(
        candidate_uuid=candidate_uuid,
        confidence=confidence,
        action=action,
        feature_scores={
            "name_similarity": 0.8,
            "affiliation_similarity": 0.7,
            "coauthor_overlap": 0.6,
            "mesh_overlap": 0.5,
            "time_continuity": 0.9,
        },
    )


def _make_review_item(
    *,
    item_id: str = "item-001",
    candidate_uuid: str = "cand-001",
    confidence: float = 0.75,
    created_at: datetime | None = None,
) -> ReviewItem:
    return ReviewItem(
        item_id=item_id,
        artifact_features={"name": "Jane Smith", "affiliation": "Harvard"},
        candidate_uuid=candidate_uuid,
        link_result=_make_link_result(
            confidence=confidence, candidate_uuid=candidate_uuid
        ),
        evidence={
            "affiliations": ["Harvard", "MIT"],
            "coauthors": ["John Doe"],
        },
        created_at=created_at or datetime.now(UTC),
    )


@pytest.fixture()
def queue(tmp_path: Path) -> Generator[ReviewQueue]:
    db_path = str(tmp_path / "test.duckdb")
    q = ReviewQueue(db_path=db_path)
    yield q
    q.close()


def test_enqueue_and_next(queue: ReviewQueue) -> None:
    """Enqueue an item, call next(), assert same item returned."""
    item = _make_review_item()
    queue.enqueue(item)

    result = queue.next()
    assert result is not None
    assert result.item_id == "item-001"
    assert result.candidate_uuid == "cand-001"
    assert result.link_result.confidence == 0.75


def test_fifo_order(queue: ReviewQueue) -> None:
    """Enqueue 3 items, assert next() returns in chronological order."""
    t1 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
    t3 = datetime(2024, 1, 3, 0, 0, 0, tzinfo=UTC)

    queue.enqueue(_make_review_item(item_id="item-3", created_at=t3))
    queue.enqueue(_make_review_item(item_id="item-1", created_at=t1))
    queue.enqueue(_make_review_item(item_id="item-2", created_at=t2))

    first = queue.next()
    assert first is not None
    assert first.item_id == "item-1"

    queue.decide(first.item_id, ReviewDecision.confirm)
    second = queue.next()
    assert second is not None
    assert second.item_id == "item-2"

    queue.decide(second.item_id, ReviewDecision.confirm)
    third = queue.next()
    assert third is not None
    assert third.item_id == "item-3"


def test_decide_confirm(queue: ReviewQueue) -> None:
    """Enqueue, decide 'confirm', assert item status is reviewed."""
    item = _make_review_item()
    queue.enqueue(item)

    queue.decide("item-001", ReviewDecision.confirm)

    # No more pending items
    assert queue.next() is None
    assert queue.pending_count() == 0

    decisions = queue.get_decisions()
    assert len(decisions) == 1
    assert decisions[0]["decision"] == "confirm"


def test_decide_reject(queue: ReviewQueue) -> None:
    """Decide 'reject', assert item status is reviewed."""
    item = _make_review_item()
    queue.enqueue(item)

    queue.decide("item-001", ReviewDecision.reject)

    assert queue.next() is None
    decisions = queue.get_decisions()
    assert len(decisions) == 1
    assert decisions[0]["decision"] == "reject"


def test_pending_count(queue: ReviewQueue) -> None:
    """Enqueue 5, decide 2, assert pending_count is 3."""
    for i in range(5):
        queue.enqueue(_make_review_item(item_id=f"item-{i:03d}"))

    assert queue.pending_count() == 5

    queue.decide("item-000", ReviewDecision.confirm)
    queue.decide("item-001", ReviewDecision.reject)

    assert queue.pending_count() == 3


def test_export_training_data(queue: ReviewQueue) -> None:
    """Enqueue 3 items, decide all, export, assert 3 tuples."""
    for i in range(3):
        queue.enqueue(
            _make_review_item(
                item_id=f"item-{i:03d}", candidate_uuid=f"cand-{i:03d}"
            )
        )

    queue.decide("item-000", ReviewDecision.confirm, reviewer="reviewer-1")
    queue.decide("item-001", ReviewDecision.reject, reviewer="reviewer-1")
    queue.decide("item-002", ReviewDecision.split, reviewer="reviewer-2")

    data = queue.export_training_data()
    assert len(data) == 3

    # Check structure: (features_dict, candidate_uuid, decision)
    features, cand_uuid, decision = data[0]
    assert isinstance(features, dict)
    assert "name" in features
    assert cand_uuid == "cand-000"
    assert decision == "confirm"

    assert data[1][2] == "reject"
    assert data[2][2] == "split"


def test_decisions_append_only(queue: ReviewQueue) -> None:
    """Decide same item twice, assert both decisions recorded."""
    item = _make_review_item()
    queue.enqueue(item)

    queue.decide("item-001", ReviewDecision.confirm, reviewer="alice")
    queue.decide("item-001", ReviewDecision.reject, reviewer="bob")

    decisions = queue.get_decisions()
    assert len(decisions) == 2
    assert decisions[0]["decision"] == "confirm"
    assert decisions[0]["reviewer"] == "alice"
    assert decisions[1]["decision"] == "reject"
    assert decisions[1]["reviewer"] == "bob"


def test_review_ui_endpoints(tmp_path: Path) -> None:
    """Use FastAPI TestClient to test all 3 endpoints."""
    from aegis.identity.review_ui.app import app, set_queue

    db_path = str(tmp_path / "ui_test.duckdb")
    q = ReviewQueue(db_path=db_path)
    set_queue(q)

    client = TestClient(app)

    # Stats: empty queue
    resp = client.get("/review/stats")
    assert resp.status_code == 200
    assert resp.json() == {"pending": 0, "reviewed": 0}

    # Next: empty queue
    resp = client.get("/review/next")
    assert resp.status_code == 200
    assert resp.json()["item"] is None

    # Enqueue an item directly
    item = _make_review_item(item_id="ui-001")
    q.enqueue(item)

    # Next: returns item
    resp = client.get("/review/next")
    assert resp.status_code == 200
    data = resp.json()["item"]
    assert data is not None
    assert data["item_id"] == "ui-001"

    # Stats: 1 pending
    resp = client.get("/review/stats")
    assert resp.status_code == 200
    assert resp.json()["pending"] == 1

    # Decide: confirm
    resp = client.post(
        "/review/ui-001/decide",
        json={"decision": "confirm", "reviewer": "tester"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Stats: 0 pending, 1 reviewed
    resp = client.get("/review/stats")
    assert resp.status_code == 200
    assert resp.json() == {"pending": 0, "reviewed": 1}

    q.close()
