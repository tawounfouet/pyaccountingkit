"""Unit tests for the transactional PostingOrchestrator (LOT-06 / LOT-QA-01)."""

from __future__ import annotations

from dataclasses import replace
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
    IdempotencyConflictError,
    InactiveAccountError,
    InactiveJournalError,
    InvalidEntryStateError,
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
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus

NOW = datetime(2024, 1, 20, 9, 0, tzinfo=UTC)
ENTITY = EntityId("ent")
OTHER_ENTITY = EntityId("other")


def _chart() -> CompanyChartOfAccounts:
    accounts = (
        CompanyAccount(
            id=AccountId("411000"),
            entity_id=ENTITY,
            code="411000",
            label="Clients",
        ),
        CompanyAccount(
            id=AccountId("707000"),
            entity_id=ENTITY,
            code="707000",
            label="Ventes",
        ),
        CompanyAccount(
            id=AccountId("41000"),
            entity_id=ENTITY,
            code="41000",
            label="Clients groupe",
            postable=False,
        ),
        CompanyAccount(
            id=AccountId("441000"),
            entity_id=ENTITY,
            code="441000",
            label="Soc inactive",
            active=False,
        ),
        CompanyAccount(
            id=AccountId("account:customers"),
            entity_id=ENTITY,
            code="411777",
            label="Clients opaque id",
        ),
        CompanyAccount(
            id=AccountId("account:revenue"),
            entity_id=ENTITY,
            code="707777",
            label="Ventes opaque id",
        ),
    )
    return CompanyChartOfAccounts(entity_id=ENTITY, accounts=accounts)


def _chart_resolver() -> InMemoryVersionedCompanyChartResolver:
    config = CompanyChart(
        chart_id="chart:ent",
        entity_id=ENTITY,
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
    entity_id: EntityId = ENTITY,
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
    journal_entity_id: EntityId = ENTITY,
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


def _draft(
    account_ids: tuple[str, str] = ("411000", "707000"),
    *,
    validated: bool = True,
) -> JournalEntry:
    entry = JournalEntry(
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
    return entry.validate() if validated else entry


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


def test_post_persisted_validated_entry_uses_existing_revision() -> None:
    orchestrator, factory, store = _bak_app()
    entry = _draft()

    with factory.open() as uow:
        uow.entries.add(entry)
        uow.commit()

    result = orchestrator.post(entry, actor_id="u1")

    assert result.posted_entry.status is EntryStatus.POSTED
    assert store.entries[EntryId("e1")].status is EntryStatus.POSTED
    assert store.entry_revisions[EntryId("e1")].value == 1
    assert len(store.audit_log) == 1


def test_post_duplicate_request_replays_cleanly() -> None:
    orchestrator, _, store = _bak_app()
    first = orchestrator.post(_draft(), actor_id="u1")
    second = orchestrator.post(_draft(), actor_id="u1")
    assert first.was_replayed is False
    assert second.was_replayed is True
    assert second.posted_entry == first.posted_entry
    assert len(store.audit_log) == 1
    assert store.entries[EntryId("e1")].status is EntryStatus.POSTED


def test_post_duplicate_key_with_different_payload_is_conflict() -> None:
    orchestrator, _, store = _bak_app()
    orchestrator.post(_draft(), actor_id="u1")

    with pytest.raises(IdempotencyConflictError):
        orchestrator.post(
            replace(_draft(), description="different semantic payload"),
            actor_id="u1",
        )

    assert len(store.audit_log) == 1
    assert len(store.outbox) == 1


def test_post_duplicate_key_with_different_journal_scope_is_conflict() -> None:
    orchestrator, factory, store = _bak_app()
    orchestrator.post(_draft(), actor_id="u1")

    with factory.open() as uow:
        uow.journals.add(
            Journal(
                id=JournalId("j_other"),
                entity_id=ENTITY,
                code="O",
                label="Other journal",
            )
        )
        uow.commit()

    with pytest.raises(IdempotencyConflictError):
        orchestrator.post(
            replace(_draft(), journal_id=JournalId("j_other")),
            actor_id="u1",
        )

    assert len(store.audit_log) == 1
    assert len(store.outbox) == 1


def test_post_rejects_period_from_another_entity() -> None:
    orchestrator, _, store = _bak_app(period=_period(entity_id=OTHER_ENTITY))
    with pytest.raises(EntityScopeMismatchError):
        orchestrator.post(_draft(), actor_id="u1")
    assert store.entries == {}
    assert store.audit_log == []
    assert store.outbox == []


def test_post_rejects_journal_from_another_entity() -> None:
    orchestrator, _, store = _bak_app(journal_entity_id=OTHER_ENTITY)
    with pytest.raises(EntityScopeMismatchError):
        orchestrator.post(_draft(), actor_id="u1")
    assert store.entries == {}
    assert store.audit_log == []
    assert store.outbox == []


def test_post_rejects_draft_entry_before_persistence() -> None:
    orchestrator, _, store = _bak_app()
    with pytest.raises(InvalidEntryStateError, match="VALIDATED"):
        orchestrator.post(_draft(validated=False), actor_id="u1")
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


def test_post_resolves_accounts_by_opaque_account_id_not_by_code() -> None:
    orchestrator, _, store = _bak_app()
    result = orchestrator.post(
        _draft(("account:customers", "account:revenue")),
        actor_id="u1",
    )

    assert result.posted_entry.status is EntryStatus.POSTED
    assert tuple(line.account_id for line in result.posted_entry.lines) == (
        AccountId("account:customers"),
        AccountId("account:revenue"),
    )
    assert store.entries[EntryId("e1")].status is EntryStatus.POSTED


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
