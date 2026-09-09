from django import forms

from apps.accounting.models import Account, Journal, JournalEntry
from apps.organizations.models import FiscalYear

from .types import TrialBalanceVariant


FORM_CONTROL = {"class": "form-control"}
FORM_SELECT = {"class": "form-select"}


class OrganizationReportForm(forms.Form):
    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization


class JournalFilterForm(OrganizationReportForm):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalYear.objects.none(),
        required=True,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Exercice",
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Du",
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Au",
    )
    journal = forms.ModelChoiceField(
        queryset=Journal.objects.none(),
        required=False,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Journal",
    )
    entry_type = forms.ChoiceField(
        required=False,
        choices=[("", "Tous les types")] + list(JournalEntry.EntryType.choices),
        widget=forms.Select(attrs=FORM_SELECT),
        label="Type d'écriture",
    )
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "N° écriture, référence, libellé, compte",
            }
        ),
        label="Recherche",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["fiscal_year"].queryset = FiscalYear.objects.filter(
            organization=organization,
        ).order_by("-start_date")
        self.fields["journal"].queryset = Journal.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")

        if not self.is_bound:
            fiscal_year = self.fields["fiscal_year"].queryset.first()
            if fiscal_year:
                self.initial["fiscal_year"] = fiscal_year
                self.initial["start_date"] = fiscal_year.start_date
                self.initial["end_date"] = fiscal_year.end_date

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")

        if fiscal_year:
            if start_date and not (fiscal_year.start_date <= start_date <= fiscal_year.end_date):
                self.add_error("start_date", "Date hors exercice.")
            if end_date and not (fiscal_year.start_date <= end_date <= fiscal_year.end_date):
                self.add_error("end_date", "Date hors exercice.")

        return cleaned


class GeneralLedgerFilterForm(OrganizationReportForm):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalYear.objects.none(),
        required=True,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Exercice",
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        required=True,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Compte",
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Du",
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Au",
    )
    variant = forms.ChoiceField(
        choices=TrialBalanceVariant.choices,
        initial=TrialBalanceVariant.ADJUSTED,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Périmètre",
    )
    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["fiscal_year"].queryset = FiscalYear.objects.filter(
            organization=organization,
        ).order_by("-start_date")
        self.fields["account"].queryset = Account.objects.filter(
            organization=organization,
            is_active=True,
        ).select_related("chart").order_by("code")

        if not self.is_bound:
            fiscal_year = self.fields["fiscal_year"].queryset.first()
            account = self.fields["account"].queryset.first()
            if fiscal_year:
                self.initial["fiscal_year"] = fiscal_year
                self.initial["start_date"] = fiscal_year.start_date
                self.initial["end_date"] = fiscal_year.end_date
            if account:
                self.initial["account"] = account

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        account = cleaned.get("account")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")

        if fiscal_year:
            if start_date and not (fiscal_year.start_date <= start_date <= fiscal_year.end_date):
                self.add_error("start_date", "Date hors exercice.")
            if end_date and not (fiscal_year.start_date <= end_date <= fiscal_year.end_date):
                self.add_error("end_date", "Date hors exercice.")

        if account and account.organization_id != self.organization.id:
            self.add_error("account", "Compte non autorisé.")

        return cleaned


class TrialBalanceFilterForm(OrganizationReportForm):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalYear.objects.none(),
        required=True,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Exercice",
    )
    as_of_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Au",
    )
    variant = forms.ChoiceField(
        choices=TrialBalanceVariant.choices,
        initial=TrialBalanceVariant.ADJUSTED,
        widget=forms.Select(attrs=FORM_SELECT),
        label="Type de balance",
    )
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Code ou libellé du compte",
            }
        ),
        label="Recherche",
    )
    include_zero = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Afficher les comptes à solde nul",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        self.fields["fiscal_year"].queryset = FiscalYear.objects.filter(
            organization=organization,
        ).order_by("-start_date")

        if not self.is_bound:
            fiscal_year = self.fields["fiscal_year"].queryset.first()
            if fiscal_year:
                self.initial["fiscal_year"] = fiscal_year
                self.initial["as_of_date"] = fiscal_year.end_date

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")
        as_of_date = cleaned.get("as_of_date")

        if fiscal_year and as_of_date:
            if not (fiscal_year.start_date <= as_of_date <= fiscal_year.end_date):
                self.add_error("as_of_date", "Date hors exercice.")

        return cleaned
