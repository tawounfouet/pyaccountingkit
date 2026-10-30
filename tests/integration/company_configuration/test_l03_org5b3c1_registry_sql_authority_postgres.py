"""ORG-5b3c1: registry SQL issuer authority and adversarial denial proofs.

Ordinary runtime credentials may SELECT tenant-scoped registry information,
but may not INSERT Establishment, LegalIdentifier, or forge their evidence.
Independent registry issuers have EXECUTE-only command authority, and an
administrator-controlled revocation stops it without touching old events.
These are CI-only roles: actor provenance is NOT authenticated human IAM.
"""

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

RUNTIME = os.getenv("CC_PG_DSN")
REGISTRY_WRITER = os.getenv("CC_PG_ORG_REGISTRY_WRITER_DSN")
COMPANY_WRITER = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
ADMIN = os.getenv("CC_PG_ADMIN_DSN")
pytestmark = pytest.mark.skipif(
    not all((RUNTIME, REGISTRY_WRITER, COMPANY_WRITER, ADMIN)),
    reason="Requires isolated PostgreSQL runtime, registry issuer and admin roles",
)

FUNCTIONS = (
    "company_configuration.register_establishment_controlled("
    "text,uuid,uuid,text,text,date,date,text,integer,text,text,text,text,"
    "uuid,uuid,text,timestamptz)",
    "company_configuration.register_legal_identifier_controlled("
    "text,uuid,uuid,text,text,text,text,date,date,text,text,text,text,text,"
    "uuid,uuid,text,timestamptz)",
)
TABLES = (
    "organizational_establishments",
    "organizational_legal_identifiers",
    "organization_command_requests",
    "organization_command_audit",
    "organization_command_outbox",
)


def _registry_insert(target_kind: str) -> tuple[str, tuple]:
    return (
        "INSERT INTO company_configuration.organization_command_requests "
        "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
        "target_id,revision,correlation_id,audit_id,event_id) "
        "VALUES ('tenant-a','fabricated',%s,%s,%s,%s,%s,1,'fabricated',%s,%s)",
        (
            "organization.establishment.register"
            if target_kind == "ESTABLISHMENT"
            else "organization.legal_identifier.register",
            str(uuid4()), "a" * 64, target_kind, uuid4(), uuid4(), uuid4(),
        ),
    )


def test_no_runtime_or_company_issuer_execute_privilege_for_registry_commands():
    for dsn in (RUNTIME, COMPANY_WRITER):
        with psycopg.connect(dsn) as conn:
            for function in FUNCTIONS:
                assert conn.execute(
                    "SELECT has_function_privilege(current_user,%s,'EXECUTE')",
                    (function,),
                ).fetchone()[0] is False
            for table in TABLES[:2]:
                assert conn.execute(
                    "SELECT has_table_privilege(current_user,%s,'INSERT')",
                    ("company_configuration." + table,),
                ).fetchone()[0] is False


def test_registry_issuer_cannot_directly_insert_domain_or_evidence():
    with psycopg.connect(REGISTRY_WRITER) as conn:
        for table in TABLES:
            assert conn.execute(
                "SELECT has_table_privilege(current_user,%s,'INSERT')",
                ("company_configuration." + table,),
            ).fetchone()[0] is False
        for function in FUNCTIONS:
            assert conn.execute(
                "SELECT has_function_privilege(current_user,%s,'EXECUTE')",
                (function,),
            ).fetchone()[0] is True


@pytest.mark.parametrize("target_kind", ["ESTABLISHMENT", "LEGAL_IDENTIFIER"])
def test_runtime_cannot_forge_registry_evidence_on_shared_tables(target_kind):
    sql, values = _registry_insert(target_kind)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute(sql, values)


def test_runtime_direct_establishment_and_identifier_inserts_are_denied():
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_establishments "
                "(tenant_id,establishment_id,legal_entity_id,name,country,"
                "valid_from,status,revision) "
                "VALUES ('tenant-a',%s,%s,'forged','FR','2026-01-01','PLANNED',1)",
                (uuid4(), uuid4()),
            )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_legal_identifiers "
                "(tenant_id,identifier_id,legal_entity_id,scheme,value,issuer,"
                "jurisdiction,valid_from,source_ref) "
                "VALUES ('tenant-a',%s,%s,'SIREN','000','INSEE','FR',"
                "'2026-01-01','forged')",
                (uuid4(), uuid4()),
            )


def test_runtime_cannot_set_role_into_registry_issuer():
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute("SET ROLE cc_org_registry_writer_a")


def test_registry_issuer_revocation_blocks_command_even_with_correct_login():
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.organization_registry_command_issuers "
            "SET enabled=false WHERE login_role='cc_org_registry_writer_a'"
        )
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(REGISTRY_WRITER) as conn:
                conn.execute(
                    "SELECT company_configuration.register_establishment_controlled("
                    "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        "tenant-a", uuid4(), uuid4(), "Revoked issuer", "FR",
                        "2026-01-01", None, "PLANNED", 1, "actor", "key",
                        "a" * 64, "corr", uuid4(), uuid4(), "test", "2026-10-30T08:00:00Z",
                    ),
                )
    finally:
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "UPDATE company_configuration.organization_registry_command_issuers "
                "SET enabled=true WHERE login_role='cc_org_registry_writer_a'"
            )


def test_registry_issuer_cannot_write_other_tenant_with_tenant_a_login():
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(REGISTRY_WRITER) as conn:
            conn.execute(
                "SELECT company_configuration.register_legal_identifier_controlled("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    "tenant-b", uuid4(), uuid4(), "SIREN", "123",
                    "INSEE", "FR", "2026-01-01", None, "fraud", "actor",
                    "key", "b" * 64, "corr", uuid4(), uuid4(),
                    "test", "2026-10-30T08:00:00Z",
                ),
            )
