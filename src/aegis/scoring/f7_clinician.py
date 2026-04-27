"""F7 sub-score: clinician-specific family.

Board cert, license, hospital tier, trials, volumes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# F7 sub-component weights (sum to 1.0 within F7)
_W_BOARD_CERT = 0.30
_W_LICENSE = 0.15
_W_HOSPITAL_TIER = 0.25
_W_TRIAL_PI = 0.15
_W_PROCEDURE_VOLUME = 0.15


class F7Score(BaseModel):
    """Result of F7 computation for a single clinician candidate."""

    model_config = ConfigDict(frozen=True)

    board_certification_score: float    # 0.0-1.0
    license_score: float                # 0.0-1.0 (1.0 = active, clean)
    hospital_tier_score: float           # 0.0-1.0 (tier 1 = 1.0)
    trial_pi_score: float               # 0.0-1.0
    procedure_volume_score: float        # 0.0-1.0
    procedure_volume_confidence: float   # 0.0-1.0 (data coverage)
    percentile: float                    # percentile within clinician cohort [0, 1]
    coverage_caveat: str | None


@dataclass
class ClinicianInput:
    """Raw inputs for F7 scoring."""

    # Board certification
    is_board_certified: bool
    has_moc: bool                   # Maintenance of Certification
    certification_count: int         # Number of board certifications

    # License
    has_active_license: bool
    has_disciplinary_action: bool
    action_severity: str | None     # "revocation", "suspension", etc.

    # Hospital tier
    hospital_tier: int              # 1, 2, 3, or 0 (unranked)
    specialty_rank: int | None      # Specialty-specific rank if applicable

    # Clinical trials
    trial_pi_count: int             # As PI on clinical trials
    trial_phases: list[int]         # Phases of trials (2, 3, etc.)

    # Procedure volume
    total_procedures: int           # From CMS data
    procedure_volume_available: bool  # Whether CMS data exists


class F7Computer:
    """Compute F7 sub-score (clinician-specific family) for candidates."""

    def score_raw(
        self,
        inp: ClinicianInput,
    ) -> tuple[float, float, float, float, float, float, str | None]:
        """Compute raw F7 component scores (before percentile).

        Returns (board_cert, license, hospital_tier, trial_pi,
                 procedure_volume, volume_confidence, coverage_caveat).
        """
        # Board certification score
        board_cert = 0.0
        if inp.is_board_certified:
            board_cert = 0.7
            if inp.has_moc:
                board_cert = 1.0
            # Bonus for multiple certifications
            if inp.certification_count > 1:
                board_cert = min(board_cert + 0.1 * (inp.certification_count - 1), 1.0)

        # License score
        license_score = 0.0
        if inp.has_active_license:
            license_score = 1.0
            if inp.has_disciplinary_action:
                # Severity-dependent penalty (but not gating — gating is integrity-only)
                if inp.action_severity in ("revocation", "suspension"):
                    license_score = 0.1
                elif inp.action_severity in ("restriction", "probation"):
                    license_score = 0.5
                elif inp.action_severity == "public_reprimand":
                    license_score = 0.7

        # Hospital tier score
        tier_map = {1: 1.0, 2: 0.7, 3: 0.4, 0: 0.2}
        hospital_tier = tier_map.get(inp.hospital_tier, 0.2)
        if inp.specialty_rank is not None and inp.specialty_rank <= 5:
            hospital_tier = max(hospital_tier, 0.9)

        # Clinical trial PI score
        trial_pi = 0.0
        if inp.trial_pi_count > 0:
            trial_pi = min(inp.trial_pi_count / 5.0, 1.0)
            # Bonus for Phase 3+ trials
            has_late_phase = any(p >= 3 for p in inp.trial_phases)
            if has_late_phase:
                trial_pi = min(trial_pi + 0.2, 1.0)

        # Procedure volume score
        volume_confidence = 1.0 if inp.procedure_volume_available else 0.3
        procedure_volume = 0.0
        coverage_caveat: str | None = None
        if inp.procedure_volume_available:
            # Normalize: top-decile is ~500+ procedures/year for most specialties
            procedure_volume = min(inp.total_procedures / 500.0, 1.0)
        else:
            coverage_caveat = (
                "Procedure volume data unavailable; "
                "score based on available signals only"
            )

        return (
            board_cert,
            license_score,
            hospital_tier,
            trial_pi,
            procedure_volume,
            volume_confidence,
            coverage_caveat,
        )

    def compute_composite(
        self,
        board_cert: float,
        license_score: float,
        hospital_tier: float,
        trial_pi: float,
        procedure_volume: float,
    ) -> float:
        """Compute weighted composite F7 score."""
        return (
            _W_BOARD_CERT * board_cert
            + _W_LICENSE * license_score
            + _W_HOSPITAL_TIER * hospital_tier
            + _W_TRIAL_PI * trial_pi
            + _W_PROCEDURE_VOLUME * procedure_volume
        )

    def compute_percentiles(
        self,
        raw_scores: list[
            tuple[str, float, float, float, float, float, float, str | None]
        ],
    ) -> dict[str, F7Score]:
        """Compute percentile-ranked F7 scores for a clinician cohort.

        Each entry: (uuid, board_cert, license, hospital_tier, trial_pi,
                    procedure_volume, volume_confidence, coverage_caveat).
        """
        if not raw_scores:
            return {}

        # Compute composites for ranking
        composites: list[tuple[str, float]] = []
        for (
            uuid, board_cert, license_s, hosp_tier,
            trial_pi, proc_vol, _vol_conf, _caveat,
        ) in raw_scores:
            composite = self.compute_composite(
                board_cert, license_s, hosp_tier, trial_pi, proc_vol
            )
            composites.append((uuid, composite))

        # Sort for percentile assignment
        sorted_composites = sorted(composites, key=lambda x: x[1])
        n = len(sorted_composites)
        rank_map: dict[str, float] = {}
        for rank_idx, (uuid, _) in enumerate(sorted_composites):
            rank_map[uuid] = (rank_idx + 0.5) / n

        # Build result
        result: dict[str, F7Score] = {}
        for (
            uuid, board_cert, license_s, hosp_tier,
            trial_pi, proc_vol, vol_conf, caveat,
        ) in raw_scores:
            result[uuid] = F7Score(
                board_certification_score=round(board_cert, 4),
                license_score=round(license_s, 4),
                hospital_tier_score=round(hosp_tier, 4),
                trial_pi_score=round(trial_pi, 4),
                procedure_volume_score=round(proc_vol, 4),
                procedure_volume_confidence=round(vol_conf, 4),
                percentile=round(rank_map[uuid], 6),
                coverage_caveat=caveat,
            )

        return result
