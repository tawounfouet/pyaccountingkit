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
            name="AccountingControl",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("severity", models.CharField(choices=[("INFO", "Information"), ("WARNING", "Avertissement"), ("ERROR", "Erreur"), ("BLOCKING", "Bloquant")], max_length=20)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="ControlRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("parameters", models.JSONField(blank=True, default=dict)),
                ("fiscal_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="control_runs", to="organizations.fiscalyear")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="control_runs", to="organizations.organization")),
                ("started_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="control_runs", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ControlResult",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("OK", "OK"), ("WARNING", "Avertissement"), ("ERROR", "Erreur")], max_length=20)),
                ("expected_value", models.JSONField(blank=True, null=True)),
                ("actual_value", models.JSONField(blank=True, null=True)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("control", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="results", to="controls.accountingcontrol")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="controls.controlrun")),
            ],
        ),
    ]
