"""L02-07g: a narrow PostgreSQL LOGIN cannot perform owner-side role DDL."""
# ruff: noqa: E402

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql
from psycopg.conninfo import make_conninfo

from pyaccountingkit.company_configuration.application.fence_contract import (
    FencedRoleOperation,
    PrivilegedFencePermit,
)
from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedRoleRequest,
    PrivilegedRoleService,
    VerifiedApproval,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.delegated_control_plane import (
    DelegatedPrivilegedControlPlane,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.privileged_audit import (
    PostgresPrivilegedAudit,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
DELEGATE = os.getenv("CC_PG_CONTROL_PLANE_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and DELEGATE and RUNTIME),
    reason="Delegated control-plane PostgreSQL credentials required",
)


@pytest.fixture
def account():
    role = "cc_runtime_control_" + uuid4().hex[:9]
    password = "ci-old-secret-control-plane-123456"
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Identifier(role), sql.Literal(password))
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,'tenant-a')", (role,)
        )
    try:
        yield role, make_conninfo(RUNTIME, user=role, password=password)
    finally:
        with psycopg.connect(ADMIN, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE usename=%s AND pid<>pg_backend_pid()", (role,)
            )
            conn.execute(
                "TRUNCATE company_configuration.privileged_fence_events, "
                "company_configuration.privileged_authorization_fences"
            )
            conn.execute(
                "DELETE FROM company_configuration.tenant_role_bindings "
                "WHERE login_role=%s::name", (role,)
            )
            conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))


def permit(role, operation="rotate"):
    return PrivilegedFencePermit(
        uuid4(), "tenant-a", role, operation, "actor-one", "checker-two",
        "approved-external-reference", datetime.now(UTC) + timedelta(minutes=5),
    )


def run(authorization):
    return FencedRoleOperation(
        authorization.request_id, authorization.tenant_id,
        authorization.login_role, authorization.operation,
        authorization.actor_id, authorization.approval_id,
    )


def test_control_plane_login_has_no_createrole_superuser_or_bypass():
    with psycopg.connect(DELEGATE) as conn:
        role = conn.execute(
            "SELECT rolcanlogin,rolsuper,rolcreaterole,rolbypassrls,rolcreatedb "
            "FROM pg_roles WHERE rolname=session_user"
        ).fetchone()
        assert role == (True, False, False, False, False)
        assert conn.execute("SELECT session_user").fetchone()[0] == "cc_control_plane"


def test_control_plane_cannot_access_fence_tables_directly_or_mutate_role(account):
    role, _ = account
    with psycopg.connect(DELEGATE) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT * FROM company_configuration.privileged_authorization_fences"
            )
    with psycopg.connect(DELEGATE) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(sql.SQL("ALTER ROLE {} NOLOGIN").format(sql.Identifier(role)))
    with psycopg.connect(DELEGATE) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT * FROM company_configuration.tenant_role_bindings"
            )


def test_runtime_role_cannot_call_delegated_control_plane_functions(account):
    authorization = permit(account[0])
    with psycopg.connect(RUNTIME) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_issue_fence(%s,%s,%s,%s,%s,%s,%s,%s)",
                (authorization.request_id,authorization.tenant_id,
                 authorization.login_role,authorization.operation,authorization.actor_id,
                 authorization.approver_id,authorization.approval_id,
                 authorization.expires_at),
            )


