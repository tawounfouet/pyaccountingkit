"""Add durable accounting execution traces.

Revision ID: 0004_execution_trace
Revises: 0003_idem_fingerprint
Create Date: 2026-10-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_execution_trace"
down_revision: str | None = "0003_idem_fingerprint"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pyak_accounting_execution_trace",
        sa.Column("trace_id", sa.String(length=128), primary_key=True),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("accounting_date", sa.Date(), nullable=False),
        sa.Column("proposal_checksum", sa.String(length=64), nullable=False),
        sa.Column("resolved_account_ids", sa.JSON(), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=128), nullable=False),
        sa.Column("company_chart_id", sa.String(length=128), nullable=False),
        sa.Column("company_chart_version", sa.String(length=128), nullable=False),
        sa.Column(
            "company_chart_reference_snapshot_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("policy_set_ids", sa.JSON(), nullable=False),
        sa.Column("policy_set_versions", sa.JSON(), nullable=False),
        sa.Column("policy_ids", sa.JSON(), nullable=False),
        sa.Column("policy_versions", sa.JSON(), nullable=False),
        sa.Column("policy_reference_snapshot_ids", sa.JSON(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["pyak_journal_entry.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "journal_entry_id",
            name="uq_pyak_execution_trace_entry",
        ),
    )
    op.create_index(
        "ix_pyak_accounting_execution_trace_entity_id",
        "pyak_accounting_execution_trace",
        ["entity_id"],
    )
    op.create_index(
        "ix_pyak_accounting_execution_trace_accounting_date",
        "pyak_accounting_execution_trace",
        ["accounting_date"],
    )
    op.create_index(
        "ix_pyak_accounting_execution_trace_proposal_checksum",
        "pyak_accounting_execution_trace",
        ["proposal_checksum"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pyak_accounting_execution_trace_proposal_checksum",
        table_name="pyak_accounting_execution_trace",
    )
    op.drop_index(
        "ix_pyak_accounting_execution_trace_accounting_date",
        table_name="pyak_accounting_execution_trace",
    )
    op.drop_index(
        "ix_pyak_accounting_execution_trace_entity_id",
        table_name="pyak_accounting_execution_trace",
    )
    op.drop_table("pyak_accounting_execution_trace")
