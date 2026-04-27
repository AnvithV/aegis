"""Base types and ABC for conference proceedings ingestion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict


class TalkType(BaseModel):
    """Classification of a conference presentation type."""

    model_config = ConfigDict(frozen=True)

    is_named_lectureship: bool = False
    is_invited_talk: bool = False
    is_oral_presentation: bool = False
    is_poster: bool = False


class TalkRecord(BaseModel):
    """A single conference talk/presentation record."""

    model_config = ConfigDict(frozen=True)

    presenter_name: str
    talk_type: TalkType
    session_title: str
    conference_name: str
    year: int
    abstract_title: str | None = None
    coauthors: list[str] = []
    source_url: str | None = None


class ConferenceIngestor(ABC):
    """Abstract base class for conference proceedings ingestors."""

    @property
    @abstractmethod
    def conference_name(self) -> str:
        """Full name of the conference."""

    @property
    @abstractmethod
    def society_code(self) -> str:
        """Short code for the society (e.g., ASCO, ACS, AACR)."""

    @abstractmethod
    def ingest(self, year: int) -> Iterator[TalkRecord]:
        """Ingest proceedings for a given year, yielding TalkRecords."""
