from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel


class FECImport(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploadé"
        PARSED = "PARSED", "Analysé"
        MAPPING = "MAPPING", "Mapping requis"
        READY = "READY", "Prêt à importer"
        IMPORTING = "IMPORTING", "Import en cours"
        IMPORTED = "IMPORTED", "Importé"
        FAILED = "FAILED", "Échec"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="fec_imports",
    )
    fiscal_year = models.ForeignKey(
        "organizations.FiscalYear",
        on_delete=models.PROTECT,
        related_name="fec_imports",
    )
    original_filename = models.CharField(max_length=255)
    original_file = models.FileField(upload_to="fec/%Y/%m/")
    sha256 = models.CharField(max_length=64, db_index=True)
    encoding = models.CharField(max_length=50, default="utf-8")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fec_imports",
    )
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_fec_imports",
    )
    parsed_at = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "fiscal_year", "sha256"],
                name="uniq_fec_import_org_year_hash",
            )
        ]

    @property
    def blocking_error_count(self):
        return self.errors.filter(
            severity=ImportError.Severity.BLOCKING,
            is_resolved=False,
        ).count()

    @property
    def unresolved_account_mapping_count(self):
        return self.mappings.filter(account__isnull=True).count()

    @property
    def unresolved_journal_mapping_count(self):
        return self.journal_mappings.filter(journal__isnull=True).count()

    @property
    def can_import(self):
        return (
            self.status == self.Status.READY
            and self.blocking_error_count == 0
            and self.unresolved_account_mapping_count == 0
            and self.unresolved_journal_mapping_count == 0
        )

    def __str__(self):
        return f"{self.original_filename} — {self.get_status_display()}"


class FECRawLine(TimeStampedUUIDModel):
    import_batch = models.ForeignKey(
        FECImport,
        on_delete=models.CASCADE,
        related_name="raw_lines",
    )
    line_number = models.PositiveIntegerField()

    journal_code = models.CharField(max_length=50, blank=True)
    journal_label = models.CharField(max_length=255, blank=True)

    entry_number = models.CharField(max_length=255, blank=True)
    entry_date = models.DateField(null=True, blank=True)

    account_number = models.CharField(max_length=50, blank=True)
    account_label = models.CharField(max_length=255, blank=True)

    auxiliary_number = models.CharField(max_length=255, blank=True)
    auxiliary_label = models.CharField(max_length=255, blank=True)

    piece_reference = models.CharField(max_length=255, blank=True)
    piece_date = models.DateField(null=True, blank=True)

    entry_label = models.TextField(blank=True)

    debit = models.DecimalField(max_digits=24, decimal_places=4, default=0)
    credit = models.DecimalField(max_digits=24, decimal_places=4, default=0)

    letter = models.CharField(max_length=100, blank=True)
    letter_date = models.DateField(null=True, blank=True)
    validation_date = models.DateField(null=True, blank=True)

    currency_amount = models.DecimalField(max_digits=24, decimal_places=4, default=0)
    currency_code = models.CharField(max_length=10, blank=True)

    row_hash = models.CharField(max_length=64, blank=True, db_index=True)
    normalized_entry_key = models.CharField(max_length=500, blank=True, db_index=True)
    is_valid = models.BooleanField(default=True)

    raw_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["import_batch", "line_number"]
        indexes = [
            models.Index(
                fields=["import_batch", "journal_code", "entry_number"],
                name="fecraw_batch_jrn_entry_idx",
            ),
            models.Index(
                fields=["import_batch", "account_number"],
                name="fecraw_batch_account_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["import_batch", "line_number"],
                name="uniq_fec_raw_import_line",
            )
        ]

    def __str__(self):
        return f"{self.import_batch_id} / ligne {self.line_number}"


class ImportError(TimeStampedUUIDModel):
    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Avertissement"
        ERROR = "ERROR", "Erreur"
        BLOCKING = "BLOCKING", "Bloquant"

    import_batch = models.ForeignKey(
        FECImport,
        on_delete=models.CASCADE,
        related_name="errors",
    )
    raw_line = models.ForeignKey(
        FECRawLine,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="errors",
    )
    code = models.CharField(max_length=100)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["severity", "created_at"]


class ImportMapping(TimeStampedUUIDModel):
    import_batch = models.ForeignKey(
        FECImport,
        on_delete=models.CASCADE,
        related_name="mappings",
    )
    source_account_number = models.CharField(max_length=50)
    source_account_label = models.CharField(max_length=255, blank=True)
    occurrence_count = models.PositiveIntegerField(default=0)

    account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="import_mappings",
    )
    created_automatically = models.BooleanField(default=False)

    class Meta:
        ordering = ["source_account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["import_batch", "source_account_number"],
                name="uniq_import_source_account",
            )
        ]

    def __str__(self):
        return f"{self.source_account_number} -> {self.account or 'Non mappé'}"


class JournalImportMapping(TimeStampedUUIDModel):
    import_batch = models.ForeignKey(
        FECImport,
        on_delete=models.CASCADE,
        related_name="journal_mappings",
    )
    source_journal_code = models.CharField(max_length=50)
    source_journal_label = models.CharField(max_length=255, blank=True)
    occurrence_count = models.PositiveIntegerField(default=0)

    journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fec_import_mappings",
    )
    created_automatically = models.BooleanField(default=False)

    class Meta:
        ordering = ["source_journal_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["import_batch", "source_journal_code"],
                name="uniq_import_source_journal",
            )
        ]

    def __str__(self):
        return f"{self.source_journal_code} -> {self.journal or 'Non mappé'}"
