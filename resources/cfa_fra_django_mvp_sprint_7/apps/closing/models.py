from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel

class ClosingRun(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        VALIDATED = "VALIDATED", "Validée"
        POSTED = "POSTED", "Postée"
        FAILED = "FAILED", "Échec"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="closing_runs"
    )
    fiscal_year = models.ForeignKey(
        "organizations.FiscalYear", on_delete=models.PROTECT, related_name="closing_runs"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="closing_runs"
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

class ClosingEntryLink(TimeStampedUUIDModel):
    closing_run = models.ForeignKey(
        ClosingRun, on_delete=models.CASCADE, related_name="entry_links"
    )
    entry = models.ForeignKey(
        "accounting.JournalEntry", on_delete=models.PROTECT, related_name="closing_links"
    )
    role = models.CharField(max_length=50)
