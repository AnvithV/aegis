"""ChEMBL bulk data ingestion from SQLite dump."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ChemblTarget(BaseModel):
    """A ChEMBL target with UniProt cross-references."""

    model_config = ConfigDict(frozen=True)

    target_chembl_id: str          # e.g., "CHEMBL2971"
    target_type: str               # e.g., "SINGLE PROTEIN"
    pref_name: str                 # e.g., "Janus kinase 2"
    organism: str | None
    uniprot_accessions: list[str]  # UniProt IDs


class ChemblDisease(BaseModel):
    """A disease association from ChEMBL drug indications."""

    model_config = ConfigDict(frozen=True)

    mesh_id: str                   # MeSH UI, e.g., "D009196"
    mesh_heading: str              # e.g., "Myeloproliferative Disorders"
    efo_id: str | None


class ChemblIngestor:
    """Ingest ChEMBL SQLite dump and extract targets + disease associations."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def iter_targets(self) -> Iterator[ChemblTarget]:
        """Iterate over all single-protein targets with UniProt accessions."""
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                """
                SELECT td.chembl_id, td.target_type, td.pref_name, td.organism,
                       GROUP_CONCAT(cs.accession, ',') as accessions
                FROM target_dictionary td
                LEFT JOIN target_components tc ON td.tid = tc.tid
                LEFT JOIN component_sequences cs ON tc.component_id = cs.component_id
                WHERE td.target_type = 'SINGLE PROTEIN'
                GROUP BY td.chembl_id
                """
            )
            for row in cursor:
                accessions = row[4].split(",") if row[4] else []
                yield ChemblTarget(
                    target_chembl_id=row[0],
                    target_type=row[1],
                    pref_name=row[2] or "",
                    organism=row[3],
                    uniprot_accessions=accessions,
                )
        finally:
            conn.close()

    def iter_disease_associations(
        self, target_chembl_id: str
    ) -> Iterator[ChemblDisease]:
        """Iterate disease associations for a target via drug indications."""
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                """
                SELECT DISTINCT di.mesh_id, di.mesh_heading, di.efo_id
                FROM drug_indication di
                JOIN activities act ON di.molregno = act.molregno
                JOIN assays a ON act.assay_id = a.assay_id
                WHERE a.tid = (
                    SELECT tid FROM target_dictionary WHERE chembl_id = ?
                )
                AND di.mesh_id IS NOT NULL
                """,
                (target_chembl_id,),
            )
            for row in cursor:
                yield ChemblDisease(
                    mesh_id=row[0],
                    mesh_heading=row[1] or "",
                    efo_id=row[2],
                )
        finally:
            conn.close()
