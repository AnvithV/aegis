"""Tests for steady-state weight relearning."""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from aegis.learning.cold_start_guard import GuardVerdict
from aegis.learning.downstream_quality import (
    DownstreamQualityStore,
    TaskOutcome,
    TaskOutcomeCandidate,
)
from aegis.learning.plackett_luce import JudgmentRecord
from aegis.learning.refit_steady_state import (
    RefitReport,
    SteadyStateConfig,
    SteadyStateRefitter,
)
from aegis.scoring.quality_prior import WeightVector


def _write_audit_judgments(path: Path, n: int = 30) -> None:
    rng = random.Random(42)
    with open(path, "w", encoding="utf-8") as fh:
        for _ in range(n):
            record = {
                "winner_scores": {
                    "quality_prior": rng.uniform(0.1, 1.0),
                    "topical_fit": rng.uniform(0.1, 1.0),
                    "recency": rng.uniform(0.1, 1.0),
                },
                "loser_scores": {
                    "quality_prior": rng.uniform(0.1, 1.0),
                    "topical_fit": rng.uniform(0.1, 1.0),
                    "recency": rng.uniform(0.1, 1.0),
                },
            }
            fh.write(json.dumps(record) + "\n")


def _write_downstream_outcomes(
    store: DownstreamQualityStore, n: int = 20
) -> None:
    rng = random.Random(99)
    for i in range(n):
        candidates = [
            TaskOutcomeCandidate(
                candidate_uuid=f"cand-{i}-{j}",
                candidate_rank=j + 1,
                quality_prior_score=rng.uniform(0.1, 1.0),
                topical_fit_score=rng.uniform(0.1, 1.0),
                recency_score=rng.uniform(0.1, 1.0),
            )
            for j in range(3)
        ]
        outcome = TaskOutcome(
            task_id=f"task-{i}",
            query_specialty="translational",
            query_mesh_terms=["Neoplasms", "Drug Therapy"],
            candidates=candidates,
            fleiss_kappa=rng.uniform(0.3, 0.9),
            accept_rate=rng.uniform(0.5, 1.0),
            consensus_rate=rng.uniform(0.6, 1.0),
            submitted_at=datetime(2026, 4, 26),
            metadata={},
        )
        store.append(outcome=outcome)


def _make_weight_yaml(weights_dir: Path) -> Path:
    """Write a translational_v1.yaml and return the path."""
    data = {
        "version": 1,
        "specialty": "translational",
        "created": "2026-04-26",
        "weights": {
            "f1_rcr": 0.35,
            "f2_funding": 0.25,
            "f3_leadership": 0.20,
            "f4_apex": 0.05,
            "f5_translational": 0.10,
            "f6_lineage": 0.05,
        },
        "exponents": {
            "alpha": 0.7,
            "beta": 1.0,
            "gamma": 0.4,
        },
        "exponent_bounds": {
            "alpha": [0.3, 1.2],
            "beta": [0.5, 1.5],
            "gamma": [0.1, 0.8],
        },
    }
    weights_dir.mkdir(parents=True, exist_ok=True)
    path = weights_dir / "translational_v1.yaml"
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False)
    return path


def _make_weight_vector() -> WeightVector:
    return WeightVector(
        version=1,
        specialty="translational",
        weights={
            "f1_rcr": 0.35,
            "f2_funding": 0.25,
            "f3_leadership": 0.20,
            "f4_apex": 0.05,
            "f5_translational": 0.10,
            "f6_lineage": 0.05,
        },
        exponents={"alpha": 0.7, "beta": 1.0, "gamma": 0.4},
        exponent_bounds={
            "alpha": [0.3, 1.2],
            "beta": [0.5, 1.5],
            "gamma": [0.1, 0.8],
        },
    )


def _make_refitter(
    tmp_path: Path,
    *,
    n_audit: int = 30,
    n_downstream: int = 20,
    config: SteadyStateConfig | None = None,
) -> SteadyStateRefitter:
    """Create a fully wired SteadyStateRefitter for testing."""
    weights_dir = tmp_path / "weights"
    _make_weight_yaml(weights_dir)

    audit_path = tmp_path / "audit_judgments.jsonl"
    _write_audit_judgments(audit_path, n=n_audit)

    downstream_path = tmp_path / "downstream.jsonl"
    downstream_store = DownstreamQualityStore(storage_path=downstream_path)
    _write_downstream_outcomes(downstream_store, n=n_downstream)

    return SteadyStateRefitter(
        weights_dir=weights_dir,
        audit_judgments_path=audit_path,
        downstream_store_path=downstream_path,
        config=config,
    )


def test_steady_state_config_defaults() -> None:
    """Verify SteadyStateConfig() has expected defaults."""
    config = SteadyStateConfig()
    assert config.auto_deploy_threshold == 0.05
    assert config.min_downstream_count == 50
    assert config.downstream_weight_multiplier == 1.5
    assert config.min_judgments_per_specialty == 20
    assert config.ci_threshold == 0.2


