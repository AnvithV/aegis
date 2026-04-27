"""Tests for NPPES/NPI bulk file ingestor."""

from __future__ import annotations

import csv
from pathlib import Path

from aegis.sources.nppes import NppesClient, NppesProvider


def _make_header() -> list[str]:
    """Create a mock NPPES CSV header row with 50+ columns."""
    cols = [f"col_{i}" for i in range(55)]
    cols[0] = "NPI"
    cols[1] = "Entity Type Code"
    cols[5] = "Provider Last Name (Legal Name)"
    cols[6] = "Provider First Name"
    cols[7] = "Provider Middle Name"
    cols[10] = "Provider Credential Text"
    cols[28] = "Provider First Line Business Practice Location Address"
    cols[30] = "Provider Business Practice Location Address City Name"
    cols[31] = "Provider Business Practice Location Address State Name"
    cols[32] = "Provider Business Practice Location Address Postal Code"
    cols[33] = "Provider Business Practice Location Address Country Code"
    cols[39] = "NPI Deactivation Date"
    cols[40] = "NPI Reactivation Date"
    cols[47] = "Healthcare Provider Taxonomy Code_1"
    cols[48] = "Provider License Number State Code_1"
    return cols


def _make_row(
    npi: str = "1234567890",
    entity_type: str = "1",
    last_name: str = "Smith",
    first_name: str = "John",
    middle_name: str = "A",
    credential: str = "MD",
    taxonomy: str = "207R00000X",
    license_state: str = "CA",
    addr: str = "123 Main St",
    city: str = "Los Angeles",
    state: str = "CA",
    zipcode: str = "90001",
    country: str = "US",
    deactivation: str = "",
    reactivation: str = "",
) -> list[str]:
    """Create a mock NPPES CSV data row."""
    row = [""] * 55
    row[0] = npi
    row[1] = entity_type
    row[5] = last_name
    row[6] = first_name
    row[7] = middle_name
    row[10] = credential
    row[28] = addr
    row[30] = city
    row[31] = state
    row[32] = zipcode
    row[33] = country
    row[39] = deactivation
    row[40] = reactivation
    row[47] = taxonomy
    row[48] = license_state
    return row


def _write_csv(path: Path, rows: list[list[str]]) -> Path:
    """Write rows to a CSV file and return the path."""
    csv_file = path / "npidata_test.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    return csv_file


def test_bulk_ingest_basic(tmp_path: Path) -> None:
    """Ingest a mock CSV with header + 5 individual rows."""
    header = _make_header()
    rows = [header]
    for i in range(5):
        rows.append(
            _make_row(
                npi=f"100000000{i}",
                first_name=f"Doc{i}",
                last_name=f"Smith{i}",
            )
        )
    csv_file = _write_csv(tmp_path, rows)

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file))
    assert len(providers) == 5
    for p in providers:
        assert isinstance(p, NppesProvider)
        assert p.entity_type == "individual"
        assert p.is_deactivated is False


def test_skip_organizations(tmp_path: Path) -> None:
    """Organization rows (entity_type=2) are skipped with individuals_only=True."""
    header = _make_header()
    rows = [
        header,
        _make_row(npi="1000000001", entity_type="1", first_name="Individual"),
        _make_row(npi="1000000002", entity_type="2", first_name="Organization"),
        _make_row(npi="1000000003", entity_type="1", first_name="Individual2"),
    ]
    csv_file = _write_csv(tmp_path, rows)

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file, individuals_only=True))
    assert len(providers) == 2
    assert all(p.entity_type == "individual" for p in providers)


def test_skip_deactivated(tmp_path: Path) -> None:
    """Deactivated providers (with deactivation date, no reactivation) are skipped."""
    header = _make_header()
    rows = [
        header,
        _make_row(npi="1000000001"),  # active
        _make_row(npi="1000000002", deactivation="01/15/2020"),  # deactivated
        _make_row(
            npi="1000000003", deactivation="01/15/2020", reactivation="06/01/2021"
        ),  # reactivated
    ]
    csv_file = _write_csv(tmp_path, rows)

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file))
    assert len(providers) == 2
    npis = {p.npi for p in providers}
    assert "1000000001" in npis
    assert "1000000003" in npis
    assert "1000000002" not in npis


def test_npi_extraction(tmp_path: Path) -> None:
    """NPI numbers are correctly extracted."""
    header = _make_header()
    rows = [
        header,
        _make_row(npi="9876543210"),
    ]
    csv_file = _write_csv(tmp_path, rows)

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file))
    assert len(providers) == 1
    assert providers[0].npi == "9876543210"


def test_taxonomy_code(tmp_path: Path) -> None:
    """NUCC taxonomy code is extracted correctly."""
    header = _make_header()
    rows = [
        header,
        _make_row(npi="1000000001", taxonomy="207R00000X"),
    ]
    csv_file = _write_csv(tmp_path, rows)

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file))
    assert len(providers) == 1
    assert providers[0].taxonomy_code == "207R00000X"


def test_credential_parsing(tmp_path: Path) -> None:
    """Credential field (MD, DO) is parsed correctly."""
    header = _make_header()
    rows = [
        header,
        _make_row(npi="1000000001", credential="MD"),
        _make_row(npi="1000000002", credential="DO"),
        _make_row(npi="1000000003", credential="PhD"),
    ]
    csv_file = _write_csv(tmp_path, rows)

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file))
    assert len(providers) == 3
    creds = {p.npi: p.credential for p in providers}
    assert creds["1000000001"] == "MD"
    assert creds["1000000002"] == "DO"
    assert creds["1000000003"] == "PhD"


def test_practice_address(tmp_path: Path) -> None:
    """Practice address, city, state, zip are extracted correctly."""
    header = _make_header()
    rows = [
        header,
        _make_row(
            npi="1000000001",
            addr="456 Oak Ave",
            city="San Francisco",
            state="CA",
            zipcode="94102",
            country="US",
        ),
    ]
    csv_file = _write_csv(tmp_path, rows)

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file))
    assert len(providers) == 1
    p = providers[0]
    assert p.practice_address == "456 Oak Ave"
    assert p.practice_city == "San Francisco"
    assert p.practice_state == "CA"
    assert p.practice_zip == "94102"
    assert p.practice_country == "US"


def test_empty_file(tmp_path: Path) -> None:
    """CSV with only header yields no records."""
    header = _make_header()
    csv_file = _write_csv(tmp_path, [header])

    client = NppesClient()
    providers = list(client.bulk_ingest(csv_file))
    assert len(providers) == 0
