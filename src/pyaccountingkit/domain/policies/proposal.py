"""JournalEntryProposal — the only bridge between policies and posting.

Policies never post directly.  A proposal is valid by construction and its
lines carry functional ``AccountRole`` values.  The canonical application
path resolves those roles through a versioned company chart before delegating
to the normal PostingOrchestrator.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.errors import (
    AccountRoleResolutionError,
    AmbiguousAccountRoleError,
    UnbalancedProposalError,
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
    """One proposed line: a role, a side and a strictly positive amount."""

    account_role: AccountRole
    side: DebitCredit
    amount: Money
    resolved_account_id: str | None = None
    description: str = ""
    dimensions: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount.is_zero() or self.amount.amount < 0:
            raise ValueError("proposed amounts must be strictly positive")


@dataclass(frozen=True, slots=True)
class JournalEntryProposal:
    """Balanced proposed accounting entry, not yet persisted in the ledger."""

    entity_id: EntityId
    accounting_date: date
    entry_type: str
    lines: tuple[JournalEntryLineProposal, ...]
    journal_hint: str | None = None
    source: str = ""
    source_reference: str = ""
    policy_traces: tuple[PolicyExecutionTrace, ...] = ()

    def __post_init__(self) -> None:
        if not self.entry_type:
            raise ValueError("proposal entry_type must be non-empty")
        if len(self.lines) < 2:
            raise ValueError("a proposal must carry at least two lines")
        first_currency = self.lines[0].amount.currency
        if any(line.amount.currency != first_currency for line in self.lines):
            raise UnbalancedProposalError("a proposal must use one currency")
        if not self.is_balanced():
            raise UnbalancedProposalError(
                "proposal debits and credits must balance before account resolution"
            )
        for trace in self.policy_traces:
            if trace.accounting_entity_id != str(self.entity_id):
                raise ValueError(
                    f"policy trace {trace.trace_id} belongs to entity "
                    f"{trace.accounting_entity_id}, expected {self.entity_id}"
                )
            if trace.accounting_date != self.accounting_date:
                raise ValueError(
                    f"policy trace {trace.trace_id} date {trace.accounting_date} "
                    f"does not match proposal date {self.accounting_date}"
                )

    def is_balanced(self) -> bool:
        """Return whether debit and credit totals are equal at the centime."""
        totals = {DebitCredit.DEBIT: Decimal("0"), DebitCredit.CREDIT: Decimal("0")}
        first_currency = self.lines[0].amount.currency
        for line in self.lines:
            if line.amount.currency != first_currency:
                return False
            totals[line.side] += line.amount.amount
        return totals[DebitCredit.DEBIT] == totals[DebitCredit.CREDIT]

    def checksum(self) -> str:
        """Return a deterministic replay fingerprint for the proposal contract."""
        payload = {
            "entity_id": str(self.entity_id),
            "accounting_date": self.accounting_date.isoformat(),
            "entry_type": self.entry_type,
            "journal_hint": self.journal_hint,
            "source": self.source,
            "source_reference": self.source_reference,
            "lines": [
                {
                    "role": line.account_role.value,
                    "side": line.side.value,
                    "amount": str(line.amount.amount),
                    "currency": line.amount.currency.code,
                    "description": line.description,
                }
                for line in self.lines
            ],
            "policy_traces": [
                {
                    "policy_set_id": trace.policy_set_id,
                    "policy_set_version": trace.policy_set_version,
                    "policy_id": trace.policy_id,
                    "policy_version": trace.policy_version,
                    "reference_snapshot_id": trace.reference_snapshot_id,
                }
                for trace in self.policy_traces
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AccountResolutionService:
    """Legacy fail-closed role mapping scoped to one entity.

    New application code should depend on ``AccountRoleResolverProtocol`` so
    resolution also selects the applicable ``CompanyChartVersion``.  This
    compatibility service remains entity-safe for LOT-13 callers.
    """

    entity_id: EntityId
    candidates_by_role: Mapping[AccountRole, Sequence[str]] = field(default_factory=dict)

    def resolve(self, *, role: AccountRole, entity_id: EntityId) -> str:
        require_same_entity(self.entity_id, entity_id, resource=f"account role {role.value}")
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
