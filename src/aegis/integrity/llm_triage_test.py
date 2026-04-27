"""Tests for LLM retraction-notice triage classifier."""

from __future__ import annotations

from aegis.integrity.llm_triage import (
    SEVERITY_DISCOUNT_MAP,
    LLMTriageClassifier,
    RetractionSeverity,
)


def test_fabrication_keyword() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        pmid="1",
        retraction_notice_text="Data was fabricated by the author.",
    )
    assert result.severity == RetractionSeverity.fabrication


def test_fabrication_made_up() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="Results were made up entirely.",
    )
    assert result.severity == RetractionSeverity.fabrication


def test_falsification_keyword() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="Evidence of data falsification.",
    )
    assert result.severity == RetractionSeverity.falsification


def test_falsification_manipulation() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="Image manipulation was detected.",
    )
    assert result.severity == RetractionSeverity.falsification


def test_honest_error_keyword() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="Retracted due to honest error.",
    )
    assert result.severity == RetractionSeverity.honest_error


def test_honest_error_inadvertent() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="An inadvertent mistake was found.",
    )
    assert result.severity == RetractionSeverity.honest_error


def test_duplicate_publication() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text=(
            "This is an overlapping publication with prior work."
        ),
    )
    assert result.severity == RetractionSeverity.duplicate_publication


def test_no_statement_empty_text() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(pmid="42", retraction_notice_text="")
    assert result.severity == RetractionSeverity.no_statement
    assert result.confidence == 0.9


def test_unclassifiable_no_match() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="Article withdrawn at request.",
    )
    assert result.severity == RetractionSeverity.unclassifiable
    assert result.confidence == 0.5


def test_confidence_for_keyword_match() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="Data fabrication confirmed.",
    )
    assert result.confidence == 0.8


def test_grounded_always_true_for_heuristic() -> None:
    clf = LLMTriageClassifier()
    for text in [
        "fabricated data",
        "falsification detected",
        "honest error",
        "overlapping publication",
        "",
        "unknown reason",
    ]:
        result = clf.classify(retraction_notice_text=text)
        assert result.grounded is True


def test_severity_discount_map_completeness() -> None:
    for severity in RetractionSeverity:
        assert severity in SEVERITY_DISCOUNT_MAP
    assert SEVERITY_DISCOUNT_MAP[RetractionSeverity.fabrication] == 0.0
    assert SEVERITY_DISCOUNT_MAP[RetractionSeverity.falsification] == 0.0
    assert SEVERITY_DISCOUNT_MAP[RetractionSeverity.honest_error] == 0.85


def test_classify_batch() -> None:
    clf = LLMTriageClassifier()
    notices = [
        {"pmid": "1", "retraction_notice_text": "fabrication"},
        {"pmid": "2", "retraction_notice_text": "honest error"},
        {"pmid": "3", "retraction_notice_text": "unknown"},
    ]
    results = clf.classify_batch(notices)
    assert len(results) == 3
    assert results[0].severity == RetractionSeverity.fabrication
    assert results[1].severity == RetractionSeverity.honest_error
    assert results[2].severity == RetractionSeverity.unclassifiable


def test_case_insensitive_matching() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        retraction_notice_text="DATA FABRICATION confirmed.",
    )
    assert result.severity == RetractionSeverity.fabrication


def test_result_contains_pmid() -> None:
    clf = LLMTriageClassifier()
    result = clf.classify(
        pmid="99999",
        retraction_notice_text="fabrication",
    )
    assert result.pmid == "99999"
