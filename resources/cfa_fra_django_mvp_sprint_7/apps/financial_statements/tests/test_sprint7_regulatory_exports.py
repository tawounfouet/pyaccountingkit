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
from apps.exports.models import ExportJob
from apps.exports.services import (
    create_regulatory_export,
    render_export_bytes,
    serialize_regulatory_package,
)
from apps.financial_statements.models import (
    RegulatoryStatementLineMapping,
)
from apps.financial_statements.regulatory import (
    auto_map_regulatory_profile,
    build_regulatory_package,
    create_regulatory_profile,
    profile_metrics,
    update_regulatory_mapping,
)
from apps.financial_statements.services import (
    auto_map_accounts,
    ensure_financial_statement_configuration,
)
from apps.organizations.models import (
    FiscalYear,
    Organization,
    OrganizationMembership,
)
from apps.organizations.services import generate_monthly_periods
from apps.referentials.models import (
    AccountingFramework,
    FrameworkVersion,
    StatementDefinition,
    StatementLine,
)
from apps.reporting.models import ReportSnapshot

pytestmark = pytest.mark.django_db


def add_line(
    definition,
    code,
    label,
    order,
    *,
    parent=None,
    sign=1,
    is_total=False,
    is_required=False,
    role="",
):
    return StatementLine.objects.create(
        definition=definition,
        code=code,
        label=label,
        order=order,
        parent=parent,
        sign=sign,
        is_total=is_total,
        is_required=is_required,
        standard_reference="DEMO",
        metadata={"role": role} if role else {},
    )


def build_target_framework():
    framework = AccountingFramework.objects.create(
        code="REG_DEMO",
        name="Regulatory Demo",
    )
    version = FrameworkVersion.objects.create(
        framework=framework,
        version="2026",
        is_current=True,
        source_url="https://example.test/regulatory-demo",
    )

    income = StatementDefinition.objects.create(
        version=version,
        code="REG_IS",
        name="Regulatory Income Statement",
        statement_type=StatementDefinition.StatementType.INCOME_STATEMENT,
    )
    income_total = add_line(
        income,
        "REG_NET",
        "Net result",
        100,
        is_total=True,
        role="net_income",
    )
    add_line(
        income,
        "REG_REVENUE",
        "Revenue",
        10,
        parent=income_total,
        sign=1,
        is_required=True,
        role="revenue",
    )
    add_line(
        income,
        "REG_EXTERNAL",
        "External services",
        20,
        parent=income_total,
        sign=-1,
        is_required=True,
        role="external_services",
    )

    balance = StatementDefinition.objects.create(
        version=version,
        code="REG_BS",
        name="Regulatory Balance Sheet",
        statement_type=StatementDefinition.StatementType.BALANCE_SHEET,
    )
    total_assets = add_line(
        balance,
        "REG_ASSETS",
        "Total assets",
        40,
        is_total=True,
        role="total_assets",
    )
    add_line(
        balance,
        "REG_CA",
        "Current assets",
        10,
        parent=total_assets,
        is_required=True,
        role="current_assets",
    )
    add_line(
        balance,
        "REG_NCA",
        "Non-current assets",
        20,
        parent=total_assets,
        is_required=True,
        role="noncurrent_assets",
    )

    total_le = add_line(
        balance,
        "REG_LE",
        "Total liabilities and equity",
        100,
        is_total=True,
        role="total_liabilities_equity",
    )
    add_line(
        balance,
        "REG_CL",
        "Current liabilities",
        60,
        parent=total_le,
        is_required=True,
        role="current_liabilities",
    )
    add_line(
        balance,
        "REG_NCL",
        "Non-current liabilities",
        70,
        parent=total_le,
        is_required=True,
        role="noncurrent_liabilities",
    )
    add_line(
        balance,
        "REG_EQ",
        "Equity",
        80,
        parent=total_le,
        is_required=True,
        role="equity",
    )
    add_line(
        balance,
        "REG_RESULT",
        "Current result",
        90,
        parent=total_le,
        is_required=True,
        role="current_result",
    )

    cash_flow = StatementDefinition.objects.create(
        version=version,
        code="REG_CF",
        name="Regulatory Cash Flow",
        statement_type=StatementDefinition.StatementType.CASH_FLOW,
    )
    add_line(
        cash_flow,
        "REG_CF_OPEN",
        "Opening cash",
        10,
        is_required=True,
        role="opening_cash",
    )
    net_change = add_line(
        cash_flow,
        "REG_CF_NET",
        "Net cash change",
        50,
        is_total=True,
        role="net_cash_change",
    )
    add_line(
        cash_flow,
        "REG_CFO",
        "Operating cash flow",
        20,
        parent=net_change,
        is_required=True,
        role="operating_cash_flow",
    )
    add_line(
        cash_flow,
        "REG_CFI",
        "Investing cash flow",
        30,
        parent=net_change,
        is_required=True,
        role="investing_cash_flow",
    )
    add_line(
        cash_flow,
        "REG_CFF",
        "Financing cash flow",
        40,
        parent=net_change,
        is_required=True,
        role="financing_cash_flow",
    )
    add_line(
        cash_flow,
        "REG_CF_UNCLASSIFIED",
        "Unclassified cash flow",
        45,
        parent=net_change,
        role="unclassified_cash_flow",
    )
    add_line(
        cash_flow,
        "REG_CF_END",
        "Ending cash",
        60,
        is_required=True,
        role="ending_cash",
    )
    add_line(
        cash_flow,
        "REG_CF_GAP",
        "Cash reconciliation gap",
        70,
        is_required=True,
        role="cash_reconciliation_gap",
    )
    return version


