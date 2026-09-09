from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedUUIDModel

class AuditEvent(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]
