"""USPTO bulk patent ingestion from Google Cloud / Bulk Data Storage System."""

from __future__ import annotations

import gzip
import json
import logging
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from aegis.sources.uspto import InventorAttribution, PatentAssignee, PatentRecord

logger = logging.getLogger(__name__)

USPTO_BULK_URL_TEMPLATE = (
    "https://bulkdata.uspto.gov/data/patent/grant/redbook/fulltext/{year}/"
)


class BulkIngestStats(BaseModel):
    """Statistics from a bulk ingestion run."""

    model_config = ConfigDict(frozen=True)

    total_files_processed: int
    total_patents_parsed: int
    total_patents_failed: int
    elapsed_seconds: float
    patents_per_second: float


class UsptoBulkIngestor:
    """Ingest USPTO patents from bulk dump files (JSONL/XML).

    Historical pull: processes pre-downloaded bulk files from local storage.
    Incremental: processes delta files by grant date.
    """

    def __init__(
        self,
        data_dir: Path,
        workers: int = 4,
    ) -> None:
        self._data_dir = data_dir
        self._workers = workers

    def iter_patents_from_file(
        self, file_path: Path
    ) -> Iterator[PatentRecord]:
        """Parse a single bulk file and yield PatentRecords.

        Supports .jsonl and .jsonl.gz files.
        """
        opener = gzip.open if file_path.suffix == ".gz" else open
        with opener(file_path, "rt", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    record = self._parse_bulk_record(data)
                    if record is not None:
                        yield record
                except (json.JSONDecodeError, KeyError, ValueError) as exc:
                    logger.debug(
                        "Parse error in %s line %d: %s",
                        file_path.name,
                        line_num,
                        exc,
                    )

    def iter_all_patents(
        self,
        since: date | None = None,
    ) -> Iterator[PatentRecord]:
        """Iterate over all patents in the data directory.

        If since is provided, only yield patents granted on or after that date.
        """
        files = sorted(self._data_dir.glob("*.jsonl*"))
        logger.info("Found %d bulk files in %s", len(files), self._data_dir)
        for file_path in files:
            for record in self.iter_patents_from_file(file_path):
                if since and record.grant_date and record.grant_date < since:
                    continue
                yield record

    @staticmethod
    def _parse_bulk_record(data: dict[str, Any]) -> PatentRecord | None:
        """Parse a single record from USPTO bulk JSON format."""
        try:
            inventors = []
            for i, inv in enumerate(data.get("inventors", [])):
                inventors.append(
                    InventorAttribution(
                        inventor_id=inv.get("id", f"bulk-{i}"),
                        full_name=inv.get("name", ""),
                        first_name=inv.get("first_name"),
                        last_name=inv.get("last_name"),
                        is_lead_inventor=(i == 0),
                    )
                )

            assignees = []
            for asg in data.get("assignees", []):
                assignees.append(
                    PatentAssignee(
                        assignee_id=asg.get("id"),
                        organization=asg.get("organization"),
                        assignee_type=asg.get("type", "organization"),
                    )
                )

            grant_date = None
            if data.get("grant_date"):
                grant_date = date.fromisoformat(data["grant_date"])

            return PatentRecord(
                patent_number=data.get("patent_number", ""),
                grant_date=grant_date,
                application_date=(
                    date.fromisoformat(data["application_date"])
                    if data.get("application_date")
                    else None
                ),
                title=data.get("title", ""),
                abstract=data.get("abstract"),
                claims_text=data.get("first_claim"),
                inventors=inventors,
                assignees=assignees,
                cpc_codes=data.get("cpc_codes", []),
                ipc_codes=data.get("ipc_codes", []),
                forward_citation_count=data.get("citation_count", 0),
                family_id=data.get("family_id"),
                maintenance_status=data.get("maintenance_status"),
            )
        except (KeyError, ValueError, TypeError):
            return None
