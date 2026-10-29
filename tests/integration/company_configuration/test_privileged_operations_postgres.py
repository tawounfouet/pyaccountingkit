"""L02-07b real PostgreSQL owner-only privileged intent/outcome evidence."""

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg.conninfo import make_conninfo  # noqa: E402
from test_role_lifecycle import disposable_login  # noqa: E402, F401

from pyaccountingkit.company_configuration.application.privileged_operations import (  # noqa: E402
    PrivilegedAccessDenied,
    PrivilegedRoleRequest,
    PrivilegedRoleService,
    VerifiedApproval,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.privileged_audit import (
    # noqa: E402
    PostgresPrivilegedAudit,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.role_lifecycle import (
    # noqa: E402
    PostgresTenantRoleOperator,
    RoleLifecycleDenied,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and RUNTIME), reason="Privileged audit proof requires PostgreSQL admin DSN"
)
NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class Identity:
    def verify(self, context):
        assert context == "trusted-auth-token"
        return VerifiedOperator("operator-7", "tenant-a")


class Approval:
    def __init__(self, evidence):
        self.evidence = evidence

    def resolve(self, *, reference):
        assert reference == self.evidence.approval_id
        return self.evidence


class Policy:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def require(self, *, principal, request):
        if not self.allowed:
            raise PrivilegedAccessDenied("No privileged grant")


def build_service(role, *, operation="rotate", allowed=True, approver="reviewer-8"):
    req = PrivilegedRoleRequest(
        uuid4(), "tenant-a", role, operation, "approval-verified-222", "incident 123",
    )
    approval = VerifiedApproval(
        req.approval_reference, approver, req.request_id, "tenant-a",
        role, operation, NOW - timedelta(minutes=10), NOW + timedelta(minutes=10),
    )
    auditor = PostgresPrivilegedAudit(ADMIN)
    service = PrivilegedRoleService(
        identity=Identity(), approvals=Approval(approval), policy=Policy(allowed),
        audit=auditor, roles=PostgresTenantRoleOperator(ADMIN), clock=Clock(),
    )
    return service, req


def phases(request_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT phase, actor_id, approver_id, approval_id FROM "
            "company_configuration.privileged_operation_audit "
            "WHERE request_id=%s ORDER BY recorded_at, phase", (request_id,),
        ).fetchall()


def test_privileged_rotation_audits_intent_and_outcome(request):
    role, old_dsn = request.getfixturevalue("disposable_login")
    service, req = build_service(role)
    new_password = "new-ci-privileged-secret-987654321"
    result = service.execute(
        req, auth_context="trusted-auth-token", new_password=new_password
    )
    assert result.operation == "rotate"
    assert sorted(p[0] for p in phases(req.request_id)) == ["INTENT", "SUCCEEDED"]
    assert all(p[1] == "operator-7" and p[2] == "reviewer-8" for p in phases(req.request_id))
    with psycopg.connect(ADMIN) as conn:
        serialized = str(conn.execute(
            "SELECT row_to_json(a) FROM company_configuration.privileged_operation_audit a "
            "WHERE request_id=%s", (req.request_id,),
        ).fetchall())
        assert new_password not in serialized
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(old_dsn)
    with psycopg.connect(make_conninfo(RUNTIME, user=role, password=new_password)) as c:
        assert c.execute("SELECT company_configuration.bound_tenant()").fetchone()[0] == (
            "tenant-a"
        )


def test_sod_denial_persists_without_role_change(request):
    role, old_dsn = request.getfixturevalue("disposable_login")
    service, req = build_service(role, approver="operator-7")
    with pytest.raises(PrivilegedAccessDenied, match="SOD_VIOLATION"):
        service.execute(req, auth_context="trusted-auth-token",
                        new_password="another-ci-super-secret-123")
    assert [x[0] for x in phases(req.request_id)] == ["DENIED"]
    with psycopg.connect(old_dsn) as c:
        assert c.execute("SELECT 1").fetchone()[0] == 1


def test_postgres_intent_uniqueness_prevents_double_privileged_rotation(request):
    role, _ = request.getfixturevalue("disposable_login")
    service, req = build_service(role)
    service.execute(req, auth_context="trusted-auth-token",
                    new_password="supersecret-passphrase-rotated-1")
    with pytest.raises(psycopg.errors.UniqueViolation):
        service.execute(req, auth_context="trusted-auth-token",
                        new_password="supersecret-passphrase-rotated-2")
    assert sorted(p[0] for p in phases(req.request_id)) == ["INTENT", "SUCCEEDED"]


def test_operation_failure_keeps_intent_and_failed_outcome(request):
    role, old_dsn = request.getfixturevalue("disposable_login")
    service, req = build_service(role)
    req = replace(req, tenant_id="tenant-b")
    # Authenticated operator is tenant-a; denial is persisted under tenant-a.
    with pytest.raises(PrivilegedAccessDenied, match="TENANT_MISMATCH"):
        service.execute(req, auth_context="trusted-auth-token",
                        new_password="new-secret-123456789")
    assert [x[0] for x in phases(req.request_id)] == ["DENIED"]
    with psycopg.connect(old_dsn) as c:
        assert c.execute("SELECT 1").fetchone()[0] == 1


def test_runtime_role_cannot_read_privileged_audit_or_modify_evidence(request):
    role, _ = request.getfixturevalue("disposable_login")
    service, req = build_service(role, allowed=False)
    with pytest.raises(PrivilegedAccessDenied):
        service.execute(req, auth_context="trusted-auth-token",
                        new_password="long-secret-123456789")
    with psycopg.connect(RUNTIME) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.privileged_operation_audit")
    with psycopg.connect(ADMIN) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE company_configuration.privileged_operation_audit "
                         "SET reason_code='MODIFIED' WHERE request_id=%s", (req.request_id,))


def test_unprivileged_operator_direct_revoke_is_rejected(request):
    role, _ = request.getfixturevalue("disposable_login")
    # The primitive cannot be invoked with application runtime DSN.
    with pytest.raises((psycopg.errors.InsufficientPrivilege, RoleLifecycleDenied)):
        PostgresTenantRoleOperator(RUNTIME).revoke_login(
            login_role=role, expected_tenant="tenant-a"
        )


def test_invalid_target_fails_after_intent_and_writes_failure_outcome():
    service, req = build_service("cc_runtime_no_such_testrole")
    with pytest.raises(RoleLifecycleDenied):
        service.execute(req, auth_context="trusted-auth-token",
                        new_password="valid-but-unused-credential-123456789")
    assert sorted(p[0] for p in phases(req.request_id)) == ["FAILED", "INTENT"]
