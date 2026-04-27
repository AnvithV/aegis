"""Tests for Phase 2e observability modules."""

from __future__ import annotations

from datetime import date

from aegis.observability.clinician_coverage import ClinicianCoverageDashboard
from aegis.observability.merge_accuracy import MergeAccuracyTracker
from aegis.observability.reassignment_metrics import ReassignmentMetrics
from aegis.observability.signal_balance import SignalBalanceDashboard
from aegis.observability.specialty_dist import SpecialtyDistDashboard

# --- Specialty Distribution Tests ---


def test_specialty_dist_basic() -> None:
    """Basic specialty distribution with clear primary specialties."""
    dashboard = SpecialtyDistDashboard()
    candidates = [
        {"uuid1": {"oncology": 0.8, "cardiology": 0.1, "neurology": 0.1}},
        {"uuid2": {"oncology": 0.7, "cardiology": 0.2, "neurology": 0.1}},
        {"uuid3": {"cardiology": 0.9, "oncology": 0.05, "neurology": 0.05}},
    ]
    metrics = dashboard.compute(candidates)
    assert metrics.total_candidates == 3
    assert metrics.per_specialty_count["oncology"] == 2
    assert metrics.per_specialty_count["cardiology"] == 1
    assert metrics.multi_specialty_count == 0


def test_specialty_dist_multi_specialty() -> None:
    """Candidates with multiple specialties above 0.2 threshold."""
    dashboard = SpecialtyDistDashboard()
    candidates = [
        {"uuid1": {"oncology": 0.5, "cardiology": 0.3, "neurology": 0.2}},
        {"uuid2": {"oncology": 0.4, "cardiology": 0.35, "neurology": 0.25}},
    ]
    metrics = dashboard.compute(candidates)
    assert metrics.total_candidates == 2
    # uuid1: oncology(0.5) and cardiology(0.3) above 0.2 => multi
    # uuid2: all three above 0.2 => multi
    assert metrics.multi_specialty_count == 2
    assert metrics.multi_specialty_pct == 100.0


# --- Reassignment Metrics Tests ---


def test_reassignment_rate_alert() -> None:
    """Alert fires when reassignment rate exceeds 5% threshold."""
    tracker = ReassignmentMetrics()
    metrics = tracker.record_run(
        run_date=date(2025, 1, 15),
        total_candidates=100,
        reassigned_count=10,
        major_changes=3,
    )
    assert metrics.reassignment_rate == 0.1
    assert metrics.alert_triggered is True
    assert metrics.alert_message is not None
    assert "exceeds threshold" in metrics.alert_message


def test_reassignment_stability() -> None:
    """Stability check passes when all runs below threshold."""
    tracker = ReassignmentMetrics()
    for day in range(1, 8):
        tracker.record_run(
            run_date=date(2025, 1, day),
            total_candidates=1000,
            reassigned_count=10,  # 1% rate, below 5%
            major_changes=0,
        )
    assert tracker.check_stability(window=7) is True

    # Add a high-churn run
    tracker.record_run(
        run_date=date(2025, 1, 8),
        total_candidates=100,
        reassigned_count=20,  # 20% rate
        major_changes=5,
    )
    assert tracker.check_stability(window=7) is False


# --- Signal Balance Tests ---


def test_signal_balance_candidate() -> None:
    """Single candidate signal contribution proportions."""
    dashboard = SignalBalanceDashboard()
    metrics = dashboard.compute_candidate(
        candidate_uuid="uuid1",
        paper_mesh_count=50,
        patent_mesh_count=30,
        trial_mesh_count=10,
        grant_mesh_count=10,
    )
    assert metrics.total_mesh_terms == 100
    assert metrics.paper_contribution == 0.5
    assert metrics.patent_contribution == 0.3
    assert metrics.trial_contribution == 0.1
    assert metrics.grant_contribution == 0.1


def test_signal_balance_cohort_alert() -> None:
    """Cohort alert fires when mean patent contribution >= 90%."""
    dashboard = SignalBalanceDashboard()
    candidates = [
        dashboard.compute_candidate("u1", 1, 90, 5, 4),
        dashboard.compute_candidate("u2", 2, 95, 1, 2),
        dashboard.compute_candidate("u3", 0, 98, 1, 1),
    ]
    cohort = dashboard.compute_cohort(candidates)
    assert cohort.alert_triggered is True
    assert cohort.alert_message is not None
    assert "dominance" in cohort.alert_message
    assert cohort.patent_dominant_count == 3


