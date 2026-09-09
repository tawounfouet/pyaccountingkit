import uuid
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [("organizations", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="DashboardSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("as_of_date", models.DateField()),
                ("metrics", models.JSONField(default=dict)),
                ("charts", models.JSONField(blank=True, default=dict)),
                ("fiscal_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="dashboard_snapshots", to="organizations.fiscalyear")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dashboard_snapshots", to="organizations.organization")),
            ],
        ),
    ]
