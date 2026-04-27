"""Tests for the composed privacy gate."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aegis.privacy.demographic_blocklist import DemographicBlocklist
from aegis.privacy.gate import GateDecision, GateResult, PrivacyGate
from aegis.privacy.opt_out import OptOutStore
from aegis.privacy.phi_scanner import PHIScanner


def _make_gate(tmp_path: Path, **kwargs: object) -> PrivacyGate:
    scanner = PHIScanner()
    blocklist = DemographicBlocklist()
    opt_out_store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    return PrivacyGate(
        phi_scanner=scanner,
        blocklist=blocklist,
        opt_out_store=opt_out_store,
        **kwargs,
    )


def test_clean_data_allowed(tmp_path: Path) -> None:
    gate = _make_gate(tmp_path)
    result = gate.check(data={"name": "Jane", "affiliation": "MIT"})
    assert result.decision == GateDecision.allowed


def test_phi_rejected(tmp_path: Path) -> None:
    gate = _make_gate(tmp_path)
    result = gate.check(data={"ssn_field": "123-45-6789"})
    assert result.decision == GateDecision.rejected_phi
    assert result.cleaned_data is None


def test_demographic_stripped(tmp_path: Path) -> None:
    gate = _make_gate(tmp_path)
    result = gate.check(data={"name": "Jane", "gender": "F"})
    assert result.decision == GateDecision.stripped
    assert result.cleaned_data is not None
    assert "gender" not in result.cleaned_data


def test_opted_out_excluded(tmp_path: Path) -> None:
    opt_out_store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    opt_out_store.opt_out(candidate_uuid="cand-1", verified_via="orcid")
    gate = PrivacyGate(
        phi_scanner=PHIScanner(),
        blocklist=DemographicBlocklist(),
        opt_out_store=opt_out_store,
    )
    result = gate.check(data={"name": "Jane"}, candidate_uuid="cand-1")
    assert result.decision == GateDecision.excluded_opt_out


def test_phi_takes_priority(tmp_path: Path) -> None:
    gate = _make_gate(tmp_path)
    result = gate.check(data={"ssn_field": "123-45-6789", "gender": "F"})
    assert result.decision == GateDecision.rejected_phi


def test_strip_then_allow(tmp_path: Path) -> None:
    gate = _make_gate(tmp_path)
    result = gate.check(data={"name": "Jane", "gender": "F", "affiliation": "MIT"})
    assert result.decision == GateDecision.stripped
    assert result.cleaned_data is not None
    assert "name" in result.cleaned_data
    assert "affiliation" in result.cleaned_data
    assert "gender" not in result.cleaned_data


def test_bypass_alert(tmp_path: Path) -> None:
    callback = MagicMock()
    gate = _make_gate(tmp_path, alert_callback=callback)
    gate.check_bypass_alert(reason="Data entered without gate")
    stats = gate.get_stats()
    assert stats.bypass_alerts == 1
    callback.assert_called_once_with("Data entered without gate")


def test_stats(tmp_path: Path) -> None:
    gate = _make_gate(tmp_path)
    # 1 clean
    gate.check(data={"name": "Jane"})
    # 1 PHI
    gate.check(data={"ssn_field": "123-45-6789"})
    # 1 demographic
    gate.check(data={"name": "Bob", "gender": "M"})
    # 1 opt-out
    opt_out_store = OptOutStore(storage_path=tmp_path / "opt_out.jsonl")
    opt_out_store.opt_out(candidate_uuid="cand-x", verified_via="admin")
    gate2 = PrivacyGate(
        phi_scanner=PHIScanner(),
        blocklist=DemographicBlocklist(),
        opt_out_store=opt_out_store,
    )
    gate2.check(data={"name": "Opted"}, candidate_uuid="cand-x")
    stats2 = gate2.get_stats()
    assert stats2.total_excluded_opt_out == 1

    stats = gate.get_stats()
    assert stats.total_checked == 3
    assert stats.total_allowed == 1
    assert stats.total_rejected_phi == 1
    assert stats.total_stripped == 1


def test_gate_result_model() -> None:
    result = GateResult(
        decision=GateDecision.allowed,
        candidate_uuid=None,
        phi_scan=None,
        blocklist_result=None,
        opted_out=False,
        cleaned_data={"name": "Jane"},
        timestamp=datetime.now(tz=UTC),
        alerts=[],
    )
    with pytest.raises(Exception):  # noqa: B017
        result.decision = GateDecision.rejected_phi


def test_fail_closed_on_error(tmp_path: Path) -> None:
    scanner = MagicMock(spec=PHIScanner)
    scanner.scan.side_effect = RuntimeError("Scanner crashed")
    gate = PrivacyGate(
        phi_scanner=scanner,
        blocklist=DemographicBlocklist(),
        opt_out_store=OptOutStore(storage_path=tmp_path / "opt_out.jsonl"),
    )
    result = gate.check(data={"name": "Jane"})
    assert result.decision == GateDecision.rejected_phi
    assert len(result.alerts) > 0
