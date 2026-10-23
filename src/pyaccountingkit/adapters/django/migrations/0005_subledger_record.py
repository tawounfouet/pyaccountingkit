from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pyaccountingkit_django", "0004_accounting_execution_trace"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubledgerRecordModel",
            fields=[
                ("key", models.CharField(max_length=320, primary_key=True, serialize=False)),
                ("kind", models.CharField(db_index=True, max_length=32)),
                ("record_id", models.CharField(db_index=True, max_length=128)),
                ("entity_id", models.CharField(db_index=True, max_length=128)),
                (
                    "subledger_id",
                    models.CharField(blank=True, db_index=True, default="", max_length=128),
                ),
                ("revision", models.PositiveBigIntegerField(default=0)),
                ("payload", models.JSONField(default=dict)),
            ],
            options={
                "db_table": "pyak_subledger_record",
                "ordering": ("kind", "record_id"),
                "indexes": [
                    models.Index(
                        fields=["entity_id", "subledger_id", "kind"],
                        name="ix_pyak_subledger_scope",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("kind", "record_id"),
                        name="uq_pyak_subledger_kind_record",
                    )
                ],
            },
        )
    ]
