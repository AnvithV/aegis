"""Tests for FeedWatcher ABC and feed utilities."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest
import respx
from httpx import Response

from aegis.ingestion.event_dispatcher import (
    IntegrityActionType,
    IntegrityEvent,
    IntegrityEventDispatcher,
    IntegritySeverity,
    IntegritySource,
)
from aegis.ingestion.event_driven.feed_watcher import (
    FeedEntry,
    FeedWatcher,
    _entry_fingerprint,
    _parse_datetime,
)
from aegis.ingestion.event_driven.ofac_sam import (
    OFAC_FEED_URL,
    SAM_FEED_URL,
    OFACWatcher,
    SAMWatcher,
    _classify_ofac_action,
)
from aegis.ingestion.event_driven.ori_register import (
    ORIRegisterWatcher,
    _extract_researcher_name,
    _is_misconduct_finding,
)
from aegis.ingestion.event_driven.retraction_watch import (
    RETRACTION_WATCH_FEED_URL,
    RetractionWatchWatcher,
    _classify_severity,
    _extract_author_names,
)
from aegis.ingestion.event_driven.state_boards import (
    STATE_BOARD_FEEDS,
    StateBoardWatcher,
    _classify_board_action_severity,
    create_all_state_watchers,
)

MOCK_RSS = """\
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
"""


class MockFeedWatcher(FeedWatcher):
    """Concrete FeedWatcher for testing."""

    @property
    def feed_url(self) -> str:
        return "https://example.com/feed.xml"

    @property
    def source_name(self) -> str:
        return "mock_source"

    async def parse_entry(
        self, entry: FeedEntry
    ) -> IntegrityEvent | None:
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


def test_feed_entry_creation() -> None:
    """Create a FeedEntry with all fields, verify attributes."""
    now = datetime.now(UTC)
    entry = FeedEntry(
        entry_id="id-1",
        title="Test Title",
        link="https://example.com",
        summary="A summary",
        published=now,
        updated=now,
        raw={"key": "value"},
    )
    assert entry.entry_id == "id-1"
    assert entry.title == "Test Title"
    assert entry.link == "https://example.com"
    assert entry.summary == "A summary"
    assert entry.published == now
    assert entry.updated == now
    assert entry.raw == {"key": "value"}


def test_entry_fingerprint_deterministic() -> None:
    """Same input dict produces same fingerprint."""
    entry = {"id": "1", "title": "Test", "link": "https://example.com"}
    fp1 = _entry_fingerprint(entry)
    fp2 = _entry_fingerprint(entry)
    assert fp1 == fp2


def test_entry_fingerprint_unique() -> None:
    """Different input dicts produce different fingerprints."""
    entry_a = {"id": "1", "title": "Test A", "link": "https://a.com"}
    entry_b = {"id": "2", "title": "Test B", "link": "https://b.com"}
    assert _entry_fingerprint(entry_a) != _entry_fingerprint(entry_b)


def test_parse_datetime_valid() -> None:
    """Pass a valid time.struct_time, verify datetime output."""
    ts = time.strptime("2024-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
    result = _parse_datetime(ts)
    assert result is not None
    assert isinstance(result, datetime)
    assert result.tzinfo == UTC


def test_parse_datetime_none() -> None:
    """Pass None, verify None returned."""
    assert _parse_datetime(None) is None


@pytest.mark.asyncio
@respx.mock
async def test_poll_once_parses_rss() -> None:
    """Poll a mocked RSS feed, verify 2 events returned."""
    respx.get("https://example.com/feed.xml").mock(
        return_value=Response(200, text=MOCK_RSS)
    )

    dispatcher = IntegrityEventDispatcher()
    watcher = MockFeedWatcher(dispatcher)
    events = await watcher.poll_once()

    assert len(events) == 2
    assert events[0].detail == "Item 1"
    assert events[1].detail == "Item 2"


@pytest.mark.asyncio
@respx.mock
async def test_deduplication() -> None:
    """Poll the same feed twice. Second poll yields 0 new events."""
    respx.get("https://example.com/feed.xml").mock(
        return_value=Response(200, text=MOCK_RSS)
    )

    dispatcher = IntegrityEventDispatcher()
    watcher = MockFeedWatcher(dispatcher)

    first = await watcher.poll_once()
    assert len(first) == 2

    second = await watcher.poll_once()
    assert len(second) == 0


@pytest.mark.asyncio
@respx.mock
async def test_http_failure_handled() -> None:
    """HTTP 500 returns empty list without raising."""
    respx.get("https://example.com/feed.xml").mock(
        return_value=Response(500)
    )

    dispatcher = IntegrityEventDispatcher()
    watcher = MockFeedWatcher(dispatcher)
    events = await watcher.poll_once()

    assert events == []


@pytest.mark.asyncio
@respx.mock
async def test_stats() -> None:
    """After polling, verify stats dict is correct."""
    respx.get("https://example.com/feed.xml").mock(
        return_value=Response(200, text=MOCK_RSS)
    )

    dispatcher = IntegrityEventDispatcher()
    watcher = MockFeedWatcher(dispatcher)
    await watcher.poll_once()

    stats = watcher.stats
    assert stats["polls_completed"] == 1
    assert stats["entries_processed"] == 2
    assert stats["seen_fingerprints"] == 2


# --- Retraction Watch watcher tests ---


def test_rw_severity_fabrication() -> None:
    """Fabrication keywords yield critical severity."""
    result = _classify_severity("Paper retracted for fabrication", None)
    assert result == IntegritySeverity.critical


def test_rw_severity_falsification() -> None:
    """Falsification keywords yield critical severity."""
    result = _classify_severity("Data falsification found", None)
    assert result == IntegritySeverity.critical


def test_rw_severity_expression_of_concern() -> None:
    """Expression of concern yields medium severity."""
    result = _classify_severity(
        "Expression of concern for paper", None
    )
    assert result == IntegritySeverity.medium


def test_rw_severity_standard_retraction() -> None:
    """Standard retraction yields high severity."""
    result = _classify_severity("Paper retracted due to errors", None)
    assert result == IntegritySeverity.high


def test_rw_extract_author() -> None:
    """Extract author name from retraction title."""
    names = _extract_author_names(
        "Paper by John Smith retracted", None
    )
    assert names == ["John Smith"]


@pytest.mark.asyncio
async def test_rw_parse_entry() -> None:
    """RetractionWatchWatcher.parse_entry returns correct event."""
    dispatcher = IntegrityEventDispatcher()
    watcher = RetractionWatchWatcher(dispatcher)

    entry = FeedEntry(
        entry_id="rw-1",
        title="Paper retracted for fabrication by Jane Doe",
        link="https://retractionwatch.com/2024/01/01/test",
        summary="A paper was retracted.",
        published=datetime.now(UTC),
        updated=None,
        raw={},
    )
    event = await watcher.parse_entry(entry)
    assert event is not None
    assert event.source == IntegritySource.retraction_watch
    assert event.action_type == IntegrityActionType.retraction_added
    assert event.severity == IntegritySeverity.critical


def test_rw_feed_url() -> None:
    """RetractionWatchWatcher.feed_url equals the constant."""
    dispatcher = IntegrityEventDispatcher()
    watcher = RetractionWatchWatcher(dispatcher)
    assert watcher.feed_url == RETRACTION_WATCH_FEED_URL


# --- ORI Federal Register watcher tests ---


def test_ori_is_misconduct_finding_true() -> None:
    """Misconduct keywords are detected."""
    assert _is_misconduct_finding(
        "Findings of Research Misconduct; John Smith", None
    )


def test_ori_is_misconduct_finding_false() -> None:
    """Non-misconduct entries are rejected."""
    assert not _is_misconduct_finding("Budget Allocation Notice", None)


def test_ori_extract_researcher_name() -> None:
    """Extract name after semicolon in ORI title."""
    name = _extract_researcher_name(
        "Findings of Research Misconduct; John Q. Smith", None
    )
    assert name == "John Q. Smith"


@pytest.mark.asyncio
async def test_ori_parse_entry_skips_non_misconduct() -> None:
    """Non-misconduct entries return None."""
    dispatcher = IntegrityEventDispatcher()
    watcher = ORIRegisterWatcher(dispatcher)
    entry = FeedEntry(
        entry_id="ori-1",
        title="Budget Allocation Notice",
        link="https://federalregister.gov/test",
        summary=None,
        published=datetime.now(UTC),
        updated=None,
        raw={},
    )
    assert await watcher.parse_entry(entry) is None


# --- OFAC/SAM watcher tests ---


def test_ofac_classify_addition() -> None:
    """New SDN listing classifies as sanctions_added/critical."""
    action, severity = _classify_ofac_action("New SDN listing", None)
    assert action == IntegrityActionType.sanctions_added
    assert severity == IntegritySeverity.critical


def test_ofac_classify_removal() -> None:
    """Entity removal classifies as sanctions_removed/low."""
    action, severity = _classify_ofac_action(
        "Entity removed from list", None
    )
    assert action == IntegrityActionType.sanctions_removed
    assert severity == IntegritySeverity.low


def test_ofac_watcher_feed_url() -> None:
    """OFACWatcher.feed_url equals OFAC_FEED_URL."""
    dispatcher = IntegrityEventDispatcher()
    watcher = OFACWatcher(dispatcher)
    assert watcher.feed_url == OFAC_FEED_URL


def test_sam_watcher_feed_url() -> None:
    """SAMWatcher.feed_url equals SAM_FEED_URL."""
    dispatcher = IntegrityEventDispatcher()
    watcher = SAMWatcher(dispatcher)
    assert watcher.feed_url == SAM_FEED_URL


# --- State board watcher tests ---


def test_state_board_severity_revocation() -> None:
    """Revocation maps to critical severity."""
    assert (
        _classify_board_action_severity("License Revocation", None)
        == IntegritySeverity.critical
    )


def test_state_board_severity_probation() -> None:
    """Probation maps to high severity."""
    assert (
        _classify_board_action_severity("Probation ordered", None)
        == IntegritySeverity.high
    )


def test_state_board_watcher_state_code() -> None:
    """StateBoardWatcher state_code property returns correct code."""
    dispatcher = IntegrityEventDispatcher()
    watcher = StateBoardWatcher(dispatcher, state_code="CA")
    assert watcher.state_code == "CA"


def test_create_all_state_watchers() -> None:
    """create_all_state_watchers creates one watcher per state."""
    dispatcher = IntegrityEventDispatcher()
    watchers = create_all_state_watchers(dispatcher)
    assert len(watchers) == len(STATE_BOARD_FEEDS)
    codes = {w.state_code for w in watchers}
    assert codes == set(STATE_BOARD_FEEDS.keys())
