"""Unit tests for the transactional ReversalOrchestrator (LOT-06)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.ledger.reversal_orchestrator import ReversalOrchestrator
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    AlreadyReversedError,
    EntryNotFoundError,
    PeriodClosedError,
)
from pyaccountingkit.core.identifiers import (
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus


def _posted_entry() -> JournalEntry:
    return JournalEntry(
        id=EntryId("e1"),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="Vente TC",
        status=EntryStatus.POSTED,
        posted_at=datetime(2024, 1, 15, 8, 0, tzinfo=UTC),
        lines=(
            JournalLine(
                account_id="411000",
                debit=Money.from_str("100.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707000",
                debit=Money.zero(EUR),
                credit=Money.from_str("100.00", EUR),
            ),
        ),
    )


def _app(
    *,
    with_posted: bool = True,
) -> tuple[ReversalOrchestrator, InMemoryUnitOfWorkFactory, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PeriodId("p_2024_01"),
                entity_id=EntityId("ent"),
                fiscal_year_id=FiscalYearId("fy"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )
        )
        uow.periods.add(
            AccountingPeriod(
                id=PeriodId("p_2024_02"),
                entity_id=EntityId("ent"),
                fiscal_year_id=FiscalYearId("fy"),
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 29),
            )
        )
        if with_posted:
            uow.entries.add(_posted_entry())
        uow.commit()
    counter = iter(range(1000))
    orchestrator = ReversalOrchestrator(
        uow_factory=factory,
        reversal_id_factory=lambda: EntryId(f"rev_{next(counter)}"),
    )
    return orchestrator, factory, store


def test_reverse_happy_path_persists_reversal() -> None:
    orchestrator, factory, store = _app()
    result = orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 10), actor_id="u1")
    assert result.was_replayed is False
    assert result.reversal_entry.reversal_of_id == EntryId("e1")
    assert result.reversal_entry.status is EntryStatus.POSTED
    reversal = store.entries[result.reversal_entry.id]
    assert reversal.reversal_of_id == EntryId("e1")
    marked = store.entries[EntryId("e1")]
    assert marked.reversed_by_id == result.reversal_entry.id
    assert marked.lines == _posted_entry().lines


def test_reverse_rejects_already_reversed() -> None:
    orchestrator, factory, store = _app()
    orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 10), actor_id="u1")
    with pytest.raises(AlreadyReversedError):
        orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 11), actor_id="u1")


def test_reverse_rejects_non_posted_entry() -> None:
    orchestrator, factory, store = _app(with_posted=False)
    draft_saved = JournalEntry(
        id=EntryId("e1"),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="brouillon",
        lines=(_posted_entry().lines),
    )
    with factory.open() as uow:
        uow.entries.add(draft_saved)
        uow.commit()
    with pytest.raises(EntryNotFoundError, match="non postée"):
        orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 10), actor_id="u1")


def _closed_february_period() -> AccountingPeriod:
    return AccountingPeriod(
        id=PeriodId("p_2024_02"),
        entity_id=EntityId("ent"),
        fiscal_year_id=FiscalYearId("fy"),
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 29),
        status=ClosingStatus.CLOSED,
    )


def test_reverse_rejects_closed_target_period() -> None:
    orchestrator, factory, store = _app()
    store.periods[PeriodId("p_2024_02")] = _closed_february_period()
    with pytest.raises(PeriodClosedError):
        orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 10), actor_id="u1")


def test_reverse_duplicate_request_replays_cleanly() -> None:
    orchestrator, factory, store = _app()
    first = orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 10), actor_id="u1")
    second = orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 10), actor_id="u1")
    assert first.was_replayed is False
    assert second.was_replayed is True
    audit_count = [r.event_type for r in store.audit_log].count("ENTRY_REVERSED")
    assert audit_count == 1
    reversals = [e for e in store.entries.values() if e.reversal_of_id == EntryId("e1")]
    assert len(reversals) == 1


def test_failed_reversal_leaves_no_partial_state() -> None:
    orchestrator, factory, store = _app()
    store.periods[PeriodId("p_2024_02")] = _closed_february_period()
    with pytest.raises(PeriodClosedError):
        orchestrator.reverse(EntryId("e1"), "p_2024_02", date(2024, 2, 10), actor_id="u1")
    assert len(store.entries) == 1
    assert [e.id for e in store.entries.values()] == [EntryId("e1")]
    assert store.entries[EntryId("e1")].reversed_by_id is None
