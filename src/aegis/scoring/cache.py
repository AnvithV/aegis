"""Score cache with pluggable backend for v_c and Q(c) results."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class CacheKey(BaseModel):
    """Cache key composed of candidate identity and scoring context."""

    model_config = ConfigDict(frozen=True)

    candidate_uuid: str
    artifact_set_hash: str
    weight_version: int

    def to_string(self) -> str:
        """Serialize to a deterministic string for use as a cache key."""
        return (
            f"{self.candidate_uuid}:"
            f"{self.artifact_set_hash}:"
            f"{self.weight_version}"
        )


class CachedScore(BaseModel):
    """Cached score payload stored alongside a CacheKey."""

    model_config = ConfigDict(frozen=True)

    quality_score_raw: float
    quality_percentile: float
    vector_data: dict[str, float]
    cached_at: str


class CacheStats(BaseModel):
    """Statistics snapshot for cache observability."""

    model_config = ConfigDict(frozen=True)

    total_requests: int
    hits: int
    misses: int
    hit_rate: float
    entry_count: int


@runtime_checkable
class CacheBackend(Protocol):
    """Pluggable storage backend for score caching."""

    def get(self, key: str) -> str | None:
        """Retrieve a JSON-encoded value by key, or None on miss."""
        ...

    def set(self, key: str, value: str) -> None:
        """Store a JSON-encoded value by key."""
        ...

    def delete(self, key: str) -> None:
        """Remove a single entry by key."""
        ...

    def clear(self) -> None:
        """Remove all entries."""
        ...

    def size(self) -> int:
        """Return the number of entries currently stored."""
        ...


class SQLiteCacheBackend:
    """SQLite-backed cache storage."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS score_cache ("
            "cache_key TEXT PRIMARY KEY, "
            "value TEXT, "
            "created_at TEXT)"
        )
        self._conn.commit()

    def get(self, key: str) -> str | None:
        """Retrieve a JSON-encoded value by key, or None on miss."""
        row = self._conn.execute(
            "SELECT value FROM score_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return row[0]  # type: ignore[no-any-return]

    def set(self, key: str, value: str) -> None:
        """Store a JSON-encoded value by key."""
        now = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO score_cache "
            "(cache_key, value, created_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
        self._conn.commit()

    def delete(self, key: str) -> None:
        """Remove a single entry by key."""
        self._conn.execute(
            "DELETE FROM score_cache WHERE cache_key = ?",
            (key,),
        )
        self._conn.commit()

    def clear(self) -> None:
        """Remove all entries."""
        self._conn.execute("DELETE FROM score_cache")
        self._conn.commit()

    def size(self) -> int:
        """Return the number of entries currently stored."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM score_cache"
        ).fetchone()
        assert row is not None
        return int(row[0])


class ScoreCache:
    """High-level score cache with stats tracking and JSON serialization."""

    def __init__(self, backend: CacheBackend) -> None:
        self._backend = backend
        self._hits = 0
        self._misses = 0

    def get(self, key: CacheKey) -> CachedScore | None:
        """Look up a cached score. Returns None on miss."""
        self._hits + self._misses  # total before this request
        raw = self._backend.get(key.to_string())
        if raw is None:
            self._misses += 1
            return None
        self._hits += 1
        return CachedScore.model_validate_json(raw)

    def put(self, key: CacheKey, score: CachedScore) -> None:
        """Store a score in the cache."""
        self._backend.set(key.to_string(), score.model_dump_json())

    def invalidate(self, key: CacheKey) -> None:
        """Invalidate a single cache entry."""
        # TODO: emit invalidation metric
        self._backend.delete(key.to_string())

    def invalidate_by_weight_version(self, weight_version: int) -> None:
        """Invalidate all entries for a given weight version."""
        # TODO: requires backend support for prefix/scan deletion
        _ = weight_version

    def get_stats(self) -> CacheStats:
        """Return a snapshot of cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return CacheStats(
            total_requests=total,
            hits=self._hits,
            misses=self._misses,
            hit_rate=round(hit_rate, 6),
            entry_count=self._backend.size(),
        )

    def clear(self) -> None:
        """Clear all cached entries and reset stats."""
        self._backend.clear()
        self._hits = 0
        self._misses = 0
