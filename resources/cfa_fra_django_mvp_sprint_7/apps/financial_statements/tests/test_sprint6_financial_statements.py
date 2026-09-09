from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounting.models import Account, JournalEntry, JournalLine
from apps.accounting.services import (
    bootstrap_accounting_core,
    create_draft_entry,
    post_journal_entry,
    validate_journal_entry,
)
from apps.financial_statements.services import (
    auto_map_accounts,
    build_balance_sheet,
    build_cash_flow_statement,
    build_income_statement,
    build_ratios,
    ensure_financial_statement_configuration,
    update_statement_account_mapping,
)
from apps.organizations.models import FiscalYear, Organization, OrganizationMembership
from apps.organizations.services import generate_monthly_periods
from apps.referentials.models import (
    StatementAccountMapping,
    StatementDefinition,
    StatementLine,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def statement_case():
    User = get_user_model()
    reviewer = User.objects.create_user(
        username="statement-reviewer",
        email="statement-reviewer@example.com",
        password="secret1234",
    )

    organization = Organization.objects.create(
        name="Sprint 6 Statements",
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
    periods = {
        period.period_number: period
        for period in fiscal_year.periods.all()
    }

    chart, journals = bootstrap_accounting_core(organization=organization)
    jan = next(j for j in journals if j.code == "JAN")
    jod = next(j for j in journals if j.code == "JOD")
    sales = next(j for j in journals if j.code == "JVTE")

    accounts = {
        "cash": Account.objects.create(
            organization=organization,
            chart=chart,
            code="57110000",
            name="Caisse",
            account_type=Account.AccountType.ASSET,
            normal_balance=Account.NormalBalance.DEBIT,
        ),
        "equipment": Account.objects.create(
            organization=organization,
            chart=chart,
            code="24440000",
            name="Matériel de bureau",
            account_type=Account.AccountType.ASSET,
            normal_balance=Account.NormalBalance.DEBIT,
        ),
        "capital": Account.objects.create(
            organization=organization,
            chart=chart,
            code="10110000",
            name="Capital",
            account_type=Account.AccountType.EQUITY,
            normal_balance=Account.NormalBalance.CREDIT,
        ),
        "loan": Account.objects.create(
            organization=organization,
            chart=chart,
            code="16200000",
            name="Emprunt bancaire",
            account_type=Account.AccountType.LIABILITY,
            normal_balance=Account.NormalBalance.CREDIT,
            current_noncurrent="NONCURRENT",
        ),
        "accrued": Account.objects.create(
            organization=organization,
            chart=chart,
            code="40810000",
            name="Charges à payer",
            account_type=Account.AccountType.LIABILITY,
            normal_balance=Account.NormalBalance.CREDIT,
            current_noncurrent="CURRENT",
        ),
        "revenue": Account.objects.create(
            organization=organization,
            chart=chart,
            code="70610000",
            name="Prestations de services",
            account_type=Account.AccountType.REVENUE,
            normal_balance=Account.NormalBalance.CREDIT,
        ),
        "rent": Account.objects.create(
            organization=organization,
            chart=chart,
            code="62220000",
            name="Loyer",
            account_type=Account.AccountType.EXPENSE,
            normal_balance=Account.NormalBalance.DEBIT,
        ),
    }

    def post_entry(
        *,
        number,
        posting_date,
        period,
        lines,
        journal=jod,
        entry_type=JournalEntry.EntryType.NORMAL,
    ):
        entry = create_draft_entry(
            organization=organization,
            user=reviewer,
            journal=journal,
            period=period,
            entry_number=number,
            posting_date=posting_date,
            description=number,
            entry_type=entry_type,
            lines=lines,
        )
        entry = validate_journal_entry(entry=entry, user=reviewer)
        return post_journal_entry(entry=entry, user=reviewer)

    post_entry(
        number="OPEN-2025",
        posting_date=date(2025, 1, 1),
        period=periods[1],
        journal=jan,
        entry_type=JournalEntry.EntryType.OPENING,
        lines=[
            {
                "account": accounts["cash"],
                "debit": Decimal("1000"),
                "credit": Decimal("0"),
            },
            {
                "account": accounts["capital"],
                "debit": Decimal("0"),
                "credit": Decimal("1000"),
            },
        ],
    )

    post_entry(
        number="SALE-001",
        posting_date=date(2025, 2, 10),
        period=periods[2],
        journal=sales,
        lines=[
            {
                "account": accounts["cash"],
                "debit": Decimal("500"),
                "credit": Decimal("0"),
                "cash_flow_tag": JournalLine.CashFlowTag.OPERATING,
            },
            {
                "account": accounts["revenue"],
                "debit": Decimal("0"),
                "credit": Decimal("500"),
            },
        ],
    )

    post_entry(
        number="RENT-001",
        posting_date=date(2025, 3, 15),
        period=periods[3],
        lines=[
            {
                "account": accounts["rent"],
                "debit": Decimal("200"),
                "credit": Decimal("0"),
            },
            {
                "account": accounts["cash"],
                "debit": Decimal("0"),
                "credit": Decimal("200"),
                "cash_flow_tag": JournalLine.CashFlowTag.OPERATING,
            },
        ],
    )

    post_entry(
        number="CAPEX-001",
        posting_date=date(2025, 4, 12),
        period=periods[4],
        lines=[
            {
                "account": accounts["equipment"],
                "debit": Decimal("100"),
                "credit": Decimal("0"),
            },
            {
                "account": accounts["cash"],
                "debit": Decimal("0"),
                "credit": Decimal("100"),
                "cash_flow_tag": JournalLine.CashFlowTag.INVESTING,
            },
        ],
    )

    post_entry(
        number="LOAN-001",
        posting_date=date(2025, 5, 10),
        period=periods[5],
        lines=[
            {
                "account": accounts["cash"],
                "debit": Decimal("300"),
                "credit": Decimal("0"),
                "cash_flow_tag": JournalLine.CashFlowTag.FINANCING,
            },
            {
                "account": accounts["loan"],
                "debit": Decimal("0"),
                "credit": Decimal("300"),
            },
        ],
    )

    post_entry(
        number="ADJ-001",
        posting_date=date(2025, 12, 31),
        period=periods[12],
        entry_type=JournalEntry.EntryType.ADJUSTING,
        lines=[
            {
                "account": accounts["rent"],
                "debit": Decimal("50"),
                "credit": Decimal("0"),
            },
            {
                "account": accounts["accrued"],
                "debit": Decimal("0"),
                "credit": Decimal("50"),
            },
        ],
    )

    configuration = ensure_financial_statement_configuration(
        organization=organization,
        user=reviewer,
    )
    auto_map_accounts(
        organization=organization,
        user=reviewer,
    )

    return {
        "user": reviewer,
        "organization": organization,
        "fiscal_year": fiscal_year,
        "accounts": accounts,
        "configuration": configuration,
    }


def set_active_organization(client, case):
    client.force_login(case["user"])
    session = client.session
    session["active_organization_id"] = str(case["organization"].pk)
    session.save()


def test_bootstrap_creates_three_statement_definitions(statement_case):
    version = statement_case["configuration"].framework_version

    types = set(
        StatementDefinition.objects.filter(version=version)
        .values_list("statement_type", flat=True)
    )

    assert types == {
        StatementDefinition.StatementType.INCOME_STATEMENT,
        StatementDefinition.StatementType.BALANCE_SHEET,
        StatementDefinition.StatementType.CASH_FLOW,
    }


def test_auto_mapping_maps_entity_accounts(statement_case):
    mappings = StatementAccountMapping.objects.filter(
        account__organization=statement_case["organization"],
        statement_line__definition__version=statement_case[
            "configuration"
        ].framework_version,
    )

    assert mappings.values("account_id").distinct().count() == 7
    assert mappings.get(
        account=statement_case["accounts"]["revenue"]
    ).statement_line.code == "IS_REVENUE"
    assert mappings.get(
        account=statement_case["accounts"]["equipment"]
    ).statement_line.code == "BS_NONCURRENT_ASSETS"


def test_income_statement_calculates_net_income(statement_case):
    report = build_income_statement(
        organization=statement_case["organization"],
        fiscal_year=statement_case["fiscal_year"],
    )

    assert report["values"]["IS_REVENUE"] == Decimal("500")
    assert report["values"]["IS_EXTERNAL_SERVICES"] == Decimal("250")
    assert report["values"]["IS_NET_INCOME"] == Decimal("250")
    assert report["unmapped_accounts"] == []


def test_balance_sheet_is_balanced_with_current_result(statement_case):
    report = build_balance_sheet(
        organization=statement_case["organization"],
        fiscal_year=statement_case["fiscal_year"],
    )

    assert report["values"]["BS_CURRENT_ASSETS"] == Decimal("1500")
    assert report["values"]["BS_NONCURRENT_ASSETS"] == Decimal("100")
    assert report["values"]["BS_TOTAL_ASSETS"] == Decimal("1600")

    assert report["values"]["BS_CURRENT_LIABILITIES"] == Decimal("50")
    assert report["values"]["BS_NONCURRENT_LIABILITIES"] == Decimal("300")
    assert report["values"]["BS_EQUITY"] == Decimal("1000")
    assert report["values"]["BS_CURRENT_RESULT"] == Decimal("250")
    assert report["values"]["BS_TOTAL_LIAB_EQUITY"] == Decimal("1600")

    assert report["balance_gap"] == Decimal("0")
    assert report["is_balanced"]


def test_cash_flow_statement_reconciles_cash(statement_case):
    report = build_cash_flow_statement(
        organization=statement_case["organization"],
        fiscal_year=statement_case["fiscal_year"],
    )

    assert report["values"]["CF_OPENING_CASH"] == Decimal("1000")
    assert report["values"]["CF_OPERATING"] == Decimal("300")
    assert report["values"]["CF_INVESTING"] == Decimal("-100")
    assert report["values"]["CF_FINANCING"] == Decimal("300")
    assert report["values"]["CF_UNCLASSIFIED"] == Decimal("0")
    assert report["values"]["CF_NET_CHANGE"] == Decimal("500")
    assert report["values"]["CF_ENDING_CASH"] == Decimal("1500")
    assert report["values"]["CF_RECONCILIATION_GAP"] == Decimal("0")
    assert report["explicit_count"] == 4


def test_financial_ratios_are_derived_from_statements(statement_case):
    report = build_ratios(
        organization=statement_case["organization"],
        fiscal_year=statement_case["fiscal_year"],
    )
    ratios = {item["code"]: item["value"] for item in report["ratios"]}

    assert ratios["NET_MARGIN"] == Decimal("0.5")
    assert ratios["CURRENT_RATIO"] == Decimal("30")
    assert ratios["DEBT_TO_ASSETS"] == Decimal("0.21875")
    assert ratios["CFO_TO_REVENUE"] == Decimal("0.6")


def test_manual_mapping_survives_auto_mapping(statement_case):
    version = statement_case["configuration"].framework_version
    rent = statement_case["accounts"]["rent"]
    other_line = StatementLine.objects.get(
        definition__version=version,
        code="IS_OTHER_EXPENSES",
    )

    update_statement_account_mapping(
        organization=statement_case["organization"],
        account=rent,
        statement_line=other_line,
        user=statement_case["user"],
    )
    auto_map_accounts(
        organization=statement_case["organization"],
        user=statement_case["user"],
    )

    mapping = StatementAccountMapping.objects.get(
        account=rent,
        statement_line__definition__version=version,
    )
    assert mapping.statement_line.code == "IS_OTHER_EXPENSES"
    assert mapping.mapping_type == StatementAccountMapping.MappingType.MANUAL


def test_financial_statement_home_and_income_ui(client, statement_case):
    set_active_organization(client, statement_case)

    response = client.get(reverse("financial_statements:index"))
    assert response.status_code == 200
    assert "Financial Statements Engine" in response.content.decode()

    response = client.get(
        reverse("financial_statements:income-statement"),
        {
            "fiscal_year": str(statement_case["fiscal_year"].pk),
            "end_date": "2025-12-31",
        },
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Résultat net" in content
    assert "500" in content


def test_balance_sheet_ui_exposes_line_drilldown(client, statement_case):
    set_active_organization(client, statement_case)
    version = statement_case["configuration"].framework_version
    current_assets = StatementLine.objects.get(
        definition__version=version,
        code="BS_CURRENT_ASSETS",
    )

    response = client.get(
        reverse("financial_statements:balance-sheet"),
        {
            "fiscal_year": str(statement_case["fiscal_year"].pk),
            "end_date": "2025-12-31",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert reverse(
        "financial_statements:line-detail",
        kwargs={"line_id": current_assets.pk},
    ) in content


def test_statement_line_detail_drills_to_general_ledger(client, statement_case):
    set_active_organization(client, statement_case)
    version = statement_case["configuration"].framework_version
    current_assets = StatementLine.objects.get(
        definition__version=version,
        code="BS_CURRENT_ASSETS",
    )

    response = client.get(
        reverse(
            "financial_statements:line-detail",
            kwargs={"line_id": current_assets.pk},
        ),
        {
            "fiscal_year": str(statement_case["fiscal_year"].pk),
            "end_date": "2025-12-31",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert statement_case["accounts"]["cash"].code in content
    assert reverse("reporting:general-ledger") in content
