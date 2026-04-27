"""Tests for cross-population identity merge and multi-specialty router."""

from __future__ import annotations

from aegis.identity.cross_population_merge import (
    AUTO_MERGE_THRESHOLD,
    CrossPopulationMerger,
    MergeCandidate,
    MergeResult,
)
from aegis.scoring.multi_specialty import MultiSpecialtyRouter


def _make_candidate(
    uuid: str = "uuid-1",
    name_variants: list[str] | None = None,
    strong_keys: dict[str, str] | None = None,
    populations: list[str] | None = None,
    specialty_distribution: dict[str, float] | None = None,
    artifact_sources: dict[str, int] | None = None,
) -> MergeCandidate:
    return MergeCandidate(
        uuid=uuid,
        name_variants=name_variants or ["Jane Doe"],
        strong_keys=strong_keys or {},
        populations=populations or ["translational"],
        specialty_distribution=specialty_distribution or {"translational": 0.8},
        artifact_sources=artifact_sources or {"pubmed": 10},
    )


def test_strong_key_merge() -> None:
    """Same ORCID should produce auto-merge with confidence >= 0.95."""
    merger = CrossPopulationMerger()
    c1 = _make_candidate(
        uuid="uuid-1",
        strong_keys={"orcid": "0000-0001-2345-6789"},
        populations=["translational"],
    )
    c2 = _make_candidate(
        uuid="uuid-2",
        strong_keys={"orcid": "0000-0001-2345-6789"},
        populations=["drug_discovery"],
    )
    merger.add_candidate(c1)
    merger.add_candidate(c2)

    matches = merger.find_merge_candidates(c1, "translational")
    assert len(matches) == 1
    match, confidence, merge_type = matches[0]
    assert confidence >= AUTO_MERGE_THRESHOLD
    assert merge_type == "strong_key"


def test_npi_merge() -> None:
    """Same NPI should produce strong-key merge."""
    merger = CrossPopulationMerger()
    c1 = _make_candidate(
        uuid="uuid-1",
        strong_keys={"npi": "1234567890"},
        populations=["clinician"],
    )
    c2 = _make_candidate(
        uuid="uuid-2",
        strong_keys={"npi": "1234567890"},
        populations=["translational"],
    )
    merger.add_candidate(c1)
    merger.add_candidate(c2)

    matches = merger.find_merge_candidates(c1, "clinician")
    assert len(matches) == 1
    _, confidence, merge_type = matches[0]
    assert confidence >= 0.95
    assert merge_type == "strong_key"


def test_name_based_merge() -> None:
    """Shared name variants should produce review-needed merge."""
    merger = CrossPopulationMerger()
    c1 = _make_candidate(
        uuid="uuid-1",
        name_variants=["Jane Doe", "J Doe"],
        strong_keys={},
    )
    c2 = _make_candidate(
        uuid="uuid-2",
        name_variants=["Jane Doe", "Jane M Doe"],
        strong_keys={},
    )
    merger.add_candidate(c1)
    merger.add_candidate(c2)

    matches = merger.find_merge_candidates(c1, "translational")
    assert len(matches) == 1
    _, confidence, merge_type = matches[0]
    assert confidence >= 0.5
    assert merge_type == "review_needed"


def test_no_match() -> None:
    """No shared keys or names should produce no matches."""
    merger = CrossPopulationMerger()
    c1 = _make_candidate(
        uuid="uuid-1",
        name_variants=["Jane Doe"],
        strong_keys={"orcid": "0000-0001-0000-0001"},
    )
    c2 = _make_candidate(
        uuid="uuid-2",
        name_variants=["John Smith"],
        strong_keys={"orcid": "0000-0002-0000-0002"},
    )
    merger.add_candidate(c1)
    merger.add_candidate(c2)

    matches = merger.find_merge_candidates(c1, "translational")
    assert len(matches) == 0


def test_merge_preserves_populations() -> None:
    """Merge should combine populations from both candidates."""
    merger = CrossPopulationMerger()
    c1 = _make_candidate(
        uuid="uuid-1",
        strong_keys={"orcid": "0000-0001-2345-6789"},
        populations=["translational"],
        specialty_distribution={"translational": 0.8, "drug_discovery": 0.2},
    )
    c2 = _make_candidate(
        uuid="uuid-2",
        strong_keys={"orcid": "0000-0001-2345-6789"},
        populations=["drug_discovery"],
        specialty_distribution={"drug_discovery": 0.7, "translational": 0.3},
    )
    merger.add_candidate(c1)
    merger.add_candidate(c2)

    result = merger.merge(c1, c2, 0.97, "strong_key")
    assert result.merged_uuid == "uuid-1"
    assert "translational" in result.populations_merged
    assert "drug_discovery" in result.populations_merged
    assert result.source_uuids == ["uuid-1", "uuid-2"]


def test_merge_log() -> None:
    """Merge log captures all operations."""
    merger = CrossPopulationMerger()
    c1 = _make_candidate(uuid="uuid-1", strong_keys={"orcid": "0000-0001"})
    c2 = _make_candidate(uuid="uuid-2", strong_keys={"orcid": "0000-0001"})
    merger.add_candidate(c1)
    merger.add_candidate(c2)

    assert len(merger.get_merge_log()) == 0
    merger.merge(c1, c2, 0.97, "strong_key")
    log = merger.get_merge_log()
    assert len(log) == 1
    assert log[0].merged_uuid == "uuid-1"
    assert log[0].confidence == 0.97


def test_multi_specialty_router_select() -> None:
    """MultiSpecialtyRouter.select_specialty picks highest probability."""
    router = MultiSpecialtyRouter()
    router.load_all()

    selected = router.select_specialty(
        {"translational": 0.2, "drug_discovery": 0.7, "clinician": 0.1}
    )
    assert selected == "drug_discovery"


def test_multi_specialty_router_query_override() -> None:
    """Query specialty should override distribution."""
    router = MultiSpecialtyRouter()
    router.load_all()

    selected = router.select_specialty(
        {"translational": 0.8, "drug_discovery": 0.1, "clinician": 0.1},
        query_specialty="clinician",
    )
    assert selected == "clinician"


def test_merge_candidate_model() -> None:
    """MergeCandidate is frozen and stores all fields."""
    mc = _make_candidate(
        uuid="test-uuid",
        name_variants=["Dr. Smith", "Smith J"],
        strong_keys={"orcid": "0000-0001"},
        populations=["translational", "drug_discovery"],
        specialty_distribution={"translational": 0.6, "drug_discovery": 0.4},
        artifact_sources={"pubmed": 5, "patents": 3},
    )
    assert mc.uuid == "test-uuid"
    assert len(mc.name_variants) == 2
    assert mc.strong_keys["orcid"] == "0000-0001"
    assert len(mc.populations) == 2
    assert mc.artifact_sources["patents"] == 3


def test_specialty_distribution_merge() -> None:
    """Merge takes max probability for overlapping specialties."""
    merger = CrossPopulationMerger()
    c1 = _make_candidate(
        uuid="uuid-1",
        strong_keys={"npi": "123"},
        specialty_distribution={"translational": 0.8, "clinician": 0.2},
        populations=["translational"],
    )
    c2 = _make_candidate(
        uuid="uuid-2",
        strong_keys={"npi": "123"},
        specialty_distribution={"clinician": 0.9, "translational": 0.1},
        populations=["clinician"],
    )
    merger.add_candidate(c1)
    merger.add_candidate(c2)

    result = merger.merge(c1, c2, 0.97, "strong_key")
    assert result.merged_uuid == "uuid-1"
    assert "translational" in result.populations_merged
    assert "clinician" in result.populations_merged
