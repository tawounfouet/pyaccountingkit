from django.contrib import admin

from .models import (
    Account,
    ChartOfAccounts,
    CostCenter,
    Counterparty,
    Journal,
    JournalEntry,
    JournalLine,
)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = (
        "entry_number",
        "organization",
        "posting_date",
        "journal",
        "status",
    )
    list_filter = ("status", "journal__journal_type", "organization")
    search_fields = ("entry_number", "description", "reference")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status in {
            JournalEntry.Status.POSTED,
            JournalEntry.Status.REVERSED,
        }:
            return [field.name for field in self.model._meta.fields]
        return []

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status in {
            JournalEntry.Status.POSTED,
            JournalEntry.Status.REVERSED,
        }:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = (
        "entry",
        "line_number",
        "account",
        "debit",
        "credit",
    )

    def has_change_permission(self, request, obj=None):
        if obj and obj.entry.status in {
            JournalEntry.Status.POSTED,
            JournalEntry.Status.REVERSED,
        }:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.entry.status in {
            JournalEntry.Status.POSTED,
            JournalEntry.Status.REVERSED,
        }:
            return False
        return super().has_delete_permission(request, obj)


admin.site.register([
    ChartOfAccounts,
    Account,
    Journal,
    Counterparty,
    CostCenter,
])
