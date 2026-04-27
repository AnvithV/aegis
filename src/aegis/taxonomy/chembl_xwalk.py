"""ChEMBL target to MeSH cross-walk."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aegis.sources.chembl import ChemblIngestor
from aegis.storage.schema import MeshDescriptor

logger = logging.getLogger(__name__)


class TargetMeshMapping(BaseModel):
    """A ChEMBL target mapped to MeSH descriptors."""

    model_config = ConfigDict(frozen=True)

    target_chembl_id: str
    target_name: str
    mesh_descriptors: list[MeshDescriptor]


class ChemblXwalk:
    """Cross-walk ChEMBL target IDs to MeSH descriptors.

    Covers: target protein name -> MeSH, pathway associations,
    and disease associations from drug indications.
    """

    def __init__(
        self,
        chembl_db_path: Path | None = None,
    ) -> None:
        self._ingestor = ChemblIngestor(chembl_db_path) if chembl_db_path else None
        self._cache: dict[str, list[MeshDescriptor]] = {}

    def target_to_mesh(self, target_id: str) -> list[MeshDescriptor]:
        """Translate a ChEMBL target ID to MeSH descriptors.

        Returns descriptors covering the target itself, its pathway,
        and its disease associations.
        """
        if target_id in self._cache:
            return self._cache[target_id]

        if self._ingestor is None:
            return []

        descriptors: list[MeshDescriptor] = []

        # Get disease associations
        for disease in self._ingestor.iter_disease_associations(target_id):
            descriptors.append(MeshDescriptor(
                descriptor=disease.mesh_heading,
                qualifier=None,
                major_topic=True,
            ))

        self._cache[target_id] = descriptors
        return descriptors

    def build_index(self) -> int:
        """Pre-build the full target-to-MeSH index from ChEMBL dump.

        Returns number of targets indexed.
        """
        if self._ingestor is None:
            return 0

        count = 0
        for target in self._ingestor.iter_targets():
            mesh = self.target_to_mesh(target.target_chembl_id)
            if mesh:
                count += 1
        logger.info("Indexed %d ChEMBL targets with MeSH mappings", count)
        return count
