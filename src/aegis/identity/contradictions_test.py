"""Tests for the affiliation contradiction handler."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from aegis.identity.contradictions import (
    ContradictionHandler,
    ContradictionSeverity,
)
from aegis.identity.ror import RorResolver


@pytest.fixture()
def ror_resolver() -> RorResolver:
    """Create a ROR resolver."""
    return RorResolver()


@pytest.fixture()
def handler(
    tmp_path: Path, ror_resolver: RorResolver
) -> Generator[ContradictionHandler]:
    """Create a ContradictionHandler with temporary DB."""
    db_path = str(tmp_path / "test.duckdb")
    h = ContradictionHandler(ror_resolver, db_path=db_path)
    yield h
    h.close()


def test_no_contradiction_same_ror(
    handler: ContradictionHandler,
) -> None:
    """Both affiliations resolve to same ROR -> returns None."""
    result = handler.detect(
        candidate_uuid="cand-1",
        source_a="pubmed",
        affiliation_a="MGH",
        source_b="reporter",
        affiliation_b="Massachusetts General Hospital",
    )
    assert result is None


def test_minor_contradiction_same_country(
    handler: ContradictionHandler,
) -> None:
    """Different orgs, same country, both academic -> minor, not flagged."""
    result = handler.detect(
        candidate_uuid="cand-2",
        source_a="pubmed",
        affiliation_a="Harvard Medical School",
        source_b="reporter",
        affiliation_b="Stanford University",
    )
    assert result is not None
    assert result.severity == ContradictionSeverity.minor
    assert result.flagged_for_review is False
    assert result.resolution == "prefer_artifact"


def test_major_contradiction_academia_vs_industry(
    handler: ContradictionHandler,
) -> None:
    """One academic, one industry -> major, flagged."""
    result = handler.detect(
        candidate_uuid="cand-3",
        source_a="pubmed",
        affiliation_a="Harvard Medical School",
        source_b="linkedin",
        affiliation_b="Novartis Pharma AG",
    )
    assert result is not None
    assert result.severity == ContradictionSeverity.major
    assert result.flagged_for_review is True


def test_major_contradiction_cross_country(
    handler: ContradictionHandler,
) -> None:
    """Same org type but different countries -> major, flagged."""
    result = handler.detect(
        candidate_uuid="cand-4",
        source_a="pubmed",
        affiliation_a="Harvard Medical School",
        source_b="reporter",
        affiliation_b="University of Oxford",
    )
    assert result is not None
    assert result.severity == ContradictionSeverity.major
    assert result.flagged_for_review is True


def test_append_only_log(
    handler: ContradictionHandler,
) -> None:
    """Detect 3 contradictions, assert all 3 in log."""
    cand = "cand-5"
    pairs = [
        ("Harvard Medical School", "Stanford University"),
        ("Harvard Medical School", "Duke University"),
        ("Harvard Medical School", "Yale University"),
    ]
    for aff_a, aff_b in pairs:
        handler.detect(
            candidate_uuid=cand,
            source_a="pubmed",
            affiliation_a=aff_a,
            source_b="reporter",
            affiliation_b=aff_b,
        )

    records = handler.get_contradictions(cand)
    assert len(records) == 3


def test_get_flagged(
    handler: ContradictionHandler,
) -> None:
    """Detect 2 minor + 1 major, assert get_flagged returns only major."""
    # Minor: same country, both academic
    handler.detect(
        candidate_uuid="cand-6a",
        source_a="pubmed",
        affiliation_a="Harvard Medical School",
        source_b="reporter",
        affiliation_b="Stanford University",
    )
    handler.detect(
        candidate_uuid="cand-6b",
        source_a="pubmed",
        affiliation_a="Duke University",
        source_b="reporter",
        affiliation_b="Yale University",
    )

    # Major: cross-country
    handler.detect(
        candidate_uuid="cand-6c",
        source_a="pubmed",
        affiliation_a="Harvard Medical School",
        source_b="reporter",
        affiliation_b="University of Oxford",
    )

    flagged = handler.get_flagged()
    assert len(flagged) == 1
    assert flagged[0].candidate_uuid == "cand-6c"
    assert flagged[0].severity == ContradictionSeverity.major


def test_no_scoring_failure(
    handler: ContradictionHandler,
) -> None:
    """Contradiction does NOT raise — records and returns."""
    # Even with unusual input, should not raise
    result = handler.detect(
        candidate_uuid="cand-7",
        source_a="pubmed",
        affiliation_a="Completely Unknown Lab XYZ",
        source_b="linkedin",
        affiliation_b="Another Unknown Place ABC",
    )
    # Should either return a record or None, never raise
    assert result is None or result.candidate_uuid == "cand-7"
