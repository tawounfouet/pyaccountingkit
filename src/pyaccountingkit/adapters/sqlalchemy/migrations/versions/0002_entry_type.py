"""Add canonical journal entry type.

Revision ID: 0002_entry_type
Revises: 0001_initial
Create Date: 2026-09-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_entry_type"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pyak_journal_entry",
        sa.Column(
            "entry_type",
            sa.String(length=16),
            nullable=False,
            server_default="NORMAL",
        ),
    )
    op.create_index(
        "ix_pyak_journal_entry_entry_type",
        "pyak_journal_entry",
        ["entry_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pyak_journal_entry_entry_type",
        table_name="pyak_journal_entry",
    )
    op.drop_column("pyak_journal_entry", "entry_type")
