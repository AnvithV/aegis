"""Tests for identity-linkage confidence reporting."""

from __future__ import annotations

from unittest.mock import MagicMock

from aegis.observability.linkage_report import (
    LinkageReporter,
)
from aegis.storage.schema import ArtifactRefBundle, Candidate


def _make_candidate(
    uuid: str,
    linkage_confidence: float = 0.8,
) -> Candidate:
    return Candidate(
        uuid=uuid,
        strong_keys={},
        name_variants=["Test Person"],
        affiliations=[],
        artifact_refs=ArtifactRefBundle(
            pmids=[], nct_ids=[], grant_ids=[]
        ),
        linkage_confidence=linkage_confidence,
        evidence_trail=[],
        last_updated_per_source={},
        mesh_descriptors=[],
    )


def _mock_store(candidates: list[Candidate]) -> MagicMock:
    store = MagicMock()
    store.list_by_cohort.return_value = candidates
    store.get_by_uuid.side_effect = lambda u: next(
        (c for c in candidates if c.uuid == u), None
    )
    return store


class TestClassifyConfident:
    def test_classify_confident(self) -> None:
        c = _make_candidate("a", linkage_confidence=0.85)
        store = _mock_store([c])
        reporter = LinkageReporter(store)
        assert reporter.classify_candidate("a") == "confident"


class TestClassifyLowConfidence:
    def test_classify_low_confidence(self) -> None:
        c = _make_candidate("a", linkage_confidence=0.6)
        store = _mock_store([c])
        reporter = LinkageReporter(store)
        assert reporter.classify_candidate("a") == "low_confidence"


class TestClassifyHoldout:
    def test_classify_holdout(self) -> None:
        c = _make_candidate("a", linkage_confidence=0.3)
        store = _mock_store([c])
        reporter = LinkageReporter(store)
        assert reporter.classify_candidate("a") == "holdout"

    def test_classify_missing_candidate(self) -> None:
        store = _mock_store([])
        reporter = LinkageReporter(store)
        assert reporter.classify_candidate("missing") == "holdout"


class TestGetHoldouts:
    def test_get_holdouts(self) -> None:
        candidates = [
            _make_candidate("a", linkage_confidence=0.9),
            _make_candidate("b", linkage_confidence=0.3),
            _make_candidate("c", linkage_confidence=0.4),
            _make_candidate("d", linkage_confidence=0.6),
        ]
        store = _mock_store(candidates)
        reporter = LinkageReporter(store)
        holdouts = reporter.get_holdouts()
        assert sorted(holdouts) == ["b", "c"]


class TestGetFlagged:
    def test_get_flagged(self) -> None:
        candidates = [
            _make_candidate("a", linkage_confidence=0.9),
            _make_candidate("b", linkage_confidence=0.3),
            _make_candidate("c", linkage_confidence=0.55),
            _make_candidate("d", linkage_confidence=0.65),
        ]
        store = _mock_store(candidates)
        reporter = LinkageReporter(store)
        flagged = reporter.get_flagged()
        assert sorted(flagged) == ["c", "d"]


class TestDailyShiftReport:
    def test_daily_shift_report(self) -> None:
        candidates = [
            _make_candidate("a", linkage_confidence=0.85),
            _make_candidate("b", linkage_confidence=0.6),
            _make_candidate("c", linkage_confidence=0.5),
        ]
        store = _mock_store(candidates)
        reporter = LinkageReporter(store)
        prev = {"a": 0.8, "b": 0.65, "c": 0.5}
        shifts = reporter.daily_shift_report(prev)

        uuids = {s.candidate_uuid for s in shifts}
        # c didn't change so should not be in the report
        assert "c" not in uuids
        assert "a" in uuids
        assert "b" in uuids

        shift_a = next(s for s in shifts if s.candidate_uuid == "a")
        assert shift_a.delta > 0


class TestThresholdCrossingDetected:
    def test_threshold_crossing_detected(self) -> None:
        # b crosses flag threshold upward (0.65 -> 0.75)
        candidates = [
            _make_candidate("b", linkage_confidence=0.75),
        ]
        store = _mock_store(candidates)
        reporter = LinkageReporter(store)
        prev = {"b": 0.65}
        shifts = reporter.daily_shift_report(prev)

        assert len(shifts) == 1
        assert shifts[0].crossed_threshold == "flag"

    def test_holdout_crossing_detected(self) -> None:
        # crosses holdout threshold downward (0.55 -> 0.45)
        candidates = [
            _make_candidate("c", linkage_confidence=0.45),
        ]
        store = _mock_store(candidates)
        reporter = LinkageReporter(store)
        prev = {"c": 0.55}
        shifts = reporter.daily_shift_report(prev)

        assert len(shifts) == 1
        assert shifts[0].crossed_threshold == "holdout"