# --- Clinician Coverage Tests ---


def test_clinician_coverage_basic() -> None:
    """Basic clinician coverage metrics computation."""
    dashboard = ClinicianCoverageDashboard()
    clinicians: list[dict[str, bool | str | None]] = [
        {
            "has_candidate_uuid": True,
            "has_abms": True,
            "has_state_board": True,
            "has_hospital_tier": True,
            "has_publications": True,
            "practice_state": "CA",
        },
        {
            "has_candidate_uuid": True,
            "has_abms": True,
            "has_state_board": False,
            "has_hospital_tier": False,
            "has_publications": True,
            "practice_state": "NY",
        },
    ]
    metrics = dashboard.compute(clinicians)
    assert metrics.total_clinicians == 2
    assert metrics.npi_crosslinked_pct == 100.0
    assert metrics.abms_coverage_pct == 100.0
    assert "CA" in metrics.covered_states
    assert "NY" in metrics.covered_states


def test_clinician_gap_states() -> None:
    """States not in COVERED_STATES appear as gap states."""
    dashboard = ClinicianCoverageDashboard()
    clinicians: list[dict[str, bool | str | None]] = [
        {
            "has_candidate_uuid": True,
            "has_abms": True,
            "has_state_board": True,
            "has_hospital_tier": True,
            "has_publications": True,
            "practice_state": "WY",
        },
    ]
    metrics = dashboard.compute(clinicians)
    assert "WY" in metrics.gap_states
    assert "WY" not in metrics.covered_states


def test_clinician_low_publication_caveat() -> None:
    """Caveat added when publication rate is below 30%."""
    dashboard = ClinicianCoverageDashboard()
    clinicians: list[dict[str, bool | str | None]] = [
        {
            "has_candidate_uuid": True,
            "has_abms": True,
            "has_state_board": True,
            "has_hospital_tier": True,
            "has_publications": False,
            "practice_state": "CA",
        }
        for _ in range(10)
    ]
    # 1 with publications out of 11
    clinicians.append(
        {
            "has_candidate_uuid": True,
            "has_abms": True,
            "has_state_board": True,
            "has_hospital_tier": True,
            "has_publications": True,
            "practice_state": "CA",
        }
    )
    metrics = dashboard.compute(clinicians)
    assert any("publication" in c.lower() for c in metrics.coverage_caveats)


# --- Merge Accuracy Tests ---


def test_merge_accuracy_perfect() -> None:
    """Perfect predictions yield precision=1.0, recall=1.0."""
    tracker = MergeAccuracyTracker()
    pairs = [(f"a{i}", f"b{i}", True) for i in range(50)]
    pairs += [(f"a{i}", f"b{i}", False) for i in range(50, 100)]
    metrics = tracker.evaluate(pairs, pairs)
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1_score == 1.0
    assert metrics.meets_precision_target is True
    assert metrics.meets_recall_target is True


def test_merge_accuracy_with_errors() -> None:
    """Predictions with errors show reduced precision and recall."""
    tracker = MergeAccuracyTracker()
    ground_truth = [
        ("a1", "b1", True),
        ("a2", "b2", True),
        ("a3", "b3", False),
        ("a4", "b4", False),
    ]
    predictions = [
        ("a1", "b1", True),   # TP
        ("a2", "b2", False),  # FN (missed match)
        ("a3", "b3", True),   # FP (false match)
        ("a4", "b4", False),  # TN
    ]
    metrics = tracker.evaluate(predictions, ground_truth)
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5


def test_merge_precision_target() -> None:
    """Precision target check with high-precision predictions."""
    tracker = MergeAccuracyTracker()
    # 100 true matches, all correctly predicted
    predictions = [(f"a{i}", f"b{i}", True) for i in range(100)]
    ground_truth = [(f"a{i}", f"b{i}", True) for i in range(100)]
    metrics = tracker.evaluate(predictions, ground_truth)
    assert metrics.precision >= 0.99
    assert metrics.meets_precision_target is True
