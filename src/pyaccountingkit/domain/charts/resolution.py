"""Traceable results of resolving versioned company chart configuration."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts


@dataclass(frozen=True, slots=True)
class ResolvedCompanyChart:
    """Operational chart selected for one entity and accounting date."""

    chart: CompanyChartOfAccounts
    chart_id: str
    chart_version: str
    entity_id: EntityId
    reference_snapshot_id: str


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


__all__ = ["ResolvedAccount", "ResolvedCompanyChart"]
