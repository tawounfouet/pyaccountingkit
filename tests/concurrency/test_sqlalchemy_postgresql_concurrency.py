"""PostgreSQL concurrency qualification for the SQLAlchemy adapter."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from threading import Barrier, Event

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

if os.getenv("PYAK_SQLALCHEMY_POSTGRES_TEST") != "1":
    pytest.skip("SQLAlchemy/PostgreSQL qualification is disabled", allow_module_level=True)

from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.sqlalchemy.repositories import (
    SQLAlchemyIdempotencyStore,
    SQLAlchemyJournalEntryRepository,
)
from pyaccountingkit.adapters.sqlalchemy.tables import (
    AccountingPeriodTable,
    IdempotencyRecordTable,
    JournalEntryTable,
)
from pyaccountingkit.adapters.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWorkFactory
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

NOW = datetime(2026, 9, 19, 15, 30, tzinfo=UTC)
ENTITY = EntityId("entity:sqlalchemy")
JOURNAL_ID = JournalId("journal:sales")
PERIOD_ID = PeriodId("period:2026-09")
DATABASE_URL = os.environ["PYAK_SQLALCHEMY_DATABASE_URL"]
ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)


@pytest.fixture(autouse=True)
def clean_postgresql_adapter_tables() -> None:
    with ENGINE.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE "
                "pyak_journal_line, pyak_journal_entry, pyak_outbox, "
                "pyak_audit_event, pyak_idempotency, pyak_accounting_period, "
                "pyak_journal RESTART IDENTITY CASCADE"
            )
        )


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
        entry_date=date(2026, 9, 19),
        description="SQLAlchemy/PostgreSQL concurrency fixture",
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


def _factory() -> SQLAlchemyUnitOfWorkFactory:
    return SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))


def _seed(*, posted: bool = False) -> SQLAlchemyUnitOfWorkFactory:
    factory = _factory()
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
        chart_id="chart:sqlalchemy",
        entity_id=ENTITY,
        code="STD",
        label="SQLAlchemy PostgreSQL test chart",
        primary_standard="fr-pcg",
        code_policy_id="numeric",
        reference_snapshot_id="snapshot:sqlalchemy",
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
        with Session(ENGINE) as session:
            repository = SQLAlchemyJournalEntryRepository(session)
            revision = repository.get_revision(EntryId("entry:1"))
            barrier.wait(timeout=5)
            try:
                repository.save(_entry().freeze(NOW.replace(hour=hour)), revision)
                session.commit()
                return "saved"
            except RevisionConflictError:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(worker, (16, 17)))

    assert outcomes == ["conflict", "saved"]
    with Session(ENGINE) as session:
        repository = SQLAlchemyJournalEntryRepository(session)
        assert repository.get_revision(EntryId("entry:1")).value == 1
        stored = session.get(JournalEntryTable, "entry:1")
        assert stored is not None
        assert stored.status == EntryStatus.POSTED.value


def test_competing_idempotency_claims_have_one_database_winner() -> None:
    barrier = Barrier(2)

    def worker() -> bool:
        with Session(ENGINE) as session:
            store = SQLAlchemyIdempotencyStore(session)
            barrier.wait(timeout=5)
            claimed = store.claim("post:entry:race")
            if claimed:
                session.commit()
            else:
                session.rollback()
            return claimed

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _: worker(), range(2)))

    assert outcomes == [False, True]
    with Session(ENGINE) as session:
        assert session.get(IdempotencyRecordTable, "post:entry:race") is not None


def test_double_reversal_commits_one_reversal_and_replays_the_other_request() -> None:
    factory = _seed(posted=True)
    barrier = Barrier(2)

    def worker() -> tuple[str, bool]:
        orchestrator = ReversalOrchestrator(
            factory,
            reversal_id_factory=lambda: EntryId("entry:reversal"),
        )
        barrier.wait(timeout=5)
        result = orchestrator.reverse(
            EntryId("entry:1"),
            PERIOD_ID,
            date(2026, 9, 20),
            actor_id="tester",
        )
        return str(result.reversal_entry.id), result.was_replayed

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: worker(), range(2)))

    assert {entry_id for entry_id, _ in results} == {"entry:reversal"}
    assert sorted(replayed for _, replayed in results) == [False, True]
    with Session(ENGINE) as session:
        reversals = session.scalars(
            select(JournalEntryTable).where(JournalEntryTable.reversal_of_id == "entry:1")
        ).all()
        assert len(reversals) == 1
        original = session.get(JournalEntryTable, "entry:1")
        assert original is not None
        assert original.status == EntryStatus.POSTED.value
        assert original.reversed_by_id == "entry:reversal"


def test_close_vs_post_serializes_on_period_lock_and_rejects_late_post() -> None:
    factory = _factory()
    with factory.open() as seed:
        seed.journals.add(_journal())
        seed.periods.add(_period())
        seed.commit()

    period_locked = Event()

    def close_period() -> None:
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

    def post_entry() -> str:
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

    with ThreadPoolExecutor(max_workers=2) as executor:
        close_future = executor.submit(close_period)
        post_future = executor.submit(post_entry)
        close_future.result(timeout=10)
        outcome = post_future.result(timeout=10)

    assert outcome == "closed"
    with Session(ENGINE) as session:
        period = session.get(AccountingPeriodTable, str(PERIOD_ID))
        assert period is not None
        assert period.status == ClosingStatus.CLOSED.value
        assert session.get(JournalEntryTable, "entry:late") is None
        assert session.get(IdempotencyRecordTable, "post:entry:late") is None
