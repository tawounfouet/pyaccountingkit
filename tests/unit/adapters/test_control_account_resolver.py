"""Tests for entity/date/context-scoped subledger control-account resolution."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.in_memory.control_account_resolver import (
    InMemoryControlAccountResolver,
)
from pyaccountingkit.core.currency import EUR, USD, Currency
from pyaccountingkit.core.errors import (
    InactiveAccountError,
    NonPostableAccountError,
    UnknownAccountError,
)
from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)
from pyaccountingkit.domain.subledgers.control_account import ControlAccountBinding
from pyaccountingkit.domain.subledgers.errors import (
    AmbiguousControlAccountError,
    ControlAccountNotConfiguredError,
)
from pyaccountingkit.domain.subledgers.primitives import BindingStatus, SubledgerPartyType

ENTITY = EntityId("ent")
OTHER_ENTITY = EntityId("other")
AR = "subledger:ar"


def _company_chart() -> CompanyChart:
    return CompanyChart(
        chart_id="chart:ent",
        entity_id=ENTITY,
        code="PCG",
        label="PCG",
        primary_standard="fr-pcg",
        code_policy_id="free-form",
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


def _account(
    account_id: str,
    code: str,
    *,
    active: bool = True,
    postable: bool = True,
) -> CompanyAccount:
    return CompanyAccount(
        id=AccountId(account_id),
        entity_id=ENTITY,
        code=code,
        label=code,
        active=active,
        postable=postable,
    )


def _chart_resolver(
    *,
    v1_accounts: tuple[CompanyAccount, ...] | None = None,
    v2_accounts: tuple[CompanyAccount, ...] | None = None,
) -> InMemoryVersionedCompanyChartResolver:
    return InMemoryVersionedCompanyChartResolver(
        _company_chart(),
        {
            "v1": CompanyChartOfAccounts(
                entity_id=ENTITY,
                accounts=v1_accounts or (_account("ar-v1", "411000"),),
            ),
            "v2": CompanyChartOfAccounts(
                entity_id=ENTITY,
                accounts=v2_accounts or (_account("ar-v2", "411100"),),
            ),
        },
    )


def _binding(
    binding_id: str,
    account_id: str,
    *,
    entity_id: EntityId = ENTITY,
    party_type: SubledgerPartyType | None = None,
    currency: Currency | None = None,
    effective_to: date | None = None,
    status: BindingStatus = BindingStatus.ACTIVE,
) -> ControlAccountBinding:
    return ControlAccountBinding(
        binding_id=binding_id,
        entity_id=entity_id,
        subledger_id=AR,
        company_account_id=AccountId(account_id),
        effective_from=date(2026, 1, 1),
        effective_to=effective_to,
        party_type=party_type,
        currency=currency,
        status=status,
    )


def test_resolver_selects_most_specific_binding() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(
            _binding("generic", "ar-v1"),
            _binding("customer", "ar-v1", party_type=SubledgerPartyType.CUSTOMER),
            _binding(
                "customer-eur",
                "ar-v1",
                party_type=SubledgerPartyType.CUSTOMER,
                currency=EUR,
            ),
        ),
        chart_resolver=_chart_resolver(),
    )

    resolved = resolver.resolve(
        entity_id=ENTITY,
        subledger_id=AR,
        accounting_date=date(2026, 6, 1),
        party_type=SubledgerPartyType.CUSTOMER,
        currency=EUR,
    )

    assert resolved.binding_id == "customer-eur"
    assert resolved.account_code == "411000"
    assert resolved.chart_version == "v1"
    assert resolved.reference_snapshot_id == "snap:pcg:2026"


def test_resolver_uses_chart_version_applicable_to_date() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(
            _binding("v1", "ar-v1", effective_to=date(2027, 1, 1)),
            ControlAccountBinding(
                binding_id="v2",
                entity_id=ENTITY,
                subledger_id=AR,
                company_account_id=AccountId("ar-v2"),
                effective_from=date(2027, 1, 1),
            ),
        ),
        chart_resolver=_chart_resolver(),
    )

    resolved = resolver.resolve(
        entity_id=ENTITY,
        subledger_id=AR,
        accounting_date=date(2027, 1, 1),
    )

    assert resolved.binding_id == "v2"
    assert resolved.account_code == "411100"
    assert resolved.chart_version == "v2"


def test_resolver_fails_when_no_binding_matches() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(_binding("usd", "ar-v1", currency=USD),),
        chart_resolver=_chart_resolver(),
    )
    with pytest.raises(ControlAccountNotConfiguredError):
        resolver.resolve(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 6, 1),
            currency=EUR,
        )


def test_resolver_fails_on_equal_specificity_ambiguity() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(
            _binding("a", "ar-v1", currency=EUR),
            _binding("b", "ar-v1", currency=EUR),
        ),
        chart_resolver=_chart_resolver(),
    )
    with pytest.raises(AmbiguousControlAccountError):
        resolver.resolve(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 6, 1),
            currency=EUR,
        )


def test_resolver_does_not_cross_entity_binding_scope() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(_binding("other", "ar-v1", entity_id=OTHER_ENTITY),),
        chart_resolver=_chart_resolver(),
    )
    with pytest.raises(ControlAccountNotConfiguredError):
        resolver.resolve(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 6, 1),
        )


def test_resolver_rejects_account_absent_from_applicable_chart() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(_binding("missing", "missing"),),
        chart_resolver=_chart_resolver(),
    )
    with pytest.raises(UnknownAccountError):
        resolver.resolve(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 6, 1),
        )


def test_resolver_rejects_inactive_control_account() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(_binding("inactive", "inactive"),),
        chart_resolver=_chart_resolver(v1_accounts=(_account("inactive", "411000", active=False),)),
    )
    with pytest.raises(InactiveAccountError):
        resolver.resolve(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 6, 1),
        )


def test_resolver_rejects_non_postable_control_account() -> None:
    resolver = InMemoryControlAccountResolver(
        bindings=(_binding("non-postable", "non-postable"),),
        chart_resolver=_chart_resolver(
            v1_accounts=(_account("non-postable", "411000", postable=False),)
        ),
    )
    with pytest.raises(NonPostableAccountError):
        resolver.resolve(
            entity_id=ENTITY,
            subledger_id=AR,
            accounting_date=date(2026, 6, 1),
        )
