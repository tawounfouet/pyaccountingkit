from django.contrib import admin

from .models import (
    FinancialStatementConfiguration,
    RegulatoryStatementLineMapping,
    RegulatoryStatementProfile,
)


@admin.register(FinancialStatementConfiguration)
class FinancialStatementConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "framework_version",
        "comparative_enabled",
        "infer_cash_flow_categories",
        "is_active",
    )
    list_filter = (
        "comparative_enabled",
        "infer_cash_flow_categories",
        "is_active",
    )


@admin.register(RegulatoryStatementProfile)
class RegulatoryStatementProfileAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "name",
        "source_version",
        "target_version",
        "is_default",
        "is_active",
    )
    list_filter = (
        "is_default",
        "is_active",
        "target_version__framework",
    )
    search_fields = (
        "organization__name",
        "name",
        "target_version__framework__code",
        "target_version__version",
    )


@admin.register(RegulatoryStatementLineMapping)
class RegulatoryStatementLineMappingAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "source_line",
        "target_line",
        "multiplier",
        "mapping_type",
        "confidence",
    )
    list_filter = (
        "mapping_type",
        "profile__target_version__framework",
    )
    search_fields = (
        "profile__name",
        "source_line__code",
        "source_line__label",
        "target_line__code",
        "target_line__label",
    )
