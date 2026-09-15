"""Unit tests for JournalEntryProposal and account resolution (LOT-13)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    AccountRoleResolutionError,
    AmbiguousAccountRoleError,
)
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.policies.proposal import (
    AccountResolutionService,
    DebitCredit,
    JournalEntryLineProposal,
    JournalEntryProposal,
)


def _line(
    role: AccountRole,
    side: DebitCredit,
    amount: str = "250.00",
) -> JournalEntryLineProposal:
    return JournalEntryLineProposal(
        account_role=role,
        side=side,
        amount=Money.from_str(amount, EUR),
    )


def _proposal() -> JournalEntryProposal:
    return JournalEntryProposal(
        entity_id=EntityId("ent:1"),
        accounting_date=date(2026, 12, 31),
        entry_type="DEPRECIATION",
        source="policy",
        source_reference="dep:1",
        lines=(
            _line(AccountRole.DEPRECIATION_EXPENSE_ACCOUNT, DebitCredit.DEBIT),
            _line(AccountRole.ACCUMULATED_DEPRECIATION_ACCOUNT, DebitCredit.CREDIT),
        ),
    )


def test_proposal_is_balanced() -> None:
    assert _proposal().is_balanced() is True


def test_proposal_detects_imbalance() -> None:
    proposal = JournalEntryProposal(
        entity_id=EntityId("ent:1"),
        accounting_date=date(2026, 12, 31),
        entry_type="DEPRECIATION",
        lines=(
            _line(AccountRole.DEPRECIATION_EXPENSE_ACCOUNT, DebitCredit.DEBIT, "250.00"),
            _line(AccountRole.ACCUMULATED_DEPRECIATION_ACCOUNT, DebitCredit.CREDIT, "240.00"),
        ),
    )
    assert proposal.is_balanced() is False


def test_proposal_requires_lines() -> None:
    with pytest.raises(ValueError, match="at least one line"):
        JournalEntryProposal(
            entity_id=EntityId("ent:1"),
            accounting_date=date(2026, 12, 31),
            entry_type="DEPRECIATION",
            lines=(),
        )


def test_proposal_rejects_zero_amount() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        JournalEntryLineProposal(
            account_role=AccountRole.ASSET,
            side=DebitCredit.DEBIT,
            amount=Money.zero(EUR),
        )


def test_role_differs_from_account_code() -> None:
    # ADR-POL-009: a policy expresses an AccountRole, not a company code.
    line = _line(AccountRole.PROVISION_ACCOUNT, DebitCredit.CREDIT)
    assert line.account_role is AccountRole.PROVISION_ACCOUNT
    assert line.resolved_account_id is None


def test_account_resolution_service_resolves_single_candidate() -> None:
    service = AccountResolutionService(
        candidates_by_role={AccountRole.ASSET_COST_ACCOUNT: ("215000",)}
    )
    resolved = service.resolve(role=AccountRole.ASSET_COST_ACCOUNT, entity_id=EntityId("ent:1"))
    assert resolved == "215000"


def test_account_resolution_fail_closed_when_missing() -> None:
    service = AccountResolutionService()
    with pytest.raises(AccountRoleResolutionError):
        service.resolve(role=AccountRole.ASSET_COST_ACCOUNT, entity_id=EntityId("ent:1"))


def test_account_resolution_fail_closed_when_ambiguous() -> None:
    service = AccountResolutionService(
        candidates_by_role={AccountRole.PROVISION_ACCOUNT: ("151000", "151100")}
    )
    with pytest.raises(AmbiguousAccountRoleError):
        service.resolve(role=AccountRole.PROVISION_ACCOUNT, entity_id=EntityId("ent:1"))


def test_new_functional_roles_are_available() -> None:
    assert AccountRole.DEPRECIATION_EXPENSE_ACCOUNT.value == "DEPRECIATION_EXPENSE_ACCOUNT"
    assert AccountRole.ACCUMULATED_DEPRECIATION_ACCOUNT.value == "ACCUMULATED_DEPRECIATION_ACCOUNT"
    assert AccountRole.IMPAIRMENT_EXPENSE_ACCOUNT.value == "IMPAIRMENT_EXPENSE_ACCOUNT"
