"""HITL linkage review queue for borderline probabilistic matches."""

from __future__ import annotations

import json
import uuid as _uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

import duckdb
from pydantic import BaseModel, ConfigDict

from aegis.identity.probabilistic import LinkResult


class ReviewDecision(StrEnum):
    """Possible decisions for a review item."""

    confirm = "confirm"
    reject = "reject"
    split = "split"  # type: ignore[assignment]


class ReviewItem(BaseModel):
    """A queued item awaiting human review."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    artifact_features: dict[str, Any]
    candidate_uuid: str
    link_result: LinkResult
    evidence: dict[str, Any]
    created_at: datetime


_QUEUE_DDL = """
CREATE TABLE IF NOT EXISTS review_queue (
    item_id TEXT PRIMARY KEY,
    artifact_features JSON NOT NULL,
    candidate_uuid TEXT NOT NULL,
    link_confidence DOUBLE NOT NULL,
    feature_scores JSON NOT NULL,
    evidence JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES review_queue(item_id),
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    decided_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);
"""


class ReviewQueue:
    """DuckDB-backed FIFO queue for borderline match review."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_QUEUE_DDL)

    def enqueue(self, item: ReviewItem) -> None:
        """Add a review item to the queue."""
        self._conn.execute(
            """
            INSERT INTO review_queue
                (item_id, artifact_features, candidate_uuid,
                 link_confidence, feature_scores, evidence,
                 created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            [
                item.item_id,
                json.dumps(item.artifact_features),
                item.candidate_uuid,
                item.link_result.confidence,
                json.dumps(item.link_result.feature_scores),
                json.dumps(item.evidence),
                item.created_at.isoformat(),
            ],
        )

    def next(self) -> ReviewItem | None:
        """Return the oldest unreviewed item (FIFO)."""
        row = self._conn.execute(
            """
            SELECT item_id, artifact_features, candidate_uuid,
                   link_confidence, feature_scores, evidence, created_at
            FROM review_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        return self._row_to_item(row)

    def decide(
        self,
        item_id: str,
        decision: ReviewDecision,
        reviewer: str = "system",
    ) -> None:
        """Record a decision for a review item."""
        decision_id = str(_uuid.uuid4())
        now = datetime.now(UTC)
        self._conn.execute(
            """
            INSERT INTO review_decisions
                (decision_id, item_id, decision, reviewer, decided_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [decision_id, item_id, decision.value, reviewer, now.isoformat()],
        )
        self._conn.execute(
            "UPDATE review_queue SET status = 'reviewed' WHERE item_id = ?",
            [item_id],
        )

    def get_decisions(
        self, since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """List all decisions, optionally filtered by time."""
        if since is not None:
            rows = self._conn.execute(
                """
                SELECT decision_id, item_id, decision, reviewer, decided_at
                FROM review_decisions
                WHERE decided_at >= ?
                ORDER BY decided_at ASC
                """,
                [since.isoformat()],
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT decision_id, item_id, decision, reviewer, decided_at
                FROM review_decisions
                ORDER BY decided_at ASC
                """
            ).fetchall()
        return [
            {
                "decision_id": r[0],
                "item_id": r[1],
                "decision": r[2],
                "reviewer": r[3],
                "decided_at": r[4],
            }
            for r in rows
        ]

    def pending_count(self) -> int:
        """Count of unreviewed items."""
        result = self._conn.execute(
            "SELECT COUNT(*) FROM review_queue WHERE status = 'pending'"
        ).fetchone()
        return int(result[0]) if result else 0

    def export_training_data(
        self,
    ) -> list[tuple[dict[str, Any], str, str]]:
        """Export decisions as (artifact_features, candidate_uuid, decision) tuples."""
        rows = self._conn.execute(
            """
            SELECT q.artifact_features, q.candidate_uuid, d.decision
            FROM review_decisions d
            JOIN review_queue q ON d.item_id = q.item_id
            ORDER BY d.decided_at ASC
            """
        ).fetchall()
        result: list[tuple[dict[str, Any], str, str]] = []
        for r in rows:
            features = json.loads(r[0]) if isinstance(r[0], str) else r[0]
            result.append((features, r[1], r[2]))
        return result

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()

    @staticmethod
    def _row_to_item(row: tuple[Any, ...]) -> ReviewItem:
        """Convert a database row to a ReviewItem."""
        artifact_features = (
            json.loads(row[1]) if isinstance(row[1], str) else row[1]
        )
        feature_scores = (
            json.loads(row[4]) if isinstance(row[4], str) else row[4]
        )
        evidence = (
            json.loads(row[5]) if isinstance(row[5], str) else row[5]
        )
        confidence = float(row[3])

        # Determine action from confidence
        action: Literal["auto-link", "review", "reject"]
        if confidence >= 0.95:
            action = "auto-link"
        elif confidence >= 0.5:
            action = "review"
        else:
            action = "reject"

        created_at = row[6]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return ReviewItem(
            item_id=row[0],
            artifact_features=artifact_features,
            candidate_uuid=row[2],
            link_result=LinkResult(
                candidate_uuid=row[2],
                confidence=confidence,
                action=action,
                feature_scores=feature_scores,
            ),
            evidence=evidence,
            created_at=created_at,
        )
