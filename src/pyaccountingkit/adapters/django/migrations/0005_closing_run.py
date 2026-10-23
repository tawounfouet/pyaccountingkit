# Generated for PyAccountingKit REM-05 / LOT-31R.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pyaccountingkit_django", "0004_accounting_execution_trace"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClosingRunModel",
            fields=[
                ("id", models.CharField(max_length=128, primary_key=True, serialize=False)),
                ("phase", models.CharField(max_length=16)),
                ("evidence_digest", models.CharField(db_index=True, max_length=64)),
                ("trial_balance_checksum", models.CharField(max_length=64)),
                ("control_runs_hash", models.CharField(max_length=64)),
                ("total_debit", models.CharField(max_length=128)),
                ("total_credit", models.CharField(max_length=128)),
                ("sealed_at", models.DateTimeField(db_index=True)),
                (
                    "period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closing_runs",
                        to="pyaccountingkit_django.accountingperiodmodel",
                    ),
                ),
            ],
            options={
                "db_table": "pyak_closing_run",
                "ordering": ("sealed_at", "id"),
            },
        ),
    ]
