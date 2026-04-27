"""Per-specialty inverted index for clinician corpus scale queries."""

from __future__ import annotations

import logging
import time

import duckdb
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_INDEX_DDL = """
CREATE TABLE IF NOT EXISTS clinician_specialty_index (
    taxonomy_code TEXT NOT NULL,
    npi TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    practice_state TEXT,
    practice_city TEXT,
    practice_zip TEXT,
    PRIMARY KEY (taxonomy_code, npi)
);

CREATE INDEX IF NOT EXISTS idx_clinician_taxonomy
    ON clinician_specialty_index(taxonomy_code);

CREATE INDEX IF NOT EXISTS idx_clinician_state
    ON clinician_specialty_index(practice_state);

CREATE INDEX IF NOT EXISTS idx_clinician_zip
    ON clinician_specialty_index(practice_zip);
"""


class ClinicianLookupResult(BaseModel):
    """Result of a clinician specialty lookup."""

    model_config = ConfigDict(frozen=True)

    npi: str
    provider_name: str
    taxonomy_code: str
    practice_state: str | None
    practice_city: str | None


class ClinicianIndex:
    """Per-specialty inverted index for fast clinician lookups.

    Keyed by NUCC taxonomy code for O(specialty_cohort) queries
    instead of O(1.6M) full scans.
    """

    def __init__(self, db_path: str = "aegis.duckdb") -> None:
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_INDEX_DDL)

    def insert(
        self,
        taxonomy_code: str,
        npi: str,
        provider_name: str,
        practice_state: str | None = None,
        practice_city: str | None = None,
        practice_zip: str | None = None,
    ) -> None:
        """Insert a clinician into the specialty index."""
        self._conn.execute(
            """
            INSERT INTO clinician_specialty_index
                (taxonomy_code, npi, provider_name, practice_state,
                 practice_city, practice_zip)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (taxonomy_code, npi) DO UPDATE SET
                provider_name = excluded.provider_name,
                practice_state = excluded.practice_state,
                practice_city = excluded.practice_city,
                practice_zip = excluded.practice_zip
            """,
            [
                taxonomy_code,
                npi,
                provider_name,
                practice_state,
                practice_city,
                practice_zip,
            ],
        )

    def insert_batch(
        self,
        records: list[
            tuple[str, str, str, str | None, str | None, str | None]
        ],
    ) -> int:
        """Batch insert clinicians into the specialty index.

        Each tuple: (taxonomy_code, npi, provider_name, state, city, zip).
        Returns number of records inserted.
        """
        for record in records:
            self.insert(*record)
        return len(records)

    def lookup_by_specialty(
        self,
        taxonomy_code: str,
        state: str | None = None,
        limit: int = 1000,
    ) -> list[ClinicianLookupResult]:
        """Look up clinicians by NUCC taxonomy code.

        Optional state filter for geographic scoping.
        """
        t0 = time.perf_counter()
        if state:
            rows = self._conn.execute(
                """
                SELECT npi, provider_name, taxonomy_code,
                       practice_state, practice_city
                FROM clinician_specialty_index
                WHERE taxonomy_code = ? AND practice_state = ?
                LIMIT ?
                """,
                [taxonomy_code, state, limit],
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT npi, provider_name, taxonomy_code,
                       practice_state, practice_city
                FROM clinician_specialty_index
                WHERE taxonomy_code = ?
                LIMIT ?
                """,
                [taxonomy_code, limit],
            ).fetchall()

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            "lookup_by_specialty(%s, state=%s) -> %d rows in %.1fms",
            taxonomy_code,
            state,
            len(rows),
            elapsed_ms,
        )

        return [
            ClinicianLookupResult(
                npi=r[0],
                provider_name=r[1],
                taxonomy_code=r[2],
                practice_state=r[3],
                practice_city=r[4],
            )
            for r in rows
        ]

    def count_by_specialty(self, taxonomy_code: str) -> int:
        """Count clinicians in a specialty."""
        result = self._conn.execute(
            "SELECT COUNT(*) FROM clinician_specialty_index "
            "WHERE taxonomy_code = ?",
            [taxonomy_code],
        ).fetchone()
        return int(result[0]) if result else 0

    def total_count(self) -> int:
        """Total clinicians in the index."""
        result = self._conn.execute(
            "SELECT COUNT(*) FROM clinician_specialty_index"
        ).fetchone()
        return int(result[0]) if result else 0

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()
