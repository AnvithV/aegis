"""Tests for Drugs@FDA source client."""

from __future__ import annotations

from aegis.sources.drugs_fda import DrugsFDAStore, FDASubmission


def _make_submission(
    app_num: str = "NDA000001",
    sponsor: str = "Acme Pharma",
    drug: str = "TestDrug",
    **kwargs: str | None,
) -> FDASubmission:
    return FDASubmission(
        application_number=app_num,
        sponsor_name=sponsor,
        drug_name=drug,
        active_ingredient=kwargs.get("active_ingredient"),
        submission_type=kwargs.get("submission_type"),
        approval_date=kwargs.get("approval_date"),
        application_type=kwargs.get("application_type"),
    )


def test_add_and_lookup_by_sponsor() -> None:
    store = DrugsFDAStore()
    subs = [
        _make_submission("NDA001", "Acme Pharma", "DrugA"),
        _make_submission("NDA002", "Beta Labs", "DrugB"),
        _make_submission("NDA003", "Acme Pharma Inc", "DrugC"),
    ]
    store.add_batch(subs)

    results = store.lookup_by_sponsor("Acme Pharma")
    assert len(results) == 2
    assert {r.application_number for r in results} == {"NDA001", "NDA003"}

    results_beta = store.lookup_by_sponsor("Beta")
    assert len(results_beta) == 1
    assert results_beta[0].drug_name == "DrugB"

    assert store.count() == 3


def test_lookup_case_insensitive() -> None:
    store = DrugsFDAStore()
    store.add_batch([_make_submission("NDA001", "Acme Pharma", "DrugA")])

    results_upper = store.lookup_by_sponsor("ACME PHARMA")
    assert len(results_upper) == 1

    results_lower = store.lookup_by_sponsor("acme pharma")
    assert len(results_lower) == 1

    results_mixed = store.lookup_by_sponsor("AcMe PhArMa")
    assert len(results_mixed) == 1
