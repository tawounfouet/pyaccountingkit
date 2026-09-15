"""Unit tests for the transactional PostingOrchestrator (LOT-06 / LOT-QA-01)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    EntityScopeMismatchError,
    InactiveAccountError,
    InactiveJournalError,
    JournalNotFoundError,
    NonPostableAccountError,
    PeriodClosedError,
    PeriodNotFoundError,
    UnknownAccountError,
)
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import ChartStatus, CompanyChart, CompanyChartVersion
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus

NOW = datetime(2024, 1, 20, 9, 0, tzinfo=UTC)


def _chart() -> CompanyChartOfAccounts:
    entity = EntityId("ent")
    accounts = (
        CompanyAccount(id=AccountId("411000"), entity_id=entity, code="411000", label="Clients"),
        CompanyAccount(id=AccountId("707000"), entity_id=entity, code="707000", label="Ventes"),
        CompanyAccount(
            id=AccountId("41000"),
            entity_id=entity,
            code="41000",
            label="Clients groupe",
            postable=False,
        ),
        CompanyAccount(
            id=AccountId("441000"),
            entity_id=entity,
            code="441000",
            label="Soc inactive",
            active=False,
        ),
    )
    return CompanyChartOfAccounts(entity_id=entity, accounts=accounts)


def _chart_resolver() -> InMemoryVersionedCompanyChartResolver:
    config = CompanyChart(
        chart_id="chart:ent",
        entity_id=EntityId("ent"),
        code="STD",
        label="Standard",
        primary_standard="fr-pcg",
        code_policy_id="numeric",
        reference_snapshot_id="snap:1",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=ChartStatus.ACTIVE,
                effective_from=date(2024, 1, 1),
            ),
        ),
    )
    return InMemoryVersionedCompanyChartResolver(config, {"v1": _chart()})


def _period(
    status: ClosingStatus = ClosingStatus.OPEN,
    *,
    entity_id: EntityId = EntityId("ent"),
) -> AccountingPeriod:
    return AccountingPeriod(
        id=PeriodId("p_2024_01"),
        entity_id=entity_id,
        fiscal_year_id=FiscalYearId("fy"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        status=status,
    )


def _bak_app(
    period: AccountingPeriod | None = None,
    *,
    journal_entity_id: EntityId = EntityId("ent"),
) -> tuple[PostingOrchestrator, InMemoryUnitOfWorkFactory, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(period or _period())
        uow.journals.add(
            Journal(
                id=JournalId("j_ventes"),
                entity_id=journal_entity_id,
                code="V",
                label="Ventes",
            )
        )
        uow.commit()
    posting = PostingService(clock=FrozenClock(NOW))
    return PostingOrchestrator(factory, _chart_resolver(), posting), factory, store


def _draft(account_ids: tuple[str, str] = ("411000", "707000")) -> JournalEntry:
    return JournalEntry(
        id=EntryId("e1"),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="Vente du 15/01",
        lines=(
            JournalLine(
                account_id=account_ids[0],
                debit=Money.from_str("250.50", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id=account_ids[1],
                debit=Money.zero(EUR),
                credit=Money.from_str("250.50", EUR),
            ),
        ),
    )


def test_post_happy_path_is_persisted_and_posted() -> None:
    orchestrator, _, store = _bak_app()
    result = orchestrator.post(_draft(), actor_id="u1")
    assert result.posted_entry.status is EntryStatus.POSTED
    assert result.posted_entry.posted_at == NOW
    assert result.was_replayed is False
    assert store.entries[EntryId("e1")].status is EntryStatus.POSTED
    assert [event.event_type for event in store.audit_log] == ["ENTRY_POSTED"]
    assert store.audit_log[0].entity_id == "ent"
    assert store.audit_log[0].payload["chart_version"] == "v1"
    assert [record.event_type for record in store.drain_outbox()] == ["ENTRY_POSTED"]


def test_post_duplicate_request_replays_cleanly() -> None:
    orchestrator, _, store = _bak_app()
    first = orchestrator.post(_draft(), actor_id="u1")
    second = orchestrator.post(_draft(), actor_id="u1")
    assert first.was_replayed is False
    assert second.was_replayed is True
    assert second.posted_entry == first.posted_entry
    assert len(store.audit_log) == 1
    assert store.entries[EntryId("e1")].status is EntryStatus.POSTED


def test_post_rejects_period_from_another_entity() -> None:
    orchestrator, _, store = _bak_app(period=_period(entity_id=EntityId("other")))
    with pytest.raises(EntityScopeMismatchError):
        orchestrator.post(_draft(), actor_id="u1")
    assert store.entries == {}
    assert store.audit_log == []
    assert store.outbox == []


def test_post_rejects_journal_from_another_entity() -> None:
    orchestrator, _, store = _bak_app(journal_entity_id=EntityId("other"))
    with pytest.raises(EntityScopeMismatchError):
        orchestrator.post(_draft(), actor_id="u1")
    assert store.entries == {}
    assert store.audit_log == []
    assert store.outbox == []


def test_post_closed_period_rejected() -> None:
    orchestrator, _, _ = _bak_app(period=_period(status=ClosingStatus.CLOSED))
    with pytest.raises(PeriodClosedError):
        orchestrator.post(_draft(), actor_id="u1")


def test_post_missing_period_rejected() -> None:
    orchestrator, _, store = _bak_app()
    store.periods.clear()
    with pytest.raises(PeriodNotFoundError):
        orchestrator.post(_draft(), actor_id="u1")


def test_post_missing_journal_rejected() -> None:
    orchestrator, _, store = _bak_app()
    store.journals.clear()
    with pytest.raises(JournalNotFoundError):
        orchestrator.post(_draft(), actor_id="u1")


def test_post_inactive_journal_rejected() -> None:
    orchestrator, _, store = _bak_app()
    journal = store.journals[JournalId("j_ventes")]
    store.journals[JournalId("j_ventes")] = journal.deactivated()
    with pytest.raises(InactiveJournalError):
        orchestrator.post(_draft(), actor_id="u1")


def test_post_unknown_account_rejected() -> None:
    orchestrator, _, _ = _bak_app()
    with pytest.raises(UnknownAccountError):
        orchestrator.post(_draft(("999999", "707000")), actor_id="u1")


def test_post_inactive_account_rejected() -> None:
    orchestrator, _, _ = _bak_app()
    with pytest.raises(InactiveAccountError):
        orchestrator.post(_draft(("441000", "707000")), actor_id="u1")


def test_post_non_postable_account_rejected() -> None:
    orchestrator, _, _ = _bak_app()
    with pytest.raises(NonPostableAccountError):
        orchestrator.post(_draft(("41000", "707000")), actor_id="u1")


def test_failed_post_leaves_no_partial_state() -> None:
    orchestrator, _, store = _bak_app()
    with pytest.raises(UnknownAccountError):
        orchestrator.post(_draft(("999999", "707000")), actor_id="u1")
    assert store.entries == {}
    assert store.outbox == []
    assert store.audit_log == []
    result = orchestrator.post(_draft(), actor_id="u1")
    assert result.was_replayed is False
    assert store.entries[EntryId("e1")].status is EntryStatus.POSTED
