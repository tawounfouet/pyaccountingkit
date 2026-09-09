from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.organizations.mixins import ActiveOrganizationMixin
from apps.organizations.permissions import REVIEW_ROLES, WRITE_ROLES

from .forms import (
    AccountForm,
    ChartOfAccountsForm,
    JournalEntryHeaderForm,
    JournalForm,
    JournalLineDraftForm,
    JournalLineDraftFormSet,
    ReverseEntryForm,
)
from .models import Account, ChartOfAccounts, Journal, JournalEntry
from .selectors import (
    accounts_for_organization,
    charts_for_organization,
    journal_entries_for_organization,
    journals_for_organization,
)
from .services import (
    create_draft_entry,
    post_journal_entry,
    reverse_journal_entry,
    update_draft_entry,
    validate_journal_entry,
)


def request_audit_metadata(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    source_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
    return {
        "path": request.path,
        "method": request.method,
        "htmx": bool(getattr(request, "htmx", False)),
        "source_ip": source_ip,
    }


def validation_error_message(exc):
    if hasattr(exc, "messages"):
        return " ".join(exc.messages)
    return str(exc)


def active_lines_from_formset(formset):
    return [
        form.cleaned_data
        for form in formset.forms
        if form.cleaned_data and not form.cleaned_data.get("DELETE")
    ]


class WriteAccountingMixin(ActiveOrganizationMixin):
    allowed_roles = WRITE_ROLES


class ReviewAccountingMixin(ActiveOrganizationMixin):
    allowed_roles = REVIEW_ROLES


class ChartListView(ActiveOrganizationMixin, ListView):
    template_name = "accounting/charts.html"
    context_object_name = "charts"

    def get_queryset(self):
        return charts_for_organization(organization=self.organization)


class ChartCreateView(WriteAccountingMixin, View):
    template_name = "accounting/chart_form.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {"form": ChartOfAccountsForm(organization=self.organization)},
        )

    def post(self, request):
        form = ChartOfAccountsForm(request.POST, organization=self.organization)
        if form.is_valid():
            chart = form.save(commit=False)
            chart.organization = self.organization
            try:
                chart.full_clean()
                chart.save()
            except (ValidationError, IntegrityError) as exc:
                form.add_error(None, str(exc))
            else:
                if chart.is_default:
                    ChartOfAccounts.objects.filter(
                        organization=self.organization,
                        is_default=True,
                    ).exclude(pk=chart.pk).update(is_default=False)
                messages.success(request, "Plan comptable créé.")
                return redirect("accounting:chart-detail", pk=chart.pk)

        return render(request, self.template_name, {"form": form}, status=400)


class ChartDetailView(ActiveOrganizationMixin, DetailView):
    template_name = "accounting/chart_detail.html"
    context_object_name = "chart"

    def get_queryset(self):
        return ChartOfAccounts.objects.filter(
            organization=self.organization
        ).prefetch_related("accounts")


class AccountListView(ActiveOrganizationMixin, ListView):
    template_name = "accounting/accounts.html"
    context_object_name = "accounts"
    paginate_by = 50

    def get_queryset(self):
        return accounts_for_organization(
            organization=self.organization,
            query=self.request.GET.get("q", "").strip(),
            chart_id=self.request.GET.get("chart"),
            account_type=self.request.GET.get("type"),
            active=self.request.GET.get("active"),
        )

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["accounting/_accounts_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["charts"] = charts_for_organization(organization=self.organization)
        context["account_types"] = Account.AccountType.choices
        return context


class AccountCreateView(WriteAccountingMixin, View):
    template_name = "accounting/account_form.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": AccountForm(organization=self.organization),
                "mode": "create",
            },
        )

    def post(self, request):
        form = AccountForm(request.POST, organization=self.organization)
        if form.is_valid():
            account = form.save(commit=False)
            account.organization = self.organization
            try:
                account.full_clean()
                account.save()
            except (ValidationError, IntegrityError) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Compte {account.code} créé.")
                return redirect("accounting:accounts")

        return render(
            request,
            self.template_name,
            {"form": form, "mode": "create"},
            status=400,
        )


