"""Fiscal year and its deterministic period decomposition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from pyaccountingkit.core.identifiers import EntityId, FiscalYearId, PeriodId
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod


@dataclass(frozen=True, slots=True)
class FiscalYear:
    """An accounting year bounded by an inclusive start and end date."""

    id: FiscalYearId
    entity_id: EntityId
    label: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError(f"Exercice invalide: {self.start_date} après {self.end_date}")

    def contains(self, business_date: date) -> bool:
        return self.start_date <= business_date <= self.end_date

    def default_period(self) -> AccountingPeriod:
        """The single period covering the whole year (deterministic)."""
        return AccountingPeriod(
            id=PeriodId(f"{self.id}_p1"),
            entity_id=self.entity_id,
            fiscal_year_id=self.id,
            start_date=self.start_date,
            end_date=self.end_date,
        )

    def monthly_periods(self) -> tuple[AccountingPeriod, ...]:
        """Split the year into one ``AccountingPeriod`` per calendar month.

        Months outside the year bounds are trimmed to the year borders; the
        resulting periods are ordered deterministically.
        """
        from calendar import monthrange

        periods: list[AccountingPeriod] = []
        current = self.start_date
        index = 1
        while current <= self.end_date:
            month_end_day = monthrange(current.year, current.month)[1]
            month_end = date(current.year, current.month, month_end_day)
            period_end = min(month_end, self.end_date)
            periods.append(
                AccountingPeriod(
                    id=PeriodId(f"{self.id}_m{index:02d}"),
                    entity_id=self.entity_id,
                    fiscal_year_id=self.id,
                    start_date=current,
                    end_date=period_end,
                )
            )
            if period_end == self.end_date:
                break
            index += 1
            current = period_end.replace(day=1) + timedelta(days=32)
            current = current.replace(day=1)
        return tuple(periods)


__all__ = ["FiscalYear"]
