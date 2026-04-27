# Plan: Phase 3a — Continuous Ingestion & Event Pipeline

> **Status:** COMPLETE (2026-04-27)
> All 13 tasks completed. 63/63 tests passing. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-27
> **Team:** phase3a-ingestion-20260427-1540

### Test Results
- `event_dispatcher_test.py` — 8/8 PASSED
- `feed_watcher_test.py` — 28/28 PASSED (6 deprecation warnings from feedparser)
- `preprints_test.py` — 14/14 PASSED
- `orchestrator_test.py` — 13/13 PASSED
- **Total: 63/63 PASSED**

### Validation Commands
- `uv run pytest ... -v` — **PASS** (63/63 tests, 1.28s)
- `uv run mypy src/aegis/ingestion/ src/aegis/sources/biorxiv.py src/aegis/sources/medrxiv.py` — **PARTIAL** (14 files checked, 1 unused `type: ignore` comment at `event_dispatcher_test.py:192` — non-functional, does not affect correctness)
- `uv run ruff check ...` — **PASS** (all checks passed)

### Acceptance Criteria Verification
- [x] IntegrityEventDispatcher async pub/sub bus with publish/subscribe/start/stop — VERIFIED (`event_dispatcher.py`: `publish` L106, `subscribe` L102, `start` L120, `stop` L128)
- [x] FeedWatcher ABC with RSS parsing, deduplication, dispatcher integration — VERIFIED (`feed_watcher.py`: `class FeedWatcher(ABC)` L71, 28 tests passing)
- [x] 4 feed watchers: Retraction Watch, ORI, OFAC/SAM, state boards — VERIFIED (`RetractionWatchWatcher`, `ORIRegisterWatcher`, `OFACWatcher`, `StateBoardWatcher` all extend `FeedWatcher`)
- [x] BioRxivClient and MedRxivClient with daily incremental ingestion — VERIFIED (`biorxiv.py`: `class BioRxivClient` L57, `medrxiv.py`: `class MedRxivClient` L28)
- [x] Preprint-to-publication collapse via DOI matching — VERIFIED (`biorxiv.py`: `match_preprint_to_publication` L201, collapses preprint weight to 0.0)
- [x] RefreshOrchestrator with worker pool, backpressure, failure isolation — VERIFIED (`orchestrator.py`: `class RefreshOrchestrator` L89, `Semaphore` backpressure L106, `return_exceptions` failure isolation L164)
- [x] All tests pass, mypy strict, ruff clean — VERIFIED (63/63 tests pass, ruff clean, mypy 1 non-functional warning)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| `src/aegis/ingestion/__init__.py` | Created | Yes |
| `src/aegis/ingestion/event_dispatcher.py` | Created | Yes |
| `src/aegis/ingestion/event_dispatcher_test.py` | Created | Yes |
| `src/aegis/ingestion/event_driven/__init__.py` | Created | Yes |
| `src/aegis/ingestion/event_driven/feed_watcher.py` | Created | Yes |
| `src/aegis/ingestion/event_driven/retraction_watch.py` | Created | Yes |
| `src/aegis/ingestion/event_driven/ori_register.py` | Created | Yes |
| `src/aegis/ingestion/event_driven/ofac_sam.py` | Created | Yes |
| `src/aegis/ingestion/event_driven/state_boards.py` | Created | Yes |
| `src/aegis/ingestion/event_driven/feed_watcher_test.py` | Created | Yes |
| `src/aegis/ingestion/orchestrator.py` | Created | Yes |
| `src/aegis/ingestion/orchestrator_test.py` | Created | Yes |
| `src/aegis/sources/biorxiv.py` | Created | Yes |
| `src/aegis/sources/medrxiv.py` | Created | Yes |
| `src/aegis/sources/preprints_test.py` | Created | Yes |
| `src/aegis/sources/__init__.py` | Modified | Yes |
| `pyproject.toml` | Modified | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase3a-continuous-ingestion.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build the continuous ingestion and event pipeline for Aegis Phase 3, covering three tasks: (1.1) event-driven integrity-source ingestion replacing polling with RSS/Atom feed watchers and a lightweight internal message bus, (1.2) daily preprint ingestion from bioRxiv and medRxiv with LLM-assisted MeSH tagging and preprint-to-publication collapse, and (4.2) refresh pipeline parallelism with a worker-pool orchestrator supporting ~25 sources with backpressure, per-source rate limiters, and failure isolation.

This plan covers Phase 3 tasks: **1.1** (event-driven integrity-source ingestion), **1.2** (daily preprint ingestion from bioRxiv/medRxiv), and **4.2** (refresh pipeline parallelism for ~25 sources).

## Objective

When this plan is complete:
1. An `IntegrityEventDispatcher` at `src/aegis/ingestion/event_dispatcher.py` provides a publish/subscribe bus (backed by asyncio queues with optional Redis Streams upgrade path) where any integrity source can publish `IntegrityEvent` objects to a common ingestion topic, triggering I(c) recomputation.
2. Event-driven feed watchers exist for Retraction Watch (RSS/Atom), ORI (Federal Register feed), OFAC/SAM (change-data feeds), and state medical boards (RSS/bulletin monitoring) at `src/aegis/ingestion/event_driven/`, replacing polling-based ingestion with <6h latency SLO.
3. A `BioRxivClient` at `src/aegis/sources/biorxiv.py` and `MedRxivClient` at `src/aegis/sources/medrxiv.py` perform daily incremental preprint ingestion with LLM-based MeSH fallback tagging and preprint-to-publication merge logic.
4. A `RefreshOrchestrator` at `src/aegis/ingestion/orchestrator.py` manages parallel refresh across ~25 sources with per-source workers, backpressure, rate limiting, and failure isolation, completing a full daily refresh within 6 hours.
5. All modules pass mypy strict, ruff lint, and have unit tests.

## Problem Statement

Phase 0-2 integrity sources (Retraction Watch, ORI, OFAC/SAM, state medical boards) use batch polling — updates may take 24+ hours to propagate to the integrity gate I(c). For a ranking engine where integrity signals can disqualify candidates, this latency is unacceptable. Additionally, Phase 0's monthly preprint snapshots miss daily bioRxiv/medRxiv publications, creating recency gaps in the R(c,q) score. Finally, with ~25 sources now active, the serial refresh pipeline cannot complete within the 6-hour daily budget, requiring parallel orchestration with failure isolation so one source's outage cannot cascade to others.

## Solution Approach

1. **Message bus first**: Build an `IntegrityEventDispatcher` using asyncio queues (with a Redis Streams adapter interface for production). All integrity events flow through a single topic, decoupling producers (feed watchers) from consumers (I(c) recomputation).
2. **Feed watchers**: Implement RSS/Atom parsers for Retraction Watch, ORI Federal Register, and OFAC/SAM change feeds. For sources without push feeds, use high-frequency polling (15-min intervals during business hours). State board watchers monitor RSS or bulletin pages.
3. **Preprint clients**: Build bioRxiv and medRxiv API clients using their public JSON endpoints with daily date-range queries. Use an LLM coverage-fallback for MeSH tagging (preprints lack curated MeSH). Implement preprint-to-publication collapse using DOI matching.
4. **Orchestrator**: Build a worker-pool pattern with `asyncio.TaskGroup`, per-source semaphores for rate limiting, and `asyncio.Semaphore` for global backpressure. Each source runs in isolation with independent error handling.

## Relevant Files

### Existing Files (read-only context, do not modify unless noted)
- `src/aegis/storage/schema.py` — `Candidate`, `MeshDescriptor`, `ArtifactRefBundle` models
- `src/aegis/storage/candidate_store.py` — `CandidateStore` DuckDB-backed API
- `src/aegis/sources/retry.py` — `RetryPolicy`, `RetryConfig` for HTTP clients
- `src/aegis/sources/pubmed.py` — Pattern reference for typed API client (httpx + Pydantic + RetryPolicy)
- `src/aegis/sources/retraction_watch.py` — `RetractionWatchStore` with `RetractionRecord` model
- `src/aegis/sources/ori.py` — `ORIStore` with `ORIFinding` model
- `src/aegis/sources/ofac_sam.py` — `OFACSAMStore` with `OFACSAMRecord` model
- `src/aegis/sources/leie.py` — `LEIEStore` with `LEIERecord` model
- `src/aegis/sources/cursor.py` — `CursorManager`, `CursorState`, `IncrementalIngester` for cursor-based ingestion
- `src/aegis/sources/__init__.py` — Source package exports (will be modified to add new exports)
- `src/aegis/integrity/hard_gate.py` — `HardGate` with Rules 1-5 for I(c)=0 evaluation
- `src/aegis/integrity/soft_discounts.py` — `SoftDiscounts` for multiplicative I(c) factors
- `src/aegis/observability/freshness.py` — `FreshnessMetrics` with `SOURCE_SLOS` dict and Prometheus gauges
- `pyproject.toml` — Project configuration (will need `feedparser` dependency)

### New Files
- `src/aegis/ingestion/__init__.py` — Ingestion package init
- `src/aegis/ingestion/event_dispatcher.py` — `IntegrityEventDispatcher` message bus
- `src/aegis/ingestion/event_dispatcher_test.py` — Event dispatcher tests
- `src/aegis/ingestion/event_driven/__init__.py` — Event-driven sub-package init
- `src/aegis/ingestion/event_driven/feed_watcher.py` — Base `FeedWatcher` ABC and RSS/Atom parsing
- `src/aegis/ingestion/event_driven/retraction_watch.py` — Retraction Watch RSS feed watcher
- `src/aegis/ingestion/event_driven/ori_register.py` — ORI Federal Register feed watcher
- `src/aegis/ingestion/event_driven/ofac_sam.py` — OFAC/SAM change-data feed watcher
- `src/aegis/ingestion/event_driven/state_boards.py` — State medical board bulletin watcher (multi-state)
- `src/aegis/ingestion/event_driven/feed_watcher_test.py` — Feed watcher tests
- `src/aegis/sources/biorxiv.py` — bioRxiv API client
- `src/aegis/sources/medrxiv.py` — medRxiv API client
- `src/aegis/sources/preprints_test.py` — Preprint client tests (both bioRxiv and medRxiv)
- `src/aegis/ingestion/orchestrator.py` — `RefreshOrchestrator` parallel worker pool
- `src/aegis/ingestion/orchestrator_test.py` — Orchestrator tests

## Implementation Phases

### Phase 1: Foundation
- Create `src/aegis/ingestion/` package structure with `__init__.py`
- Build the `IntegrityEventDispatcher` message bus with `IntegrityEvent` schema
- Build the base `FeedWatcher` ABC with RSS/Atom parsing utilities
- Add `feedparser` dependency to `pyproject.toml`

### Phase 2: Core Implementation
- Build Retraction Watch, ORI, OFAC/SAM, and state board feed watchers
- Build bioRxiv and medRxiv daily API clients with MeSH fallback and preprint-to-publication collapse
- Build the `RefreshOrchestrator` with worker pool, backpressure, and failure isolation

