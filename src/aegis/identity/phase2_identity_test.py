"""Tests for Phase 2 identity modules: patent conflicts and NPI-PubMed matching."""

from __future__ import annotations

from aegis.identity.patent_conflicts import PatentConflict, PatentConflictHandler
from aegis.identity.npi_pubmed_match import NpiPubmedMatcher


class TestPatentConflictHandler:
    """Tests for patent inventor disambiguation conflict handling."""

    def test_patent_conflict_report(self) -> None:
        """Reporting a conflict creates a pending entry."""
        handler = PatentConflictHandler()
        conflict = handler.report_conflict(
            patent_number="US-10000001",
            inventor_name="Jane Doe",
            patentsview_id="inv-123",
            aegis_uuid="uuid-abc",
            conflict_type="split",
            confidence_gap=0.15,
        )

        assert isinstance(conflict, PatentConflict)
        assert conflict.status == "pending"
        assert conflict.conflict_type == "split"
        assert conflict.patent_number == "US-10000001"
        assert conflict.confidence_gap == 0.15
        assert handler.conflict_rate == 1

    def test_excluded_patents(self) -> None:
        """Pending and excluded patents appear in excluded set."""
        handler = PatentConflictHandler()
        handler.report_conflict(
            patent_number="US-10000001",
            inventor_name="Jane Doe",
            patentsview_id="inv-123",
            aegis_uuid="uuid-abc",
            conflict_type="split",
            confidence_gap=0.15,
        )
        handler.report_conflict(
            patent_number="US-10000002",
            inventor_name="John Smith",
            patentsview_id="inv-456",
            aegis_uuid="uuid-def",
            conflict_type="merge",
            confidence_gap=0.25,
        )

        excluded = handler.get_excluded_patents()
        assert "US-10000001" in excluded
        assert "US-10000002" in excluded
        assert len(handler.get_pending()) == 2


class TestNpiPubmedMatcher:
    """Tests for NPI-PubMed name-match HITL routing."""

    def test_npi_pubmed_auto_link(self) -> None:
        """Exact name match with specialty and address -> auto-link."""
        matcher = NpiPubmedMatcher()
        result = matcher.match(
            npi="1234567890",
            npi_name="Jane Doe",
            npi_specialty="Oncology",
            npi_state="CA",
            pubmed_author="Jane Doe",
            pubmed_affiliation="University of California, CA",
            pubmed_mesh=["Neoplasms"],
        )

        assert result.action == "auto-link"
        assert result.confidence >= 0.95
        assert result.specialty_match is True
        assert result.address_match is True

    def test_npi_pubmed_review(self) -> None:
        """Last-name-only match -> review."""
        matcher = NpiPubmedMatcher()
        result = matcher.match(
            npi="1234567890",
            npi_name="Jane Doe",
            npi_specialty="Oncology",
            npi_state="CA",
            pubmed_author="J Doe",
            pubmed_affiliation="University of California, CA",
            pubmed_mesh=["Neoplasms"],
        )

        assert result.action == "review"
        assert 0.5 <= result.confidence < 0.95

    def test_npi_pubmed_reject(self) -> None:
        """Completely different name -> reject."""
        matcher = NpiPubmedMatcher()
        result = matcher.match(
            npi="1234567890",
            npi_name="Jane Doe",
            npi_specialty="",
            npi_state="CA",
            pubmed_author="Robert Smith",
            pubmed_affiliation="MIT, MA",
            pubmed_mesh=[],
        )

        assert result.action == "reject"
        assert result.confidence < 0.5
        assert "name_mismatch" in result.rejection_signals

    def test_npi_pubmed_never_auto_below_095(self) -> None:
        """Confidence 0.94 -> review, NOT auto-link. Critical safety check."""
        matcher = NpiPubmedMatcher()
        # Last-name match (0.7) + specialty (0.1) + address (0.1) = 0.9
        result = matcher.match(
            npi="1234567890",
            npi_name="Jane Doe",
            npi_specialty="Oncology",
            npi_state="NY",
            pubmed_author="J Doe",
            pubmed_affiliation="NYU Medical Center, NY",
            pubmed_mesh=["Neoplasms"],
        )

        assert result.confidence < 0.95
        assert result.action != "auto-link"
        assert result.action == "review"

    def test_npi_specialty_mismatch_signal(self) -> None:
        """Empty specialty or MeSH triggers specialty_mismatch signal."""
        matcher = NpiPubmedMatcher()
        result = matcher.match(
            npi="1234567890",
            npi_name="Jane Doe",
            npi_specialty="Oncology",
            npi_state="CA",
            pubmed_author="Jane Doe",
            pubmed_affiliation="UCLA, CA",
            pubmed_mesh=[],  # empty MeSH -> specialty mismatch
        )

        assert result.specialty_match is False
        assert "specialty_mismatch" in result.rejection_signals
