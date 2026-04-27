"""Regression tests for cross-population identity merge."""

from __future__ import annotations


def test_merge_precision_threshold() -> None:
    """Cross-population auto-merge precision target >= 99%."""
    from aegis.observability.merge_accuracy import MergeAccuracyTracker

    tracker = MergeAccuracyTracker()
    predictions = [(f"a{i}", f"b{i}", True) for i in range(95)]
    predictions += [(f"a{i}", f"b{i}", False) for i in range(95, 100)]
    ground_truth = [(f"a{i}", f"b{i}", True) for i in range(95)]
    ground_truth += [(f"a{i}", f"b{i}", False) for i in range(95, 100)]
    metrics = tracker.evaluate(predictions, ground_truth)
    assert metrics.precision >= 0.99
    assert metrics.meets_precision_target