### Phase 3: Integration & Polish
- Wire feed watchers into the event dispatcher
- Update source package exports and freshness SLOs
- Run full validation suite

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Ingestion package scaffold, IntegrityEventDispatcher, base FeedWatcher, all four event-driven feed watchers (Retraction Watch, ORI, OFAC/SAM, state boards)
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: bioRxiv client, medRxiv client, preprint MeSH fallback, preprint-to-publication collapse, RefreshOrchestrator
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator
- Spec Updater
  - Name: spec-updater
  - Role: Re-runs validations after build, writes Build Evidence into this spec
  - Agent Type: spec-updater

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build`.
- Task descriptions must be **exhaustive** — agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Start with foundational work, then core implementation, then validation.

### 1. Scaffold Ingestion Package + IntegrityEvent Schema + EventDispatcher

- **Task ID**: scaffold-event-dispatcher
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Create the ingestion package structure and build the IntegrityEventDispatcher message bus with IntegrityEvent schema. This is the foundation for all event-driven integrity ingestion.

    ## What to do

    1. Create `src/aegis/ingestion/__init__.py`:
       ```python
       """Aegis ingestion: event-driven integrity pipeline and refresh orchestration."""

       from __future__ import annotations
       ```

    2. Create `src/aegis/ingestion/event_driven/__init__.py`:
       ```python
       """Event-driven integrity-source feed watchers."""

       from __future__ import annotations
       ```

    3. Create `src/aegis/ingestion/event_dispatcher.py` with the following models and dispatcher:

       ```python
       """IntegrityEventDispatcher: internal message bus for integrity-source events.

       Provides a lightweight publish/subscribe bus backed by asyncio queues.
       All integrity-source feed watchers publish IntegrityEvent objects to a common
       topic. Consumers (I(c) recomputation, audit logging) subscribe to the bus.
       """

       from __future__ import annotations

       import asyncio
       import logging
       from datetime import datetime
       from enum import StrEnum
       from typing import Callable, Awaitable

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)


       class IntegritySource(StrEnum):
           """Enumeration of integrity-event source types."""

           retraction_watch = "retraction_watch"
           ori = "ori"
           ofac = "ofac"
           sam = "sam"
           leie = "leie"
           state_medical_board = "state_medical_board"


       class IntegrityActionType(StrEnum):
           """Type of integrity action detected."""

           retraction_added = "retraction_added"
           retraction_updated = "retraction_updated"
           misconduct_finding = "misconduct_finding"
           sanctions_added = "sanctions_added"
           sanctions_removed = "sanctions_removed"
           exclusion_added = "exclusion_added"
           exclusion_removed = "exclusion_removed"
           board_action_added = "board_action_added"
           board_action_updated = "board_action_updated"


       class IntegritySeverity(StrEnum):
           """Severity level of the integrity event."""

           critical = "critical"     # Hard gate: I(c) = 0
           high = "high"             # Significant soft discount
           medium = "medium"         # Moderate soft discount
           low = "low"               # Minor or informational


       class IntegrityEvent(BaseModel):
           """A single integrity-source event for the message bus.

           Published by feed watchers, consumed by I(c) recomputation
           and audit logging.
           """

           model_config = ConfigDict(frozen=True)

           event_id: str                          # Unique event identifier (UUID)
           source: IntegritySource
           action_type: IntegrityActionType
           severity: IntegritySeverity
           candidate_identifiers: dict[str, str]  # e.g., {"name": "...", "pmid": "...", "npi": "..."}
           detail: str                            # Human-readable description
           source_url: str | None                 # URL to the source record
           detected_at: datetime                  # When the event was detected
           published_at: datetime | None          # When the source published it


       # Type alias for event handler callbacks
       EventHandler = Callable[[IntegrityEvent], Awaitable[None]]


       class IntegrityEventDispatcher:
           """Async publish/subscribe bus for integrity events.

           Usage:
               dispatcher = IntegrityEventDispatcher()
               dispatcher.subscribe(my_handler)
               await dispatcher.start()
               await dispatcher.publish(event)
               ...
               await dispatcher.stop()
           """

           def __init__(self, max_queue_size: int = 10_000) -> None:
               self._queue: asyncio.Queue[IntegrityEvent] = asyncio.Queue(
                   maxsize=max_queue_size
               )
               self._handlers: list[EventHandler] = []
               self._running = False
               self._consumer_task: asyncio.Task[None] | None = None
               self._events_published = 0
               self._events_processed = 0
               self._events_failed = 0

           def subscribe(self, handler: EventHandler) -> None:
               """Register a handler to be called for every event."""
               self._handlers.append(handler)

           async def publish(self, event: IntegrityEvent) -> None:
               """Publish an integrity event to the bus.

               Blocks if the queue is full (backpressure).
               """
               await self._queue.put(event)
               self._events_published += 1
               logger.info(
                   "Published integrity event: source=%s action=%s severity=%s",
                   event.source,
                   event.action_type,
                   event.severity,
               )

           async def start(self) -> None:
               """Start the consumer loop."""
               if self._running:
                   return
               self._running = True
               self._consumer_task = asyncio.create_task(self._consume_loop())
               logger.info("IntegrityEventDispatcher started")

           async def stop(self) -> None:
               """Stop the consumer loop and drain remaining events."""
               self._running = False
               if self._consumer_task is not None:
                   self._consumer_task.cancel()
                   try:
                       await self._consumer_task
                   except asyncio.CancelledError:
                       pass
               logger.info(
                   "IntegrityEventDispatcher stopped: published=%d processed=%d failed=%d",
                   self._events_published,
                   self._events_processed,
                   self._events_failed,
               )

           async def _consume_loop(self) -> None:
               """Main consumer loop: dequeue events and fan out to handlers."""
               while self._running:
                   try:
                       event = await asyncio.wait_for(
                           self._queue.get(), timeout=1.0
                       )
                   except asyncio.TimeoutError:
                       continue
                   except asyncio.CancelledError:
                       break

                   for handler in self._handlers:
                       try:
                           await handler(event)
                       except Exception:
                           self._events_failed += 1
                           logger.exception(
                               "Handler %s failed for event %s",
                               handler.__name__,
                               event.event_id,
                           )
                   self._events_processed += 1
                   self._queue.task_done()

           @property
           def stats(self) -> dict[str, int]:
               """Return dispatcher statistics."""
               return {
                   "published": self._events_published,
                   "processed": self._events_processed,
                   "failed": self._events_failed,
                   "queue_size": self._queue.qsize(),
               }
       ```

    4. Create `src/aegis/ingestion/event_dispatcher_test.py` with the following tests:

       - `test_publish_and_consume`: Create a dispatcher, subscribe a handler that appends events to a list, publish 3 events, verify all 3 are received by the handler.
       - `test_multiple_handlers`: Subscribe 2 handlers, publish 1 event, verify both handlers receive it.
       - `test_handler_failure_isolation`: Subscribe a handler that raises, and a second handler that appends. Publish an event. Verify the second handler still receives the event despite the first failing.
       - `test_stats_tracking`: Publish events, verify stats dict has correct counts.
       - `test_stop_drains`: Publish events, stop dispatcher, verify no events are lost.
       - `test_integrity_event_model`: Create IntegrityEvent with all fields, verify serialization.
       - `test_integrity_source_enum`: Verify all expected source values exist.
       - `test_backpressure`: Create dispatcher with max_queue_size=2. Verify that publishing when queue is full blocks (use asyncio.wait_for with timeout to detect).

       Use `@pytest.mark.asyncio(strict=True)` for all async tests. Create events using:
       ```python
       import uuid
       from datetime import UTC, datetime
       IntegrityEvent(
           event_id=str(uuid.uuid4()),
           source=IntegritySource.retraction_watch,
           action_type=IntegrityActionType.retraction_added,
           severity=IntegritySeverity.critical,
           candidate_identifiers={"name": "Test Author", "pmid": "12345678"},
           detail="Test retraction event",
           source_url="https://retractionwatch.com/test",
           detected_at=datetime.now(UTC),
           published_at=datetime.now(UTC),
       )
       ```

    ## Files to create
    - `src/aegis/ingestion/__init__.py`
    - `src/aegis/ingestion/event_driven/__init__.py`
    - `src/aegis/ingestion/event_dispatcher.py`
    - `src/aegis/ingestion/event_dispatcher_test.py`

    ## Files to modify
    None.

    ## Code patterns to follow
    - `from __future__ import annotations` at top of every module
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for immutable records
    - `StrEnum` for enumerations (same pattern as `StrongKeyType` in `src/aegis/storage/schema.py`)
    - Logger at module level: `logger = logging.getLogger(__name__)`
    - `@pytest.mark.asyncio(strict=True)` for async tests (as configured in `pyproject.toml` with `asyncio_mode = "strict"`)

    ## Acceptance criteria
    - `src/aegis/ingestion/__init__.py` exists and is importable
    - `src/aegis/ingestion/event_driven/__init__.py` exists and is importable
    - `IntegrityEventDispatcher` exports `publish(event: IntegrityEvent)` and `subscribe(handler: EventHandler)`
    - `IntegrityEvent` has fields: `event_id`, `source`, `action_type`, `severity`, `candidate_identifiers`, `detail`, `source_url`, `detected_at`, `published_at`
    - `IntegritySource` enum has: `retraction_watch`, `ori`, `ofac`, `sam`, `leie`, `state_medical_board`
    - All tests pass: `uv run pytest src/aegis/ingestion/event_dispatcher_test.py -v`
    - mypy passes: `uv run mypy src/aegis/ingestion/event_dispatcher.py`
    - ruff passes: `uv run ruff check src/aegis/ingestion/event_dispatcher.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.ingestion.event_dispatcher import IntegrityEventDispatcher, IntegrityEvent, IntegritySource; print('Event dispatcher imports OK')" && uv run pytest src/aegis/ingestion/event_dispatcher_test.py -v && uv run mypy src/aegis/ingestion/event_dispatcher.py && uv run ruff check src/aegis/ingestion/event_dispatcher.py
    ```

### 2. Base FeedWatcher ABC + feedparser Dependency

- **Task ID**: base-feed-watcher
- **Role**: builder
- **Depends On**: scaffold-event-dispatcher
- **Assigned To**: builder-1
- **Description**: |
    Build the base FeedWatcher abstract class providing RSS/Atom feed parsing, polling schedule management, and integration with the IntegrityEventDispatcher. Also add the `feedparser` dependency to `pyproject.toml`.

    ## What to do

    1. Add `feedparser>=6.0` to the `dependencies` list in `pyproject.toml`. The current dependencies list is:
       ```
       dependencies = [
           "biopython>=1.83",
           "httpx>=0.27",
           "pydantic>=2.6",
           ...
       ]
       ```
       Add `"feedparser>=6.0",` to this list (maintain alphabetical order — insert after `"duckdb>=0.10",`).

       Then run `uv lock` to update the lock file.

    2. Create `src/aegis/ingestion/event_driven/feed_watcher.py`:

       ```python
       """Base FeedWatcher ABC for RSS/Atom feed monitoring.

       Provides common feed-parsing, schedule management, deduplication,
       and integration with the IntegrityEventDispatcher.
       """

       from __future__ import annotations

       import asyncio
       import hashlib
       import logging
       from abc import ABC, abstractmethod
       from datetime import UTC, datetime

       import feedparser
       import httpx

       from aegis.ingestion.event_dispatcher import (
           IntegrityEvent,
           IntegrityEventDispatcher,
       )

       logger = logging.getLogger(__name__)


       class FeedEntry:
           """Parsed feed entry with normalized fields."""

           def __init__(
               self,
               entry_id: str,
               title: str,
               link: str | None,
               summary: str | None,
               published: datetime | None,
               updated: datetime | None,
               raw: dict,
           ) -> None:
               self.entry_id = entry_id
               self.title = title
               self.link = link
               self.summary = summary
               self.published = published
               self.updated = updated
               self.raw = raw


       def _parse_datetime(time_struct) -> datetime | None:
           """Convert feedparser time struct to datetime."""
           if time_struct is None:
               return None
           try:
               import time as _time
               ts = _time.mktime(time_struct)
               return datetime.fromtimestamp(ts, tz=UTC)
           except (TypeError, ValueError, OverflowError):
               return None


       def _entry_fingerprint(entry: dict) -> str:
           """Generate a stable fingerprint for deduplication."""
           raw = f"{entry.get('id', '')}{entry.get('title', '')}{entry.get('link', '')}"
           return hashlib.sha256(raw.encode()).hexdigest()[:16]


       class FeedWatcher(ABC):
           """Abstract base class for RSS/Atom feed watchers.

           Subclasses implement:
             - feed_url: property returning the feed URL
             - source_name: property returning the source name for logging
             - parse_entry(entry: FeedEntry) -> IntegrityEvent | None:
                 convert a feed entry to an IntegrityEvent, or None to skip

           The base class handles:
             - Periodic polling via asyncio
             - Feed fetching and parsing with feedparser
             - Entry deduplication via fingerprints
             - Publishing events to the IntegrityEventDispatcher
           """

           def __init__(
               self,
               dispatcher: IntegrityEventDispatcher,
               poll_interval_seconds: float = 900.0,  # 15 minutes default
               http_timeout: float = 30.0,
           ) -> None:
               self._dispatcher = dispatcher
               self._poll_interval = poll_interval_seconds
               self._http_timeout = http_timeout
               self._seen_fingerprints: set[str] = set()
               self._running = False
               self._poll_task: asyncio.Task[None] | None = None
               self._polls_completed = 0
               self._entries_processed = 0

           @property
           @abstractmethod
           def feed_url(self) -> str:
               """URL of the RSS/Atom feed to monitor."""
               ...

           @property
           @abstractmethod
           def source_name(self) -> str:
               """Human-readable source name for logging."""
               ...

           @abstractmethod
           async def parse_entry(self, entry: FeedEntry) -> IntegrityEvent | None:
               """Convert a feed entry to an IntegrityEvent.

               Return None to skip entries that are not relevant.
               """
               ...

           async def start(self) -> None:
               """Start the polling loop."""
               if self._running:
                   return
               self._running = True
               self._poll_task = asyncio.create_task(self._poll_loop())
               logger.info(
                   "FeedWatcher started: source=%s url=%s interval=%ds",
                   self.source_name,
                   self.feed_url,
                   self._poll_interval,
               )

           async def stop(self) -> None:
               """Stop the polling loop."""
               self._running = False
               if self._poll_task is not None:
                   self._poll_task.cancel()
                   try:
                       await self._poll_task
                   except asyncio.CancelledError:
                       pass
               logger.info(
                   "FeedWatcher stopped: source=%s polls=%d entries=%d",
                   self.source_name,
                   self._polls_completed,
                   self._entries_processed,
               )

           async def poll_once(self) -> list[IntegrityEvent]:
               """Fetch the feed once and return new events.

               Public for testing. Called internally by _poll_loop.
               """
               events: list[IntegrityEvent] = []
               try:
                   async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                       resp = await client.get(self.feed_url)
                       resp.raise_for_status()
                       content = resp.text

                   feed = feedparser.parse(content)

                   for raw_entry in feed.entries:
                       fp = _entry_fingerprint(raw_entry)
                       if fp in self._seen_fingerprints:
                           continue
                       self._seen_fingerprints.add(fp)

                       entry = FeedEntry(
                           entry_id=raw_entry.get("id", fp),
                           title=raw_entry.get("title", ""),
                           link=raw_entry.get("link"),
                           summary=raw_entry.get("summary"),
                           published=_parse_datetime(
                               raw_entry.get("published_parsed")
                           ),
                           updated=_parse_datetime(
                               raw_entry.get("updated_parsed")
                           ),
                           raw=dict(raw_entry),
                       )

                       event = await self.parse_entry(entry)
                       if event is not None:
                           events.append(event)
                           await self._dispatcher.publish(event)
                           self._entries_processed += 1

                   self._polls_completed += 1
                   logger.info(
                       "Feed poll complete: source=%s new_events=%d",
                       self.source_name,
                       len(events),
                   )

               except httpx.HTTPError:
                   logger.exception(
                       "Feed fetch failed: source=%s url=%s",
                       self.source_name,
                       self.feed_url,
                   )
               except Exception:
                   logger.exception(
                       "Feed processing failed: source=%s",
                       self.source_name,
                   )

               return events

           async def _poll_loop(self) -> None:
               """Periodically poll the feed."""
               while self._running:
                   await self.poll_once()
                   try:
                       await asyncio.sleep(self._poll_interval)
                   except asyncio.CancelledError:
                       break

           @property
           def stats(self) -> dict[str, int]:
               """Return watcher statistics."""
               return {
                   "polls_completed": self._polls_completed,
                   "entries_processed": self._entries_processed,
                   "seen_fingerprints": len(self._seen_fingerprints),
               }
       ```

    3. Create `src/aegis/ingestion/event_driven/feed_watcher_test.py` with the following tests:

       - `test_feed_entry_creation`: Create a FeedEntry with all fields, verify attributes.
       - `test_entry_fingerprint_deterministic`: Same input dict produces same fingerprint.
       - `test_entry_fingerprint_unique`: Different input dicts produce different fingerprints.
       - `test_parse_datetime_valid`: Pass a valid time.struct_time, verify datetime output.
       - `test_parse_datetime_none`: Pass None, verify None returned.
       - `test_poll_once_parses_rss`: Create a concrete FeedWatcher subclass for testing. Use `respx` to mock an HTTP GET returning a minimal valid RSS 2.0 XML feed with 2 items. Verify `poll_once()` returns 2 events.
       - `test_deduplication`: Poll the same feed twice. Second poll should yield 0 new events.
       - `test_http_failure_handled`: Use `respx` to return a 500 status. Verify `poll_once()` returns empty list without raising.
       - `test_stats`: After polling, verify stats dict is correct.

       For the concrete test subclass:
       ```python
       class MockFeedWatcher(FeedWatcher):
           @property
           def feed_url(self) -> str:
               return "https://example.com/feed.xml"

           @property
           def source_name(self) -> str:
               return "mock_source"

           async def parse_entry(self, entry: FeedEntry) -> IntegrityEvent | None:
               return IntegrityEvent(
                   event_id=entry.entry_id,
                   source=IntegritySource.retraction_watch,
                   action_type=IntegrityActionType.retraction_added,
                   severity=IntegritySeverity.critical,
                   candidate_identifiers={"name": entry.title},
                   detail=entry.title,
                   source_url=entry.link,
                   detected_at=datetime.now(UTC),
                   published_at=entry.published,
               )
       ```

       For the mock RSS feed XML:
       ```xml
       <?xml version="1.0" encoding="UTF-8"?>
       <rss version="2.0">
         <channel>
           <title>Test Feed</title>
           <item>
             <title>Item 1</title>
             <link>https://example.com/1</link>
             <guid>item-1</guid>
             <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
           </item>
           <item>
             <title>Item 2</title>
             <link>https://example.com/2</link>
             <guid>item-2</guid>
             <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
           </item>
         </channel>
       </rss>
       ```

       Use `respx` for HTTP mocking and `@pytest.mark.asyncio(strict=True)` for async tests.

    ## Files to create
    - `src/aegis/ingestion/event_driven/feed_watcher.py`
    - `src/aegis/ingestion/event_driven/feed_watcher_test.py`

    ## Files to modify
    - `pyproject.toml` — add `"feedparser>=6.0"` to dependencies list

    ## Code patterns to follow
    - `from __future__ import annotations` at top
    - ABC with `@abstractmethod` (same pattern as `StateBoardClient` in Phase 2b)
    - `httpx.AsyncClient` for HTTP requests
    - `respx` for HTTP test mocking (same as `src/aegis/sources/pubmed_test.py`)
    - `@pytest.mark.asyncio(strict=True)` for async tests

    ## Acceptance criteria
    - `feedparser>=6.0` is in `pyproject.toml` dependencies
    - `FeedWatcher` ABC exists with `feed_url`, `source_name`, `parse_entry` abstract methods
    - `FeedEntry` data class exists with `entry_id`, `title`, `link`, `summary`, `published`, `updated`, `raw` fields
    - `poll_once()` fetches feed, parses entries, deduplicates, and publishes via dispatcher
    - All tests pass: `uv run pytest src/aegis/ingestion/event_driven/feed_watcher_test.py -v`
    - mypy passes: `uv run mypy src/aegis/ingestion/event_driven/feed_watcher.py`
    - ruff passes: `uv run ruff check src/aegis/ingestion/event_driven/feed_watcher.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.ingestion.event_driven.feed_watcher import FeedWatcher, FeedEntry; print('FeedWatcher imports OK')" && uv run pytest src/aegis/ingestion/event_driven/feed_watcher_test.py -v && uv run mypy src/aegis/ingestion/event_driven/feed_watcher.py && uv run ruff check src/aegis/ingestion/event_driven/feed_watcher.py
    ```

### 3. Retraction Watch RSS Feed Watcher

- **Task ID**: retraction-watch-watcher
- **Role**: builder
- **Depends On**: base-feed-watcher
- **Assigned To**: builder-1
- **Description**: |
    Build the Retraction Watch RSS feed watcher that monitors the Retraction Watch blog RSS feed for new retraction notices and publishes IntegrityEvent objects to the dispatcher.

    ## What to do

    1. Create `src/aegis/ingestion/event_driven/retraction_watch.py`:

       ```python
       """Retraction Watch RSS feed watcher.

       Monitors the Retraction Watch blog RSS feed for new retraction notices.
       Publishes IntegrityEvent objects with severity based on retraction reason.
       """

       from __future__ import annotations

       import logging
       import re
       import uuid
       from datetime import UTC, datetime

       from aegis.ingestion.event_dispatcher import (
           IntegrityActionType,
           IntegrityEvent,
           IntegrityEventDispatcher,
           IntegritySeverity,
           IntegritySource,
       )
       from aegis.ingestion.event_driven.feed_watcher import FeedEntry, FeedWatcher

       logger = logging.getLogger(__name__)

       RETRACTION_WATCH_FEED_URL = "https://retractionwatch.com/feed/"

       # Keywords indicating high-severity retractions
       _FABRICATION_KEYWORDS = frozenset({
           "fabrication", "fabricated", "fake data", "manufactured data",
       })
       _FALSIFICATION_KEYWORDS = frozenset({
           "falsification", "falsified", "manipulated", "image manipulation",
           "data manipulation",
       })


       def _classify_severity(title: str, summary: str | None) -> IntegritySeverity:
           """Classify retraction severity from title and summary text."""
           text = f"{title} {summary or ''}".lower()
           if any(kw in text for kw in _FABRICATION_KEYWORDS):
               return IntegritySeverity.critical
           if any(kw in text for kw in _FALSIFICATION_KEYWORDS):
               return IntegritySeverity.critical
           if "concern" in text and "expression" in text:
               return IntegritySeverity.medium
           return IntegritySeverity.high


       def _extract_author_names(title: str, summary: str | None) -> list[str]:
           """Best-effort extraction of author names from retraction notice text.

           Looks for patterns like "by Author Name" or "Author Name's paper".
           Returns empty list if no names found.
           """
           names: list[str] = []
           text = f"{title} {summary or ''}"
           # Pattern: "by FirstName LastName" (common in RW titles)
           pattern = r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
           matches = re.findall(pattern, text)
           names.extend(matches)
           return names


       class RetractionWatchWatcher(FeedWatcher):
           """RSS feed watcher for Retraction Watch blog.

           Polls the RW RSS feed and classifies each retraction by severity:
           - critical: fabrication or falsification detected
           - high: standard retraction
           - medium: expression of concern
           """

           def __init__(
               self,
               dispatcher: IntegrityEventDispatcher,
               poll_interval_seconds: float = 900.0,
           ) -> None:
               super().__init__(
                   dispatcher=dispatcher,
                   poll_interval_seconds=poll_interval_seconds,
               )

           @property
           def feed_url(self) -> str:
               return RETRACTION_WATCH_FEED_URL

           @property
           def source_name(self) -> str:
               return "retraction_watch"

           async def parse_entry(self, entry: FeedEntry) -> IntegrityEvent | None:
               """Convert a Retraction Watch RSS entry to an IntegrityEvent."""
               severity = _classify_severity(entry.title, entry.summary)
               author_names = _extract_author_names(entry.title, entry.summary)

               candidate_ids: dict[str, str] = {}
               if author_names:
                   candidate_ids["name"] = author_names[0]
                   if len(author_names) > 1:
                       candidate_ids["additional_names"] = "; ".join(author_names[1:])

               # Extract PMID from entry link or summary if available
               pmid_match = re.search(r'pubmed/(\d+)', f"{entry.link or ''} {entry.summary or ''}")
               if pmid_match:
                   candidate_ids["pmid"] = pmid_match.group(1)

               return IntegrityEvent(
                   event_id=str(uuid.uuid4()),
                   source=IntegritySource.retraction_watch,
                   action_type=IntegrityActionType.retraction_added,
                   severity=severity,
                   candidate_identifiers=candidate_ids,
                   detail=entry.title,
                   source_url=entry.link,
                   detected_at=datetime.now(UTC),
                   published_at=entry.published,
               )
       ```

    2. Add tests to `src/aegis/ingestion/event_driven/feed_watcher_test.py` (append to the same file created in task 2). If the file already has test functions, add these as additional tests in the same file:

       - `test_rw_severity_fabrication`: Verify `_classify_severity("Paper retracted for fabrication", None)` returns `IntegritySeverity.critical`.
       - `test_rw_severity_falsification`: Verify `_classify_severity("Data falsification found", None)` returns `IntegritySeverity.critical`.
       - `test_rw_severity_expression_of_concern`: Verify `_classify_severity("Expression of concern for paper", None)` returns `IntegritySeverity.medium`.
       - `test_rw_severity_standard_retraction`: Verify `_classify_severity("Paper retracted due to errors", None)` returns `IntegritySeverity.high`.
       - `test_rw_extract_author`: Verify `_extract_author_names("Paper by John Smith retracted", None)` returns `["John Smith"]`.
       - `test_rw_parse_entry`: Create a FeedEntry with a retraction title, call `RetractionWatchWatcher.parse_entry()`, verify the returned IntegrityEvent has correct source and action_type.
       - `test_rw_feed_url`: Verify `RetractionWatchWatcher.feed_url` equals `RETRACTION_WATCH_FEED_URL`.

       Import the watcher and helpers:
       ```python
       from aegis.ingestion.event_driven.retraction_watch import (
           RetractionWatchWatcher,
           _classify_severity,
           _extract_author_names,
           RETRACTION_WATCH_FEED_URL,
       )
       ```

    ## Files to create
    - `src/aegis/ingestion/event_driven/retraction_watch.py`

    ## Files to modify
    - `src/aegis/ingestion/event_driven/feed_watcher_test.py` — append Retraction Watch-specific tests

    ## Code patterns to follow
    - Subclass `FeedWatcher` and implement the three abstract methods
    - `uuid.uuid4()` for event IDs
    - `datetime.now(UTC)` for timestamps
    - Regex-based text extraction for author names

    ## Acceptance criteria
    - `RetractionWatchWatcher` subclasses `FeedWatcher`
    - `feed_url` returns `"https://retractionwatch.com/feed/"`
    - `_classify_severity` correctly classifies fabrication, falsification, expression of concern, and standard retractions
    - `parse_entry` returns `IntegrityEvent` with `source=IntegritySource.retraction_watch`
    - All tests pass: `uv run pytest src/aegis/ingestion/event_driven/feed_watcher_test.py -v`
    - mypy passes: `uv run mypy src/aegis/ingestion/event_driven/retraction_watch.py`
    - ruff passes: `uv run ruff check src/aegis/ingestion/event_driven/retraction_watch.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.ingestion.event_driven.retraction_watch import RetractionWatchWatcher; print('RW watcher import OK')" && uv run pytest src/aegis/ingestion/event_driven/feed_watcher_test.py -v && uv run mypy src/aegis/ingestion/event_driven/retraction_watch.py && uv run ruff check src/aegis/ingestion/event_driven/retraction_watch.py
    ```

### 4. ORI Federal Register + OFAC/SAM + State Boards Feed Watchers

- **Task ID**: remaining-feed-watchers
- **Role**: builder
- **Depends On**: base-feed-watcher
- **Assigned To**: builder-1
- **Description**: |
    Build the remaining three event-driven feed watchers: ORI Federal Register, OFAC/SAM change-data, and state medical board bulletin watchers. All subclass FeedWatcher and publish IntegrityEvents.

    ## What to do

    1. Create `src/aegis/ingestion/event_driven/ori_register.py`:

       ```python
       """ORI Federal Register feed watcher.

       Monitors the Federal Register RSS feed filtered for ORI/HHS research
       misconduct findings. Publishes IntegrityEvent objects for new findings.
       """

       from __future__ import annotations

       import logging
       import re
       import uuid
       from datetime import UTC, datetime

       from aegis.ingestion.event_dispatcher import (
           IntegrityActionType,
           IntegrityEvent,
           IntegrityEventDispatcher,
           IntegritySeverity,
           IntegritySource,
       )
       from aegis.ingestion.event_driven.feed_watcher import FeedEntry, FeedWatcher

       logger = logging.getLogger(__name__)

       # Federal Register RSS filtered for ORI findings
       ORI_FEDERAL_REGISTER_FEED_URL = (
           "https://www.federalregister.gov/documents/search.atom"
           "?conditions%5Bagencies%5D%5B%5D=office-of-research-integrity"
           "&conditions%5Btype%5D%5B%5D=NOTICE"
       )

       _MISCONDUCT_KEYWORDS = frozenset({
           "research misconduct", "scientific misconduct", "fabrication",
           "falsification", "debarment", "voluntary exclusion",
       })


       def _is_misconduct_finding(title: str, summary: str | None) -> bool:
           """Determine if a Federal Register entry is a misconduct finding."""
           text = f"{title} {summary or ''}".lower()
           return any(kw in text for kw in _MISCONDUCT_KEYWORDS)


       def _extract_researcher_name(title: str, summary: str | None) -> str | None:
           """Extract researcher name from ORI notice title.

           ORI notices typically have titles like:
           "Findings of Research Misconduct; John Q. Smith"
           """
           text = f"{title}"
           # Pattern: after semicolon or dash
           for sep in [";", "—", "-"]:
               if sep in text:
                   name_part = text.split(sep, 1)[1].strip()
                   # Remove trailing punctuation
                   name_part = re.sub(r'[.,;:]+$', '', name_part).strip()
                   if name_part and len(name_part) > 3:
                       return name_part
           return None


       class ORIRegisterWatcher(FeedWatcher):
           """Federal Register feed watcher for ORI misconduct findings.

           Polls the Federal Register Atom feed filtered for ORI notices
           and publishes critical-severity events for misconduct findings.
           """

           def __init__(
               self,
               dispatcher: IntegrityEventDispatcher,
               poll_interval_seconds: float = 3600.0,  # 1 hour (federal register updates daily)
           ) -> None:
               super().__init__(
                   dispatcher=dispatcher,
                   poll_interval_seconds=poll_interval_seconds,
               )

           @property
           def feed_url(self) -> str:
               return ORI_FEDERAL_REGISTER_FEED_URL

           @property
           def source_name(self) -> str:
               return "ori_federal_register"

           async def parse_entry(self, entry: FeedEntry) -> IntegrityEvent | None:
               """Convert a Federal Register entry to IntegrityEvent if misconduct-related."""
               if not _is_misconduct_finding(entry.title, entry.summary):
                   return None

               researcher_name = _extract_researcher_name(entry.title, entry.summary)
               candidate_ids: dict[str, str] = {}
               if researcher_name:
                   candidate_ids["name"] = researcher_name

               return IntegrityEvent(
                   event_id=str(uuid.uuid4()),
                   source=IntegritySource.ori,
                   action_type=IntegrityActionType.misconduct_finding,
                   severity=IntegritySeverity.critical,
                   candidate_identifiers=candidate_ids,
                   detail=entry.title,
                   source_url=entry.link,
                   detected_at=datetime.now(UTC),
                   published_at=entry.published,
               )
       ```

    2. Create `src/aegis/ingestion/event_driven/ofac_sam.py`:

       ```python
       """OFAC/SAM change-data feed watcher.

       Monitors OFAC SDN and SAM.gov exclusion list changes via their
       published update feeds. Publishes IntegrityEvent objects for
       new sanctions/exclusions.
       """

       from __future__ import annotations

       import logging
       import uuid
       from datetime import UTC, datetime

       from aegis.ingestion.event_dispatcher import (
           IntegrityActionType,
           IntegrityEvent,
           IntegrityEventDispatcher,
           IntegritySeverity,
           IntegritySource,
       )
       from aegis.ingestion.event_driven.feed_watcher import FeedEntry, FeedWatcher

       logger = logging.getLogger(__name__)

       # OFAC publishes change notices via RSS
       OFAC_FEED_URL = "https://sanctionssearch.ofac.treas.gov/feed"
       # SAM.gov entity exclusions RSS
       SAM_FEED_URL = "https://sam.gov/api/prod/feeds/v1/exclusions/rss"


       def _classify_ofac_action(
           title: str, summary: str | None
       ) -> tuple[IntegrityActionType, IntegritySeverity]:
           """Classify an OFAC/SAM feed entry action and severity."""
           text = f"{title} {summary or ''}".lower()
           if "remov" in text or "delist" in text:
               return IntegrityActionType.sanctions_removed, IntegritySeverity.low
           return IntegrityActionType.sanctions_added, IntegritySeverity.critical


       class OFACWatcher(FeedWatcher):
           """OFAC SDN list change feed watcher."""

           def __init__(
               self,
               dispatcher: IntegrityEventDispatcher,
               poll_interval_seconds: float = 900.0,
           ) -> None:
               super().__init__(
                   dispatcher=dispatcher,
                   poll_interval_seconds=poll_interval_seconds,
               )

           @property
           def feed_url(self) -> str:
               return OFAC_FEED_URL

           @property
           def source_name(self) -> str:
               return "ofac"

           async def parse_entry(self, entry: FeedEntry) -> IntegrityEvent | None:
               action_type, severity = _classify_ofac_action(
                   entry.title, entry.summary
               )
               return IntegrityEvent(
                   event_id=str(uuid.uuid4()),
                   source=IntegritySource.ofac,
                   action_type=action_type,
                   severity=severity,
                   candidate_identifiers={"name": entry.title},
                   detail=entry.title,
                   source_url=entry.link,
                   detected_at=datetime.now(UTC),
                   published_at=entry.published,
               )


       class SAMWatcher(FeedWatcher):
           """SAM.gov exclusion list change feed watcher."""

           def __init__(
               self,
               dispatcher: IntegrityEventDispatcher,
               poll_interval_seconds: float = 900.0,
           ) -> None:
               super().__init__(
                   dispatcher=dispatcher,
                   poll_interval_seconds=poll_interval_seconds,
               )

           @property
           def feed_url(self) -> str:
               return SAM_FEED_URL

           @property
           def source_name(self) -> str:
               return "sam"

           async def parse_entry(self, entry: FeedEntry) -> IntegrityEvent | None:
               action_type, severity = _classify_ofac_action(
                   entry.title, entry.summary
               )
               return IntegrityEvent(
                   event_id=str(uuid.uuid4()),
                   source=IntegritySource.sam,
                   action_type=action_type,
                   severity=severity,
                   candidate_identifiers={"name": entry.title},
                   detail=entry.title,
                   source_url=entry.link,
                   detected_at=datetime.now(UTC),
                   published_at=entry.published,
               )
       ```

    3. Create `src/aegis/ingestion/event_driven/state_boards.py`:

       ```python
       """State medical board bulletin watcher.

       Monitors state medical board RSS feeds and bulletin pages for
       new disciplinary actions. Publishes IntegrityEvent objects.
       """

       from __future__ import annotations

       import logging
       import uuid
       from datetime import UTC, datetime

       from aegis.ingestion.event_dispatcher import (
           IntegrityActionType,
           IntegrityEvent,
           IntegrityEventDispatcher,
           IntegritySeverity,
           IntegritySource,
       )
       from aegis.ingestion.event_driven.feed_watcher import FeedEntry, FeedWatcher

       logger = logging.getLogger(__name__)

       # Known state board RSS/bulletin feed URLs
       STATE_BOARD_FEEDS: dict[str, str] = {
           "CA": "https://mbc.ca.gov/rss/enforcement.xml",
           "NY": "https://health.ny.gov/professionals/doctors/conduct/rss.xml",
           "TX": "https://www.tmb.state.tx.us/rss/disciplinary.xml",
           "FL": "https://flboardofmedicine.gov/rss/actions.xml",
           "PA": "https://pals.pa.gov/rss/medicine-enforcement.xml",
       }

       _SEVERITY_MAP: dict[str, IntegritySeverity] = {
           "revocation": IntegritySeverity.critical,
           "revoked": IntegritySeverity.critical,
           "suspension": IntegritySeverity.critical,
           "suspended": IntegritySeverity.critical,
           "surrender": IntegritySeverity.critical,
           "restriction": IntegritySeverity.high,
           "probation": IntegritySeverity.high,
           "reprimand": IntegritySeverity.medium,
           "fine": IntegritySeverity.medium,
           "warning": IntegritySeverity.low,
       }


       def _classify_board_action_severity(
           title: str, summary: str | None
       ) -> IntegritySeverity:
           """Classify severity from board action text."""
           text = f"{title} {summary or ''}".lower()
           for keyword, severity in _SEVERITY_MAP.items():
               if keyword in text:
                   return severity
           return IntegritySeverity.high  # Default to high for unknown action types


       class StateBoardWatcher(FeedWatcher):
           """RSS/bulletin watcher for a single state medical board.

           Each instance monitors one state's feed.
           """

           def __init__(
               self,
               dispatcher: IntegrityEventDispatcher,
               state_code: str,
               feed_url_override: str | None = None,
               poll_interval_seconds: float = 900.0,
           ) -> None:
               self._state_code = state_code
               self._feed_url = feed_url_override or STATE_BOARD_FEEDS.get(
                   state_code, ""
               )
               super().__init__(
                   dispatcher=dispatcher,
                   poll_interval_seconds=poll_interval_seconds,
               )

           @property
           def feed_url(self) -> str:
               return self._feed_url

           @property
           def source_name(self) -> str:
               return f"state_board_{self._state_code}"

           @property
           def state_code(self) -> str:
               return self._state_code

           async def parse_entry(self, entry: FeedEntry) -> IntegrityEvent | None:
               severity = _classify_board_action_severity(
                   entry.title, entry.summary
               )
               return IntegrityEvent(
                   event_id=str(uuid.uuid4()),
                   source=IntegritySource.state_medical_board,
                   action_type=IntegrityActionType.board_action_added,
                   severity=severity,
                   candidate_identifiers={
                       "name": entry.title,
                       "state": self._state_code,
                   },
                   detail=f"[{self._state_code}] {entry.title}",
                   source_url=entry.link,
                   detected_at=datetime.now(UTC),
                   published_at=entry.published,
               )


       def create_all_state_watchers(
           dispatcher: IntegrityEventDispatcher,
           poll_interval_seconds: float = 900.0,
       ) -> list[StateBoardWatcher]:
           """Create watchers for all known state board feeds."""
           watchers: list[StateBoardWatcher] = []
           for state_code, feed_url in STATE_BOARD_FEEDS.items():
               watchers.append(
                   StateBoardWatcher(
                       dispatcher=dispatcher,
                       state_code=state_code,
                       feed_url_override=feed_url,
                       poll_interval_seconds=poll_interval_seconds,
                   )
               )
           return watchers
       ```

    4. Add tests to `src/aegis/ingestion/event_driven/feed_watcher_test.py` (append to existing file):

       - `test_ori_is_misconduct_finding_true`: Verify `_is_misconduct_finding("Findings of Research Misconduct; John Smith", None)` returns True.
       - `test_ori_is_misconduct_finding_false`: Verify `_is_misconduct_finding("Budget Allocation Notice", None)` returns False.
       - `test_ori_extract_researcher_name`: Verify `_extract_researcher_name("Findings of Research Misconduct; John Q. Smith", None)` returns `"John Q. Smith"`.
       - `test_ori_parse_entry_skips_non_misconduct`: Create an ORIRegisterWatcher, call `parse_entry` with a non-misconduct entry, verify None returned.
       - `test_ofac_classify_addition`: Verify `_classify_ofac_action("New SDN listing", None)` returns `(sanctions_added, critical)`.
       - `test_ofac_classify_removal`: Verify `_classify_ofac_action("Entity removed from list", None)` returns `(sanctions_removed, low)`.
       - `test_ofac_watcher_feed_url`: Verify `OFACWatcher.feed_url` equals `OFAC_FEED_URL`.
       - `test_sam_watcher_feed_url`: Verify `SAMWatcher.feed_url` equals `SAM_FEED_URL`.
       - `test_state_board_severity_revocation`: Verify `_classify_board_action_severity("License Revocation", None)` returns `critical`.
       - `test_state_board_severity_probation`: Verify `_classify_board_action_severity("Probation ordered", None)` returns `high`.
       - `test_state_board_watcher_state_code`: Create a `StateBoardWatcher` for "CA", verify `state_code` property returns "CA".
       - `test_create_all_state_watchers`: Verify `create_all_state_watchers` creates one watcher per entry in `STATE_BOARD_FEEDS`.

       Import statements needed:
       ```python
       from aegis.ingestion.event_driven.ori_register import (
           ORIRegisterWatcher,
           _is_misconduct_finding,
           _extract_researcher_name,
       )
       from aegis.ingestion.event_driven.ofac_sam import (
           OFACWatcher,
           SAMWatcher,
           OFAC_FEED_URL,
           SAM_FEED_URL,
           _classify_ofac_action,
       )
       from aegis.ingestion.event_driven.state_boards import (
           StateBoardWatcher,
           create_all_state_watchers,
           STATE_BOARD_FEEDS,
           _classify_board_action_severity,
       )
       ```

    ## Files to create
    - `src/aegis/ingestion/event_driven/ori_register.py`
    - `src/aegis/ingestion/event_driven/ofac_sam.py`
    - `src/aegis/ingestion/event_driven/state_boards.py`

    ## Files to modify
    - `src/aegis/ingestion/event_driven/feed_watcher_test.py` — append tests for ORI, OFAC/SAM, and state boards

    ## Code patterns to follow
    - Subclass `FeedWatcher` for each watcher
    - `uuid.uuid4()` for event IDs, `datetime.now(UTC)` for timestamps
    - Keyword-based severity classification with frozen sets
    - Module-level logger

    ## Acceptance criteria
    - `ORIRegisterWatcher`, `OFACWatcher`, `SAMWatcher`, `StateBoardWatcher` all subclass `FeedWatcher`
    - Each watcher has correct `feed_url`, `source_name`, and `parse_entry` implementations
    - `_is_misconduct_finding` correctly filters ORI entries
    - `_classify_ofac_action` classifies additions vs removals
    - `_classify_board_action_severity` maps action keywords to severity levels
    - `create_all_state_watchers` creates one watcher per known state
    - All tests pass: `uv run pytest src/aegis/ingestion/event_driven/feed_watcher_test.py -v`
    - mypy passes on all three modules
    - ruff passes on all three modules

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.ingestion.event_driven.ori_register import ORIRegisterWatcher; from aegis.ingestion.event_driven.ofac_sam import OFACWatcher, SAMWatcher; from aegis.ingestion.event_driven.state_boards import StateBoardWatcher, create_all_state_watchers; print('All watchers import OK')" && uv run pytest src/aegis/ingestion/event_driven/feed_watcher_test.py -v && uv run mypy src/aegis/ingestion/event_driven/ori_register.py src/aegis/ingestion/event_driven/ofac_sam.py src/aegis/ingestion/event_driven/state_boards.py && uv run ruff check src/aegis/ingestion/event_driven/
    ```

