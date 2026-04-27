"""Tests for PHI/HIPAA scanner."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aegis.privacy.phi_scanner import (
    LLMPHIClassifier,
    PHIScanner,
    PHIType,
    ScanResult,
)


def test_detect_ssn_dashed() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"ssn_field": "123-45-6789"})
    assert result.contains_phi is True
    assert len(result.detections) >= 1
    assert result.detections[0].phi_type == PHIType.ssn


def test_detect_ssn_no_context_ignored() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"notes": "123456789"})
    assert result.contains_phi is False


def test_detect_ssn_in_ssn_field() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"ssn_number": "123456789"})
    assert result.contains_phi is True
    assert any(d.phi_type == PHIType.ssn for d in result.detections)


def test_detect_phone() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"contact": "(555) 123-4567"})
    assert result.contains_phi is True
    assert any(d.phi_type == PHIType.phone_number for d in result.detections)


def test_detect_email() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"email_field": "patient@hospital.com"})
    assert result.contains_phi is True
    assert any(d.phi_type == PHIType.email_address for d in result.detections)


def test_detect_mrn() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"record": "MRN: 12345678"})
    assert result.contains_phi is True
    assert any(d.phi_type == PHIType.medical_record_number for d in result.detections)


def test_date_in_publication_field_not_flagged() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"publication_date": "2024-01-15"})
    assert result.contains_phi is False


def test_date_in_dob_field_flagged() -> None:
    scanner = PHIScanner()
    result = scanner.scan({"date_of_birth": "01/15/1990"})
    assert result.contains_phi is True
    assert any(d.phi_type == PHIType.date_of_birth for d in result.detections)


def test_clean_data_no_phi() -> None:
    scanner = PHIScanner()
    result = scanner.scan(
        {
            "name": "Jane Smith",
            "affiliation": "Harvard Medical School",
            "pmid": "12345678",
        }
    )
    assert result.contains_phi is False
    assert len(result.detections) == 0


def test_multiple_phi_in_one_record() -> None:
    scanner = PHIScanner()
    result = scanner.scan(
        {
            "ssn_field": "123-45-6789",
            "contact": "(555) 123-4567",
            "email_field": "patient@hospital.com",
        }
    )
    assert len(result.detections) == 3


def test_redact_long_text() -> None:
    scanner = PHIScanner()
    assert scanner._redact("123-45-6789") == "123***"


def test_redact_short_text() -> None:
    scanner = PHIScanner()
    assert scanner._redact("ab") == "***"


def test_alert_callback_called() -> None:
    callback = MagicMock()
    scanner = PHIScanner(alert_callback=callback)
    scanner.scan({"ssn_field": "123-45-6789"})
    callback.assert_called_once()
    call_arg = callback.call_args[0][0]
    assert isinstance(call_arg, ScanResult)


def test_stats_tracking() -> None:
    scanner = PHIScanner()
    scanner.scan({"ssn_field": "123-45-6789"})
    scanner.scan({"contact": "(555) 123-4567"})
    scanner.scan({"name": "Jane Smith", "affiliation": "MIT"})
    stats = scanner.get_stats()
    assert stats.total_scans == 3
    assert stats.total_phi_detected == 2


def test_llm_classifier_disabled_by_default() -> None:
    classifier = LLMPHIClassifier()
    assert classifier.is_enabled is False
    result = classifier.classify("Some text with patient info", "notes")
    assert result == []


def test_scan_result_model() -> None:
    from datetime import UTC, datetime

    result = ScanResult(
        contains_phi=False,
        detections=[],
        fields_scanned=1,
        scanned_at=datetime.now(tz=UTC),
        alert_triggered=False,
    )
    with pytest.raises(Exception):  # noqa: B017
        result.contains_phi = True
