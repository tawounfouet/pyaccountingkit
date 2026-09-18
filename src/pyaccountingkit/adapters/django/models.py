"""Django/PostgreSQL persistence schema for canonical accounting aggregates."""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q


class JournalModel(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    entity_id = models.CharField(max_length=128, db_index=True)
    code = models.CharField(max_length=64)
    label = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    class Meta:
        app_label = "pyaccountingkit_django"
        db_table = "pyak_journal"
        constraints = [
            models.UniqueConstraint(
                fields=("entity_id", "code"),
                name="uq_pyak_journal_entity_code",
            )
        ]


class AccountingPeriodModel(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    entity_id = models.CharField(max_length=128, db_index=True)
    fiscal_year_id = models.CharField(max_length=128, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=16, db_index=True)

    class Meta:
        app_label = "pyaccountingkit_django"
        db_table = "pyak_accounting_period"
        ordering = ("start_date", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__lte=F("end_date")),
                name="ck_pyak_period_date_order",
            )
        ]


class JournalEntryModel(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    journal = models.ForeignKey(
        JournalModel,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    period = models.ForeignKey(
        AccountingPeriodModel,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    entry_date = models.DateField(db_index=True)
    description = models.TextField()
    status = models.CharField(max_length=16, db_index=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    reversal_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_entries",
    )
    reversed_by = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        app_label = "pyaccountingkit_django"
        db_table = "pyak_journal_entry"
        ordering = ("entry_date", "id")
        indexes = [
            models.Index(fields=("period", "status", "entry_date"), name="ix_pyak_entry_period"),
            models.Index(fields=("journal", "status", "entry_date"), name="ix_pyak_entry_journal"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("reversal_of",),
                condition=Q(reversal_of__isnull=False),
                name="uq_pyak_entry_full_reversal",
            )
        ]


class JournalLineModel(models.Model):
    entry = models.ForeignKey(
        JournalEntryModel,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_number = models.PositiveIntegerField()
    account_id = models.CharField(max_length=128, db_index=True)
    debit_amount = models.DecimalField(max_digits=38, decimal_places=18)
    credit_amount = models.DecimalField(max_digits=38, decimal_places=18)
    currency_code = models.CharField(max_length=3)
    currency_exponent = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        app_label = "pyaccountingkit_django"
        db_table = "pyak_journal_line"
        ordering = ("line_number", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("entry", "line_number"),
                name="uq_pyak_line_entry_number",
            ),
            models.CheckConstraint(
                condition=Q(debit_amount__gte=0) & Q(credit_amount__gte=0),
                name="ck_pyak_line_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    (Q(debit_amount__gt=0) & Q(credit_amount=0))
                    | (Q(credit_amount__gt=0) & Q(debit_amount=0))
                ),
                name="ck_pyak_line_one_sided",
            ),
            models.CheckConstraint(
                condition=Q(currency_exponent__gte=0) & Q(currency_exponent__lte=4),
                name="ck_pyak_line_currency_exp",
            ),
        ]


class AuditEventModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=128, db_index=True)
    entity_id = models.CharField(max_length=128, db_index=True)
    actor_id = models.CharField(max_length=128)
    occurred_at = models.DateTimeField(db_index=True)
    payload = models.JSONField(default=dict)

    class Meta:
        app_label = "pyaccountingkit_django"
        db_table = "pyak_audit_event"
        ordering = ("id",)


class IdempotencyRecordModel(models.Model):
    key = models.CharField(max_length=255, primary_key=True)
    status = models.CharField(max_length=16)

    class Meta:
        app_label = "pyaccountingkit_django"
        db_table = "pyak_idempotency"


class OutboxMessageModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=128, db_index=True)
    entity_id = models.CharField(max_length=128, db_index=True)
    payload = models.JSONField(default=dict)
    idempotency_key = models.CharField(max_length=255, blank=True, default="", db_index=True)

    class Meta:
        app_label = "pyaccountingkit_django"
        db_table = "pyak_outbox"
        ordering = ("id",)


__all__ = [
    "AccountingPeriodModel",
    "AuditEventModel",
    "IdempotencyRecordModel",
    "JournalEntryModel",
    "JournalLineModel",
    "JournalModel",
    "OutboxMessageModel",
]
