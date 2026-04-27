"""Tests for soft discount evaluation."""

from __future__ import annotations

from aegis.integrity.soft_discounts import (
    PAPERMILL_PENDING_FLOOR,
    PREDATORY_FLOOR,
    RETRACTION_FLOOR,
    DiscountType,
    SoftDiscounts,
)


def test_clean_candidate_no_discounts() -> None:
    sd = SoftDiscounts()
    result = sd.evaluate(candidate_uuid="c1")
    assert result.combined_factor == 1.0
    assert result.discounts == []


def test_predatory_load_discount() -> None:
    sd = SoftDiscounts()
    result = sd.evaluate(
        candidate_uuid="c2",
        predatory_load=0.5,
    )
    assert len(result.discounts) == 1
    d = result.discounts[0]
    assert d.discount_type == DiscountType.predatory_load
    # load 0.5 -> factor = 1.0 - 0.5*(1-0.5) = 0.75
    assert abs(d.factor - 0.75) < 1e-9


def test_predatory_load_floor_enforced() -> None:
    sd = SoftDiscounts()
    # load 2.0 would give negative without floor
    result = sd.evaluate(
        candidate_uuid="c3",
        predatory_load=2.0,
    )
    d = result.discounts[0]
    assert d.factor == PREDATORY_FLOOR


def test_retraction_discount() -> None:
    sd = SoftDiscounts()
    result = sd.evaluate(
        candidate_uuid="c4",
        out_of_subdomain_retraction_count=3,
    )
    d = result.discounts[0]
    assert d.discount_type == DiscountType.out_of_subdomain_retraction
    # 3 retractions -> factor = 1.0 - 0.3 = 0.7
    assert abs(d.factor - 0.7) < 1e-9


def test_retraction_floor_enforced() -> None:
    sd = SoftDiscounts()
    result = sd.evaluate(
        candidate_uuid="c5",
        out_of_subdomain_retraction_count=20,
    )
    d = result.discounts[0]
    assert d.factor == RETRACTION_FLOOR


def test_papermill_signal() -> None:
    sd = SoftDiscounts()
    result = sd.evaluate(
        candidate_uuid="c6",
        papermill_suspected=True,
    )
    d = result.discounts[0]
    assert d.discount_type == DiscountType.papermill_pending
    assert d.factor == PAPERMILL_PENDING_FLOOR


def test_combined_discounts_multiply() -> None:
    sd = SoftDiscounts()
    result = sd.evaluate(
        candidate_uuid="c7",
        predatory_load=0.5,
        out_of_subdomain_retraction_count=2,
        papermill_suspected=True,
    )
    assert len(result.discounts) == 3
    # 0.75 * 0.8 * 0.7 = 0.42
    expected = 0.75 * 0.8 * PAPERMILL_PENDING_FLOOR
    assert abs(result.combined_factor - expected) < 1e-9


def test_authorship_inconsistency_stub() -> None:
    """Phase 1 stub: no authorship inconsistency discount applied."""
    sd = SoftDiscounts()
    result = sd.evaluate(candidate_uuid="c8")
    discount_types = [d.discount_type for d in result.discounts]
    assert DiscountType.authorship_inconsistency not in discount_types
