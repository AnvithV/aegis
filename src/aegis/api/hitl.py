"""HITL review queue API: review items and decisions."""

from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from aegis.identity.review_queue import ReviewDecision, ReviewQueue

router = APIRouter(prefix="/v1/hitl", tags=["hitl"])


def _db_path() -> str:
    return os.environ.get("AEGIS_DB_PATH", "aegis.duckdb")


class DecideRequest(BaseModel):
    """Request body for deciding on a review item."""

    model_config = ConfigDict(frozen=True)

    decision: Literal["confirm", "reject", "split"]
    reviewer: str = "system"


@router.get("/next")
def get_next_review_item() -> dict[str, Any]:
    """Return the next pending review item (FIFO)."""
    queue = ReviewQueue(db_path=_db_path())
    try:
        item = queue.next()
        return {"item": item.model_dump() if item else None}
    finally:
        queue.close()


@router.post("/{item_id}/decide")
def decide_review_item(item_id: str, body: DecideRequest) -> dict[str, str]:
    """Record a decision for a review item."""
    queue = ReviewQueue(db_path=_db_path())
    try:
        queue.decide(item_id, ReviewDecision(body.decision), reviewer=body.reviewer)
        return {"status": "ok", "item_id": item_id, "decision": body.decision}
    finally:
        queue.close()


@router.get("/stats")
def get_hitl_stats() -> dict[str, int]:
    """Get summary statistics for the HITL review queue."""
    queue = ReviewQueue(db_path=_db_path())
    try:
        return {
            "pending": queue.pending_count(),
            "reviewed": len(queue.get_decisions()),
        }
    finally:
        queue.close()
