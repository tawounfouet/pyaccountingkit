# Generated for PyAccountingKit REM-04 / A03.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pyaccountingkit_django", "0003_idempotency_payload_fingerprint"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountingExecutionTraceModel",
            fields=[
                (
                    "trace_id",
                    models.CharField(max_length=128, primary_key=True, serialize=False),
                ),
                ("entity_id", models.CharField(db_index=True, max_length=128)),
                ("accounting_date", models.DateField(db_index=True)),
                ("proposal_checksum", models.CharField(db_index=True, max_length=64)),
                ("resolved_account_ids", models.JSONField(default=list)),
                ("company_chart_id", models.CharField(max_length=128)),
                ("company_chart_version", models.CharField(max_length=128)),
                ("company_chart_reference_snapshot_id", models.CharField(max_length=128)),
                ("policy_set_ids", models.JSONField(default=list)),
                ("policy_set_versions", models.JSONField(default=list)),
                ("policy_ids", models.JSONField(default=list)),
                ("policy_versions", models.JSONField(default=list)),
                ("policy_reference_snapshot_ids", models.JSONField(default=list)),
                ("source_reference", models.TextField(blank=True, default="")),
                (
                    "journal_entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="pyaccountingkit_django.journalentrymodel",
                    ),
                ),
            ],
            options={
                "db_table": "pyak_accounting_execution_trace",
                "ordering": ("accounting_date", "trace_id"),
            },
        ),
    ]
