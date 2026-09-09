from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.accounting.models import Account
from apps.organizations.mixins import ActiveOrganizationMixin
from apps.organizations.permissions import WRITE_ROLES
from apps.referentials.models import (
    StatementAccountMapping,
    StatementDefinition,
    StatementLine,
)

from .forms import (
    FinancialStatementConfigurationForm,
    FinancialStatementPeriodForm,
    StatementAccountMappingForm,
)
from .services import (
    auto_map_accounts,
    build_balance_sheet,
    build_cash_flow_statement,
    build_income_statement,
    build_ratios,
    ensure_financial_statement_configuration,
    statement_line_account_ids,
    update_financial_statement_configuration,
    update_statement_account_mapping,
)


def _bound_period_form(request, organization):
    if request.GET:
        return FinancialStatementPeriodForm(
            request.GET,
            organization=organization,
        )

    probe = FinancialStatementPeriodForm(organization=organization)
    data = {}
    for key, value in probe.initial.items():
        if hasattr(value, "pk"):
            data[key] = str(value.pk)
        elif hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        else:
            data[key] = value
    return FinancialStatementPeriodForm(
        data,
        organization=organization,
    )


def _mapping_stats(organization, version):
    total_accounts = Account.objects.filter(
        organization=organization,
        is_active=True,
    ).count()
    mapped_accounts = (
        StatementAccountMapping.objects.filter(
            account__organization=organization,
            statement_line__definition__version=version,
        )
        .values("account_id")
        .distinct()
        .count()
    )
    return {
        "total_accounts": total_accounts,
        "mapped_accounts": mapped_accounts,
        "unmapped_accounts": max(total_accounts - mapped_accounts, 0),
        "coverage": (
            (Decimal(mapped_accounts) / Decimal(total_accounts)) * Decimal("100")
            if total_accounts
            else Decimal("0")
        ),
    }


class WriteFinancialStatementsMixin(ActiveOrganizationMixin):
    allowed_roles = WRITE_ROLES


class FinancialStatementsHomeView(ActiveOrganizationMixin, TemplateView):
    template_name = "financial_statements/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configuration = ensure_financial_statement_configuration(
            organization=self.organization
        )
        context["configuration"] = configuration
        context["mapping_stats"] = _mapping_stats(
            self.organization,
            configuration.framework_version,
        )
        context["definitions"] = configuration.framework_version.statement_definitions.all().order_by(
            "statement_type",
            "code",
        )
        return context


class StatementMappingView(WriteFinancialStatementsMixin, TemplateView):
    template_name = "financial_statements/mappings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configuration = ensure_financial_statement_configuration(
            organization=self.organization,
            user=self.request.user,
        )
        version = configuration.framework_version

        mappings = {
            mapping.account_id: mapping
            for mapping in StatementAccountMapping.objects.filter(
                account__organization=self.organization,
                statement_line__definition__version=version,
            ).select_related(
                "statement_line",
                "statement_line__definition",
            )
        }

        rows = []
        for account in Account.objects.filter(
            organization=self.organization,
        ).select_related("chart").order_by("code"):
            mapping = mappings.get(account.id)
            rows.append(
                {
                    "account": account,
                    "mapping": mapping,
                    "form": StatementAccountMappingForm(
                        framework_version=version,
                        initial_line=(
                            mapping.statement_line
                            if mapping
                            else None
                        ),
                        prefix=f"mapping-{account.pk}",
                    ),
                }
            )

        context["configuration"] = configuration
        context["rows"] = rows
        context["mapping_stats"] = _mapping_stats(
            self.organization,
            version,
        )
        return context


class StatementMappingUpdateView(WriteFinancialStatementsMixin, View):
    def post(self, request, account_id):
        configuration = ensure_financial_statement_configuration(
            organization=self.organization,
            user=request.user,
        )
        account = get_object_or_404(
            Account,
            pk=account_id,
            organization=self.organization,
        )

        form = StatementAccountMappingForm(
            request.POST,
            framework_version=configuration.framework_version,
            prefix=f"mapping-{account.pk}",
        )

        if form.is_valid():
            update_statement_account_mapping(
                organization=self.organization,
                account=account,
                statement_line=form.cleaned_data["statement_line"],
                user=request.user,
            )
            messages.success(
                request,
                f"Mapping du compte {account.code} mis à jour.",
            )

        if getattr(request, "htmx", False):
            mapping = (
                StatementAccountMapping.objects.filter(
                    account=account,
                    statement_line__definition__version=configuration.framework_version,
                )
                .select_related(
                    "statement_line",
                    "statement_line__definition",
                )
                .first()
            )
            return render(
                request,
                "financial_statements/_mapping_row.html",
                {
                    "account": account,
                    "mapping": mapping,
                    "form": StatementAccountMappingForm(
                        framework_version=configuration.framework_version,
                        initial_line=(
                            mapping.statement_line
                            if mapping
                            else None
                        ),
                        prefix=f"mapping-{account.pk}",
                    ),
                },
                status=200 if form.is_valid() else 400,
            )

        return redirect("financial_statements:mappings")


