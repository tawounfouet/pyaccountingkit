"""Tests for entity/date/version-scoped account-role resolution."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.adapters.in_memory.account_role_resolver import InMemoryAccountRoleResolver
from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.core.errors import (
    AccountRoleResolutionError,
    AmbiguousAccountRoleError,
    EntityScopeMismatchError,
)
from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)


def _company_chart() -> CompanyChart:
    return CompanyChart(
        chart_id="chart:ent",
        entity_id=EntityId("ent"),
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


def _accounts(version: str, code: str) -> CompanyChartOfAccounts:
    return CompanyChartOfAccounts(
        entity_id=EntityId("ent"),
        accounts=(
            CompanyAccount(
                id=AccountId(f"{version}:{code}"),
                entity_id=EntityId("ent"),
                code=code,
                label="Dotations",
                role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
            ),
        ),
    )


def _chart_resolver(
    *,
    v1_chart: CompanyChartOfAccounts | None = None,
) -> InMemoryVersionedCompanyChartResolver:
    return InMemoryVersionedCompanyChartResolver(
        _company_chart(),
        {
            "v1": v1_chart or _accounts("v1", "681100"),
            "v2": _accounts("v2", "681200"),
        },
    )


def _resolver() -> InMemoryAccountRoleResolver:
    return InMemoryAccountRoleResolver(_chart_resolver())


def test_resolver_uses_historical_chart_version_by_date() -> None:
    resolved = _resolver().resolve(
        entity_id=EntityId("ent"),
        accounting_date=date(2026, 6, 1),
        role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
    )
    assert resolved.account_code == "681100"
    assert resolved.chart_version == "v1"
    assert resolved.reference_snapshot_id == "snap:pcg:2026"


def test_resolver_uses_new_version_at_effective_boundary() -> None:
    resolved = _resolver().resolve(
        entity_id=EntityId("ent"),
        accounting_date=date(2027, 1, 1),
        role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
    )
    assert resolved.account_code == "681200"
    assert resolved.chart_version == "v2"


def test_resolver_rejects_cross_entity_request() -> None:
    with pytest.raises(EntityScopeMismatchError):
        _resolver().resolve(
            entity_id=EntityId("other"),
            accounting_date=date(2026, 6, 1),
            role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
        )


def test_resolver_rejects_missing_role() -> None:
    with pytest.raises(AccountRoleResolutionError):
        _resolver().resolve(
            entity_id=EntityId("ent"),
            accounting_date=date(2026, 6, 1),
            role=AccountRole.PROVISION_ACCOUNT,
        )


def test_resolver_rejects_ambiguous_role() -> None:
    account_a = CompanyAccount(
        id=AccountId("a"),
        entity_id=EntityId("ent"),
        code="681100",
        label="A",
        role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
    )
    account_b = CompanyAccount(
        id=AccountId("b"),
        entity_id=EntityId("ent"),
        code="681110",
        label="B",
        role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
    )
    ambiguous_v1 = CompanyChartOfAccounts(
        EntityId("ent"),
        (account_a, account_b),
    )
    resolver = InMemoryAccountRoleResolver(_chart_resolver(v1_chart=ambiguous_v1))
    with pytest.raises(AmbiguousAccountRoleError):
        resolver.resolve(
            entity_id=EntityId("ent"),
            accounting_date=date(2026, 6, 1),
            role=AccountRole.DEPRECIATION_EXPENSE_ACCOUNT,
        )
