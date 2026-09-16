"""Port for resolving subledger control accounts explicitly and fail-closed."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.subledgers.control_account import ResolvedControlAccount
from pyaccountingkit.domain.subledgers.primitives import SubledgerPartyType


class ControlAccountResolverProtocol(Protocol):
    """Resolve exactly one control account for a subledger execution context."""

    def resolve(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        accounting_date: date,
        party_type: SubledgerPartyType | None = None,
        currency: Currency | None = None,
    ) -> ResolvedControlAccount: ...


__all__ = ["ControlAccountResolverProtocol"]
