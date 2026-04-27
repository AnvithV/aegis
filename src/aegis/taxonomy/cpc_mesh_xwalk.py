"""CPC/IPC to MeSH cross-walk: curated mapping + LLM fallback for tail codes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from aegis.storage.schema import MeshDescriptor

logger = logging.getLogger(__name__)

_DEFAULT_XWALK_PATH = Path("data/aegis/cpc_mesh_xwalk_v1.yaml")


class MeshMapping(BaseModel):
    """A single CPC-to-MeSH mapping with weight."""

    model_config = ConfigDict(frozen=True)

    descriptor: str
    weight: float


class LLMFallback(Protocol):
    """Protocol for LLM-based CPC-to-MeSH translation."""

    def translate(self, cpc_code: str, cpc_description: str) -> list[MeshMapping]:
        """Propose up to 3 MeSH descriptors for an unmapped CPC code."""
        ...


class DefaultLLMFallback:
    """Stub LLM fallback that returns empty results.

    Replace with actual LLM integration (constrained generation
    against MeSH controlled vocabulary) in production.
    """

    def translate(self, cpc_code: str, cpc_description: str) -> list[MeshMapping]:
        logger.info("LLM fallback invoked for CPC %s (stub)", cpc_code)
        return []


class CpcMeshXwalk:
    """Translate CPC/IPC codes to weighted MeSH descriptors."""

    def __init__(
        self,
        xwalk_path: Path | None = None,
        llm_fallback: LLMFallback | None = None,
    ) -> None:
        self._llm = llm_fallback or DefaultLLMFallback()
        self._mapping: dict[str, list[MeshMapping]] = {}
        self._load(xwalk_path or _DEFAULT_XWALK_PATH)

    def _load(self, path: Path) -> None:
        """Load curated cross-walk from YAML."""
        with open(path) as f:  # noqa: PTH123
            data: dict[str, Any] = yaml.safe_load(f)
        for entry in data.get("entries", []):
            cpc = entry["cpc"]
            mappings = [
                MeshMapping(descriptor=m["descriptor"], weight=m["weight"])
                for m in entry.get("mesh", [])
            ]
            self._mapping[cpc] = mappings
        logger.info("Loaded %d CPC-MeSH mappings", len(self._mapping))

    def translate(self, cpc_code: str) -> list[tuple[MeshDescriptor, float]]:
        """Translate a CPC code to weighted MeSH descriptors.

        Returns list of (MeshDescriptor, weight) tuples.
        Uses curated mapping first; falls back to LLM for unmapped codes.
        """
        # Exact match
        if cpc_code in self._mapping:
            return self._to_mesh_descriptors(self._mapping[cpc_code])

        # Prefix match (try progressively shorter prefixes)
        parts = cpc_code
        while len(parts) > 4:
            parts = parts[:-1]
            if parts in self._mapping:
                return self._to_mesh_descriptors(self._mapping[parts])

        # LLM fallback
        fallback_results = self._llm.translate(cpc_code, "")
        if fallback_results:
            return self._to_mesh_descriptors(fallback_results)

        return []

    @property
    def curated_count(self) -> int:
        """Number of curated CPC-MeSH mappings."""
        return len(self._mapping)

    @staticmethod
    def _to_mesh_descriptors(
        mappings: list[MeshMapping],
    ) -> list[tuple[MeshDescriptor, float]]:
        """Convert MeshMapping list to (MeshDescriptor, weight) tuples."""
        return [
            (
                MeshDescriptor(
                    descriptor=m.descriptor,
                    qualifier=None,
                    major_topic=m.weight >= 0.8,
                ),
                m.weight,
            )
            for m in mappings
        ]
