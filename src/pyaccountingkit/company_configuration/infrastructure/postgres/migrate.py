"""Small, checksum-verified, transactional migration entrypoint for L02.

Requires an explicitly supplied *administrator* DSN. Never applies migrations
from application startup; migration ownership remains a deployment decision.
"""

import hashlib
import os
from importlib import resources

import psycopg

MIGRATION_PACKAGE = "pyaccountingkit.company_configuration.infrastructure.postgres.migrations"


def apply_migrations(admin_dsn: str) -> list[str]:
    """Apply only missing numbered scripts; reject checksum drift, atomically."""
    if not admin_dsn or not admin_dsn.strip():
        raise ValueError("An explicit administrator DSN is required")
    applied = []
    with psycopg.connect(admin_dsn) as connection:
        with connection.transaction():
            connection.execute("SELECT pg_advisory_xact_lock(hashtext('cc:migrations'))")
            connection.execute("CREATE SCHEMA IF NOT EXISTS company_configuration")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS company_configuration.schema_migrations "
                "(filename text PRIMARY KEY, sha256 char(64) NOT NULL, "
                "applied_at timestamptz NOT NULL DEFAULT now())"
            )
            directory = resources.files(MIGRATION_PACKAGE)
            migrations = sorted(
                name for name in (entry.name for entry in directory.iterdir())
                if name.endswith(".sql") and name[:4].isdigit()
            )
            for filename in migrations:
                sql = directory.joinpath(filename).read_text(encoding="utf-8")
                digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                row = connection.execute(
                    "SELECT sha256 FROM company_configuration.schema_migrations "
                    "WHERE filename = %s", (filename,)
                ).fetchone()
                if row is not None:
                    if row[0].strip() != digest:
                        raise RuntimeError(f"Migration checksum changed: {filename}")
                    continue
                connection.execute(sql)
                connection.execute(
                    "INSERT INTO company_configuration.schema_migrations "
                    "(filename, sha256) VALUES (%s, %s)", (filename, digest)
                )
                applied.append(filename)
    return applied


if __name__ == "__main__":
    dsn = os.getenv("CC_PG_ADMIN_DSN")
    if not dsn:
        raise SystemExit("CC_PG_ADMIN_DSN required")
    print("Applied:", apply_migrations(dsn))
