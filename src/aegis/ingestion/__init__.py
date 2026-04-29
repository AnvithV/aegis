"""Aegis ingestion: event-driven integrity pipeline and refresh orchestration."""

from __future__ import annotations

from aegis.ingestion.event_dispatcher import (
    IntegrityActionType,
    IntegrityEvent,
    IntegrityEventDispatcher,
    IntegritySeverity,
    IntegritySource,
)
from aegis.ingestion.converters import (
    grant_record_to_candidates,
    openalex_work_to_candidates,
    pubmed_record_to_candidates,
    study_record_to_candidates,
)
from aegis.ingestion.orchestrator import (
    RefreshOrchestrator,
    RefreshSummary,
    SourceConfig,
    SourceRefreshResult,
    SourceStatus,
)
from aegis.ingestion.record_ingester import RecordIngester

__all__ = [
    "IntegrityActionType",
    "IntegrityEvent",
    "IntegrityEventDispatcher",
    "IntegritySeverity",
    "IntegritySource",
    "RecordIngester",
    "RefreshOrchestrator",
    "RefreshSummary",
    "SourceConfig",
    "SourceRefreshResult",
    "SourceStatus",
    "grant_record_to_candidates",
    "openalex_work_to_candidates",
    "pubmed_record_to_candidates",
    "study_record_to_candidates",
]
