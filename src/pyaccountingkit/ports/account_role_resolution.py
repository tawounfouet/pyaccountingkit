"""Port for resolving functional AccountRole values to company accounts."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.resolution import ResolvedAccount


class AccountRoleResolverProtocol(Protocol):
    """Resolve one role in the chart version applicable to entity/date."""

    def resolve(
        self,
        *,
        entity_id: EntityId,
        accounting_date: date,
        role: AccountRole,
    ) -> ResolvedAccount:
        ...


__all__ = ["AccountRoleResolverProtocol"]
