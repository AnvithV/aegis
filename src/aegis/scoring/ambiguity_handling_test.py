"""Tests for specialty-classifier ambiguity handling."""

from __future__ import annotations

from aegis.scoring.ambiguity_handling import AmbiguityHandler, DualRankResult


class TestAmbiguityHandler:
    """Tests for AmbiguityHandler dual-ranking logic."""

    def test_high_confidence_single_rank(self) -> None:
        """Confidence 0.85 -> not ambiguous, single rank."""
        handler = AmbiguityHandler()
        result = handler.evaluate(
            candidate_uuid="uuid-001",
            specialty_probabilities={
                "translational": 0.85,
                "drug_discovery": 0.10,
                "clinician": 0.05,
            },
            score_under_specialty={
                "translational": 0.92,
                "drug_discovery": 0.45,
                "clinician": 0.30,
            },
        )

        assert isinstance(result, DualRankResult)
        assert not result.is_ambiguous
        assert result.primary_specialty == "translational"
        assert result.primary_rank_percentile == 0.92
        assert result.secondary_specialty is None
        assert result.secondary_rank_percentile is None
        assert result.confidence == 0.85

    def test_low_confidence_dual_rank(self) -> None:
        """Confidence 0.45 -> ambiguous, dual rank."""
        handler = AmbiguityHandler()
        result = handler.evaluate(
            candidate_uuid="uuid-002",
            specialty_probabilities={
                "translational": 0.45,
                "drug_discovery": 0.35,
                "clinician": 0.20,
            },
            score_under_specialty={
                "translational": 0.80,
                "drug_discovery": 0.65,
                "clinician": 0.30,
            },
        )

        assert result.is_ambiguous
        assert result.primary_specialty == "translational"
        assert result.primary_rank_percentile == 0.80
        assert result.secondary_specialty == "drug_discovery"
        assert result.secondary_rank_percentile == 0.65
        assert result.confidence == 0.45

    def test_threshold_boundary(self) -> None:
        """Exactly 0.6 confidence -> not ambiguous."""
        handler = AmbiguityHandler()
        result = handler.evaluate(
            candidate_uuid="uuid-003",
            specialty_probabilities={
                "drug_discovery": 0.6,
                "translational": 0.3,
                "clinician": 0.1,
            },
            score_under_specialty={
                "drug_discovery": 0.75,
                "translational": 0.50,
                "clinician": 0.20,
            },
        )

        assert not result.is_ambiguous
        assert result.primary_specialty == "drug_discovery"
        assert result.confidence == 0.6

    def test_empty_probabilities(self) -> None:
        """No data -> ambiguous, default translational."""
        handler = AmbiguityHandler()
        result = handler.evaluate(
            candidate_uuid="uuid-004",
            specialty_probabilities={},
            score_under_specialty={"translational": 0.50},
        )

        assert result.is_ambiguous
        assert result.primary_specialty == "translational"
        assert result.primary_rank_percentile == 0.50
        assert result.confidence == 0.0
        assert "defaulting to translational" in result.recommendation.lower()

    def test_dual_rank_both_scores(self) -> None:
        """Verify both primary and secondary scores populated for ambiguous."""
        handler = AmbiguityHandler()
        result = handler.evaluate(
            candidate_uuid="uuid-005",
            specialty_probabilities={
                "clinician": 0.40,
                "translational": 0.35,
                "drug_discovery": 0.25,
            },
            score_under_specialty={
                "clinician": 0.88,
                "translational": 0.72,
                "drug_discovery": 0.55,
            },
        )

        assert result.is_ambiguous
        assert result.primary_specialty == "clinician"
        assert result.primary_rank_percentile == 0.88
        assert result.secondary_specialty == "translational"
        assert result.secondary_rank_percentile == 0.72

    def test_recommendation_text(self) -> None:
        """High confidence -> 'High-confidence...' recommendation text."""
        handler = AmbiguityHandler()
        result = handler.evaluate(
            candidate_uuid="uuid-006",
            specialty_probabilities={
                "clinician": 0.90,
                "translational": 0.07,
                "drug_discovery": 0.03,
            },
            score_under_specialty={
                "clinician": 0.95,
            },
        )

        assert not result.is_ambiguous
        assert result.recommendation.startswith("High-confidence")
        assert "clinician" in result.recommendation
