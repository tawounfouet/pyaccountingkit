"""PostgreSQL 16 proof for owner-only privilege fence and SQL role DDL ordering."""
# ruff: noqa: E402

import os
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql
from psycopg.conninfo import make_conninfo

from pyaccountingkit.company_configuration.application.authorization_fence import (
    PrivilegedFencePermit,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.authorization_fence import (
    FencedRoleOperation,
    PostgresPrivilegedAuthorizationFence,
    PrivilegedFenceDenied,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and RUNTIME), reason="Owner-only PostgreSQL integration DSNs required"
)


@pytest.fixture
def login():
    name = "cc_runtime_fence_" + uuid4().hex[:10]
    secret = "initial-ci-fence-password-12345"
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Identifier(name), sql.Literal(secret))
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,%s)", (name, "tenant-a")
        )
        conn.execute(
            sql.SQL("GRANT USAGE ON SCHEMA company_configuration TO {}").format(
                sql.Identifier(name)
            )
        )
        conn.execute(
            sql.SQL(
                "GRANT EXECUTE ON FUNCTION company_configuration.bound_tenant() TO {}"
            ).format(sql.Identifier(name))
        )
    try:
        yield name, make_conninfo(RUNTIME, user=name, password=secret)
    finally:
        # CI-only owner cleanup, never a production recovery procedure.
        with psycopg.connect(ADMIN, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE usename=%s AND pid<>pg_backend_pid()", (name,)
            )
            conn.execute(
                "TRUNCATE company_configuration.privileged_fence_events, "
                "company_configuration.privileged_authorization_fences"
            )
            conn.execute(
                "DELETE FROM company_configuration.tenant_role_bindings "
                "WHERE login_role=%s::name", (name,)
            )
            conn.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(name)))
            conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(name)))


def grant(name, operation="rotate"):
    return PrivilegedFencePermit(
        uuid4(), "tenant-a", name, operation, "op-a", "checker-b", "approval-123",
        datetime.now(UTC) + timedelta(minutes=10),
    )


def execute_request(permit):
    return FencedRoleOperation(
        permit.request_id, permit.tenant_id, permit.login_role,
        permit.operation, permit.actor_id, permit.approval_id,
    )


def audit(request_id):
    with psycopg.connect(ADMIN) as conn:
        state = conn.execute(
            "SELECT state FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s", (request_id,),
        ).fetchone()[0]
        events = [r[0] for r in conn.execute(
            "SELECT action FROM company_configuration.privileged_fence_events "
            "WHERE request_id=%s ORDER BY recorded_at", (request_id,),
        ).fetchall()]
    return state, events


def test_consumption_rotates_password_and_replay_is_denied(login):
    name, old_dsn = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    permit = grant(name)
    fence.issue(permit)
    assert audit(permit.request_id) == ("ACTIVE", ["ISSUED"])
    new_password = "new-ci-fence-password-123456789"
    receipt = fence.execute(execute_request(permit), new_password=new_password)
    assert receipt.operation == "rotate"
    assert audit(permit.request_id) == ("CONSUMED", ["ISSUED", "CONSUMED"])
    with pytest.raises(PrivilegedFenceDenied):
        fence.execute(execute_request(permit), new_password=new_password)
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(old_dsn)
    with psycopg.connect(make_conninfo(RUNTIME, user=name, password=new_password)) as conn:
        assert conn.execute("SELECT company_configuration.bound_tenant()").fetchone()[0] == (
            "tenant-a"
        )


def test_revocation_before_ddl_blocks_role_change(login):
    name, dsn = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    permit = grant(name)
    fence.issue(permit)
    assert fence.revoke(request_id=permit.request_id, tenant_id="tenant-a", revoked_by="iam")
    assert not fence.revoke(
        request_id=permit.request_id, tenant_id="tenant-a", revoked_by="iam"
    )
    with pytest.raises(PrivilegedFenceDenied):
        fence.execute(execute_request(permit), new_password="not-used-ci-pass-123456")
    assert audit(permit.request_id) == ("REVOKED", ["ISSUED", "REVOKED"])
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1