def test_delegated_fence_rotates_and_is_consumed_once(account):
    role, old_dsn = account
    control = DelegatedPrivilegedControlPlane(DELEGATE)
    authorization = permit(role)
    control.issue(authorization)
    new_secret = "new-delegated-control-plane-secret-12345"
    result = control.execute(run(authorization), new_password=new_secret)
    assert result.operation == "rotate"
    assert "password" not in repr(control).lower()
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT state FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s", (authorization.request_id,),
        ).fetchone()[0] == "CONSUMED"
        assert [x[0] for x in conn.execute(
            "SELECT action FROM company_configuration.privileged_fence_events "
            "WHERE request_id=%s ORDER BY recorded_at", (authorization.request_id,),
        ).fetchall()] == ["ISSUED", "CONSUMED"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        control.execute(run(authorization), new_password="another-delegated-secret-12345")
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(old_dsn)
    with psycopg.connect(make_conninfo(
        RUNTIME, user=role, password=new_secret,
    )) as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1


def test_revoked_delegated_permit_cannot_change_role(account):
    role, old_dsn = account
    control = DelegatedPrivilegedControlPlane(DELEGATE)
    authorization = permit(role)
    control.issue(authorization)
    assert control.revoke(
        request_id=authorization.request_id, tenant_id="tenant-a", revoked_by="iam",
    )
    assert not control.revoke(
        request_id=authorization.request_id, tenant_id="tenant-a", revoked_by="iam",
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        control.execute(run(authorization), new_password="invalid-new-secret-123456")
    with psycopg.connect(old_dsn) as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1


def test_delegated_scope_rejects_impersonated_tenant_and_actor(account):
    role, _ = account
    control = DelegatedPrivilegedControlPlane(DELEGATE)
    authorization = permit(role)
    control.issue(authorization)
    for mutation in (
        replace(run(authorization), tenant_id="tenant-b"),
        replace(run(authorization), actor_id="impersonator"),
        replace(run(authorization), approval_id="other-approval"),
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            control.execute(mutation, new_password="candidate-secret-123456789")


def test_delegated_revoke_disables_login_and_clears_binding(account):
    role, old_dsn = account
    control = DelegatedPrivilegedControlPlane(DELEGATE)
    authorization = permit(role, "revoke")
    control.issue(authorization)
    assert control.execute(run(authorization)).operation == "revoke"
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.tenant_role_bindings "
            "WHERE login_role=%s::name", (role,),
        ).fetchone()[0] == 0
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(old_dsn)


def test_main_service_uses_delegated_fence_with_separate_owner_audit(account):
    """DDL uses delegated role; the separate legacy audit still owns its DSN."""
    role, _ = account
    request_id = uuid4()
    request = PrivilegedRoleRequest(
        request_id, "tenant-a", role, "rotate", "approval-e2e",
        "delegated control plane verification",
    )
    now = datetime.now(UTC)
    approval = VerifiedApproval(
        request.approval_reference, "checker-b", request_id, "tenant-a", role,
        "rotate", now - timedelta(minutes=1), now + timedelta(minutes=5),
    )

    class Identity:
        def verify(self, context):
            assert context == "trusted-internal-context"
            return VerifiedOperator("operator-a", "tenant-a")

    class Approvals:
        def resolve(self, *, reference):
            assert reference == request.approval_reference
            return approval

    class Policy:
        def require(self, *, principal, request):
            assert principal.tenant_id == request.tenant_id

    class Clock:
        def now(self):
            return datetime.now(UTC)

    service = PrivilegedRoleService(
        identity=Identity(), approvals=Approvals(), policy=Policy(),
        audit=PostgresPrivilegedAudit(ADMIN),
        fence=DelegatedPrivilegedControlPlane(DELEGATE), clock=Clock(),
    )
    result = service.execute(
        request, auth_context="trusted-internal-context",
        new_password="delegated-end-to-end-rotation-secret-123456",
    )
    assert result.operation == "rotate"
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT state FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s", (request_id,),
        ).fetchone()[0] == "CONSUMED"
        phases = [r[0] for r in conn.execute(
            "SELECT phase FROM company_configuration.privileged_operation_audit "
            "WHERE request_id=%s", (request_id,),
        ).fetchall()]
        assert sorted(phases) == ["INTENT", "SUCCEEDED"]


def test_control_plane_rejects_owner_superuser_target():
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        DelegatedPrivilegedControlPlane(DELEGATE).issue(permit("postgres"))
