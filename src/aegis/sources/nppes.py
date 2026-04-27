"""NPPES/NPI Registry bulk file ingestor."""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Key column indices in NPPES CSV (0-based)
_COL_NPI = 0
_COL_ENTITY_TYPE = 1       # 1=Individual, 2=Organization
_COL_LAST_NAME = 5
_COL_FIRST_NAME = 6
_COL_MIDDLE_NAME = 7
_COL_CREDENTIAL = 10
_COL_TAXONOMY_1 = 47
_COL_LICENSE_STATE_1 = 48
_COL_PRACTICE_ADDR_LINE1 = 28
_COL_PRACTICE_CITY = 30
_COL_PRACTICE_STATE = 31
_COL_PRACTICE_ZIP = 32
_COL_PRACTICE_COUNTRY = 33
_COL_DEACTIVATION_DATE = 39
_COL_REACTIVATION_DATE = 40


class NppesProvider(BaseModel):
    """A single NPI registry provider record."""

    model_config = ConfigDict(frozen=True)

    npi: str
    entity_type: str               # "individual" or "organization"
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    credential: str | None          # e.g., "MD", "DO", "PhD"
    taxonomy_code: str | None       # NUCC taxonomy code (primary)
    license_state: str | None
    practice_address: str | None
    practice_city: str | None
    practice_state: str | None
    practice_zip: str | None
    practice_country: str | None
    is_deactivated: bool


class IngestStats(BaseModel):
    """Statistics from an NPPES bulk ingestion."""

    model_config = ConfigDict(frozen=True)

    total_rows: int
    individuals: int
    organizations: int
    deactivated_skipped: int
    parse_errors: int


class NppesClient:
    """Streaming ingestor for the NPPES bulk CSV file."""

    def bulk_ingest(
        self,
        file_path: Path,
        individuals_only: bool = True,
    ) -> Iterator[NppesProvider]:
        """Stream NPI records from the NPPES bulk CSV.

        The NPPES file is ~6 GB; this uses csv.reader with
        streaming to avoid loading the entire file into memory.

        Args:
            file_path: Path to the NPPES CSV file (npidata_*.csv)
            individuals_only: If True, skip organization records (entity_type=2)

        Yields:
            NppesProvider records for active individual providers.
        """
        with open(file_path, newline="", encoding="utf-8") as f:  # noqa: PTH123
            reader = csv.reader(f)
            # Skip header row
            next(reader, None)

            for row_num, row in enumerate(reader, start=2):
                try:
                    if len(row) < 50:
                        continue

                    entity_type = row[_COL_ENTITY_TYPE].strip()
                    if individuals_only and entity_type != "1":
                        continue

                    # Skip deactivated providers without reactivation
                    deactivation = row[_COL_DEACTIVATION_DATE].strip()
                    reactivation = row[_COL_REACTIVATION_DATE].strip()
                    is_deactivated = bool(deactivation and not reactivation)
                    if is_deactivated:
                        continue

                    npi = row[_COL_NPI].strip()
                    if not npi:
                        continue

                    addr_parts = [
                        row[_COL_PRACTICE_ADDR_LINE1].strip(),
                    ]
                    practice_address = ", ".join(p for p in addr_parts if p) or None

                    et = "individual" if entity_type == "1" else "organization"
                    yield NppesProvider(
                        npi=npi,
                        entity_type=et,
                        first_name=row[_COL_FIRST_NAME].strip() or None,
                        last_name=row[_COL_LAST_NAME].strip() or None,
                        middle_name=row[_COL_MIDDLE_NAME].strip() or None,
                        credential=row[_COL_CREDENTIAL].strip() or None,
                        taxonomy_code=row[_COL_TAXONOMY_1].strip() or None,
                        license_state=row[_COL_LICENSE_STATE_1].strip() or None,
                        practice_address=practice_address,
                        practice_city=row[_COL_PRACTICE_CITY].strip() or None,
                        practice_state=row[_COL_PRACTICE_STATE].strip() or None,
                        practice_zip=row[_COL_PRACTICE_ZIP].strip() or None,
                        practice_country=row[_COL_PRACTICE_COUNTRY].strip() or None,
                        is_deactivated=False,
                    )
                except (IndexError, ValueError) as exc:
                    logger.debug("Parse error at row %d: %s", row_num, exc)

    def ingest_with_stats(
        self,
        file_path: Path,
    ) -> tuple[list[NppesProvider], IngestStats]:
        """Ingest all records and return with statistics.

        For smaller test files; production should use bulk_ingest() iterator.
        """
        providers: list[NppesProvider] = []
        total = 0
        individuals = 0
        organizations = 0
        deactivated = 0
        errors = 0

        with open(file_path, newline="", encoding="utf-8") as f:  # noqa: PTH123
            reader = csv.reader(f)
            next(reader, None)
            for row_num, row in enumerate(reader, start=2):
                total += 1
                try:
                    if len(row) < 50:
                        errors += 1
                        continue
                    entity = row[_COL_ENTITY_TYPE].strip()
                    if entity == "1":
                        individuals += 1
                    else:
                        organizations += 1
                except IndexError:
                    errors += 1

        for provider in self.bulk_ingest(file_path):
            providers.append(provider)

        return providers, IngestStats(
            total_rows=total,
            individuals=individuals,
            organizations=organizations,
            deactivated_skipped=deactivated,
            parse_errors=errors,
        )
