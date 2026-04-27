"""ICD-10-CM to MeSH cross-walk."""

from __future__ import annotations

import logging

from aegis.storage.schema import MeshDescriptor

logger = logging.getLogger(__name__)


class Icd10MeshMapping:
    """A single ICD-10 to MeSH mapping entry (metadata only)."""

    def __init__(
        self,
        icd10_code: str,
        icd10_description: str,
        mesh_descriptors: list[MeshDescriptor],
    ) -> None:
        self.icd10_code = icd10_code
        self.icd10_description = icd10_description
        self.mesh_descriptors = mesh_descriptors


class Icd10MeshXwalk:
    """Translate ICD-10-CM codes to MeSH descriptors.

    Uses UMLS-derived mappings for the most common codes
    plus hierarchical prefix matching for variants.
    """

    def __init__(self) -> None:
        self._mapping: dict[str, list[MeshDescriptor]] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        """Load built-in ICD-10 to MeSH mappings.

        In production, these come from UMLS; here we include
        the most common codes for the target specialties.
        """
        # Common oncology ICD-10 codes
        builtins: dict[str, list[tuple[str, str | None, bool]]] = {
            "C34": [("Lung Neoplasms", None, True)],
            "C34.1": [("Carcinoma, Non-Small-Cell Lung", None, True)],
            "C34.9": [("Lung Neoplasms", None, True)],
            "C50": [("Breast Neoplasms", None, True)],
            "C61": [("Prostatic Neoplasms", None, True)],
            "C18": [("Colonic Neoplasms", None, True)],
            "C71": [("Brain Neoplasms", None, True)],
            "C91.0": [("Precursor Cell Lymphoblastic Leukemia-Lymphoma", None, True)],
            "C92.0": [("Leukemia, Myeloid, Acute", None, True)],
            # Common cardiology codes
            "I21": [("Myocardial Infarction", None, True)],
            "I25": [("Coronary Artery Disease", None, True)],
            "I48": [("Atrial Fibrillation", None, True)],
            "I50": [("Heart Failure", None, True)],
            # Common radiology-relevant codes
            "R91": [("Solitary Pulmonary Nodule", None, True)],
            "R93": [("Diagnostic Imaging", "abnormal findings", True)],
            # Endocrinology
            "E11": [("Diabetes Mellitus, Type 2", None, True)],
            "E10": [("Diabetes Mellitus, Type 1", None, True)],
            "E05": [("Hyperthyroidism", None, True)],
            # Neurology
            "G20": [("Parkinson Disease", None, True)],
            "G30": [("Alzheimer Disease", None, True)],
            "G35": [("Multiple Sclerosis", None, True)],
        }
        for code, mesh_list in builtins.items():
            self._mapping[code] = [
                MeshDescriptor(descriptor=d, qualifier=q, major_topic=m)
                for d, q, m in mesh_list
            ]

    def translate(self, icd10: str) -> list[MeshDescriptor]:
        """Translate an ICD-10 code to MeSH descriptors.

        Tries exact match, then progressively shorter prefixes.
        """
        # Normalize: remove dots for matching
        normalized = icd10.replace(".", "").upper()
        dotted = icd10.upper()

        # Exact match (with dot)
        if dotted in self._mapping:
            return self._mapping[dotted]

        # Exact match (without dot)
        if normalized in self._mapping:
            return self._mapping[normalized]

        # Prefix match
        prefix = dotted
        while len(prefix) > 1:
            prefix = prefix[:-1]
            if prefix in self._mapping:
                return self._mapping[prefix]

        return []