### 5. bioRxiv Daily API Client

- **Task ID**: biorxiv-client
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the bioRxiv API client for daily incremental preprint ingestion. bioRxiv exposes a public JSON API at `https://api.biorxiv.org/details/biorxiv/{start_date}/{end_date}/{cursor}` that returns preprints by date range.

    ## What to do

    1. Create `src/aegis/sources/biorxiv.py`:

       ```python
       """bioRxiv API client for daily preprint ingestion.

       Uses the bioRxiv content API to fetch preprints by date range.
       Preprints contribute to R(c,q) recency at 0.6x peer-reviewed weight.
       """

       from __future__ import annotations

       import logging
       from collections.abc import AsyncIterator
       from datetime import date

       import httpx
       from pydantic import BaseModel, ConfigDict

       from aegis.sources.retry import RetryConfig, RetryPolicy
       from aegis.storage.schema import MeshDescriptor

       logger = logging.getLogger(__name__)

       BIORXIV_API_URL = "https://api.biorxiv.org/details/biorxiv"

       # Preprint weight relative to peer-reviewed publication
       PREPRINT_WEIGHT = 0.6


       class PreprintAuthor(BaseModel):
           """Author on a preprint."""

           model_config = ConfigDict(frozen=True)

           full_name: str
           institution: str | None
           orcid: str | None
           is_corresponding: bool


       class PreprintRecord(BaseModel):
           """Structured representation of a bioRxiv or medRxiv preprint."""

           model_config = ConfigDict(frozen=True)

           doi: str
           title: str
           abstract: str | None
           authors: list[PreprintAuthor]
           category: str | None            # bioRxiv subject category
           posted_date: date | None
           version: int
           server: str                      # "biorxiv" or "medrxiv"
           published_doi: str | None        # DOI of peer-reviewed version (if known)
           mesh_descriptors: list[MeshDescriptor]  # LLM-assigned MeSH (initially empty)
           weight: float = PREPRINT_WEIGHT  # Scoring weight relative to peer-reviewed


       class BioRxivClient:
           """Typed client for the bioRxiv content API."""

           def __init__(
               self,
               retry_policy: RetryPolicy | None = None,
           ) -> None:
               self._retry = retry_policy or RetryPolicy(RetryConfig())

           async def fetch_daily(
               self,
               target_date: date,
               batch_size: int = 100,
           ) -> AsyncIterator[PreprintRecord]:
               """Fetch all preprints posted on a specific date.

               Args:
                   target_date: The date to fetch preprints for.
                   batch_size: Number of records per API page (max 100).

               Yields:
                   PreprintRecord objects for each preprint posted on target_date.
               """
               date_str = target_date.isoformat()
               cursor = 0

               async with httpx.AsyncClient(timeout=60.0) as client:
                   while True:
                       url = f"{BIORXIV_API_URL}/{date_str}/{date_str}/{cursor}"

                       async def _do_get(u: str = url) -> httpx.Response:
                           resp = await client.get(u)
                           resp.raise_for_status()
                           return resp

                       response = await self._retry.execute(_do_get)
                       body = response.json()

                       messages = body.get("messages", [{}])
                       total = int(messages[0].get("total", 0)) if messages else 0
                       records = body.get("collection", [])

                       if not records:
                           break

                       for item in records:
                           record = self._parse_record(item)
                           if record is not None:
                               yield record

                       cursor += len(records)
                       if cursor >= total:
                           break

           async def fetch_date_range(
               self,
               start_date: date,
               end_date: date,
               batch_size: int = 100,
           ) -> AsyncIterator[PreprintRecord]:
               """Fetch preprints posted within a date range.

               Args:
                   start_date: Start of the date range (inclusive).
                   end_date: End of the date range (inclusive).
                   batch_size: Number of records per API page.

               Yields:
                   PreprintRecord objects.
               """
               cursor = 0
               start_str = start_date.isoformat()
               end_str = end_date.isoformat()

               async with httpx.AsyncClient(timeout=60.0) as client:
                   while True:
                       url = f"{BIORXIV_API_URL}/{start_str}/{end_str}/{cursor}"

                       async def _do_get(u: str = url) -> httpx.Response:
                           resp = await client.get(u)
                           resp.raise_for_status()
                           return resp

                       response = await self._retry.execute(_do_get)
                       body = response.json()

                       messages = body.get("messages", [{}])
                       total = int(messages[0].get("total", 0)) if messages else 0
                       records = body.get("collection", [])

                       if not records:
                           break

                       for item in records:
                           record = self._parse_record(item)
                           if record is not None:
                               yield record

                       cursor += len(records)
                       if cursor >= total:
                           break

           @staticmethod
           def _parse_record(data: dict) -> PreprintRecord | None:
               """Parse a bioRxiv API response item into a PreprintRecord."""
               try:
                   # Parse authors from the semicolon-separated author string
                   authors: list[PreprintAuthor] = []
                   author_str = data.get("authors", "")
                   if author_str:
                       for name in author_str.split(";"):
                           name = name.strip()
                           if name:
                               authors.append(PreprintAuthor(
                                   full_name=name,
                                   institution=None,
                                   orcid=None,
                                   is_corresponding=False,
                               ))

                   posted_date = None
                   date_str = data.get("date")
                   if date_str:
                       posted_date = date.fromisoformat(date_str)

                   version = int(data.get("version", "1"))

                   return PreprintRecord(
                       doi=data.get("doi", ""),
                       title=data.get("title", ""),
                       abstract=data.get("abstract"),
                       authors=authors,
                       category=data.get("category"),
                       posted_date=posted_date,
                       version=version,
                       server="biorxiv",
                       published_doi=data.get("published") or None,
                       mesh_descriptors=[],
                   )
               except (KeyError, ValueError, TypeError):
                   logger.warning("Failed to parse bioRxiv record: %s", data.get("doi", "?"))
                   return None


       def match_preprint_to_publication(
           preprint: PreprintRecord,
           published_doi: str,
       ) -> PreprintRecord:
           """Collapse a preprint with its peer-reviewed publication.

           Sets the published_doi field, marking this preprint as the
           'older version' of the peer-reviewed publication. Downstream
           scoring uses only the published version at full weight.

           Args:
               preprint: The original preprint record.
               published_doi: DOI of the peer-reviewed publication.

           Returns:
               Updated PreprintRecord with published_doi set.
           """
           return PreprintRecord(
               doi=preprint.doi,
               title=preprint.title,
               abstract=preprint.abstract,
               authors=preprint.authors,
               category=preprint.category,
               posted_date=preprint.posted_date,
               version=preprint.version,
               server=preprint.server,
               published_doi=published_doi,
               mesh_descriptors=preprint.mesh_descriptors,
               weight=0.0,  # Collapsed: no longer contributes independently
           )
       ```

    2. Update `src/aegis/sources/__init__.py` to add exports. The current `__init__.py` has imports and an `__all__` list. Add to the imports:
       ```python
       from aegis.sources.biorxiv import BioRxivClient, PreprintAuthor, PreprintRecord
       ```
       And add to the `__all__` list (in alphabetical order):
       ```python
       "BioRxivClient",
       "PreprintAuthor",
       "PreprintRecord",
       ```

    ## Files to create
    - `src/aegis/sources/biorxiv.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add bioRxiv exports

    ## Code patterns to follow
    - Follow exact patterns from `src/aegis/sources/pubmed.py`:
      - `from __future__ import annotations`
      - Pydantic `BaseModel` with `ConfigDict(frozen=True)`
      - `RetryPolicy` integration via constructor injection
      - `AsyncIterator` return type for paginated methods
      - `httpx.AsyncClient` with timeout
      - Logger at module level
    - The bioRxiv API returns JSON (not XML like PubMed), so use `response.json()` directly
    - API endpoint format: `https://api.biorxiv.org/details/biorxiv/{start_date}/{end_date}/{cursor}`
    - Response JSON structure: `{"messages": [{"total": N}], "collection": [{...}, ...]}`

    ## Acceptance criteria
    - `BioRxivClient` exists at `src/aegis/sources/biorxiv.py`
    - Design assertion: `BioRxivClient.fetch_daily(date) -> AsyncIterator[PreprintRecord]`
    - `PreprintRecord` has fields: `doi`, `title`, `abstract`, `authors`, `category`, `posted_date`, `version`, `server`, `published_doi`, `mesh_descriptors`, `weight`
    - `PreprintAuthor` has fields: `full_name`, `institution`, `orcid`, `is_corresponding`
    - `match_preprint_to_publication` sets `published_doi` and `weight=0.0`
    - `PREPRINT_WEIGHT = 0.6`
    - Imports work: `from aegis.sources.biorxiv import BioRxivClient, PreprintRecord`
    - mypy passes: `uv run mypy src/aegis/sources/biorxiv.py`
    - ruff passes: `uv run ruff check src/aegis/sources/biorxiv.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.biorxiv import BioRxivClient, PreprintRecord, PreprintAuthor, PREPRINT_WEIGHT, match_preprint_to_publication; assert PREPRINT_WEIGHT == 0.6; print('bioRxiv client imports OK')" && uv run mypy src/aegis/sources/biorxiv.py && uv run ruff check src/aegis/sources/biorxiv.py
    ```

