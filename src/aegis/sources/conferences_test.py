"""Tests for conference proceedings ingestion."""

from __future__ import annotations

from aegis.sources.conferences.aacr import AacrIngestor
from aegis.sources.conferences.acs import AcsIngestor
from aegis.sources.conferences.asco import AscoIngestor
from aegis.sources.conferences.base import ConferenceIngestor, TalkRecord, TalkType
from aegis.sources.conferences.llm_extract import (
    DefaultLLMExtractor,
    talks_from_extraction,
)


def test_talk_record_model() -> None:
    """TalkRecord is frozen and stores all fields."""
    talk = TalkRecord(
        presenter_name="Jane Doe",
        talk_type=TalkType(is_oral_presentation=True),
        session_title="Oncology Advances",
        conference_name="ASCO Annual Meeting",
        year=2025,
        abstract_title="Novel Biomarker Discovery",
        coauthors=["John Smith", "Alice Brown"],
        source_url="https://example.com/abstract/123",
    )
    assert talk.presenter_name == "Jane Doe"
    assert talk.year == 2025
    assert talk.abstract_title == "Novel Biomarker Discovery"
    assert len(talk.coauthors) == 2
    assert talk.source_url == "https://example.com/abstract/123"


def test_talk_type_named_lectureship() -> None:
    """TalkType correctly flags named lectureships."""
    tt = TalkType(is_named_lectureship=True)
    assert tt.is_named_lectureship is True
    assert tt.is_invited_talk is False
    assert tt.is_oral_presentation is False
    assert tt.is_poster is False


def test_talk_type_invited() -> None:
    """TalkType correctly flags invited talks."""
    tt = TalkType(is_invited_talk=True)
    assert tt.is_invited_talk is True
    assert tt.is_named_lectureship is False


def test_talks_from_extraction() -> None:
    """talks_from_extraction converts raw dicts to TalkRecords."""
    raw = [
        {
            "presenter_name": "Dr. Smith",
            "talk_type": "invited oral",
            "session_title": "Keynote Session",
            "abstract_title": "Cancer Genomics",
            "coauthors": "Alice, Bob",
        },
        {
            "presenter_name": "Dr. Jones",
            "talk_type": "poster",
            "session_title": "Poster Hall",
        },
    ]
    records = talks_from_extraction(raw, "ASCO Annual Meeting", 2025)
    assert len(records) == 2

    r0 = records[0]
    assert r0.presenter_name == "Dr. Smith"
    assert r0.talk_type.is_invited_talk is True
    assert r0.talk_type.is_oral_presentation is True
    assert r0.conference_name == "ASCO Annual Meeting"
    assert r0.year == 2025
    assert r0.coauthors == ["Alice", "Bob"]

    r1 = records[1]
    assert r1.talk_type.is_poster is True
    assert r1.talk_type.is_invited_talk is False
    assert r1.coauthors == []


def test_asco_ingestor_interface() -> None:
    """AscoIngestor implements ConferenceIngestor correctly."""
    ingestor = AscoIngestor()
    assert isinstance(ingestor, ConferenceIngestor)
    assert ingestor.conference_name == "ASCO Annual Meeting"
    assert ingestor.society_code == "ASCO"
    results = list(ingestor.ingest(2025))
    assert results == []


def test_acs_ingestor_interface() -> None:
    """AcsIngestor implements ConferenceIngestor correctly."""
    ingestor = AcsIngestor()
    assert isinstance(ingestor, ConferenceIngestor)
    assert ingestor.conference_name == "ACS National Meeting"
    assert ingestor.society_code == "ACS"
    results = list(ingestor.ingest(2025))
    assert results == []


def test_aacr_ingestor_interface() -> None:
    """AacrIngestor implements ConferenceIngestor correctly."""
    ingestor = AacrIngestor()
    assert isinstance(ingestor, ConferenceIngestor)
    assert ingestor.conference_name == "AACR Annual Meeting"
    assert ingestor.society_code == "AACR"
    results = list(ingestor.ingest(2025))
    assert results == []


def test_default_llm_extractor_stub() -> None:
    """DefaultLLMExtractor returns empty results."""
    extractor = DefaultLLMExtractor()
    results = extractor.extract_talks(
        "Some raw text", "ASCO Annual Meeting", 2025
    )
    assert results == []
