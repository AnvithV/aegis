"""Query expansion cache: per-(query, mesh_version) caching of LLM expansions.

Aggressively caches expansion results to minimize LLM costs.
Target: >= 95% hit rate on warmed query populations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ExpansionCacheKey(BaseModel):
    """Cache key composed of raw query and MeSH version."""

    model_config = ConfigDict(frozen=True)

    raw_query: str
    mesh_version: str

    def to_hash(self) -> str:
        """Return SHA-256 hex of the key components."""
        data = f"{self.raw_query}|{self.mesh_version}"
        return hashlib.sha256(data.encode()).hexdigest()


class ExpansionCacheEntry(BaseModel):
    """A cached expansion result."""

    model_config = ConfigDict(frozen=True)

    key_hash: str
    raw_query: str
    mesh_version: str
    mesh_terms: list[str]
    expansion_method: str
    low_confidence: bool
    cached_at: str


class ExpansionCacheStats(BaseModel):
    """Statistics for cache observability."""

    model_config = ConfigDict(frozen=True)

    total_requests: int
    hits: int
    misses: int
    hit_rate: float
    entry_count: int


class ExpansionCache:
    """SQLite-backed query expansion cache."""

    def __init__(self, *, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS expansion_cache ("
            "key_hash TEXT PRIMARY KEY, "
            "mesh_version TEXT, "
            "data TEXT, "
            "created_at TEXT)"
        )
        self._conn.commit()
        self._hits = 0
        self._misses = 0

    def get(self, key: ExpansionCacheKey) -> ExpansionCacheEntry | None:
        """Look up a cached expansion by key. Returns None on miss."""
        key_hash = key.to_hash()
        row = self._conn.execute(
            "SELECT data FROM expansion_cache WHERE key_hash = ?",
            (key_hash,),
        ).fetchone()
        if row is None:
            self._misses += 1
            return None
        self._hits += 1
        return ExpansionCacheEntry.model_validate(json.loads(row[0]))

    def put(
        self,
        key: ExpansionCacheKey,
        *,
        mesh_terms: list[str],
        expansion_method: str,
        low_confidence: bool,
    ) -> None:
        """Store an expansion result in the cache."""
        now = datetime.now(tz=UTC).isoformat()
        key_hash = key.to_hash()
        entry = ExpansionCacheEntry(
            key_hash=key_hash,
            raw_query=key.raw_query,
            mesh_version=key.mesh_version,
            mesh_terms=mesh_terms,
            expansion_method=expansion_method,
            low_confidence=low_confidence,
            cached_at=now,
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO expansion_cache "
            "(key_hash, mesh_version, data, created_at) VALUES (?, ?, ?, ?)",
            (key_hash, key.mesh_version, entry.model_dump_json(), now),
        )
        self._conn.commit()

    def invalidate(self, key: ExpansionCacheKey) -> None:
        """Delete a single cache entry."""
        self._conn.execute(
            "DELETE FROM expansion_cache WHERE key_hash = ?",
            (key.to_hash(),),
        )
        self._conn.commit()

    def invalidate_by_mesh_version(self, mesh_version: str) -> int:
        """Delete all entries for a given mesh_version. Returns count deleted."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM expansion_cache WHERE mesh_version = ?",
            (mesh_version,),
        )
        row = cursor.fetchone()
        count = int(row[0]) if row else 0
        self._conn.execute(
            "DELETE FROM expansion_cache WHERE mesh_version = ?",
            (mesh_version,),
        )
        self._conn.commit()
        return count

    def get_stats(self) -> ExpansionCacheStats:
        """Return cache statistics snapshot."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        row = self._conn.execute(
            "SELECT COUNT(*) FROM expansion_cache"
        ).fetchone()
        entry_count = int(row[0]) if row else 0
        return ExpansionCacheStats(
            total_requests=total,
            hits=self._hits,
            misses=self._misses,
            hit_rate=round(hit_rate, 6),
            entry_count=entry_count,
        )

    def clear(self) -> None:
        """Delete all entries and reset counters."""
        self._conn.execute("DELETE FROM expansion_cache")
        self._conn.commit()
        self._hits = 0
        self._misses = 0