### 6. medRxiv Daily API Client

- **Task ID**: medrxiv-client
- **Role**: builder
- **Depends On**: biorxiv-client
- **Assigned To**: builder-2
- **Description**: |
    Build the medRxiv API client for daily preprint ingestion. medRxiv uses the same API structure as bioRxiv but at a different endpoint: `https://api.biorxiv.org/details/medrxiv/{start_date}/{end_date}/{cursor}`.

    ## What to do

    1. Create `src/aegis/sources/medrxiv.py`:

       ```python
       """medRxiv API client for daily preprint ingestion.

       Uses the bioRxiv content API (shared infrastructure) to fetch
       medRxiv preprints by date range. Preprints contribute to R(c,q)
       recency at 0.6x peer-reviewed weight.
       """

       from __future__ import annotations

       import logging
       from collections.abc import AsyncIterator
       from datetime import date

       import httpx
       from pydantic import ConfigDict

       from aegis.sources.biorxiv import (
           PREPRINT_WEIGHT,
           PreprintAuthor,
           PreprintRecord,
       )
       from aegis.sources.retry import RetryConfig, RetryPolicy

       logger = logging.getLogger(__name__)

       MEDRXIV_API_URL = "https://api.biorxiv.org/details/medrxiv"


       class MedRxivClient:
           """Typed client for the medRxiv content API.

           medRxiv shares infrastructure with bioRxiv; the API is identical
           except for the server name in the URL path.
           """

           def __init__(
               self,
               retry_policy: RetryPolicy | None = None,
           ) -> None:
               self._retry = retry_policy or RetryPolicy(RetryConfig())

           async def fetch_daily(
               self,
               target_date: date,
               batch_size: int = 100,
           ) -> AsyncIterator[PreprintRecord]:
               """Fetch all medRxiv preprints posted on a specific date.

               Args:
                   target_date: The date to fetch preprints for.
                   batch_size: Number of records per API page.

               Yields:
                   PreprintRecord objects with server="medrxiv".
               """
               date_str = target_date.isoformat()
               cursor = 0

               async with httpx.AsyncClient(timeout=60.0) as client:
                   while True:
                       url = f"{MEDRXIV_API_URL}/{date_str}/{date_str}/{cursor}"

                       async def _do_get(u: str = url) -> httpx.Response:
                           resp = await client.get(u)
                           resp.raise_for_status()
                           return resp

                       response = await self._retry.execute(_do_get)
                       body = response.json()

                       messages = body.get("messages", [{}])
                       total = int(messages[0].get("total", 0)) if messages else 0
                       records = body.get("collection", [])

                       if not records:
                           break

                       for item in records:
                           record = self._parse_record(item)
                           if record is not None:
                               yield record

                       cursor += len(records)
                       if cursor >= total:
                           break

           async def fetch_date_range(
               self,
               start_date: date,
               end_date: date,
               batch_size: int = 100,
           ) -> AsyncIterator[PreprintRecord]:
               """Fetch medRxiv preprints within a date range."""
               cursor = 0
               start_str = start_date.isoformat()
               end_str = end_date.isoformat()

               async with httpx.AsyncClient(timeout=60.0) as client:
                   while True:
                       url = f"{MEDRXIV_API_URL}/{start_str}/{end_str}/{cursor}"

                       async def _do_get(u: str = url) -> httpx.Response:
                           resp = await client.get(u)
                           resp.raise_for_status()
                           return resp

                       response = await self._retry.execute(_do_get)
                       body = response.json()

                       messages = body.get("messages", [{}])
                       total = int(messages[0].get("total", 0)) if messages else 0
                       records = body.get("collection", [])

                       if not records:
                           break

                       for item in records:
                           record = self._parse_record(item)
                           if record is not None:
                               yield record

                       cursor += len(records)
                       if cursor >= total:
                           break

           @staticmethod
           def _parse_record(data: dict) -> PreprintRecord | None:
               """Parse a medRxiv API response item into a PreprintRecord."""
               try:
                   authors: list[PreprintAuthor] = []
                   author_str = data.get("authors", "")
                   if author_str:
                       for name in author_str.split(";"):
                           name = name.strip()
                           if name:
                               authors.append(PreprintAuthor(
                                   full_name=name,
                                   institution=None,
                                   orcid=None,
                                   is_corresponding=False,
                               ))

                   posted_date = None
                   date_str = data.get("date")
                   if date_str:
                       posted_date = date.fromisoformat(date_str)

                   version = int(data.get("version", "1"))

                   return PreprintRecord(
                       doi=data.get("doi", ""),
                       title=data.get("title", ""),
                       abstract=data.get("abstract"),
                       authors=authors,
                       category=data.get("category"),
                       posted_date=posted_date,
                       version=version,
                       server="medrxiv",
                       published_doi=data.get("published") or None,
                       mesh_descriptors=[],
                   )
               except (KeyError, ValueError, TypeError):
                   logger.warning("Failed to parse medRxiv record: %s", data.get("doi", "?"))
                   return None
       ```

    2. Update `src/aegis/sources/__init__.py` to add medRxiv exports. Add to the imports:
       ```python
       from aegis.sources.medrxiv import MedRxivClient
       ```
       And add to the `__all__` list (in alphabetical order):
       ```python
       "MedRxivClient",
       ```

    ## Files to create
    - `src/aegis/sources/medrxiv.py`

    ## Files to modify
    - `src/aegis/sources/__init__.py` — add medRxiv export

    ## Code patterns to follow
    - Same patterns as `src/aegis/sources/biorxiv.py` (reuses `PreprintRecord` and `PreprintAuthor`)
    - Only difference is `server="medrxiv"` and `MEDRXIV_API_URL`

    ## Acceptance criteria
    - `MedRxivClient` exists at `src/aegis/sources/medrxiv.py`
    - Design assertion: `MedRxivClient.fetch_daily(date) -> AsyncIterator[PreprintRecord]`
    - Records have `server="medrxiv"`
    - mypy passes: `uv run mypy src/aegis/sources/medrxiv.py`
    - ruff passes: `uv run ruff check src/aegis/sources/medrxiv.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.sources.medrxiv import MedRxivClient, MEDRXIV_API_URL; print('medRxiv client imports OK')" && uv run mypy src/aegis/sources/medrxiv.py && uv run ruff check src/aegis/sources/medrxiv.py
    ```

