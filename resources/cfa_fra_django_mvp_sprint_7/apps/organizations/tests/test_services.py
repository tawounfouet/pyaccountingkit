from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.organizations.models import FiscalYear, Organization
from apps.organizations.services import generate_monthly_periods

pytestmark = pytest.mark.django_db

def test_generate_calendar_year_periods():
    organization = Organization.objects.create(
        name="Demo",
        base_currency="XAF",
        country_code="CM",
    )
    fiscal_year = FiscalYear.objects.create(
        organization=organization,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    periods = generate_monthly_periods(fiscal_year=fiscal_year)

    assert len(periods) == 12
    assert periods[0].start_date == date(2025, 1, 1)
    assert periods[0].end_date == date(2025, 1, 31)
    assert periods[-1].start_date == date(2025, 12, 1)
    assert periods[-1].end_date == date(2025, 12, 31)

def test_generate_periods_is_idempotence_guarded():
    organization = Organization.objects.create(name="Demo")
    fiscal_year = FiscalYear.objects.create(
        organization=organization,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    generate_monthly_periods(fiscal_year=fiscal_year)

    with pytest.raises(ValidationError):
        generate_monthly_periods(fiscal_year=fiscal_year)
