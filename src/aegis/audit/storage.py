"""Append-only JSONL storage for pairwise judgments."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class PairwiseJudgment(BaseModel):
    """A single pairwise comparison judgment from a reviewer."""

    model_config = ConfigDict(frozen=True)

    judgment_id: str
    reviewer_id: str
    query_mesh_terms: list[str]
    candidate_a_uuid: str
    candidate_b_uuid: str
    winner_uuid: str
    timestamp: datetime
    evidence_shown: dict[str, str]
    session_id: str


class JudgmentStore:
    """Append-only JSONL store for pairwise judgments."""

    def __init__(self, *, storage_path: Path) -> None:
        self._path = storage_path

    def append(self, *, judgment: PairwiseJudgment) -> None:
        """Append a judgment to the JSONL file."""
        with open(self._path, mode="a", encoding="utf-8") as fh:
            fh.write(judgment.model_dump_json() + "\n")
            fh.flush()

    def load_all(self) -> list[PairwiseJudgment]:
        """Load all judgments from the JSONL file.

        Returns an empty list if the file does not exist.
        """
        if not self._path.exists():
            return []
        judgments: list[PairwiseJudgment] = []
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    judgments.append(
                        PairwiseJudgment.model_validate_json(stripped)
                    )
        return judgments

    def count(self) -> int:
        """Return the number of stored judgments."""
        return len(self.load_all())

    def by_reviewer(self, *, reviewer_id: str) -> list[PairwiseJudgment]:
        """Filter judgments by reviewer_id."""
        return [
            j for j in self.load_all() if j.reviewer_id == reviewer_id
        ]
