from django import forms

from apps.accounting.models import Account, Journal
from apps.organizations.models import FiscalYear

from .models import ImportMapping, JournalImportMapping


class FECUploadForm(forms.Form):
    fiscal_year = forms.ModelChoiceField(
        queryset=FiscalYear.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Exercice comptable",
    )
    file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".txt,.tsv,text/plain,text/tab-separated-values",
            }
        ),
        label="Fichier FEC",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["fiscal_year"].queryset = FiscalYear.objects.filter(
            organization=organization,
        ).order_by("-start_date")

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        name = uploaded_file.name.lower()

        if not name.endswith((".txt", ".tsv")):
            raise forms.ValidationError("Le FEC doit être un fichier .txt ou .tsv.")

        max_size = 50 * 1024 * 1024
        if uploaded_file.size > max_size:
            raise forms.ValidationError("Le FEC dépasse la taille maximale de 50 Mo.")

        return uploaded_file


class AccountImportMappingForm(forms.ModelForm):
    class Meta:
        model = ImportMapping
        fields = ["account"]
        widgets = {
            "account": forms.Select(attrs={"class": "form-select form-select-sm"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(
            organization=organization,
            is_active=True,
        ).select_related("chart").order_by("code")
        self.fields["account"].required = False


class JournalImportMappingForm(forms.ModelForm):
    class Meta:
        model = JournalImportMapping
        fields = ["journal"]
        widgets = {
            "journal": forms.Select(attrs={"class": "form-select form-select-sm"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["journal"].queryset = Journal.objects.filter(
            organization=organization,
            is_active=True,
        ).order_by("code")
        self.fields["journal"].required = False
