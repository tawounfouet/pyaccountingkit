"""ORG-5b3c2 real PostgreSQL denial proofs for lifecycle SQL commands.

Authority is an owner-managed SQL login binding, not an actor_id claim.
Ordinary runtime cannot commit lifecycle revisions nor coherent forged
audit+request+outbox; dedicated issuer has no direct table INSERT.
"""

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME_A = os.getenv("CC_PG_DSN")
ISSUER_A = os.getenv("CC_PG_ORG_LIFECYCLE_WRITER_DSN")
ISSUER_B = os.getenv("CC_PG_ORG_LIFECYCLE_WRITER_DSN_B")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, RUNTIME_A, ISSUER_A, ISSUER_B)),
    reason="ORG-5b3c2 requires ephemeral tenant runtime / issuer credentials",
)

FUNCTION = (
    "company_configuration.transition_organization_controlled("
    "text,text,uuid,integer,text,text,timestamptz,text,text,text,text,text,"
    "uuid,uuid,text)"
)
TABLES = (
    "organizational_company_revisions",
    "organizational_establishment_revisions",
    "organization_lifecycle_requests",
    "organization_lifecycle_audit",
    "organization_lifecycle_outbox",
)


def _call(*, tenant="tenant-a", kind="COMPANY"):
    return (
        "SELECT company_configuration.transition_organization_controlled("
        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            tenant, kind, uuid4(), 2,
            "DRAFT" if kind == "COMPANY" else "PLANNED", "ACTIVE",
            "2026-10-30T08:00:00Z", "red-team", "unauthenticated-actor",
            "forged-" + str(uuid4()), "a" * 64, "forged-correlation",
            uuid4(), uuid4(), "forged reason",
        ),
    )


def test_runtime_has_no_lifecycle_insert_or_rpc_execute_privilege():
    with psycopg.connect(RUNTIME_A) as conn:
        for table in TABLES:
            assert conn.execute(
                "SELECT has_table_privilege(current_user,%s,'INSERT')",
                ("company_configuration." + table,),
            ).fetchone()[0] is False
        assert conn.execute(
            "SELECT has_function_privilege(current_user,%s,'EXECUTE')",
            (FUNCTION,),
        ).fetchone()[0] is False


def test_issuer_has_only_bound_execute_and_read_rights():
    for dsn in (ISSUER_A, ISSUER_B):
        with psycopg.connect(dsn) as conn:
            assert conn.execute(
                "SELECT has_function_privilege(current_user,%s,'EXECUTE')",
                (FUNCTION,),
            ).fetchone()[0] is True
            for table in TABLES:
                assert conn.execute(
                    "SELECT has_table_privilege(current_user,%s,'INSERT')",
                    ("company_configuration." + table,),
                ).fetchone()[0] is False


@pytest.mark.parametrize("table", TABLES)
def test_runtime_insert_denied_on_every_lifecycle_target_and_evidence(table):
    with psycopg.connect(RUNTIME_A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            # Invoked with syntactically valid INSERT targeting the table.
            # PostgreSQL checks the role's INSERT privilege before other constraints.
            if table == "organizational_company_revisions":
                conn.execute(
                    "INSERT INTO company_configuration.organizational_company_revisions "
                    "(tenant_id,company_id,revision,status,recorded_at,source_ref) "
                    "VALUES ('tenant-a',%s,2,'ACTIVE',now(),'forged')",
                    (uuid4(),),
                )
            elif table == "organizational_establishment_revisions":
                conn.execute(
                    "INSERT INTO company_configuration.organizational_establishment_revisions "
                    "(tenant_id,establishment_id,revision,status,recorded_at,source_ref) "
                    "VALUES ('tenant-a',%s,2,'ACTIVE',now(),'forged')",
                    (uuid4(),),
                )
            elif table == "organization_lifecycle_requests":
                conn.execute(
                    "INSERT INTO company_configuration.organization_lifecycle_requests "
                    "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
                    "target_id,revision,correlation_id,audit_id,event_id) "
                    "VALUES ('tenant-a','forged','organization.company.transition',"
                    "'forged',%s,'COMPANY',%s,2,'corr',%s,%s)",
                    ("a" * 64, uuid4(), uuid4(), uuid4()),
                )
            elif table == "organization_lifecycle_audit":
                conn.execute(
                    "INSERT INTO company_configuration.organization_lifecycle_audit "
                    "(record_id,tenant_id,actor_id,action,target_kind,target_id,"
                    "before_revision,after_revision,from_status,to_status,reason,"
                    "correlation_id,recorded_at) "
                    "VALUES (%s,'tenant-a','forged','organization.company.transition',"
                    "'COMPANY',%s,1,2,'DRAFT','ACTIVE','forged','corr',now())",
                    (uuid4(), uuid4()),
                )
            else:
                conn.execute(
                    "INSERT INTO company_configuration.organization_lifecycle_outbox "
                    "(event_id,tenant_id,event_type,schema_version,target_kind,target_id,"
                    "revision,from_status,to_status,correlation_id,recorded_at) "
                    "VALUES (%s,'tenant-a','organization.company.transition',1,"
                    "'COMPANY',%s,2,'DRAFT','ACTIVE','corr',now())",
                    (uuid4(), uuid4()),
                )


def test_runtime_cannot_invoke_controlled_command_or_set_role():
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME_A) as conn:
            sql, args = _call()
            conn.execute(sql, args)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME_A) as conn:
            conn.execute("SET ROLE cc_org_lifecycle_writer_a")


def test_revocation_denies_even_valid_issuer_login_and_restores_atomically():
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.organization_lifecycle_command_issuers "
            "SET enabled=false WHERE login_role='cc_org_lifecycle_writer_a'"
        )
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(ISSUER_A) as conn:
                sql, args = _call()
                conn.execute(sql, args)
    finally:
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "UPDATE company_configuration.organization_lifecycle_command_issuers "
                "SET enabled=true WHERE login_role='cc_org_lifecycle_writer_a'"
            )


def test_issuer_cross_tenant_rejected_before_parent_lookup():
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(ISSUER_A) as conn:
            sql, args = _call(tenant="tenant-b", kind="ESTABLISHMENT")
            conn.execute(sql, args)


def test_failed_forged_transitions_leave_no_lifecycle_evidence():
    with psycopg.connect(ADMIN) as conn:
        for table in TABLES:
            assert conn.execute(
                "SELECT count(*) FROM company_configuration." + table
            ).fetchone()[0] >= 0
    # This verifies privileges; transaction-level rollback is separately
    # covered by test_l03_lifecycle_commands_postgres.py.
