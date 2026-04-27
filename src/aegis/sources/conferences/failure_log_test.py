"""Tests for conference abstract parsing failure logger."""

from __future__ import annotations

from aegis.sources.conferences.failure_log import (
    ConferenceFailureLog,
    ParseFailure,
)


class TestConferenceFailureLog:
    """Tests for ConferenceFailureLog."""

    def test_log_failure(self) -> None:
        """Logging a failure creates a ParseFailure entry."""
        log = ConferenceFailureLog()
        failure = log.log_failure(
            conference="ASCO",
            year=2024,
            source_url="https://example.com/abstract/123",
            error_type="parse_error",
            error_message="Malformed HTML in abstract body",
        )

        assert isinstance(failure, ParseFailure)
        assert failure.conference == "ASCO"
        assert failure.year == 2024
        assert failure.error_type == "parse_error"
        assert len(log.get_all_failures()) == 1

    def test_failure_stats(self) -> None:
        """3 failures of 10 attempts -> rate = 0.3."""
        log = ConferenceFailureLog()
        for _ in range(10):
            log.record_attempt("ASCO")
        for i in range(3):
            log.log_failure(
                conference="ASCO",
                year=2024,
                source_url=None,
                error_type="timeout",
                error_message=f"Request timed out {i}",
            )

        stats = log.get_stats("ASCO")
        assert stats.total_attempted == 10
        assert stats.total_failed == 3
        assert abs(stats.failure_rate - 0.3) < 1e-9

    def test_most_common_error(self) -> None:
        """Most common error type is reported correctly."""
        log = ConferenceFailureLog()
        for _ in range(5):
            log.record_attempt("AACR")
        log.log_failure("AACR", 2024, None, "timeout", "timed out")
        log.log_failure("AACR", 2024, None, "timeout", "timed out again")
        log.log_failure("AACR", 2024, None, "parse_error", "bad html")

        stats = log.get_stats("AACR")
        assert stats.most_common_error == "timeout"

    def test_pipeline_continues(self) -> None:
        """Logging a failure does NOT raise — pipeline continues."""
        log = ConferenceFailureLog()
        # This should not raise
        failure = log.log_failure(
            conference="ACS",
            year=2024,
            source_url=None,
            error_type="connection_error",
            error_message="Connection refused",
        )
        assert failure is not None
        # Pipeline continues: we can still record attempts and log more
        log.record_attempt("ACS")
        assert log.get_stats("ACS").total_attempted == 1

    def test_failure_model(self) -> None:
        """ParseFailure model fields are correctly populated."""
        log = ConferenceFailureLog()
        failure = log.log_failure(
            conference="ASCO",
            year=2025,
            source_url="https://example.com/abs/456",
            error_type="validation_error",
            error_message="Missing author field",
        )

        assert failure.failure_id  # non-empty uuid
        assert failure.conference == "ASCO"
        assert failure.year == 2025
        assert failure.source_url == "https://example.com/abs/456"
        assert failure.error_type == "validation_error"
        assert failure.timestamp is not None
