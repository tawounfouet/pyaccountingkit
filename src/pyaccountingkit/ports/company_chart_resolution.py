"""Port for resolving the operational company chart by entity and date."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.charts.resolution import ResolvedCompanyChart


class CompanyChartResolverProtocol(Protocol):
    """Resolve exactly one operational chart version for entity/date."""

    def resolve(
        self,
        *,
        entity_id: EntityId,
        accounting_date: date,
    ) -> ResolvedCompanyChart:
        ...


__all__ = ["CompanyChartResolverProtocol"]
