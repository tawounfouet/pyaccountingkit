import calendar
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AccountingPeriod, AccountingSettings, FiscalYear, Organization

def next_month_start(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)

@transaction.atomic
def ensure_accounting_settings(*, organization: Organization) -> AccountingSettings:
    settings, _ = AccountingSettings.objects.get_or_create(organization=organization)
    return settings

@transaction.atomic
def generate_monthly_periods(*, fiscal_year: FiscalYear) -> list[AccountingPeriod]:
    if fiscal_year.periods.exists():
        raise ValidationError("Cet exercice possède déjà des périodes comptables.")

    periods = []
    current = fiscal_year.start_date
    period_number = 1

    while current <= fiscal_year.end_date:
        month_end = date(
            current.year,
            current.month,
            calendar.monthrange(current.year, current.month)[1],
        )
        period_end = min(month_end, fiscal_year.end_date)

        periods.append(
            AccountingPeriod(
                fiscal_year=fiscal_year,
                period_number=period_number,
                name=current.strftime("%Y-%m"),
                start_date=current,
                end_date=period_end,
                status=AccountingPeriod.Status.OPEN,
            )
        )

        if period_end >= fiscal_year.end_date:
            break

        current = next_month_start(current)
        period_number += 1

    AccountingPeriod.objects.bulk_create(periods)
    return list(fiscal_year.periods.order_by("period_number"))

@transaction.atomic
def close_period(*, period: AccountingPeriod) -> AccountingPeriod:
    if period.status == AccountingPeriod.Status.CLOSED:
        return period
    period.status = AccountingPeriod.Status.CLOSED
    period.save(update_fields=["status", "updated_at"])
    return period

@transaction.atomic
def reopen_period(*, period: AccountingPeriod) -> AccountingPeriod:
    period.status = AccountingPeriod.Status.OPEN
    period.save(update_fields=["status", "updated_at"])
    return period
