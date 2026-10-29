"""Ephemeral CI-only per-tenant PostgreSQL roles. NEVER use in production.

Role credentials are deliberately local test fixtures, not real secrets.
A production deployer must provision and rotate independently trusted credentials.
"""

import os

import psycopg
from psycopg import sql

admin_dsn = os.environ["CC_PG_ADMIN_DSN"]

# Session roles have exactly one bound tenant. None is deliberately unbound.
roles = (
    ("cc_runtime_a", "tenant-a", "runtime"),
    ("cc_runtime_b", "tenant-b", "runtime"),
    ("cc_dispatcher_a", "tenant-a", "dispatcher"),
    ("cc_dispatcher_b", "tenant-b", "dispatcher"),
    ("cc_inbox_a", "tenant-a", "inbox"),
    ("cc_inbox_b", "tenant-b", "inbox"),
    ("cc_unbound", None, "unbound"),
)

with psycopg.connect(admin_dsn, autocommit=True) as conn:
    for role, tenant, category in roles:
        conn.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Identifier(role), sql.Literal("cc_testing_only"))
        )
        conn.execute(
            sql.SQL("GRANT USAGE ON SCHEMA company_configuration TO {}").format(
                sql.Identifier(role)
            )
        )
        conn.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION company_configuration.bound_tenant() TO {}")
            .format(sql.Identifier(role))
        )
        if tenant is not None:
            conn.execute(
                "INSERT INTO company_configuration.tenant_role_bindings "
                "(login_role, tenant_id) VALUES (%s, %s)",
                (role, tenant),
            )
        if category == "runtime":
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE ON company_configuration.legal_entities "
                    "TO {}"
                ).format(sql.Identifier(role))
            )
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT ON company_configuration.idempotency_requests, "
                    "company_configuration.audit_records, "
                    "company_configuration.outbox_events, "
                    "company_configuration.authorization_denials TO {}"
                ).format(sql.Identifier(role))
            )
        elif category == "dispatcher":
            conn.execute(
                sql.SQL("GRANT SELECT ON company_configuration.outbox_events TO {}")
                .format(sql.Identifier(role))
            )
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE ON company_configuration.outbox_delivery "
                    "TO {}"
                ).format(sql.Identifier(role))
            )
        elif category == "inbox":
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT ON company_configuration.inbox_receipts TO {}"
                ).format(sql.Identifier(role))
            )
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE "
                    "ON company_configuration.inbox_projection_counts TO {}"
                ).format(sql.Identifier(role))
            )
        elif category == "unbound":
            conn.execute(
                sql.SQL("GRANT SELECT ON company_configuration.legal_entities TO {}")
                .format(sql.Identifier(role))
            )
