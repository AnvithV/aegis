"""Conference proceedings ingestion (ASCO, ACS, AACR, etc.)."""

from __future__ import annotations

from aegis.sources.conferences.asco import AscoIngestor
from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord, TalkType

__all__ = [
    "AscoIngestor",
    "ConferenceIngestor",
    "TalkRecord",
    "TalkType",
]
