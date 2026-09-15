"""Atomic batch posting qualification used by accounting imports."""

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.company_chart_resolver import InMemoryVersionedCompanyChartResolver
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import UnknownAccountError
from pyaccountingkit.core.identifiers import AccountId, EntityId, EntryId, FiscalYearId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import ChartStatus, CompanyChart, CompanyChartVersion
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod

ENTITY = EntityId("ent")
NOW = datetime(2026, 1, 20, 9, 0, tzinfo=UTC)


def _orchestrator() -> tuple[PostingOrchestrator, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PeriodId("p1"),
                entity_id=ENTITY,
                fiscal_year_id=FiscalYearId("fy"),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )
        )
        uow.journals.add(
            Journal(id=JournalId("j1"), entity_id=ENTITY, code="AC", label="Achats")
        )
        uow.commit()

    chart = CompanyChartOfAccounts(
        entity_id=ENTITY,
        accounts=(
            CompanyAccount(
                id=AccountId("401000"),
                entity_id=ENTITY,
                code="401000",
                label="Fournisseurs",
            ),
            CompanyAccount(
                id=AccountId("512000"),
                entity_id=ENTITY,
                code="512000",
                label="Banque",
            ),
        ),
    )
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
                effective_from=date(2026, 1, 1),
            ),
        ),
    )
    resolver = InMemoryVersionedCompanyChartResolver(config, {"v1": chart})
    posting = PostingOrchestrator(
        factory,
        resolver,
        PostingService(clock=FrozenClock(NOW)),
    )
    return posting, store


def _entry(entry_id: str, debit_account: str = "401000") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j1"),
        period_id=PeriodId("p1"),
        entry_date=date(2026, 1, 15),
        description=entry_id,
        lines=(
            JournalLine(
                account_id=AccountId(debit_account),
                debit=Money.from_str("10.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id=AccountId("512000"),
                debit=Money.zero(EUR),
                credit=Money.from_str("10.00", EUR),
            ),
        ),
    )


def test_post_many_rolls_back_all_entries_if_one_entry_fails() -> None:
    posting, store = _orchestrator()
    with pytest.raises(UnknownAccountError):
        posting.post_many(
            (_entry("e1"), _entry("e2", debit_account="999999")),
            actor_id="migration",
        )
    assert store.entries == {}
    assert store.audit_log == []
    assert store.outbox == []
