"""Add durable closing runs.

Revision ID: 0005_closing_run
Revises: 0004_execution_trace
Create Date: 2026-10-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_closing_run"
down_revision: str | None = "0004_execution_trace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pyak_closing_run",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("period_id", sa.String(length=128), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("evidence_digest", sa.String(length=64), nullable=False),
        sa.Column("trial_balance_checksum", sa.String(length=64), nullable=False),
        sa.Column("control_runs_hash", sa.String(length=64), nullable=False),
        sa.Column("total_debit", sa.String(length=128), nullable=False),
        sa.Column("total_credit", sa.String(length=128), nullable=False),
        sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["pyak_accounting_period.id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_pyak_closing_run_period_id",
        "pyak_closing_run",
        ["period_id"],
    )
    op.create_index(
        "ix_pyak_closing_run_evidence_digest",
        "pyak_closing_run",
        ["evidence_digest"],
    )
    op.create_index(
        "ix_pyak_closing_run_sealed_at",
        "pyak_closing_run",
        ["sealed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pyak_closing_run_sealed_at",
        table_name="pyak_closing_run",
    )
    op.drop_index(
        "ix_pyak_closing_run_evidence_digest",
        table_name="pyak_closing_run",
    )
    op.drop_index(
        "ix_pyak_closing_run_period_id",
        table_name="pyak_closing_run",
    )
    op.drop_table("pyak_closing_run")
