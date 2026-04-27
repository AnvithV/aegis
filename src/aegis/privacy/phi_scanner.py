"""PHI/HIPAA scanner for data entering Aegis.

Detects protected health information using:
1. Regex pattern matching for structured PHI (SSN, DOB, MRN, phone, address)
2. LLM classifier for unstructured text fields (abstracts, notes)

Design principle: false-positives preferred over false-negatives.
Any PHI detection REJECTS the data and triggers an alert.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class PHIType(StrEnum):
    """Types of protected health information detected."""

    ssn = "ssn"
    date_of_birth = "date_of_birth"
    medical_record_number = "medical_record_number"
    phone_number = "phone_number"
    street_address = "street_address"
    email_address = "email_address"
    patient_name_context = "patient_name_context"
    unstructured_phi = "unstructured_phi"


class PHIDetection(BaseModel):
    """A single PHI detection result."""

    model_config = ConfigDict(frozen=True)

    phi_type: PHIType
    field_name: str
    matched_text: str
    confidence: float
    pattern_name: str | None


class ScanResult(BaseModel):
    """Result of scanning a data record for PHI."""

    model_config = ConfigDict(frozen=True)

    contains_phi: bool
    detections: list[PHIDetection]
    fields_scanned: int
    scanned_at: datetime
    alert_triggered: bool


class ScannerStats(BaseModel):
    """Aggregate scanner statistics."""

    model_config = ConfigDict(frozen=True)

    total_scans: int
    total_phi_detected: int
    total_fields_scanned: int
    detection_rate: float
    by_type: dict[str, int]


_PHI_PATTERNS: dict[str, tuple[str, PHIType]] = {
    "ssn_dashed": (r"\b\d{3}-\d{2}-\d{4}\b", PHIType.ssn),
    "ssn_nodash": (r"\b\d{9}\b", PHIType.ssn),
    "dob_mmddyyyy": (
        r"\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b",
        PHIType.date_of_birth,
    ),
    "dob_iso": (
        r"\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b",
        PHIType.date_of_birth,
    ),
    "mrn_pattern": (r"\bMRN[\s:#-]*\d{5,12}\b", PHIType.medical_record_number),
    "phone_us": (
        r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        PHIType.phone_number,
    ),
    "email": (
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        PHIType.email_address,
    ),
    "street_address": (
        r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s+){1,3}"
        r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Lane|Ln|Way|Court|Ct)\b",
        PHIType.street_address,
    ),
}

_SENSITIVE_FIELD_NAMES: set[str] = {
    "birth",
    "dob",
    "patient",
    "personal",
    "demographic",
    "ssn",
    "mrn",
}

_SSN_NODASH_FIELD_NAMES: set[str] = {"ssn", "social", "tax", "identifier"}
_SSN_NODASH_CONTEXT_TERMS: list[str] = ["ssn", "social security", "tax id"]


class LLMPHIClassifier:
    """LLM-based PHI classifier for unstructured text.

    Uses an LLM to detect PHI in free-text fields like abstracts,
    notes, and descriptions. Stub implementation for initial build;
    production uses Anthropic tool-use classification.
    """

    def __init__(self) -> None:
        self._enabled = False  # Disabled by default; enable in production

    def classify(self, text: str, field_name: str) -> list[PHIDetection]:
        """Classify unstructured text for PHI content.

        Stub: returns empty list. Production implementation would:
        1. Call Anthropic API with tool-use for structured PHI detection
        2. Parse tool response for PHI categories
        3. Return PHIDetection list with confidence scores

        When enabled, scans for:
        - Patient names in clinical context
        - Medical record references
        - Treatment/diagnosis details tied to identifiable individuals
        - Any other HIPAA-defined PHI categories
        """
        if not self._enabled:
            return []

        # Production implementation placeholder:
        # client = Anthropic()
        # response = client.messages.create(
        #     model="claude-sonnet-4-20250514",
        #     tools=[_phi_detection_tool_schema()],
        #     ...
        # )
        return []  # pragma: no cover

    def enable(self) -> None:
        """Enable LLM classification (requires API key)."""
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        return self._enabled


class PHIScanner:
    """Scan data fields for PHI/HIPAA-sensitive content.

    Combines regex pattern matching for structured PHI with LLM
    classification for unstructured text. Rejects data containing
    PHI and triggers alerts.
    """

    def __init__(
        self,
        *,
        llm_classifier: LLMPHIClassifier | None = None,
        alert_callback: Any | None = None,
    ) -> None:
        self._llm = llm_classifier or LLMPHIClassifier()
        self._alert_callback = alert_callback  # Callable[[ScanResult], None]
        self._compiled_patterns: dict[str, tuple[re.Pattern[str], PHIType]] = {
            name: (re.compile(pattern, re.IGNORECASE), phi_type)
            for name, (pattern, phi_type) in _PHI_PATTERNS.items()
        }
        self._total_scans = 0
        self._total_phi = 0
        self._total_fields = 0
        self._by_type: dict[str, int] = {}

    def _redact(self, text: str) -> str:
        """Redact text for logging: first 3 chars + '***'."""
        if len(text) < 3:
            return "***"
        return text[:3] + "***"

    def _check_field(self, field_name: str, value: str) -> list[PHIDetection]:
        """Run regex patterns against a single field value."""
        detections: list[PHIDetection] = []
        field_lower = field_name.lower()

        for pattern_name, (compiled, phi_type) in self._compiled_patterns.items():
            # Date patterns: only flag in sensitive-named fields
            if pattern_name in ("dob_iso", "dob_mmddyyyy"):
                if not any(s in field_lower for s in _SENSITIVE_FIELD_NAMES):
                    continue

            matches = list(compiled.finditer(value))
            if not matches:
                continue

            # SSN no-dash: context filtering
            if pattern_name == "ssn_nodash":
                has_field_context = any(
                    s in field_lower for s in _SSN_NODASH_FIELD_NAMES
                )
                if not has_field_context:
                    # Check surrounding text for SSN context
                    context_found = False
                    for match in matches:
                        start = max(0, match.start() - 20)
                        end = min(len(value), match.end() + 20)
                        surrounding = value[start:end].lower()
                        has_context = any(
                            term in surrounding
                            for term in _SSN_NODASH_CONTEXT_TERMS
                        )
                        if has_context:
                            context_found = True
                            break
                    if not context_found:
                        continue

            for match in matches:
                detections.append(
                    PHIDetection(
                        phi_type=phi_type,
                        field_name=field_name,
                        matched_text=self._redact(match.group()),
                        confidence=1.0,
                        pattern_name=pattern_name,
                    )
                )

        return detections

    def _check_unstructured(self, field_name: str, value: str) -> list[PHIDetection]:
        """Check unstructured text via LLM classifier."""
        if len(value) > 50:
            return self._llm.classify(value, field_name)
        return []

    def scan(self, data: dict[str, str]) -> ScanResult:
        """Scan a data record for PHI across all fields."""
        all_detections: list[PHIDetection] = []

        for field_name, value in data.items():
            all_detections.extend(self._check_field(field_name, value))
            all_detections.extend(self._check_unstructured(field_name, value))

        contains_phi = len(all_detections) > 0
        alert_triggered = contains_phi

        result = ScanResult(
            contains_phi=contains_phi,
            detections=all_detections,
            fields_scanned=len(data),
            scanned_at=datetime.now(tz=UTC),
            alert_triggered=alert_triggered,
        )

        if alert_triggered and self._alert_callback:
            self._alert_callback(result)

        # Update stats
        self._total_scans += 1
        self._total_fields += len(data)
        if contains_phi:
            self._total_phi += 1
        for det in all_detections:
            key = det.phi_type.value
            self._by_type[key] = self._by_type.get(key, 0) + 1

        return result

    def scan_single(self, field_name: str, value: str) -> list[PHIDetection]:
        """Scan a single field for PHI. Returns list of detections."""
        detections = self._check_field(field_name, value)
        detections.extend(self._check_unstructured(field_name, value))
        return detections

    def get_stats(self) -> ScannerStats:
        """Return current scanner statistics."""
        return ScannerStats(
            total_scans=self._total_scans,
            total_phi_detected=self._total_phi,
            total_fields_scanned=self._total_fields,
            detection_rate=(
                self._total_phi / self._total_scans if self._total_scans > 0 else 0.0
            ),
            by_type=dict(self._by_type),
        )
