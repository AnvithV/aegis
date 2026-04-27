"""Tests for NCCN guideline panel roster source client."""

from __future__ import annotations

from aegis.sources.nccn import NCCNPanelMember, NCCNPanelStore


def _make_member(
    name: str = "Jane Doe",
    panel: str = "NSCLC",
    role: str | None = "Member",
    institution: str | None = "MGH",
) -> NCCNPanelMember:
    return NCCNPanelMember(
        name=name,
        institution=institution,
        panel_name=panel,
        role=role,
        guideline_version=None,
    )


def test_is_panel_member() -> None:
    store = NCCNPanelStore()
    store.add_batch([
        _make_member("Alice Smith", "NSCLC"),
        _make_member("Bob Jones", "NSCLC"),
    ])

    assert store.is_panel_member("Alice Smith") is True
    assert store.is_panel_member("alice smith") is True
    assert store.is_panel_member("Charlie Brown") is False


def test_is_panel_member_specific_panel() -> None:
    store = NCCNPanelStore()
    store.add_batch([
        _make_member("Alice Smith", "NSCLC"),
        _make_member("Alice Smith", "Breast Cancer"),
    ])

    assert store.is_panel_member("Alice Smith", "NSCLC") is True
    assert store.is_panel_member("Alice Smith", "nsclc") is True
    assert store.is_panel_member("Alice Smith", "Melanoma") is False


def test_list_panel() -> None:
    store = NCCNPanelStore()
    store.add_batch([
        _make_member("Alice Smith", "NSCLC"),
        _make_member("Bob Jones", "NSCLC"),
        _make_member("Charlie Brown", "Breast Cancer"),
    ])

    nsclc_members = store.list_panel("NSCLC")
    assert len(nsclc_members) == 2
    assert {m.name for m in nsclc_members} == {"Alice Smith", "Bob Jones"}

    breast_members = store.list_panel("Breast Cancer")
    assert len(breast_members) == 1
    assert breast_members[0].name == "Charlie Brown"

    assert store.count() == 3