def test_merge_judgments_no_oversample(tmp_path: Path) -> None:
    """10 audit + 10 downstream (below min=50) produces 20 total."""
    refitter = _make_refitter(tmp_path, n_audit=0, n_downstream=0)
    audit = [
        JudgmentRecord(
            winner_scores={"quality_prior": 0.8, "topical_fit": 0.7, "recency": 0.6},
            loser_scores={"quality_prior": 0.3, "topical_fit": 0.2, "recency": 0.1},
        )
        for _ in range(10)
    ]
    downstream = [
        JudgmentRecord(
            winner_scores={"quality_prior": 0.9, "topical_fit": 0.8, "recency": 0.7},
            loser_scores={"quality_prior": 0.4, "topical_fit": 0.3, "recency": 0.2},
        )
        for _ in range(10)
    ]
    merged, breakdown = refitter._merge_judgments(
        audit=audit, downstream=downstream
    )
    assert len(merged) == 20
    assert breakdown.audit_panel_count == 10
    assert breakdown.downstream_count == 10
    assert breakdown.downstream_weight_multiplier == 1.0
    assert breakdown.total_effective_count == 20


def test_merge_judgments_with_oversample(tmp_path: Path) -> None:
    """10 audit + 60 downstream (above min=50) with multiplier=1.5."""
    refitter = _make_refitter(tmp_path, n_audit=0, n_downstream=0)
    audit = [
        JudgmentRecord(
            winner_scores={"quality_prior": 0.8, "topical_fit": 0.7, "recency": 0.6},
            loser_scores={"quality_prior": 0.3, "topical_fit": 0.2, "recency": 0.1},
        )
        for _ in range(10)
    ]
    downstream = [
        JudgmentRecord(
            winner_scores={"quality_prior": 0.9, "topical_fit": 0.8, "recency": 0.7},
            loser_scores={"quality_prior": 0.4, "topical_fit": 0.3, "recency": 0.2},
        )
        for _ in range(60)
    ]
    merged, breakdown = refitter._merge_judgments(
        audit=audit, downstream=downstream
    )
    # round(1.5) = 2, so 60 * 2 = 120 downstream + 10 audit = 130
    assert len(merged) == 130
    assert breakdown.audit_panel_count == 10
    assert breakdown.downstream_count == 60
    assert breakdown.downstream_weight_multiplier == 1.5
    assert breakdown.total_effective_count == 130


def test_deployment_decision_auto_deploy(tmp_path: Path) -> None:
    """Small deltas trigger auto_deploy."""
    refitter = _make_refitter(tmp_path, n_audit=0, n_downstream=0)
    prior = {"alpha": 0.7, "beta": 1.0, "gamma": 0.4}
    new = {"alpha": 0.72, "beta": 1.01, "gamma": 0.41}
    decision = refitter._compute_deployment_decision(
        prior_exponents=prior, new_exponents=new
    )
    assert decision.action == "auto_deploy"


def test_deployment_decision_manual_gate(tmp_path: Path) -> None:
    """Large delta triggers manual_gate."""
    refitter = _make_refitter(tmp_path, n_audit=0, n_downstream=0)
    prior = {"alpha": 0.7, "beta": 1.0, "gamma": 0.4}
    new = {"alpha": 0.8, "beta": 1.0, "gamma": 0.4}
    decision = refitter._compute_deployment_decision(
        prior_exponents=prior, new_exponents=new
    )
    assert decision.action == "manual_gate"


def test_run_produces_refit_report(tmp_path: Path) -> None:
    """Full integration test: run produces a valid RefitReport."""
    refitter = _make_refitter(tmp_path, n_audit=30, n_downstream=20)
    wv = _make_weight_vector()

    report = refitter.run(specialty="translational", current_weights=wv)

    assert isinstance(report, RefitReport)
    assert report.source_breakdown.audit_panel_count == 30
    assert report.source_breakdown.downstream_count > 0
    assert report.deployment_decision.action in (
        "auto_deploy",
        "manual_gate",
        "blocked",
    )
    assert "alpha" in report.new_exponents
    assert "beta" in report.new_exponents
    assert "gamma" in report.new_exponents
    assert isinstance(report.guard_verdict, GuardVerdict)


def test_run_auto_deploys_yaml(tmp_path: Path) -> None:
    """With high threshold, any fit auto-deploys; verify YAML written."""
    config = SteadyStateConfig(auto_deploy_threshold=1.0)
    refitter = _make_refitter(
        tmp_path, n_audit=30, n_downstream=20, config=config
    )
    wv = _make_weight_vector()

    report = refitter.run(specialty="translational", current_weights=wv)

    weights_dir = tmp_path / "weights"
    # Should have the original v1 + new v2
    yamls = list(weights_dir.glob("translational_v*.yaml"))
    if report.deployment_decision.action == "auto_deploy":
        assert len(yamls) >= 2
    # If guard blocked, no new file written
    elif report.deployment_decision.action == "blocked":
        assert len(yamls) >= 1


