"""Unit tests for the Journal definition and its activation semantics."""

from __future__ import annotations

from pyaccountingkit.core.identifiers import EntityId, JournalId
from pyaccountingkit.domain.journals.journal import Journal


def test_journal_is_active_by_default() -> None:
    journal = Journal(
        id=JournalId("j_sales"),
        entity_id=EntityId("ent_1"),
        code="VTE",
        label="Ventes",
    )
    assert journal.is_active()


def test_journal_carries_entity_scope() -> None:
    journal = Journal(
        id=JournalId("j_sales"), entity_id=EntityId("ent_1"), code="VTE", label="Ventes"
    )
    assert journal.entity_id == EntityId("ent_1")


def test_journal_deactivation_is_immutable() -> None:
    journal = Journal(
        id=JournalId("j_sales"),
        entity_id=EntityId("ent_1"),
        code="VTE",
        label="Ventes",
    )
    inactive = journal.deactivated()
    assert journal.is_active()
    assert not inactive.is_active()
    assert inactive.code == journal.code


def test_deactivating_an_inactive_journal_is_a_noop() -> None:
    inactive = Journal(
        id=JournalId("j_old"),
        entity_id=EntityId("ent_1"),
        code="OLD",
        label="Ancien",
        active=False,
    )
    assert inactive.deactivated() is inactive
