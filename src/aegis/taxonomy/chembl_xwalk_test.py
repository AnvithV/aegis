"""Tests for ChEMBL target-to-MeSH cross-walk and bulk ingestor."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from aegis.sources.chembl import ChemblIngestor, ChemblTarget
from aegis.storage.schema import MeshDescriptor
from aegis.taxonomy.chembl_xwalk import ChemblXwalk


def _create_chembl_db(db_path: Path) -> None:
    """Create a minimal ChEMBL-like SQLite database for testing."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE target_dictionary (
            tid INTEGER PRIMARY KEY,
            chembl_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            pref_name TEXT,
            organism TEXT
        );

        CREATE TABLE target_components (
            tid INTEGER NOT NULL,
            component_id INTEGER NOT NULL
        );

        CREATE TABLE component_sequences (
            component_id INTEGER PRIMARY KEY,
            accession TEXT
        );

        CREATE TABLE assays (
            assay_id INTEGER PRIMARY KEY,
            tid INTEGER NOT NULL
        );

        CREATE TABLE activities (
            activity_id INTEGER PRIMARY KEY,
            assay_id INTEGER NOT NULL,
            molregno INTEGER NOT NULL
        );

        CREATE TABLE drug_indication (
            drugind_id INTEGER PRIMARY KEY,
            molregno INTEGER NOT NULL,
            mesh_id TEXT,
            mesh_heading TEXT,
            efo_id TEXT
        );

        -- JAK2 target
        INSERT INTO target_dictionary
            VALUES (1, 'CHEMBL2971', 'SINGLE PROTEIN',
                    'Janus kinase 2', 'Homo sapiens');
        INSERT INTO target_components VALUES (1, 100);
        INSERT INTO component_sequences VALUES (100, 'O60674');

        -- A second target for iteration testing
        INSERT INTO target_dictionary
            VALUES (2, 'CHEMBL1824', 'SINGLE PROTEIN',
                    'EGFR', 'Homo sapiens');
        INSERT INTO target_components VALUES (2, 200);
        INSERT INTO component_sequences VALUES (200, 'P00533');

        -- Assay for JAK2
        INSERT INTO assays VALUES (1000, 1);
        -- Activity linking assay to molecule
        INSERT INTO activities VALUES (5000, 1000, 42);
        -- Drug indication for that molecule
        INSERT INTO drug_indication
            VALUES (9000, 42, 'D009196',
                    'Myeloproliferative Disorders',
                    'EFO:0002429');
        INSERT INTO drug_indication
            VALUES (9001, 42, 'D011565',
                    'Psoriasis', NULL);
    """)
    conn.close()


def test_chembl_target_parse(tmp_path: Path) -> None:
    """iter_targets should yield ChemblTarget objects from the SQLite DB."""
    db_path = tmp_path / "chembl.db"
    _create_chembl_db(db_path)

    ingestor = ChemblIngestor(db_path)
    targets = list(ingestor.iter_targets())

    assert len(targets) == 2
    assert all(isinstance(t, ChemblTarget) for t in targets)

    jak2 = next(t for t in targets if t.target_chembl_id == "CHEMBL2971")
    assert jak2.pref_name == "Janus kinase 2"
    assert jak2.target_type == "SINGLE PROTEIN"
    assert "O60674" in jak2.uniprot_accessions


def test_disease_association(tmp_path: Path) -> None:
    """iter_disease_associations should yield ChemblDisease objects."""
    db_path = tmp_path / "chembl.db"
    _create_chembl_db(db_path)

    ingestor = ChemblIngestor(db_path)
    diseases = list(ingestor.iter_disease_associations("CHEMBL2971"))

    assert len(diseases) == 2
    headings = {d.mesh_heading for d in diseases}
    assert "Myeloproliferative Disorders" in headings
    assert "Psoriasis" in headings


def test_target_to_mesh(tmp_path: Path) -> None:
    """target_to_mesh should return MeshDescriptor list."""
    db_path = tmp_path / "chembl.db"
    _create_chembl_db(db_path)

    xwalk = ChemblXwalk(chembl_db_path=db_path)
    descriptors = xwalk.target_to_mesh("CHEMBL2971")

    assert len(descriptors) > 0
    assert all(isinstance(d, MeshDescriptor) for d in descriptors)
    names = [d.descriptor for d in descriptors]
    assert "Myeloproliferative Disorders" in names


def test_target_to_mesh_caching(tmp_path: Path) -> None:
    """Second call to target_to_mesh should use the cache."""
    db_path = tmp_path / "chembl.db"
    _create_chembl_db(db_path)

    xwalk = ChemblXwalk(chembl_db_path=db_path)
    result1 = xwalk.target_to_mesh("CHEMBL2971")
    result2 = xwalk.target_to_mesh("CHEMBL2971")

    assert result1 is result2  # Same object from cache


def test_jak2_expansion(tmp_path: Path) -> None:
    """CHEMBL2971 (JAK2) should expand to Janus Kinase 2 disease associations."""
    db_path = tmp_path / "chembl.db"
    _create_chembl_db(db_path)

    xwalk = ChemblXwalk(chembl_db_path=db_path)
    descriptors = xwalk.target_to_mesh("CHEMBL2971")

    descriptor_names = [d.descriptor for d in descriptors]
    assert "Myeloproliferative Disorders" in descriptor_names
    assert all(d.major_topic for d in descriptors)
