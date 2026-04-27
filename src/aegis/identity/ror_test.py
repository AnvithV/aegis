"""Tests for the ROR-normalized affiliation resolver."""

from __future__ import annotations

import time

import pytest

from aegis.identity.ror import RorMatch, RorResolver


@pytest.fixture()
def resolver() -> RorResolver:
    """Create a RorResolver with default alias file."""
    return RorResolver()


def test_exact_alias_match(resolver: RorResolver) -> None:
    """Assert 'MGH' resolves to Massachusetts General Hospital via alias."""
    result = resolver.resolve("MGH")
    assert result is not None
    assert result.canonical_name == "Massachusetts General Hospital"
    assert result.matched_via == "alias"
    assert result.confidence == 1.0
    assert result.ror_id == "https://ror.org/002pd6e78"


def test_fuzzy_match(resolver: RorResolver) -> None:
    """Assert 'Mass General Hosp' resolves with confidence > 0.7."""
    result = resolver.resolve("Mass General Hosp")
    assert result is not None
    assert result.canonical_name == "Massachusetts General Hospital"
    assert result.confidence > 0.7
    assert result.matched_via == "fuzzy"


def test_low_confidence_not_overwritten(resolver: RorResolver) -> None:
    """Assert an unrecognizable string returns a match with low confidence."""
    result = resolver.resolve("Xyzzy Quantum Biodynamics Lab")
    assert result is not None
    assert result.confidence < 0.7
    assert result.matched_via == "fuzzy-low"


def test_parent_org_resolution(resolver: RorResolver) -> None:
    """Assert MGH returns parent org info."""
    result = resolver.resolve("Massachusetts General Hospital")
    assert result is not None
    assert result.parent_ror_id is not None
    assert result.parent_name == "Mass General Brigham"


def test_cache_hit(resolver: RorResolver) -> None:
    """Resolve same string twice, assert second call benefits from cache."""
    query = "Massachusetts General Hospital"
    # Warm the cache
    r1 = resolver.resolve(query)

    # Time many iterations to get measurable difference
    start = time.perf_counter_ns()
    for _ in range(1000):
        r2 = resolver.resolve(query)
    cached_ns = time.perf_counter_ns() - start

    assert r1 == r2
    # Cache hit should be fast: < 1ms per call on average
    assert cached_ns / 1000 < 1_000_000  # < 1ms per call


def test_batch_resolve(resolver: RorResolver) -> None:
    """Resolve 10 strings in batch, assert results match individual resolves."""
    queries = [
        "MGH",
        "HMS",
        "Stanford",
        "Mayo",
        "NIH",
        "UCSF",
        "Yale",
        "Duke",
        "Oxford",
        "RIKEN",
    ]
    batch_results = resolver.resolve_batch(queries)
    individual_results = [resolver.resolve(q) for q in queries]

    assert len(batch_results) == len(queries)
    for batch_r, indiv_r in zip(batch_results, individual_results):
        assert batch_r == indiv_r


def test_abbreviation_expansion(resolver: RorResolver) -> None:
    """Assert 'Harvard Med School' expands to match Harvard Medical School."""
    result = resolver.resolve("Harvard Med School")
    assert result is not None
    assert result.canonical_name == "Harvard Medical School"
    assert result.confidence > 0.7


def test_exact_name_match(resolver: RorResolver) -> None:
    """Exact canonical name should resolve with confidence 1.0."""
    result = resolver.resolve("Johns Hopkins University")
    assert result is not None
    assert result.canonical_name == "Johns Hopkins University"
    assert result.confidence == 1.0
    assert result.matched_via == "exact"


def test_case_insensitive(resolver: RorResolver) -> None:
    """Resolution should be case-insensitive."""
    result = resolver.resolve("johns hopkins university")
    assert result is not None
    assert result.canonical_name == "Johns Hopkins University"
    assert result.confidence == 1.0


def test_empty_string(resolver: RorResolver) -> None:
    """Empty string should return None."""
    assert resolver.resolve("") is None
    assert resolver.resolve("   ") is None


def test_ror_match_frozen() -> None:
    """RorMatch should be immutable (frozen)."""
    match = RorMatch(
        ror_id="https://ror.org/test",
        canonical_name="Test",
        parent_ror_id=None,
        parent_name=None,
        country="US",
        confidence=0.9,
        matched_via="exact",
    )
    with pytest.raises(Exception):  # noqa: B017
        match.confidence = 0.5