class StatementAutoMapView(WriteFinancialStatementsMixin, View):
    def post(self, request):
        result = auto_map_accounts(
            organization=self.organization,
            user=request.user,
        )
        messages.success(
            request,
            (
                f"Auto-mapping terminé : {result['created']} mapping(s) créé(s), "
                f"{result['manual_preserved_or_unmapped']} compte(s) conservé(s) ou non classé(s)."
            ),
        )
        return redirect("financial_statements:mappings")


class FinancialStatementConfigurationView(WriteFinancialStatementsMixin, View):
    template_name = "financial_statements/configuration.html"

    def get(self, request):
        configuration = ensure_financial_statement_configuration(
            organization=self.organization,
            user=request.user,
        )
        return render(
            request,
            self.template_name,
            {
                "configuration": configuration,
                "form": FinancialStatementConfigurationForm(
                    configuration=configuration,
                ),
            },
        )

    def post(self, request):
        configuration = ensure_financial_statement_configuration(
            organization=self.organization,
            user=request.user,
        )
        form = FinancialStatementConfigurationForm(
            request.POST,
            configuration=configuration,
        )
        if form.is_valid():
            update_financial_statement_configuration(
                configuration=configuration,
                comparative_enabled=form.cleaned_data["comparative_enabled"],
                infer_cash_flow_categories=form.cleaned_data[
                    "infer_cash_flow_categories"
                ],
                cash_account_prefixes=form.cleaned_data["cash_account_prefixes"],
                user=request.user,
            )
            messages.success(
                request,
                "Configuration des états financiers mise à jour.",
            )
            return redirect("financial_statements:index")

        return render(
            request,
            self.template_name,
            {
                "configuration": configuration,
                "form": form,
            },
            status=400,
        )


class IncomeStatementView(ActiveOrganizationMixin, View):
    template_name = "financial_statements/income_statement.html"

    def get(self, request):
        form = _bound_period_form(request, self.organization)
        report = None
        if form.is_valid():
            report = build_income_statement(
                organization=self.organization,
                fiscal_year=form.cleaned_data["fiscal_year"],
                end_date=form.cleaned_data.get("end_date"),
            )
        return render(
            request,
            self.template_name,
            {
                "organization": self.organization,
                "membership": self.membership,
                "form": form,
                "report": report,
            },
        )


class BalanceSheetView(ActiveOrganizationMixin, View):
    template_name = "financial_statements/balance_sheet.html"

    def get(self, request):
        form = _bound_period_form(request, self.organization)
        report = None
        if form.is_valid():
            report = build_balance_sheet(
                organization=self.organization,
                fiscal_year=form.cleaned_data["fiscal_year"],
                as_of_date=form.cleaned_data.get("end_date"),
            )
        return render(
            request,
            self.template_name,
            {
                "organization": self.organization,
                "membership": self.membership,
                "form": form,
                "report": report,
            },
        )


class CashFlowStatementView(ActiveOrganizationMixin, View):
    template_name = "financial_statements/cash_flow.html"

    def get(self, request):
        form = _bound_period_form(request, self.organization)
        report = None
        if form.is_valid():
            report = build_cash_flow_statement(
                organization=self.organization,
                fiscal_year=form.cleaned_data["fiscal_year"],
                end_date=form.cleaned_data.get("end_date"),
            )
        return render(
            request,
            self.template_name,
            {
                "organization": self.organization,
                "membership": self.membership,
                "form": form,
                "report": report,
            },
        )


class FinancialRatiosView(ActiveOrganizationMixin, View):
    template_name = "financial_statements/ratios.html"

    def get(self, request):
        form = _bound_period_form(request, self.organization)
        report = None

        if form.is_valid():
            report = build_ratios(
                organization=self.organization,
                fiscal_year=form.cleaned_data["fiscal_year"],
                end_date=form.cleaned_data.get("end_date"),
            )
            for ratio in report["ratios"]:
                value = ratio["value"]
                if value is None:
                    ratio["display_value"] = "n/a"
                elif ratio["format"] == "percent":
                    ratio["display_value"] = f"{value * Decimal('100'):.2f} %"
                else:
                    ratio["display_value"] = f"{value:.2f}x"

        return render(
            request,
            self.template_name,
            {
                "organization": self.organization,
                "membership": self.membership,
                "form": form,
                "report": report,
            },
        )


class StatementLineDetailView(ActiveOrganizationMixin, View):
    template_name = "financial_statements/line_detail.html"

    def get(self, request, line_id):
        configuration = ensure_financial_statement_configuration(
            organization=self.organization
        )
        line = get_object_or_404(
            StatementLine.objects.select_related(
                "definition",
                "definition__version",
            ),
            pk=line_id,
            definition__version=configuration.framework_version,
        )
        form = _bound_period_form(request, self.organization)
        mappings = []

        if form.is_valid():
            account_ids = statement_line_account_ids(line)
            mappings = list(
                StatementAccountMapping.objects.filter(
                    account__organization=self.organization,
                    account_id__in=account_ids,
                    statement_line__definition__version=configuration.framework_version,
                )
                .select_related(
                    "account",
                    "statement_line",
                )
                .order_by("account__code")
            )

        return render(
            request,
            self.template_name,
            {
                "organization": self.organization,
                "membership": self.membership,
                "line": line,
                "form": form,
                "mappings": mappings,
            },
        )