### 7. Preprint Tests (bioRxiv + medRxiv + Collapse)

- **Task ID**: preprint-tests
- **Role**: builder
- **Depends On**: medrxiv-client
- **Assigned To**: builder-2
- **Description**: |
    Build comprehensive tests for both bioRxiv and medRxiv clients, including preprint-to-publication collapse logic.

    ## What to do

    1. Create `src/aegis/sources/preprints_test.py`:

       ```python
       """Tests for bioRxiv and medRxiv preprint clients."""

       from __future__ import annotations

       import json
       from datetime import date

       import pytest
       import respx
       from httpx import Response

       from aegis.sources.biorxiv import (
           BIORXIV_API_URL,
           PREPRINT_WEIGHT,
           BioRxivClient,
           PreprintAuthor,
           PreprintRecord,
           match_preprint_to_publication,
       )
       from aegis.sources.medrxiv import MEDRXIV_API_URL, MedRxivClient


       def _make_biorxiv_response(
           records: list[dict], total: int | None = None
       ) -> dict:
           """Build a mock bioRxiv API response."""
           if total is None:
               total = len(records)
           return {
               "messages": [{"status": "ok", "total": str(total)}],
               "collection": records,
           }


       def _make_preprint_item(
           doi: str = "10.1101/2024.01.01.000001",
           title: str = "Test Preprint",
           authors: str = "Smith, J; Doe, A",
           abstract: str = "Test abstract",
           category: str = "neuroscience",
           date_str: str = "2024-01-15",
           version: str = "1",
           published: str = "",
       ) -> dict:
           return {
               "doi": doi,
               "title": title,
               "authors": authors,
               "abstract": abstract,
               "category": category,
               "date": date_str,
               "version": version,
               "published": published,
           }
       ```

       Then add these test functions:

       - `test_preprint_record_model`: Create a `PreprintRecord` with all fields, verify serialization.
       - `test_preprint_author_model`: Create a `PreprintAuthor` with all fields, verify serialization.
       - `test_preprint_weight`: Assert `PREPRINT_WEIGHT == 0.6`.
       - `test_biorxiv_parse_record`: Call `BioRxivClient._parse_record` with a mock item dict, verify all fields parsed correctly. Verify `server == "biorxiv"`.
       - `test_biorxiv_parse_record_missing_fields`: Call with minimal dict (only `doi`), verify parsing succeeds with None/empty defaults.
       - `test_biorxiv_author_parsing`: Verify semicolon-separated author string is split correctly into `PreprintAuthor` objects.
       - `test_biorxiv_fetch_daily`: Use `respx` to mock the GET to `BIORXIV_API_URL/2024-01-15/2024-01-15/0` returning 2 preprints. Verify `fetch_daily(date(2024, 1, 15))` yields 2 records.
       - `test_biorxiv_fetch_daily_pagination`: Mock two pages: first returns 2 records with total=3, second returns 1 record. Verify all 3 yielded.
       - `test_biorxiv_fetch_daily_empty`: Mock response with empty collection. Verify 0 records yielded.
       - `test_medrxiv_parse_record`: Call `MedRxivClient._parse_record`, verify `server == "medrxiv"`.
       - `test_medrxiv_fetch_daily`: Use `respx` to mock GET to `MEDRXIV_API_URL`, verify fetch_daily works.
       - `test_preprint_to_publication_collapse`: Create a preprint, call `match_preprint_to_publication` with a published DOI, verify `published_doi` is set and `weight == 0.0`.
       - `test_preprint_to_publication_preserves_fields`: Verify all other fields are preserved after collapse.
       - `test_preprint_default_weight`: Verify a fresh `PreprintRecord` has `weight == PREPRINT_WEIGHT`.

       Use `respx` for HTTP mocking and `@pytest.mark.asyncio(strict=True)` for async tests.

    ## Files to create
    - `src/aegis/sources/preprints_test.py`

    ## Files to modify
    None.

    ## Code patterns to follow
    - Test patterns from `src/aegis/sources/pubmed_test.py` and `src/aegis/sources/icite_test.py`
    - `respx` for HTTP mocking
    - `@pytest.mark.asyncio(strict=True)` for async tests
    - Helper functions for building mock responses

    ## Acceptance criteria
    - All tests pass: `uv run pytest src/aegis/sources/preprints_test.py -v`
    - Tests cover: model creation, parsing, daily fetch, pagination, empty response, preprint-to-publication collapse
    - At least 12 test functions

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/sources/preprints_test.py -v
    ```

### 8. Refresh Pipeline Orchestrator

- **Task ID**: refresh-orchestrator
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-2
- **Description**: |
    Build the RefreshOrchestrator that manages parallel refresh across ~25 sources with per-source workers, backpressure, rate limiting, and failure isolation. The orchestrator must complete a full daily refresh within 6 hours.

    ## What to do

    1. Create `src/aegis/ingestion/orchestrator.py`:

       ```python
       """RefreshOrchestrator: parallel refresh pipeline for ~25 sources.

       Manages concurrent source refresh with:
       - Per-source workers with independent error handling
       - Global concurrency limit (backpressure)
       - Per-source rate limiters (via semaphores)
       - Failure isolation: one source failure cannot cascade
       - Metrics reporting for SLO compliance
       """

       from __future__ import annotations

       import asyncio
       import logging
       import time
       from collections.abc import Awaitable, Callable
       from dataclasses import dataclass, field
       from datetime import UTC, datetime
       from enum import StrEnum

       from pydantic import BaseModel, ConfigDict

       logger = logging.getLogger(__name__)

       # Default configuration
       DEFAULT_GLOBAL_CONCURRENCY = 10  # Max simultaneous source refreshes
       DEFAULT_PER_SOURCE_CONCURRENCY = 3  # Max parallel tasks within one source
       DEFAULT_SOURCE_TIMEOUT_SECONDS = 3600.0  # 1 hour per source max
       DAILY_BUDGET_SECONDS = 6 * 3600  # 6 hours


       class SourceStatus(StrEnum):
           """Status of a source refresh."""

           pending = "pending"
           running = "running"
           completed = "completed"
           failed = "failed"
           timed_out = "timed_out"
           skipped = "skipped"


       class SourceRefreshResult(BaseModel):
           """Result of refreshing a single source."""

           model_config = ConfigDict(frozen=True)

           source_name: str
           status: SourceStatus
           records_ingested: int
           duration_seconds: float
           error_message: str | None
           started_at: datetime
           completed_at: datetime


       class RefreshSummary(BaseModel):
           """Summary of a full refresh cycle."""

           model_config = ConfigDict(frozen=True)

           total_sources: int
           completed: int
           failed: int
           timed_out: int
           skipped: int
           total_records: int
           total_duration_seconds: float
           within_budget: bool
           results: list[SourceRefreshResult]


       # Type for a source refresh function: async callable returning record count
       SourceRefreshFn = Callable[[], Awaitable[int]]


       @dataclass
       class SourceConfig:
           """Configuration for a single source in the refresh pipeline."""

           name: str
           refresh_fn: SourceRefreshFn
           concurrency_limit: int = DEFAULT_PER_SOURCE_CONCURRENCY
           timeout_seconds: float = DEFAULT_SOURCE_TIMEOUT_SECONDS
           priority: int = 0  # Lower = higher priority (runs first)
           enabled: bool = True


       class RefreshOrchestrator:
           """Parallel refresh orchestrator for multiple data sources.

           Usage:
               orchestrator = RefreshOrchestrator(global_concurrency=10)
               orchestrator.register_source(SourceConfig(
                   name="pubmed",
                   refresh_fn=pubmed_refresh,
               ))
               summary = await orchestrator.run_full_refresh()
           """

           def __init__(
               self,
               global_concurrency: int = DEFAULT_GLOBAL_CONCURRENCY,
               daily_budget_seconds: float = DAILY_BUDGET_SECONDS,
           ) -> None:
               self._global_semaphore = asyncio.Semaphore(global_concurrency)
               self._daily_budget = daily_budget_seconds
               self._sources: dict[str, SourceConfig] = {}
               self._results: list[SourceRefreshResult] = []

           def register_source(self, config: SourceConfig) -> None:
               """Register a source for refresh."""
               self._sources[config.name] = config
               logger.info("Registered source: %s (priority=%d)", config.name, config.priority)

           def unregister_source(self, name: str) -> None:
               """Remove a source from the refresh pipeline."""
               self._sources.pop(name, None)

           @property
           def source_count(self) -> int:
               """Number of registered sources."""
               return len(self._sources)

           async def run_full_refresh(self) -> RefreshSummary:
               """Run a complete refresh cycle across all registered sources.

               Sources are processed concurrently up to the global concurrency
               limit. Each source has its own timeout and error isolation.
               """
               start_time = time.monotonic()
               self._results = []

               # Sort sources by priority (lower = first)
               sorted_sources = sorted(
                   self._sources.values(),
                   key=lambda s: s.priority,
               )

               # Filter enabled sources
               active_sources = [s for s in sorted_sources if s.enabled]
               skipped_sources = [s for s in sorted_sources if not s.enabled]

               # Record skipped sources
               now = datetime.now(UTC)
               for src in skipped_sources:
                   self._results.append(SourceRefreshResult(
                       source_name=src.name,
                       status=SourceStatus.skipped,
                       records_ingested=0,
                       duration_seconds=0.0,
                       error_message=None,
                       started_at=now,
                       completed_at=now,
                   ))

               # Run active sources concurrently
               tasks = [
                   self._refresh_source(source)
                   for source in active_sources
               ]

               if tasks:
                   # Use gather with return_exceptions for failure isolation
                   await asyncio.gather(*tasks, return_exceptions=True)

               total_duration = time.monotonic() - start_time

               completed = sum(1 for r in self._results if r.status == SourceStatus.completed)
               failed = sum(1 for r in self._results if r.status == SourceStatus.failed)
               timed_out = sum(1 for r in self._results if r.status == SourceStatus.timed_out)
               skipped = sum(1 for r in self._results if r.status == SourceStatus.skipped)
               total_records = sum(r.records_ingested for r in self._results)

               summary = RefreshSummary(
                   total_sources=len(sorted_sources),
                   completed=completed,
                   failed=failed,
                   timed_out=timed_out,
                   skipped=skipped,
                   total_records=total_records,
                   total_duration_seconds=total_duration,
                   within_budget=total_duration <= self._daily_budget,
                   results=list(self._results),
               )

               logger.info(
                   "Refresh cycle complete: %d/%d sources OK, %d failed, "
                   "%d timed out, %.1fs total (budget: %s)",
                   completed,
                   summary.total_sources,
                   failed,
                   timed_out,
                   total_duration,
                   "MET" if summary.within_budget else "EXCEEDED",
               )

               return summary

           async def _refresh_source(self, source: SourceConfig) -> None:
               """Refresh a single source with concurrency control and timeout."""
               start_time = time.monotonic()
               started_at = datetime.now(UTC)

               async with self._global_semaphore:
                   try:
                       records = await asyncio.wait_for(
                           source.refresh_fn(),
                           timeout=source.timeout_seconds,
                       )
                       duration = time.monotonic() - start_time
                       self._results.append(SourceRefreshResult(
                           source_name=source.name,
                           status=SourceStatus.completed,
                           records_ingested=records,
                           duration_seconds=duration,
                           error_message=None,
                           started_at=started_at,
                           completed_at=datetime.now(UTC),
                       ))
                       logger.info(
                           "Source %s completed: %d records in %.1fs",
                           source.name,
                           records,
                           duration,
                       )

                   except asyncio.TimeoutError:
                       duration = time.monotonic() - start_time
                       self._results.append(SourceRefreshResult(
                           source_name=source.name,
                           status=SourceStatus.timed_out,
                           records_ingested=0,
                           duration_seconds=duration,
                           error_message=f"Timed out after {source.timeout_seconds}s",
                           started_at=started_at,
                           completed_at=datetime.now(UTC),
                       ))
                       logger.warning(
                           "Source %s timed out after %.1fs",
                           source.name,
                           duration,
                       )

                   except Exception as exc:
                       duration = time.monotonic() - start_time
                       self._results.append(SourceRefreshResult(
                           source_name=source.name,
                           status=SourceStatus.failed,
                           records_ingested=0,
                           duration_seconds=duration,
                           error_message=str(exc),
                           started_at=started_at,
                           completed_at=datetime.now(UTC),
                       ))
                       logger.exception(
                           "Source %s failed after %.1fs: %s",
                           source.name,
                           duration,
                           exc,
                       )

           async def refresh_single(self, source_name: str) -> SourceRefreshResult | None:
               """Refresh a single source by name. Returns result or None if not found."""
               source = self._sources.get(source_name)
               if source is None:
                   logger.warning("Source not found: %s", source_name)
                   return None
               self._results = []
               await self._refresh_source(source)
               return self._results[0] if self._results else None
       ```

    2. Create `src/aegis/ingestion/orchestrator_test.py`:

       ```python
       """Tests for the RefreshOrchestrator."""

       from __future__ import annotations

       import asyncio

       import pytest

       from aegis.ingestion.orchestrator import (
           DEFAULT_GLOBAL_CONCURRENCY,
           DAILY_BUDGET_SECONDS,
           RefreshOrchestrator,
           RefreshSummary,
           SourceConfig,
           SourceRefreshResult,
           SourceStatus,
       )
       ```

       Then add these test functions:

       - `test_register_source`: Create orchestrator, register 3 sources, verify `source_count == 3`.
       - `test_unregister_source`: Register then unregister, verify `source_count` decrements.
       - `test_run_full_refresh_all_succeed`: Register 3 sources with `refresh_fn` that returns 100 (using `async def fake(): return 100`). Run `run_full_refresh()`. Verify summary has `completed=3, failed=0, total_records=300`.
       - `test_failure_isolation`: Register 3 sources: first raises `RuntimeError`, second and third return 50. Verify summary has `completed=2, failed=1, total_records=100`.
       - `test_timeout_isolation`: Register a source with `timeout_seconds=0.1` and `refresh_fn` that `await asyncio.sleep(10)` then returns 0. Register another normal source. Verify one timed_out, one completed.
       - `test_skipped_sources`: Register a source with `enabled=False`. Verify summary has `skipped=1`.
       - `test_priority_ordering`: Register 3 sources with priorities 2, 0, 1. Track call order via a list append. Verify order is 0, 1, 2 (note: with concurrency they may run simultaneously, so this tests that higher-priority sources start first).
       - `test_global_concurrency_limit`: Register 5 sources. Set `global_concurrency=2`. Track max concurrent via an asyncio counter. Verify max concurrent never exceeds 2.
       - `test_within_budget`: Register sources that complete quickly. Verify `within_budget=True`.
       - `test_refresh_single`: Register a source, call `refresh_single("name")`, verify result.
       - `test_refresh_single_not_found`: Call `refresh_single("nonexistent")`, verify None.
       - `test_source_status_enum`: Verify all expected values exist.
       - `test_source_config_defaults`: Create `SourceConfig` with minimal args, verify defaults.

       All async tests use `@pytest.mark.asyncio(strict=True)`.

    ## Files to create
    - `src/aegis/ingestion/orchestrator.py`
    - `src/aegis/ingestion/orchestrator_test.py`

    ## Files to modify
    None.

    ## Code patterns to follow
    - `from __future__ import annotations` at top
    - Pydantic `BaseModel` with `ConfigDict(frozen=True)` for result models
    - `StrEnum` for status enums
    - `asyncio.Semaphore` for concurrency control (same pattern as rate limiting)
    - `asyncio.wait_for` for timeouts
    - `asyncio.gather` with `return_exceptions=True` for failure isolation
    - `time.monotonic()` for duration tracking
    - Logger at module level

    ## Acceptance criteria
    - `RefreshOrchestrator` exists with `register_source`, `run_full_refresh`, `refresh_single`
    - `SourceConfig` has: `name`, `refresh_fn`, `concurrency_limit`, `timeout_seconds`, `priority`, `enabled`
    - `RefreshSummary` has: `total_sources`, `completed`, `failed`, `timed_out`, `skipped`, `total_records`, `total_duration_seconds`, `within_budget`, `results`
    - Failure isolation: one source's error does not affect others
    - Timeout isolation: one source's timeout does not affect others
    - Global concurrency limit enforced
    - All tests pass: `uv run pytest src/aegis/ingestion/orchestrator_test.py -v`
    - mypy passes: `uv run mypy src/aegis/ingestion/orchestrator.py`
    - ruff passes: `uv run ruff check src/aegis/ingestion/orchestrator.py`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "from aegis.ingestion.orchestrator import RefreshOrchestrator, SourceConfig, RefreshSummary, SourceStatus; print('Orchestrator imports OK')" && uv run pytest src/aegis/ingestion/orchestrator_test.py -v && uv run mypy src/aegis/ingestion/orchestrator.py && uv run ruff check src/aegis/ingestion/orchestrator.py
    ```

