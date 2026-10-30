"""ORG-5b3a RED-TEAM BASELINE: prove known SQL authority gap, not protection.

The ordinary tenant runtime role can currently manufacture an internally
consistent Company registration + request/audit/outbox without passing the
Application Service. These tests deliberately lock down *the observed risk*;
future ORG-5b3 remediation must replace these positive exploit assertions
with DENIAL assertions. They never persist a forged audit trail.
"""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

RUNTIME_A = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not RUNTIME_A,
    reason="ORG-5b3a threat baseline requires isolated tenant PostgreSQL CI roles",
)

SENSITIVE_TABLES = (
    "organizational_companies",
    "organization_command_requests",
    "organization_command_audit",
    "organization_command_outbox",
    "organizational_membership_revisions",
    "organization_membership_requests",
    "organization_membership_audit",
    "organization_membership_outbox",
    "organizational_company_revisions",
    "organization_lifecycle_requests",
    "organization_lifecycle_audit",
    "organization_lifecycle_outbox",
)


def test_runtime_login_still_has_broad_organization_insert_grants():
    """Known-open ORG-5b3 risk: write and evidence authority are not separated."""
    with psycopg.connect(RUNTIME_A) as conn:
        for table in SENSITIVE_TABLES:
            can_insert = conn.execute(
                "SELECT has_table_privilege(current_user, %s, 'INSERT')",
                ("company_configuration." + table,),
            ).fetchone()[0]
            assert can_insert, (
                f"ORG-5b3 attack baseline changed for {table}: "
                "replace positive exposure proof with a negative security gate"
            )


def test_runtime_login_can_forge_complete_company_registration_evidence():
    """An internally consistent fabricated triple passes the COMMIT guard.

    SET CONSTRAINTS ALL IMMEDIATE fires the deferred COMMIT-time checks while
    the surrounding transaction is explicitly rolled back: zero forged rows
    survive even if a test fails.
    """
    company_id, audit_id, event_id = uuid4(), uuid4(), uuid4()
    recorded_at = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
    actor = "red-team-fabricated-actor"
    action = "organization.company.register"
    correlation = "red-team-not-attested"
    with psycopg.connect(RUNTIME_A) as conn:
        try:
            conn.execute(
                "INSERT INTO company_configuration.organizational_companies "
                "(tenant_id,company_id,name,kind,home_country,status,revision) "
                "VALUES ('tenant-a',%s,'Threat proof','GROUP','FR','DRAFT',1)",
                (company_id,),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_command_requests "
                "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
                "target_id,revision,correlation_id,audit_id,event_id) "
                "VALUES ('tenant-a',%s,%s,%s,%s,'COMPANY',%s,1,%s,%s,%s)",
                (
                    actor, action, "red-team-" + str(company_id), "0" * 64,
                    company_id, correlation, audit_id, event_id,
                ),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_command_audit "
                "(record_id,tenant_id,actor_id,action,target_kind,target_id,"
                "company_id,legal_entity_id,before_revision,after_revision,"
                "reason,correlation_id,recorded_at) "
                "VALUES (%s,'tenant-a',%s,%s,'COMPANY',%s,%s,NULL,0,1,"
                "'forged',%s,%s)",
                (audit_id, actor, action, company_id, company_id, correlation, recorded_at),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_command_outbox "
                "(event_id,tenant_id,event_type,schema_version,target_kind,target_id,"
                "company_id,legal_entity_id,revision,correlation_id,recorded_at) "
                "VALUES (%s,'tenant-a',%s,1,'COMPANY',%s,%s,NULL,1,%s,%s)",
                (event_id, action, company_id, company_id, correlation, recorded_at),
            )
            # Materially exercise all currently deferred SQL constraint triggers.
            conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
            count = conn.execute(
                "SELECT count(*) FROM company_configuration.organizational_companies "
                "WHERE tenant_id='tenant-a' AND company_id=%s",
                (company_id,),
            ).fetchone()[0]
            assert count == 1, "The threat proof requires a validated domain row"
        finally:
            # Intentional rollback, even on successful red-team demonstration.
            conn.rollback()


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
