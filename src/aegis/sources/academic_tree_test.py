"""Tests for Academic Family Tree source client."""

from __future__ import annotations

from aegis.sources.academic_tree import AcademicTreeStore, MentorEdge


def _make_edge(
    mentor: str = "Prof A",
    mentee: str = "Dr B",
    confidence: float = 0.9,
    year: int | None = None,
) -> MentorEdge:
    return MentorEdge(
        mentor_name=mentor,
        mentee_name=mentee,
        mentor_institution=None,
        mentee_institution=None,
        relationship_type="PhD advisor",
        year=year,
        confidence=confidence,
    )


def test_get_mentees() -> None:
    store = AcademicTreeStore()
    store.add_batch([
        _make_edge("Prof A", "Dr B"),
        _make_edge("Prof A", "Dr C"),
        _make_edge("Prof X", "Dr Y"),
    ])

    mentees = store.get_mentees("Prof A")
    assert len(mentees) == 2
    assert {e.mentee_name for e in mentees} == {"Dr B", "Dr C"}

    mentees_x = store.get_mentees("Prof X")
    assert len(mentees_x) == 1


def test_get_lineage_depth() -> None:
    store = AcademicTreeStore()
    # Build a 3-level chain: A -> B -> C -> D
    store.add_batch([
        _make_edge("Prof A", "Dr B"),
        _make_edge("Dr B", "Dr C"),
        _make_edge("Dr C", "Dr D"),
    ])

    # D is at depth 3 from A (D -> C -> B -> A)
    depth_d = store.get_lineage_depth("Dr D")
    assert depth_d == 3

    # B is at depth 1 (B -> A)
    depth_b = store.get_lineage_depth("Dr B")
    assert depth_b == 1

    # A is at depth 0 (no mentors)
    depth_a = store.get_lineage_depth("Prof A")
    assert depth_a == 0


def test_lineage_depth_cycle_safe() -> None:
    store = AcademicTreeStore()
    # Create a cycle: A -> B -> C -> A
    store.add_batch([
        _make_edge("Prof A", "Dr B"),
        _make_edge("Dr B", "Dr C"),
        _make_edge("Dr C", "Prof A"),
    ])

    # Should not infinite-loop; depth should be finite
    depth = store.get_lineage_depth("Dr C")
    assert depth >= 0
    assert depth <= 5  # bounded by max_depth default
