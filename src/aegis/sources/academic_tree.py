"""Academic Family Tree (academictree.org) data client for mentorship lineage."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class MentorEdge(BaseModel):
    """A mentor-mentee relationship edge."""

    model_config = ConfigDict(frozen=True)

    mentor_name: str
    mentee_name: str
    mentor_institution: str | None
    mentee_institution: str | None
    relationship_type: str | None  # "PhD advisor", "Postdoc mentor", etc.
    year: int | None
    confidence: float  # linkage confidence to cohort candidate


class AcademicTreeStore:
    """In-memory store for academic lineage data.

    Coverage is ~30% of biomed researchers.
    Phase 1 loads from bulk export; Phase 3 adds live API.
    """

    def __init__(self) -> None:
        self._edges: list[MentorEdge] = []

    def add_batch(self, edges: list[MentorEdge]) -> None:
        self._edges.extend(edges)

    def get_mentees(self, mentor_name: str) -> list[MentorEdge]:
        """Get all mentees for a given mentor (case-insensitive)."""
        name_lower = mentor_name.lower()
        return [e for e in self._edges if e.mentor_name.lower() == name_lower]

    def get_mentors(self, mentee_name: str) -> list[MentorEdge]:
        """Get all mentors for a given mentee (case-insensitive)."""
        name_lower = mentee_name.lower()
        return [e for e in self._edges if e.mentee_name.lower() == name_lower]

    def get_lineage_depth(self, name: str, max_depth: int = 5) -> int:
        """BFS up the mentor chain to find lineage depth."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(name.lower(), 0)]
        max_found = 0

        while queue:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            max_found = max(max_found, depth)

            if depth >= max_depth:
                continue

            for edge in self._edges:
                if edge.mentee_name.lower() == current:
                    queue.append((edge.mentor_name.lower(), depth + 1))

        return max_found

    def count(self) -> int:
        return len(self._edges)
