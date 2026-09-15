"""End-to-end: policy → proposal → role resolution → posting (LOT-13).

Demonstrates the LOT-13 DoD: a measurement policy never posts directly; it
produces a ``JournalEntryProposal`` whose roles are resolved to company
accounts and then handed to the normal ``PostingOrchestrator``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.policies.depreciation import StraightLineDepreciationPolicy
from pyaccountingkit.domain.policies.measurement import MeasurementContext, MeasurementPurpose
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace
from pyaccountingkit.domain.policies.proposal import (
    AccountResolutionService,
    DebitCredit,
    JournalEntryLineProposal,
    JournalEntryProposal,
)

NOW = datetime(2026, 12, 31, 18, 0, tzinfo=UTC)


class RecordingAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def _chart() -> CompanyChartOfAccounts:
    entity = EntityId("ent")
    accounts = (
        CompanyAccount(id=AccountId("681100"), entity_id=entity, code="681100", label="Dotations"),
        CompanyAccount(
            id=AccountId("281500"),
            entity_id=entity,
            code="281500",
            label="Amort. mat.",
        ),
    )
    return CompanyChartOfAccounts(entity_id=entity, accounts=accounts)


def _orchestrator() -> tuple[PostingOrchestrator, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PeriodId("p_2026_12"),
                entity_id=EntityId("ent"),
                fiscal_year_id=FiscalYearId("fy_2026"),
                start_date=date(2026, 12, 1),
                end_date=date(2026, 12, 31),
                status=ClosingStatus.OPEN,
            )
        )
        uow.journals.add(
            Journal(
                id=JournalId("j_od"),
                entity_id=EntityId("ent"),
                code="OD",
                label="Opérations diverses",
            )
        )
        uow.commit()
    posting = PostingService(clock=FrozenClock(NOW), audit_sink=RecordingAuditSink())
    return PostingOrchestrator(factory, _chart(), posting), store


def test_measurement_to_proposal_to_posting() -> None:
    context = MeasurementContext(
        accounting_date=date(2026, 12, 31),
        functional_currency=EUR,
        measurement_purpose=MeasurementPurpose.SUBSEQUENT,
        policy_set_version="3",
        reference_snapshot_id="snap:1",
    )
    depreciation = StraightLineDepreciationPolicy().depreciate(
        depreciable_base=Money.from_str("12000.00", EUR),
        residual_value=Money.zero(EUR),
        useful_life_total=Decimal("5"),
        cumulative_before=Money.zero(EUR),
        period=(date(2026, 1, 1), date(2026, 12, 31)),
        context=context,
    )
    # Decimal is preserved end to end (no float anywhere).
    assert isinstance(depreciation.period_amount.amount, Decimal)

    trace = PolicyExecutionTrace(
        trace_id="tr:dep:2026",
        policy_type=PolicyType.DEPRECIATION,
        policy_id="dep-straight-line",
        policy_version="1.0",
        policy_set_id="ps:1",
        policy_set_version="3",
        accounting_entity_id="ent",
        accounting_date=date(2026, 12, 31),
        reference_snapshot_id="snap:1",
        outcome="DEPRECIATION",
    )
    amount = depreciation.period_amount
    proposal = JournalEntryProposal(
        entity_id=EntityId("ent"),
        accounting_date=date(2026, 12, 31),
        entry_type="DEPRECIATION",
        source="policy",
        source_reference="dep:2026",
        policy_traces=(trace,),
        lines=(
            JournalEntryLineProposal(
                account_role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
                side=DebitCredit.DEBIT,
                amount=amount,
            ),
            JournalEntryLineProposal(
                account_role=AccountRole.ACCUMULATED_DEPRECIATION_ACCOUNT,
                side=DebitCredit.CREDIT,
                amount=amount,
            ),
        ),
    )
    assert proposal.is_balanced() is True

    resolution = AccountResolutionService(
        candidates_by_role={
            AccountRole.DEPRECIATION_EXPENSE_ACCOUNT: ("681100",),
            AccountRole.ACCUMULATED_DEPRECIATION_ACCOUNT: ("281500",),
        }
    )
    resolved = tuple(
        resolution.resolve(role=line.account_role, entity_id=proposal.entity_id)
        for line in proposal.lines
    )
    assert resolved == ("681100", "281500")

    entry = JournalEntry(
        id=EntryId("e_dep_2026"),
        journal_id=JournalId("j_od"),
        period_id=PeriodId("p_2026_12"),
        entry_date=proposal.accounting_date,
        description="Dotation aux amortissements 2026",
        lines=tuple(
            JournalLine(
                account_id=account_id,
                debit=line.amount if line.side is DebitCredit.DEBIT else Money.zero(EUR),
                credit=line.amount if line.side is DebitCredit.CREDIT else Money.zero(EUR),
            )
            for account_id, line in zip(resolved, proposal.lines, strict=True)
        ),
    )

    orchestrator, store = _orchestrator()
    result = orchestrator.post(entry, actor_id="u1")

    assert result.posted_entry.status is EntryStatus.POSTED
    assert store.entries[EntryId("e_dep_2026")].status is EntryStatus.POSTED
    # Policy snapshot and reference snapshot stay pinned in the trace.
    assert proposal.policy_traces[0].reference_snapshot_id == "snap:1"
    assert proposal.policy_traces[0].policy_set_version == "3"
