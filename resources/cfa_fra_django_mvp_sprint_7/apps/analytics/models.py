from django.db import models

from apps.common.models import TimeStampedUUIDModel

class DashboardSnapshot(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="dashboard_snapshots"
    )
    fiscal_year = models.ForeignKey(
        "organizations.FiscalYear", on_delete=models.PROTECT, related_name="dashboard_snapshots"
    )
    as_of_date = models.DateField()
    metrics = models.JSONField(default=dict)
    charts = models.JSONField(default=dict, blank=True)
