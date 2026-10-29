"""L02-07h: separately authenticated writer has no raw owner capabilities."""

# ruff: noqa: E402

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql
from psycopg.conninfo import make_conninfo

from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedRoleRequest,
    VerifiedApproval,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.delegated_control_plane import (
    DelegatedPrivilegedControlPlane,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.delegated_privileged_audit import (
    DelegatedPrivilegedAudit,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.restricted_control_plane import (
    PrivilegedCompositionDenied,
    build_restricted_privileged_service,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
AUDIT = os.getenv("CC_PG_PRIVILEGED_AUDIT_DSN")
CONTROL = os.getenv("CC_PG_CONTROL_PLANE_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and AUDIT and CONTROL and RUNTIME),
    reason="PostgreSQL privileged audit and delegated control credentials required",
)


@pytest.fixture
def role():
    name = "cc_runtime_audit_" + uuid4().hex[:10]
    old_password = "ci-audit-initial-credential-123456"
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Identifier(name), sql.Literal(old_password))
        )
        conn.execute(
            "INSERT INTO company_configuration.tenant_role_bindings "
            "(login_role,tenant_id) VALUES (%s,'tenant-a')", (name,),
        )
    try:
        yield name, make_conninfo(RUNTIME, user=name, password=old_password)
    finally:
        with psycopg.connect(ADMIN, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE usename=%s AND pid<>pg_backend_pid()", (name,),
            )
            conn.execute(
                "TRUNCATE company_configuration.privileged_fence_events, "
                "company_configuration.privileged_authorization_fences"
            )
            conn.execute(
                "DELETE FROM company_configuration.tenant_role_bindings "
                "WHERE login_role=%s::name", (name,),
            )
            conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(name)))


def make_request(name, operation="rotate"):
    request = PrivilegedRoleRequest(
        uuid4(), "tenant-a", name, operation, "approval-writer-1",
        "independent audit test",
    )
    now = datetime.now(UTC)
    approval = VerifiedApproval(
        request.approval_reference, "checker-2", request.request_id,
        "tenant-a", name, operation, now - timedelta(minutes=1),
        now + timedelta(minutes=5),
    )
    return request, approval


def audit_rows(request_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT phase,actor_id,approver_id,approval_id "
            "FROM company_configuration.privileged_operation_audit "
            "WHERE request_id=%s ORDER BY recorded_at", (request_id,),
        ).fetchall()


def test_writer_has_only_narrow_execute_grant():
    with psycopg.connect(AUDIT) as conn:
        role = conn.execute(
            "SELECT rolcanlogin,rolsuper,rolcreaterole,rolbypassrls "
            "FROM pg_roles WHERE rolname=session_user"
        ).fetchone()
        assert role == (True, False, False, False)
        assert conn.execute("SELECT session_user").fetchone()[0] == "cc_privileged_audit"
    with psycopg.connect(AUDIT) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.privileged_operation_audit")
    with psycopg.connect(AUDIT) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM company_configuration.privileged_operation_audit")
    with psycopg.connect(AUDIT) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.privileged_authorization_fences")
    with psycopg.connect(CONTROL) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_append_privileged_audit("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (uuid4(), uuid4(), "tenant-a", "role", "actor", None, None,
                 "rotate", "DENIED", "PERMISSION_DENIED"),
            )
    with psycopg.connect(RUNTIME) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_append_privileged_audit("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (uuid4(), uuid4(), "tenant-a", "role", "actor", None, None,
                 "rotate", "DENIED", "PERMISSION_DENIED"),
            )


def test_durable_denial_from_restricted_writer(role):
    name, _ = role
    request, _ = make_request(name)
    audit = DelegatedPrivilegedAudit(AUDIT)
    audit.record_denial(
        request=request, actor=VerifiedOperator("actor-1", "tenant-a"),
        code="PERMISSION_DENIED", recorded_at=datetime.now(UTC),
    )
    assert [r[0] for r in audit_rows(request.request_id)] == ["DENIED"]
    assert "cc_testing_only" not in repr(audit)


