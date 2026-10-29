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
                entry.name for entry in directory.iterdir()
                if entry.name.endswith(".sql") and entry.name[:4].isdigit()
            )
            numbers = [int(filename[:4]) for filename in migrations]
            if numbers != list(range(1, len(migrations) + 1)):
                raise RuntimeError("Migration source inventory has gaps or duplicate numbers")

            # Fail closed BEFORE executing the first missing script: never run
            # an older migrator against a newer schema, or skip a missing
            # previously applied migration. Both cases need an explicit,
            # reviewed upgrade/rollback procedure, not best-effort execution.
            rows = connection.execute(
                "SELECT filename, sha256 FROM company_configuration.schema_migrations"
            ).fetchall()
            recorded = {filename: checksum.strip() for filename, checksum in rows}
            unknown = sorted(set(recorded) - set(migrations))
            if unknown:
                raise RuntimeError(f"Unknown already-applied migrations: {unknown}")
            if set(recorded) != set(migrations[:len(recorded)]):
                raise RuntimeError("Applied migration history is not a contiguous prefix")

            sources = []
            for filename in migrations:
                sql = directory.joinpath(filename).read_text(encoding="utf-8")
                digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                if filename in recorded and recorded[filename] != digest:
                    raise RuntimeError(f"Migration checksum changed: {filename}")
                sources.append((filename, sql, digest))

            for filename, sql, digest in sources:
                if filename in recorded:
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
