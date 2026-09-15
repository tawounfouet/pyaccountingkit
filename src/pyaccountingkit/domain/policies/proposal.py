"""JournalEntryProposal — the only bridge between policies and posting.

Policies never post directly (ADR-POL-007).  They produce a
``JournalEntryProposal`` (spec section 66-67) whose lines carry an
``AccountRole`` (spec section 68-69).  An ``AccountResolutionService``
translates roles into company accounts — fail-closed (§71):
``AccountRoleResolutionError`` when nothing resolves,
``AmbiguousAccountRoleError`` when several candidates compete and no rule
breaks the tie.  The proposal is then validated and posted by the normal
posting pipeline (ADR-POL-008).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pyaccountingkit.core.errors import (
    AccountRoleResolutionError,
    AmbiguousAccountRoleError,
)
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace


class DebitCredit(StrEnum):
    """Side of a proposed accounting line."""

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


@dataclass(frozen=True, slots=True)
class JournalEntryLineProposal:
    """One proposed line: a role, a side and an amount (§67)."""

    account_role: AccountRole
    side: DebitCredit
    amount: Money
    resolved_account_id: str | None = None
    description: str = ""
    dimensions: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount.is_zero() or self.amount.amount < 0:
            raise ValueError("proposed amounts must be strictly positive (line usages)")


@dataclass(frozen=True, slots=True)
class JournalEntryProposal:
    """Proposed, not-yet-posted accounting entry (spec section 66)."""

    entity_id: EntityId
    accounting_date: date
    entry_type: str
    lines: tuple[JournalEntryLineProposal, ...]
    journal_hint: str | None = None
    source: str = ""
    source_reference: str = ""
    policy_traces: tuple[PolicyExecutionTrace, ...] = ()

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError("a proposal must carry at least one line")
        for line in self.lines:
            if line.amount.is_zero() or line.amount.amount < 0:
                raise ValueError("proposed amounts must be strictly positive (line usages)")

    def is_balanced(self) -> bool:
        """Debits and credits must sum equally at the centime."""
        totals = {"DEBIT": Decimal("0"), "CREDIT": Decimal("0")}
        first_currency = self.lines[0].amount.currency
        for line in self.lines:
            if line.amount.currency != first_currency:
                return False
            totals[line.side.value] += line.amount.amount
        return totals["DEBIT"] == totals["CREDIT"]


@dataclass(frozen=True, slots=True)
class AccountResolutionService:
    """Fail-closed role → company-account translation (§70-71).

    ``candidates_by_role`` maps a role to the company account ids that can
    serve it.  Zero candidates raise ``AccountRoleResolutionError``; several
    raise ``AmbiguousAccountRoleError``.
    """

    candidates_by_role: Mapping[AccountRole, Sequence[str]] = field(default_factory=dict)

    def resolve(self, *, role: AccountRole, entity_id: EntityId) -> str:
        candidates = self._candidates(role)
        if not candidates:
            raise AccountRoleResolutionError(
                f"no company account resolves role {role.value!r} for {entity_id}"
            )
        if len(candidates) > 1:
            raise AmbiguousAccountRoleError(
                f"role {role.value!r} resolves to several accounts for {entity_id}: "
                f"{', '.join(sorted(candidates))}"
            )
        return next(iter(candidates))

    def _candidates(self, role: AccountRole) -> set[str]:
        return {account_id for account_id in self.candidates_by_role.get(role, ()) if account_id}


__all__ = [
    "AccountResolutionService",
    "DebitCredit",
    "JournalEntryLineProposal",
    "JournalEntryProposal",
]
