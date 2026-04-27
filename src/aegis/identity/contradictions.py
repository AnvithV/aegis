"""Affiliation contradiction detection and logging."""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import UTC, datetime
from enum import StrEnum

import duckdb
from pydantic import BaseModel, ConfigDict

from aegis.identity.ror import RorResolver

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS contradiction_log (
    record_id TEXT PRIMARY KEY,
    candidate_uuid TEXT NOT NULL,
    source_a TEXT NOT NULL,
    source_b TEXT NOT NULL,
    affiliation_a TEXT NOT NULL,
    affiliation_b TEXT NOT NULL,
    ror_a TEXT,
    ror_b TEXT,
    severity TEXT NOT NULL,
    resolution TEXT NOT NULL,
    flagged_for_review BOOLEAN NOT NULL,
    detected_at TIMESTAMP NOT NULL
);
"""

# Org-type classification based on ROR canonical name heuristics.
_INDUSTRY_KEYWORDS = frozenset({
    "pharma",
    "therapeutics",
    "biosciences",
    "biotech",
    "inc",
    "corp",
    "ltd",
    "gmbh",
    "labs",
    "laboratories",
})

_ACADEMIC_KEYWORDS = frozenset({
    "university",
    "college",
    "institute",
    "school",
    "hospital",
    "medical center",
    "cancer center",
    "cancer centre",
    "clinic",
    "national",
    "centre",
    "center",
})


class ContradictionSeverity(StrEnum):
    """Severity of an affiliation contradiction."""

    minor = "minor"
    major = "major"


class ContradictionRecord(BaseModel):
    """A detected affiliation contradiction."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    candidate_uuid: str
    source_a: str
    source_b: str
    affiliation_a: str
    affiliation_b: str
    ror_a: str | None
    ror_b: str | None
    severity: ContradictionSeverity
    resolution: str
    flagged_for_review: bool
    detected_at: datetime


