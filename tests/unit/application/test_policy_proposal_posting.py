"""End-to-end: policy → proposal → versioned role resolution → posting."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.adapters.in_memory.account_role_resolver import InMemoryAccountRoleResolver
from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.application.ledger.proposal_posting_orchestrator import (
    ProposalPostingOrchestrator,
)
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
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.policies.depreciation import StraightLineDepreciationPolicy
from pyaccountingkit.domain.policies.measurement import MeasurementContext, MeasurementPurpose
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace
from pyaccountingkit.domain.policies.proposal import (
    DebitCredit,
    JournalEntryLineProposal,
    JournalEntryProposal,
)

NOW = datetime(2026, 12, 31, 18, 0, tzinfo=UTC)
ENTITY = EntityId("ent")


def _chart() -> CompanyChartOfAccounts:
    return CompanyChartOfAccounts(
        entity_id=ENTITY,
        accounts=(
            CompanyAccount(
                id=AccountId("681100"),
                entity_id=ENTITY,
                code="681100",
                label="Dotations",
                role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
            ),
            CompanyAccount(
                id=AccountId("281500"),
                entity_id=ENTITY,
                code="281500",
                label="Amort. mat.",
                role=AccountRole.ACCUMULATED_DEPRECIATION_ACCOUNT,
            ),
        ),
    )


def _chart_resolver() -> InMemoryVersionedCompanyChartResolver:
    config = CompanyChart(
        chart_id="chart:ent",
        entity_id=ENTITY,
        code="STD-FR",
        label="Standard France",
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
    return InMemoryVersionedCompanyChartResolver(config, {"v1": _chart()})


def _posting(
    chart_resolver: InMemoryVersionedCompanyChartResolver,
) -> tuple[PostingOrchestrator, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PeriodId("p_2026_12"),
                entity_id=ENTITY,
                fiscal_year_id=FiscalYearId("fy_2026"),
                start_date=date(2026, 12, 1),
                end_date=date(2026, 12, 31),
                status=ClosingStatus.OPEN,
            )
        )
        uow.journals.add(
            Journal(
                id=JournalId("j_od"),
                entity_id=ENTITY,
                code="OD",
                label="Opérations diverses",
            )
        )
        uow.commit()
    posting = PostingService(clock=FrozenClock(NOW))
    return PostingOrchestrator(factory, chart_resolver, posting), store


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
    assert isinstance(depreciation.period_amount.amount, Decimal)

    trace = PolicyExecutionTrace(
        trace_id="tr:dep:2026",
        policy_type=PolicyType.DEPRECIATION,
        policy_id="dep-straight-line",
        policy_version="1.0",
        policy_set_id="ps:1",
        policy_set_version="3",
        accounting_entity_id=str(ENTITY),
        accounting_date=date(2026, 12, 31),
        reference_snapshot_id="snap:1",
        outcome="DEPRECIATION",
    )
    amount = depreciation.period_amount
    proposal = JournalEntryProposal(
        entity_id=ENTITY,
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

    chart_resolver = _chart_resolver()
    posting, store = _posting(chart_resolver)
    orchestrator = ProposalPostingOrchestrator(
        account_role_resolver=InMemoryAccountRoleResolver(chart_resolver),
        posting_orchestrator=posting,
        entry_id_factory=lambda: EntryId("e_dep_2026"),
    )
    result = orchestrator.post(
        proposal,
        journal_id=JournalId("j_od"),
        period_id=PeriodId("p_2026_12"),
        actor_id="u1",
        description="Dotation aux amortissements 2026",
    )

    assert result.posted_entry.status is EntryStatus.POSTED
    assert store.entries[EntryId("e_dep_2026")].status is EntryStatus.POSTED
    assert tuple(account.account_code for account in result.resolved_accounts) == (
        "681100",
        "281500",
    )
    assert result.execution_trace.company_chart_version == "v1"
    assert result.execution_trace.company_chart_reference_snapshot_id == "snap:1"
    assert result.execution_trace.policy_set_versions == ("3",)
    assert result.execution_trace.policy_versions == ("1.0",)
    assert result.execution_trace.proposal_checksum == proposal.checksum()
    assert result.execution_trace.journal_entry_id == EntryId("e_dep_2026")
    assert store.audit_log[-1].entity_id == "ent"
    assert store.audit_log[-1].payload["chart_version"] == "v1"
