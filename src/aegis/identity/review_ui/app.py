"""Minimal FastAPI app for HITL linkage review."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from aegis.identity.review_queue import ReviewDecision, ReviewQueue

app = FastAPI(title="Aegis Review UI", version="0.1.0")

# Module-level queue instance; overridden in tests.
_queue: ReviewQueue | None = None


def get_queue() -> ReviewQueue:
    """Return the module-level ReviewQueue, creating if needed."""
    global _queue  # noqa: PLW0603
    if _queue is None:
        _queue = ReviewQueue()
    return _queue


def set_queue(queue: ReviewQueue) -> None:
    """Override the queue instance (used in tests)."""
    global _queue  # noqa: PLW0603
    _queue = queue


class DecideRequest(BaseModel):
    """Request body for the decide endpoint."""

    decision: str
    reviewer: str = "system"


@app.get("/review/next")
def review_next() -> dict[str, Any]:
    """Return the next item for review."""
    queue = get_queue()
    item = queue.next()
    if item is None:
        return {"item": None}
    return {"item": item.model_dump(mode="json")}


@app.post("/review/{item_id}/decide")
def review_decide(item_id: str, body: DecideRequest) -> dict[str, str]:
    """Record a decision for a review item."""
    queue = get_queue()
    try:
        decision = ReviewDecision(body.decision)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid decision: {body.decision}. "
                "Must be one of: confirm, reject, split"
            ),
        )
    queue.decide(item_id, decision, reviewer=body.reviewer)
    return {"status": "ok", "item_id": item_id, "decision": body.decision}


@app.get("/review/stats")
def review_stats() -> dict[str, int]:
    """Return queue statistics."""
    queue = get_queue()
    pending = queue.pending_count()
    decisions = queue.get_decisions()
    return {"pending": pending, "reviewed": len(decisions)}
