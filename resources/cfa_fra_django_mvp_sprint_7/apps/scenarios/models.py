from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel

class Scenario(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="scenarios"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    fiscal_year = models.ForeignKey(
        "organizations.FiscalYear", on_delete=models.PROTECT, related_name="scenarios"
    )
    source_import = models.ForeignKey(
        "imports.FECImport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenarios",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="scenarios"
    )
    is_reference_case = models.BooleanField(default=False)
    expected_results = models.JSONField(default=dict, blank=True)

class ScenarioVariable(TimeStampedUUIDModel):
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="variables"
    )
    key = models.CharField(max_length=100)
    value = models.JSONField()
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "key"],
                name="uniq_scenario_variable_key",
            )
        ]
