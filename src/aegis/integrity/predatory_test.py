"""Tests for predatory journal classification and load scoring."""

from __future__ import annotations

from aegis.integrity.predatory import (
    PredatoryClassifier,
    PredatoryLoadCalculator,
    PredatorySignal,
)


def test_medline_never_predatory() -> None:
    clf = PredatoryClassifier()
    signal = clf.classify(
        is_medline_indexed=True,
        is_doaj_listed=False,
        cabells_flagged=True,
        heuristic_flags=["fee", "spam", "fake"],
    )
    assert signal.is_predatory is False


def test_cabells_flagged_predatory() -> None:
    clf = PredatoryClassifier()
    signal = clf.classify(
        is_medline_indexed=False,
        is_doaj_listed=True,
        cabells_flagged=True,
        heuristic_flags=[],
    )
    assert signal.is_predatory is True


def test_heuristic_fallback_predatory() -> None:
    clf = PredatoryClassifier()
    # Not MEDLINE, not DOAJ, >=2 heuristic flags
    signal = clf.classify(
        is_medline_indexed=False,
        is_doaj_listed=False,
        cabells_flagged=False,
        heuristic_flags=["fee", "spam"],
    )
    assert signal.is_predatory is True


def test_heuristic_fallback_doaj_not_predatory() -> None:
    clf = PredatoryClassifier()
    # Not MEDLINE but DOAJ-listed, heuristic flags ignored
    signal = clf.classify(
        is_medline_indexed=False,
        is_doaj_listed=True,
        cabells_flagged=False,
        heuristic_flags=["fee", "spam"],
    )
    assert signal.is_predatory is False


def test_heuristic_below_threshold() -> None:
    clf = PredatoryClassifier()
    signal = clf.classify(
        is_medline_indexed=False,
        is_doaj_listed=False,
        cabells_flagged=False,
        heuristic_flags=["fee"],
    )
    assert signal.is_predatory is False


def test_classify_returns_signal_fields() -> None:
    clf = PredatoryClassifier()
    signal = clf.classify(
        is_medline_indexed=True,
        is_doaj_listed=False,
        cabells_flagged=False,
        heuristic_flags=[],
        pmid="12345",
        journal_nlm_id="NLM001",
    )
    assert signal.pmid == "12345"
    assert signal.journal_nlm_id == "NLM001"
    assert signal.is_medline_indexed is True


def test_load_calculator_all_predatory() -> None:
    calc = PredatoryLoadCalculator()
    signals = [
        PredatorySignal(
            pmid="1",
            journal_nlm_id=None,
            is_medline_indexed=False,
            is_doaj_listed=False,
            cabells_flagged=True,
            heuristic_flags=[],
            is_predatory=True,
        ),
        PredatorySignal(
            pmid="2",
            journal_nlm_id=None,
            is_medline_indexed=False,
            is_doaj_listed=False,
            cabells_flagged=True,
            heuristic_flags=[],
            is_predatory=True,
        ),
    ]
    load = calc.compute_load(signals, ["last", "first"])
    assert load == 1.0


def test_load_calculator_none_predatory() -> None:
    calc = PredatoryLoadCalculator()
    signals = [
        PredatorySignal(
            pmid="1",
            journal_nlm_id=None,
            is_medline_indexed=True,
            is_doaj_listed=False,
            cabells_flagged=False,
            heuristic_flags=[],
            is_predatory=False,
        ),
    ]
    load = calc.compute_load(signals, ["first"])
    assert load == 0.0


def test_load_calculator_mixed() -> None:
    calc = PredatoryLoadCalculator()
    pred = PredatorySignal(
        pmid="1",
        journal_nlm_id=None,
        is_medline_indexed=False,
        is_doaj_listed=False,
        cabells_flagged=True,
        heuristic_flags=[],
        is_predatory=True,
    )
    clean = PredatorySignal(
        pmid="2",
        journal_nlm_id=None,
        is_medline_indexed=True,
        is_doaj_listed=False,
        cabells_flagged=False,
        heuristic_flags=[],
        is_predatory=False,
    )
    # last=1.0 (predatory) + first=0.8 (clean)
    load = calc.compute_load([pred, clean], ["last", "first"])
    assert abs(load - 1.0 / 1.8) < 1e-9


def test_load_calculator_empty() -> None:
    calc = PredatoryLoadCalculator()
    assert calc.compute_load([], []) == 0.0
