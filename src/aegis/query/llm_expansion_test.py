"""Tests for LLM-backed query expansion."""

from __future__ import annotations

from datetime import UTC, datetime

from aegis.query.llm_expansion import (
    ExpandedQuery,
    LlmExpansionConfig,
    LlmQueryExpander,
    MetaMapExpander,
    MetaMapResult,
)


def test_metamap_expander_stub() -> None:
    result = MetaMapExpander().expand(
        "evaluate JAK2 kinase inhibitor candidates"
    )
    assert isinstance(result, MetaMapResult)
    assert len(result.mesh_terms) > 0
    assert result.confidence == 0.5


def test_expand_with_override() -> None:
    expander = LlmQueryExpander()
    result = expander.expand(
        "test query for override",
        mesh_override=["Neoplasms", "Drug Therapy"],
    )
    assert result.expansion_method == "override"
    assert result.mesh_terms == ["Neoplasms", "Drug Therapy"]
    assert result.cost_tokens == 0
    assert result.low_confidence is False


def test_expand_metamap_fallback_no_api_key(monkeypatch: object) -> None:
    """Without an API key, LLM should fail and fall back to MetaMap."""
    import os

    # Ensure no API key is set
    os.environ.pop("ANTHROPIC_API_KEY", None)
    expander = LlmQueryExpander()
    result = expander.expand("evaluate JAK2 inhibitors for kinase activity")
    assert result.expansion_method in ("metamap", "llm_fallback_metamap")
    assert len(result.mesh_terms) > 0


def test_expanded_query_model() -> None:
    now = datetime.now(UTC)
    eq = ExpandedQuery(
        original_query="test query",
        mesh_terms=["Neoplasms"],
        expansion_method="llm",
        low_confidence=False,
        raw_llm_terms=["Neoplasms", "Cancer"],
        rejected_terms=["Cancer"],
        cached=False,
        cost_tokens=150,
        expanded_at=now,
    )
    assert eq.original_query == "test query"
    assert eq.cost_tokens == 150
    # Verify frozen
    data = eq.model_dump_json()
    assert "Neoplasms" in data


def test_llm_expansion_config_defaults() -> None:
    config = LlmExpansionConfig()
    assert config.model == "claude-sonnet-4-20250514"
    assert config.max_terms == 20
    assert config.temperature == 0.0
    assert config.max_tokens == 1024
    assert config.timeout_seconds == 10.0


def test_build_tool_schema() -> None:
    expander = LlmQueryExpander()
    schema = expander._build_tool_schema()
    assert schema["name"] == "expand_mesh_terms"
    assert "input_schema" in schema
    assert "mesh_terms" in schema["input_schema"]["properties"]


def test_expand_empty_override_uses_expansion() -> None:
    """Empty override list should NOT use override path."""
    expander = LlmQueryExpander()
    result = expander.expand(
        "test query at least 10 chars",
        mesh_override=[],
    )
    # Should go through normal expansion, not override
    assert result.expansion_method != "override"
