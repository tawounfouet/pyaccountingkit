from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounting.models import Account, ChartOfAccounts, Journal, JournalEntry
from apps.accounting.services import bootstrap_accounting_core, create_draft_entry
from apps.organizations.models import AccountingPeriod, FiscalYear, Organization, OrganizationMembership

pytestmark = pytest.mark.django_db


@pytest.fixture
def core_case():
    user = get_user_model().objects.create_user(
        username="core-user",
        email="core@example.com",
        password="secret1234",
    )
    org = Organization.objects.create(
        name="Sprint 2 Demo",
        base_currency="XAF",
        country_code="CM",
    )
    OrganizationMembership.objects.create(
        organization=org,
        user=user,
        role=OrganizationMembership.Role.ADMIN,
    )
    fy = FiscalYear.objects.create(
        organization=org,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    period = AccountingPeriod.objects.create(
        fiscal_year=fy,
        period_number=1,
        name="2025-01",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )
    chart, journals = bootstrap_accounting_core(organization=org)
    cash = Account.objects.create(
        organization=org,
        chart=chart,
        code="57110000",
        name="Caisse",
        account_type=Account.AccountType.ASSET,
        normal_balance=Account.NormalBalance.DEBIT,
    )
    capital = Account.objects.create(
        organization=org,
        chart=chart,
        code="10110000",
        name="Capital",
        account_type=Account.AccountType.EQUITY,
        normal_balance=Account.NormalBalance.CREDIT,
    )
    return {
        "user": user,
        "org": org,
        "fy": fy,
        "period": period,
        "chart": chart,
        "journal": next(j for j in journals if j.code == "JAN"),
        "cash": cash,
        "capital": capital,
    }


def test_accounting_core_bootstrap_is_idempotent(core_case):
    org = core_case["org"]

    chart_2, journals_2 = bootstrap_accounting_core(organization=org)

    assert chart_2.pk == core_case["chart"].pk
    assert org.charts_of_accounts.filter(code="ENTITY").count() == 1
    assert org.journals.count() == 8
    assert len(journals_2) == 8


def test_cross_organization_account_parent_is_rejected(core_case):
    other_org = Organization.objects.create(name="Other")
    other_chart = ChartOfAccounts.objects.create(
        organization=other_org,
        code="OTHER",
        name="Other chart",
    )
    other_parent = Account.objects.create(
        organization=other_org,
        chart=other_chart,
        code="10",
        name="Other parent",
    )

    child = Account(
        organization=core_case["org"],
        chart=core_case["chart"],
        code="101",
        name="Invalid child",
        parent=other_parent,
    )

    with pytest.raises(ValidationError):
        child.full_clean()


def test_draft_entry_can_be_created_from_core_models(core_case):
    entry = create_draft_entry(
        organization=core_case["org"],
        user=core_case["user"],
        journal=core_case["journal"],
        period=core_case["period"],
        entry_number="OPEN-001",
        posting_date=date(2025, 1, 1),
        description="Apport initial",
        entry_type=JournalEntry.EntryType.OPENING,
        lines=[
            {
                "account": core_case["cash"],
                "debit": Decimal("1000"),
                "credit": Decimal("0"),
            },
            {
                "account": core_case["capital"],
                "debit": Decimal("0"),
                "credit": Decimal("1000"),
            },
        ],
    )

    assert entry.status == JournalEntry.Status.DRAFT
    assert entry.lines.count() == 2
    assert entry.total_debit == Decimal("1000")
    assert entry.total_credit == Decimal("1000")
    assert entry.is_balanced


def test_entry_date_must_match_period(core_case):
    entry = JournalEntry(
        organization=core_case["org"],
        journal=core_case["journal"],
        period=core_case["period"],
        entry_number="OUTSIDE-001",
        posting_date=date(2025, 2, 1),
        description="Outside period",
        created_by=core_case["user"],
    )

    with pytest.raises(ValidationError):
        entry.full_clean()


def test_account_list_is_scoped_to_active_organization(client, core_case):
    other_org = Organization.objects.create(name="Invisible")
    other_chart = ChartOfAccounts.objects.create(
        organization=other_org,
        code="OTHER",
        name="Other chart",
    )
    Account.objects.create(
        organization=other_org,
        chart=other_chart,
        code="9999",
        name="Invisible account",
    )

    client.force_login(core_case["user"])
    session = client.session
    session["active_organization_id"] = str(core_case["org"].pk)
    session.save()

    response = client.get(reverse("accounting:accounts"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "57110000" in content
    assert "9999" not in content


def test_admin_can_create_journal(client, core_case):
    client.force_login(core_case["user"])
    session = client.session
    session["active_organization_id"] = str(core_case["org"].pk)
    session.save()

    response = client.post(
        reverse("accounting:journal-create"),
        {
            "code": "SPEC",
            "name": "Journal spécial",
            "journal_type": Journal.JournalType.GENERAL,
            "is_active": "on",
        },
    )

    assert response.status_code == 302
    assert core_case["org"].journals.filter(code="SPEC").exists()
