from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel

class ExportJob(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        RUNNING = "RUNNING", "En cours"
        DONE = "DONE", "Terminé"
        FAILED = "FAILED", "Échec"

    class Format(models.TextChoices):
        XLSX = "XLSX", "Excel"
        PDF = "PDF", "PDF"
        CSV = "CSV", "CSV"
        JSON = "JSON", "JSON"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="export_jobs"
    )
    export_type = models.CharField(max_length=100)
    format = models.CharField(
        max_length=20,
        choices=Format.choices,
        default=Format.CSV,
    )
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file = models.FileField(upload_to="exports/%Y/%m/", blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="export_jobs"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    mime_type = models.CharField(max_length=150, blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    snapshot = models.ForeignKey(
        "reporting.ReportSnapshot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="export_jobs",
    )
    regulatory_profile = models.ForeignKey(
        "financial_statements.RegulatoryStatementProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="export_jobs",
    )

    class Meta:
        ordering = ["-created_at"]
