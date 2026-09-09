import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("action", models.CharField(max_length=100)),
                ("entity_type", models.CharField(max_length=100)),
                ("entity_id", models.CharField(max_length=100)),
                ("before", models.JSONField(blank=True, null=True)),
                ("after", models.JSONField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("source_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("request_id", models.CharField(blank=True, max_length=100)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="organizations.organization")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="auditevent", index=models.Index(fields=["organization", "created_at"], name="audit_audit_organiz_d80768_idx")),
        migrations.AddIndex(model_name="auditevent", index=models.Index(fields=["entity_type", "entity_id"], name="audit_audit_entity__5e4c07_idx")),
    ]
