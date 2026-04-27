"""Composed privacy gate: single entry point for all data entering Aegis.

Chains three runtime checks:
1. PHI/HIPAA scanner -- rejects data containing protected health information
2. Demographic blocklist -- strips prohibited demographic fields
3. Opt-out enforcement -- excludes opted-out candidates from results

Bypassing ANY check is an alertable event. The gate logs all decisions
for auditability.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from aegis.privacy.demographic_blocklist import BlocklistResult, DemographicBlocklist
from aegis.privacy.opt_out import OptOutStore
from aegis.privacy.phi_scanner import PHIScanner, ScanResult

logger = logging.getLogger(__name__)


class GateDecision(StrEnum):
    """Possible gate decisions."""

    allowed = "allowed"
    rejected_phi = "rejected_phi"
    stripped = "stripped"
    excluded_opt_out = "excluded_opt_out"


class GateResult(BaseModel):
    """Result of running data through the privacy gate."""

    model_config = ConfigDict(frozen=True)

    decision: GateDecision
    candidate_uuid: str | None
    phi_scan: ScanResult | None
    blocklist_result: BlocklistResult | None
    opted_out: bool
    cleaned_data: dict[str, str] | None
    timestamp: datetime
    alerts: list[str]


class GateStats(BaseModel):
    """Aggregate gate statistics."""

    model_config = ConfigDict(frozen=True)

    total_checked: int
    total_allowed: int
    total_rejected_phi: int
    total_stripped: int
    total_excluded_opt_out: int
    bypass_alerts: int


class PrivacyGate:
    """Composed privacy gate for data entering Aegis.

    All data must pass through this gate before entering the scoring
    pipeline. The gate is fail-closed: any error in the checks
    results in rejection rather than silent admission.
    """

    def __init__(
        self,
        *,
        phi_scanner: PHIScanner,
        blocklist: DemographicBlocklist,
        opt_out_store: OptOutStore,
        alert_callback: Any | None = None,
    ) -> None:
        self._phi = phi_scanner
        self._blocklist = blocklist
        self._opt_out = opt_out_store
        self._alert_callback = alert_callback
        self._total_checked = 0
        self._total_allowed = 0
        self._total_rejected_phi = 0
        self._total_stripped = 0
        self._total_excluded_opt_out = 0
        self._bypass_alerts = 0

    def check(
        self,
        *,
        data: dict[str, str],
        candidate_uuid: str | None = None,
    ) -> GateResult:
        """Run data through all privacy checks.

        Order: PHI scan -> demographic strip -> opt-out check.
        Fail-closed: errors result in rejection.
        """
        alerts: list[str] = []
        self._total_checked += 1

        # Step 1: PHI scan (fail-closed on error)
        try:
            phi_result = self._phi.scan(data)
        except Exception as exc:
            logger.error("PHI scanner error (fail-closed): %s", exc)
            alerts.append(f"PHI scanner error: {exc}")
            self._total_rejected_phi += 1
            return GateResult(
                decision=GateDecision.rejected_phi,
                candidate_uuid=candidate_uuid,
                phi_scan=None,
                blocklist_result=None,
                opted_out=False,
                cleaned_data=None,
                timestamp=datetime.now(tz=UTC),
                alerts=alerts,
            )

        if phi_result.contains_phi:
            alerts.append("PHI detected in data")
            self._total_rejected_phi += 1
            return GateResult(
                decision=GateDecision.rejected_phi,
                candidate_uuid=candidate_uuid,
                phi_scan=phi_result,
                blocklist_result=None,
                opted_out=False,
                cleaned_data=None,
                timestamp=datetime.now(tz=UTC),
                alerts=alerts,
            )

        # Step 2: Demographic blocklist strip
        bl_result = self._blocklist.strip(data)
        fields_stripped = bl_result.stripped_field_count > 0

        # Step 3: Opt-out check
        opted_out = False
        if candidate_uuid is not None:
            opted_out = self._opt_out.is_opted_out(candidate_uuid)

        if opted_out:
            self._total_excluded_opt_out += 1
            return GateResult(
                decision=GateDecision.excluded_opt_out,
                candidate_uuid=candidate_uuid,
                phi_scan=phi_result,
                blocklist_result=bl_result,
                opted_out=True,
                cleaned_data=None,
                timestamp=datetime.now(tz=UTC),
                alerts=alerts,
            )

        if fields_stripped:
            self._total_stripped += 1
            decision = GateDecision.stripped
        else:
            self._total_allowed += 1
            decision = GateDecision.allowed

        return GateResult(
            decision=decision,
            candidate_uuid=candidate_uuid,
            phi_scan=phi_result,
            blocklist_result=bl_result,
            opted_out=False,
            cleaned_data=bl_result.cleaned_data,
            timestamp=datetime.now(tz=UTC),
            alerts=alerts,
        )

    def check_bypass_alert(self, *, reason: str) -> None:
        """Alert when a privacy gate bypass is detected."""
        self._bypass_alerts += 1
        logger.error("PRIVACY GATE BYPASS: %s", reason)
        if self._alert_callback:
            self._alert_callback(reason)

    def get_stats(self) -> GateStats:
        """Return current gate statistics."""
        return GateStats(
            total_checked=self._total_checked,
            total_allowed=self._total_allowed,
            total_rejected_phi=self._total_rejected_phi,
            total_stripped=self._total_stripped,
            total_excluded_opt_out=self._total_excluded_opt_out,
            bypass_alerts=self._bypass_alerts,
        )
