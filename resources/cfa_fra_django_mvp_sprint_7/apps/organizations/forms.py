from django import forms

from .models import FiscalYear, Organization

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "legal_name",
            "registration_number",
            "base_currency",
            "country_code",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "legal_name": forms.TextInput(attrs={"class": "form-control"}),
            "registration_number": forms.TextInput(attrs={"class": "form-control"}),
            "base_currency": forms.TextInput(attrs={"class": "form-control", "maxlength": 3}),
            "country_code": forms.TextInput(attrs={"class": "form-control", "maxlength": 2}),
        }

class FiscalYearForm(forms.ModelForm):
    class Meta:
        model = FiscalYear
        fields = ["name", "start_date", "end_date"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
        return cleaned
