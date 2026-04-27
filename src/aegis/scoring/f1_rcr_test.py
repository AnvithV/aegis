"""Tests for F1 sub-score: RCR aggregation."""

from __future__ import annotations

import math

from aegis.scoring.f1_rcr import (
    AUTHOR_WEIGHT_FIRST,
    AUTHOR_WEIGHT_LAST,
    F1Computer,
    F1Score,
    PaperRCR,
)


def _make_paper(
    pmid: str,
    rcr: float,
    weight: float = AUTHOR_WEIGHT_LAST,
    article_type: str | None = "Journal Article",
) -> PaperRCR:
    return PaperRCR(
        pmid=pmid,
        rcr=rcr,
        author_weight=weight,
        article_type=article_type,
    )


def test_score_raw_basic() -> None:
    """15 papers with varying RCR and positions compute correctly."""
    computer = F1Computer()
    papers = [
        _make_paper(f"P{i}", rcr=float(i + 1), weight=AUTHOR_WEIGHT_LAST)
        for i in range(10)
    ] + [
        _make_paper(f"P{10+i}", rcr=float(i + 1), weight=AUTHOR_WEIGHT_FIRST)
        for i in range(5)
    ]

    mean_log, top_log, low_conf, count = computer.score_raw(papers)

    assert count == 15
    assert low_conf is False
    assert mean_log != 0.0
    assert top_log >= mean_log  # 90th pctile >= mean

    # Verify mean manually
    weighted = []
    for p in papers:
        weighted.append(math.log(p.rcr + 1e-9) * p.author_weight)
    expected_mean = sum(weighted) / len(weighted)
    assert abs(mean_log - expected_mean) < 1e-9


def test_score_raw_excludes_editorials() -> None:
    """Editorial articles are excluded from RCR aggregation."""
    computer = F1Computer()
    papers = [
        _make_paper("P1", rcr=5.0, article_type="Journal Article"),
        _make_paper("P2", rcr=10.0, article_type="Editorial"),
        _make_paper("P3", rcr=3.0, article_type="Letter"),
        _make_paper("P4", rcr=2.0, article_type="Comment"),
    ]

    _, _, _, count = computer.score_raw(papers)
    assert count == 1  # only P1 is eligible


def test_score_raw_low_confidence() -> None:
    """Fewer than 10 eligible papers triggers low_confidence=True."""
    computer = F1Computer()
    papers = [_make_paper(f"P{i}", rcr=2.0) for i in range(5)]

    _, _, low_conf, count = computer.score_raw(papers)
    assert count == 5
    assert low_conf is True


def test_score_raw_empty() -> None:
    """No papers returns zeros and low_confidence=True."""
    computer = F1Computer()
    mean_log, top_log, low_conf, count = computer.score_raw([])

    assert mean_log == 0.0
    assert top_log == 0.0
    assert low_conf is True
    assert count == 0


def test_compute_percentiles_uniform() -> None:
    """100 candidates with uniform RCR span percentiles [0, 1]."""
    computer = F1Computer()
    raw_scores: list[tuple[str, float, float, bool, int]] = [
        (f"C{i}", float(i), float(i), False, 20)
        for i in range(100)
    ]

    results = computer.compute_percentiles(raw_scores)

    assert len(results) == 100

    # Lowest candidate should have low percentile
    assert results["C0"].percentile < 0.02
    # Highest should have high percentile
    assert results["C99"].percentile > 0.98
    # Percentiles should be strictly increasing for distinct inputs
    pcts = [results[f"C{i}"].percentile for i in range(100)]
    for i in range(1, len(pcts)):
        assert pcts[i] > pcts[i - 1]


def test_compute_percentiles_single() -> None:
    """Single candidate gets percentile 0.5."""
    computer = F1Computer()
    raw_scores: list[tuple[str, float, float, bool, int]] = [
        ("C0", 1.5, 2.0, False, 15),
    ]

    results = computer.compute_percentiles(raw_scores)

    assert len(results) == 1
    assert isinstance(results["C0"], F1Score)
    assert results["C0"].percentile == 0.5
    assert results["C0"].mean_rcr_log == 1.5
    assert results["C0"].top_rcr_log == 2.0
    assert results["C0"].low_confidence is False
    assert results["C0"].eligible_paper_count == 15
