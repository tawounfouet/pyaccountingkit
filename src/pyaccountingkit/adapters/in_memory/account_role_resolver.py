"""In-memory reference adapter for versioned company account-role resolution."""

from __future__ import annotations

from datetime import date

from pyaccountingkit.core.errors import AccountRoleResolutionError, AmbiguousAccountRoleError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.account_role import AccountRole
from pyaccountingkit.domain.charts.resolution import ResolvedAccount
from pyaccountingkit.ports.company_chart_resolution import CompanyChartResolverProtocol


class InMemoryAccountRoleResolver:
    """Resolve roles through the same versioned chart authority as Posting."""

    def __init__(self, chart_resolver: CompanyChartResolverProtocol) -> None:
        self._chart_resolver = chart_resolver

    def resolve(
        self,
        *,
        entity_id: EntityId,
        accounting_date: date,
        role: AccountRole,
    ) -> ResolvedAccount:
        resolved_chart = self._chart_resolver.resolve(
            entity_id=entity_id,
            accounting_date=accounting_date,
        )
        candidates = tuple(
            account
            for account in resolved_chart.chart.accounts
            if account.role is role and account.active and account.postable
        )
        if not candidates:
            raise AccountRoleResolutionError(
                f"no account for role {role.value} in entity {entity_id} "
                f"chart version {resolved_chart.chart_version}"
            )
        if len(candidates) > 1:
            raise AmbiguousAccountRoleError(
                f"{len(candidates)} accounts for role {role.value} in entity {entity_id} "
                f"chart version {resolved_chart.chart_version}: "
                + ", ".join(account.code for account in candidates)
            )
        account = candidates[0]
        return ResolvedAccount(
            account_id=account.id,
            account_code=account.code,
            account_role=role,
            entity_id=entity_id,
            chart_id=resolved_chart.chart_id,
            chart_version=resolved_chart.chart_version,
            reference_snapshot_id=resolved_chart.reference_snapshot_id,
        )


__all__ = ["InMemoryAccountRoleResolver"]
