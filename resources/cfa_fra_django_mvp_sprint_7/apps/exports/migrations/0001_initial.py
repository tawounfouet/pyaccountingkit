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
            name="ExportJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("export_type", models.CharField(max_length=100)),
                ("format", models.CharField(default="CSV", max_length=20)),
                ("parameters", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("PENDING", "En attente"), ("RUNNING", "En cours"), ("DONE", "Terminé"), ("FAILED", "Échec")], default="PENDING", max_length=20)),
                ("file", models.FileField(blank=True, upload_to="exports/%Y/%m/")),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="export_jobs", to="organizations.organization")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="export_jobs", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
