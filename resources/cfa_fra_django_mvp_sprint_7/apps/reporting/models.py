from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel

class ReportSnapshot(TimeStampedUUIDModel):
    class ReportType(models.TextChoices):
        JOURNAL = "JOURNAL", "Journal"
        GENERAL_LEDGER = "GENERAL_LEDGER", "Grand livre"
        TRIAL_BALANCE = "TRIAL_BALANCE", "Balance"
        INCOME_STATEMENT = "INCOME_STATEMENT", "Compte de résultat"
        BALANCE_SHEET = "BALANCE_SHEET", "Bilan"
        CASH_FLOW = "CASH_FLOW", "Flux de trésorerie"
        REGULATORY_PACKAGE = "REGULATORY_PACKAGE", "Package réglementaire"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="report_snapshots"
    )
    fiscal_year = models.ForeignKey(
        "organizations.FiscalYear", on_delete=models.PROTECT, related_name="report_snapshots"
    )
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    as_of_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="generated_report_snapshots",
    )