class AccountUpdateView(WriteAccountingMixin, View):
    template_name = "accounting/account_form.html"

    def get_object(self):
        return get_object_or_404(
            Account,
            pk=self.kwargs["pk"],
            organization=self.organization,
        )

    def get(self, request, pk):
        account = self.get_object()
        return render(
            request,
            self.template_name,
            {
                "form": AccountForm(instance=account, organization=self.organization),
                "mode": "update",
                "account": account,
            },
        )

    def post(self, request, pk):
        account = self.get_object()
        form = AccountForm(
            request.POST,
            instance=account,
            organization=self.organization,
        )
        if form.is_valid():
            account = form.save(commit=False)
            try:
                account.full_clean()
                account.save()
            except (ValidationError, IntegrityError) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Compte {account.code} mis à jour.")
                return redirect("accounting:accounts")

        return render(
            request,
            self.template_name,
            {"form": form, "mode": "update", "account": account},
            status=400,
        )


class JournalListView(ActiveOrganizationMixin, ListView):
    template_name = "accounting/journals.html"
    context_object_name = "journals"
    paginate_by = 50

    def get_queryset(self):
        return journals_for_organization(
            organization=self.organization,
            query=self.request.GET.get("q", "").strip(),
            journal_type=self.request.GET.get("type"),
            active=self.request.GET.get("active"),
        )

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["accounting/_journals_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["journal_types"] = Journal.JournalType.choices
        return context


class JournalCreateView(WriteAccountingMixin, View):
    template_name = "accounting/journal_form.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {"form": JournalForm(organization=self.organization), "mode": "create"},
        )

    def post(self, request):
        form = JournalForm(request.POST, organization=self.organization)
        if form.is_valid():
            journal = form.save(commit=False)
            journal.organization = self.organization
            try:
                journal.full_clean()
                journal.save()
            except (ValidationError, IntegrityError) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Journal {journal.code} créé.")
                return redirect("accounting:journals")

        return render(
            request,
            self.template_name,
            {"form": form, "mode": "create"},
            status=400,
        )


class JournalUpdateView(WriteAccountingMixin, View):
    template_name = "accounting/journal_form.html"

    def get_object(self):
        return get_object_or_404(
            Journal,
            pk=self.kwargs["pk"],
            organization=self.organization,
        )

    def get(self, request, pk):
        journal = self.get_object()
        return render(
            request,
            self.template_name,
            {
                "form": JournalForm(instance=journal, organization=self.organization),
                "mode": "update",
                "journal": journal,
            },
        )

    def post(self, request, pk):
        journal = self.get_object()
        form = JournalForm(
            request.POST,
            instance=journal,
            organization=self.organization,
        )
        if form.is_valid():
            journal = form.save(commit=False)
            try:
                journal.full_clean()
                journal.save()
            except (ValidationError, IntegrityError) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Journal {journal.code} mis à jour.")
                return redirect("accounting:journals")

        return render(
            request,
            self.template_name,
            {"form": form, "mode": "update", "journal": journal},
            status=400,
        )


class EntryListView(ActiveOrganizationMixin, ListView):
    template_name = "accounting/entries.html"
    context_object_name = "entries"
    paginate_by = 50

    def get_queryset(self):
        return journal_entries_for_organization(
            organization=self.organization,
            query=self.request.GET.get("q", "").strip(),
            journal_id=self.request.GET.get("journal"),
            status=self.request.GET.get("status"),
        )

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["accounting/_entries_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["journals"] = journals_for_organization(
            organization=self.organization,
            active="1",
        )
        context["statuses"] = JournalEntry.Status.choices
        return context