def test_foreign_actor_approval_tenant_or_operation_denied(login):
    name, _ = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    permit = grant(name)
    fence.issue(permit)
    for scope in (
        FencedRoleOperation(permit.request_id, "tenant-b", name, "rotate", "op-a", "approval-123"),
        FencedRoleOperation(permit.request_id, "tenant-a", name, "rotate", "wrong", "approval-123"),
        FencedRoleOperation(permit.request_id, "tenant-a", name, "revoke", "op-a", "approval-123"),
        FencedRoleOperation(permit.request_id, "tenant-a", name, "rotate", "op-a", "wrong"),
    ):
        with pytest.raises(PrivilegedFenceDenied):
            fence.execute(scope, new_password="long-invalid-ci-secret-1234")
    assert audit(permit.request_id) == ("ACTIVE", ["ISSUED"])


def test_only_one_active_authorization_per_login(login):
    name, _ = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    first = grant(name)
    fence.issue(first)
    with pytest.raises(psycopg.errors.UniqueViolation):
        fence.issue(grant(name, "revoke"))
    fence.revoke(request_id=first.request_id, tenant_id="tenant-a", revoked_by="iam")
    second = grant(name, "revoke")
    fence.issue(second)
    assert audit(second.request_id) == ("ACTIVE", ["ISSUED"])


def test_fenced_revoke_no_login_and_binding_atomic(login):
    name, dsn = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    permit = grant(name, "revoke")
    fence.issue(permit)
    assert fence.execute(execute_request(permit)).operation == "revoke"
    assert audit(permit.request_id)[0] == "CONSUMED"
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.tenant_role_bindings "
            "WHERE login_role=%s::name", (name,),
        ).fetchone()[0] == 0
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(dsn)


def test_runtime_role_cannot_read_fence_or_its_evidence(login):
    name, _ = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    permit = grant(name)
    fence.issue(permit)
    for tab in ("privileged_authorization_fences", "privileged_fence_events"):
        with psycopg.connect(RUNTIME) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT count(*) FROM company_configuration." + tab)


def test_sql_row_lock_serializes_revoke_ahead_of_execute(login):
    name, old_dsn = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    permit = grant(name)
    fence.issue(permit)
    ready, finished = Event(), Event()
    result = []

    def worker():
        ready.set()
        try:
            fence.execute(execute_request(permit), new_password="race-new-password-123456")
            result.append("executed")
        except PrivilegedFenceDenied:
            result.append("denied")
        finally:
            finished.set()

    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "SELECT request_id FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s FOR UPDATE", (permit.request_id,),
        )
        thread = Thread(target=worker)
        thread.start()
        assert ready.wait(timeout=5)
        assert not finished.wait(timeout=0.1)
        conn.execute(
            "UPDATE company_configuration.privileged_authorization_fences "
            "SET state='REVOKED',revoked_at=clock_timestamp() "
            "WHERE request_id=%s", (permit.request_id,),
        )
        fence._event(conn, permit.request_id, "tenant-a", "iam", "REVOKED")
    thread.join(timeout=10)
    assert not thread.is_alive() and result == ["denied"]
    with psycopg.connect(old_dsn) as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1


def test_role_change_rolls_back_if_consumption_evidence_cannot_commit(login):
    name, old_dsn = login
    fence = PostgresPrivilegedAuthorizationFence(ADMIN)
    permit = grant(name)
    fence.issue(permit)
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "CREATE FUNCTION company_configuration.reject_consumed_ci() "
            "RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
            "IF NEW.action='CONSUMED' THEN RAISE EXCEPTION 'simulated audit outage'; "
            "END IF; RETURN NEW; END $$"
        )
        conn.execute(
            "CREATE TRIGGER deny_consumption_ci BEFORE INSERT "
            "ON company_configuration.privileged_fence_events FOR EACH ROW "
            "EXECUTE FUNCTION company_configuration.reject_consumed_ci()"
        )
    try:
        with pytest.raises(psycopg.errors.RaiseException, match="simulated audit outage"):
            fence.execute(execute_request(permit), new_password="rolled-back-ci-pass-123456")
        assert audit(permit.request_id) == ("ACTIVE", ["ISSUED"])
        with psycopg.connect(old_dsn) as conn:
            assert conn.execute("SELECT 1").fetchone()[0] == 1
    finally:
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "DROP TRIGGER IF EXISTS deny_consumption_ci "
                "ON company_configuration.privileged_fence_events"
            )
            conn.execute("DROP FUNCTION IF EXISTS company_configuration.reject_consumed_ci()")
