from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.accounting.models import (
    Account,
    ChartOfAccounts,
    Journal,
    JournalEntry,
    JournalLine,
)
from apps.accounting.services import validate_entry
from apps.organizations.models import AccountingPeriod, FiscalYear, Organization

pytestmark = pytest.mark.django_db

@pytest.fixture
def accounting_case():
    user = get_user_model().objects.create_user(
        username="accountant",
        email="accountant@example.com",
        password="secret",
    )
    org = Organization.objects.create(name="Demo", base_currency="XAF", country_code="CM")
    fy = FiscalYear.objects.create(
        organization=org,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    period = AccountingPeriod.objects.create(
        fiscal_year=fy,
        period_number=1,
        name="Janvier 2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )
    chart = ChartOfAccounts.objects.create(
        organization=org, code="OHADA", name="Plan Demo", is_default=True
    )
    cash = Account.objects.create(
        organization=org,
        chart=chart,
        code="5711",
        name="Caisse",
        account_type=Account.AccountType.ASSET,
        normal_balance=Account.NormalBalance.DEBIT,
    )
    capital = Account.objects.create(
        organization=org,
        chart=chart,
        code="1030",
        name="Capital",
        account_type=Account.AccountType.EQUITY,
        normal_balance=Account.NormalBalance.CREDIT,
    )
    journal = Journal.objects.create(
        organization=org,
        code="JAN",
        name="À-nouveaux",
        journal_type=Journal.JournalType.OPENING,
    )
    entry = JournalEntry.objects.create(
        organization=org,
        journal=journal,
        period=period,
        entry_number="OPEN-001",
        posting_date=date(2025, 1, 1),
        description="Apport initial",
        entry_type=JournalEntry.EntryType.OPENING,
        created_by=user,
    )
    return user, org, fy, period, cash, capital, entry

def test_balanced_entry_is_valid(accounting_case):
    _, _, _, _, cash, capital, entry = accounting_case

    JournalLine.objects.create(
        entry=entry,
        line_number=1,
        account=cash,
        debit=Decimal("1000"),
        credit=Decimal("0"),
    )
    JournalLine.objects.create(
        entry=entry,
        line_number=2,
        account=capital,
        debit=Decimal("0"),
        credit=Decimal("1000"),
    )

    validate_entry(entry)
    assert entry.is_balanced

def test_unbalanced_entry_is_rejected(accounting_case):
    _, _, _, _, cash, capital, entry = accounting_case

    JournalLine.objects.create(
        entry=entry,
        line_number=1,
        account=cash,
        debit=Decimal("1000"),
        credit=Decimal("0"),
    )
    JournalLine.objects.create(
        entry=entry,
        line_number=2,
        account=capital,
        debit=Decimal("0"),
        credit=Decimal("900"),
    )

    with pytest.raises(Exception):
        validate_entry(entry)
