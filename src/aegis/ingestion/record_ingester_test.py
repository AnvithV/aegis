"""Tests for RecordIngester merge-and-upsert layer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from aegis.ingestion.record_ingester import (
    RecordIngester,
    _MAX_EVIDENCE_ITEMS,
    _MAX_MESH_DESCRIPTORS,
    _merge_candidates,
)
from aegis.storage.schema import ArtifactRefBundle, Candidate, MeshDescriptor


def _make_candidate(
    uuid: str = "abc123",
    pmids: list[str] | None = None,
    strong_keys: dict[str, str] | None = None,
    evidence: list[str] | None = None,
    mesh: list[MeshDescriptor] | None = None,
    name: str = "Test Person",
) -> Candidate:
    return Candidate(
        uuid=uuid,
        strong_keys=strong_keys or {},
        name_variants=[name],
        affiliations=[],
        artifact_refs=ArtifactRefBundle(
            pmids=pmids or [], nct_ids=[], grant_ids=[], patent_ids=[]
        ),
        linkage_confidence=0.80,
        evidence_trail=evidence or ["test evidence"],
        last_updated_per_source={"test": datetime.now(UTC)},
        mesh_descriptors=mesh or [],
    )


def test_ingest_new_candidate(tmp_path: pytest.TempPathFactory) -> None:
    """Ingest one new candidate → returns True, new_count == 1."""
    ingester = RecordIngester(db_path=str(tmp_path / "test.duckdb"))  # type: ignore[operator]
    try:
        c = _make_candidate(uuid="new001")
        result = ingester.ingest(c)
        assert result is True
        assert ingester.new_count == 1
        assert ingester.merged_count == 0
    finally:
        ingester.close()


def test_ingest_merge_by_orcid(tmp_path: pytest.TempPathFactory) -> None:
    """Two candidates with same ORCID → second merges, both PMIDs present."""
    ingester = RecordIngester(db_path=str(tmp_path / "test.duckdb"))  # type: ignore[operator]
    try:
        c1 = _make_candidate(
            uuid="orcid_001",
            strong_keys={"orcid": "0000-0001-0000-0001"},
            pmids=["P1"],
        )
        c2 = _make_candidate(
            uuid="orcid_002",
            strong_keys={"orcid": "0000-0001-0000-0001"},
            pmids=["P2"],
        )
        r1 = ingester.ingest(c1)
        r2 = ingester.ingest(c2)
        assert r1 is True
        assert r2 is False
        assert ingester.merged_count == 1

        # Verify merged candidate has both PMIDs
        merged = ingester._store.get_by_uuid("orcid_001")
        assert merged is not None
        assert "P1" in merged.artifact_refs.pmids
        assert "P2" in merged.artifact_refs.pmids
    finally:
        ingester.close()


def test_merge_evidence_cap() -> None:
    """Evidence trail capped at _MAX_EVIDENCE_ITEMS."""
    existing = _make_candidate(
        evidence=[f"evidence_{i}" for i in range(19)]
    )
    new = _make_candidate(
        evidence=[f"new_evidence_{i}" for i in range(5)]
    )
    merged = _merge_candidates(existing, new)
    assert len(merged.evidence_trail) == _MAX_EVIDENCE_ITEMS


def test_merge_mesh_cap() -> None:
    """MeSH descriptors capped at _MAX_MESH_DESCRIPTORS."""
    existing = _make_candidate(
        mesh=[
            MeshDescriptor(descriptor=f"D{i:04d}", qualifier=None, major_topic=False)
            for i in range(29)
        ]
    )
    new = _make_candidate(
        mesh=[
            MeshDescriptor(descriptor=f"N{i:04d}", qualifier=None, major_topic=False)
            for i in range(5)
        ]
    )
    merged = _merge_candidates(existing, new)
    assert len(merged.mesh_descriptors) == _MAX_MESH_DESCRIPTORS


def test_merge_name_variants_deduped() -> None:
    """Name variants are case-insensitively deduped, preserving first-seen case."""
    existing = _make_candidate(name="John Smith")
    new = Candidate(
        uuid="abc123",
        strong_keys={},
        name_variants=["john smith", "J. Smith"],
        affiliations=[],
        artifact_refs=ArtifactRefBundle(pmids=[], nct_ids=[], grant_ids=[], patent_ids=[]),
        linkage_confidence=0.80,
        evidence_trail=["test"],
        last_updated_per_source={"test": datetime.now(UTC)},
        mesh_descriptors=[],
    )
    merged = _merge_candidates(existing, new)
    assert "John Smith" in merged.name_variants
    assert "J. Smith" in merged.name_variants
    # "john smith" should NOT be a separate entry (deduped with "John Smith")
    assert len([n for n in merged.name_variants if n.lower() == "john smith"]) == 1


def test_merge_strong_keys_unioned() -> None:
    """Strong keys from both candidates are unioned."""
    existing = _make_candidate(strong_keys={"orcid": "X"})
    new = _make_candidate(strong_keys={"era_commons": "Y"})
    merged = _merge_candidates(existing, new)
    assert merged.strong_keys == {"orcid": "X", "era_commons": "Y"}


def test_ingest_never_raises(tmp_path: pytest.TempPathFactory) -> None:
    """Ingest catches exceptions, increments error_count."""
    ingester = RecordIngester(db_path=str(tmp_path / "test.duckdb"))  # type: ignore[operator]
    try:
        c = _make_candidate(uuid="err001")
        with patch.object(ingester._store, "upsert", side_effect=RuntimeError("boom")):
            result = ingester.ingest(c)
        assert result is False
        assert ingester.error_count == 1
    finally:
        ingester.close()


def test_cache_prevents_db_lookup(tmp_path: pytest.TempPathFactory) -> None:
    """After first ingest, second ingest with same ORCID uses cache, not DB lookup."""
    ingester = RecordIngester(db_path=str(tmp_path / "test.duckdb"))  # type: ignore[operator]
    try:
        c1 = _make_candidate(
            uuid="cache_001",
            strong_keys={"orcid": "0000-0001-0000-9999"},
            pmids=["P1"],
        )
        ingester.ingest(c1)

        with patch.object(
            ingester._store,
            "get_by_strong_key",
            wraps=ingester._store.get_by_strong_key,
        ) as mock_lookup:
            c2 = _make_candidate(
                uuid="cache_002",
                strong_keys={"orcid": "0000-0001-0000-9999"},
                pmids=["P2"],
            )
            ingester.ingest(c2)
            # Cache should serve the lookup — no DB call to get_by_strong_key
            mock_lookup.assert_not_called()
    finally:
        ingester.close()
