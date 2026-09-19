"""PostgreSQL concurrency qualification for the Django adapter."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from threading import Barrier, Event

import pytest

if os.getenv("PYAK_POSTGRES_TEST") != "1":
    pytest.skip("PostgreSQL adapter qualification is disabled", allow_module_level=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.support.django_settings")

import django

django.setup()

from django.db import close_old_connections

from pyaccountingkit.adapters.django.models import (
    AccountingPeriodModel,
    AuditEventModel,
    IdempotencyRecordModel,
    JournalEntryModel,
    JournalLineModel,
    JournalModel,
    OutboxMessageModel,
)
from pyaccountingkit.adapters.django.repositories import (
    DjangoIdempotencyStore,
    DjangoJournalEntryRepository,
)
from pyaccountingkit.adapters.django.unit_of_work import DjangoUnitOfWorkFactory
from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.application.ledger.reversal_orchestrator import ReversalOrchestrator
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import PeriodClosedError, RevisionConflictError
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

NOW = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
ENTITY = EntityId("entity:postgres")
JOURNAL_ID = JournalId("journal:sales")
PERIOD_ID = PeriodId("period:2026-09")


@pytest.fixture(autouse=True)
def clean_postgresql_adapter_tables() -> None:
    JournalLineModel.objects.all().delete()
    JournalEntryModel.objects.all().update(reversal_of=None, reversed_by=None)
    JournalEntryModel.objects.all().delete()
    OutboxMessageModel.objects.all().delete()
    AuditEventModel.objects.all().delete()
    IdempotencyRecordModel.objects.all().delete()
    AccountingPeriodModel.objects.all().delete()
    JournalModel.objects.all().delete()


def _journal() -> Journal:
    return Journal(
        id=JOURNAL_ID,
        entity_id=ENTITY,
        code="SAL",
        label="Sales",
    )


def _period() -> AccountingPeriod:
    return AccountingPeriod(
        id=PERIOD_ID,
        entity_id=ENTITY,
        fiscal_year_id=FiscalYearId("fy:2026"),
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )


def _entry(entry_id: str = "entry:1") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JOURNAL_ID,
        period_id=PERIOD_ID,
        entry_date=date(2026, 9, 18),
        description="PostgreSQL concurrency fixture",
        lines=(
            JournalLine(
                account_id=AccountId("411000"),
                debit=Money.from_str("100.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id=AccountId("707000"),
                debit=Money.zero(EUR),
                credit=Money.from_str("100.00", EUR),
            ),
        ),
    )


def _seed(*, posted: bool = False) -> DjangoUnitOfWorkFactory:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    entry = _entry()
    if posted:
        entry = entry.freeze(NOW)
    with factory.open() as uow:
        uow.journals.add(_journal())
        uow.periods.add(_period())
        uow.entries.add(entry)
        uow.commit()
    return factory


def _chart_resolver() -> InMemoryVersionedCompanyChartResolver:
    chart = CompanyChartOfAccounts(
        entity_id=ENTITY,
        accounts=(
            CompanyAccount(
                id=AccountId("411000"),
                entity_id=ENTITY,
                code="411000",
                label="Customers",
            ),
            CompanyAccount(
                id=AccountId("707000"),
                entity_id=ENTITY,
                code="707000",
                label="Revenue",
            ),
        ),
    )
    config = CompanyChart(
        chart_id="chart:postgres",
        entity_id=ENTITY,
        code="STD",
        label="PostgreSQL test chart",
        primary_standard="fr-pcg",
        code_policy_id="numeric",
        reference_snapshot_id="snapshot:postgres",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=ChartStatus.ACTIVE,
                effective_from=date(2026, 1, 1),
            ),
        ),
    )
    return InMemoryVersionedCompanyChartResolver(config, {"v1": chart})


def test_competing_optimistic_saves_allow_exactly_one_revision_winner() -> None:
    _seed()
    barrier = Barrier(2)

    def worker(hour: int) -> str:
        close_old_connections()
        try:
            repository = DjangoJournalEntryRepository()
            entry = repository.get(EntryId("entry:1"))
            revision = repository.get_revision(EntryId("entry:1"))
            barrier.wait(timeout=5)
            repository.save(entry.freeze(NOW.replace(hour=hour)), revision)
            return "saved"
        except RevisionConflictError:
            return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(worker, (11, 12)))

    assert outcomes == ["conflict", "saved"]
    assert DjangoJournalEntryRepository().get_revision(EntryId("entry:1")).value == 1
    assert JournalEntryModel.objects.get(pk="entry:1").status == EntryStatus.POSTED.value


def test_competing_idempotency_claims_have_one_database_winner() -> None:
    barrier = Barrier(2)

    def worker() -> bool:
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return DjangoIdempotencyStore().claim("post:entry:race")
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _: worker(), range(2)))

    assert outcomes == [False, True]
    assert IdempotencyRecordModel.objects.filter(pk="post:entry:race").count() == 1


def test_double_reversal_commits_one_reversal_and_replays_the_other_request() -> None:
    factory = _seed(posted=True)
    barrier = Barrier(2)

    def worker() -> tuple[str, bool]:
        close_old_connections()
        try:
            orchestrator = ReversalOrchestrator(
                factory,
                reversal_id_factory=lambda: EntryId("entry:reversal"),
            )
            barrier.wait(timeout=5)
            result = orchestrator.reverse(
                EntryId("entry:1"),
                PERIOD_ID,
                date(2026, 9, 19),
                actor_id="tester",
            )
            return str(result.reversal_entry.id), result.was_replayed
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: worker(), range(2)))

    assert {entry_id for entry_id, _ in results} == {"entry:reversal"}
    assert sorted(replayed for _, replayed in results) == [False, True]
    assert JournalEntryModel.objects.filter(reversal_of_id="entry:1").count() == 1
    original = JournalEntryModel.objects.get(pk="entry:1")
    assert original.status == EntryStatus.POSTED.value
    assert original.reversed_by_id == "entry:reversal"


def test_close_vs_post_serializes_on_period_lock_and_rejects_late_post() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    with factory.open() as seed:
        seed.journals.add(_journal())
        seed.periods.add(_period())
        seed.commit()

    period_locked = Event()

    def close_period() -> None:
        close_old_connections()
        try:
            with factory.open() as uow:
                period = uow.periods.get(PERIOD_ID)
                period_locked.set()
                time.sleep(0.25)
                closed = (
                    period.with_status(ClosingStatus.REVIEW)
                    .with_status(ClosingStatus.CLOSING)
                    .with_status(ClosingStatus.CLOSED)
                )
                uow.periods.save(closed)
                uow.commit()
        finally:
            close_old_connections()

    def post_entry() -> str:
        close_old_connections()
        try:
            assert period_locked.wait(timeout=5)
            orchestrator = PostingOrchestrator(
                factory,
                _chart_resolver(),
                PostingService(clock=FrozenClock(NOW)),
            )
            try:
                orchestrator.post(_entry("entry:late"), actor_id="tester")
            except PeriodClosedError:
                return "closed"
            return "posted"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        close_future = executor.submit(close_period)
        post_future = executor.submit(post_entry)
        close_future.result(timeout=10)
        outcome = post_future.result(timeout=10)

    assert outcome == "closed"
    assert AccountingPeriodModel.objects.get(pk=str(PERIOD_ID)).status == ClosingStatus.CLOSED.value
    assert JournalEntryModel.objects.filter(pk="entry:late").count() == 0
    assert IdempotencyRecordModel.objects.filter(pk="post:entry:late").count() == 0
