"""CPC cross-walk cache: SQLite-backed caching with version-keyed invalidation."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aegis.storage.schema import MeshDescriptor

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_PATH = Path("data/aegis/cpc_xwalk_cache.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS cpc_cache (
    cpc_code TEXT NOT NULL,
    version TEXT NOT NULL,
    mesh_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cpc_code, version)
);
"""


class CacheStats(BaseModel):
    """Cache performance statistics."""

    model_config = ConfigDict(frozen=True)

    total_entries: int
    version: str
    hit_count: int
    miss_count: int
    hit_rate: float


class CpcXwalkCache:
    """SQLite-backed cache for CPC-to-MeSH cross-walk lookups.

    Cache invalidation: on version bump (quarterly), old entries
    are retained but lookups use the current version only.
    """

    def __init__(
        self,
        cache_path: Path | None = None,
        version: str = "v1",
    ) -> None:
        self._path = cache_path or _DEFAULT_CACHE_PATH
        self._version = version
        self._hits = 0
        self._misses = 0
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute("PRAGMA journal_mode=WAL")

    def get(
        self, cpc_code: str
    ) -> list[tuple[MeshDescriptor, float]] | None:
        """Look up cached CPC-to-MeSH translation.

        Returns None on cache miss.
        """
        cursor = self._conn.execute(
            "SELECT mesh_json FROM cpc_cache WHERE cpc_code = ? AND version = ?",
            (cpc_code, self._version),
        )
        row = cursor.fetchone()
        if row is None:
            self._misses += 1
            return None

        self._hits += 1
        return self._deserialize(row[0])

    def put(
        self,
        cpc_code: str,
        mappings: list[tuple[MeshDescriptor, float]],
    ) -> None:
        """Cache a CPC-to-MeSH translation result."""
        mesh_json = self._serialize(mappings)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO cpc_cache (cpc_code, version, mesh_json)
            VALUES (?, ?, ?)
            """,
            (cpc_code, self._version, mesh_json),
        )
        self._conn.commit()

    def put_batch(
        self,
        entries: list[tuple[str, list[tuple[MeshDescriptor, float]]]],
    ) -> int:
        """Batch insert cache entries. Returns count inserted."""
        for cpc_code, mappings in entries:
            mesh_json = self._serialize(mappings)
            self._conn.execute(
                """
                INSERT OR REPLACE INTO cpc_cache (cpc_code, version, mesh_json)
                VALUES (?, ?, ?)
                """,
                (cpc_code, self._version, mesh_json),
            )
        self._conn.commit()
        return len(entries)

    def invalidate_version(self, old_version: str) -> int:
        """Delete all entries for an old version. Returns count deleted."""
        cursor = self._conn.execute(
            "DELETE FROM cpc_cache WHERE version = ?",
            (old_version,),
        )
        self._conn.commit()
        return cursor.rowcount

    def stats(self) -> CacheStats:
        """Return cache performance statistics."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM cpc_cache WHERE version = ?",
            (self._version,),
        )
        total = cursor.fetchone()[0]
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        return CacheStats(
            total_entries=total,
            version=self._version,
            hit_count=self._hits,
            miss_count=self._misses,
            hit_rate=round(hit_rate, 4),
        )

    def close(self) -> None:
        """Close the SQLite connection."""
        self._conn.close()

    @staticmethod
    def _serialize(
        mappings: list[tuple[MeshDescriptor, float]],
    ) -> str:
        """Serialize MeSH mappings to JSON string."""
        return json.dumps([
            {
                "descriptor": m.descriptor,
                "qualifier": m.qualifier,
                "major_topic": m.major_topic,
                "weight": w,
            }
            for m, w in mappings
        ])

    @staticmethod
    def _deserialize(
        mesh_json: str,
    ) -> list[tuple[MeshDescriptor, float]]:
        """Deserialize JSON string to MeSH mappings."""
        data = json.loads(mesh_json)
        return [
            (
                MeshDescriptor(
                    descriptor=item["descriptor"],
                    qualifier=item.get("qualifier"),
                    major_topic=item.get("major_topic", False),
                ),
                item["weight"],
            )
            for item in data
        ]
