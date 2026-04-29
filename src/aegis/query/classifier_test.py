"""Tests for query type classifier."""

from __future__ import annotations

from aegis.query.classifier import QueryClassifier, QueryType


def test_drug_discovery_classification() -> None:
    classifier = QueryClassifier()
    result = classifier.classify("KRAS inhibitor drug discovery for lung cancer")
    assert result.query_type == QueryType.drug_discovery
    assert "inhibitor" in result.keyword_matches
    assert "drug" in result.keyword_matches
    assert result.confidence > 0.5
    assert result.weight_vector.specialty == "drug_discovery"


def test_clinical_trial_pi_classification() -> None:
    classifier = QueryClassifier()
    result = classifier.classify("phase 3 trial principal investigator for oncology")
    assert result.query_type == QueryType.clinical_trial_pi
    assert "principal investigator" in result.keyword_matches
    assert "phase 3" in result.keyword_matches
    assert result.confidence > 0.5


def test_policy_epi_classification() -> None:
    classifier = QueryClassifier()
    result = classifier.classify("COVID-19 epidemiology surveillance and public health")
    assert result.query_type == QueryType.policy_epi
    assert "epidemiology" in result.keyword_matches
    assert "surveillance" in result.keyword_matches
    assert result.confidence > 0.5
    assert result.weight_vector.specialty == "policy_epi"


def test_basic_research_fallback() -> None:
    classifier = QueryClassifier()
    result = classifier.classify("KRAS oncogene research")
    assert result.query_type == QueryType.basic_research
    assert result.confidence == 0.5
    assert result.keyword_matches == []
    assert result.weight_vector.specialty == "basic_research"


def test_weight_vector_loaded_for_each_type() -> None:
    classifier = QueryClassifier()
    drug = classifier.classify("drug compound inhibitor")
    assert drug.weight_vector.specialty == "drug_discovery"

    clinical = classifier.classify("clinical trial phase 2 enrollment")
    assert clinical.weight_vector.specialty == "clinician"

    epi = classifier.classify("epidemiology population health surveillance")
    assert epi.weight_vector.specialty == "policy_epi"

    basic = classifier.classify("generic biology research")
    assert basic.weight_vector.specialty == "basic_research"