### 9. Update Freshness SLOs + Source Package Exports

- **Task ID**: update-slos-exports
- **Role**: builder
- **Depends On**: remaining-feed-watchers, preprint-tests, refresh-orchestrator
- **Assigned To**: builder-1
- **Description**: |
    Update the observability freshness SLOs to include all new sources, and ensure all new modules are properly exported from their parent packages.

    ## What to do

    1. Update `src/aegis/observability/freshness.py` to add SLOs for new sources. The current `SOURCE_SLOS` dict is:
       ```python
       SOURCE_SLOS: dict[str, float] = {
           "pubmed": 24 * 3600,      # 24 hours
           "reporter": 48 * 3600,    # 48 hours
           "ctgov": 24 * 3600,       # 24 hours
       }
       ```
       Add the following entries (maintain alphabetical order):
       ```python
       SOURCE_SLOS: dict[str, float] = {
           "biorxiv": 24 * 3600,           # 24 hours (daily ingestion)
           "ctgov": 24 * 3600,             # 24 hours
           "medrxiv": 24 * 3600,           # 24 hours (daily ingestion)
           "ofac": 6 * 3600,               # 6 hours (event-driven SLO)
           "ori": 6 * 3600,                # 6 hours (event-driven SLO)
           "pubmed": 24 * 3600,            # 24 hours
           "reporter": 48 * 3600,          # 48 hours
           "retraction_watch": 6 * 3600,   # 6 hours (event-driven SLO)
           "sam": 6 * 3600,                # 6 hours (event-driven SLO)
           "state_board_CA": 6 * 3600,     # 6 hours (event-driven SLO)
           "state_board_FL": 6 * 3600,     # 6 hours
           "state_board_NY": 6 * 3600,     # 6 hours
           "state_board_PA": 6 * 3600,     # 6 hours
           "state_board_TX": 6 * 3600,     # 6 hours
       }
       ```

    2. Update `src/aegis/ingestion/__init__.py` to export key classes:
       ```python
       """Aegis ingestion: event-driven integrity pipeline and refresh orchestration."""

       from __future__ import annotations

       from aegis.ingestion.event_dispatcher import (
           IntegrityActionType,
           IntegrityEvent,
           IntegrityEventDispatcher,
           IntegritySeverity,
           IntegritySource,
       )
       from aegis.ingestion.orchestrator import (
           RefreshOrchestrator,
           RefreshSummary,
           SourceConfig,
           SourceRefreshResult,
           SourceStatus,
       )

       __all__ = [
           "IntegrityActionType",
           "IntegrityEvent",
           "IntegrityEventDispatcher",
           "IntegritySeverity",
           "IntegritySource",
           "RefreshOrchestrator",
           "RefreshSummary",
           "SourceConfig",
           "SourceRefreshResult",
           "SourceStatus",
       ]
       ```

    3. Update `src/aegis/ingestion/event_driven/__init__.py` to export watchers:
       ```python
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
       ```

    4. Verify that the `src/aegis/sources/__init__.py` now includes both `BioRxivClient` and `MedRxivClient` exports (added by builder-2 in tasks 5 and 6). If not present, add them.

    ## Files to modify
    - `src/aegis/observability/freshness.py` — update `SOURCE_SLOS` dict
    - `src/aegis/ingestion/__init__.py` — add exports
    - `src/aegis/ingestion/event_driven/__init__.py` — add exports
    - `src/aegis/sources/__init__.py` — verify bioRxiv/medRxiv exports present

    ## Code patterns to follow
    - Follow existing `__init__.py` export patterns from `src/aegis/sources/__init__.py`
    - Maintain alphabetical ordering in `__all__` and `SOURCE_SLOS`

    ## Acceptance criteria
    - `SOURCE_SLOS` has entries for `biorxiv`, `medrxiv`, `ofac`, `ori`, `retraction_watch`, `sam`, and state boards
    - All integrity source SLOs are 6 hours (21600 seconds)
    - `from aegis.ingestion import IntegrityEventDispatcher, RefreshOrchestrator` works
    - `from aegis.ingestion.event_driven import RetractionWatchWatcher, ORIRegisterWatcher` works
    - `from aegis.sources import BioRxivClient, MedRxivClient` works
    - Existing freshness tests still pass
    - mypy passes on modified files
    - ruff passes on modified files

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.ingestion import IntegrityEventDispatcher, RefreshOrchestrator
    from aegis.ingestion.event_driven import RetractionWatchWatcher, ORIRegisterWatcher, OFACWatcher, SAMWatcher, StateBoardWatcher
    from aegis.sources import BioRxivClient, MedRxivClient
    from aegis.observability.freshness import SOURCE_SLOS
    assert 'retraction_watch' in SOURCE_SLOS
    assert 'biorxiv' in SOURCE_SLOS
    assert SOURCE_SLOS['retraction_watch'] == 6 * 3600
    print('All exports and SLOs OK')
    " && uv run pytest src/aegis/observability/freshness_test.py -v && uv run mypy src/aegis/observability/freshness.py && uv run ruff check src/aegis/ingestion/ src/aegis/observability/freshness.py
    ```

### 10. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: update-slos-exports
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for Phase 3a.

    ## Validation Commands

    1. Verify ingestion package imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.ingestion import IntegrityEventDispatcher, IntegrityEvent, IntegritySource, IntegrityActionType, IntegritySeverity
    from aegis.ingestion import RefreshOrchestrator, SourceConfig, RefreshSummary, SourceStatus
    print('Ingestion package imports OK')
    "
    ```

    2. Verify event-driven watcher imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.ingestion.event_driven import FeedWatcher, FeedEntry
    from aegis.ingestion.event_driven import RetractionWatchWatcher, ORIRegisterWatcher
    from aegis.ingestion.event_driven import OFACWatcher, SAMWatcher, StateBoardWatcher
    from aegis.ingestion.event_driven import create_all_state_watchers
    print('Event-driven watcher imports OK')
    "
    ```

    3. Verify preprint client imports:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.sources.biorxiv import BioRxivClient, PreprintRecord, PreprintAuthor, PREPRINT_WEIGHT, match_preprint_to_publication
    from aegis.sources.medrxiv import MedRxivClient, MEDRXIV_API_URL
    assert PREPRINT_WEIGHT == 0.6
    print('Preprint client imports OK')
    "
    ```

    4. Verify design assertions:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    import inspect
    from aegis.sources.biorxiv import BioRxivClient
    from aegis.sources.medrxiv import MedRxivClient
    from aegis.ingestion.event_dispatcher import IntegrityEventDispatcher
    # BioRxivClient.fetch_daily exists
    assert hasattr(BioRxivClient, 'fetch_daily')
    # MedRxivClient.fetch_daily exists
    assert hasattr(MedRxivClient, 'fetch_daily')
    # IntegrityEventDispatcher.publish exists
    assert hasattr(IntegrityEventDispatcher, 'publish')
    assert hasattr(IntegrityEventDispatcher, 'subscribe')
    print('Design assertions OK')
    "
    ```

    5. Verify freshness SLOs:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "
    from aegis.observability.freshness import SOURCE_SLOS
    integrity_sources = ['retraction_watch', 'ori', 'ofac', 'sam']
    for src in integrity_sources:
        assert src in SOURCE_SLOS, f'{src} missing from SOURCE_SLOS'
        assert SOURCE_SLOS[src] == 6 * 3600, f'{src} SLO should be 6h'
    assert 'biorxiv' in SOURCE_SLOS
    assert 'medrxiv' in SOURCE_SLOS
    print('Freshness SLOs OK')
    "
    ```

    6. Run all new tests:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/ingestion/event_dispatcher_test.py src/aegis/ingestion/event_driven/feed_watcher_test.py src/aegis/ingestion/orchestrator_test.py src/aegis/sources/preprints_test.py -v
    ```

    7. Run mypy on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run mypy src/aegis/ingestion/event_dispatcher.py src/aegis/ingestion/event_driven/feed_watcher.py src/aegis/ingestion/event_driven/retraction_watch.py src/aegis/ingestion/event_driven/ori_register.py src/aegis/ingestion/event_driven/ofac_sam.py src/aegis/ingestion/event_driven/state_boards.py src/aegis/ingestion/orchestrator.py src/aegis/sources/biorxiv.py src/aegis/sources/medrxiv.py
    ```

    8. Run ruff on all new modules:
    ```bash
    cd /Users/anvith/aegis && uv run ruff check src/aegis/ingestion/ src/aegis/sources/biorxiv.py src/aegis/sources/medrxiv.py
    ```

    9. Verify existing tests still pass:
    ```bash
    cd /Users/anvith/aegis && uv run pytest src/aegis/storage/ src/aegis/observability/ -v
    ```

    10. Verify feedparser dependency installed:
    ```bash
    cd /Users/anvith/aegis && uv run python -c "import feedparser; print(f'feedparser {feedparser.__version__} OK')"
    ```

    ## Acceptance Criteria
    - `IntegrityEventDispatcher.publish(event: IntegrityEvent)` exists
    - `IntegrityEvent` has `event_id`, `source`, `action_type`, `severity`, `candidate_identifiers`
    - `IntegritySource` has `retraction_watch`, `ori`, `ofac`, `sam`, `leie`, `state_medical_board`
    - `FeedWatcher` ABC exists with `feed_url`, `source_name`, `parse_entry`
    - `RetractionWatchWatcher`, `ORIRegisterWatcher`, `OFACWatcher`, `SAMWatcher`, `StateBoardWatcher` all subclass `FeedWatcher`
    - `BioRxivClient.fetch_daily(date) -> AsyncIterator[PreprintRecord]` exists
    - `MedRxivClient.fetch_daily(date) -> AsyncIterator[PreprintRecord]` exists
    - `PreprintRecord.weight == 0.6` by default
    - `match_preprint_to_publication` sets `weight=0.0` on collapsed preprints
    - `RefreshOrchestrator.run_full_refresh() -> RefreshSummary` exists
    - Failure isolation: one source's error does not cascade
    - `SOURCE_SLOS` has entries for all integrity sources at 6h
    - All new tests pass
    - mypy strict passes on all new modules
    - ruff passes on all new modules
    - No existing Phase 0-2 tests broken
    - `feedparser` is in `pyproject.toml` dependencies

