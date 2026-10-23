"""Unit tests for the closing orchestrator (LOT-09)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import (
    InMemoryUnitOfWork,
    InMemoryUnitOfWorkFactory,
)
from pyaccountingkit.application.closing.closing_orchestrator import ClosingOrchestrator
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    ControlFailureError,
    EntityScopeMismatchError,
    PeriodClosedError,
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
from pyaccountingkit.domain.closing.closing_run import (
    CloseGate,
    ClosingEvidenceError,
    ClosingRunBook,
)
from pyaccountingkit.domain.controls.control import (
    ControlOutcome,
    ControlResult,
    ControlRun,
)
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance, TrialBalanceSnapshot

NOW = datetime(2024, 12, 31, 23, 0, tzinfo=UTC)
ENTITY = EntityId("ent")


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
        reference_snapshot_id="snap:core",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=ChartStatus.ACTIVE,
                effective_from=date(2024, 1, 1),
            ),
        ),
    )
    return InMemoryVersionedCompanyChartResolver(config, {"v1": _chart()})


def _periods() -> dict[PeriodId, AccountingPeriod]:
    fy = FiscalYearId("fy")
    return {
        PeriodId("p_2024_12"): AccountingPeriod(
            id=PeriodId("p_2024_12"),
            entity_id=ENTITY,
            fiscal_year_id=fy,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            status=ClosingStatus.OPEN,
        ),
        PeriodId("p_2025_01"): AccountingPeriod(
            id=PeriodId("p_2025_01"),
            entity_id=ENTITY,
            fiscal_year_id=fy,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            status=ClosingStatus.OPEN,
        ),
    }


def _tb(
    *,
    period_id: str = "p_2024_12",
    entity_id: EntityId | None = ENTITY,
    snapshot: TrialBalanceSnapshot = TrialBalanceSnapshot.POST_CLOSING,
    amount: str = "250.00",
) -> TrialBalance:
    lines = (
        AccountBalanceLine(
            account_id=AccountId("411000"),
            account_code="411000",
            label="Clients",
            sum_debit=Money.from_str(amount, EUR),
            sum_credit=Money.zero(EUR),
        ),
        AccountBalanceLine(
            account_id=AccountId("707000"),
            account_code="707000",
            label="Ventes",
            sum_debit=Money.zero(EUR),
            sum_credit=Money.from_str(amount, EUR),
        ),
    )
    return TrialBalance.build(
        period_id,
        snapshot,
        lines,
        accounting_entity_id=entity_id,
    )


def _control(outcome: ControlOutcome, code: str = "BALANCE") -> ControlRun:
    return ControlRun(
        id=f"cr_{code}_{outcome.value}",
        definition_code=code,
        version=1,
        period_id="p_2024_12",
        result=ControlResult(outcome=outcome, detail="ok"),
        executed_at=NOW,
    )


def _build(
    *,
    fresh_balance: TrialBalance | None = None,
) -> tuple[ClosingOrchestrator, InMemoryUnitOfWorkFactory, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        for period in _periods().values():
            uow.periods.add(period)
        uow.journals.add(
            Journal(id=JournalId("j_ventes"), entity_id=ENTITY, code="V", label="Ventes")
        )
        uow.commit()
    book = ClosingRunBook()
    gate = CloseGate()
    gate.require("BALANCE")
    current_balance = fresh_balance or _tb()
    posting = PostingOrchestrator(
        factory,
        _chart_resolver(),
        PostingService(clock=FrozenClock(NOW)),
    )
    orchestrator = ClosingOrchestrator(
        factory,
        book,
        gate,
        run_id_factory=lambda: "c1",
        clock=FrozenClock(NOW),
        trial_balance_provider=lambda uow, period_id, snapshot: current_balance,
        posting_orchestrator=posting,
    )
    return orchestrator, factory, store


def test_close_seals_period_and_records_evidence() -> None:
    orchestrator, _, store = _build()
    run = orchestrator.close_period(
        PeriodId("p_2024_12"),
        control_runs=[_control(ControlOutcome.PASS)],
        trial_balance=_tb(),
    )
    assert run.is_sealed
    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.CLOSED
    assert run.evidence is not None
    assert run.evidence.trial_balance_checksum == _tb().checksum
    closing_audit = [event for event in store.audit_log if event.event_type == "CLOSING_SEALED"]
    closing_outbox = [record for record in store.outbox if record.event_type == "CLOSING_SEALED"]
    assert len(closing_audit) == 1
    assert len(closing_outbox) == 1
    assert closing_audit[0].payload["evidence_digest"] == run.evidence_digest()
    assert closing_outbox[0].payload["evidence_digest"] == run.evidence_digest()


def test_post_rejected_after_close() -> None:
    orchestrator, factory, store = _build()
    posting = PostingOrchestrator(
        factory,
        _chart_resolver(),
        PostingService(clock=FrozenClock(NOW)),
    )
    first = posting.post(_balanced_draft("e1").validate(), actor_id="u1")
    assert first.posted_entry.status is EntryStatus.POSTED
    orchestrator.close_period(
        PeriodId("p_2024_12"),
        control_runs=[_control(ControlOutcome.PASS)],
        trial_balance=_tb(),
    )
    with pytest.raises(PeriodClosedError):
        posting.post(_balanced_draft("e2").validate(), actor_id="u1")
    assert EntryId("e2") not in store.entries


def _balanced_draft(entry_id: str) -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_12"),
        entry_date=date(2024, 12, 15),
        description="Vente du 15/12",
        lines=(
            JournalLine(
                account_id="411000",
                debit=Money.from_str("250.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707000",
                debit=Money.zero(EUR),
                credit=Money.from_str("250.00", EUR),
            ),
        ),
    )


def test_missing_blocking_control_prevents_close() -> None:
    orchestrator, _, store = _build()

    with pytest.raises(ControlFailureError, match="absents.*BALANCE"):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[],
            trial_balance=_tb(),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN


def test_error_blocking_control_prevents_close() -> None:
    orchestrator, _, store = _build()

    with pytest.raises(ControlFailureError, match="BALANCE:ERROR"):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.ERROR)],
            trial_balance=_tb(),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN


def test_closing_rejects_balance_for_another_period() -> None:
    orchestrator, _, store = _build()

    with pytest.raises(ClosingEvidenceError, match="targets period"):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.PASS)],
            trial_balance=_tb(period_id="p_2024_11"),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN


def test_closing_rejects_balance_for_another_entity() -> None:
    orchestrator, _, store = _build()

    with pytest.raises(EntityScopeMismatchError, match="closing balance belongs to entity"):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.PASS)],
            trial_balance=_tb(entity_id=EntityId("other")),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN


def test_closing_rejects_non_post_closing_balance() -> None:
    orchestrator, _, store = _build()

    with pytest.raises(ClosingEvidenceError, match="must be POST_CLOSING"):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.PASS)],
            trial_balance=_tb(snapshot=TrialBalanceSnapshot.ADJUSTED),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN


def test_closing_rejects_stale_balance_checksum() -> None:
    orchestrator, _, store = _build(fresh_balance=_tb(amount="300.00"))

    with pytest.raises(ClosingEvidenceError, match="stale"):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.PASS)],
            trial_balance=_tb(amount="250.00"),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN


def test_blocking_control_failure_prevents_close() -> None:
    orchestrator, _, store = _build()
    with pytest.raises(ControlFailureError):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.FAIL)],
            trial_balance=_tb(),
        )
    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN
    assert store.entries == {}


def test_opening_target_scope_failure_rolls_back_entire_close() -> None:
    orchestrator, factory, store = _build()
    foreign_period = AccountingPeriod(
        id=PeriodId("p_foreign"),
        entity_id=EntityId("other"),
        fiscal_year_id=FiscalYearId("fy:other"),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        status=ClosingStatus.OPEN,
    )
    with factory.open() as uow:
        uow.periods.add(foreign_period)
        uow.commit()

    with pytest.raises(EntityScopeMismatchError):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.PASS)],
            trial_balance=_tb(),
            next_period_id=PeriodId("p_foreign"),
            opening_journal_id=JournalId("j_ventes"),
            opening_entry_id=EntryId("o-foreign"),
            opening_date=date(2025, 1, 1),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN
    assert EntryId("o-foreign") not in store.entries
    assert not any(event.event_type == "CLOSING_SEALED" for event in store.audit_log)


def test_commit_failure_rolls_back_period_opening_and_closing_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orchestrator, _, store = _build()

    def fail_commit(self: InMemoryUnitOfWork) -> None:
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(InMemoryUnitOfWork, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.PASS)],
            trial_balance=_tb(),
            next_period_id=PeriodId("p_2025_01"),
            opening_journal_id=JournalId("j_ventes"),
            opening_entry_id=EntryId("o-rollback"),
            opening_date=date(2025, 1, 1),
        )

    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN
    assert EntryId("o-rollback") not in store.entries
    assert not any(event.event_type == "CLOSING_SEALED" for event in store.audit_log)
    assert not any(record.event_type == "CLOSING_SEALED" for record in store.outbox)


def test_close_generates_traceable_opening_balances() -> None:
    orchestrator, _, store = _build()
    orchestrator.close_period(
        PeriodId("p_2024_12"),
        control_runs=[_control(ControlOutcome.PASS)],
        trial_balance=_tb(),
        next_period_id=PeriodId("p_2025_01"),
        opening_journal_id=JournalId("j_ventes"),
        opening_entry_id=EntryId("o2025"),
        opening_date=date(2025, 1, 1),
    )
    opening = store.entries[EntryId("o2025")]
    assert opening.period_id == PeriodId("p_2025_01")
    assert opening.status is EntryStatus.POSTED
    assert opening.posted_at == NOW
    assert opening.is_balanced()
    assert "c1" in opening.description
    assert store.periods[PeriodId("p_2025_01")].status is ClosingStatus.OPEN
    assert any(
        event.event_type == "ENTRY_POSTED" and event.payload["entry_id"] == "o2025"
        for event in store.audit_log
    )
