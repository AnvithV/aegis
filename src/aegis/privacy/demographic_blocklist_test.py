"""Tests for demographic feature blocklist."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from aegis.privacy.demographic_blocklist import (
    BlocklistResult,
    DemographicBlocklist,
)


def test_block_gender() -> None:
    bl = DemographicBlocklist()
    assert bl.is_blocked("gender") is True
    assert bl.is_blocked("Gender") is True


def test_block_race() -> None:
    bl = DemographicBlocklist()
    assert bl.is_blocked("race") is True
    assert bl.is_blocked("ethnicity") is True


def test_block_citizenship() -> None:
    bl = DemographicBlocklist()
    assert bl.is_blocked("citizenship_status") is True


def test_block_age_exact() -> None:
    bl = DemographicBlocklist()
    assert bl.is_blocked("age") is True


def test_allow_dosage() -> None:
    bl = DemographicBlocklist()
    assert bl.is_blocked("dosage") is False


def test_allow_coverage() -> None:
    bl = DemographicBlocklist()
    assert bl.is_blocked("coverage") is False


def test_allow_lineage() -> None:
    bl = DemographicBlocklist()
    assert bl.is_blocked("lineage") is False


def test_strip_removes_blocked_fields() -> None:
    bl = DemographicBlocklist()
    result = bl.strip(
        {
            "name": "Jane",
            "gender": "F",
            "affiliation": "Harvard",
            "race": "Asian",
        }
    )
    assert "name" in result.cleaned_data
    assert "affiliation" in result.cleaned_data
    assert "gender" not in result.cleaned_data
    assert "race" not in result.cleaned_data
    assert "gender" in result.stripped_fields
    assert "race" in result.stripped_fields


def test_strip_preserves_clean_data() -> None:
    bl = DemographicBlocklist()
    result = bl.strip({"name": "Jane", "pmid": "12345", "affiliation": "MIT"})
    assert result.stripped_field_count == 0
    assert len(result.cleaned_data) == 3


def test_strip_case_insensitive() -> None:
    bl = DemographicBlocklist()
    result = bl.strip({"Gender": "M", "RACE": "White"})
    assert result.stripped_field_count == 2
    assert len(result.cleaned_data) == 0


def test_extra_blocked_fields() -> None:
    bl = DemographicBlocklist(extra_blocked=frozenset({"religion"}))
    assert bl.is_blocked("religion") is True


def test_alert_callback_on_strip() -> None:
    callback = MagicMock()
    bl = DemographicBlocklist(alert_callback=callback)
    bl.strip({"gender": "F", "name": "Jane"})
    callback.assert_called_once()
    call_arg = callback.call_args[0][0]
    assert "gender" in call_arg


def test_stats_tracking() -> None:
    bl = DemographicBlocklist()
    bl.strip({"gender": "F", "name": "Jane"})
    bl.strip({"race": "Asian", "pmid": "123"})
    bl.strip({"name": "Bob", "affiliation": "MIT"})
    stats = bl.get_stats()
    assert stats.total_records_processed == 3
    assert stats.total_fields_stripped == 2


def test_blocklist_result_model() -> None:
    result = BlocklistResult(
        original_field_count=3,
        stripped_field_count=1,
        stripped_fields=["gender"],
        remaining_fields=["name", "pmid"],
        cleaned_data={"name": "Jane", "pmid": "123"},
        timestamp=datetime.now(tz=UTC),
    )
    with pytest.raises(Exception):  # noqa: B017
        result.original_field_count = 5
