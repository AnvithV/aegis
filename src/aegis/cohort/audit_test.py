"""Tests for the cohort-membership audit log."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis.cohort.audit import AuditAction, CohortAuditLog


@pytest.fixture()
def audit(tmp_path: Path) -> Generator[CohortAuditLog]:
    db_path = str(tmp_path / "test_audit.duckdb")
    a = CohortAuditLog(db_path=db_path)
    yield a
    a.close()


def test_log_add(audit: CohortAuditLog) -> None:
    """Log an addition, retrieve by cohort, assert entry exists."""
    entry = audit.log_add("cohort-1", "uuid-a", "seed_expansion", "pubmed")
    assert entry.action == AuditAction.add
    assert entry.cohort_id == "cohort-1"

    entries = audit.get_log("cohort-1")
    assert len(entries) == 1
    assert entries[0].entry_id == entry.entry_id
    assert entries[0].action == AuditAction.add


def test_log_remove(audit: CohortAuditLog) -> None:
    """Log a removal, retrieve, assert action='remove'."""
    entry = audit.log_remove("cohort-1", "uuid-b", "duplicate", "manual")
    assert entry.action == AuditAction.remove

    entries = audit.get_log("cohort-1")
    assert len(entries) == 1
    assert entries[0].action == AuditAction.remove


def test_get_by_candidate(audit: CohortAuditLog) -> None:
    """Log 3 entries for same candidate across 2 cohorts, query by candidate."""
    audit.log_add("cohort-1", "uuid-c", "seed", "pubmed")
    audit.log_add("cohort-2", "uuid-c", "seed", "nih")
    audit.log_remove("cohort-1", "uuid-c", "duplicate", "manual")

    entries = audit.get_by_candidate("uuid-c")
    assert len(entries) == 3


def test_get_by_reason(audit: CohortAuditLog) -> None:
    """Log 5 entries with different reasons, query by specific reason."""
    audit.log_add("cohort-1", "uuid-1", "seed_expansion", "pubmed")
    audit.log_add("cohort-1", "uuid-2", "seed_expansion", "pubmed")
    audit.log_add("cohort-1", "uuid-3", "manual_add", "manual")
    audit.log_remove("cohort-1", "uuid-4", "duplicate", "system")
    audit.log_remove("cohort-1", "uuid-5", "duplicate", "system")

    seed_entries = audit.get_by_reason("seed_expansion")
    assert len(seed_entries) == 2

    dup_entries = audit.get_by_reason("duplicate")
    assert len(dup_entries) == 2


def test_daily_summary(audit: CohortAuditLog) -> None:
    """Log 3 adds and 1 remove today, assert summary counts."""
    audit.log_add("cohort-1", "uuid-a", "seed", "pubmed")
    audit.log_add("cohort-1", "uuid-b", "seed", "pubmed")
    audit.log_add("cohort-1", "uuid-c", "seed", "nih")
    audit.log_remove("cohort-1", "uuid-a", "duplicate", "system")

    today = datetime.now(UTC).date()
    summary = audit.daily_summary("cohort-1", today)
    assert summary["added"] == 3
    assert summary["removed"] == 1


def test_append_only(audit: CohortAuditLog) -> None:
    """Logging same candidate again creates a new entry, not an update."""
    entry1 = audit.log_add("cohort-1", "uuid-x", "seed", "pubmed")
    entry2 = audit.log_add("cohort-1", "uuid-x", "re-added", "manual")

    assert entry1.entry_id != entry2.entry_id
    entries = audit.get_by_candidate("uuid-x")
    assert len(entries) == 2


def test_chronological_order(audit: CohortAuditLog) -> None:
    """Log 5 entries, retrieve, assert sorted by timestamp ascending."""
    for i in range(5):
        audit.log_add("cohort-1", f"uuid-{i}", "seed", "pubmed")

    entries = audit.get_log("cohort-1")
    assert len(entries) == 5
    for i in range(len(entries) - 1):
        assert entries[i].timestamp <= entries[i + 1].timestamp
