"""Stale-data circuit breaker for integrity source freshness.

When a hard-gate integrity source has lagged beyond its SLA, the circuit
breaker opens and adds a 'stale integrity data' caveat to API responses.
Caveats are INFORMATIONAL -- they never block responses. Better to disclose
than silently serve potentially-wrong rankings.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from aegis.api.schemas import StalenessWarning

logger = logging.getLogger(__name__)

# Per-source SLA thresholds in seconds (hard-gate sources have tighter SLAs)
_INTEGRITY_SOURCE_SLAS: dict[str, float] = {
    "retraction_watch": 6 * 3600,  # 6 hours
    "ori": 24 * 3600,  # 24 hours
    "ofac_sam": 6 * 3600,  # 6 hours
    "leie": 24 * 3600,  # 24 hours
    "state_medical_boards": 48 * 3600,  # 48 hours
}


class StalenessCircuitBreaker:
    """Circuit breaker that detects stale integrity sources and emits caveats."""

    def __init__(
        self, *, sla_overrides: dict[str, float] | None = None
    ) -> None:
        self._slas = dict(_INTEGRITY_SOURCE_SLAS)
        if sla_overrides:
            self._slas.update(sla_overrides)
        self._last_refresh: dict[str, float] = {}
        self._open_circuits: set[str] = set()

    def record_refresh(self, source: str) -> None:
        """Record a successful refresh for a source, closing its circuit."""
        self._last_refresh[source] = time.time()
        self._open_circuits.discard(source)

    def check_all(self) -> list[StalenessWarning]:
        """Check all sources for staleness. Returns warnings for stale sources."""
        warnings: list[StalenessWarning] = []
        now = time.time()

        for source, sla_seconds in self._slas.items():
            if source not in self._last_refresh:
                # No refresh ever recorded
                self._open_circuits.add(source)
                warnings.append(
                    StalenessWarning(
                        source=source,
                        last_updated=datetime.fromtimestamp(0, tz=UTC),
                        sla_hours=sla_seconds / 3600,
                        message=f"No refresh recorded for {source}",
                    )
                )
            elif (now - self._last_refresh[source]) > sla_seconds:
                self._open_circuits.add(source)
                last = self._last_refresh[source]
                warnings.append(
                    StalenessWarning(
                        source=source,
                        last_updated=datetime.fromtimestamp(last, tz=UTC),
                        sla_hours=sla_seconds / 3600,
                        message=(
                            f"{source} data is stale: "
                            f"last refreshed "
                            f"{round((now - last) / 3600, 1)}h "
                            f"ago, SLA is {sla_seconds / 3600}h"
                        ),
                    )
                )
            else:
                self._open_circuits.discard(source)

        return warnings

    def is_stale(self, source: str) -> bool:
        """Return True if a source is currently stale."""
        self.check_all()
        return source in self._open_circuits

    def get_open_circuits(self) -> set[str]:
        """Return set of source names with open (stale) circuits."""
        self.check_all()
        return set(self._open_circuits)