class ContradictionHandler:
    """Detect and log affiliation contradictions."""

    def __init__(
        self,
        ror_resolver: RorResolver,
        db_path: str = "aegis.duckdb",
    ) -> None:
        self._ror = ror_resolver
        self._conn = duckdb.connect(db_path)
        self._conn.execute(_CREATE_TABLE)

    def detect(
        self,
        candidate_uuid: str,
        source_a: str,
        affiliation_a: str,
        source_b: str,
        affiliation_b: str,
    ) -> ContradictionRecord | None:
        """Detect contradiction between two affiliation sources.

        Returns None if both resolve to the same ROR ID (no contradiction).
        Never raises — records and returns.
        """
        try:
            return self._detect_impl(
                candidate_uuid,
                source_a,
                affiliation_a,
                source_b,
                affiliation_b,
            )
        except Exception:
            logger.exception(
                "Error detecting contradiction for %s",
                candidate_uuid,
            )
            return None

    def _detect_impl(
        self,
        candidate_uuid: str,
        source_a: str,
        affiliation_a: str,
        source_b: str,
        affiliation_b: str,
    ) -> ContradictionRecord | None:
        """Core detection logic."""
        ror_a = self._ror.resolve(affiliation_a)
        ror_b = self._ror.resolve(affiliation_b)

        ror_id_a = ror_a.ror_id if ror_a else None
        ror_id_b = ror_b.ror_id if ror_b else None

        # Same ROR ID -> no contradiction
        if ror_id_a is not None and ror_id_a == ror_id_b:
            return None

        # Classify severity
        country_a = ror_a.country if ror_a else None
        country_b = ror_b.country if ror_b else None

        # Use both raw input and ROR canonical name for org-type
        # classification — raw input may contain industry keywords
        # that the fuzzy-matched ROR name does not.
        names_a = [affiliation_a]
        if ror_a:
            names_a.append(ror_a.canonical_name)
        names_b = [affiliation_b]
        if ror_b:
            names_b.append(ror_b.canonical_name)

        severity = self._classify_severity(
            country_a, country_b, names_a, names_b
        )
        flagged = severity == ContradictionSeverity.major

        record = ContradictionRecord(
            record_id=str(_uuid.uuid4()),
            candidate_uuid=candidate_uuid,
            source_a=source_a,
            source_b=source_b,
            affiliation_a=affiliation_a,
            affiliation_b=affiliation_b,
            ror_a=ror_id_a,
            ror_b=ror_id_b,
            severity=severity,
            resolution="prefer_artifact",
            flagged_for_review=flagged,
            detected_at=datetime.now(UTC),
        )

        self._persist(record)
        return record

    def get_contradictions(
        self, candidate_uuid: str
    ) -> list[ContradictionRecord]:
        """List all contradictions for a candidate."""
        rows = self._conn.execute(
            "SELECT * FROM contradiction_log "
            "WHERE candidate_uuid = ? "
            "ORDER BY detected_at",
            [candidate_uuid],
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_flagged(self) -> list[ContradictionRecord]:
        """List all flagged (major) contradictions."""
        rows = self._conn.execute(
            "SELECT * FROM contradiction_log "
            "WHERE flagged_for_review = true "
            "ORDER BY detected_at",
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()

    def _persist(self, record: ContradictionRecord) -> None:
        """Insert contradiction record into the log."""
        self._conn.execute(
            """
            INSERT INTO contradiction_log
                (record_id, candidate_uuid, source_a, source_b,
                 affiliation_a, affiliation_b, ror_a, ror_b,
                 severity, resolution, flagged_for_review,
                 detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.record_id,
                record.candidate_uuid,
                record.source_a,
                record.source_b,
                record.affiliation_a,
                record.affiliation_b,
                record.ror_a,
                record.ror_b,
                record.severity.value,
                record.resolution,
                record.flagged_for_review,
                record.detected_at.isoformat(),
            ],
        )

    @staticmethod
    def _row_to_record(row: tuple[object, ...]) -> ContradictionRecord:
        """Convert a DuckDB row to ContradictionRecord."""
        detected_at = row[11]
        if isinstance(detected_at, str):
            detected_at = datetime.fromisoformat(detected_at)
        if not isinstance(detected_at, datetime):
            detected_at = datetime.now(UTC)
        # Ensure timezone-aware
        if detected_at.tzinfo is None:
            detected_at = detected_at.replace(tzinfo=UTC)

        return ContradictionRecord(
            record_id=str(row[0]),
            candidate_uuid=str(row[1]),
            source_a=str(row[2]),
            source_b=str(row[3]),
            affiliation_a=str(row[4]),
            affiliation_b=str(row[5]),
            ror_a=str(row[6]) if row[6] is not None else None,
            ror_b=str(row[7]) if row[7] is not None else None,
            severity=ContradictionSeverity(str(row[8])),
            resolution=str(row[9]),
            flagged_for_review=bool(row[10]),
            detected_at=detected_at,
        )

    @staticmethod
    def _classify_severity(
        country_a: str | None,
        country_b: str | None,
        names_a: list[str],
        names_b: list[str],
    ) -> ContradictionSeverity:
        """Classify contradiction severity."""
        # Different countries -> major
        if (
            country_a is not None
            and country_b is not None
            and country_a != country_b
        ):
            return ContradictionSeverity.major

        # Check org type mismatch using all available name signals
        type_a = _classify_org_type_multi(names_a)
        type_b = _classify_org_type_multi(names_b)
        if type_a != type_b and type_a != "unknown" and type_b != "unknown":
            return ContradictionSeverity.major

        return ContradictionSeverity.minor


def _classify_org_type(name: str) -> str:
    """Classify an organization as academic, industry, or unknown."""
    lower = name.lower()
    for keyword in _INDUSTRY_KEYWORDS:
        if keyword in lower:
            return "industry"
    for keyword in _ACADEMIC_KEYWORDS:
        if keyword in lower:
            return "academic"
    return "unknown"


def _classify_org_type_multi(names: list[str]) -> str:
    """Classify org type from multiple name signals.

    Returns the first non-unknown classification, preferring industry
    detection (since industry keywords are more specific).
    """
    for name in names:
        result = _classify_org_type(name)
        if result != "unknown":
            return result
    return "unknown"
