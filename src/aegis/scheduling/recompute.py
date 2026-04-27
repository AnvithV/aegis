"""Nightly score recomputation — idempotent, resumable, DuckDB-logged."""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime

import duckdb
from pydantic import BaseModel, ConfigDict

from aegis.scoring.candidate_vector import (
    ArtifactWeight,
    CandidateVectorBuilder,
)
from aegis.scoring.quality_prior import QualityPrior

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS recompute_log (
    candidate_uuid TEXT NOT NULL,
    quality_score_raw DOUBLE NOT NULL,
    quality_percentile DOUBLE NOT NULL,
    vector_nonzero_dims INTEGER NOT NULL,
    artifact_set_hash TEXT NOT NULL,
    weight_version INTEGER NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (candidate_uuid, weight_version)
);
"""


class RecomputeResult(BaseModel):
    """Summary of a batch recomputation run."""

    model_config = ConfigDict(frozen=True)

    cohort_id: str
    total_candidates: int
    recomputed_count: int
    skipped_count: int
    failed_count: int
    elapsed_seconds: float
    weight_version: int
    idempotent: bool


class CandidateRecomputeRecord(BaseModel):
    """Record of a single candidate's recomputed score."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    quality_score_raw: float
    quality_percentile: float
    vector_nonzero_dims: int
    artifact_set_hash: str
    weight_version: int
    computed_at: str


class ScoreRecomputer:
    """Idempotent score recomputer with DuckDB logging."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)

    @staticmethod
    def compute_artifact_set_hash(
        artifact_ids: list[str],
    ) -> str:
        """Deterministic hash of a sorted artifact ID set."""
        joined = "|".join(sorted(artifact_ids))
        return hashlib.sha256(joined.encode()).hexdigest()

    def is_up_to_date(
        self,
        candidate_uuid: str,
        artifact_set_hash: str,
        weight_version: int,
    ) -> bool:
        """Check if a candidate already has a current recompute record."""
        result = self._conn.execute(
            "SELECT 1 FROM recompute_log "
            "WHERE candidate_uuid = ? "
            "AND artifact_set_hash = ? "
            "AND weight_version = ?",
            [candidate_uuid, artifact_set_hash, weight_version],
        ).fetchone()
        return result is not None

    def recompute_candidate(
        self,
        candidate_uuid: str,
        artifacts: list[ArtifactWeight],
        quality_prior: QualityPrior,
        component_percentiles: dict[str, float],
    ) -> CandidateRecomputeRecord:
        """Recompute a single candidate's score and vector."""
        cvb = CandidateVectorBuilder()
        vec = cvb.build(artifacts)

        raw_score = quality_prior.compute_raw(component_percentiles)
        artifact_ids = [a.pmid for a in artifacts]
        artifact_hash = self.compute_artifact_set_hash(artifact_ids)

        return CandidateRecomputeRecord(
            candidate_uuid=candidate_uuid,
            quality_score_raw=round(raw_score, 8),
            quality_percentile=0.0,  # percentile requires cohort context
            vector_nonzero_dims=vec.nonzero_count(),
            artifact_set_hash=artifact_hash,
            weight_version=quality_prior.weight_vector.version,
            computed_at=datetime.now(tz=UTC).isoformat(),
        )

    def record_recompute(
        self,
        record: CandidateRecomputeRecord,
    ) -> None:
        """Persist a recompute record to the log."""
        self._conn.execute(
            "INSERT OR REPLACE INTO recompute_log "
            "(candidate_uuid, quality_score_raw, quality_percentile, "
            "vector_nonzero_dims, artifact_set_hash, weight_version, "
            "computed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                record.candidate_uuid,
                record.quality_score_raw,
                record.quality_percentile,
                record.vector_nonzero_dims,
                record.artifact_set_hash,
                record.weight_version,
                record.computed_at,
            ],
        )

    def recompute_batch(
        self,
        cohort_id: str,
        candidates: list[
            tuple[str, list[ArtifactWeight], dict[str, float]]
        ],
        quality_prior: QualityPrior,
    ) -> RecomputeResult:
        """Recompute scores for a batch of candidates.

        Each entry is (candidate_uuid, artifacts, component_percentiles).
        Skips candidates that are already up-to-date. Records results.
        """
        t0 = time.monotonic()
        weight_version = quality_prior.weight_vector.version
        recomputed = 0
        skipped = 0
        failed = 0

        for uuid, artifacts, comp_pcts in candidates:
            artifact_ids = [a.pmid for a in artifacts]
            artifact_hash = self.compute_artifact_set_hash(artifact_ids)

            if self.is_up_to_date(uuid, artifact_hash, weight_version):
                skipped += 1
                continue

            try:
                record = self.recompute_candidate(
                    uuid, artifacts, quality_prior, comp_pcts,
                )
                self.record_recompute(record)
                recomputed += 1
            except Exception:  # noqa: BLE001
                failed += 1

        elapsed = time.monotonic() - t0

        return RecomputeResult(
            cohort_id=cohort_id,
            total_candidates=len(candidates),
            recomputed_count=recomputed,
            skipped_count=skipped,
            failed_count=failed,
            elapsed_seconds=round(elapsed, 4),
            weight_version=weight_version,
            idempotent=True,
        )

    def get_latest_records(
        self,
        weight_version: int,
    ) -> list[CandidateRecomputeRecord]:
        """Retrieve all records for a given weight version."""
        rows = self._conn.execute(
            "SELECT candidate_uuid, quality_score_raw, "
            "quality_percentile, vector_nonzero_dims, "
            "artifact_set_hash, weight_version, computed_at "
            "FROM recompute_log WHERE weight_version = ? "
            "ORDER BY candidate_uuid",
            [weight_version],
        ).fetchall()
        return [
            CandidateRecomputeRecord(
                candidate_uuid=row[0],
                quality_score_raw=row[1],
                quality_percentile=row[2],
                vector_nonzero_dims=row[3],
                artifact_set_hash=row[4],
                weight_version=row[5],
                computed_at=row[6],
            )
            for row in rows
        ]