@pytest.fixture
def regulatory_case(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"

    User = get_user_model()
    reviewer = User.objects.create_user(
        username="reg-reviewer",
        email="reg-reviewer@example.com",
        password="secret1234",
    )

    organization = Organization.objects.create(
        name="Sprint 7 Regulatory",
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
        p.period_number: p
        for p in fiscal_year.periods.all()
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
            name="Cash",
            account_type=Account.AccountType.ASSET,
            normal_balance=Account.NormalBalance.DEBIT,
        ),
        "equipment": Account.objects.create(
            organization=organization,
            chart=chart,
            code="24440000",
            name="Equipment",
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
            name="Bank loan",
            account_type=Account.AccountType.LIABILITY,
            normal_balance=Account.NormalBalance.CREDIT,
            current_noncurrent="NONCURRENT",
        ),
        "accrued": Account.objects.create(
            organization=organization,
            chart=chart,
            code="40810000",
            name="Accrued expenses",
            account_type=Account.AccountType.LIABILITY,
            normal_balance=Account.NormalBalance.CREDIT,
            current_noncurrent="CURRENT",
        ),
        "revenue": Account.objects.create(
            organization=organization,
            chart=chart,
            code="70610000",
            name="Services revenue",
            account_type=Account.AccountType.REVENUE,
            normal_balance=Account.NormalBalance.CREDIT,
        ),
        "rent": Account.objects.create(
            organization=organization,
            chart=chart,
            code="62220000",
            name="Rent",
            account_type=Account.AccountType.EXPENSE,
            normal_balance=Account.NormalBalance.DEBIT,
        ),
    }

    def post(number, posting_date, period, lines, *, journal=jod, entry_type=JournalEntry.EntryType.NORMAL):
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

    post(
        "OPEN",
        date(2025, 1, 1),
        periods[1],
        [
            {"account": accounts["cash"], "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": accounts["capital"], "debit": Decimal("0"), "credit": Decimal("1000")},
        ],
        journal=jan,
        entry_type=JournalEntry.EntryType.OPENING,
    )
    post(
        "SALE",
        date(2025, 2, 1),
        periods[2],
        [
            {
                "account": accounts["cash"],
                "debit": Decimal("500"),
                "credit": Decimal("0"),
                "cash_flow_tag": JournalLine.CashFlowTag.OPERATING,
            },
            {"account": accounts["revenue"], "debit": Decimal("0"), "credit": Decimal("500")},
        ],
        journal=sales,
    )
    post(
        "RENT",
        date(2025, 3, 1),
        periods[3],
        [
            {"account": accounts["rent"], "debit": Decimal("200"), "credit": Decimal("0")},
            {
                "account": accounts["cash"],
                "debit": Decimal("0"),
                "credit": Decimal("200"),
                "cash_flow_tag": JournalLine.CashFlowTag.OPERATING,
            },
        ],
    )
    post(
        "CAPEX",
        date(2025, 4, 1),
        periods[4],
        [
            {"account": accounts["equipment"], "debit": Decimal("100"), "credit": Decimal("0")},
            {
                "account": accounts["cash"],
                "debit": Decimal("0"),
                "credit": Decimal("100"),
                "cash_flow_tag": JournalLine.CashFlowTag.INVESTING,
            },
        ],
    )
    post(
        "LOAN",
        date(2025, 5, 1),
        periods[5],
        [
            {
                "account": accounts["cash"],
                "debit": Decimal("300"),
                "credit": Decimal("0"),
                "cash_flow_tag": JournalLine.CashFlowTag.FINANCING,
            },
            {"account": accounts["loan"], "debit": Decimal("0"), "credit": Decimal("300")},
        ],
    )
    post(
        "ADJ",
        date(2025, 12, 31),
        periods[12],
        [
            {"account": accounts["rent"], "debit": Decimal("50"), "credit": Decimal("0")},
            {"account": accounts["accrued"], "debit": Decimal("0"), "credit": Decimal("50")},
        ],
        entry_type=JournalEntry.EntryType.ADJUSTING,
    )

    ensure_financial_statement_configuration(
        organization=organization,
        user=reviewer,
    )
    auto_map_accounts(organization=organization, user=reviewer)

    target_version = build_target_framework()
    profile = create_regulatory_profile(
        organization=organization,
        target_version=target_version,
        user=reviewer,
        name="REG Demo 2026",
    )
    auto_map_regulatory_profile(profile=profile, user=reviewer)

    return {
        "user": reviewer,
        "organization": organization,
        "fiscal_year": fiscal_year,
        "target_version": target_version,
        "profile": profile,
    }


