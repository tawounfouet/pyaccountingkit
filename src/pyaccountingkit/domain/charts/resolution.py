"""Traceable result of resolving a functional account role."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account_role import AccountRole


@dataclass(frozen=True, slots=True)
class ResolvedAccount:
    """Company account selected through a versioned chart for one role."""

    account_id: AccountId
    account_code: str
    account_role: AccountRole
    entity_id: EntityId
    chart_id: str
    chart_version: str
    reference_snapshot_id: str


__all__ = ["ResolvedAccount"]
