from decimal import Decimal

from django import forms
from django.forms import formset_factory

from apps.organizations.models import AccountingPeriod

from .models import Account, ChartOfAccounts, CostCenter, Counterparty, Journal, JournalEntry, JournalLine


FORM_CONTROL = {"class": "form-control"}
FORM_SELECT = {"class": "form-select"}


class OrganizationScopedFormMixin:
    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization


class ChartOfAccountsForm(OrganizationScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ChartOfAccounts
        fields = ["code", "name", "is_default", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs=FORM_CONTROL),
            "name": forms.TextInput(attrs=FORM_CONTROL),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AccountForm(OrganizationScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "chart",
            "code",
            "name",
            "account_type",
            "normal_balance",
            "current_noncurrent",
            "parent",
            "is_active",
        ]
        widgets = {
            "chart": forms.Select(attrs=FORM_SELECT),
            "code": forms.TextInput(attrs=FORM_CONTROL),
            "name": forms.TextInput(attrs=FORM_CONTROL),
            "account_type": forms.Select(attrs=FORM_SELECT),
            "normal_balance": forms.Select(attrs=FORM_SELECT),
            "current_noncurrent": forms.TextInput(attrs=FORM_CONTROL),
            "parent": forms.Select(attrs=FORM_SELECT),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["chart"].queryset = ChartOfAccounts.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")
        parent_qs = Account.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")
        if self.instance and self.instance.pk:
            parent_qs = parent_qs.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parent_qs
        self.fields["parent"].required = False

    def clean(self):
        cleaned = super().clean()
        chart = cleaned.get("chart")
        parent = cleaned.get("parent")

        if chart and chart.organization_id != self.organization.id:
            self.add_error("chart", "Plan comptable non autorisé.")

        if parent:
            if parent.organization_id != self.organization.id:
                self.add_error("parent", "Compte parent non autorisé.")
            elif chart and parent.chart_id != chart.id:
                self.add_error("parent", "Le parent doit appartenir au même plan comptable.")

        return cleaned


class JournalForm(OrganizationScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Journal
        fields = ["code", "name", "journal_type", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs=FORM_CONTROL),
            "name": forms.TextInput(attrs=FORM_CONTROL),
            "journal_type": forms.Select(attrs=FORM_SELECT),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class JournalEntryHeaderForm(OrganizationScopedFormMixin, forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = [
            "journal",
            "period",
            "entry_number",
            "posting_date",
            "description",
            "reference",
            "entry_type",
        ]
        widgets = {
            "journal": forms.Select(attrs=FORM_SELECT),
            "period": forms.Select(attrs=FORM_SELECT),
            "entry_number": forms.TextInput(attrs=FORM_CONTROL),
            "posting_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "reference": forms.TextInput(attrs=FORM_CONTROL),
            "entry_type": forms.Select(attrs=FORM_SELECT),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["journal"].queryset = Journal.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")
        self.fields["period"].queryset = AccountingPeriod.objects.filter(
            fiscal_year__organization=organization,
            status=AccountingPeriod.Status.OPEN,
        ).select_related("fiscal_year").order_by("start_date")

    def clean(self):
        cleaned = super().clean()
        journal = cleaned.get("journal")
        period = cleaned.get("period")
        posting_date = cleaned.get("posting_date")

        if journal and journal.organization_id != self.organization.id:
            self.add_error("journal", "Journal non autorisé.")

        if period and period.fiscal_year.organization_id != self.organization.id:
            self.add_error("period", "Période non autorisée.")

        if period and posting_date and not (period.start_date <= posting_date <= period.end_date):
            self.add_error("posting_date", "La date n'appartient pas à la période sélectionnée.")

        return cleaned


class JournalLineDraftForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs=FORM_SELECT),
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs=FORM_CONTROL),
    )
    debit = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=24,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control amount-input",
                "step": "0.0001",
                "autocomplete": "off",
            }
        ),
    )
    credit = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=24,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control amount-input",
                "step": "0.0001",
                "autocomplete": "off",
            }
        ),
    )
    counterparty = forms.ModelChoiceField(
        queryset=Counterparty.objects.none(),
        required=False,
        widget=forms.Select(attrs=FORM_SELECT),
    )
    cost_center = forms.ModelChoiceField(
        queryset=CostCenter.objects.none(),
        required=False,
        widget=forms.Select(attrs=FORM_SELECT),
    )
    cash_flow_tag = forms.ChoiceField(
        required=False,
        choices=JournalLine.CashFlowTag.choices,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Flux de trésorerie",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["account"].queryset = Account.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")
        self.fields["counterparty"].queryset = Counterparty.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")
        self.fields["cost_center"].queryset = CostCenter.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("DELETE"):
            return cleaned

        debit = cleaned.get("debit") or Decimal("0")
        credit = cleaned.get("credit") or Decimal("0")

        if debit > 0 and credit > 0:
            raise forms.ValidationError(
                "Une ligne ne peut pas être débitée et créditée simultanément."
            )
        if debit <= 0 and credit <= 0:
            raise forms.ValidationError(
                "Renseignez un montant au débit ou au crédit."
            )

        cleaned["debit"] = debit
        cleaned["credit"] = credit
        return cleaned


JournalLineDraftFormSet = formset_factory(
    JournalLineDraftForm,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True,
)


class ReverseEntryForm(OrganizationScopedFormMixin, forms.Form):
    period = forms.ModelChoiceField(
        queryset=AccountingPeriod.objects.none(),
        widget=forms.Select(attrs=FORM_SELECT),
        label="Période d'extourne",
    )
    posting_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Date d'extourne",
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="Motif",
    )

    def __init__(self, *args, organization=None, initial_period=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["period"].queryset = AccountingPeriod.objects.filter(
            fiscal_year__organization=organization,
            status=AccountingPeriod.Status.OPEN,
        ).select_related("fiscal_year").order_by("start_date")

        if initial_period and initial_period.status == AccountingPeriod.Status.OPEN:
            self.fields["period"].initial = initial_period

    def clean(self):
        cleaned = super().clean()
        period = cleaned.get("period")
        posting_date = cleaned.get("posting_date")

        if period and period.fiscal_year.organization_id != self.organization.id:
            self.add_error("period", "Période non autorisée.")

        if period and posting_date and not (period.start_date <= posting_date <= period.end_date):
            self.add_error(
                "posting_date",
                "La date d'extourne doit appartenir à la période sélectionnée.",
            )

        return cleaned
