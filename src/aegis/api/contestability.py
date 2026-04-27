"""Contestability endpoint and workflow for candidate-initiated corrections.

POST /v1/candidates/{uuid}/contests

Candidates (verified via ORCID or NPI) can submit structured corrections:
- Affiliation history errors
- Misattributed artifacts (wrong PMID/NCT/patent linked)
- Integrity gate false positives (retraction misclassified, etc.)
- Identity resolution errors (merged with wrong person)

Submissions enter the HITL review queue with ELEVATED priority.
Reviewer decisions update the candidate record (append-only).
SLA targets: 5-day median, 14-day p95 resolution.
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


class ContestCategory(StrEnum):
    """Categories for contestability submissions."""

    affiliation_error = "affiliation_error"
    artifact_misattribution = "artifact_misattribution"
    integrity_false_positive = "integrity_false_positive"
    identity_error = "identity_error"
    score_dispute = "score_dispute"
    other = "other"


class ContestStatus(StrEnum):
    """Status of a contest submission."""

    submitted = "submitted"
    in_review = "in_review"
    resolved_accepted = "resolved_accepted"
    resolved_rejected = "resolved_rejected"


class ContestPriority(StrEnum):
    """Priority levels for contest items."""

    normal = "normal"
    elevated = "elevated"
    urgent = "urgent"


class ContestSubmission(BaseModel):
    """A contestability submission from a candidate."""

    model_config = ConfigDict(frozen=True)

    contest_id: str
    candidate_uuid: str
    category: ContestCategory
    description: str
    evidence: dict[str, Any]
    verified_via: str
    requester_id: str
    submitted_at: datetime
    status: ContestStatus
    priority: ContestPriority


class ContestDecision(BaseModel):
    """A reviewer's decision on a contest submission."""

    model_config = ConfigDict(frozen=True)

    decision_id: str
    contest_id: str
    reviewer_id: str
    accepted: bool
    reasoning: str
    actions_taken: list[str]
    decided_at: datetime


class ContestSummary(BaseModel):
    """Summary of a contest for listing."""

    model_config = ConfigDict(frozen=True)

    contest_id: str
    candidate_uuid: str
    category: ContestCategory
    status: ContestStatus
    submitted_at: datetime
    resolved_at: datetime | None
    resolution_days: float | None


class ContestStats(BaseModel):
    """Aggregate contestability statistics."""

    model_config = ConfigDict(frozen=True)

    total_submitted: int
    total_in_review: int
    total_resolved: int
    total_accepted: int
    total_rejected: int
    median_resolution_days: float | None
    p95_resolution_days: float | None


_CONTEST_DDL = """
CREATE TABLE IF NOT EXISTS contest_submissions (
    contest_id TEXT PRIMARY KEY,
    candidate_uuid TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence JSON NOT NULL,
    verified_via TEXT NOT NULL,
    requester_id TEXT NOT NULL,
    submitted_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted',
    priority TEXT NOT NULL DEFAULT 'elevated'
);

CREATE TABLE IF NOT EXISTS contest_decisions (
    decision_id TEXT PRIMARY KEY,
    contest_id TEXT NOT NULL REFERENCES contest_submissions(contest_id),
    reviewer_id TEXT NOT NULL,
    accepted BOOLEAN NOT NULL,
    reasoning TEXT NOT NULL,
    actions_taken JSON NOT NULL,
    decided_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);
"""


