"""Tests for per-specialty clinician inverted index."""

from __future__ import annotations

import time
from pathlib import Path

from aegis.storage.clinician_index import ClinicianIndex, ClinicianLookupResult


def _make_index(tmp_path: Path) -> ClinicianIndex:
    """Create a ClinicianIndex with a temp DuckDB file."""
    return ClinicianIndex(db_path=str(tmp_path / "test.duckdb"))


def test_insert_and_lookup(tmp_path: Path) -> None:
    """Insert 5 clinicians with same taxonomy, lookup, verify 5 returned."""
    idx = _make_index(tmp_path)
    try:
        for i in range(5):
            idx.insert(
                taxonomy_code="207R00000X",
                npi=f"100000000{i}",
                provider_name=f"Dr. Smith{i}",
                practice_state="CA",
                practice_city="Los Angeles",
                practice_zip="90001",
            )
        results = idx.lookup_by_specialty("207R00000X")
        assert len(results) == 5
        for r in results:
            assert isinstance(r, ClinicianLookupResult)
            assert r.taxonomy_code == "207R00000X"
    finally:
        idx.close()


def test_lookup_by_state(tmp_path: Path) -> None:
    """Insert clinicians in 3 states, filter by state."""
    idx = _make_index(tmp_path)
    try:
        states = ["CA", "CA", "NY", "TX", "TX", "TX"]
        for i, state in enumerate(states):
            idx.insert(
                taxonomy_code="207R00000X",
                npi=f"200000000{i}",
                provider_name=f"Dr. State{i}",
                practice_state=state,
            )

        ca_results = idx.lookup_by_specialty("207R00000X", state="CA")
        assert len(ca_results) == 2
        assert all(r.practice_state == "CA" for r in ca_results)

        tx_results = idx.lookup_by_specialty("207R00000X", state="TX")
        assert len(tx_results) == 3
        assert all(r.practice_state == "TX" for r in tx_results)

        ny_results = idx.lookup_by_specialty("207R00000X", state="NY")
        assert len(ny_results) == 1
    finally:
        idx.close()


def test_count_by_specialty(tmp_path: Path) -> None:
    """Insert 10 clinicians across 2 taxonomies, verify counts."""
    idx = _make_index(tmp_path)
    try:
        for i in range(7):
            idx.insert(
                taxonomy_code="207R00000X",
                npi=f"300000000{i}",
                provider_name=f"Dr. Oncology{i}",
                practice_state="CA",
            )
        for i in range(3):
            idx.insert(
                taxonomy_code="208600000X",
                npi=f"400000000{i}",
                provider_name=f"Dr. Surgery{i}",
                practice_state="NY",
            )

        assert idx.count_by_specialty("207R00000X") == 7
        assert idx.count_by_specialty("208600000X") == 3
    finally:
        idx.close()


def test_total_count(tmp_path: Path) -> None:
    """Verify total count matches insertions."""
    idx = _make_index(tmp_path)
    try:
        assert idx.total_count() == 0
        for i in range(5):
            idx.insert(
                taxonomy_code="207R00000X",
                npi=f"500000000{i}",
                provider_name=f"Dr. Total{i}",
            )
        assert idx.total_count() == 5
    finally:
        idx.close()


def test_upsert_idempotent(tmp_path: Path) -> None:
    """Insert same NPI twice, verify count is 1."""
    idx = _make_index(tmp_path)
    try:
        idx.insert(
            taxonomy_code="207R00000X",
            npi="6000000001",
            provider_name="Dr. Original",
            practice_state="CA",
        )
        idx.insert(
            taxonomy_code="207R00000X",
            npi="6000000001",
            provider_name="Dr. Updated",
            practice_state="NY",
        )
        assert idx.count_by_specialty("207R00000X") == 1

        results = idx.lookup_by_specialty("207R00000X")
        assert len(results) == 1
        assert results[0].provider_name == "Dr. Updated"
        assert results[0].practice_state == "NY"
    finally:
        idx.close()


def test_lookup_performance(tmp_path: Path) -> None:
    """Insert 5000 clinicians, time specialty lookup, assert p95 < 100ms."""
    idx = _make_index(tmp_path)
    try:
        taxonomy = "207R00000X"
        batch = [
            (taxonomy, f"{7000000000 + i}", f"Dr. Perf{i}", "CA", "City", "90001")
            for i in range(5000)
        ]
        idx.insert_batch(batch)

        # Run 20 lookups and measure times
        timings: list[float] = []
        for _ in range(20):
            t0 = time.perf_counter()
            results = idx.lookup_by_specialty(taxonomy)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            timings.append(elapsed_ms)
            assert len(results) > 0

        # p95
        timings.sort()
        p95_idx = int(len(timings) * 0.95)
        p95 = timings[p95_idx]
        assert p95 < 100, f"p95 lookup time {p95:.1f}ms exceeds 100ms"
    finally:
        idx.close()
