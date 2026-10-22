"""Add idempotency payload fingerprint.

Revision ID: 0003_idempotency_payload_fingerprint
Revises: 0002_entry_type
Create Date: 2026-10-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_idempotency_payload_fingerprint"
down_revision: str | None = "0002_entry_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pyak_idempotency",
        sa.Column(
            "payload_fingerprint",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("pyak_idempotency", "payload_fingerprint")
