from django.contrib import admin

from .models import ExportJob


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "organization",
        "export_type",
        "format",
        "status",
        "regulatory_profile",
        "completed_at",
    )
    list_filter = (
        "status",
        "format",
        "export_type",
        "organization",
    )
    search_fields = (
        "content_sha256",
        "regulatory_profile__name",
        "organization__name",
    )
    readonly_fields = (
        "content_sha256",
        "mime_type",
        "completed_at",
    )
