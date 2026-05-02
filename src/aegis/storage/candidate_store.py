"""CandidateStore: DuckDB-backed read/write API for Candidate records."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from aegis.config import get_db_path
from aegis.storage.schema import Candidate

_ARTIFACT_INSERT = (
    "INSERT INTO artifact_refs "
    "(artifact_type, artifact_id, candidate_uuid) "
    "VALUES (?, ?, ?)"
)


class CandidateStore:
    """Persistent store for Candidate records backed by DuckDB."""

    def __init__(self, db_path: str | None = None) -> None:
        self._conn = duckdb.connect(db_path or get_db_path())
        self._run_migrations()

    def _run_migrations(self) -> None:
        migration_dir = Path(__file__).parent / "migrations"
        for sql_file in sorted(migration_dir.glob("*.sql")):
            sql = sql_file.read_text()
            self._conn.execute(sql)

    def upsert(self, candidate: Candidate) -> None:
        """Insert or update a candidate record by UUID."""
        data_json = candidate.model_dump_json()

        # Upsert into candidates table
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO candidates
                (uuid, data, linkage_confidence,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (uuid) DO UPDATE SET
                data = excluded.data,
                linkage_confidence = excluded.linkage_confidence,
                updated_at = excluded.updated_at
            """,
            [
                candidate.uuid,
                data_json,
                candidate.linkage_confidence,
                now,
                now,
            ],
        )

        # Sync strong_keys: delete old, insert current
        self._conn.execute(
            "DELETE FROM strong_keys WHERE candidate_uuid = ?",
            [candidate.uuid],
        )
        for key_type, key_value in candidate.strong_keys.items():
            self._conn.execute(
                """
                INSERT INTO strong_keys
                    (key_type, key_value, candidate_uuid)
                VALUES (?, ?, ?)
                ON CONFLICT (key_type, key_value) DO UPDATE SET
                    candidate_uuid = excluded.candidate_uuid
                """,
                [key_type, key_value, candidate.uuid],
            )

        # Sync artifact_refs: delete old, insert current
        self._conn.execute(
            "DELETE FROM artifact_refs WHERE candidate_uuid = ?",
            [candidate.uuid],
        )
        for pmid in candidate.artifact_refs.pmids:
            self._conn.execute(
                _ARTIFACT_INSERT,
                ["pmid", pmid, candidate.uuid],
            )
        for nct_id in candidate.artifact_refs.nct_ids:
            self._conn.execute(
                _ARTIFACT_INSERT,
                ["nct_id", nct_id, candidate.uuid],
            )
        for grant_id in candidate.artifact_refs.grant_ids:
            self._conn.execute(
                _ARTIFACT_INSERT,
                ["grant_id", grant_id, candidate.uuid],
            )

        # Sync affiliation_history: delete old, insert current
        self._conn.execute(
            "DELETE FROM affiliation_history WHERE candidate_uuid = ?",
            [candidate.uuid],
        )
        for aff in candidate.affiliations:
            self._conn.execute(
                """
                INSERT INTO affiliation_history
                    (candidate_uuid, ror_id, canonical_name,
                     raw_string, country, confidence,
                     start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    candidate.uuid,
                    aff.ror_id,
                    aff.canonical_name,
                    aff.raw_string,
                    aff.country,
                    aff.confidence,
                    aff.start_date,
                    aff.end_date,
                ],
            )

    def get_by_uuid(self, uuid: str) -> Candidate | None:
        """Retrieve a candidate by UUID."""
        result = self._conn.execute(
            "SELECT data FROM candidates WHERE uuid = ?", [uuid]
        ).fetchone()
        if result is None:
            return None
        return Candidate.model_validate_json(result[0])

    def get_by_strong_key(
        self, key_type: str, key_value: str
    ) -> Candidate | None:
        """Retrieve a candidate by a strong identity key."""
        result = self._conn.execute(
            """
            SELECT c.data FROM candidates c
            JOIN strong_keys sk ON c.uuid = sk.candidate_uuid
            WHERE sk.key_type = ? AND sk.key_value = ?
            """,
            [key_type, key_value],
        ).fetchone()
        if result is None:
            return None
        return Candidate.model_validate_json(result[0])

    def list_by_cohort(
        self, cohort_id: str | None = None
    ) -> list[Candidate]:
        """Return all candidates."""
        rows = self._conn.execute(
            "SELECT data FROM candidates"
        ).fetchall()
        return [
            Candidate.model_validate_json(row[0]) for row in rows
        ]

    def count(self) -> int:
        """Return the total number of candidate records."""
        result = self._conn.execute(
            "SELECT COUNT(*) FROM candidates"
        ).fetchone()
        return int(result[0]) if result else 0

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()
