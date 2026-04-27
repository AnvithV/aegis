"""Tests for score cache with pluggable backend."""

from __future__ import annotations

from aegis.scoring.cache import (
    CacheBackend,
    CachedScore,
    CacheKey,
    ScoreCache,
    SQLiteCacheBackend,
)


def _make_key(
    uuid: str = "c-001",
    artifact_hash: str = "abc123",
    weight_version: int = 1,
) -> CacheKey:
    return CacheKey(
        candidate_uuid=uuid,
        artifact_set_hash=artifact_hash,
        weight_version=weight_version,
    )


def _make_score(raw: float = 0.75, percentile: float = 0.85) -> CachedScore:
    return CachedScore(
        quality_score_raw=raw,
        quality_percentile=percentile,
        vector_data={"f1_rcr": 0.9, "f2_funding": 0.6},
        cached_at="2026-01-15T12:00:00Z",
    )


def test_put_and_get() -> None:
    """Round-trip a cached score through put/get."""
    cache = ScoreCache(SQLiteCacheBackend())
    key = _make_key()
    score = _make_score()

    cache.put(key, score)
    result = cache.get(key)

    assert result is not None
    assert result.quality_score_raw == score.quality_score_raw
    assert result.quality_percentile == score.quality_percentile
    assert result.vector_data == score.vector_data
    assert result.cached_at == score.cached_at


def test_cache_miss() -> None:
    """Getting a non-existent key returns None."""
    cache = ScoreCache(SQLiteCacheBackend())
    key = _make_key(uuid="nonexistent")

    result = cache.get(key)

    assert result is None


def test_cache_stats() -> None:
    """Stats track hits, misses, and hit rate correctly."""
    cache = ScoreCache(SQLiteCacheBackend())
    key = _make_key()
    score = _make_score()

    # One miss
    cache.get(key)
    # One hit
    cache.put(key, score)
    cache.get(key)

    stats = cache.get_stats()
    assert stats.total_requests == 2
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.hit_rate == 0.5
    assert stats.entry_count == 1


def test_cache_key_isolation() -> None:
    """Different keys do not collide."""
    cache = ScoreCache(SQLiteCacheBackend())
    key_a = _make_key(uuid="a")
    key_b = _make_key(uuid="b")
    score_a = _make_score(raw=0.5)
    score_b = _make_score(raw=0.9)

    cache.put(key_a, score_a)
    cache.put(key_b, score_b)

    result_a = cache.get(key_a)
    result_b = cache.get(key_b)

    assert result_a is not None
    assert result_b is not None
    assert result_a.quality_score_raw == 0.5
    assert result_b.quality_score_raw == 0.9


def test_clear() -> None:
    """Clear removes all entries and resets stats."""
    cache = ScoreCache(SQLiteCacheBackend())
    key = _make_key()
    score = _make_score()

    cache.put(key, score)
    cache.get(key)
    cache.clear()

    assert cache.get(key) is None
    stats = cache.get_stats()
    assert stats.entry_count == 0
    assert stats.total_requests == 1
    assert stats.hits == 0
    assert stats.misses == 1


def test_sqlite_backend() -> None:
    """SQLite backend satisfies the CacheBackend protocol."""
    backend = SQLiteCacheBackend()

    assert isinstance(backend, CacheBackend)
    assert backend.size() == 0

    backend.set("k1", '{"a": 1}')
    assert backend.get("k1") == '{"a": 1}'
    assert backend.size() == 1

    backend.delete("k1")
    assert backend.get("k1") is None
    assert backend.size() == 0


def test_overwrite() -> None:
    """Putting a new value for the same key overwrites the old one."""
    cache = ScoreCache(SQLiteCacheBackend())
    key = _make_key()
    score_v1 = _make_score(raw=0.5)
    score_v2 = _make_score(raw=0.9)

    cache.put(key, score_v1)
    cache.put(key, score_v2)
    result = cache.get(key)

    assert result is not None
    assert result.quality_score_raw == 0.9
    stats = cache.get_stats()
    assert stats.entry_count == 1