class ContestabilityQueue:
    """DuckDB-backed queue for candidate contestability requests.

    Follows the ReviewQueue pattern from src/aegis/identity/review_queue.py.
    Contestability items have ELEVATED priority by default.
    """

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CONTEST_DDL)

    def submit(
        self,
        *,
        candidate_uuid: str,
        category: ContestCategory,
        description: str,
        evidence: dict[str, Any],
        verified_via: str,
        requester_id: str,
    ) -> ContestSubmission:
        """Submit a new contest."""
        contest_id = _uuid.uuid4().hex
        now = datetime.now(tz=UTC)
        self._conn.execute(
            """INSERT INTO contest_submissions
               (contest_id, candidate_uuid, category, description, evidence,
                verified_via, requester_id, submitted_at, status, priority)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted', 'elevated')""",
            [
                contest_id,
                candidate_uuid,
                category.value,
                description,
                json.dumps(evidence),
                verified_via,
                requester_id,
                now,
            ],
        )
        return ContestSubmission(
            contest_id=contest_id,
            candidate_uuid=candidate_uuid,
            category=category,
            description=description,
            evidence=evidence,
            verified_via=verified_via,
            requester_id=requester_id,
            submitted_at=now,
            status=ContestStatus.submitted,
            priority=ContestPriority.elevated,
        )

    def next_for_review(self) -> ContestSubmission | None:
        """Return oldest unresolved submission, priority-ordered."""
        row = self._conn.execute(
            """SELECT contest_id, candidate_uuid, category, description, evidence,
                      verified_via, requester_id, submitted_at, status, priority
               FROM contest_submissions
               WHERE status IN ('submitted', 'in_review')
               ORDER BY
                 CASE priority
                   WHEN 'urgent' THEN 1
                   WHEN 'elevated' THEN 2
                   WHEN 'normal' THEN 3
                 END ASC,
                 submitted_at ASC
               LIMIT 1"""
        ).fetchone()

        if row is None:
            return None

        contest_id = row[0]
        self._conn.execute(
            "UPDATE contest_submissions SET status = 'in_review' WHERE contest_id = ?",
            [contest_id],
        )

        evidence = row[4] if isinstance(row[4], dict) else json.loads(row[4])
        return ContestSubmission(
            contest_id=row[0],
            candidate_uuid=row[1],
            category=ContestCategory(row[2]),
            description=row[3],
            evidence=evidence,
            verified_via=row[5],
            requester_id=row[6],
            submitted_at=row[7],
            status=ContestStatus.in_review,
            priority=ContestPriority(row[9]),
        )

    def decide(
        self,
        *,
        contest_id: str,
        reviewer_id: str,
        accepted: bool,
        reasoning: str,
        actions_taken: list[str] | None = None,
    ) -> ContestDecision:
        """Record a reviewer decision on a contest."""
        decision_id = _uuid.uuid4().hex
        now = datetime.now(tz=UTC)
        self._conn.execute(
            """INSERT INTO contest_decisions
               (decision_id, contest_id, reviewer_id, accepted, reasoning,
                actions_taken, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                decision_id,
                contest_id,
                reviewer_id,
                accepted,
                reasoning,
                json.dumps(actions_taken or []),
                now,
            ],
        )
        new_status = "resolved_accepted" if accepted else "resolved_rejected"
        self._conn.execute(
            "UPDATE contest_submissions SET status = ? WHERE contest_id = ?",
            [new_status, contest_id],
        )
        return ContestDecision(
            decision_id=decision_id,
            contest_id=contest_id,
            reviewer_id=reviewer_id,
            accepted=accepted,
            reasoning=reasoning,
            actions_taken=actions_taken or [],
            decided_at=now,
        )

    def get_submission(self, contest_id: str) -> ContestSubmission | None:
        """Look up a submission by contest_id."""
        row = self._conn.execute(
            """SELECT contest_id, candidate_uuid, category, description, evidence,
                      verified_via, requester_id, submitted_at, status, priority
               FROM contest_submissions WHERE contest_id = ?""",
            [contest_id],
        ).fetchone()

        if row is None:
            return None

        evidence = row[4] if isinstance(row[4], dict) else json.loads(row[4])
        return ContestSubmission(
            contest_id=row[0],
            candidate_uuid=row[1],
            category=ContestCategory(row[2]),
            description=row[3],
            evidence=evidence,
            verified_via=row[5],
            requester_id=row[6],
            submitted_at=row[7],
            status=ContestStatus(row[8]),
            priority=ContestPriority(row[9]),
        )

    def get_by_candidate(self, candidate_uuid: str) -> list[ContestSummary]:
        """Return all submissions for a candidate with resolution info."""
        rows = self._conn.execute(
            """SELECT s.contest_id, s.candidate_uuid, s.category, s.status,
                      s.submitted_at,
                      d.decided_at
               FROM contest_submissions s
               LEFT JOIN (
                   SELECT contest_id, MAX(decided_at) AS decided_at
                   FROM contest_decisions
                   GROUP BY contest_id
               ) d ON s.contest_id = d.contest_id
               WHERE s.candidate_uuid = ?
               ORDER BY s.submitted_at ASC""",
            [candidate_uuid],
        ).fetchall()

        summaries: list[ContestSummary] = []
        for row in rows:
            resolved_at = row[5]
            resolution_days: float | None = None
            if resolved_at is not None:
                delta = resolved_at - row[4]
                resolution_days = delta.total_seconds() / 86400.0
            summaries.append(
                ContestSummary(
                    contest_id=row[0],
                    candidate_uuid=row[1],
                    category=ContestCategory(row[2]),
                    status=ContestStatus(row[3]),
                    submitted_at=row[4],
                    resolved_at=resolved_at,
                    resolution_days=resolution_days,
                )
            )
        return summaries

    def get_decisions(self, contest_id: str) -> list[ContestDecision]:
        """Return all decisions for a contest."""
        rows = self._conn.execute(
            """SELECT decision_id, contest_id, reviewer_id, accepted,
                      reasoning, actions_taken, decided_at
               FROM contest_decisions
               WHERE contest_id = ?
               ORDER BY decided_at ASC""",
            [contest_id],
        ).fetchall()

        return [
            ContestDecision(
                decision_id=row[0],
                contest_id=row[1],
                reviewer_id=row[2],
                accepted=row[3],
                reasoning=row[4],
                actions_taken=(
                    row[5] if isinstance(row[5], list) else json.loads(row[5])
                ),
                decided_at=row[6],
            )
            for row in rows
        ]

    def pending_count(self) -> int:
        """Count of submitted + in_review items."""
        row = self._conn.execute(
            """SELECT COUNT(*) FROM contest_submissions
               WHERE status IN ('submitted', 'in_review')"""
        ).fetchone()
        return int(row[0]) if row else 0

    def get_stats(self) -> ContestStats:
        """Aggregate statistics."""
        rows = self._conn.execute(
            "SELECT status FROM contest_submissions"
        ).fetchall()
        total_in_review = sum(1 for r in rows if r[0] == ContestStatus.in_review)
        total_accepted = sum(
            1 for r in rows if r[0] == ContestStatus.resolved_accepted
        )
        total_rejected = sum(
            1 for r in rows if r[0] == ContestStatus.resolved_rejected
        )
        total_resolved = total_accepted + total_rejected

        # Compute resolution days for resolved items
        resolution_rows = self._conn.execute(
            """SELECT s.submitted_at, d.decided_at
               FROM contest_submissions s
               JOIN (
                   SELECT contest_id, MAX(decided_at) AS decided_at
                   FROM contest_decisions GROUP BY contest_id
               ) d ON s.contest_id = d.contest_id
               WHERE s.status IN ('resolved_accepted', 'resolved_rejected')"""
        ).fetchall()

        median_days: float | None = None
        p95_days: float | None = None
        if resolution_rows:
            days_list = sorted(
                (r[1] - r[0]).total_seconds() / 86400.0 for r in resolution_rows
            )
            median_days = statistics.median(days_list)
            p95_index = int(0.95 * len(days_list))
            p95_index = min(p95_index, len(days_list) - 1)
            p95_days = days_list[p95_index]

        return ContestStats(
            total_submitted=len(rows),
            total_in_review=total_in_review,
            total_resolved=total_resolved,
            total_accepted=total_accepted,
            total_rejected=total_rejected,
            median_resolution_days=median_days,
            p95_resolution_days=p95_days,
        )

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()
