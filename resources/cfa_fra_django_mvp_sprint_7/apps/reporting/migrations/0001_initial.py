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
            name="ReportSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("report_type", models.CharField(choices=[("JOURNAL", "Journal"), ("GENERAL_LEDGER", "Grand livre"), ("TRIAL_BALANCE", "Balance"), ("INCOME_STATEMENT", "Compte de résultat"), ("BALANCE_SHEET", "Bilan"), ("CASH_FLOW", "Flux de trésorerie")], max_length=30)),
                ("as_of_date", models.DateField(blank=True, null=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("parameters", models.JSONField(blank=True, default=dict)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("fiscal_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="report_snapshots", to="organizations.fiscalyear")),
                ("generated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="generated_report_snapshots", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="report_snapshots", to="organizations.organization")),
            ],
        ),
    ]
