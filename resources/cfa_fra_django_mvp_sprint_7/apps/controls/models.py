from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel

class AccountingControl(TimeStampedUUIDModel):
    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Avertissement"
        ERROR = "ERROR", "Erreur"
        BLOCKING = "BLOCKING", "Bloquant"

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    is_active = models.BooleanField(default=True)

class ControlRun(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="control_runs"
    )
    fiscal_year = models.ForeignKey(
        "organizations.FiscalYear", on_delete=models.PROTECT, related_name="control_runs"
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="control_runs"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    parameters = models.JSONField(default=dict, blank=True)

class ControlResult(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        OK = "OK", "OK"
        WARNING = "WARNING", "Avertissement"
        ERROR = "ERROR", "Erreur"

    run = models.ForeignKey(ControlRun, on_delete=models.CASCADE, related_name="results")
    control = models.ForeignKey(
        AccountingControl, on_delete=models.PROTECT, related_name="results"
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    expected_value = models.JSONField(null=True, blank=True)
    actual_value = models.JSONField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
