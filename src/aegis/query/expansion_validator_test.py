"""Tests for expansion validator (fail-closed MeSH ontology validation)."""

from __future__ import annotations

from aegis.query.expansion_validator import ExpansionValidator


def test_valid_mesh_term() -> None:
    v = ExpansionValidator(
        mesh_descriptors={"Neoplasms", "Protein Kinases", "Drug Therapy"}
    )
    report = v.validate(["Neoplasms"])
    assert report.valid_count == 1
    assert report.rejected_count == 0


def test_invalid_term_rejected() -> None:
    v = ExpansionValidator(mesh_descriptors={"Neoplasms"})
    report = v.validate(["Neoplasms", "MadeUpTerm123"])
    assert report.valid_count == 1
    assert report.rejected_count == 1
    assert "MadeUpTerm123" in report.rejected_terms


def test_case_insensitive() -> None:
    v = ExpansionValidator(mesh_descriptors={"Neoplasms"})
    report = v.validate(["neoplasms", "NEOPLASMS"])
    assert report.valid_count == 2
    assert report.rejected_count == 0


def test_cpc_xwalk_fallback() -> None:
    v = ExpansionValidator(
        mesh_descriptors=set(), cpc_mesh_terms={"Organic Chemistry"}
    )
    report = v.validate(["Organic Chemistry"])
    assert report.valid_count == 1
    assert report.details[0].source == "cpc_xwalk"


def test_chembl_xwalk_fallback() -> None:
    v = ExpansionValidator(
        mesh_descriptors=set(),
        cpc_mesh_terms=set(),
        chembl_mesh_terms={"Imatinib"},
    )
    report = v.validate(["Imatinib"])
    assert report.valid_count == 1
    assert report.details[0].source == "chembl_xwalk"


def test_fail_closed_empty_vocab() -> None:
    v = ExpansionValidator()
    report = v.validate(["Anything"])
    assert report.valid_count == 0
    assert report.rejected_count == 1


def test_validate_single() -> None:
    v = ExpansionValidator(mesh_descriptors={"Neoplasms"})
    assert v.validate_single("Neoplasms") is True
    assert v.validate_single("Fake") is False


def test_stats_tracking() -> None:
    v = ExpansionValidator(
        mesh_descriptors={"Neoplasms", "Drug Therapy", "Protein Kinases"}
    )
    v.validate(["Neoplasms", "Drug Therapy", "Protein Kinases", "Fake1", "Fake2"])
    stats = v.get_stats()
    assert stats.total_terms_checked == 5
    assert stats.total_rejected == 2


def test_validation_report_structure() -> None:
    v = ExpansionValidator(mesh_descriptors={"Neoplasms"})
    report = v.validate(["Neoplasms", "Fake"])
    assert report.total_terms == 2
    assert len(report.details) == 2
    assert report.validated_at is not None


def test_whitespace_handling() -> None:
    v = ExpansionValidator(mesh_descriptors={"Neoplasms", "Drug Therapy"})
    report = v.validate([" Neoplasms ", "  Drug Therapy  "])
    assert report.valid_count == 2
    assert report.rejected_count == 0
