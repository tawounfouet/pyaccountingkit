from django import forms

from apps.organizations.models import FiscalYear
from apps.referentials.models import FrameworkVersion, StatementDefinition, StatementLine


FORM_CONTROL = {"class": "form-control"}
FORM_SELECT = {"class": "form-select"}


class FinancialStatementPeriodForm(forms.Form):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalYear.objects.none(),
        widget=forms.Select(attrs=FORM_SELECT),
        label="Exercice",
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Date d'arrêté",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["fiscal_year"].queryset = FiscalYear.objects.filter(
            organization=organization,
        ).order_by("-start_date")

        if not self.is_bound:
            fiscal_year = self.fields["fiscal_year"].queryset.first()
            if fiscal_year:
                self.initial["fiscal_year"] = fiscal_year
                self.initial["end_date"] = fiscal_year.end_date

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")
        end_date = cleaned.get("end_date")

        if fiscal_year and end_date:
            if not (
                fiscal_year.start_date
                <= end_date
                <= fiscal_year.end_date
            ):
                self.add_error("end_date", "Date hors exercice.")

        return cleaned


class FinancialStatementConfigurationForm(forms.Form):
    comparative_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Afficher les comparatifs N-1",
    )
    infer_cash_flow_categories = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Inférer les catégories de flux non taguées",
    )
    cash_account_prefixes = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "5",
            }
        ),
        label="Préfixes des comptes de trésorerie",
        help_text="Séparer plusieurs préfixes par des virgules, par ex. 52,57.",
    )

    def __init__(self, *args, configuration=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.configuration = configuration
        if configuration and not self.is_bound:
            self.initial.update(
                {
                    "comparative_enabled": configuration.comparative_enabled,
                    "infer_cash_flow_categories": configuration.infer_cash_flow_categories,
                    "cash_account_prefixes": ",".join(
                        configuration.cash_account_prefixes or ["5"]
                    ),
                }
            )

    def clean_cash_account_prefixes(self):
        raw = self.cleaned_data["cash_account_prefixes"]
        prefixes = [
            token.strip()
            for token in raw.split(",")
            if token.strip()
        ]
        if not prefixes:
            raise forms.ValidationError(
                "Renseignez au moins un préfixe de trésorerie."
            )
        if any(len(prefix) > 10 for prefix in prefixes):
            raise forms.ValidationError("Préfixe de compte trop long.")
        return prefixes


class StatementAccountMappingForm(forms.Form):
    statement_line = forms.ModelChoiceField(
        queryset=StatementLine.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
        label="Rubrique",
        empty_label="— Non mappé —",
    )

    def __init__(
        self,
        *args,
        framework_version=None,
        initial_line=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["statement_line"].queryset = (
            StatementLine.objects.filter(
                definition__version=framework_version,
                definition__statement_type__in=[
                    StatementDefinition.StatementType.INCOME_STATEMENT,
                    StatementDefinition.StatementType.BALANCE_SHEET,
                ],
                is_total=False,
            ).exclude(code="BS_CURRENT_RESULT")
            .select_related("definition")
            .order_by(
                "definition__statement_type",
                "order",
                "code",
            )
        )
        if initial_line and not self.is_bound:
            self.initial["statement_line"] = initial_line



class RegulatoryProfileForm(forms.Form):
    target_version = forms.ModelChoiceField(
        queryset=FrameworkVersion.objects.none(),
        widget=forms.Select(attrs=FORM_SELECT),
        label="Référentiel / version cible",
    )
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ex. SYSCOHADA 2017",
            }
        ),
        label="Nom du profil",
    )

    def __init__(self, *args, source_version=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_version"].queryset = (
            FrameworkVersion.objects.filter(
                framework__is_active=True,
                statement_definitions__isnull=False,
            )
            .exclude(pk=getattr(source_version, "pk", None))
            .select_related("framework")
            .distinct()
            .order_by("framework__code", "-is_current", "-version")
        )


class RegulatoryPeriodForm(forms.Form):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalYear.objects.none(),
        widget=forms.Select(attrs=FORM_SELECT),
        label="Exercice",
    )
    end_date = forms.DateField(
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date"}
        ),
        label="Date d'arrêté",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fiscal_year"].queryset = FiscalYear.objects.filter(
            organization=organization,
        ).order_by("-start_date")

        if not self.is_bound:
            fiscal_year = self.fields["fiscal_year"].queryset.first()
            if fiscal_year:
                self.initial["fiscal_year"] = fiscal_year
                self.initial["end_date"] = fiscal_year.end_date

    def clean(self):
        cleaned = super().clean()
        fiscal_year = cleaned.get("fiscal_year")
        end_date = cleaned.get("end_date")
        if fiscal_year and end_date:
            if not (
                fiscal_year.start_date
                <= end_date
                <= fiscal_year.end_date
            ):
                self.add_error("end_date", "Date hors exercice.")
        return cleaned


class RegulatoryMappingForm(forms.Form):
    target_line = forms.ModelChoiceField(
        queryset=StatementLine.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm"}
        ),
        label="Ligne réglementaire",
        empty_label="— Non mappé —",
    )
    multiplier = forms.DecimalField(
        max_digits=12,
        decimal_places=6,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm",
                "step": "0.000001",
            }
        ),
        label="Multiplicateur",
    )

    def __init__(
        self,
        *args,
        target_version=None,
        statement_type=None,
        initial_mapping=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["target_line"].queryset = (
            StatementLine.objects.filter(
                definition__version=target_version,
                definition__statement_type=statement_type,
                is_total=False,
            )
            .select_related("definition")
            .order_by("order", "code")
        )
        if initial_mapping and not self.is_bound:
            self.initial["target_line"] = initial_mapping.target_line
            self.initial["multiplier"] = initial_mapping.multiplier


class RegulatoryExportForm(RegulatoryPeriodForm):
    export_format = forms.ChoiceField(
        choices=[
            ("XLSX", "Excel (.xlsx)"),
            ("PDF", "PDF"),
            ("CSV", "CSV"),
            ("JSON", "JSON"),
        ],
        initial="XLSX",
        widget=forms.Select(attrs=FORM_SELECT),
        label="Format",
    )
