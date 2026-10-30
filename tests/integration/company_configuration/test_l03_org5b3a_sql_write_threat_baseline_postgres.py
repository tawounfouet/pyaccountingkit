"""ORG-5b3b: deny ordinary runtime SQL registration and forged Company evidence.

The ordinary tenant runtime role can currently manufacture an internally
consistent Company registration + request/audit/outbox without passing the
Application Service. These tests deliberately lock down *the observed risk*;
future ORG-5b3 remediation must replace these positive exploit assertions
with DENIAL assertions. They never persist a forged audit trail.
"""

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

RUNTIME_A = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not RUNTIME_A,
    reason="ORG-5b3a threat baseline requires isolated tenant PostgreSQL CI roles",
)

def test_runtime_login_lacks_company_insert_and_controlled_execute():
    """The ordinary SQL runtime cannot directly INSERT Company rows."""
    with psycopg.connect(RUNTIME_A) as conn:
        assert conn.execute(
            "SELECT has_table_privilege(current_user, "
            "'company_configuration.organizational_companies', 'INSERT')"
        ).fetchone()[0] is False
        assert conn.execute(
            "SELECT has_function_privilege(current_user, %s, 'EXECUTE')",
            (
                "company_configuration.register_company_controlled("
                "text,uuid,text,text,text,text,text,integer,text,text,text,text,"
                "uuid,uuid,text,timestamptz)",
            ),
        ).fetchone()[0] is False


def test_forged_company_registration_and_evidence_are_denied():
    """Both direct Company DML and forged Company evidence fail closed."""
    company_id = uuid4()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME_A) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_companies "
                "(tenant_id,company_id,name,kind,home_country,status,revision) "
                "VALUES ('tenant-a',%s,'Threat proof','GROUP','FR','DRAFT',1)",
                (company_id,),
            )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME_A) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organization_command_requests "
                "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
                "target_id,revision,correlation_id,audit_id,event_id) "
                "VALUES ('tenant-a','forged','organization.company.register',"
                "%s,%s,'COMPANY',%s,1,'forged-correlation',%s,%s)",
                ("forged-" + str(company_id), "0" * 64, company_id, uuid4(), uuid4()),
            )


def test_independent_issuer_cannot_directly_insert_company_or_evidence():
    """Controlled writer has a dedicated SQL RPC, not arbitrary table INSERT."""
    dsn = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
    if not dsn:
        pytest.skip("CI-only independent Company issuer DSN not configured")
    with psycopg.connect(dsn) as conn:
        for table in (
            "organizational_companies", "organization_command_requests",
            "organization_command_audit", "organization_command_outbox",
        ):
            assert conn.execute(
                "SELECT has_table_privilege(current_user, %s, 'INSERT')",
                ("company_configuration." + table,),
            ).fetchone()[0] is False


def test_cross_tenant_injection_is_still_denied_by_session_role_binding():
    """Prove the existing RLS boundary; its success does NOT authenticate actors."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME_A) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_companies "
                "(tenant_id,company_id,name,kind,home_country,status,revision) "
                "VALUES ('tenant-b',%s,'Cross tenant','GROUP','FR','DRAFT',1)",
                (uuid4(),),
            )
