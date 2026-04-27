"""Tests for USNWR hospital-tier classification."""

from __future__ import annotations

from pathlib import Path

from aegis.sources.usnwr import HospitalTier

_SAMPLE_YAML = """\
version: 2026
tiers:
  - tier: 1
    description: "Top tier"
    hospitals:
      - ror_id: "https://ror.org/00hj8s172"
        name: "Mayo Clinic"
        overall_rank: 1
      - ror_id: "https://ror.org/01y2jtd41"
        name: "Cleveland Clinic"
        overall_rank: 2
  - tier: 2
    description: "Second tier"
    hospitals:
      - ror_id: "https://ror.org/05byvp690"
        name: "UCSF Medical Center"
        overall_rank: 10
  - tier: 3
    description: "Third tier"
    hospitals:
      - ror_id: "https://ror.org/99999999"
        name: "Regional Hospital"
        overall_rank: null
specialty_overrides:
  - specialty: "oncology"
    hospitals:
      - ror_id: "https://ror.org/mdanderson"
        name: "MD Anderson Cancer Center"
        specialty_rank: 1
  - specialty: "cardiology"
    hospitals:
      - ror_id: "https://ror.org/01y2jtd41"
        name: "Cleveland Clinic"
        specialty_rank: 1
"""


def _make_tier(tmp_path: Path) -> HospitalTier:
    yaml_path = tmp_path / "tiers.yaml"
    yaml_path.write_text(_SAMPLE_YAML)
    return HospitalTier(tier_path=yaml_path)


def test_load_tier_data(tmp_path: Path) -> None:
    ht = _make_tier(tmp_path)
    # Should have loaded entries into by_ror and by_name
    assert len(ht._by_ror) >= 3
    assert len(ht._by_name) >= 4


def test_lookup_by_ror(tmp_path: Path) -> None:
    ht = _make_tier(tmp_path)
    result = ht.lookup(ror_id="https://ror.org/00hj8s172")
    assert result.tier == 1
    assert result.hospital_name == "Mayo Clinic"
    assert result.overall_rank == 1
    assert result.specialty_override is False


def test_lookup_by_name(tmp_path: Path) -> None:
    ht = _make_tier(tmp_path)
    result = ht.lookup(hospital_name="UCSF Medical Center")
    assert result.tier == 2
    assert result.overall_rank == 10


def test_unranked_hospital(tmp_path: Path) -> None:
    ht = _make_tier(tmp_path)
    result = ht.lookup(ror_id="https://ror.org/unknown")
    assert result.tier == 0
    assert result.overall_rank is None
    assert result.specialty_override is False


def test_specialty_override(tmp_path: Path) -> None:
    ht = _make_tier(tmp_path)
    result = ht.lookup(
        ror_id="https://ror.org/mdanderson",
        specialty="oncology",
    )
    assert result.specialty_rank == 1
    assert result.specialty_override is True


def test_specialty_override_promotes_tier(tmp_path: Path) -> None:
    ht = _make_tier(tmp_path)
    # MD Anderson is not in the overall tiers, but has oncology specialty_rank=1
    # specialty_rank <= 5 should promote to tier 1
    result = ht.lookup(
        ror_id="https://ror.org/mdanderson",
        specialty="oncology",
    )
    assert result.specialty_override is True
    assert result.specialty_rank == 1
    # MD Anderson is not in _by_ror for overall, so tier starts at 0
    # but specialty override with rank <= 5 promotes to tier 1
    assert result.tier == 1
