"""Score-collapse detection and fallback MeSH expansion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# Default floor below which a score is considered collapsed
DEFAULT_COLLAPSE_FLOOR: float = 0.05

# Hardcoded MeSH parent mappings for NSCLC-relevant descriptors
MESH_PARENT_MAP: dict[str, str] = {
    "D002289": "D009369",  # Carcinoma, Non-Small-Cell Lung -> Neoplasms
    "D008175": "D009369",  # Lung Neoplasms -> Neoplasms
    "D000074322": "D060890",  # Immunotherapy -> Molecular Targeted Therapy
    "D000077192": "D060890",  # Immune Checkpoint Inhibitors
    "D011958": "D009367",  # Receptor, Epidermal Growth Factor -> Neoplasm Proteins
    "D000077594": "D047428",  # Osimertinib -> Protein Kinase Inhibitors
    "D047428": "D004791",  # Protein Kinase Inhibitors -> Enzyme Inhibitors
    "D000068437": "D047428",  # Pemetrexed -> Protein Kinase Inhibitors
    "D016190": "D009369",  # Lymphoma, T-Cell -> Neoplasms
    "D002945": "D060890",  # Cisplatin -> Molecular Targeted Therapy
}


class CollapseResult(BaseModel):
    """Result of score-collapse analysis."""

    model_config = ConfigDict(frozen=True)

    collapsed: bool
    expanded_mesh_terms: list[str]
    flag: str
    retry_count: int


class ScoreCollapseHandler:
    """Detect all-below-floor score collapse and handle via MeSH expansion."""

    def __init__(
        self,
        *,
        floor: float = DEFAULT_COLLAPSE_FLOOR,
        mesh_parent_map: dict[str, str] | None = None,
    ) -> None:
        self._floor = floor
        self._mesh_parent_map = (
            mesh_parent_map if mesh_parent_map is not None else MESH_PARENT_MAP
        )

    def check_collapse(self, scores: list[float]) -> bool:
        """Return True if ALL scores are below the floor (or empty)."""
        if not scores:
            return True
        return all(s < self._floor for s in scores)

    def expand_mesh(self, mesh_terms: list[str]) -> list[str]:
        """Return union of original terms + parent terms, deduplicated."""
        expanded: set[str] = set(mesh_terms)
        for term in mesh_terms:
            parent = self._mesh_parent_map.get(term)
            if parent is not None:
                expanded.add(parent)
        return sorted(expanded)

    def handle_collapse(
        self, scores: list[float], query_mesh: list[str]
    ) -> CollapseResult:
        """Check for collapse and return appropriate result."""
        if not self.check_collapse(scores):
            return CollapseResult(
                collapsed=False,
                expanded_mesh_terms=list(query_mesh),
                flag="normal",
                retry_count=0,
            )
        return CollapseResult(
            collapsed=True,
            expanded_mesh_terms=self.expand_mesh(query_mesh),
            flag="low_confidence_ranking",
            retry_count=1,
        )

    def make_cohort_fallback(self) -> CollapseResult:
        """Return a cohort fallback result for when expansion also collapses."""
        return CollapseResult(
            collapsed=True,
            expanded_mesh_terms=[],
            flag="cohort_fallback",
            retry_count=2,
        )
