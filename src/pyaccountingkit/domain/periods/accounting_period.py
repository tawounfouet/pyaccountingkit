"""Accounting period within a fiscal year.

An entry's business date must fall within an open period of the same entity
and fiscal year before it can be posted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.errors import DateOutsidePeriodError
from pyaccountingkit.core.identifiers import EntityId, FiscalYearId, PeriodId
from pyaccountingkit.domain.periods.closing_status import ClosingStatus


@dataclass(frozen=True, slots=True)
class AccountingPeriod:
    """Bounded posting window inside one fiscal year."""

    id: PeriodId
    entity_id: EntityId
    fiscal_year_id: FiscalYearId
    start_date: date
    end_date: date
    status: ClosingStatus = ClosingStatus.OPEN

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError(f"Période invalide: début {self.start_date} après fin {self.end_date}")

    def is_open_for_posting(self) -> bool:
        return self.status.is_open_for_posting()

    def is_closed(self) -> bool:
        return self.status.is_closed()

    def contains(self, business_date: date) -> bool:
        return self.start_date <= business_date <= self.end_date

    def assert_date_within(self, business_date: date) -> None:
        """Reject dates outside the period with a typed error."""
        if not self.contains(business_date):
            raise DateOutsidePeriodError(
                f"Date {business_date} hors de la période {self.id} "
                f"[{self.start_date}, {self.end_date}]"
            )

    def with_status(self, status: ClosingStatus) -> AccountingPeriod:
        """Return a copy with a new closing status (periods are immutable)."""
        if not self.status.can_transition_to(status):
            raise ValueError(
                f"Transition invalide {self.status} -> {status} pour la période {self.id}"
            )
        return AccountingPeriod(
            id=self.id,
            entity_id=self.entity_id,
            fiscal_year_id=self.fiscal_year_id,
            start_date=self.start_date,
            end_date=self.end_date,
            status=status,
        )


__all__ = ["AccountingPeriod"]
