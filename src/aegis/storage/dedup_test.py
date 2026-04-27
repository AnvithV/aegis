"""Tests for artifact deduplication and cross-reference preservation."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from aegis.storage.dedup import ArtifactDeduplicator, CrossReference


@pytest.fixture()
def dedup(tmp_path: Path) -> Generator[ArtifactDeduplicator]:
    """Create an ArtifactDeduplicator backed by a temporary DuckDB file."""
    db_path = str(tmp_path / "test_dedup.duckdb")
    d = ArtifactDeduplicator(db_path=db_path)
    yield d
    d.close()


def test_first_ingestion_is_new(dedup: ArtifactDeduplicator) -> None:
    """Ingest a paper via PubMed (canonical), assert is_new=True."""
    canonical_id, is_new = dedup.deduplicate("publication", "PMID001", "pubmed")
    assert canonical_id == "PMID001"
    assert is_new is True


def test_duplicate_from_same_source(dedup: ArtifactDeduplicator) -> None:
    """Ingest same PMID twice from PubMed, assert second returns is_new=False."""
    dedup.deduplicate("publication", "PMID002", "pubmed")
    canonical_id, is_new = dedup.deduplicate("publication", "PMID002", "pubmed")
    assert canonical_id == "PMID002"
    assert is_new is False

    # Only one canonical record
    count = dedup._conn.execute(
        "SELECT COUNT(*) FROM canonical_artifacts "
        "WHERE artifact_type = 'publication' AND artifact_id = 'PMID002'"
    ).fetchone()
    assert count is not None
    assert count[0] == 1


def test_cross_source_dedup(dedup: ArtifactDeduplicator) -> None:
    """Ingest a paper via PubMed (canonical), then same paper via CT.gov.

    Should produce one canonical record and one cross-reference edge.
    """
    # Canonical ingestion
    _, is_new = dedup.deduplicate("publication", "PMID003", "pubmed")
    assert is_new is True

    # Non-canonical ingestion of same artifact
    canonical_id, is_new = dedup.deduplicate("publication", "PMID003", "ctgov")
    assert canonical_id == "PMID003"
    assert is_new is False

    # Still only one canonical record
    count = dedup._conn.execute(
        "SELECT COUNT(*) FROM canonical_artifacts "
        "WHERE artifact_type = 'publication' AND artifact_id = 'PMID003'"
    ).fetchone()
    assert count is not None
    assert count[0] == 1


def test_cross_reference_preserved(dedup: ArtifactDeduplicator) -> None:
    """After cross-source dedup, get_cross_references returns the CT.gov reference."""
    dedup.deduplicate("publication", "PMID004", "pubmed")
    dedup.deduplicate("publication", "PMID004", "ctgov")

    refs = dedup.get_cross_references("PMID004")
    assert len(refs) == 1
    assert refs[0].discovered_via == "ctgov"
    assert refs[0].source_artifact_id == "PMID004"
    assert refs[0].relationship == "references"


def test_idempotent_rerun(dedup: ArtifactDeduplicator) -> None:
    """Run dedup twice on same data, assert identical state."""
    dedup.deduplicate("publication", "PMID005", "pubmed")
    dedup.deduplicate("publication", "PMID005", "ctgov")

    # Capture state
    artifacts_1 = dedup._conn.execute(
        "SELECT artifact_type, artifact_id, source FROM canonical_artifacts ORDER BY artifact_id"
    ).fetchall()
    xrefs_1 = dedup._conn.execute(
        "SELECT source_artifact_id, target_artifact_id, discovered_via "
        "FROM cross_references ORDER BY source_artifact_id"
    ).fetchall()

    # Re-run the same ingestions
    dedup.deduplicate("publication", "PMID005", "pubmed")
    dedup.deduplicate("publication", "PMID005", "ctgov")

    artifacts_2 = dedup._conn.execute(
        "SELECT artifact_type, artifact_id, source FROM canonical_artifacts ORDER BY artifact_id"
    ).fetchall()
    xrefs_2 = dedup._conn.execute(
        "SELECT source_artifact_id, target_artifact_id, discovered_via "
        "FROM cross_references ORDER BY source_artifact_id"
    ).fetchall()

    assert artifacts_1 == artifacts_2
    assert len(xrefs_1) == len(xrefs_2)


def test_batch_dedup(dedup: ArtifactDeduplicator) -> None:
    """Batch of 10 artifacts, 3 duplicates, assert 7 unique + 3 cross-references."""
    batch: list[tuple[str, str, str]] = [
        # 7 unique canonical publications
        ("publication", "PMID100", "pubmed"),
        ("publication", "PMID101", "pubmed"),
        ("publication", "PMID102", "pubmed"),
        ("publication", "PMID103", "pubmed"),
        ("publication", "PMID104", "pubmed"),
        ("publication", "PMID105", "pubmed"),
        ("publication", "PMID106", "pubmed"),
        # 3 duplicates from non-canonical source
        ("publication", "PMID100", "ctgov"),
        ("publication", "PMID101", "ctgov"),
        ("publication", "PMID102", "ctgov"),
    ]
    results = dedup.deduplicate_batch(batch)
    assert len(results) == 10

    new_count = sum(1 for _, is_new in results if is_new)
    dup_count = sum(1 for _, is_new in results if not is_new)
    assert new_count == 7
    assert dup_count == 3

    # 7 canonical records
    total_artifacts = dedup._conn.execute(
        "SELECT COUNT(*) FROM canonical_artifacts"
    ).fetchone()
    assert total_artifacts is not None
    assert total_artifacts[0] == 7

    # 3 cross-reference edges
    total_xrefs = dedup._conn.execute(
        "SELECT COUNT(*) FROM cross_references"
    ).fetchone()
    assert total_xrefs is not None
    assert total_xrefs[0] == 3
