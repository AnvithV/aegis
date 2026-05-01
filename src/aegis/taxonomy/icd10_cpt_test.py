"""Tests for ICD-10/CPT to MeSH cross-walks."""

from __future__ import annotations

from aegis.taxonomy.cpt_mesh import CptMeshXwalk
from aegis.taxonomy.icd10_mesh import Icd10MeshXwalk


def test_icd10_lung_cancer() -> None:
    xwalk = Icd10MeshXwalk()
    result = xwalk.translate("C34.1")
    assert len(result) == 1
    assert result[0].descriptor == "Carcinoma, Non-Small-Cell Lung"


def test_icd10_prefix_match() -> None:
    xwalk = Icd10MeshXwalk()
    # C34.9 is an exact match in the builtins
    result = xwalk.translate("C34.9")
    assert len(result) == 1
    assert result[0].descriptor == "Lung Neoplasms"
    # C34.2 should prefix-match to C34
    result2 = xwalk.translate("C34.2")
    assert len(result2) == 1
    assert result2[0].descriptor == "Lung Neoplasms"


def test_icd10_unknown() -> None:
    xwalk = Icd10MeshXwalk()
    result = xwalk.translate("Z99.99")
    assert result == []


def test_cpt_radiology() -> None:
    xwalk = CptMeshXwalk()
    result = xwalk.translate("71250")
    assert len(result) == 1
    assert result[0].descriptor == "Tomography, X-Ray Computed"
    assert result[0].qualifier == "methods"


def test_cpt_cardiac_cath() -> None:
    xwalk = CptMeshXwalk()
    result = xwalk.translate("93458")
    assert len(result) == 1
    assert result[0].descriptor == "Cardiac Catheterization"


def test_cpt_unknown() -> None:
    xwalk = CptMeshXwalk()
    result = xwalk.translate("00000")
    assert result == []
