"""Create the canonical PyAccountingKit PostgreSQL schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pyak_journal",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_id", "code", name="uq_pyak_journal_entity_code"),
    )
    op.create_index("ix_pyak_journal_entity_id", "pyak_journal", ["entity_id"], unique=False)

    op.create_table(
        "pyak_accounting_period",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("fiscal_year_id", sa.String(length=128), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint("start_date <= end_date", name="ck_pyak_period_date_order"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pyak_accounting_period_entity_id",
        "pyak_accounting_period",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_accounting_period_fiscal_year_id",
        "pyak_accounting_period",
        ["fiscal_year_id"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_accounting_period_status",
        "pyak_accounting_period",
        ["status"],
        unique=False,
    )

    op.create_table(
        "pyak_journal_entry",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("journal_id", sa.String(length=128), nullable=False),
        sa.Column("period_id", sa.String(length=128), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_of_id", sa.String(length=128), nullable=True),
        sa.Column("reversed_by_id", sa.String(length=128), nullable=True),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["journal_id"], ["pyak_journal.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["pyak_accounting_period.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_of_id"],
            ["pyak_journal_entry.id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["reversed_by_id"],
            ["pyak_journal_entry.id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pyak_journal_entry_entry_date",
        "pyak_journal_entry",
        ["entry_date"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_journal_entry_status",
        "pyak_journal_entry",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_entry_period",
        "pyak_journal_entry",
        ["period_id", "status", "entry_date"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_entry_journal",
        "pyak_journal_entry",
        ["journal_id", "status", "entry_date"],
        unique=False,
    )
    op.create_index(
        "uq_pyak_entry_full_reversal",
        "pyak_journal_entry",
        ["reversal_of_id"],
        unique=True,
        postgresql_where=sa.text("reversal_of_id IS NOT NULL"),
    )

    op.create_table(
        "pyak_journal_line",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entry_id", sa.String(length=128), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("debit_amount", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("credit_amount", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("currency_exponent", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "debit_amount >= 0 AND credit_amount >= 0",
            name="ck_pyak_line_nonnegative",
        ),
        sa.CheckConstraint(
            "((debit_amount > 0 AND credit_amount = 0) OR "
            "(credit_amount > 0 AND debit_amount = 0))",
            name="ck_pyak_line_one_sided",
        ),
        sa.CheckConstraint(
            "currency_exponent >= 0 AND currency_exponent <= 4",
            name="ck_pyak_line_currency_exp",
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["pyak_journal_entry.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "line_number", name="uq_pyak_line_entry_number"),
    )
    op.create_index(
        "ix_pyak_journal_line_entry_id",
        "pyak_journal_line",
        ["entry_id"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_journal_line_account_id",
        "pyak_journal_line",
        ["account_id"],
        unique=False,
    )

    op.create_table(
        "pyak_audit_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pyak_audit_event_event_type", "pyak_audit_event", ["event_type"])
    op.create_index("ix_pyak_audit_event_entity_id", "pyak_audit_event", ["entity_id"])
    op.create_index("ix_pyak_audit_event_occurred_at", "pyak_audit_event", ["occurred_at"])

    op.create_table(
        "pyak_idempotency",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "pyak_outbox",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pyak_outbox_event_type", "pyak_outbox", ["event_type"])
    op.create_index("ix_pyak_outbox_entity_id", "pyak_outbox", ["entity_id"])
    op.create_index(
        "ix_pyak_outbox_idempotency_key",
        "pyak_outbox",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_table("pyak_outbox")
    op.drop_table("pyak_idempotency")
    op.drop_table("pyak_audit_event")
    op.drop_table("pyak_journal_line")
    op.drop_table("pyak_journal_entry")
    op.drop_table("pyak_accounting_period")
    op.drop_table("pyak_journal")
