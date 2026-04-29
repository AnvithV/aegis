"""LLM-backed query expansion using Anthropic tool use for constrained MeSH generation.

Implements the program overview section 10 pattern: deterministic MetaMap pass first,
then LLM expansion constrained to MeSH vocabulary for synonyms, related subtopics,
and disambiguation. Falls back to MetaMap-only on LLM failure.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-6"


class ExpandedQuery(BaseModel):
    """Result of query expansion."""

    model_config = ConfigDict(frozen=True)

    original_query: str
    mesh_terms: list[str]
    expansion_method: str
    low_confidence: bool
    raw_llm_terms: list[str] | None
    rejected_terms: list[str]
    cached: bool
    cost_tokens: int
    expanded_at: datetime


class MetaMapResult(BaseModel):
    """Result from MetaMap expansion (stub)."""

    model_config = ConfigDict(frozen=True)

    mesh_terms: list[str]
    confidence: float


class LlmExpansionConfig(BaseModel):
    """Configuration for LLM-based query expansion."""

    model_config = ConfigDict(frozen=True)

    model: str = _DEFAULT_MODEL
    max_terms: int = 20
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_seconds: float = 10.0


class MetaMapExpander:
    """MeSH term extractor via NLM MeSH Lookup API (no auth required).

    Uses https://id.nlm.nih.gov/mesh/lookup/descriptor — the public NLM
    linked-data endpoint backed by the same UMLS MeSH snapshot.

    Upgrade path: when UMLS_API_KEY is available, swap this class for a
    full UMLS REST client (uts.nlm.nih.gov/uts/rest/search) to get CUI
    resolution and broader concept coverage.
    """

    _BASE_URL = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    _TIMEOUT = 5.0  # seconds per term lookup

    def expand(self, query: str) -> MetaMapResult:
        """Map query text to MeSH descriptors via NLM MeSH Lookup API."""
        import httpx

        candidates = self._extract_candidates(query)
        mesh_terms: list[str] = []
        seen: set[str] = set()

        for term in candidates:
            try:
                resp = httpx.get(
                    self._BASE_URL,
                    params={"label": term, "match": "contains", "limit": 5},
                    timeout=self._TIMEOUT,
                )
                if resp.status_code == 200:
                    for item in resp.json():
                        label = item.get("label", "")
                        if label and label.lower() not in seen:
                            seen.add(label.lower())
                            mesh_terms.append(label)
            except Exception:
                logger.debug("MeSH lookup failed for term %r", term)

        if not mesh_terms:
            # Graceful degradation: fall back to title-cased words
            words = [w.strip(".,;:!?()") for w in query.split()]
            mesh_terms = [w.title() for w in words if len(w) > 3]
            return MetaMapResult(mesh_terms=mesh_terms, confidence=0.3)

        return MetaMapResult(mesh_terms=mesh_terms, confidence=0.8)

    def _extract_candidates(self, query: str) -> list[str]:
        """Extract candidate lookup terms: multi-word phrases + single tokens."""
        query = query.strip()
        words = [w.strip(".,;:!?()[]") for w in query.split() if len(w.strip(".,;:!?()[]")) > 2]

        candidates: list[str] = []
        # Full query first (best for exact phrases like "KRAS G12C")
        candidates.append(query)
        # Sliding bigrams
        for i in range(len(words) - 1):
            candidates.append(f"{words[i]} {words[i + 1]}")
        # Individual tokens (skip stopwords)
        _STOP = {"the", "for", "and", "with", "using", "from", "into", "that", "this", "are"}
        candidates.extend(w for w in words if w.lower() not in _STOP)

        # Deduplicate preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for c in candidates:
            if c.lower() not in seen:
                seen.add(c.lower())
                unique.append(c)
        return unique


class LlmQueryExpander:
    """LLM-backed query expansion with MetaMap fallback."""

    def __init__(
        self,
        *,
        config: LlmExpansionConfig | None = None,
        validator: Any = None,
    ) -> None:
        self._config = config or LlmExpansionConfig()
        self._validator = validator
        self._metamap = MetaMapExpander()
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(
                    api_key=os.environ.get("ANTHROPIC_API_KEY", "")
                )
            except Exception:
                logger.warning("Failed to initialize Anthropic client")
                return None
        return self._client

    def _build_tool_schema(self) -> dict[str, Any]:
        """Build the Anthropic tool-use schema for constrained MeSH expansion."""
        return {
            "name": "expand_mesh_terms",
            "description": (
                "Expand a biomedical query into relevant MeSH descriptor terms. "
                "Return ONLY valid MeSH descriptors from the NLM Medical Subject "
                "Headings vocabulary."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "mesh_terms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of valid MeSH descriptor terms relevant to the "
                            "query. Each must be an exact MeSH descriptor heading."
                        ),
                        "maxItems": self._config.max_terms,
                    },
                    "reasoning": {
                        "type": "string",
                        "description": (
                            "Brief explanation of why "
                            "these terms were selected."
                        ),
                    },
                },
                "required": ["mesh_terms", "reasoning"],
            },
        }

    def expand_via_llm(self, query: str) -> tuple[list[str], int]:
        """Call the Anthropic API for MeSH term expansion.

        Returns (mesh_terms, total_tokens). On failure returns ([], 0).
        """
        try:
            client = self._get_client()
            if client is None:
                return [], 0

            response = client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                tools=[self._build_tool_schema()],
                tool_choice={"type": "tool", "name": "expand_mesh_terms"},
                system=(
                    "You are a biomedical query expansion "
                    "assistant. Given a research task "
                    "description, identify the most relevant "
                    "MeSH (Medical Subject Headings) "
                    "descriptor terms. Only use exact MeSH "
                    "descriptor headings from the NLM "
                    "vocabulary. Include synonyms, related "
                    "concepts, and relevant subtopics."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Expand this research task "
                            f"into MeSH terms: {query}"
                        ),
                    }
                ],
            )

            # Parse tool_use content block
            mesh_terms: list[str] = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "expand_mesh_terms":
                    mesh_terms = block.input.get("mesh_terms", [])
                    break

            total_tokens = response.usage.input_tokens + response.usage.output_tokens
            return mesh_terms, total_tokens

        except Exception:
            logger.warning(
                "LLM expansion failed, will fall back to MetaMap",
                exc_info=True,
            )
            return [], 0

    def expand(
        self, query: str, *, mesh_override: list[str] | None = None
    ) -> ExpandedQuery:
        """Expand a query into MeSH terms.

        If mesh_override is provided and non-empty, returns immediately
        with the override terms. Otherwise tries LLM expansion with
        MetaMap fallback.
        """
        now = datetime.now(UTC)

        # Override path
        if mesh_override is not None and len(mesh_override) > 0:
            return ExpandedQuery(
                original_query=query,
                mesh_terms=mesh_override,
                expansion_method="override",
                low_confidence=False,
                raw_llm_terms=None,
                rejected_terms=[],
                cached=False,
                cost_tokens=0,
                expanded_at=now,
            )

        # Step 1: MetaMap pass
        metamap_result = self._metamap.expand(query)

        # Step 2: Try LLM expansion
        llm_terms: list[str] = []
        cost_tokens = 0
        rejected_terms: list[str] = []

        try:
            llm_terms, cost_tokens = self.expand_via_llm(query)
        except Exception:
            logger.warning("LLM expansion raised exception", exc_info=True)

        if llm_terms:
            # Validate if validator available
            valid_terms = llm_terms
            if self._validator is not None:
                try:
                    report = self._validator.validate(llm_terms)
                    valid_terms = report.valid_terms
                    rejected_terms = report.rejected_terms
                except Exception:
                    logger.warning("Validator failed", exc_info=True)
                    valid_terms = llm_terms

            if not valid_terms:
                # All LLM terms rejected, fall back to MetaMap
                return ExpandedQuery(
                    original_query=query,
                    mesh_terms=metamap_result.mesh_terms,
                    expansion_method="llm_fallback_metamap",
                    low_confidence=True,
                    raw_llm_terms=llm_terms,
                    rejected_terms=rejected_terms,
                    cached=False,
                    cost_tokens=cost_tokens,
                    expanded_at=now,
                )

            # Merge LLM + MetaMap terms (LLM first, deduplicated)
            seen: set[str] = set()
            merged: list[str] = []
            for term in valid_terms + metamap_result.mesh_terms:
                lower = term.lower()
                if lower not in seen:
                    seen.add(lower)
                    merged.append(term)

            return ExpandedQuery(
                original_query=query,
                mesh_terms=merged,
                expansion_method="llm",
                low_confidence=False,
                raw_llm_terms=llm_terms,
                rejected_terms=rejected_terms,
                cached=False,
                cost_tokens=cost_tokens,
                expanded_at=now,
            )

        # LLM failed entirely, use MetaMap
        return ExpandedQuery(
            original_query=query,
            mesh_terms=metamap_result.mesh_terms,
            expansion_method="metamap",
            low_confidence=metamap_result.confidence < 0.7,
            raw_llm_terms=None,
            rejected_terms=[],
            cached=False,
            cost_tokens=0,
            expanded_at=now,
        )
