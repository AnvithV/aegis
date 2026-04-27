"""Cross-population merge accuracy tracking for identity resolution."""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

PRECISION_TARGET = 0.99
RECALL_TARGET = 0.85


class MergeAccuracyMetrics(BaseModel):
    """Frozen snapshot of merge accuracy evaluation."""

    model_config = ConfigDict(frozen=True)

    total_test_cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    meets_precision_target: bool
    meets_recall_target: bool


class MergeAccuracyTracker:
    """Evaluate cross-population merge accuracy against ground truth."""

    def evaluate(
        self,
        predictions: list[tuple[str, str, bool]],
        ground_truth: list[tuple[str, str, bool]],
    ) -> MergeAccuracyMetrics:
        """Evaluate merge predictions against ground truth.

        Each entry is (id_a, id_b, is_match). Computes TP/FP/FN,
        precision, recall, and F1 against configured targets.
        """
        truth_map: dict[tuple[str, str], bool] = {}
        for id_a, id_b, is_match in ground_truth:
            key = (id_a, id_b)
            truth_map[key] = is_match

        tp = 0
        fp = 0
        fn = 0

        pred_map: dict[tuple[str, str], bool] = {}
        for id_a, id_b, is_match in predictions:
            key = (id_a, id_b)
            pred_map[key] = is_match

        # Count TP and FP from predictions
        for key, predicted_match in pred_map.items():
            actual_match = truth_map.get(key, False)
            if predicted_match and actual_match:
                tp += 1
            elif predicted_match and not actual_match:
                fp += 1

        # Count FN from ground truth
        for key, actual_match in truth_map.items():
            predicted_match = pred_map.get(key, False)
            if actual_match and not predicted_match:
                fn += 1

        total_test_cases = len(set(list(pred_map.keys()) + list(truth_map.keys())))

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = (
            2 * precision * recall / max(precision + recall, 1e-9)
        )

        logger.info(
            "Merge accuracy: P=%.4f R=%.4f F1=%.4f (TP=%d FP=%d FN=%d)",
            precision,
            recall,
            f1,
            tp,
            fp,
            fn,
        )

        return MergeAccuracyMetrics(
            total_test_cases=total_test_cases,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            meets_precision_target=precision >= PRECISION_TARGET,
            meets_recall_target=recall >= RECALL_TARGET,
        )
