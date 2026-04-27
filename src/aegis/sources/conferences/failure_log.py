"""Conference abstract parsing failure logger.

Logs parsing failures without blocking the pipeline and tracks
per-conference failure rates for observability.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ParseFailure(BaseModel):
    """A single conference parsing failure."""

    model_config = ConfigDict(frozen=True)

    failure_id: str
    conference: str
    year: int
    source_url: str | None
    error_type: str
    error_message: str
    timestamp: datetime


class ConferenceFailureStats(BaseModel):
    """Aggregate failure statistics for a conference."""

    model_config = ConfigDict(frozen=True)

    conference: str
    total_attempted: int
    total_failed: int
    failure_rate: float
    most_common_error: str | None


class ConferenceFailureLog:
    """Track conference parsing failures without blocking the pipeline."""

    def __init__(self) -> None:
        self._failures: list[ParseFailure] = []
        self._attempt_counts: Counter[str] = Counter()

    def log_failure(
        self,
        conference: str,
        year: int,
        source_url: str | None,
        error_type: str,
        error_message: str,
    ) -> ParseFailure:
        """Log a parsing failure. Does NOT raise."""
        failure = ParseFailure(
            failure_id=str(uuid.uuid4()),
            conference=conference,
            year=year,
            source_url=source_url,
            error_type=error_type,
            error_message=error_message,
            timestamp=datetime.now(UTC),
        )
        self._failures.append(failure)
        logger.warning(
            "Parse failure [%s %d]: %s — %s",
            conference,
            year,
            error_type,
            error_message,
        )
        return failure

    def record_attempt(self, conference: str) -> None:
        """Record a parsing attempt for a conference."""
        self._attempt_counts[conference] += 1

    def get_stats(self, conference: str) -> ConferenceFailureStats:
        """Get failure statistics for a specific conference."""
        conf_failures = [
            f for f in self._failures if f.conference == conference
        ]
        total_attempted = self._attempt_counts.get(conference, 0)
        total_failed = len(conf_failures)
        failure_rate = total_failed / max(total_attempted, 1)

        # Most common error type
        error_types = [f.error_type for f in conf_failures]
        most_common: str | None = None
        if error_types:
            counter: Counter[str] = Counter(error_types)
            most_common = counter.most_common(1)[0][0]

        return ConferenceFailureStats(
            conference=conference,
            total_attempted=total_attempted,
            total_failed=total_failed,
            failure_rate=failure_rate,
            most_common_error=most_common,
        )

    def get_all_failures(self) -> list[ParseFailure]:
        """Return all recorded failures."""
        return list(self._failures)
