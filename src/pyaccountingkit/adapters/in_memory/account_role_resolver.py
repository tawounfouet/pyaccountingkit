"""In-memory reference adapter for versioned company account-role resolution."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.errors import AccountRoleResolutionError, AmbiguousAccountRoleError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import CompanyChart
from pyaccountingkit.domain.charts.resolution import ResolvedAccount


class InMemoryAccountRoleResolver:
    """Resolve roles through the CompanyChart version effective on a date."""

    def __init__(
        self,
        company_chart: CompanyChart,
        accounts_by_version: Mapping[str, CompanyChartOfAccounts],
    ) -> None:
        self._company_chart = company_chart
        self._accounts_by_version = dict(accounts_by_version)

    def resolve(
        self,
        *,
        entity_id: EntityId,
        accounting_date: date,
        role: AccountRole,
    ) -> ResolvedAccount:
        require_same_entity(
            self._company_chart.entity_id,
            entity_id,
            resource=f"account-role resolution {role.value}",
        )
        version = self._company_chart.version_at(accounting_date)
        operational_chart = self._accounts_by_version.get(version.label)
        if operational_chart is None:
            raise AccountRoleResolutionError(
                f"no operational accounts registered for chart version {version.label!r}"
            )
        require_same_entity(
            entity_id,
            operational_chart.entity_id,
            resource=f"operational chart version {version.label}",
        )
        candidates = tuple(
            account
            for account in operational_chart.accounts
            if account.role is role and account.active and account.postable
        )
        if not candidates:
            raise AccountRoleResolutionError(
                f"no account for role {role.value} in entity {entity_id} "
                f"chart version {version.label}"
            )
        if len(candidates) > 1:
            raise AmbiguousAccountRoleError(
                f"{len(candidates)} accounts for role {role.value} in entity {entity_id} "
                f"chart version {version.label}: "
                + ", ".join(account.code for account in candidates)
            )
        account = candidates[0]
        return ResolvedAccount(
            account_id=account.id,
            account_code=account.code,
            account_role=role,
            entity_id=entity_id,
            chart_id=self._company_chart.chart_id,
            chart_version=version.label,
            reference_snapshot_id=self._company_chart.reference_snapshot_id,
        )


__all__ = ["InMemoryAccountRoleResolver"]
