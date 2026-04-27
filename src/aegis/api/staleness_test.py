"""Tests for audit log and stale-data circuit breaker."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from aegis.api.audit_log import AuditEntry, AuditLog
from aegis.api.staleness import StalenessCircuitBreaker


def test_no_refresh_all_stale() -> None:
    breaker = StalenessCircuitBreaker()
    warnings = breaker.check_all()
    # All sources should be stale (no refreshes recorded)
    assert len(warnings) > 0
    sources = {w.source for w in warnings}
    assert "retraction_watch" in sources
    assert "ori" in sources


def test_refresh_clears_staleness() -> None:
    breaker = StalenessCircuitBreaker()
    breaker.record_refresh("retraction_watch")
    warnings = breaker.check_all()
    stale_sources = {w.source for w in warnings}
    assert "retraction_watch" not in stale_sources


def test_stale_after_sla() -> None:
    breaker = StalenessCircuitBreaker(
        sla_overrides={"retraction_watch": 0.01}
    )
    breaker.record_refresh("retraction_watch")
    time.sleep(0.02)
    warnings = breaker.check_all()
    stale_sources = {w.source for w in warnings}
    assert "retraction_watch" in stale_sources


def test_warning_format() -> None:
    breaker = StalenessCircuitBreaker()
    warnings = breaker.check_all()
    w = warnings[0]
    assert w.source != ""
    assert w.last_updated is not None
    assert w.sla_hours > 0
    assert w.message != ""


def test_is_stale() -> None:
    breaker = StalenessCircuitBreaker()
    assert breaker.is_stale("retraction_watch") is True
    breaker.record_refresh("retraction_watch")
    assert breaker.is_stale("retraction_watch") is False


def test_open_circuits() -> None:
    breaker = StalenessCircuitBreaker()
    open_circuits = breaker.get_open_circuits()
    assert "retraction_watch" in open_circuits
    assert "ori" in open_circuits

    # Record all refreshes
    all_sources = [
        "retraction_watch", "ori", "ofac_sam",
        "leie", "state_medical_boards",
    ]
    for source in all_sources:
        breaker.record_refresh(source)
    assert breaker.get_open_circuits() == set()


def test_audit_log_append_and_load(tmp_path: Path) -> None:
    log = AuditLog(storage_path=tmp_path / "audit.jsonl")
    now = datetime.now(UTC)
    for i in range(3):
        log.append(
            entry=AuditEntry(
                request_id=f"req-{i}",
                customer_id="cust-1",
                customer_name="Test Corp",
                timestamp=now,
                endpoint="POST /v1/queries",
                query_text="test query",
                expanded_mesh_terms=["Neoplasms"],
                response_candidate_uuids=[f"uuid-{i}"],
                weight_version=1,
                integrity_rule_version="1.0.0",
                latency_ms=50.0,
                status_code=200,
                cohort_filter=None,
            )
        )
    assert len(log.load_all()) == 3


def test_audit_log_by_customer(tmp_path: Path) -> None:
    log = AuditLog(storage_path=tmp_path / "audit.jsonl")
    now = datetime.now(UTC)
    for cid in ["cust-1", "cust-1", "cust-2"]:
        log.append(
            entry=AuditEntry(
                request_id=f"req-{cid}",
                customer_id=cid,
                customer_name=f"Corp {cid}",
                timestamp=now,
                endpoint="POST /v1/queries",
                query_text="test",
                expanded_mesh_terms=[],
                response_candidate_uuids=[],
                weight_version=1,
                integrity_rule_version="1.0.0",
                latency_ms=10.0,
                status_code=200,
                cohort_filter=None,
            )
        )
    assert len(log.load_by_customer("cust-1")) == 2
    assert len(log.load_by_customer("cust-2")) == 1


def test_audit_log_by_request_id(tmp_path: Path) -> None:
    log = AuditLog(storage_path=tmp_path / "audit.jsonl")
    now = datetime.now(UTC)
    log.append(
        entry=AuditEntry(
            request_id="known-req",
            customer_id="cust-1",
            customer_name="Test Corp",
            timestamp=now,
            endpoint="POST /v1/queries",
            query_text="test",
            expanded_mesh_terms=[],
            response_candidate_uuids=[],
            weight_version=1,
            integrity_rule_version="1.0.0",
            latency_ms=10.0,
            status_code=200,
            cohort_filter=None,
        )
    )
    assert log.load_by_request_id("known-req") is not None
    assert log.load_by_request_id("unknown") is None


def test_audit_entry_model() -> None:
    now = datetime.now(UTC)
    entry = AuditEntry(
        request_id="req-1",
        customer_id="cust-1",
        customer_name="Test",
        timestamp=now,
        endpoint="POST /v1/queries",
        query_text="test query",
        expanded_mesh_terms=["Neoplasms"],
        response_candidate_uuids=["uuid-1"],
        weight_version=1,
        integrity_rule_version="1.0.0",
        latency_ms=25.0,
        status_code=200,
        cohort_filter="translational",
    )
    # Verify frozen
    data = entry.model_dump_json()
    assert "req-1" in data
