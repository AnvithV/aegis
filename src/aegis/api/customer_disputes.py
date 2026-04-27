"""Customer dispute workflow.

POST /v1/disputes

Customers file disputes about ranked candidates ("candidate X who you
ranked highly produced low-quality labels"). Flow:
1. Customer submits dispute via API (JWT authenticated)
2. Dispute enters admin review queue
3. Admin reviews: candidate evidence trail + customer task-quality data
4. Admin confirms or rejects with reasoning
5. CONFIRMED disputes feed back as highest-confidence ground truth
   for weight relearning via the Plackett-Luce pipeline

Disputes are NOT contestability (candidate-driven). This is customer-driven.
"""

from __future__ import annotations

import json
import logging
import statistics
import uuid as _uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import duckdb
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class DisputeCategory(StrEnum):
    """Categories for customer disputes."""

    low_quality_output = "low_quality_output"
    incorrect_ranking = "incorrect_ranking"
    missing_expertise = "missing_expertise"
    integrity_concern = "integrity_concern"
    other = "other"


class DisputeStatus(StrEnum):
    """Status of a customer dispute."""

    submitted = "submitted"
    under_review = "under_review"
    confirmed = "confirmed"
    rejected = "rejected"


class DisputeSubmission(BaseModel):
    """A customer dispute submission."""

    model_config = ConfigDict(frozen=True)

    dispute_id: str
    customer_id: str
    candidate_uuid: str
    query_id: str | None
    category: DisputeCategory
    description: str
    evidence: dict[str, Any]
    submitted_at: datetime
    status: DisputeStatus


class DisputeDecision(BaseModel):
    """An admin decision on a customer dispute."""

    model_config = ConfigDict(frozen=True)

    decision_id: str
    dispute_id: str
    admin_id: str
    confirmed: bool
    reasoning: str
    feedback_weight: float
    decided_at: datetime


class DisputeFeedback(BaseModel):
    """Feedback generated from a confirmed dispute for weight relearning."""

    model_config = ConfigDict(frozen=True)

    dispute_id: str
    candidate_uuid: str
    query_id: str | None
    category: DisputeCategory
    feedback_weight: float
    direction: str
    generated_at: datetime


class DisputeStats(BaseModel):
    """Aggregate dispute statistics."""

    model_config = ConfigDict(frozen=True)

    total_submitted: int
    total_under_review: int
    total_confirmed: int
    total_rejected: int
    confirmation_rate: float
    median_resolution_days: float | None
    feedback_generated: int


_DISPUTE_DDL = """
CREATE TABLE IF NOT EXISTS dispute_submissions (
    dispute_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    candidate_uuid TEXT NOT NULL,
    query_id TEXT,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence JSON NOT NULL,
    submitted_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted'
);

CREATE TABLE IF NOT EXISTS dispute_decisions (
    decision_id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL REFERENCES dispute_submissions(dispute_id),
    admin_id TEXT NOT NULL,
    confirmed BOOLEAN NOT NULL,
    reasoning TEXT NOT NULL,
    feedback_weight DOUBLE NOT NULL DEFAULT 1.0,
    decided_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);
"""


