"""Conference proceedings ingestion (ASCO, ACS, AACR, etc.)."""

from __future__ import annotations

from aegis.sources.conferences.asco import AscoIngestor
from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord, TalkType
from aegis.sources.conferences.failure_log import (
    ConferenceFailureLog,
    ConferenceFailureStats,
    ParseFailure,
)

__all__ = [
    "AscoIngestor",
    "ConferenceFailureLog",
    "ConferenceFailureStats",
    "ConferenceIngestor",
    "ParseFailure",
    "TalkRecord",
    "TalkType",
]
