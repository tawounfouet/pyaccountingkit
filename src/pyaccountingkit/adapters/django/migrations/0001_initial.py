# Generated for PyAccountingKit LOT-23 / 0.5.0b1.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AccountingPeriodModel",
            fields=[
                ("id", models.CharField(max_length=128, primary_key=True, serialize=False)),
                ("entity_id", models.CharField(db_index=True, max_length=128)),
                ("fiscal_year_id", models.CharField(db_index=True, max_length=128)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(db_index=True, max_length=16)),
            ],
            options={
                "db_table": "pyak_accounting_period",
                "ordering": ("start_date", "id"),
            },
        ),
        migrations.CreateModel(
            name="AuditEventModel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("event_type", models.CharField(db_index=True, max_length=128)),
                ("entity_id", models.CharField(db_index=True, max_length=128)),
                ("actor_id", models.CharField(max_length=128)),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("payload", models.JSONField(default=dict)),
            ],
            options={
                "db_table": "pyak_audit_event",
                "ordering": ("id",),
            },
        ),
        migrations.CreateModel(
            name="IdempotencyRecordModel",
            fields=[
                ("key", models.CharField(max_length=255, primary_key=True, serialize=False)),
                ("status", models.CharField(max_length=16)),
            ],
            options={"db_table": "pyak_idempotency"},
        ),
        migrations.CreateModel(
            name="JournalModel",
            fields=[
                ("id", models.CharField(max_length=128, primary_key=True, serialize=False)),
                ("entity_id", models.CharField(db_index=True, max_length=128)),
                ("code", models.CharField(max_length=64)),
                ("label", models.CharField(max_length=255)),
                ("active", models.BooleanField(default=True)),
            ],
            options={"db_table": "pyak_journal"},
        ),
        migrations.CreateModel(
            name="OutboxMessageModel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("event_type", models.CharField(db_index=True, max_length=128)),
                ("entity_id", models.CharField(db_index=True, max_length=128)),
                ("payload", models.JSONField(default=dict)),
                (
                    "idempotency_key",
                    models.CharField(blank=True, db_index=True, default="", max_length=255),
                ),
            ],
            options={
                "db_table": "pyak_outbox",
                "ordering": ("id",),
            },
        ),
        migrations.CreateModel(
            name="JournalEntryModel",
            fields=[
                ("id", models.CharField(max_length=128, primary_key=True, serialize=False)),
                ("entry_date", models.DateField(db_index=True)),
                ("description", models.TextField()),
                ("status", models.CharField(db_index=True, max_length=16)),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("revision", models.PositiveBigIntegerField(default=0)),
                (
                    "journal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entries",
                        to="pyaccountingkit_django.journalmodel",
                    ),
                ),
                (
                    "period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entries",
                        to="pyaccountingkit_django.accountingperiodmodel",
                    ),
                ),
                (
                    "reversal_of",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reversal_entries",
                        to="pyaccountingkit_django.journalentrymodel",
                    ),
                ),
                (
                    "reversed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="pyaccountingkit_django.journalentrymodel",
                    ),
                ),
            ],
            options={
                "db_table": "pyak_journal_entry",
                "ordering": ("entry_date", "id"),
            },
        ),
        migrations.CreateModel(
            name="JournalLineModel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("line_number", models.PositiveIntegerField()),
                ("account_id", models.CharField(db_index=True, max_length=128)),
                ("debit_amount", models.DecimalField(decimal_places=18, max_digits=38)),
                ("credit_amount", models.DecimalField(decimal_places=18, max_digits=38)),
                ("currency_code", models.CharField(max_length=3)),
                ("currency_exponent", models.PositiveSmallIntegerField()),
                ("label", models.CharField(blank=True, default="", max_length=255)),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="pyaccountingkit_django.journalentrymodel",
                    ),
                ),
            ],
            options={
                "db_table": "pyak_journal_line",
                "ordering": ("line_number", "id"),
            },
        ),
        migrations.AddConstraint(
            model_name="accountingperiodmodel",
            constraint=models.CheckConstraint(
                condition=Q(start_date__lte=F("end_date")),
                name="ck_pyak_period_date_order",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalmodel",
            constraint=models.UniqueConstraint(
                fields=("entity_id", "code"),
                name="uq_pyak_journal_entity_code",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentrymodel",
            index=models.Index(
                fields=["period", "status", "entry_date"],
                name="ix_pyak_entry_period",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentrymodel",
            index=models.Index(
                fields=["journal", "status", "entry_date"],
                name="ix_pyak_entry_journal",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentrymodel",
            constraint=models.UniqueConstraint(
                condition=Q(reversal_of__isnull=False),
                fields=("reversal_of",),
                name="uq_pyak_entry_full_reversal",
            ),
        ),
        migrations.AddConstraint(
            model_name="journallinemodel",
            constraint=models.UniqueConstraint(
                fields=("entry", "line_number"),
                name="uq_pyak_line_entry_number",
            ),
        ),
        migrations.AddConstraint(
            model_name="journallinemodel",
            constraint=models.CheckConstraint(
                condition=Q(debit_amount__gte=0) & Q(credit_amount__gte=0),
                name="ck_pyak_line_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="journallinemodel",
            constraint=models.CheckConstraint(
                condition=(
                    (Q(debit_amount__gt=0) & Q(credit_amount=0))
                    | (Q(credit_amount__gt=0) & Q(debit_amount=0))
                ),
                name="ck_pyak_line_one_sided",
            ),
        ),
        migrations.AddConstraint(
            model_name="journallinemodel",
            constraint=models.CheckConstraint(
                condition=Q(currency_exponent__gte=0) & Q(currency_exponent__lte=4),
                name="ck_pyak_line_currency_exp",
            ),
        ),
    ]