def set_active_organization(client, case):
    client.force_login(case["user"])
    session = client.session
    session["active_organization_id"] = str(case["organization"].pk)
    session.save()


def test_regulatory_auto_mapping_uses_metadata_roles(regulatory_case):
    profile = regulatory_case["profile"]
    mappings = profile.line_mappings.select_related(
        "source_line",
        "target_line",
    )

    assert mappings.filter(
        source_line__code="IS_REVENUE",
        target_line__code="REG_REVENUE",
    ).exists()
    assert mappings.filter(
        source_line__code="BS_CURRENT_RESULT",
        target_line__code="REG_RESULT",
    ).exists()
    assert mappings.filter(
        source_line__code="CF_OPERATING",
        target_line__code="REG_CFO",
    ).exists()

    metrics = profile_metrics(profile)
    assert metrics["unmapped_required_target_count"] == 0
    assert metrics["is_ready"]


def test_regulatory_package_preserves_statement_values(regulatory_case):
    package = build_regulatory_package(
        profile=regulatory_case["profile"],
        fiscal_year=regulatory_case["fiscal_year"],
        end_date=date(2025, 12, 31),
    )

    assert package["is_ready"]
    statements = {
        statement["statement_type"]: statement
        for statement in package["statements"]
    }

    income = statements[StatementDefinition.StatementType.INCOME_STATEMENT]
    assert income["values"]["REG_REVENUE"] == Decimal("500")
    assert income["values"]["REG_EXTERNAL"] == Decimal("250")
    assert income["values"]["REG_NET"] == Decimal("250")

    balance = statements[StatementDefinition.StatementType.BALANCE_SHEET]
    assert balance["values"]["REG_ASSETS"] == Decimal("1600")
    assert balance["values"]["REG_LE"] == Decimal("1600")
    assert balance["validations"][0]["is_ok"]

    cash = statements[StatementDefinition.StatementType.CASH_FLOW]
    assert cash["values"]["REG_CFO"] == Decimal("300")
    assert cash["values"]["REG_CFI"] == Decimal("-100")
    assert cash["values"]["REG_CFF"] == Decimal("300")
    assert cash["values"]["REG_CF_END"] == Decimal("1500")
    assert cash["values"]["REG_CF_GAP"] == Decimal("0")


