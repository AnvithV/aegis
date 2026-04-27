"""Tests for pairwise audit consistency tracking."""

from __future__ import annotations

from aegis.observability.audit_consistency import (
    AuditConsistencyTracker,
    ConsistencyReport,
    JudgmentRecord,
)


def _make_judgment(
    judgment_id: str,
    reviewer_id: str,
    a: str,
    b: str,
    winner: str,
    is_reshow: bool = False,
) -> JudgmentRecord:
    return JudgmentRecord(
        judgment_id=judgment_id,
        reviewer_id=reviewer_id,
        candidate_a_uuid=a,
        candidate_b_uuid=b,
        winner_uuid=winner,
        is_reshow=is_reshow,
    )


def test_should_reshow_rate() -> None:
    """should_reshow triggers at expected intervals."""
    tracker = AuditConsistencyTracker(reshow_rate=0.05)
    # 1/0.05 = 20, so every 20th pair
    results = [tracker.should_reshow(i) for i in range(40)]
    reshow_indices = [i for i, r in enumerate(results) if r]
    assert 0 in reshow_indices  # 0 % 20 == 0
    assert 20 in reshow_indices  # 20 % 20 == 0
    assert 1 not in reshow_indices


def test_kappa_perfect_agreement() -> None:
    """Perfect agreement gives kappa = 1.0."""
    tracker = AuditConsistencyTracker()
    pairs = [("a", "a"), ("b", "b"), ("a", "a"), ("b", "b")]
    kappa = tracker.compute_kappa(pairs)
    assert kappa is not None
    assert abs(kappa - 1.0) < 1e-9


def test_kappa_random_agreement() -> None:
    """Random agreement gives kappa near 0."""
    tracker = AuditConsistencyTracker()
    # Construct pairs where agreement is roughly at chance
    pairs = [
        ("a", "b"),
        ("b", "a"),
        ("a", "a"),
        ("b", "b"),
    ]
    kappa = tracker.compute_kappa(pairs)
    assert kappa is not None
    assert abs(kappa) < 0.5  # near zero


def test_kappa_no_pairs() -> None:
    """Fewer than 2 pairs returns None."""
    tracker = AuditConsistencyTracker()
    assert tracker.compute_kappa([]) is None
    assert tracker.compute_kappa([("a", "a")]) is None


def test_find_overlapping_pairs() -> None:
    """Overlapping pairs found when different reviewers judge same pair."""
    tracker = AuditConsistencyTracker()
    judgments = [
        _make_judgment("j1", "r1", "c1", "c2", "c1"),
        _make_judgment("j2", "r2", "c1", "c2", "c1"),
        _make_judgment("j3", "r1", "c3", "c4", "c3"),
    ]
    overlapping = tracker.find_overlapping_pairs(judgments)
    assert len(overlapping) == 1
    key = ("c1", "c2")
    assert key in overlapping
    assert len(overlapping[key]) == 2


def test_find_reshow_pairs() -> None:
    """Reshow pairs found when same reviewer judges same pair twice."""
    tracker = AuditConsistencyTracker()
    judgments = [
        _make_judgment("j1", "r1", "c1", "c2", "c1"),
        _make_judgment("j2", "r1", "c1", "c2", "c1", is_reshow=True),
        _make_judgment("j3", "r2", "c3", "c4", "c3"),
    ]
    reshow = tracker.find_reshow_pairs(judgments)
    assert len(reshow) == 1
    key = ("r1", "c1", "c2")
    assert key in reshow
    assert len(reshow[key]) == 2


def test_full_report() -> None:
    """Full report computes inter and intra kappa."""
    tracker = AuditConsistencyTracker()
    judgments = [
        # Inter-reviewer: r1 and r2 judge same pair, agree
        _make_judgment("j1", "r1", "c1", "c2", "c1"),
        _make_judgment("j2", "r2", "c1", "c2", "c1"),
        _make_judgment("j3", "r1", "c3", "c4", "c3"),
        _make_judgment("j4", "r2", "c3", "c4", "c3"),
        # Intra-reviewer: r1 reshows
        _make_judgment("j5", "r1", "c5", "c6", "c5"),
        _make_judgment(
            "j6", "r1", "c5", "c6", "c5", is_reshow=True
        ),
        _make_judgment("j7", "r1", "c7", "c8", "c7"),
        _make_judgment(
            "j8", "r1", "c7", "c8", "c7", is_reshow=True
        ),
    ]
    report = tracker.compute_report(judgments)
    assert isinstance(report, ConsistencyReport)
    assert report.overlapping_pair_count == 2
    assert report.inter_reviewer_kappa is not None
    assert report.inter_reviewer_kappa == 1.0  # perfect agreement
    assert report.intra_reviewer_kappa is not None
    assert report.intra_reviewer_kappa == 1.0  # perfect reshow


def test_low_agreement_detection() -> None:
    """Reviewers with low reshow agreement are flagged."""
    tracker = AuditConsistencyTracker(low_agreement_threshold=0.6)
    judgments = [
        # r1 reshows: disagrees with self
        _make_judgment("j1", "r1", "c1", "c2", "c1"),
        _make_judgment(
            "j2", "r1", "c1", "c2", "c2", is_reshow=True
        ),
        _make_judgment("j3", "r1", "c3", "c4", "c3"),
        _make_judgment(
            "j4", "r1", "c3", "c4", "c4", is_reshow=True
        ),
        # r2 reshows: agrees with self
        _make_judgment("j5", "r2", "c5", "c6", "c5"),
        _make_judgment(
            "j6", "r2", "c5", "c6", "c5", is_reshow=True
        ),
        _make_judgment("j7", "r2", "c7", "c8", "c7"),
        _make_judgment(
            "j8", "r2", "c7", "c8", "c7", is_reshow=True
        ),
    ]
    report = tracker.compute_report(judgments)
    assert "r1" in report.low_agreement_reviewers
    assert "r2" not in report.low_agreement_reviewers
    assert report.per_reviewer_agreement["r1"] == 0.0
    assert report.per_reviewer_agreement["r2"] == 1.0
