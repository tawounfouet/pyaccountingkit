from django.db import models

from apps.common.models import TimeStampedUUIDModel


class FinancialStatementConfiguration(TimeStampedUUIDModel):
    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="financial_statement_configuration",
    )
    framework_version = models.ForeignKey(
        "referentials.FrameworkVersion",
        on_delete=models.PROTECT,
        related_name="entity_financial_statement_configurations",
    )
    comparative_enabled = models.BooleanField(default=True)
    cash_account_prefixes = models.JSONField(default=list, blank=True)
    infer_cash_flow_categories = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["organization__name"]

    def __str__(self):
        return f"{self.organization} — {self.framework_version}"



class RegulatoryStatementProfile(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="regulatory_statement_profiles",
    )
    name = models.CharField(max_length=255)
    source_version = models.ForeignKey(
        "referentials.FrameworkVersion",
        on_delete=models.PROTECT,
        related_name="source_regulatory_profiles",
    )
    target_version = models.ForeignKey(
        "referentials.FrameworkVersion",
        on_delete=models.PROTECT,
        related_name="target_regulatory_profiles",
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["organization__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "target_version"],
                name="uniq_org_regulatory_target_version",
            )
        ]

    def __str__(self):
        return (
            f"{self.organization} — {self.name} "
            f"({self.target_version.framework.code} {self.target_version.version})"
        )


class RegulatoryStatementLineMapping(TimeStampedUUIDModel):
    class MappingType(models.TextChoices):
        MANUAL = "MANUAL", "Manuel"
        RULE = "RULE", "Règle"
        SUGGESTED = "SUGGESTED", "Suggestion"

    profile = models.ForeignKey(
        RegulatoryStatementProfile,
        on_delete=models.CASCADE,
        related_name="line_mappings",
    )
    source_line = models.ForeignKey(
        "referentials.StatementLine",
        on_delete=models.PROTECT,
        related_name="regulatory_source_mappings",
    )
    target_line = models.ForeignKey(
        "referentials.StatementLine",
        on_delete=models.PROTECT,
        related_name="regulatory_target_mappings",
    )
    multiplier = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=1,
    )
    mapping_type = models.CharField(
        max_length=20,
        choices=MappingType.choices,
        default=MappingType.MANUAL,
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )
    validated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_regulatory_statement_mappings",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = [
            "source_line__definition__statement_type",
            "source_line__order",
            "source_line__code",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "source_line"],
                name="uniq_regulatory_profile_source_line",
            )
        ]

    def __str__(self):
        return (
            f"{self.profile.name}: {self.source_line.code} "
            f"→ {self.target_line.code}"
        )
