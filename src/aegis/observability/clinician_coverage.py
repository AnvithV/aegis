"""Clinician coverage diagnostics for multi-population observability."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

COVERED_STATES = frozenset(
    {"CA", "NY", "TX", "FL", "IL", "PA", "OH", "NC", "GA", "MI"}
)


class ClinicianCoverageMetrics(BaseModel):
    """Frozen snapshot of clinician data coverage statistics."""

    model_config = ConfigDict(frozen=True)

    total_clinicians: int
    npi_crosslinked_pct: float
    abms_coverage_pct: float
    state_board_coverage_pct: float
    hospital_tier_pct: float
    publication_pct: float
    covered_states: list[str]
    gap_states: list[str]
    coverage_caveats: list[str]


class ClinicianCoverageDashboard:
    """Compute clinician coverage metrics from enriched clinician records."""

    def compute(
        self, clinicians: list[dict[str, bool | str | None]]
    ) -> ClinicianCoverageMetrics:
        """Compute coverage metrics for a list of clinician records.

        Each clinician dict has keys: has_candidate_uuid, has_abms,
        has_state_board, has_hospital_tier, has_publications, practice_state.
        """
        total = len(clinicians)
        if total == 0:
            return ClinicianCoverageMetrics(
                total_clinicians=0,
                npi_crosslinked_pct=0.0,
                abms_coverage_pct=0.0,
                state_board_coverage_pct=0.0,
                hospital_tier_pct=0.0,
                publication_pct=0.0,
                covered_states=[],
                gap_states=[],
                coverage_caveats=[],
            )

        npi_count = sum(1 for c in clinicians if c.get("has_candidate_uuid"))
        abms_count = sum(1 for c in clinicians if c.get("has_abms"))
        state_board_count = sum(
            1 for c in clinicians if c.get("has_state_board")
        )
        hospital_tier_count = sum(
            1 for c in clinicians if c.get("has_hospital_tier")
        )
        pub_count = sum(1 for c in clinicians if c.get("has_publications"))

        # Collect unique states
        observed_states: set[str] = set()
        for c in clinicians:
            state = c.get("practice_state")
            if isinstance(state, str) and state:
                observed_states.add(state)

        covered = sorted(observed_states & COVERED_STATES)
        gap = sorted(observed_states - COVERED_STATES)

        npi_pct = round(100.0 * npi_count / total, 2)
        abms_pct = round(100.0 * abms_count / total, 2)
        state_board_pct = round(100.0 * state_board_count / total, 2)
        hospital_tier_pct = round(100.0 * hospital_tier_count / total, 2)
        pub_pct = round(100.0 * pub_count / total, 2)

        caveats: list[str] = []
        if pub_pct < 30.0:
            caveats.append(
                f"Low publication rate: {pub_pct}% (below 30% threshold)"
            )
        if abms_pct < 50.0:
            caveats.append(
                f"Low board certification coverage: {abms_pct}% (below 50% threshold)"
            )

        logger.info(
            "Clinician coverage: %d total, %d gap states, %d caveats",
            total,
            len(gap),
            len(caveats),
        )

        return ClinicianCoverageMetrics(
            total_clinicians=total,
            npi_crosslinked_pct=npi_pct,
            abms_coverage_pct=abms_pct,
            state_board_coverage_pct=state_board_pct,
            hospital_tier_pct=hospital_tier_pct,
            publication_pct=pub_pct,
            covered_states=covered,
            gap_states=gap,
            coverage_caveats=caveats,
        )