def test_required_target_gap_blocks_export_readiness(regulatory_case):
    profile = regulatory_case["profile"]
    mapping = profile.line_mappings.get(
        target_line__code="REG_CFO",
    )
    mapping.delete()

    package = build_regulatory_package(
        profile=profile,
        fiscal_year=regulatory_case["fiscal_year"],
        end_date=date(2025, 12, 31),
    )

    assert not package["is_ready"]
    assert any(
        warning["code"] == "UNMAPPED_REQUIRED_TARGET_LINES"
        for warning in package["warnings"]
    )


def test_manual_regulatory_mapping_survives_auto_map(regulatory_case):
    profile = regulatory_case["profile"]
    source_line = StatementLine.objects.get(
        definition__version=profile.source_version,
        code="IS_EXTERNAL_SERVICES",
    )
    target_line = StatementLine.objects.get(
        definition__version=profile.target_version,
        code="REG_EXTERNAL",
    )

    update_regulatory_mapping(
        profile=profile,
        source_line=source_line,
        target_line=target_line,
        multiplier=Decimal("1"),
        user=regulatory_case["user"],
    )
    auto_map_regulatory_profile(
        profile=profile,
        user=regulatory_case["user"],
    )

    mapping = profile.line_mappings.get(source_line=source_line)
    assert mapping.mapping_type == RegulatoryStatementLineMapping.MappingType.MANUAL
    assert mapping.target_line == target_line


def test_regulatory_export_creates_snapshot_file_and_hash(regulatory_case):
    job = create_regulatory_export(
        profile=regulatory_case["profile"],
        fiscal_year=regulatory_case["fiscal_year"],
        end_date=date(2025, 12, 31),
        export_format=ExportJob.Format.JSON,
        user=regulatory_case["user"],
    )

    assert job.status == ExportJob.Status.DONE
    assert job.snapshot.report_type == ReportSnapshot.ReportType.REGULATORY_PACKAGE
    assert job.content_sha256
    assert job.file

    job.file.open("rb")
    try:
        content = job.file.read()
    finally:
        job.file.close()

    assert content.startswith(b"{")
    assert b"REG_DEMO" in content


def test_xlsx_and_pdf_renderers_generate_real_files(regulatory_case):
    package = build_regulatory_package(
        profile=regulatory_case["profile"],
        fiscal_year=regulatory_case["fiscal_year"],
        end_date=date(2025, 12, 31),
    )
    payload = serialize_regulatory_package(package)

    xlsx = render_export_bytes(
        payload=payload,
        export_format=ExportJob.Format.XLSX,
    )
    pdf = render_export_bytes(
        payload=payload,
        export_format=ExportJob.Format.PDF,
    )

    assert xlsx.startswith(b"PK")
    assert pdf.startswith(b"%PDF")


def test_regulatory_ui_and_export_download(client, regulatory_case):
    set_active_organization(client, regulatory_case)

    response = client.get(
        reverse(
            "financial_statements:regulatory-detail",
            kwargs={"pk": regulatory_case["profile"].pk},
        ),
        {
            "fiscal_year": str(regulatory_case["fiscal_year"].pk),
            "end_date": "2025-12-31",
        },
    )
    assert response.status_code == 200
    assert "REG_REVENUE" in response.content.decode()

    job = create_regulatory_export(
        profile=regulatory_case["profile"],
        fiscal_year=regulatory_case["fiscal_year"],
        end_date=date(2025, 12, 31),
        export_format=ExportJob.Format.CSV,
        user=regulatory_case["user"],
    )

    response = client.get(
        reverse("exports:download", kwargs={"pk": job.pk})
    )
    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment;")
