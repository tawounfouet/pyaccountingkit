import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("imports", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Scenario",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("is_reference_case", models.BooleanField(default=False)),
                ("expected_results", models.JSONField(blank=True, default=dict)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="scenarios", to=settings.AUTH_USER_MODEL)),
                ("fiscal_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="scenarios", to="organizations.fiscalyear")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scenarios", to="organizations.organization")),
                ("source_import", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scenarios", to="imports.fecimport")),
            ],
        ),
        migrations.CreateModel(
            name="ScenarioVariable",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(max_length=100)),
                ("value", models.JSONField()),
                ("description", models.TextField(blank=True)),
                ("scenario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variables", to="scenarios.scenario")),
            ],
        ),
        migrations.AddConstraint(model_name="scenariovariable", constraint=models.UniqueConstraint(fields=("scenario", "key"), name="uniq_scenario_variable_key")),
    ]