def test_run_manual_gate_stages(tmp_path: Path) -> None:
    """With very low threshold, any change triggers manual gate; verify staging."""
    config = SteadyStateConfig(auto_deploy_threshold=0.001)
    refitter = _make_refitter(
        tmp_path, n_audit=30, n_downstream=20, config=config
    )
    wv = _make_weight_vector()

    report = refitter.run(specialty="translational", current_weights=wv)

    weights_dir = tmp_path / "weights"
    staging_dir = weights_dir / "staging"

    if report.deployment_decision.action == "manual_gate":
        staged = list(staging_dir.glob("*_pending.yaml"))
        assert len(staged) >= 1
    elif report.deployment_decision.action == "blocked":
        # Guard blocked takes priority
        pass


def test_run_blocked_when_guard_rejects(tmp_path: Path) -> None:
    """With only 5 audit judgments and 0 downstream, guard blocks."""
    config = SteadyStateConfig(ci_threshold=0.0001)
    refitter = _make_refitter(
        tmp_path, n_audit=5, n_downstream=0, config=config
    )
    wv = _make_weight_vector()

    report = refitter.run(specialty="translational", current_weights=wv)

    assert report.deployment_decision.action == "blocked"


def test_synthetic_feedback_loop(tmp_path: Path) -> None:
    """Feed 100 outcomes where quality_prior correlates with task quality.

    Verify the fitter doesn't drive alpha to the floor.
    """
    weights_dir = tmp_path / "weights"
    _make_weight_yaml(weights_dir)

    # Write audit judgments where winners have higher quality_prior
    audit_path = tmp_path / "audit_judgments.jsonl"
    rng = random.Random(42)
    with open(audit_path, "w", encoding="utf-8") as fh:
        for _ in range(50):
            # Winner has systematically higher quality_prior
            record = {
                "winner_scores": {
                    "quality_prior": rng.uniform(0.6, 1.0),
                    "topical_fit": rng.uniform(0.3, 0.7),
                    "recency": rng.uniform(0.3, 0.7),
                },
                "loser_scores": {
                    "quality_prior": rng.uniform(0.1, 0.5),
                    "topical_fit": rng.uniform(0.3, 0.7),
                    "recency": rng.uniform(0.3, 0.7),
                },
            }
            fh.write(json.dumps(record) + "\n")

    # Write 100 downstream outcomes where candidates with higher
    # quality_prior_score tend to produce higher fleiss_kappa
    downstream_path = tmp_path / "downstream.jsonl"
    downstream_store = DownstreamQualityStore(storage_path=downstream_path)
    rng2 = random.Random(123)
    for i in range(100):
        # 3 candidates: quality_prior correlates with task quality
        candidates = []
        for j in range(3):
            qp = rng2.uniform(0.1, 1.0)
            candidates.append(
                TaskOutcomeCandidate(
                    candidate_uuid=f"cand-{i}-{j}",
                    candidate_rank=j + 1,
                    quality_prior_score=qp,
                    topical_fit_score=rng2.uniform(0.3, 0.7),
                    recency_score=rng2.uniform(0.3, 0.7),
                )
            )
        # fleiss_kappa positively correlated with avg quality_prior
        avg_qp = sum(c.quality_prior_score for c in candidates) / len(
            candidates
        )
        kappa = min(1.0, max(-1.0, avg_qp + rng2.uniform(-0.1, 0.1)))

        outcome = TaskOutcome(
            task_id=f"synth-{i}",
            query_specialty="translational",
            query_mesh_terms=["Neoplasms"],
            candidates=candidates,
            fleiss_kappa=kappa,
            accept_rate=rng2.uniform(0.5, 1.0),
            consensus_rate=rng2.uniform(0.5, 1.0),
            submitted_at=datetime(2026, 4, 26),
            metadata={},
        )
        downstream_store.append(outcome=outcome)

    config = SteadyStateConfig(
        auto_deploy_threshold=1.0,
        min_downstream_count=50,
    )
    refitter = SteadyStateRefitter(
        weights_dir=weights_dir,
        audit_judgments_path=audit_path,
        downstream_store_path=downstream_path,
        config=config,
    )
    wv = _make_weight_vector()

    report = refitter.run(specialty="translational", current_weights=wv)

    # The fitter should not drive alpha to the absolute lower bound (0.3)
    # since quality_prior is positively correlated with task quality
    assert report.new_exponents["alpha"] > 0.3
    assert isinstance(report, RefitReport)
