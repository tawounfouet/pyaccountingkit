"""Replay qualification for policy proposals and versioned company charts."""

from __future__ import annotations

from datetime import date

from pyaccountingkit.adapters.in_memory.account_role_resolver import InMemoryAccountRoleResolver
from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import ChartStatus, CompanyChart, CompanyChartVersion
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace
from pyaccountingkit.domain.policies.proposal import (
    DebitCredit,
    JournalEntryLineProposal,
    JournalEntryProposal,
)

ENTITY = EntityId("ent")


def _trace(policy_version: str = "1.0") -> PolicyExecutionTrace:
    return PolicyExecutionTrace(
        trace_id=f"trace:{policy_version}",
        policy_type=PolicyType.DEPRECIATION,
        policy_id="dep-straight-line",
        policy_version=policy_version,
        policy_set_id="ps:1",
        policy_set_version="3",
        accounting_entity_id=str(ENTITY),
        accounting_date=date(2026, 6, 30),
        reference_snapshot_id="snap:pcg:2026",
        outcome="DEPRECIATION",
    )


def _proposal(policy_version: str = "1.0") -> JournalEntryProposal:
    amount = Money.from_str("100.00", EUR)
    return JournalEntryProposal(
        entity_id=ENTITY,
        accounting_date=date(2026, 6, 30),
        entry_type="DEPRECIATION",
        source="policy",
        source_reference="asset:42",
        policy_traces=(_trace(policy_version),),
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


def _accounts(version: str, expense_code: str) -> CompanyChartOfAccounts:
    return CompanyChartOfAccounts(
        entity_id=ENTITY,
        accounts=(
            CompanyAccount(
                id=AccountId(f"{version}:{expense_code}"),
                entity_id=ENTITY,
                code=expense_code,
                label="Dotations",
                role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
            ),
            CompanyAccount(
                id=AccountId(f"{version}:281500"),
                entity_id=ENTITY,
                code="281500",
                label="Amortissements cumulés",
                role=AccountRole.ACCUMULATED_DEPRECIATION_ACCOUNT,
            ),
        ),
    )


def _resolver() -> InMemoryAccountRoleResolver:
    company_chart = CompanyChart(
        chart_id="chart:ent",
        entity_id=ENTITY,
        code="STD-FR",
        label="Standard France",
        primary_standard="fr-pcg",
        code_policy_id="numeric",
        reference_snapshot_id="snap:pcg:2026",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=ChartStatus.SUPERSEDED,
                effective_from=date(2026, 1, 1),
                effective_to=date(2027, 1, 1),
            ),
            CompanyChartVersion(
                label="v2",
                status=ChartStatus.ACTIVE,
                effective_from=date(2027, 1, 1),
            ),
        ),
    )
    chart_resolver = InMemoryVersionedCompanyChartResolver(
        company_chart,
        {
            "v1": _accounts("v1", "681100"),
            "v2": _accounts("v2", "681200"),
        },
    )
    return InMemoryAccountRoleResolver(chart_resolver)


def test_same_pinned_inputs_produce_same_proposal_checksum() -> None:
    assert _proposal().checksum() == _proposal().checksum()


def test_policy_version_change_changes_replay_fingerprint() -> None:
    assert _proposal("1.0").checksum() != _proposal("1.1").checksum()


def test_historical_date_replays_same_chart_version_and_account() -> None:
    resolver = _resolver()
    first = resolver.resolve(
        entity_id=ENTITY,
        accounting_date=date(2026, 6, 30),
        role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
    )
    replay = resolver.resolve(
        entity_id=ENTITY,
        accounting_date=date(2026, 6, 30),
        role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
    )
    assert first == replay
    assert replay.chart_version == "v1"
    assert replay.account_code == "681100"
    assert replay.reference_snapshot_id == "snap:pcg:2026"


def test_later_date_selects_new_chart_version_explicitly() -> None:
    resolved = _resolver().resolve(
        entity_id=ENTITY,
        accounting_date=date(2027, 1, 1),
        role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
    )
    assert resolved.chart_version == "v2"
    assert resolved.account_code == "681200"
