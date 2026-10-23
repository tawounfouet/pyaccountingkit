"""Add generic persistent subledger record table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0006_subledger_record"
down_revision: str | None = "0005_closing_run"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "pyak_subledger_record",
        sa.Column("key", sa.String(length=320), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("record_id", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("subledger_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
        sa.UniqueConstraint("kind", "record_id", name="uq_pyak_subledger_kind_record"),
    )
    op.create_index(
        "ix_pyak_subledger_record_kind",
        "pyak_subledger_record",
        ["kind"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_subledger_record_record_id",
        "pyak_subledger_record",
        ["record_id"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_subledger_record_entity_id",
        "pyak_subledger_record",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_subledger_record_subledger_id",
        "pyak_subledger_record",
        ["subledger_id"],
        unique=False,
    )
    op.create_index(
        "ix_pyak_subledger_scope",
        "pyak_subledger_record",
        ["entity_id", "subledger_id", "kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pyak_subledger_scope", table_name="pyak_subledger_record")
    op.drop_index("ix_pyak_subledger_record_subledger_id", table_name="pyak_subledger_record")
    op.drop_index("ix_pyak_subledger_record_entity_id", table_name="pyak_subledger_record")
    op.drop_index("ix_pyak_subledger_record_record_id", table_name="pyak_subledger_record")
    op.drop_index("ix_pyak_subledger_record_kind", table_name="pyak_subledger_record")
    op.drop_table("pyak_subledger_record")
