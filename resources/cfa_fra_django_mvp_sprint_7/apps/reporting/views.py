from decimal import Decimal

from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.organizations.mixins import ActiveOrganizationMixin

from .forms import (
    GeneralLedgerFilterForm,
    JournalFilterForm,
    TrialBalanceFilterForm,
)
from .selectors import (
    journal_lines,
    journal_totals,
    ledger_lines,
    trial_balance_rows,
    trial_balance_totals,
)
from .types import TrialBalanceVariant


def _default_bound_data(form_class, organization):
    probe = form_class(organization=organization)
    data = {}

    for name, field in probe.fields.items():
        value = probe.initial.get(name, field.initial)
        if callable(value):
            value = value()

        if value in (None, ""):
            continue

        if hasattr(value, "pk"):
            data[name] = str(value.pk)
        elif hasattr(value, "isoformat"):
            data[name] = value.isoformat()
        elif isinstance(value, bool):
            if value:
                data[name] = "on"
        else:
            data[name] = value

    return data


def bound_filter_form(form_class, request, organization):
    data = request.GET if request.GET else _default_bound_data(
        form_class,
        organization,
    )
    return form_class(data, organization=organization)


def split_signed_balance(value):
    value = value or Decimal("0")
    if value >= 0:
        return value, Decimal("0")
    return Decimal("0"), -value


class JournalReportView(ActiveOrganizationMixin, TemplateView):
    template_name = "reporting/journal.html"

    def get(self, request, *args, **kwargs):
        form = bound_filter_form(
            JournalFilterForm,
            request,
            self.organization,
        )

        rows = None
        totals = {
            "total_debit": Decimal("0"),
            "total_credit": Decimal("0"),
        }
        page_obj = None

        if form.is_valid():
            cleaned = form.cleaned_data
            rows = journal_lines(
                organization=self.organization,
                fiscal_year=cleaned["fiscal_year"],
                start_date=cleaned.get("start_date"),
                end_date=cleaned.get("end_date"),
                journal=cleaned.get("journal"),
                entry_type=cleaned.get("entry_type"),
                query=cleaned.get("query", ""),
            )
            totals = journal_totals(rows)
            paginator = Paginator(rows, 100)
            page_obj = paginator.get_page(request.GET.get("page"))

        context = {
            "organization": self.organization,
            "membership": self.membership,
            "form": form,
            "page_obj": page_obj,
            "rows": page_obj.object_list if page_obj else [],
            "totals": totals,
        }

        return render(request, self.template_name, context)


class GeneralLedgerView(ActiveOrganizationMixin, TemplateView):
    template_name = "reporting/general_ledger.html"

    def get(self, request, *args, **kwargs):
        form = bound_filter_form(
            GeneralLedgerFilterForm,
            request,
            self.organization,
        )

        report = None
        page_obj = None
        opening_debit_balance = Decimal("0")
        opening_credit_balance = Decimal("0")
        closing_debit_balance = Decimal("0")
        closing_credit_balance = Decimal("0")

        if form.is_valid():
            cleaned = form.cleaned_data
            report = ledger_lines(
                organization=self.organization,
                fiscal_year=cleaned["fiscal_year"],
                account=cleaned["account"],
                start_date=cleaned.get("start_date"),
                end_date=cleaned.get("end_date"),
                variant=cleaned.get("variant") or TrialBalanceVariant.ADJUSTED,
                query="",
            )

            paginator = Paginator(report["queryset"], 100)
            page_obj = paginator.get_page(request.GET.get("page"))

            for row in page_obj.object_list:
                (
                    row.running_debit_balance,
                    row.running_credit_balance,
                ) = split_signed_balance(row.running_signed_balance)

            (
                opening_debit_balance,
                opening_credit_balance,
            ) = split_signed_balance(report["opening_signed"])

            (
                closing_debit_balance,
                closing_credit_balance,
            ) = split_signed_balance(report["closing_signed"])

        context = {
            "organization": self.organization,
            "membership": self.membership,
            "form": form,
            "report": report,
            "page_obj": page_obj,
            "rows": page_obj.object_list if page_obj else [],
            "opening_debit_balance": opening_debit_balance,
            "opening_credit_balance": opening_credit_balance,
            "closing_debit_balance": closing_debit_balance,
            "closing_credit_balance": closing_credit_balance,
        }
        return render(request, self.template_name, context)


class TrialBalanceView(ActiveOrganizationMixin, TemplateView):
    template_name = "reporting/trial_balance.html"

    def get(self, request, *args, **kwargs):
        form = bound_filter_form(
            TrialBalanceFilterForm,
            request,
            self.organization,
        )

        rows = []
        totals = {
            "movement_debit": Decimal("0"),
            "movement_credit": Decimal("0"),
            "balance_debit": Decimal("0"),
            "balance_credit": Decimal("0"),
        }
        page_obj = None
        difference = Decimal("0")

        if form.is_valid():
            cleaned = form.cleaned_data
            queryset = trial_balance_rows(
                organization=self.organization,
                fiscal_year=cleaned["fiscal_year"],
                as_of_date=cleaned["as_of_date"],
                variant=cleaned["variant"],
                query=cleaned.get("query", ""),
                include_zero=cleaned.get("include_zero", False),
            )
            totals = trial_balance_totals(queryset)
            difference = totals["balance_debit"] - totals["balance_credit"]

            paginator = Paginator(queryset, 100)
            page_obj = paginator.get_page(request.GET.get("page"))
            rows = page_obj.object_list

        context = {
            "organization": self.organization,
            "membership": self.membership,
            "form": form,
            "rows": rows,
            "page_obj": page_obj,
            "totals": totals,
            "difference": difference,
            "is_balanced": difference == Decimal("0"),
            "variants": TrialBalanceVariant,
        }
        return render(request, self.template_name, context)
