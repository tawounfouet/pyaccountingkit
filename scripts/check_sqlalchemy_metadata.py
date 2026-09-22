#!/usr/bin/env python3
"""Compare a migrated PostgreSQL database with SQLAlchemy Declarative metadata."""

from __future__ import annotations

import os
import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from pyaccountingkit.adapters.sqlalchemy.tables import Base


def main() -> int:
    database_url = os.environ.get("PYAK_SQLALCHEMY_DATABASE_URL")
    if not database_url:
        print("PYAK_SQLALCHEMY_DATABASE_URL is required", file=sys.stderr)
        return 2

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={
                "compare_type": True,
                "compare_server_default": False,
            },
        )
        differences = compare_metadata(context, Base.metadata)

    if differences:
        print("SQLAlchemy metadata coherence: FAIL", file=sys.stderr)
        for difference in differences:
            print(f"- {difference!r}", file=sys.stderr)
        return 1

    print("SQLAlchemy metadata coherence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
