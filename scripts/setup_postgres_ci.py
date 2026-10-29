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
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT ON "
                    "company_configuration.organizational_companies, "
                    "company_configuration.organizational_establishments, "
                    "company_configuration.organizational_legal_identifiers, "
                    "company_configuration.organizational_membership_revisions "
                    "TO {}"
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
                sql.SQL("GRANT SELECT ON company_configuration.organizational_companies TO {}")
                .format(sql.Identifier(role))
            )
            conn.execute(
                sql.SQL("GRANT SELECT ON company_configuration.legal_entities TO {}")
                .format(sql.Identifier(role))
            )

    # Dedicated control-plane LOGIN: no direct role DDL or private-table grants.
    conn.execute(
        "CREATE ROLE cc_control_plane LOGIN NOSUPERUSER NOCREATEDB "
        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS "
        "PASSWORD 'cc_testing_only'"
    )
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_control_plane")
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_issue_fence("
        "uuid,text,text,text,text,text,text,timestamptz) TO cc_control_plane"
    )
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_revoke_fence("
        "uuid,text,text) TO cc_control_plane"
    )
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_execute_fence("
        "uuid,text,text,text,text,text,text) TO cc_control_plane"
    )

    # Independent write-only privileged audit LOGIN, not a schema owner and
    # deliberately not a member of the delegated DDL control-plane role.
    conn.execute(
        "CREATE ROLE cc_privileged_audit LOGIN NOSUPERUSER NOCREATEDB "
        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS "
        "PASSWORD 'cc_testing_only'"
    )
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_privileged_audit")
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_append_privileged_audit("
        "uuid,uuid,text,text,text,text,text,text,text,text) TO cc_privileged_audit"
    )

    # Ephemeral independent IAM revocation receiver, no DDL/audit grants.
    conn.execute(
        "CREATE ROLE cc_iam_revocation LOGIN NOSUPERUSER NOCREATEDB "
        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS "
        "PASSWORD 'cc_testing_only'"
    )
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_iam_revocation")
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_ack_iam_revocation("
        "uuid,uuid,text,text,text,text,text,text,text) TO cc_iam_revocation"
    )

    # Independent IAM acknowledgement delivery identity, no revocation/DDL rights.
    conn.execute(
        "CREATE ROLE cc_iam_delivery LOGIN NOSUPERUSER NOCREATEDB "
        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS "
        "PASSWORD 'cc_testing_only'"
    )
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_iam_delivery")
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_claim_iam_ack(integer) "
        "TO cc_iam_delivery"
    )
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_complete_iam_ack(uuid,uuid) "
        "TO cc_iam_delivery"
    )
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_fail_iam_ack(uuid,uuid,text) "
        "TO cc_iam_delivery"
    )

    # Limited IAM DEAD-letter recovery login, separate from delivery and DDL.
    conn.execute(
        "CREATE ROLE cc_iam_recovery LOGIN NOSUPERUSER NOCREATEDB "
        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS "
        "PASSWORD 'cc_testing_only'"
    )
    conn.execute("GRANT USAGE ON SCHEMA company_configuration TO cc_iam_recovery")
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_list_dead_iam_acks("
        "text,integer) TO cc_iam_recovery"
    )
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_redrive_dead_iam_ack("
        "uuid,uuid,text,text,text,text,text,text) TO cc_iam_recovery"
    )
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_iam_ack_metrics() "
        "TO cc_iam_delivery"
    )

    # Independent IAM recovery APPROVAL writer. Recovery never receives this
    # capability; only approval-writer can issue short-lived SQL grants.
    conn.execute(
        "CREATE ROLE cc_iam_approval_writer LOGIN NOSUPERUSER NOCREATEDB "
        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS "
        "PASSWORD 'cc_testing_only'"
    )
    conn.execute(
        "GRANT USAGE ON SCHEMA company_configuration TO cc_iam_approval_writer"
    )
    conn.execute(
        "GRANT EXECUTE ON FUNCTION company_configuration.cp_grant_iam_ack_redrive("
        "uuid,uuid,text,text,text,text,text,text,timestamptz) "
        "TO cc_iam_approval_writer"
    )
