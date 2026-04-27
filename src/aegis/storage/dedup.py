"""Artifact deduplication across sources with cross-reference preservation."""

from __future__ import annotations

import uuid as _uuid
from enum import StrEnum

import duckdb
from pydantic import BaseModel, ConfigDict


class CanonicalSource(StrEnum):
    """Mapping of artifact types to their canonical source."""

    publication = "pubmed"
    grant = "reporter"
    trial = "ctgov"


# Lookup from artifact type to canonical source name
_CANONICAL_MAP: dict[str, str] = {
    "publication": CanonicalSource.publication,
    "grant": CanonicalSource.grant,
    "trial": CanonicalSource.trial,
}


class CrossReference(BaseModel):
    """An edge linking two artifact records discovered via different sources."""

    model_config = ConfigDict(frozen=True)

    ref_id: str
    source_artifact_type: str
    source_artifact_id: str
    target_artifact_type: str
    target_artifact_id: str
    relationship: str
    discovered_via: str


_CROSS_REF_DDL = """\
CREATE TABLE IF NOT EXISTS cross_references (
    ref_id TEXT PRIMARY KEY,
    source_artifact_type TEXT NOT NULL,
    source_artifact_id TEXT NOT NULL,
    target_artifact_type TEXT NOT NULL,
    target_artifact_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    discovered_via TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT current_timestamp
);
CREATE INDEX IF NOT EXISTS idx_xref_source
    ON cross_references(source_artifact_id);
CREATE INDEX IF NOT EXISTS idx_xref_target
    ON cross_references(target_artifact_id);
"""

_ARTIFACTS_DDL = """\
CREATE TABLE IF NOT EXISTS canonical_artifacts (
    artifact_type TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (artifact_type, artifact_id)
);
"""


class ArtifactDeduplicator:
    """De-duplicates artifacts by canonical source and preserves cross-references."""

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute(_ARTIFACTS_DDL)
        for stmt in _CROSS_REF_DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                self._conn.execute(stmt)

    def deduplicate(
        self, artifact_type: str, artifact_id: str, source: str
    ) -> tuple[str, bool]:
        """Return ``(canonical_id, is_new)``.

        If *source* is the canonical source for *artifact_type*, the artifact
        is stored (or recognised as already present).  If *source* is not
        canonical, a cross-reference edge is created pointing from this
        occurrence to the canonical record and ``is_new`` is ``False``.
        """
        canonical_source = _CANONICAL_MAP.get(artifact_type, source)

        if source == canonical_source:
            # This is the canonical source — insert if not already present
            existing = self._conn.execute(
                "SELECT artifact_id FROM canonical_artifacts "
                "WHERE artifact_type = ? AND artifact_id = ?",
                [artifact_type, artifact_id],
            ).fetchone()
            if existing is not None:
                return (artifact_id, False)
            self._conn.execute(
                "INSERT INTO canonical_artifacts (artifact_type, artifact_id, source) "
                "VALUES (?, ?, ?)",
                [artifact_type, artifact_id, source],
            )
            return (artifact_id, True)

        # Non-canonical source.  Check whether we already recorded this
        # exact cross-reference (idempotency).
        already_xref = self._conn.execute(
            "SELECT 1 FROM cross_references "
            "WHERE source_artifact_type = ? "
            "AND source_artifact_id = ? "
            "AND discovered_via = ?",
            [artifact_type, artifact_id, source],
        ).fetchone()
        if already_xref is not None:
            return (artifact_id, False)

        # Record a cross-reference edge.  The canonical record may or may not
        # exist yet; we still record the edge so the graph is complete.
        self.add_cross_reference(
            CrossReference(
                ref_id=str(_uuid.uuid4()),
                source_artifact_type=artifact_type,
                source_artifact_id=artifact_id,
                target_artifact_type=artifact_type,
                target_artifact_id=artifact_id,
                relationship="references",
                discovered_via=source,
            )
        )
        return (artifact_id, False)

    def add_cross_reference(self, cross_ref: CrossReference) -> None:
        """Persist a :class:`CrossReference` edge."""
        self._conn.execute(
            "INSERT INTO cross_references "
            "(ref_id, source_artifact_type, source_artifact_id, "
            "target_artifact_type, target_artifact_id, relationship, "
            "discovered_via) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                cross_ref.ref_id,
                cross_ref.source_artifact_type,
                cross_ref.source_artifact_id,
                cross_ref.target_artifact_type,
                cross_ref.target_artifact_id,
                cross_ref.relationship,
                cross_ref.discovered_via,
            ],
        )

    def get_cross_references(self, artifact_id: str) -> list[CrossReference]:
        """Return all cross-references mentioning *artifact_id*."""
        rows = self._conn.execute(
            "SELECT ref_id, source_artifact_type, source_artifact_id, "
            "target_artifact_type, target_artifact_id, relationship, "
            "discovered_via "
            "FROM cross_references "
            "WHERE source_artifact_id = ? OR target_artifact_id = ?",
            [artifact_id, artifact_id],
        ).fetchall()
        return [
            CrossReference(
                ref_id=r[0],
                source_artifact_type=r[1],
                source_artifact_id=r[2],
                target_artifact_type=r[3],
                target_artifact_id=r[4],
                relationship=r[5],
                discovered_via=r[6],
            )
            for r in rows
        ]

    def deduplicate_batch(
        self, artifacts: list[tuple[str, str, str]]
    ) -> list[tuple[str, bool]]:
        """Deduplicate a batch of ``(artifact_type, artifact_id, source)`` tuples."""
        return [
            self.deduplicate(artifact_type, artifact_id, source)
            for artifact_type, artifact_id, source in artifacts
        ]

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()
