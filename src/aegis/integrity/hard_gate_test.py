"""Tests for hard-zero integrity gate."""

from __future__ import annotations

from datetime import date

from aegis.integrity.hard_gate import HardGate
from aegis.integrity.llm_triage import LLMTriageClassifier
from aegis.sources.leie import LEIERecord, LEIEStore
from aegis.sources.ofac_sam import OFACSAMRecord, OFACSAMStore
from aegis.sources.ori import ORIFinding, ORIStore
from aegis.sources.retraction_watch import (
    RetractionRecord,
    RetractionWatchStore,
)


def _empty_gate() -> HardGate:
    """Gate with empty stores — clean candidate."""
    return HardGate(
        leie_store=LEIEStore(),
        ofac_sam_store=OFACSAMStore(),
        ori_store=ORIStore(),
        retraction_store=RetractionWatchStore(),
    )


def test_clean_candidate_passes() -> None:
    gate = _empty_gate()
    result = gate.evaluate(
        candidate_uuid="c1",
        candidate_name="Good Doctor",
    )
    assert result.is_zero is False
    assert result.reason is None
    assert result.artifact_ref is None
    assert result.rules_evaluated == 5


def test_leie_exclusion_triggers_hard_zero() -> None:
    leie = LEIEStore()
    leie.add_batch([
        LEIERecord(
            first_name="Bad",
            last_name="Actor",
            npi="1111111111",
            exclusion_type="1128(a)(1)",
            exclusion_date=date(2020, 1, 1),
            reinstate_date=None,
            state="NY",
            specialty=None,
        )
    ])
    gate = HardGate(
        leie_store=leie,
        ofac_sam_store=OFACSAMStore(),
        ori_store=ORIStore(),
        retraction_store=RetractionWatchStore(),
    )
    result = gate.evaluate(
        candidate_uuid="c2",
        candidate_name="Bad Actor",
        npi="1111111111",
    )
    assert result.is_zero is True
    assert result.reason == "LEIE federal exclusion"
    assert result.rules_evaluated == 1


def test_ofac_sam_triggers_hard_zero() -> None:
    ofac = OFACSAMStore()
    ofac.add_batch([
        OFACSAMRecord(
            primary_name="Sanctioned Person",
            aliases=[],
            source="OFAC",
            record_type="Individual",
            program=None,
            remarks=None,
        )
    ])
    gate = HardGate(
        leie_store=LEIEStore(),
        ofac_sam_store=ofac,
        ori_store=ORIStore(),
        retraction_store=RetractionWatchStore(),
    )
    result = gate.evaluate(
        candidate_uuid="c3",
        candidate_name="Sanctioned Person",
    )
    assert result.is_zero is True
    assert result.reason == "OFAC/SAM listing"
    assert result.rules_evaluated == 2


def test_ori_recent_finding_triggers_hard_zero() -> None:
    ori = ORIStore()
    ori.add_batch([
        ORIFinding(
            name="Fraud Researcher",
            institution="MIT",
            finding_date=date(2024, 1, 1),
            misconduct_type="Fabrication",
            settlement_type="Debarment",
            debarment_end_date=None,
        )
    ])
    gate = HardGate(
        leie_store=LEIEStore(),
        ofac_sam_store=OFACSAMStore(),
        ori_store=ori,
        retraction_store=RetractionWatchStore(),
    )
    result = gate.evaluate(
        candidate_uuid="c4",
        candidate_name="Fraud Researcher",
    )
    assert result.is_zero is True
    assert result.reason == "ORI misconduct finding (10yr)"
    assert result.rules_evaluated == 3


