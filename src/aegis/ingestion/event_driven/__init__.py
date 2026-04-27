"""Event-driven integrity-source feed watchers."""

from __future__ import annotations

from aegis.ingestion.event_driven.feed_watcher import FeedEntry, FeedWatcher
from aegis.ingestion.event_driven.ofac_sam import OFACWatcher, SAMWatcher
from aegis.ingestion.event_driven.ori_register import ORIRegisterWatcher
from aegis.ingestion.event_driven.retraction_watch import RetractionWatchWatcher
from aegis.ingestion.event_driven.state_boards import (
    StateBoardWatcher,
    create_all_state_watchers,
)

__all__ = [
    "FeedEntry",
    "FeedWatcher",
    "OFACWatcher",
    "ORIRegisterWatcher",
    "RetractionWatchWatcher",
    "SAMWatcher",
    "StateBoardWatcher",
    "create_all_state_watchers",
]