def test_intent_and_failure_carry_original_approval_and_disallow_replay(role):
    request, approval = make_request(role[0])
    writer = DelegatedPrivilegedAudit(AUDIT)
    actor = VerifiedOperator("actor-1", "tenant-a")
    writer.record_intent(
        request=request, actor=actor, approval=approval,
        recorded_at=datetime.now(UTC),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        writer.record_intent(
            request=request, actor=actor, approval=approval,
            recorded_at=datetime.now(UTC),
        )
    writer.record_outcome(
        request=request, actor=actor, outcome="FAILED",
        recorded_at=datetime.now(UTC),
    )
    assert audit_rows(request.request_id) == [
        ("INTENT", "actor-1", "checker-2", request.approval_reference),
        ("FAILED", "actor-1", "checker-2", request.approval_reference),
    ]
    with pytest.raises(psycopg.errors.UniqueViolation):
        writer.record_outcome(
            request=request, actor=actor, outcome="CANCELLED",
            recorded_at=datetime.now(UTC),
        )


def test_success_without_consumed_exact_fence_is_rejected(role):
    request, approval = make_request(role[0])
    writer = DelegatedPrivilegedAudit(AUDIT)
    actor = VerifiedOperator("actor-1", "tenant-a")
    writer.record_intent(
        request=request, actor=actor, approval=approval,
        recorded_at=datetime.now(UTC),
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        writer.record_outcome(
            request=request, actor=actor, outcome="SUCCEEDED",
            recorded_at=datetime.now(UTC),
        )
    assert [r[0] for r in audit_rows(request.request_id)] == ["INTENT"]


def test_wrong_actor_tenant_and_phase_cannot_complete_intent(role):
    request, approval = make_request(role[0])
    writer = DelegatedPrivilegedAudit(AUDIT)
    writer.record_intent(
        request=request, actor=VerifiedOperator("actor-1", "tenant-a"),
        approval=approval, recorded_at=datetime.now(UTC),
    )
    for actor in (
        VerifiedOperator("forged-actor", "tenant-a"),
        VerifiedOperator("actor-1", "tenant-b"),
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            writer.record_outcome(
                request=request, actor=actor, outcome="FAILED",
                recorded_at=datetime.now(UTC),
            )
    with pytest.raises(ValueError):
        writer.record_outcome(
            request=request, actor=VerifiedOperator("actor-1", "tenant-a"),
            outcome="UNKNOWN", recorded_at=datetime.now(UTC),
        )


def test_main_service_uses_only_two_narrow_dsn_adapters(role):
    name, old_dsn = role
    request, approval = make_request(name)

    class Identity:
        def verify(self, context):
            assert context == "trusted-internal"
            return VerifiedOperator("operator-1", "tenant-a")

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

    service = build_restricted_privileged_service(
        identity=Identity(), approvals=Approvals(), policy=Policy(), clock=Clock(),
        audit_writer_dsn=AUDIT, control_plane_dsn=CONTROL,
    )
    result = service.execute(
        request, auth_context="trusted-internal",
        new_password="new-ci-delegated-audit-secret-123456",
    )
    assert result.operation == "rotate"
    assert audit_rows(request.request_id) == [
        ("INTENT", "operator-1", "checker-2", request.approval_reference),
        ("SUCCEEDED", "operator-1", "checker-2", request.approval_reference),
    ]
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(old_dsn)


def test_unverified_self_approval_is_rejected_by_sql_endpoint(role):
    request, _ = make_request(role[0])
    with psycopg.connect(AUDIT) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_append_privileged_audit("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (uuid4(), request.request_id, "tenant-a", request.login_role,
                 "actor-1", "actor-1", "approval-id", "rotate", "INTENT", "APPROVED"),
            )


def test_composition_rejects_admin_runtime_and_swapped_sql_credentials():
    for audit_dsn, fence_dsn in (
        (ADMIN, CONTROL), (AUDIT, ADMIN), (RUNTIME, CONTROL),
        (CONTROL, AUDIT), (AUDIT, AUDIT),
    ):
        with pytest.raises(PrivilegedCompositionDenied):
            build_restricted_privileged_service(
                audit_writer_dsn=audit_dsn, control_plane_dsn=fence_dsn,
                identity=object(), approvals=object(),
                policy=object(), clock=object(),
            )
