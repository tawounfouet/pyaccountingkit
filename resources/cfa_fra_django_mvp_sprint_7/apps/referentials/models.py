from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel

class AccountingFramework(TimeStampedUUIDModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.name}"

class FrameworkVersion(TimeStampedUUIDModel):
    framework = models.ForeignKey(
        AccountingFramework, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.CharField(max_length=50)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    source_url = models.URLField(blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "version"],
                name="uniq_framework_version",
            )
        ]

    def __str__(self):
        return f"{self.framework.code} — {self.version}"

class FrameworkAccount(TimeStampedUUIDModel):
    version = models.ForeignKey(
        FrameworkVersion, on_delete=models.CASCADE, related_name="accounts"
    )
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=500)
    name_en = models.CharField(max_length=500, blank=True)
    account_type = models.CharField(max_length=50, blank=True)
    normal_balance = models.CharField(max_length=20, blank=True)
    current_noncurrent = models.CharField(max_length=30, blank=True)
    statement = models.CharField(max_length=100, blank=True)
    statement_section = models.CharField(max_length=150, blank=True)
    standard_reference = models.CharField(max_length=255, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["version", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "code"],
                name="uniq_framework_account_code",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"

class StatementDefinition(TimeStampedUUIDModel):
    class StatementType(models.TextChoices):
        BALANCE_SHEET = "BALANCE_SHEET", "Bilan"
        INCOME_STATEMENT = "INCOME_STATEMENT", "Compte de résultat"
        CASH_FLOW = "CASH_FLOW", "Flux de trésorerie"
        EQUITY_CHANGES = "EQUITY_CHANGES", "Variation des capitaux propres"

    version = models.ForeignKey(
        FrameworkVersion, on_delete=models.CASCADE, related_name="statement_definitions"
    )
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    statement_type = models.CharField(max_length=50, choices=StatementType.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["version", "code"],
                name="uniq_statement_definition_code",
            )
        ]

    def __str__(self):
        return f"{self.get_statement_type_display()} — {self.name}"

class StatementLine(TimeStampedUUIDModel):
    definition = models.ForeignKey(
        StatementDefinition, on_delete=models.CASCADE, related_name="lines"
    )
    code = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    order = models.PositiveIntegerField(default=0)
    sign = models.SmallIntegerField(default=1)
    is_total = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    standard_reference = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["definition", "order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "code"],
                name="uniq_statement_line_code",
            )
        ]

    def __str__(self):
        return f"{self.definition.get_statement_type_display()} — {self.code} — {self.label}"

class AccountMapping(TimeStampedUUIDModel):
    class MappingType(models.TextChoices):
        MANUAL = "MANUAL", "Manuel"
        RULE = "RULE", "Règle"
        SUGGESTED = "SUGGESTED", "Suggestion"

    account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.CASCADE,
        related_name="framework_mappings",
    )
    framework_account = models.ForeignKey(
        FrameworkAccount,
        on_delete=models.PROTECT,
        related_name="entity_account_mappings",
    )
    mapping_type = models.CharField(
        max_length=20, choices=MappingType.choices, default=MappingType.MANUAL
    )
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_account_mappings",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "framework_account"],
                name="uniq_account_framework_mapping",
            )
        ]



class StatementAccountMapping(TimeStampedUUIDModel):
    class MappingType(models.TextChoices):
        MANUAL = "MANUAL", "Manuel"
        RULE = "RULE", "Règle"
        SUGGESTED = "SUGGESTED", "Suggestion"

    account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.CASCADE,
        related_name="statement_mappings",
    )
    statement_line = models.ForeignKey(
        StatementLine,
        on_delete=models.PROTECT,
        related_name="entity_account_mappings",
    )
    balance_multiplier = models.SmallIntegerField(default=1)
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
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_statement_account_mappings",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["account__code", "statement_line__definition__statement_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "statement_line"],
                name="uniq_account_statement_line_mapping",
            )
        ]

    def __str__(self):
        return f"{self.account} -> {self.statement_line.code}"
