"""CPT to MeSH cross-walk for clinician procedure coding."""

from __future__ import annotations

import logging

from aegis.storage.schema import MeshDescriptor

logger = logging.getLogger(__name__)


class CptMeshXwalk:
    """Translate CPT (Current Procedural Terminology) codes to MeSH.

    CPT -> MeSH mapping is sparser than ICD-10 -> MeSH.
    Built-in covers the most common diagnostic and procedural codes.
    """

    def __init__(self) -> None:
        self._mapping: dict[str, list[MeshDescriptor]] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        """Load built-in CPT to MeSH mappings."""
        builtins: dict[str, list[tuple[str, str | None, bool]]] = {
            # Radiology CPTs
            "71250": [("Tomography, X-Ray Computed", "methods", True)],
            "71260": [
                ("Tomography, X-Ray Computed", "methods", True),
                ("Contrast Media", None, False),
            ],
            "71275": [("Computed Tomography Angiography", None, True)],
            "74177": [
                ("Tomography, X-Ray Computed", "methods", True),
                ("Abdomen", "diagnostic imaging", True),
            ],
            "77065": [("Mammography", None, True)],
            "77066": [("Mammography", None, True)],
            # Cardiology CPTs
            "93000": [("Electrocardiography", None, True)],
            "93306": [("Echocardiography", None, True)],
            "93350": [("Echocardiography, Stress", None, True)],
            "93458": [("Cardiac Catheterization", None, True)],
            "93459": [("Cardiac Catheterization", None, True)],
            "92928": [
                ("Percutaneous Coronary Intervention", None, True),
            ],
            # Surgery CPTs
            "47600": [("Cholecystectomy", None, True)],
            "44970": [("Appendectomy", None, True)],
            "27447": [
                ("Arthroplasty, Replacement, Knee", None, True),
            ],
            # Pathology
            "88305": [("Biopsy", "pathology", True)],
            "88342": [("Immunohistochemistry", None, True)],
            # Oncology
            "96413": [
                ("Antineoplastic Agents", "administration & dosage", True),
            ],
            "96415": [("Infusions, Intravenous", None, True)],
        }
        for code, mesh_list in builtins.items():
            self._mapping[code] = [
                MeshDescriptor(descriptor=d, qualifier=q, major_topic=m)
                for d, q, m in mesh_list
            ]

    def translate(self, cpt: str) -> list[MeshDescriptor]:
        """Translate a CPT code to MeSH descriptors."""
        normalized = cpt.strip()
        if normalized in self._mapping:
            return self._mapping[normalized]
        return []
