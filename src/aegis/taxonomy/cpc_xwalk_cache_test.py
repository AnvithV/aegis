"""Tests for CPC cross-walk cache."""

from __future__ import annotations

import time
from pathlib import Path

from aegis.storage.schema import MeshDescriptor
from aegis.taxonomy.cpc_xwalk_cache import CpcXwalkCache


def _make_mappings(
    n: int = 1,
) -> list[tuple[MeshDescriptor, float]]:
    """Helper to create test MeSH mappings."""
    return [
        (
            MeshDescriptor(
                descriptor=f"Descriptor {i}",
                qualifier=f"Q{i}" if i % 2 == 0 else None,
                major_topic=i % 3 == 0,
            ),
            round(0.5 + i * 0.1, 2),
        )
        for i in range(n)
    ]


def test_put_and_get(tmp_path: Path) -> None:
    """Put a CPC mapping, get it back, verify equality."""
    cache = CpcXwalkCache(cache_path=tmp_path / "cache.db")
    mappings = _make_mappings(3)
    cache.put("A61K31/00", mappings)

    result = cache.get("A61K31/00")
    assert result is not None
    assert len(result) == 3
    for (orig_md, orig_w), (cached_md, cached_w) in zip(mappings, result):
        assert cached_md.descriptor == orig_md.descriptor
        assert cached_md.qualifier == orig_md.qualifier
        assert cached_md.major_topic == orig_md.major_topic
        assert cached_w == orig_w
    cache.close()


def test_cache_miss(tmp_path: Path) -> None:
    """Get a non-existent CPC code, verify returns None."""
    cache = CpcXwalkCache(cache_path=tmp_path / "cache.db")
    result = cache.get("Z99Z99/99")
    assert result is None
    cache.close()


def test_version_isolation(tmp_path: Path) -> None:
    """Put with version v1, get with version v2, verify miss."""
    cache_v1 = CpcXwalkCache(cache_path=tmp_path / "cache.db", version="v1")
    cache_v1.put("A61K31/00", _make_mappings(2))
    cache_v1.close()

    cache_v2 = CpcXwalkCache(cache_path=tmp_path / "cache.db", version="v2")
    result = cache_v2.get("A61K31/00")
    assert result is None
    cache_v2.close()


def test_invalidate_version(tmp_path: Path) -> None:
    """Put entries for v1, invalidate v1, verify all deleted."""
    cache = CpcXwalkCache(cache_path=tmp_path / "cache.db", version="v1")
    for i in range(5):
        cache.put(f"CPC{i}", _make_mappings(1))

    deleted = cache.invalidate_version("v1")
    assert deleted == 5

    for i in range(5):
        assert cache.get(f"CPC{i}") is None
    cache.close()


def test_batch_insert(tmp_path: Path) -> None:
    """Put 100 entries in batch, verify all retrievable."""
    cache = CpcXwalkCache(cache_path=tmp_path / "cache.db")
    entries = [(f"CPC{i:04d}", _make_mappings(2)) for i in range(100)]

    count = cache.put_batch(entries)
    assert count == 100

    for cpc_code, expected in entries:
        result = cache.get(cpc_code)
        assert result is not None
        assert len(result) == 2
    cache.close()


def test_cache_stats(tmp_path: Path) -> None:
    """Do 5 hits and 3 misses, verify stats."""
    cache = CpcXwalkCache(cache_path=tmp_path / "cache.db")
    for i in range(5):
        cache.put(f"HIT{i}", _make_mappings(1))

    # 5 hits
    for i in range(5):
        cache.get(f"HIT{i}")

    # 3 misses
    for i in range(3):
        cache.get(f"MISS{i}")

    stats = cache.stats()
    assert stats.hit_count == 5
    assert stats.miss_count == 3
    assert stats.total_entries == 5
    assert stats.version == "v1"
    assert abs(stats.hit_rate - 5 / 8) < 0.01
    cache.close()


def test_warm_cache_performance(tmp_path: Path) -> None:
    """Put 1000 entries, time 1000 lookups, assert p99 < 1ms."""
    cache = CpcXwalkCache(cache_path=tmp_path / "cache.db")
    entries = [(f"CPC{i:04d}", _make_mappings(3)) for i in range(1000)]
    cache.put_batch(entries)

    latencies: list[float] = []
    for cpc_code, _ in entries:
        start = time.perf_counter()
        cache.get(cpc_code)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

    latencies.sort()
    p99_index = int(len(latencies) * 0.99)
    p99 = latencies[p99_index]
    assert p99 < 1.0, f"p99 latency {p99:.3f}ms exceeds 1ms threshold"
    cache.close()


def test_serialization_round_trip(tmp_path: Path) -> None:
    """Serialize/deserialize MeshDescriptor with qualifier and major_topic."""
    cache = CpcXwalkCache(cache_path=tmp_path / "cache.db")
    mappings = [
        (
            MeshDescriptor(
                descriptor="Pharmaceutical Preparations",
                qualifier="therapeutic use",
                major_topic=True,
            ),
            0.95,
        ),
        (
            MeshDescriptor(
                descriptor="Pyridines",
                qualifier=None,
                major_topic=False,
            ),
            0.75,
        ),
    ]
    cache.put("A61K31/00", mappings)
    result = cache.get("A61K31/00")

    assert result is not None
    assert len(result) == 2

    md0, w0 = result[0]
    assert md0.descriptor == "Pharmaceutical Preparations"
    assert md0.qualifier == "therapeutic use"
    assert md0.major_topic is True
    assert w0 == 0.95

    md1, w1 = result[1]
    assert md1.descriptor == "Pyridines"
    assert md1.qualifier is None
    assert md1.major_topic is False
    assert w1 == 0.75
    cache.close()
