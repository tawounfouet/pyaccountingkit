"""L02-06 operational PostgreSQL role lifecycle tests in ephemeral CI only."""

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql  # noqa: E402
from psycopg.conninfo import make_conninfo  # noqa: E402

from pyaccountingkit.company_configuration.infrastructure.postgres.role_lifecycle import (  # noqa: E402
    PostgresTenantRoleOperator,
    RoleLifecycleDenied,
    TenantConnectionFactory,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.tenant_boundary import (  # noqa: E402
    TenantConnectionMismatch,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
A = os.getenv("CC_PG_DSN")
B = os.getenv("CC_PG_DSN_B")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, A, B)), reason="Operations proof requires real PostgreSQL test DSNs"
)


@pytest.fixture
def disposable_login():
    role = "cc_runtime_ops_" + uuid4().hex[:10]
    secret = "old-ci-credential-123456"
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(secret)
            )
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
            sql.SQL("GRANT SELECT ON company_configuration.legal_entities TO {}")
            .format(sql.Identifier(role))
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role, tenant_id) VALUES (%s, %s)", (role, "tenant-a"),
        )
    role_dsn = make_conninfo(A, user=role, password=secret)
    try:
        yield role, role_dsn
    finally:
        with psycopg.connect(ADMIN, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE usename=%s AND pid<>pg_backend_pid()", (role,)
            )
            conn.execute(
                "DELETE FROM company_configuration.tenant_role_bindings "
                "WHERE login_role=%s::name", (role,)
            )
            conn.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role)))
            conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))


def test_rotation_invalidates_old_password_and_drains_open_connections(disposable_login):
    role, old_dsn = disposable_login
    operator = PostgresTenantRoleOperator(ADMIN)
    session = psycopg.connect(old_dsn)
    try:
        assert session.execute(
            "SELECT company_configuration.bound_tenant()"
        ).fetchone()[0] == "tenant-a"
        new_password = "rotated-ci-credential-987654"
        receipt = operator.rotate_password(
            login_role=role, expected_tenant="tenant-a", new_password=new_password
        )
        assert receipt.operation == "rotate" and receipt.sessions_terminated >= 1
        with pytest.raises(psycopg.OperationalError):
            session.execute("SELECT 1")
        with pytest.raises(psycopg.OperationalError):
            psycopg.connect(old_dsn)
        new_dsn = make_conninfo(A, user=role, password=new_password)
        with TenantConnectionFactory(new_dsn, tenant_id="tenant-a").connect() as c:
            assert c.execute("SELECT company_configuration.bound_tenant()").fetchone()[0] == (
                "tenant-a"
            )
        assert "rotated-ci-credential" not in repr(
            TenantConnectionFactory(new_dsn, tenant_id="tenant-a")
        )
    finally:
        session.close()


def test_revocation_denies_new_sessions_and_kills_live_session(disposable_login):
    role, dsn = disposable_login
    operator = PostgresTenantRoleOperator(ADMIN)
    session = psycopg.connect(dsn)
    try:
        receipt = operator.revoke_login(login_role=role, expected_tenant="tenant-a")
        assert receipt.operation == "revoke" and receipt.sessions_terminated >= 1
        with pytest.raises(psycopg.OperationalError):
            session.execute("SELECT 1")
        with pytest.raises(psycopg.OperationalError):
            psycopg.connect(dsn)
        with psycopg.connect(ADMIN) as conn:
            assert conn.execute(
                "SELECT count(*) FROM company_configuration.tenant_role_bindings "
                "WHERE login_role=%s::name", (role,)
            ).fetchone()[0] == 0
    finally:
        session.close()


def test_wrong_tenant_and_role_target_are_rejected_without_mutation(disposable_login):
    role, dsn = disposable_login
    operator = PostgresTenantRoleOperator(ADMIN)
    with pytest.raises(RoleLifecycleDenied):
        operator.revoke_login(login_role=role, expected_tenant="tenant-b")
    with pytest.raises(RoleLifecycleDenied):
        operator.rotate_password(login_role="postgres", expected_tenant="tenant-a",
                                 new_password="a-long-secret-from-the-operator")
    with pytest.raises(RoleLifecycleDenied):
        operator.rotate_password(login_role=role, expected_tenant="tenant-a",
                                 new_password="short")
    with TenantConnectionFactory(dsn, tenant_id="tenant-a").connect() as conn:
        assert conn.execute("SELECT company_configuration.bound_tenant()").fetchone()[0] == (
            "tenant-a"
        )


def test_factory_rejects_tenant_mismatch_and_disposes_connection():
    with pytest.raises(TenantConnectionMismatch):
        TenantConnectionFactory(A, tenant_id="tenant-b").connect()
    with TenantConnectionFactory(A, tenant_id="tenant-a").connect() as a:
        assert a.execute("SELECT company_configuration.bound_tenant()").fetchone()[0] == (
            "tenant-a"
        )
    with TenantConnectionFactory(B, tenant_id="tenant-b").connect() as b:
        assert b.execute("SELECT company_configuration.bound_tenant()").fetchone()[0] == (
            "tenant-b"
        )
