"""USNWR hospital-tier classification."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_TIER_PATH = Path("data/aegis/hospital_tier_v2026.yaml")


class HospitalTierRank(BaseModel):
    """Tier classification result for a hospital."""

    model_config = ConfigDict(frozen=True)

    ror_id: str | None
    hospital_name: str
    tier: int                      # 1, 2, 3, or 0 (unranked)
    overall_rank: int | None
    specialty_rank: int | None     # Non-null if specialty override applies
    specialty_override: bool       # True if specialty ranking overrides overall


class HospitalTier:
    """Map hospital affiliations to USNWR tier rankings."""

    def __init__(
        self,
        tier_path: Path | None = None,
    ) -> None:
        self._by_ror: dict[str, dict[str, Any]] = {}
        self._by_name: dict[str, dict[str, Any]] = {}
        self._specialty_overrides: dict[str, dict[str, dict[str, Any]]] = {}
        self._load(tier_path or _DEFAULT_TIER_PATH)

    def _load(self, path: Path) -> None:
        """Load tier data from YAML."""
        with open(path) as f:  # noqa: PTH123
            data: dict[str, Any] = yaml.safe_load(f)

        for tier_group in data.get("tiers", []):
            tier_num = tier_group["tier"]
            for hosp in tier_group.get("hospitals", []):
                entry = {
                    "name": hosp["name"],
                    "tier": tier_num,
                    "overall_rank": hosp.get("overall_rank"),
                }
                if hosp.get("ror_id"):
                    self._by_ror[hosp["ror_id"]] = entry
                self._by_name[hosp["name"].lower()] = entry

        for override in data.get("specialty_overrides", []):
            specialty = override["specialty"].lower()
            self._specialty_overrides[specialty] = {}
            for hosp in override.get("hospitals", []):
                if hosp.get("ror_id"):
                    self._specialty_overrides[specialty][hosp["ror_id"]] = {
                        "name": hosp["name"],
                        "specialty_rank": hosp.get("specialty_rank"),
                    }

        logger.info(
            "Loaded %d hospitals, %d specialty overrides",
            len(self._by_ror) + len(self._by_name),
            len(self._specialty_overrides),
        )

    def lookup(
        self,
        ror_id: str | None = None,
        hospital_name: str | None = None,
        specialty: str | None = None,
    ) -> HospitalTierRank:
        """Look up hospital tier by ROR ID or name.

        If specialty is provided and a specialty-specific ranking exists,
        it overrides the overall tier.
        """
        # Check specialty override first
        specialty_rank = None
        specialty_override = False
        if specialty and ror_id:
            spec_lower = specialty.lower()
            if spec_lower in self._specialty_overrides:
                if ror_id in self._specialty_overrides[spec_lower]:
                    override = self._specialty_overrides[spec_lower][ror_id]
                    specialty_rank = override.get("specialty_rank")
                    specialty_override = True

        # Look up overall tier
        entry = None
        if ror_id and ror_id in self._by_ror:
            entry = self._by_ror[ror_id]
        elif hospital_name:
            entry = self._by_name.get(hospital_name.lower())

        if entry is None:
            # Specialty override may promote an unranked hospital to tier 1
            tier = 0
            if specialty_override and specialty_rank and specialty_rank <= 5:
                tier = 1
            return HospitalTierRank(
                ror_id=ror_id,
                hospital_name=hospital_name or "Unknown",
                tier=tier,
                overall_rank=None,
                specialty_rank=specialty_rank,
                specialty_override=specialty_override,
            )

        # Specialty override may promote to tier 1
        tier = entry["tier"]
        if specialty_override and specialty_rank and specialty_rank <= 5:
            tier = 1

        return HospitalTierRank(
            ror_id=ror_id,
            hospital_name=entry["name"],
            tier=tier,
            overall_rank=entry.get("overall_rank"),
            specialty_rank=specialty_rank,
            specialty_override=specialty_override,
        )
