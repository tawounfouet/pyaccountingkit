from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounting.models import Account, JournalEntry
from apps.accounting.services import (
    bootstrap_accounting_core,
    create_draft_entry,
    post_journal_entry,
    validate_journal_entry,
)
from apps.organizations.models import FiscalYear, Organization, OrganizationMembership
from apps.organizations.services import generate_monthly_periods
from apps.reporting.selectors import (
    journal_lines,
    journal_totals,
    ledger_lines,
    trial_balance_rows,
    trial_balance_totals,
)
from apps.reporting.types import TrialBalanceVariant

pytestmark = pytest.mark.django_db


@pytest.fixture
def reporting_case():
    User = get_user_model()
    reviewer = User.objects.create_user(
        username="report-reviewer",
        email="report-reviewer@example.com",
        password="secret1234",
    )

    organization = Organization.objects.create(
        name="Sprint 5 Reporting",
        base_currency="XAF",
        country_code="CM",
    )
    OrganizationMembership.objects.create(
        organization=organization,
        user=reviewer,
        role=OrganizationMembership.Role.REVIEWER,
    )

    fiscal_year = FiscalYear.objects.create(
        organization=organization,
        name="2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    generate_monthly_periods(fiscal_year=fiscal_year)

    chart, journals = bootstrap_accounting_core(organization=organization)
    jan = next(journal for journal in journals if journal.code == "JAN")
    jod = next(journal for journal in journals if journal.code == "JOD")

    cash = Account.objects.create(
        organization=organization,
        chart=chart,
        code="57110000",
        name="Caisse",
        account_type=Account.AccountType.ASSET,
        normal_balance=Account.NormalBalance.DEBIT,
    )
    capital = Account.objects.create(
        organization=organization,
        chart=chart,
        code="10110000",
        name="Capital",
        account_type=Account.AccountType.EQUITY,
        normal_balance=Account.NormalBalance.CREDIT,
    )
    rent = Account.objects.create(
        organization=organization,
        chart=chart,
        code="62220000",
        name="Loyer",
        account_type=Account.AccountType.EXPENSE,
        normal_balance=Account.NormalBalance.DEBIT,
    )
    accrued = Account.objects.create(
        organization=organization,
        chart=chart,
        code="40810000",
        name="Charges à payer",
        account_type=Account.AccountType.LIABILITY,
        normal_balance=Account.NormalBalance.CREDIT,
    )

    periods = {
        period.period_number: period
        for period in fiscal_year.periods.all()
    }

    def post_entry(
        *,
        number,
        posting_date,
        period,
        entry_type,
        lines,
        journal=jod,
        description=None,
    ):
        entry = create_draft_entry(
            organization=organization,
            user=reviewer,
            journal=journal,
            period=period,
            entry_number=number,
            posting_date=posting_date,
            description=description or number,
            entry_type=entry_type,
            lines=lines,
        )
        entry = validate_journal_entry(entry=entry, user=reviewer)
        return post_journal_entry(entry=entry, user=reviewer)

    opening = post_entry(
        number="OPEN-2025",
        posting_date=date(2025, 1, 1),
        period=periods[1],
        entry_type=JournalEntry.EntryType.OPENING,
        journal=jan,
        lines=[
            {"account": cash, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("1000")},
        ],
    )

    normal = post_entry(
        number="N-001",
        posting_date=date(2025, 1, 10),
        period=periods[1],
        entry_type=JournalEntry.EntryType.NORMAL,
        lines=[
            {"account": rent, "debit": Decimal("200"), "credit": Decimal("0")},
            {"account": cash, "debit": Decimal("0"), "credit": Decimal("200")},
        ],
    )

    adjusting = post_entry(
        number="A-001",
        posting_date=date(2025, 1, 31),
        period=periods[1],
        entry_type=JournalEntry.EntryType.ADJUSTING,
        lines=[
            {"account": rent, "debit": Decimal("50"), "credit": Decimal("0")},
            {"account": accrued, "debit": Decimal("0"), "credit": Decimal("50")},
        ],
    )

    closing = post_entry(
        number="C-001",
        posting_date=date(2025, 12, 31),
        period=periods[12],
        entry_type=JournalEntry.EntryType.CLOSING,
        lines=[
            {"account": capital, "debit": Decimal("250"), "credit": Decimal("0")},
            {"account": rent, "debit": Decimal("0"), "credit": Decimal("250")},
        ],
    )

    # A non-posted draft must never leak into accounting reports.
    create_draft_entry(
        organization=organization,
        user=reviewer,
        journal=jod,
        period=periods[2],
        entry_number="DRAFT-IGNORED",
        posting_date=date(2025, 2, 1),
        description="Ignored draft",
        lines=[
            {"account": cash, "debit": Decimal("999"), "credit": Decimal("0")},
            {"account": capital, "debit": Decimal("0"), "credit": Decimal("999")},
        ],
    )

    return {
        "user": reviewer,
        "organization": organization,
        "fiscal_year": fiscal_year,
        "periods": periods,
        "cash": cash,
        "capital": capital,
        "rent": rent,
        "accrued": accrued,
        "opening": opening,
        "normal": normal,
        "adjusting": adjusting,
        "closing": closing,
    }


def set_active_organization(client, case):
    client.force_login(case["user"])
    session = client.session
    session["active_organization_id"] = str(case["organization"].pk)
    session.save()


def rows_by_code(rows):
    return {row.code: row for row in rows}


def test_journal_uses_only_posted_or_reversed_entries(reporting_case):
    qs = journal_lines(
        organization=reporting_case["organization"],
        fiscal_year=reporting_case["fiscal_year"],
    )
    totals = journal_totals(qs)

    assert qs.count() == 8
    assert totals["total_debit"] == Decimal("1500")
    assert totals["total_credit"] == Decimal("1500")
    assert not qs.filter(entry__entry_number="DRAFT-IGNORED").exists()


def test_general_ledger_uses_database_window_for_running_balance(reporting_case):
    report = ledger_lines(
        organization=reporting_case["organization"],
        fiscal_year=reporting_case["fiscal_year"],
        account=reporting_case["cash"],
        start_date=date(2025, 1, 5),
        end_date=date(2025, 12, 31),
        variant=TrialBalanceVariant.ADJUSTED,
    )

    rows = list(report["queryset"])

    assert report["opening_signed"] == Decimal("1000")
    assert report["period_debit"] == Decimal("0")
    assert report["period_credit"] == Decimal("200")
    assert report["closing_signed"] == Decimal("800")

    assert len(rows) == 1
    assert rows[0].signed_movement == Decimal("-200")
    assert rows[0].period_running_signed == Decimal("-200")
    assert rows[0].running_signed_balance == Decimal("800")


def test_trial_balance_before_adjustments_excludes_adjusting_and_closing(reporting_case):
    qs = trial_balance_rows(
        organization=reporting_case["organization"],
        fiscal_year=reporting_case["fiscal_year"],
        as_of_date=date(2025, 12, 31),
        variant=TrialBalanceVariant.BEFORE_ADJUSTMENTS,
    )
    rows = rows_by_code(qs)
    totals = trial_balance_totals(qs)

    assert rows["57110000"].debit_balance == Decimal("800")
    assert rows["62220000"].debit_balance == Decimal("200")
    assert rows["10110000"].credit_balance == Decimal("1000")
    assert "40810000" not in rows

    assert totals["balance_debit"] == Decimal("1000")
    assert totals["balance_credit"] == Decimal("1000")


def test_adjusted_trial_balance_includes_adjusting_but_excludes_closing(reporting_case):
    qs = trial_balance_rows(
        organization=reporting_case["organization"],
        fiscal_year=reporting_case["fiscal_year"],
        as_of_date=date(2025, 12, 31),
        variant=TrialBalanceVariant.ADJUSTED,
    )
    rows = rows_by_code(qs)
    totals = trial_balance_totals(qs)

    assert rows["57110000"].debit_balance == Decimal("800")
    assert rows["62220000"].debit_balance == Decimal("250")
    assert rows["40810000"].credit_balance == Decimal("50")
    assert rows["10110000"].credit_balance == Decimal("1000")

    assert totals["balance_debit"] == Decimal("1050")
    assert totals["balance_credit"] == Decimal("1050")


def test_post_closing_trial_balance_includes_closing_and_hides_zero_temp_accounts(reporting_case):
    qs = trial_balance_rows(
        organization=reporting_case["organization"],
        fiscal_year=reporting_case["fiscal_year"],
        as_of_date=date(2025, 12, 31),
        variant=TrialBalanceVariant.POST_CLOSING,
        include_zero=False,
    )
    rows = rows_by_code(qs)
    totals = trial_balance_totals(qs)

    assert rows["57110000"].debit_balance == Decimal("800")
    assert rows["10110000"].credit_balance == Decimal("750")
    assert rows["40810000"].credit_balance == Decimal("50")
    assert "62220000" not in rows

    assert totals["balance_debit"] == Decimal("800")
    assert totals["balance_credit"] == Decimal("800")


def test_post_closing_can_show_zero_balance_accounts(reporting_case):
    qs = trial_balance_rows(
        organization=reporting_case["organization"],
        fiscal_year=reporting_case["fiscal_year"],
        as_of_date=date(2025, 12, 31),
        variant=TrialBalanceVariant.POST_CLOSING,
        include_zero=True,
    )
    rows = rows_by_code(qs)

    assert "62220000" in rows
    assert rows["62220000"].signed_balance == Decimal("0")
    assert rows["62220000"].total_debit == Decimal("250")
    assert rows["62220000"].total_credit == Decimal("250")


def test_journal_ui_has_source_drilldown(client, reporting_case):
    set_active_organization(client, reporting_case)

    response = client.get(
        reverse("reporting:journal"),
        {
            "fiscal_year": str(reporting_case["fiscal_year"].pk),
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "N-001" in content
    assert reverse(
        "accounting:entry-detail",
        kwargs={"pk": reporting_case["normal"].pk},
    ) in content
    assert "DRAFT-IGNORED" not in content


def test_trial_balance_ui_drills_into_general_ledger(client, reporting_case):
    set_active_organization(client, reporting_case)

    response = client.get(
        reverse("reporting:trial-balance"),
        {
            "fiscal_year": str(reporting_case["fiscal_year"].pk),
            "as_of_date": "2025-12-31",
            "variant": TrialBalanceVariant.ADJUSTED,
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Balance ajustée" in content
    assert reporting_case["cash"].code in content
    assert reverse("reporting:general-ledger") in content


def test_general_ledger_ui_drills_to_source_entry(client, reporting_case):
    set_active_organization(client, reporting_case)

    response = client.get(
        reverse("reporting:general-ledger"),
        {
            "fiscal_year": str(reporting_case["fiscal_year"].pk),
            "account": str(reporting_case["cash"].pk),
            "start_date": "2025-01-05",
            "end_date": "2025-12-31",
            "variant": TrialBalanceVariant.ADJUSTED,
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "800.00" in content or "800,00" in content
    assert reverse(
        "accounting:entry-detail",
        kwargs={"pk": reporting_case["normal"].pk},
    ) in content
