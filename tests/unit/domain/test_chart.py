"""Unit tests for the CompanyAccount, AccountRole and CompanyChartOfAccounts."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.errors import EntityScopeMismatchError
from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts

ENTITY = EntityId("ent_1")
OTHER_ENTITY = EntityId("ent_2")


def _account(code: str = "411000", entity_id: EntityId = ENTITY) -> CompanyAccount:
    return CompanyAccount(
        id=AccountId(code),
        entity_id=entity_id,
        code=code,
        label=f"Compte {code}",
    )


def _chart(accounts: tuple[CompanyAccount, ...] = ()) -> CompanyChartOfAccounts:
    return CompanyChartOfAccounts(entity_id=ENTITY, accounts=accounts)


def test_account_code_is_string() -> None:
    assert _account("411000").code == "411000"


def test_account_code_rejects_empty_or_oversized() -> None:
    with pytest.raises(ValueError):
        CompanyAccount(id=AccountId("a"), entity_id=EntityId("e"), code="", label="empty")
    with pytest.raises(ValueError):
        CompanyAccount(
            id=AccountId("a"),
            entity_id=EntityId("e"),
            code="A" * 51,
            label="too long",
        )


def test_account_deactivation_is_immutable() -> None:
    account = _account()
    deactivated = account.deactivated()
    assert account.is_active()
    assert not deactivated.is_active()
    assert deactivated.code == account.code


def test_deactivating_an_inactive_account_is_a_noop() -> None:
    inactive = CompanyAccount(
        id=AccountId("a"), entity_id=EntityId("e"), code="x", label="x", active=False
    )
    assert inactive.deactivated() is inactive


def test_account_postable_flag() -> None:
    account = _account()
    assert account.postable
    parent = CompanyAccount(
        id=AccountId("41000"),
        entity_id=ENTITY,
        code="41000",
        label="Parent",
        postable=False,
    )
    assert not parent.postable


def test_chart_add_rejects_duplicate_code() -> None:
    chart = _chart((_account("411"),))
    with pytest.raises(Exception, match="already exists"):
        chart.add(_account("411"))


def test_chart_add_increases_size() -> None:
    chart = _chart()
    updated = chart.add(_account("411"))
    assert len(updated.accounts) == 1


def test_chart_rejects_duplicate_code_on_construction() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        CompanyChartOfAccounts(
            entity_id=ENTITY,
            accounts=(_account("411"), _account("411")),
        )


def test_chart_rejects_cross_entity_account_on_construction() -> None:
    with pytest.raises(EntityScopeMismatchError):
        CompanyChartOfAccounts(
            entity_id=ENTITY,
            accounts=(_account("411", OTHER_ENTITY),),
        )


def test_chart_rejects_cross_entity_account_on_add() -> None:
    with pytest.raises(EntityScopeMismatchError):
        _chart().add(_account("411", OTHER_ENTITY))


def test_chart_get_by_code() -> None:
    acc = _account("411")
    chart = _chart((acc,))
    assert chart.get_by_code("411") == acc
    assert chart.get_by_code("999") is None


def test_chart_get_by_id() -> None:
    acc = _account("411")
    chart = _chart((acc,))
    assert chart.get_by_id(acc.id) == acc


def test_chart_deactivate_existing_account() -> None:
    acc = _account("411")
    chart = _chart((acc,))
    updated = chart.deactivate(acc.id)
    assert len(updated.accounts) == 1
    assert not updated.accounts[0].is_active()


def test_chart_deactivate_nonexistent_raises() -> None:
    chart = _chart()
    with pytest.raises(Exception, match="not found"):
        chart.deactivate(AccountId("missing"))
