"""Tests for CPC/IPC to MeSH cross-walk."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import yaml

from aegis.storage.schema import MeshDescriptor
from aegis.taxonomy.cpc_mesh_xwalk import CpcMeshXwalk, MeshMapping

_XWALK_PATH = Path("data/aegis/cpc_mesh_xwalk_v1.yaml")


def test_load_curated_xwalk() -> None:
    """Curated YAML should have at least 40 entries."""
    xwalk = CpcMeshXwalk(xwalk_path=_XWALK_PATH)
    assert xwalk.curated_count >= 40


def test_exact_match() -> None:
    """A61K31/00 should map to Pharmaceutical Preparations."""
    xwalk = CpcMeshXwalk(xwalk_path=_XWALK_PATH)
    results = xwalk.translate("A61K31/00")
    assert len(results) > 0
    descriptors = [md.descriptor for md, _ in results]
    assert "Pharmaceutical Preparations" in descriptors


def test_prefix_fallback() -> None:
    """A code not in YAML but whose prefix is should match via prefix fallback."""
    xwalk = CpcMeshXwalk(xwalk_path=_XWALK_PATH)
    # A61K31/4439 is in YAML; A61K31/44391 is not, should fall back to A61K31/4439
    results = xwalk.translate("A61K31/44391")
    assert len(results) > 0
    descriptors = [md.descriptor for md, _ in results]
    assert "Pyridines" in descriptors


def test_llm_fallback_invoked() -> None:
    """Unknown CPC code should invoke the LLM fallback."""
    mock_llm = MagicMock()
    mock_llm.translate.return_value = [
        MeshMapping(descriptor="Test Descriptor", weight=0.9),
    ]
    xwalk = CpcMeshXwalk(xwalk_path=_XWALK_PATH, llm_fallback=mock_llm)
    results = xwalk.translate("Z99Z99/99")
    mock_llm.translate.assert_called_once_with("Z99Z99/99", "")
    assert len(results) == 1
    assert results[0][0].descriptor == "Test Descriptor"


def test_translate_returns_mesh_descriptors() -> None:
    """translate() should return list of (MeshDescriptor, float) tuples."""
    xwalk = CpcMeshXwalk(xwalk_path=_XWALK_PATH)
    results = xwalk.translate("A61K31/00")
    assert len(results) > 0
    for md, weight in results:
        assert isinstance(md, MeshDescriptor)
        assert isinstance(weight, float)


def test_weight_range() -> None:
    """All weights in the curated YAML should be 0 < w <= 1."""
    with open(_XWALK_PATH) as f:
        data = yaml.safe_load(f)
    for entry in data["entries"]:
        for m in entry["mesh"]:
            assert 0.0 < m["weight"] <= 1.0, (
                f"Weight {m['weight']} out of range for CPC {entry['cpc']}"
            )
