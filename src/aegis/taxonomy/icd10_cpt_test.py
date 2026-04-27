"""Tests for ICD-10/CPT to MeSH cross-walks and CMS PPSAS client."""

from __future__ import annotations

from pathlib import Path

from aegis.sources.cms_ppsas import CmsPpsasClient
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


_CMS_CSV = """\
Rndrng_NPI,Rndrng_Prvdr_Last_Org_Name,Rndrng_Prvdr_Crdntls,HCPCS_Cd,HCPCS_Desc,Tot_Srvcs,Tot_Benes,Avg_Sbmtd_Chrg,Avg_Mdcr_Pymt_Amt
1234567890,Smith,MD,99213,Office visit,150,120,100.00,75.00
1234567890,Smith,MD,99214,Office visit extended,50,40,150.00,112.50
9876543210,Jones,DO,71250,CT chest,200,180,"1,200.00",800.00
"""


def test_cms_ppsas_parse(tmp_path: Path) -> None:
    csv_path = tmp_path / "cms.csv"
    csv_path.write_text(_CMS_CSV)
    client = CmsPpsasClient()
    records = list(client.iter_utilization(csv_path))
    assert len(records) == 3
    assert records[0].npi == "1234567890"
    assert records[0].total_services == 150
    assert records[2].average_submitted_charge == 1200.00


def test_cms_aggregate_by_npi(tmp_path: Path) -> None:
    csv_path = tmp_path / "cms.csv"
    csv_path.write_text(_CMS_CSV)
    client = CmsPpsasClient()
    agg = client.aggregate_by_npi(csv_path)
    assert "1234567890" in agg
    assert agg["1234567890"]["99213"] == 150
    assert agg["1234567890"]["99214"] == 50
    assert agg["9876543210"]["71250"] == 200
