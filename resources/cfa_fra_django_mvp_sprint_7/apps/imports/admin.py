from django.contrib import admin

from .models import (
    FECImport,
    FECRawLine,
    ImportError,
    ImportMapping,
    JournalImportMapping,
)


@admin.register(FECImport)
class FECImportAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "organization",
        "fiscal_year",
        "status",
        "created_at",
        "imported_at",
    )
    list_filter = ("status", "organization", "fiscal_year")
    search_fields = ("original_filename", "sha256")


@admin.register(FECRawLine)
class FECRawLineAdmin(admin.ModelAdmin):
    list_display = (
        "import_batch",
        "line_number",
        "journal_code",
        "entry_number",
        "account_number",
        "debit",
        "credit",
        "is_valid",
    )
    list_filter = ("is_valid", "journal_code")
    search_fields = (
        "entry_number",
        "account_number",
        "account_label",
        "piece_reference",
    )


@admin.register(ImportError)
class ImportErrorAdmin(admin.ModelAdmin):
    list_display = (
        "import_batch",
        "code",
        "severity",
        "raw_line",
        "is_resolved",
    )
    list_filter = ("severity", "is_resolved", "code")


@admin.register(ImportMapping)
class ImportMappingAdmin(admin.ModelAdmin):
    list_display = (
        "import_batch",
        "source_account_number",
        "account",
        "occurrence_count",
        "created_automatically",
    )


@admin.register(JournalImportMapping)
class JournalImportMappingAdmin(admin.ModelAdmin):
    list_display = (
        "import_batch",
        "source_journal_code",
        "journal",
        "occurrence_count",
        "created_automatically",
    )
