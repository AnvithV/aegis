"""Tests for paper-mill detection via tortured-phrase scanning."""

from __future__ import annotations

from aegis.integrity.papermill import PaperMillDetector


def test_detect_tortured_phrases_in_title() -> None:
    det = PaperMillDetector(phrase_threshold=1)
    signal = det.analyze(
        title="A study on arbitrary forest classification",
    )
    assert signal.tortured_phrase_count >= 1
    assert signal.suspected_papermill is True


def test_detect_tortured_phrases_in_abstract() -> None:
    det = PaperMillDetector(phrase_threshold=1)
    signal = det.analyze(
        abstract="We used profound learning for this task.",
    )
    assert signal.tortured_phrase_count >= 1
    assert signal.suspected_papermill is True


def test_no_tortured_phrases() -> None:
    det = PaperMillDetector()
    signal = det.analyze(
        title="Normal scientific paper title",
        abstract="Standard methods and results.",
    )
    assert signal.tortured_phrase_count == 0
    assert signal.suspected_papermill is False


def test_threshold_behavior() -> None:
    det = PaperMillDetector(phrase_threshold=2)
    # Only 1 tortured phrase, below threshold
    signal = det.analyze(
        title="We used arbitrary forest",
    )
    assert signal.tortured_phrase_count == 1
    assert signal.suspected_papermill is False


def test_threshold_met() -> None:
    det = PaperMillDetector(phrase_threshold=2)
    signal = det.analyze(
        title="arbitrary forest with profound learning",
    )
    assert signal.tortured_phrase_count >= 2
    assert signal.suspected_papermill is True


def test_coordinated_authorship_triggers() -> None:
    det = PaperMillDetector()
    signal = det.analyze(
        title="Normal paper",
        coordinated_authorship_score=0.8,
    )
    assert signal.suspected_papermill is True


def test_coordinated_authorship_below_threshold() -> None:
    det = PaperMillDetector()
    signal = det.analyze(
        title="Normal paper",
        coordinated_authorship_score=0.5,
    )
    assert signal.suspected_papermill is False


def test_case_insensitive_matching() -> None:
    det = PaperMillDetector(phrase_threshold=1)
    signal = det.analyze(
        title="ARBITRARY FOREST method",
    )
    assert signal.tortured_phrase_count >= 1


def test_analyze_batch() -> None:
    det = PaperMillDetector(phrase_threshold=1)
    papers: list[dict[str, str | float]] = [
        {
            "pmid": "1",
            "title": "arbitrary forest study",
            "abstract": "",
        },
        {
            "pmid": "2",
            "title": "normal paper",
            "abstract": "nothing suspicious",
        },
    ]
    results = det.analyze_batch(papers)
    assert len(results) == 2
    assert results[0].suspected_papermill is True
    assert results[1].suspected_papermill is False


def test_analyze_returns_pmid() -> None:
    det = PaperMillDetector()
    signal = det.analyze(pmid="99999", title="test")
    assert signal.pmid == "99999"
