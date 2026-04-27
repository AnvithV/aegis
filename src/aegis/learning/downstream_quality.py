"""Downstream-task-quality feedback store and pairwise judgment derivation."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aegis.learning.plackett_luce import JudgmentRecord

logger = logging.getLogger(__name__)


class TaskOutcomeCandidate(BaseModel):
    """A candidate who participated in a downstream task."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    candidate_rank: int
    quality_prior_score: float
    topical_fit_score: float
    recency_score: float


class TaskOutcome(BaseModel):
    """Structured outcome of a downstream task for feedback ingestion."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    query_specialty: str
    query_mesh_terms: list[str]
    candidates: list[TaskOutcomeCandidate]
    fleiss_kappa: float | None
    accept_rate: float | None
    consensus_rate: float | None
    submitted_at: datetime
    metadata: dict[str, str]


class DownstreamQualityStore:
    """Append-only JSONL store for downstream task quality outcomes."""

    def __init__(self, *, storage_path: Path) -> None:
        self._path = storage_path

    def append(self, *, outcome: TaskOutcome) -> None:
        """Append a task outcome to the JSONL file."""
        with open(self._path, mode="a", encoding="utf-8") as fh:
            fh.write(outcome.model_dump_json() + "\n")
            fh.flush()

    def load_all(self) -> list[TaskOutcome]:
        """Load all outcomes from the JSONL file.

        Returns an empty list if the file does not exist.
        """
        if not self._path.exists():
            return []
        outcomes: list[TaskOutcome] = []
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    outcomes.append(TaskOutcome.model_validate_json(stripped))
        return outcomes

    def count(self) -> int:
        """Return the number of stored outcomes."""
        return len(self.load_all())

    def by_specialty(self, *, specialty: str) -> list[TaskOutcome]:
        """Filter outcomes by query_specialty."""
        return [o for o in self.load_all() if o.query_specialty == specialty]

    def derive_pairwise_judgments(
        self, *, specialty: str | None = None
    ) -> list[JudgmentRecord]:
        """Convert stored task outcomes into pairwise JudgmentRecord objects.

        For each task outcome with >= 2 candidates:
        1. Compute a composite quality signal per candidate.
        2. Sort candidates by quality_signal descending.
        3. For each adjacent pair (higher, lower), create a JudgmentRecord.
        """
        if specialty is not None:
            outcomes = self.by_specialty(specialty=specialty)
        else:
            outcomes = self.load_all()

        records: list[JudgmentRecord] = []
        for outcome in outcomes:
            if len(outcome.candidates) < 2:
                continue

            # Compute composite quality signal per candidate
            scored: list[tuple[float, TaskOutcomeCandidate]] = []
            for cand in outcome.candidates:
                quality_signal = 0.0
                if outcome.fleiss_kappa is not None:
                    quality_signal += outcome.fleiss_kappa * 0.4
                if outcome.accept_rate is not None:
                    quality_signal += outcome.accept_rate * 0.35
                if outcome.consensus_rate is not None:
                    quality_signal += outcome.consensus_rate * 0.25
                scored.append((quality_signal, cand))

            # Sort by quality_signal descending
            scored.sort(key=lambda x: x[0], reverse=True)

            # Create adjacent pair judgments
            for i in range(len(scored) - 1):
                _, higher = scored[i]
                _, lower = scored[i + 1]
                records.append(
                    JudgmentRecord(
                        winner_scores={
                            "quality_prior": higher.quality_prior_score,
                            "topical_fit": higher.topical_fit_score,
                            "recency": higher.recency_score,
                        },
                        loser_scores={
                            "quality_prior": lower.quality_prior_score,
                            "topical_fit": lower.topical_fit_score,
                            "recency": lower.recency_score,
                        },
                    )
                )

        return records
