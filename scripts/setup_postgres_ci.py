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
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT ON "
                    "company_configuration.organization_command_requests, "
                    "company_configuration.organization_command_audit, "
                    "company_configuration.organization_command_outbox TO {}"
                ).format(sql.Identifier(role))
            )
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT ON "
                    "company_configuration.organizational_company_revisions, "
                    "company_configuration.organizational_establishment_revisions, "
                    "company_configuration.organization_lifecycle_requests, "
                    "company_configuration.organization_lifecycle_audit, "
                    "company_configuration.organization_lifecycle_outbox TO {}"
                ).format(sql.Identifier(role))
            )
            conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT ON "
                    "company_configuration.organization_membership_requests, "
                    "company_configuration.organization_membership_audit, "
                    "company_configuration.organization_membership_outbox TO {}"
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
                sql.SQL(
                    "GRANT SELECT ON company_configuration.organization_command_outbox TO {}"
                ).format(sql.Identifier(role))
            )
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

    # ORG-5b3b: independently provisioned issuer login; ordinary runtime roles
    # are NEVER members and cannot SET ROLE into it. CI-only test credentials.
    company_function = (
        "company_configuration.register_company_controlled("
        "text,uuid,text,text,text,text,text,integer,text,text,text,text,"
        "uuid,uuid,text,timestamptz)"
    )
    for role, tenant in (
        ("cc_org_company_writer_a", "tenant-a"),
        ("cc_org_company_writer_b", "tenant-b"),
    ):
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
            sql.SQL(
                "GRANT SELECT ON company_configuration.organization_command_requests, "
                "company_configuration.organization_command_audit, "
                "company_configuration.organization_command_outbox TO {}"
            ).format(sql.Identifier(role))
        )
        conn.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION company_configuration.bound_tenant() TO {}")
            .format(sql.Identifier(role))
        )
        conn.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION " + company_function + " TO {}")
            .format(sql.Identifier(role))
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )
        conn.execute(
            "INSERT INTO company_configuration.organization_company_command_issuers "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )

    # New ordinary runtime sessions can read Company history, but cannot
    # write Company registrations, nor execute the controlled command function.
    conn.execute(
        "REVOKE INSERT ON company_configuration.organizational_companies "
        "FROM cc_runtime_a,cc_runtime_b"
    )

    # ORG-5b3c1: separate registry command issuer from ordinary runtime and
    # from the Company issuer. Ephemeral CI credentials only, not production IAM.
    registry_functions = (
        "company_configuration.register_establishment_controlled("
        "text,uuid,uuid,text,text,date,date,text,integer,text,text,text,text,"
        "uuid,uuid,text,timestamptz)",
        "company_configuration.register_legal_identifier_controlled("
        "text,uuid,uuid,text,text,text,text,date,date,text,text,text,text,text,"
        "uuid,uuid,text,timestamptz)",
    )
    for role, tenant in (
        ("cc_org_registry_writer_a", "tenant-a"),
        ("cc_org_registry_writer_b", "tenant-b"),
    ):
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
        conn.execute(
            sql.SQL(
                "GRANT SELECT ON company_configuration.organization_command_requests, "
                "company_configuration.organization_command_audit, "
                "company_configuration.organization_command_outbox TO {}"
            ).format(sql.Identifier(role))
        )
        for func in registry_functions:
            conn.execute(
                sql.SQL("GRANT EXECUTE ON FUNCTION " + func + " TO {}").format(
                    sql.Identifier(role)
                )
            )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )
        conn.execute(
            "INSERT INTO company_configuration.organization_registry_command_issuers "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )

    # Ordinary SQL credentials must not directly create any registration target.
    # They retain evidence SELECT for existing read paths, but evidence INSERT
    # with either registry target_kind is rejected by migration 0023 guard.
    conn.execute(
        "REVOKE INSERT ON company_configuration.organizational_establishments, "
        "company_configuration.organizational_legal_identifiers "
        "FROM cc_runtime_a,cc_runtime_b"
    )

    # ORG-5b3c2: lifecycle issuer identities are independent of both runtime
    # and the registration issuers. CI-only credentials; production IAM absent.
    lifecycle_func = (
        "company_configuration.transition_organization_controlled("
        "text,text,uuid,integer,text,text,timestamptz,text,text,text,text,text,"
        "uuid,uuid,text)"
    )
    for role, tenant in (
        ("cc_org_lifecycle_writer_a", "tenant-a"),
        ("cc_org_lifecycle_writer_b", "tenant-b"),
    ):
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
        # Read-only projections and deferred commit guard support.
        conn.execute(
            sql.SQL(
                "GRANT SELECT ON company_configuration.organizational_companies, "
                "company_configuration.organizational_establishments, "
                "company_configuration.organizational_company_revisions, "
                "company_configuration.organizational_establishment_revisions, "
                "company_configuration.organization_lifecycle_requests, "
                "company_configuration.organization_lifecycle_audit, "
                "company_configuration.organization_lifecycle_outbox TO {}"
            ).format(sql.Identifier(role))
        )
        conn.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION " + lifecycle_func + " TO {}")
            .format(sql.Identifier(role))
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )
        conn.execute(
            "INSERT INTO company_configuration.organization_lifecycle_command_issuers "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )

    # Runtime can still SELECT its own lifecycle records through FORCE RLS,
    # but can no longer INSERT even a coherent forged transition+evidence.
    conn.execute(
        "REVOKE INSERT ON "
        "company_configuration.organizational_company_revisions, "
        "company_configuration.organizational_establishment_revisions, "
        "company_configuration.organization_lifecycle_requests, "
        "company_configuration.organization_lifecycle_audit, "
        "company_configuration.organization_lifecycle_outbox "
        "FROM cc_runtime_a,cc_runtime_b"
    )

    # ORG-5b3c3: native membership issuer is separate from ordinary runtime,
    # registration, and lifecycle identities. Testing credentials only.
    membership_func = (
        "company_configuration.register_membership_revision_controlled("
        "text,uuid,integer,uuid,uuid,text,boolean,date,date,timestamptz,"
        "text,text,text,text,text,uuid,uuid,text)"
    )
    for role, tenant in (
        ("cc_org_membership_writer_a", "tenant-a"),
        ("cc_org_membership_writer_b", "tenant-b"),
    ):
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
        # Domain read + 0021 deferred membership evidence guard; absolutely no
        # table INSERT, UPDATE or DELETE for this scoped writer identity.
        conn.execute(
            sql.SQL(
                "GRANT SELECT ON company_configuration.legal_entities, "
                "company_configuration.organizational_companies, "
                "company_configuration.organizational_company_revisions, "
                "company_configuration.organizational_membership_revisions, "
                "company_configuration.organization_membership_requests, "
                "company_configuration.organization_membership_audit, "
                "company_configuration.organization_membership_outbox TO {}"
            ).format(sql.Identifier(role))
        )
        conn.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION " + membership_func + " TO {}")
            .format(sql.Identifier(role))
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )
        conn.execute(
            "INSERT INTO company_configuration.organization_membership_command_issuers "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )

    # Defense in depth: revoked runtime INSERT plus permanent owner-guarded
    # SQL INSERT triggers in 0025, including all three evidence tables.
    conn.execute(
        "REVOKE INSERT ON "
        "company_configuration.organizational_membership_revisions, "
        "company_configuration.organization_membership_requests, "
        "company_configuration.organization_membership_audit, "
        "company_configuration.organization_membership_outbox "
        "FROM cc_runtime_a,cc_runtime_b"
    )

    # G3-C02b1: CI-only nonce consumers, isolated from ordinary runtime and
    # every SQL business issuer. No direct table privileges, no role inheritance.
    nonce_function = (
        "company_configuration.consume_organization_command_nonce("
        "text,text,uuid,timestamptz)"
    )
    for role, tenant in (
        ("cc_org_nonce_consumer_a", "tenant-a"),
        ("cc_org_nonce_consumer_b", "tenant-b"),
    ):
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
            sql.SQL(
                "GRANT EXECUTE ON FUNCTION company_configuration.bound_tenant() TO {}"
            ).format(sql.Identifier(role))
        )
        conn.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION " + nonce_function + " TO {}").format(
                sql.Identifier(role)
            )
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )
        conn.execute(
            "INSERT INTO company_configuration.organization_nonce_consumers "
            "(login_role,tenant_id) VALUES (%s,%s)", (role, tenant),
        )
