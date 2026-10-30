"""ORG-5b3c3: adversarial PostgreSQL write-authority qualification.

An ordinary bound runtime SQL principal cannot forge membership revisions or
MembershipId-native evidence; a separately bound issuer can call only the
controlled stored command. This does NOT attest a human actor's identity.
"""

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
ISSUER_A = os.getenv("CC_PG_ORG_MEMBERSHIP_WRITER_DSN")
ISSUER_B = os.getenv("CC_PG_ORG_MEMBERSHIP_WRITER_DSN_B")
COMPANY_WRITER = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
LIFECYCLE_WRITER = os.getenv("CC_PG_ORG_LIFECYCLE_WRITER_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, RUNTIME, ISSUER_A, ISSUER_B, COMPANY_WRITER, LIFECYCLE_WRITER)),
    reason="ORG-5b3c3 requires ephemeral isolated SQL roles",
)

FUNCTION = (
    "company_configuration.register_membership_revision_controlled("
    "text,uuid,integer,uuid,uuid,text,boolean,date,date,timestamptz,"
    "text,text,text,text,text,uuid,uuid,text)"
)
TABLES = (
    "organizational_membership_revisions",
    "organization_membership_requests",
    "organization_membership_audit",
    "organization_membership_outbox",
)


def _call(tenant="tenant-a"):
    return (
        "SELECT company_configuration.register_membership_revision_controlled("
        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            tenant, uuid4(), 1, uuid4(), uuid4(), "ADMINISTRATIVE", True,
            "2026-01-01", None, "2026-10-30T09:00:00Z",
            "red-team", "self-asserted", "forged-" + str(uuid4()),
            "a" * 64, "correlation", uuid4(), uuid4(), "fake approval",
        ),
    )


def _count_rows():
    with psycopg.connect(ADMIN) as conn:
        return tuple(
            conn.execute("SELECT count(*) FROM company_configuration." + table)
            .fetchone()[0]
            for table in TABLES
        )


def test_runtime_and_other_domain_issuers_cannot_execute_membership_command():
    for dsn in (RUNTIME, COMPANY_WRITER, LIFECYCLE_WRITER):
        with psycopg.connect(dsn) as conn:
            assert conn.execute(
                "SELECT has_function_privilege(current_user,%s,'EXECUTE')",
                (FUNCTION,),
            ).fetchone()[0] is False


def test_issuer_is_read_and_execute_only_not_direct_insert():
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
def test_runtime_has_no_membership_insert_privilege_for_any_surface(table):
    with psycopg.connect(RUNTIME) as conn:
        assert conn.execute(
            "SELECT has_table_privilege(current_user,%s,'INSERT')",
            ("company_configuration." + table,),
        ).fetchone()[0] is False


@pytest.mark.parametrize("table", TABLES)
def test_direct_membership_and_evidence_forgery_fail_without_persisting(table):
    before = _count_rows()
    sql, values = {
        "organizational_membership_revisions": (
            "INSERT INTO company_configuration.organizational_membership_revisions "
            "(tenant_id,membership_id,revision,company_id,legal_entity_id,"
            "kind,exclusive,valid_from,recorded_at,source_ref) "
            "VALUES ('tenant-a',%s,1,%s,%s,'OPERATIONAL',true,'2026-01-01',"
            "now(),'red-team')",
            (uuid4(), uuid4(), uuid4()),
        ),
        "organization_membership_requests": (
            "INSERT INTO company_configuration.organization_membership_requests "
            "(tenant_id,actor_id,action,request_key,request_digest,membership_id,"
            "company_id,legal_entity_id,revision,correlation_id,audit_id,event_id) "
            "VALUES ('tenant-a','untrusted','organization.membership.assign',"
            "'red-team',%s,%s,%s,%s,1,'corr',%s,%s)",
            ("a" * 64, uuid4(), uuid4(), uuid4(), uuid4(), uuid4()),
        ),
        "organization_membership_audit": (
            "INSERT INTO company_configuration.organization_membership_audit "
            "(record_id,tenant_id,actor_id,action,membership_id,company_id,"
            "legal_entity_id,before_revision,after_revision,valid_from,"
            "source_ref,reason,correlation_id,recorded_at) "
            "VALUES (%s,'tenant-a','untrusted','organization.membership.assign',"
            "%s,%s,%s,0,1,'2026-01-01','fake','forgery','corr',now())",
            (uuid4(), uuid4(), uuid4(), uuid4()),
        ),
        "organization_membership_outbox": (
            "INSERT INTO company_configuration.organization_membership_outbox "
            "(event_id,tenant_id,event_type,schema_version,membership_id,company_id,"
            "legal_entity_id,revision,kind,exclusive,valid_from,"
            "source_ref,correlation_id,recorded_at) "
            "VALUES (%s,'tenant-a','organization.membership.assign',1,"
            "%s,%s,%s,1,'OPERATIONAL',true,'2026-01-01','fake','corr',now())",
            (uuid4(), uuid4(), uuid4(), uuid4()),
        ),
    }[table]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute(sql, values)
    assert _count_rows() == before


def test_runtime_cannot_invoke_command_or_set_role_into_issuer():
    before = _count_rows()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            statement, values = _call()
            conn.execute(statement, values)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute("SET ROLE cc_org_membership_writer_a")
    assert _count_rows() == before


def test_revoked_issuer_cannot_submit_membership_command():
    before = _count_rows()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.organization_membership_command_issuers "
            "SET enabled=false WHERE login_role='cc_org_membership_writer_a'"
        )
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(ISSUER_A) as conn:
                statement, values = _call()
                conn.execute(statement, values)
    finally:
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "UPDATE company_configuration.organization_membership_command_issuers "
                "SET enabled=true WHERE login_role='cc_org_membership_writer_a'"
            )
    assert _count_rows() == before


def test_issuer_cannot_assert_another_tenant():
    before = _count_rows()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(ISSUER_A) as conn:
            statement, values = _call("tenant-b")
            conn.execute(statement, values)
    assert _count_rows() == before
