"""Tests for query expansion cache."""

from __future__ import annotations

from aegis.query.cache import ExpansionCache, ExpansionCacheEntry, ExpansionCacheKey


def test_cache_miss_then_hit() -> None:
    cache = ExpansionCache()
    key = ExpansionCacheKey(raw_query="JAK2 inhibitors", mesh_version="2024")
    assert cache.get(key) is None  # miss

    cache.put(
        key,
        mesh_terms=["Neoplasms"],
        expansion_method="llm",
        low_confidence=False,
    )
    entry = cache.get(key)
    assert entry is not None  # hit
    assert entry.mesh_terms == ["Neoplasms"]

    stats = cache.get_stats()
    assert stats.hit_rate == 0.5


def test_cache_key_hash_deterministic() -> None:
    k1 = ExpansionCacheKey(raw_query="test", mesh_version="2024")
    k2 = ExpansionCacheKey(raw_query="test", mesh_version="2024")
    k3 = ExpansionCacheKey(raw_query="different", mesh_version="2024")
    assert k1.to_hash() == k2.to_hash()
    assert k1.to_hash() != k3.to_hash()


def test_cache_stats() -> None:
    cache = ExpansionCache()
    key_a = ExpansionCacheKey(raw_query="query-a", mesh_version="2024")
    key_b = ExpansionCacheKey(raw_query="query-b", mesh_version="2024")

    cache.put(key_a, mesh_terms=["Term1"], expansion_method="llm", low_confidence=False)

    # 3 hits
    for _ in range(3):
        cache.get(key_a)
    # 1 miss
    cache.get(key_b)

    stats = cache.get_stats()
    assert stats.hits == 3
    assert stats.misses == 1
    assert stats.hit_rate == 0.75


def test_invalidate_single() -> None:
    cache = ExpansionCache()
    key = ExpansionCacheKey(raw_query="query", mesh_version="2024")
    cache.put(key, mesh_terms=["T1"], expansion_method="llm", low_confidence=False)
    assert cache.get(key) is not None
    cache.invalidate(key)
    assert cache.get(key) is None


def test_invalidate_by_mesh_version() -> None:
    cache = ExpansionCache()
    k1 = ExpansionCacheKey(raw_query="q1", mesh_version="2024")
    k2 = ExpansionCacheKey(raw_query="q2", mesh_version="2024")
    k3 = ExpansionCacheKey(raw_query="q3", mesh_version="2025")

    cache.put(k1, mesh_terms=["A"], expansion_method="llm", low_confidence=False)
    cache.put(k2, mesh_terms=["B"], expansion_method="llm", low_confidence=False)
    cache.put(k3, mesh_terms=["C"], expansion_method="llm", low_confidence=False)

    deleted = cache.invalidate_by_mesh_version("2024")
    assert deleted == 2
    # k3 should still exist
    assert cache.get(k3) is not None


def test_clear() -> None:
    cache = ExpansionCache()
    for i in range(3):
        key = ExpansionCacheKey(raw_query=f"q{i}", mesh_version="2024")
        cache.put(
            key,
            mesh_terms=[f"T{i}"],
            expansion_method="llm",
            low_confidence=False,
        )

    cache.clear()
    stats = cache.get_stats()
    assert stats.entry_count == 0
    assert stats.hits == 0
    assert stats.misses == 0


def test_cache_entry_model() -> None:
    entry = ExpansionCacheEntry(
        key_hash="abc123",
        raw_query="test",
        mesh_version="2024",
        mesh_terms=["Neoplasms"],
        expansion_method="llm",
        low_confidence=False,
        cached_at="2024-01-01T00:00:00+00:00",
    )
    data = entry.model_dump_json()
    assert "Neoplasms" in data


def test_overwrite_existing() -> None:
    cache = ExpansionCache()
    key = ExpansionCacheKey(raw_query="query", mesh_version="2024")
    cache.put(key, mesh_terms=["Old"], expansion_method="llm", low_confidence=False)
    cache.put(key, mesh_terms=["New"], expansion_method="metamap", low_confidence=True)

    entry = cache.get(key)
    assert entry is not None
    assert entry.mesh_terms == ["New"]
    assert entry.expansion_method == "metamap"