class DisputeQueue:
    """DuckDB-backed queue for customer disputes.

    Follows the ReviewQueue pattern. Confirmed disputes are converted
    to highest-confidence ground truth for weight relearning.
    """

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_DISPUTE_DDL)

    def submit(
        self,
        *,
        customer_id: str,
        candidate_uuid: str,
        category: DisputeCategory,
        description: str,
        evidence: dict[str, Any],
        query_id: str | None = None,
    ) -> DisputeSubmission:
        """Submit a new dispute."""
        dispute_id = _uuid.uuid4().hex
        now = datetime.now(tz=UTC)
        self._conn.execute(
            """INSERT INTO dispute_submissions
               (dispute_id, customer_id, candidate_uuid, query_id, category,
                description, evidence, submitted_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted')""",
            [
                dispute_id,
                customer_id,
                candidate_uuid,
                query_id,
                category.value,
                description,
                json.dumps(evidence),
                now,
            ],
        )
        return DisputeSubmission(
            dispute_id=dispute_id,
            customer_id=customer_id,
            candidate_uuid=candidate_uuid,
            query_id=query_id,
            category=category,
            description=description,
            evidence=evidence,
            submitted_at=now,
            status=DisputeStatus.submitted,
        )

    def next_for_review(self) -> DisputeSubmission | None:
        """Return oldest unresolved dispute."""
        row = self._conn.execute(
            """SELECT dispute_id, customer_id, candidate_uuid, query_id,
                      category, description, evidence, submitted_at, status
               FROM dispute_submissions
               WHERE status = 'submitted'
               ORDER BY submitted_at ASC
               LIMIT 1"""
        ).fetchone()

        if row is None:
            return None

        dispute_id = row[0]
        self._conn.execute(
            "UPDATE dispute_submissions SET status = 'under_review'"
            " WHERE dispute_id = ?",
            [dispute_id],
        )

        evidence = row[6] if isinstance(row[6], dict) else json.loads(row[6])
        return DisputeSubmission(
            dispute_id=row[0],
            customer_id=row[1],
            candidate_uuid=row[2],
            query_id=row[3],
            category=DisputeCategory(row[4]),
            description=row[5],
            evidence=evidence,
            submitted_at=row[7],
            status=DisputeStatus.under_review,
        )

    def decide(
        self,
        *,
        dispute_id: str,
        admin_id: str,
        confirmed: bool,
        reasoning: str,
    ) -> DisputeDecision:
        """Record an admin decision on a dispute."""
        decision_id = _uuid.uuid4().hex
        now = datetime.now(tz=UTC)
        feedback_weight = 1.0 if confirmed else 0.0
        self._conn.execute(
            """INSERT INTO dispute_decisions
               (decision_id, dispute_id, admin_id, confirmed, reasoning,
                feedback_weight, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                decision_id, dispute_id, admin_id, confirmed,
                reasoning, feedback_weight, now,
            ],
        )
        new_status = "confirmed" if confirmed else "rejected"
        self._conn.execute(
            "UPDATE dispute_submissions SET status = ? WHERE dispute_id = ?",
            [new_status, dispute_id],
        )
        return DisputeDecision(
            decision_id=decision_id,
            dispute_id=dispute_id,
            admin_id=admin_id,
            confirmed=confirmed,
            reasoning=reasoning,
            feedback_weight=feedback_weight,
            decided_at=now,
        )

    def generate_feedback(self, dispute_id: str) -> DisputeFeedback | None:
        """Generate feedback from a confirmed dispute."""
        sub = self.get_submission(dispute_id)
        if sub is None:
            return None

        # Check for confirmed decision
        row = self._conn.execute(
            """SELECT confirmed FROM dispute_decisions
               WHERE dispute_id = ? ORDER BY decided_at DESC LIMIT 1""",
            [dispute_id],
        ).fetchone()

        if row is None or not row[0]:
            return None

        # Determine direction based on category
        if sub.category in (
            DisputeCategory.low_quality_output,
            DisputeCategory.incorrect_ranking,
            DisputeCategory.missing_expertise,
        ):
            direction = "downweight"
        elif sub.category == DisputeCategory.integrity_concern:
            direction = "flag"
        else:
            direction = "review"

        return DisputeFeedback(
            dispute_id=dispute_id,
            candidate_uuid=sub.candidate_uuid,
            query_id=sub.query_id,
            category=sub.category,
            feedback_weight=1.0,
            direction=direction,
            generated_at=datetime.now(tz=UTC),
        )

    def get_all_feedback(self) -> list[DisputeFeedback]:
        """Return feedback for ALL confirmed disputes."""
        rows = self._conn.execute(
            """SELECT dispute_id FROM dispute_submissions
               WHERE status = 'confirmed'"""
        ).fetchall()
        feedback_list: list[DisputeFeedback] = []
        for row in rows:
            fb = self.generate_feedback(row[0])
            if fb is not None:
                feedback_list.append(fb)
        return feedback_list

    def get_submission(self, dispute_id: str) -> DisputeSubmission | None:
        """Look up a dispute by dispute_id."""
        row = self._conn.execute(
            """SELECT dispute_id, customer_id, candidate_uuid, query_id,
                      category, description, evidence, submitted_at, status
               FROM dispute_submissions WHERE dispute_id = ?""",
            [dispute_id],
        ).fetchone()

        if row is None:
            return None

        evidence = row[6] if isinstance(row[6], dict) else json.loads(row[6])
        return DisputeSubmission(
            dispute_id=row[0],
            customer_id=row[1],
            candidate_uuid=row[2],
            query_id=row[3],
            category=DisputeCategory(row[4]),
            description=row[5],
            evidence=evidence,
            submitted_at=row[7],
            status=DisputeStatus(row[8]),
        )

    def get_by_customer(self, customer_id: str) -> list[DisputeSubmission]:
        """Return all disputes for a customer."""
        rows = self._conn.execute(
            """SELECT dispute_id, customer_id, candidate_uuid, query_id,
                      category, description, evidence, submitted_at, status
               FROM dispute_submissions WHERE customer_id = ?
               ORDER BY submitted_at ASC""",
            [customer_id],
        ).fetchall()

        return [
            DisputeSubmission(
                dispute_id=row[0],
                customer_id=row[1],
                candidate_uuid=row[2],
                query_id=row[3],
                category=DisputeCategory(row[4]),
                description=row[5],
                evidence=row[6] if isinstance(row[6], dict) else json.loads(row[6]),
                submitted_at=row[7],
                status=DisputeStatus(row[8]),
            )
            for row in rows
        ]

    def get_by_candidate(self, candidate_uuid: str) -> list[DisputeSubmission]:
        """Return all disputes about a candidate."""
        rows = self._conn.execute(
            """SELECT dispute_id, customer_id, candidate_uuid, query_id,
                      category, description, evidence, submitted_at, status
               FROM dispute_submissions WHERE candidate_uuid = ?
               ORDER BY submitted_at ASC""",
            [candidate_uuid],
        ).fetchall()

        return [
            DisputeSubmission(
                dispute_id=row[0],
                customer_id=row[1],
                candidate_uuid=row[2],
                query_id=row[3],
                category=DisputeCategory(row[4]),
                description=row[5],
                evidence=row[6] if isinstance(row[6], dict) else json.loads(row[6]),
                submitted_at=row[7],
                status=DisputeStatus(row[8]),
            )
            for row in rows
        ]

    def pending_count(self) -> int:
        """Count of submitted + under_review items."""
        row = self._conn.execute(
            """SELECT COUNT(*) FROM dispute_submissions
               WHERE status IN ('submitted', 'under_review')"""
        ).fetchone()
        return int(row[0]) if row else 0

    def get_stats(self) -> DisputeStats:
        """Aggregate dispute statistics."""
        rows = self._conn.execute(
            "SELECT status FROM dispute_submissions"
        ).fetchall()
        total_submitted_count = len(rows)
        total_under_review = sum(
            1 for r in rows if r[0] == DisputeStatus.under_review
        )
        total_confirmed = sum(1 for r in rows if r[0] == DisputeStatus.confirmed)
        total_rejected = sum(1 for r in rows if r[0] == DisputeStatus.rejected)
        total_resolved = total_confirmed + total_rejected

        confirmation_rate = (
            total_confirmed / total_resolved if total_resolved > 0 else 0.0
        )

        # Compute resolution days
        resolution_rows = self._conn.execute(
            """SELECT s.submitted_at, d.decided_at
               FROM dispute_submissions s
               JOIN (
                   SELECT dispute_id, MAX(decided_at) AS decided_at
                   FROM dispute_decisions GROUP BY dispute_id
               ) d ON s.dispute_id = d.dispute_id
               WHERE s.status IN ('confirmed', 'rejected')"""
        ).fetchall()

        median_days: float | None = None
        if resolution_rows:
            days_list = sorted(
                (r[1] - r[0]).total_seconds() / 86400.0 for r in resolution_rows
            )
            median_days = statistics.median(days_list)

        return DisputeStats(
            total_submitted=total_submitted_count,
            total_under_review=total_under_review,
            total_confirmed=total_confirmed,
            total_rejected=total_rejected,
            confirmation_rate=confirmation_rate,
            median_resolution_days=median_days,
            feedback_generated=total_confirmed,
        )

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()
