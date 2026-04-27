"""Tests for USPTO and EPO bulk patent ingestion (fixture-based, no live API calls)."""

from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path
from typing import Any

from aegis.sources.epo_bulk import EpoBulkIngestor
from aegis.sources.uspto import PatentRecord
from aegis.sources.uspto_bulk import UsptoBulkIngestor

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_uspto_record(
    patent_number: str,
    grant_date: str = "2023-06-15",
    title: str = "Test Patent",
) -> dict[str, Any]:
    return {
        "patent_number": patent_number,
        "grant_date": grant_date,
        "title": title,
        "abstract": "Abstract text",
        "inventors": [
            {
                "id": "inv-1",
                "name": "Alice Smith",
                "first_name": "Alice",
                "last_name": "Smith",
            }
        ],
        "assignees": [
            {
                "id": "asg-1",
                "organization": "Test Corp",
                "type": "organization",
            }
        ],
        "cpc_codes": ["A61K31/00"],
        "ipc_codes": [],
        "citation_count": 10,
    }


def _make_epo_record(
    doc_number: str,
    publication_date: str = "2023-06-15",
    title: str = "EP Test Patent",
) -> dict[str, Any]:
    return {
        "doc_number": doc_number,
        "publication_date": publication_date,
        "title": title,
        "abstract": "EP abstract",
        "inventors": [
            {
                "id": "epo-inv-1",
                "name": "Bob Jones",
                "first_name": "Bob",
                "last_name": "Jones",
            }
        ],
        "cpc_codes": ["C07D401/12"],
        "ipc_codes": [],
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_uspto_bulk_parse_single_file(tmp_path: Path) -> None:
    """Parse 10 JSONL records into PatentRecords."""
    records = [_make_uspto_record(f"US{10000000 + i}B2") for i in range(10)]
    jsonl_file = tmp_path / "patents.jsonl"
    _write_jsonl(jsonl_file, records)

    ingestor = UsptoBulkIngestor(data_dir=tmp_path)
    results = list(ingestor.iter_patents_from_file(jsonl_file))

    assert len(results) == 10
    assert all(isinstance(r, PatentRecord) for r in results)
    assert results[0].patent_number == "US10000000B2"
    assert results[9].patent_number == "US10000009B2"
    assert results[0].forward_citation_count == 10


def test_uspto_bulk_parse_gzip(tmp_path: Path) -> None:
    """Gzipped JSONL parses correctly."""
    records = [_make_uspto_record(f"US{20000000 + i}B1") for i in range(5)]
    gz_file = tmp_path / "patents.jsonl.gz"
    with gzip.open(gz_file, "wt", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    ingestor = UsptoBulkIngestor(data_dir=tmp_path)
    results = list(ingestor.iter_patents_from_file(gz_file))

    assert len(results) == 5
    assert results[0].patent_number == "US20000000B1"


def test_uspto_bulk_since_filter(tmp_path: Path) -> None:
    """Date filtering only yields patents on or after the since date."""
    records = [
        _make_uspto_record("US1000A", grant_date="2019-06-01"),
        _make_uspto_record("US1001A", grant_date="2020-01-01"),
        _make_uspto_record("US1002A", grant_date="2021-03-15"),
        _make_uspto_record("US1003A", grant_date="2022-12-31"),
    ]
    jsonl_file = tmp_path / "patents.jsonl"
    _write_jsonl(jsonl_file, records)

    ingestor = UsptoBulkIngestor(data_dir=tmp_path)
    results = list(ingestor.iter_all_patents(since=date(2020, 1, 1)))

    assert len(results) == 3
    patent_numbers = [r.patent_number for r in results]
    assert "US1000A" not in patent_numbers
    assert "US1001A" in patent_numbers
    assert "US1002A" in patent_numbers
    assert "US1003A" in patent_numbers


def test_epo_bulk_parse(tmp_path: Path) -> None:
    """EPO JSONL records parse with EP prefix on patent numbers."""
    records = [_make_epo_record(f"{3000000 + i}") for i in range(5)]
    jsonl_file = tmp_path / "ep_patents.jsonl"
    _write_jsonl(jsonl_file, records)

    ingestor = EpoBulkIngestor(data_dir=tmp_path)
    results = list(ingestor.iter_patents_from_file(jsonl_file))

    assert len(results) == 5
    assert all(isinstance(r, PatentRecord) for r in results)
    assert results[0].patent_number == "EP3000000"
    assert results[4].patent_number == "EP3000004"
    assert results[0].cpc_codes == ["C07D401/12"]


def test_bulk_malformed_line(tmp_path: Path) -> None:
    """Malformed JSON lines are skipped without exception."""
    jsonl_file = tmp_path / "mixed.jsonl"
    with open(jsonl_file, "w") as f:
        f.write(json.dumps(_make_uspto_record("US1111A")) + "\n")
        f.write("THIS IS NOT JSON\n")
        f.write("{broken json\n")
        f.write(json.dumps(_make_uspto_record("US2222A")) + "\n")

    ingestor = UsptoBulkIngestor(data_dir=tmp_path)
    results = list(ingestor.iter_patents_from_file(jsonl_file))

    assert len(results) == 2
    assert results[0].patent_number == "US1111A"
    assert results[1].patent_number == "US2222A"


def test_bulk_empty_file(tmp_path: Path) -> None:
    """Empty file yields no records."""
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("")

    ingestor = UsptoBulkIngestor(data_dir=tmp_path)
    results = list(ingestor.iter_patents_from_file(empty_file))

    assert results == []
