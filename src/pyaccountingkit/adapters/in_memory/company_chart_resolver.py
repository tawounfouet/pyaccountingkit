"""In-memory reference adapter for company-chart version resolution."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.errors import ChartVersionNotFoundError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import CompanyChart
from pyaccountingkit.domain.charts.resolution import ResolvedCompanyChart


class InMemoryVersionedCompanyChartResolver:
    """Resolve an operational chart from a CompanyChart version aggregate."""

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
    ) -> ResolvedCompanyChart:
        require_same_entity(
            self._company_chart.entity_id,
            entity_id,
            resource=f"company chart {self._company_chart.chart_id}",
        )
        version = self._company_chart.version_at(accounting_date)
        operational_chart = self._accounts_by_version.get(version.label)
        if operational_chart is None:
            raise ChartVersionNotFoundError(
                f"no operational accounts registered for chart version {version.label!r}"
            )
        require_same_entity(
            entity_id,
            operational_chart.entity_id,
            resource=f"operational chart version {version.label}",
        )
        return ResolvedCompanyChart(
            chart=operational_chart,
            chart_id=self._company_chart.chart_id,
            chart_version=version.label,
            entity_id=entity_id,
            reference_snapshot_id=self._company_chart.reference_snapshot_id,
        )


__all__ = ["InMemoryVersionedCompanyChartResolver"]