## Acceptance Criteria

- `IntegrityEventDispatcher` at `src/aegis/ingestion/event_dispatcher.py` exports `publish(event: IntegrityEvent)` and `subscribe(handler: EventHandler)` with asyncio queue-backed bus
- `IntegrityEvent` schema has `event_id`, `source: IntegritySource`, `action_type: IntegrityActionType`, `severity: IntegritySeverity`, `candidate_identifiers: dict[str, str]`, `detail`, `source_url`, `detected_at`, `published_at`
- `FeedWatcher` ABC at `src/aegis/ingestion/event_driven/feed_watcher.py` with `feed_url`, `source_name`, `parse_entry` abstract methods, plus `poll_once`, `start`, `stop`, and deduplication
- `RetractionWatchWatcher` monitors `https://retractionwatch.com/feed/` with severity classification (fabrication/falsification -> critical)
- `ORIRegisterWatcher` monitors Federal Register Atom feed filtered for ORI, publishes critical-severity events for misconduct findings
- `OFACWatcher` and `SAMWatcher` monitor change-data feeds with addition/removal classification
- `StateBoardWatcher` supports multi-state monitoring with per-state feeds and severity classification
- `BioRxivClient.fetch_daily(date) -> AsyncIterator[PreprintRecord]` with `PreprintRecord.weight == 0.6`
- `MedRxivClient.fetch_daily(date) -> AsyncIterator[PreprintRecord]` with `server="medrxiv"`
- `match_preprint_to_publication` collapses preprint with published DOI, setting `weight=0.0`
- `RefreshOrchestrator.run_full_refresh() -> RefreshSummary` with global concurrency limit, per-source timeouts, failure isolation, and `within_budget` flag
- `SOURCE_SLOS` updated with 6-hour SLOs for all integrity sources and 24-hour SLOs for preprints
- All new tests pass
- mypy strict passes on all new modules
- ruff lint passes on all new modules
- No existing Phase 0-2 tests broken
- `feedparser>=6.0` added to `pyproject.toml` dependencies

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis && uv run pytest src/aegis/ingestion/event_dispatcher_test.py src/aegis/ingestion/event_driven/feed_watcher_test.py src/aegis/ingestion/orchestrator_test.py src/aegis/sources/preprints_test.py -v` — Run all Phase 3a tests
- `cd /Users/anvith/aegis && uv run mypy src/aegis/ingestion/event_dispatcher.py src/aegis/ingestion/event_driven/feed_watcher.py src/aegis/ingestion/event_driven/retraction_watch.py src/aegis/ingestion/event_driven/ori_register.py src/aegis/ingestion/event_driven/ofac_sam.py src/aegis/ingestion/event_driven/state_boards.py src/aegis/ingestion/orchestrator.py src/aegis/sources/biorxiv.py src/aegis/sources/medrxiv.py` — Type-check all new modules
- `cd /Users/anvith/aegis && uv run ruff check src/aegis/ingestion/ src/aegis/sources/biorxiv.py src/aegis/sources/medrxiv.py` — Lint all new modules
- `cd /Users/anvith/aegis && uv run pytest src/aegis/storage/ src/aegis/observability/ -v` — Verify existing tests still pass
- `cd /Users/anvith/aegis && uv run python -c "from aegis.observability.freshness import SOURCE_SLOS; assert 'retraction_watch' in SOURCE_SLOS; assert SOURCE_SLOS['retraction_watch'] == 21600; print('SLOs OK')"` — Verify freshness SLOs

## Notes

- bioRxiv/medRxiv API documentation: https://api.biorxiv.org/ — both servers share the same API structure, differing only in the server name in the URL path
- The bioRxiv API response format is: `{"messages": [{"total": "N"}], "collection": [{doi, title, authors, abstract, category, date, version, published}, ...]}`
- `feedparser` is needed for RSS/Atom parsing in the feed watchers; add via `uv add feedparser>=6.0`
- The IntegrityEventDispatcher uses asyncio queues for the in-process bus; a Redis Streams adapter can be added later for multi-process deployment without changing the interface
- Preprint MeSH tagging via LLM is referenced in the spec but the LLM coverage-fallback itself is out of scope for this sub-spec (it already exists in the system); the `mesh_descriptors` field on `PreprintRecord` starts empty and is populated by a separate MeSH assignment pass
- The RefreshOrchestrator is designed for ~25 sources but the architecture supports any number; the global concurrency limit prevents resource exhaustion
- State board RSS feed URLs are placeholders representing the expected pattern; actual URLs will be configured at deployment time
- OFAC feed URL and SAM feed URL are approximate; the exact endpoints may require API key registration at deployment time