def test_subdomain_retraction_fabrication() -> None:
    rw = RetractionWatchStore()
    rw.add_batch([
        RetractionRecord(
            title="Retracted paper",
            authors=["John Doe"],
            pmid="99999",
            doi=None,
            journal=None,
            retraction_date=date(2023, 1, 1),
            reason="fabrication",
            original_paper_date=None,
        )
    ])
    gate = HardGate(
        leie_store=LEIEStore(),
        ofac_sam_store=OFACSAMStore(),
        ori_store=ORIStore(),
        retraction_store=rw,
        triage_classifier=LLMTriageClassifier(),
    )
    # MeSH overlap high enough
    result = gate.evaluate(
        candidate_uuid="c5",
        candidate_name="John Doe",
        candidate_mesh={"neoplasms", "lung", "therapy"},
        query_mesh={"neoplasms", "lung", "therapy", "diagnosis"},
        retraction_notices=[
            {
                "pmid": "99999",
                "retraction_notice_text": "fabrication of data",
            }
        ],
    )
    assert result.is_zero is True
    assert "retraction" in (result.reason or "")
    assert result.rules_evaluated == 4


def test_subdomain_retraction_low_overlap_passes() -> None:
    gate = _empty_gate()
    result = gate.evaluate(
        candidate_uuid="c6",
        candidate_name="John Doe",
        candidate_mesh={"neoplasms"},
        query_mesh={"cardiology", "heart", "surgery"},
        retraction_notices=[
            {
                "pmid": "88888",
                "retraction_notice_text": "fabrication",
            }
        ],
    )
    assert result.is_zero is False


def test_subdomain_retraction_honest_error_passes() -> None:
    rw = RetractionWatchStore()
    rw.add_batch([
        RetractionRecord(
            title="Retracted paper",
            authors=["Jane Smith"],
            pmid="77777",
            doi=None,
            journal=None,
            retraction_date=date(2023, 1, 1),
            reason="honest error",
            original_paper_date=None,
        )
    ])
    gate = HardGate(
        leie_store=LEIEStore(),
        ofac_sam_store=OFACSAMStore(),
        ori_store=ORIStore(),
        retraction_store=rw,
    )
    result = gate.evaluate(
        candidate_uuid="c7",
        candidate_name="Jane Smith",
        candidate_mesh={"neoplasms", "lung"},
        query_mesh={"neoplasms", "lung"},
        retraction_notices=[
            {
                "pmid": "77777",
                "retraction_notice_text": "honest error",
            }
        ],
    )
    assert result.is_zero is False


def test_early_exit_leie_skips_later_rules() -> None:
    leie = LEIEStore()
    leie.add_batch([
        LEIERecord(
            first_name="Bad",
            last_name="Actor",
            npi=None,
            exclusion_type=None,
            exclusion_date=None,
            reinstate_date=None,
            state=None,
            specialty=None,
        )
    ])
    ori = ORIStore()
    ori.add_batch([
        ORIFinding(
            name="Bad Actor",
            institution=None,
            finding_date=date(2024, 1, 1),
            misconduct_type="Fabrication",
            settlement_type=None,
            debarment_end_date=None,
        )
    ])
    gate = HardGate(
        leie_store=leie,
        ofac_sam_store=OFACSAMStore(),
        ori_store=ori,
        retraction_store=RetractionWatchStore(),
    )
    result = gate.evaluate(
        candidate_uuid="c8",
        candidate_name="Bad Actor",
    )
    # Stops at rule 1 (LEIE), never reaches ORI
    assert result.is_zero is True
    assert result.rules_evaluated == 1


def test_artifact_ref_populated() -> None:
    ofac = OFACSAMStore()
    ofac.add_batch([
        OFACSAMRecord(
            primary_name="Listed Entity",
            aliases=[],
            source="SAM",
            record_type="Entity",
            program=None,
            remarks=None,
        )
    ])
    gate = HardGate(
        leie_store=LEIEStore(),
        ofac_sam_store=ofac,
        ori_store=ORIStore(),
        retraction_store=RetractionWatchStore(),
    )
    result = gate.evaluate(
        candidate_uuid="c9",
        candidate_name="Listed Entity",
    )
    assert result.artifact_ref is not None
    assert result.artifact_ref.source == "OFAC_SAM"
    assert result.artifact_ref.identifier == "Listed Entity"


def test_medical_board_stub_passes() -> None:
    """Rule 5 is a Phase 1 stub — always passes."""
    gate = _empty_gate()
    result = gate.evaluate(
        candidate_uuid="c10",
        candidate_name="Any Doctor",
    )
    assert result.is_zero is False
    assert result.rules_evaluated == 5
