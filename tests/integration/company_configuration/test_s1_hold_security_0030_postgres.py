"""S1 #71 quarantine smoke tests on disposable PG16 only.

These tests prove the HOLD path rejects all 15 organization/evidence INSERT
surfaces. They do NOT demonstrate authenticated IAM pairing or production GO.
The existing positive L03 integration suite is intentionally incompatible
with this HOLD migration and must not be marked green or skipped as a gate.
"""

import os

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql  # noqa: E402

from scripts.verify_org_sql_authority import TABLES  # noqa: E402

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
pytestmark = pytest.mark.skipif(
    not ADMIN, reason="S1 HOLD smoke tests require disposable PostgreSQL",
)

TRIGGER = "a00_s1_hold_security"
FUNCTION = "deny_organization_mutation_s1_hold"


def test_every_organization_mutation_surface_has_enabled_hold_trigger():
    assert len(TABLES) == 15
    with psycopg.connect(ADMIN) as conn:
        actual = conn.execute(
            "SELECT c.relname,t.tgname,t.tgenabled,p.proname,"
            "pg_catalog.pg_get_triggerdef(t.oid) "
            "FROM pg_catalog.pg_trigger t "
            "JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid "
            "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid "
            "WHERE n.nspname='company_configuration' "
            "AND t.tgname=%s AND NOT t.tgisinternal",
            (TRIGGER,),
        ).fetchall()
    assert len(actual) == len(TABLES)
    assert {row[0] for row in actual} == set(TABLES)
    for table, trigger, enabled, function, definition in actual:
        assert trigger == TRIGGER, table
        assert enabled == "O", table
        assert function == FUNCTION, table
        assert "BEFORE INSERT OR DELETE OR UPDATE" in definition or (
            "BEFORE INSERT OR UPDATE OR DELETE" in definition
        ), table


@pytest.mark.parametrize("table", TABLES)
def test_all_org_evidence_inserts_are_fail_closed_even_for_schema_owner(table):
    # PostgreSQL executes BEFORE ROW triggers before NOT NULL / CHECK validation.
    # DEFAULT VALUES is sufficient to exercise the guard on every surface.
    with psycopg.connect(ADMIN) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="S1 HOLD_SECURITY"):
            with conn.transaction():
                conn.execute(
                    sql.SQL("INSERT INTO {}.{} DEFAULT VALUES").format(
                        sql.Identifier("company_configuration"), sql.Identifier(table)
                    )
                )


def test_no_public_execute_on_hold_guard():
    with psycopg.connect(ADMIN) as conn:
        (allowed,) = conn.execute(
            "SELECT EXISTS("
            "SELECT 1 FROM pg_catalog.pg_proc p "
            "JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace "
            "CROSS JOIN LATERAL pg_catalog.aclexplode("
            "COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) acl "
            "WHERE n.nspname='company_configuration' AND p.proname=%s "
            "AND acl.grantee=0 AND acl.privilege_type='EXECUTE')",
            (FUNCTION,),
        ).fetchone()
    assert not allowed