class EntryDetailView(ActiveOrganizationMixin, DetailView):
    template_name = "accounting/entry_detail.html"
    context_object_name = "entry"

    def get_queryset(self):
        return (
            JournalEntry.objects.filter(organization=self.organization)
            .select_related(
                "journal",
                "period",
                "period__fiscal_year",
                "created_by",
                "validated_by",
                "posted_by",
            )
            .prefetch_related(
                "lines__account",
                "lines__counterparty",
                "lines__cost_center",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_review"] = self.membership.role in REVIEW_ROLES
        return context


class EntryCreateView(WriteAccountingMixin, View):
    template_name = "accounting/entry_form.html"

    def _forms(self, data=None):
        header = JournalEntryHeaderForm(
            data=data,
            organization=self.organization,
        )
        lines = JournalLineDraftFormSet(
            data=data,
            prefix="lines",
            form_kwargs={"organization": self.organization},
        )
        return header, lines

    def get(self, request):
        header, lines = self._forms()
        return render(
            request,
            self.template_name,
            {"form": header, "line_formset": lines, "mode": "create"},
        )

    def post(self, request):
        header, lines = self._forms(request.POST)
        if header.is_valid() and lines.is_valid():
            cleaned_lines = active_lines_from_formset(lines)
            try:
                entry = create_draft_entry(
                    organization=self.organization,
                    user=request.user,
                    lines=cleaned_lines,
                    audit_metadata=request_audit_metadata(request),
                    **header.cleaned_data,
                )
            except ValidationError as exc:
                header.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"Écriture {entry.entry_number} enregistrée en brouillon.",
                )
                return redirect("accounting:entry-detail", pk=entry.pk)

        return render(
            request,
            self.template_name,
            {"form": header, "line_formset": lines, "mode": "create"},
            status=400,
        )


class EntryUpdateView(WriteAccountingMixin, View):
    template_name = "accounting/entry_form.html"

    def get_entry(self):
        entry = get_object_or_404(
            JournalEntry.objects.prefetch_related("lines"),
            pk=self.kwargs["pk"],
            organization=self.organization,
        )
        if entry.status != JournalEntry.Status.DRAFT:
            raise Http404("Seules les écritures brouillon sont modifiables.")
        return entry

    def _initial_lines(self, entry):
        return [
            {
                "account": line.account,
                "description": line.description,
                "debit": line.debit,
                "credit": line.credit,
                "counterparty": line.counterparty,
                "cost_center": line.cost_center,
                "cash_flow_tag": line.cash_flow_tag,
            }
            for line in entry.lines.all().order_by("line_number")
        ]

    def get(self, request, pk):
        entry = self.get_entry()
        header = JournalEntryHeaderForm(
            instance=entry,
            organization=self.organization,
        )
        lines = JournalLineDraftFormSet(
            prefix="lines",
            initial=self._initial_lines(entry),
            form_kwargs={"organization": self.organization},
        )
        return render(
            request,
            self.template_name,
            {"form": header, "line_formset": lines, "entry": entry, "mode": "update"},
        )

    def post(self, request, pk):
        entry = self.get_entry()
        header = JournalEntryHeaderForm(
            request.POST,
            instance=entry,
            organization=self.organization,
        )
        lines = JournalLineDraftFormSet(
            request.POST,
            prefix="lines",
            form_kwargs={"organization": self.organization},
        )

        if header.is_valid() and lines.is_valid():
            cleaned_lines = active_lines_from_formset(lines)
            try:
                entry = update_draft_entry(
                    entry=entry,
                    user=request.user,
                    header_data=header.cleaned_data,
                    lines=cleaned_lines,
                    audit_metadata=request_audit_metadata(request),
                )
            except ValidationError as exc:
                header.add_error(None, exc)
            else:
                messages.success(request, f"Écriture {entry.entry_number} mise à jour.")
                return redirect("accounting:entry-detail", pk=entry.pk)

        return render(
            request,
            self.template_name,
            {"form": header, "line_formset": lines, "entry": entry, "mode": "update"},
            status=400,
        )


class EntryLineFormView(WriteAccountingMixin, View):
    def get(self, request):
        raw_total = request.GET.get("lines-TOTAL_FORMS", "0")
        try:
            index = int(raw_total)
        except (TypeError, ValueError):
            return HttpResponseBadRequest("TOTAL_FORMS invalide.")

        form = JournalLineDraftForm(
            prefix=f"lines-{index}",
            organization=self.organization,
        )
        return render(
            request,
            "accounting/_entry_line_row.html",
            {
                "line_form": form,
                "line_index": index,
            },
        )


class EntryLineRemoveView(WriteAccountingMixin, View):
    def post(self, request, index):
        response = render(
            request,
            "accounting/_entry_line_deleted.html",
            {"line_index": index},
        )
        response["HX-Trigger"] = "entryLineChanged"
        return response


class EntryTotalsView(WriteAccountingMixin, View):
    def post(self, request):
        try:
            total_forms = int(request.POST.get("lines-TOTAL_FORMS", "0"))
        except (TypeError, ValueError):
            return HttpResponseBadRequest("TOTAL_FORMS invalide.")

        total_debit = Decimal("0")
        total_credit = Decimal("0")
        active_count = 0

        for index in range(total_forms):
            if request.POST.get(f"lines-{index}-DELETE"):
                continue

            debit = self._decimal(request.POST.get(f"lines-{index}-debit"))
            credit = self._decimal(request.POST.get(f"lines-{index}-credit"))

            if debit > 0 or credit > 0:
                active_count += 1

            total_debit += debit
            total_credit += credit

        difference = total_debit - total_credit

        return render(
            request,
            "accounting/_entry_totals.html",
            {
                "total_debit": total_debit,
                "total_credit": total_credit,
                "difference": difference,
                "is_balanced": (
                    active_count >= 2
                    and total_debit > 0
                    and difference == Decimal("0")
                ),
                "active_count": active_count,
            },
        )

    @staticmethod
    def _decimal(value):
        normalized = (value or "").strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
        if not normalized:
            return Decimal("0")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return Decimal("0")


class EntryValidateView(ReviewAccountingMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(
            JournalEntry,
            pk=pk,
            organization=self.organization,
        )
        try:
            entry = validate_journal_entry(
                entry=entry,
                user=request.user,
                audit_metadata=request_audit_metadata(request),
            )
        except ValidationError as exc:
            messages.error(request, validation_error_message(exc))
        else:
            messages.success(
                request,
                f"Écriture {entry.entry_number} validée. Elle peut maintenant être postée.",
            )
        return redirect("accounting:entry-detail", pk=entry.pk)


class EntryPostView(ReviewAccountingMixin, View):
    def post(self, request, pk):
        entry = get_object_or_404(
            JournalEntry,
            pk=pk,
            organization=self.organization,
        )
        try:
            entry = post_journal_entry(
                entry=entry,
                user=request.user,
                audit_metadata=request_audit_metadata(request),
            )
        except ValidationError as exc:
            messages.error(request, validation_error_message(exc))
        else:
            messages.success(
                request,
                f"Écriture {entry.entry_number} postée et désormais immuable.",
            )
        return redirect("accounting:entry-detail", pk=entry.pk)


class EntryReverseView(ReviewAccountingMixin, View):
    template_name = "accounting/entry_reverse.html"

    def get_entry(self):
        return get_object_or_404(
            JournalEntry.objects.select_related(
                "journal",
                "period",
                "period__fiscal_year",
            ).prefetch_related("lines__account"),
            pk=self.kwargs["pk"],
            organization=self.organization,
        )

    def get(self, request, pk):
        entry = self.get_entry()
        if entry.status != JournalEntry.Status.POSTED:
            raise Http404("Seule une écriture postée peut être extournée.")

        form = ReverseEntryForm(
            organization=self.organization,
            initial_period=entry.period,
            initial={"posting_date": entry.posting_date},
        )
        return render(
            request,
            self.template_name,
            {"entry": entry, "form": form},
        )

    def post(self, request, pk):
        entry = self.get_entry()
        form = ReverseEntryForm(
            request.POST,
            organization=self.organization,
            initial_period=entry.period,
        )

        if form.is_valid():
            try:
                reversal = reverse_journal_entry(
                    entry=entry,
                    user=request.user,
                    period=form.cleaned_data["period"],
                    posting_date=form.cleaned_data["posting_date"],
                    reason=form.cleaned_data.get("reason", ""),
                    audit_metadata=request_audit_metadata(request),
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"Écriture {entry.entry_number} extournée par {reversal.entry_number}.",
                )
                return redirect("accounting:entry-detail", pk=reversal.pk)

        return render(
            request,
            self.template_name,
            {"entry": entry, "form": form},
            status=400,
        )
