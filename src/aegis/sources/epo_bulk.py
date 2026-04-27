"""EPO bulk patent ingestion from pre-downloaded feed files."""

from __future__ import annotations

import gzip
import json
import logging
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from aegis.sources.uspto import InventorAttribution, PatentRecord

logger = logging.getLogger(__name__)


class EpoBulkIngestStats(BaseModel):
    """Statistics from an EPO bulk ingestion run."""

    model_config = ConfigDict(frozen=True)

    total_files_processed: int
    total_patents_parsed: int
    total_patents_failed: int
    elapsed_seconds: float


class EpoBulkIngestor:
    """Ingest EPO patents from bulk feed files (JSONL/XML)."""

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
        """Parse a single EPO bulk file and yield PatentRecords."""
        opener = gzip.open if file_path.suffix == ".gz" else open
        with opener(file_path, "rt", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    record = self._parse_epo_record(data)
                    if record is not None:
                        yield record
                except (json.JSONDecodeError, KeyError, ValueError) as exc:
                    logger.debug(
                        "EPO parse error in %s line %d: %s",
                        file_path.name,
                        line_num,
                        exc,
                    )

    def iter_all_patents(
        self,
        since: date | None = None,
    ) -> Iterator[PatentRecord]:
        """Iterate over all EPO patents in the data directory."""
        files = sorted(self._data_dir.glob("*.jsonl*"))
        logger.info("Found %d EPO bulk files in %s", len(files), self._data_dir)
        for file_path in files:
            for record in self.iter_patents_from_file(file_path):
                if since and record.grant_date and record.grant_date < since:
                    continue
                yield record

    @staticmethod
    def _parse_epo_record(data: dict[str, Any]) -> PatentRecord | None:
        """Parse a single record from EPO bulk JSON format."""
        try:
            inventors = []
            for i, inv in enumerate(data.get("inventors", [])):
                inventors.append(
                    InventorAttribution(
                        inventor_id=inv.get("id", f"epo-{i}"),
                        full_name=inv.get("name", ""),
                        first_name=inv.get("first_name"),
                        last_name=inv.get("last_name"),
                        is_lead_inventor=(i == 0),
                    )
                )

            return PatentRecord(
                patent_number=f"EP{data.get('doc_number', '')}",
                grant_date=(
                    date.fromisoformat(data["publication_date"])
                    if data.get("publication_date")
                    else None
                ),
                application_date=(
                    date.fromisoformat(data["application_date"])
                    if data.get("application_date")
                    else None
                ),
                title=data.get("title", ""),
                abstract=data.get("abstract"),
                claims_text=None,
                inventors=inventors,
                assignees=[],
                cpc_codes=data.get("cpc_codes", []),
                ipc_codes=data.get("ipc_codes", []),
                forward_citation_count=0,
                family_id=data.get("family_id"),
                maintenance_status=None,
            )
        except (KeyError, ValueError, TypeError):
            return None
