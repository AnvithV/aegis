"""Per-request audit logging for the Aegis query API.

Every API request is logged with: customer identity, query content,
response candidate UUIDs, served weight version, and integrity rule version.
This enables exact ranking reproduction for compliance review.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class AuditEntry(BaseModel):
    """A single audit log entry for an API request."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    customer_id: str
    customer_name: str
    timestamp: datetime
    endpoint: str
    query_text: str
    expanded_mesh_terms: list[str]
    response_candidate_uuids: list[str]
    weight_version: int
    integrity_rule_version: str
    latency_ms: float
    status_code: int
    cohort_filter: str | None


class AuditLog:
    """Append-only JSONL store for API request audit entries."""

    def __init__(self, *, storage_path: Path) -> None:
        self._path = storage_path

    def append(self, *, entry: AuditEntry) -> None:
        """Append an audit entry to the JSONL file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            f.write(entry.model_dump_json() + "\n")
            f.flush()

    def load_all(self) -> list[AuditEntry]:
        """Load all audit entries from the JSONL file."""
        if not self._path.exists():
            return []
        records: list[AuditEntry] = []
        with open(self._path) as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(
                        AuditEntry.model_validate(json.loads(stripped))
                    )
        return records

    def load_by_customer(self, customer_id: str) -> list[AuditEntry]:
        """Load audit entries for a specific customer."""
        return [e for e in self.load_all() if e.customer_id == customer_id]

    def load_by_request_id(self, request_id: str) -> AuditEntry | None:
        """Look up a specific audit entry by request ID."""
        for e in self.load_all():
            if e.request_id == request_id:
                return e
        return None

    def count(self) -> int:
        """Return total number of audit entries."""
        return len(self.load_all())
