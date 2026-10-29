"""L02-07b pure application proof: verified identities, SoD, fail-closed audit."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    PrivilegedAuditIncomplete,
    PrivilegedRoleRequest,
    PrivilegedRoleService,
    VerifiedApproval,
    VerifiedOperator,
)


NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class Identity:
    def __init__(self, result=None):
        self.result = result if result is not None else VerifiedOperator("operator-1", "tenant-a")

    def verify(self, context):
        if context != "verified-transport-context":
            raise PrivilegedAccessDenied("Unverified transport context")
        return self.result


class Approvals:
    def __init__(self, result):
        self.result = result

    def resolve(self, *, reference):
        assert reference == "approval-123"
        return self.result


class Policy:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls = 0

    def require(self, *, principal, request):
        self.calls += 1
        if not self.allowed:
            raise PrivilegedAccessDenied("policy revoked")


class Audit:
    def __init__(self, *, fail_on=None):
        self.events = []
        self.intent_ids = set()
        self.fail_on = fail_on

    def record_intent(self, *, request, actor, approval, recorded_at):
        if self.fail_on == "intent":
            raise OSError("audit unavailable")
        if request.request_id in self.intent_ids:
            raise ValueError("request replay")
        self.intent_ids.add(request.request_id)
        self.events.append(("INTENT", request.tenant_id, actor.actor_id))

    def record_outcome(self, *, request, actor, outcome, recorded_at):
        if self.fail_on == "outcome":
            raise OSError("audit outcome unavailable")
        self.events.append((outcome, request.tenant_id, actor.actor_id))

    def record_denial(self, *, request, actor, code, recorded_at):
        if self.fail_on == "denial":
            raise OSError("denial audit unavailable")
        self.events.append((code, actor.tenant_id, actor.actor_id))


class Roles:
    def __init__(self, failing=False):
        self.calls = []
        self.failing = failing

    def rotate_password(self, *, login_role, expected_tenant, new_password):
        self.calls.append(("rotate", login_role, expected_tenant))
        if self.failing:
            raise OSError("operator failed")
        return "rotated"

    def revoke_login(self, *, login_role, expected_tenant):
        self.calls.append(("revoke", login_role, expected_tenant))
        if self.failing:
            raise OSError("operator failed")
        return "revoked"


@pytest.fixture
def setup():
    request = PrivilegedRoleRequest(
        uuid4(), "tenant-a", "cc_runtime_ops_test", "rotate",
        "approval-123", "emergency credential change",
    )
    approval = VerifiedApproval(
        "approval-123", "reviewer-2", request.request_id, "tenant-a",
        request.login_role, "rotate", NOW - timedelta(minutes=1), NOW + timedelta(hours=1),
    )
    return request, approval


def service(request, approval, *, actor=None, allowed=True, audit=None, roles=None):
    a = audit if audit is not None else Audit()
    r = roles if roles is not None else Roles()
    return (
        PrivilegedRoleService(
            identity=Identity(actor), approvals=Approvals(approval), policy=Policy(allowed),
            audit=a, roles=r, clock=Clock(),
        ),
        a, r,
    )


def test_rotation_succeeds_only_with_independent_approval_and_durable_intent(setup):
    request, approval = setup
    runner, audit, roles = service(request, approval)
    assert "new-password-123456789" not in repr(request)
    assert runner.execute(
        request, auth_context="verified-transport-context", new_password="new-password-123456789"
    ) == "rotated"
    assert audit.events == [
        ("INTENT", "tenant-a", "operator-1"),
        ("SUCCEEDED", "tenant-a", "operator-1"),
    ]
    assert roles.calls == [("rotate", request.login_role, "tenant-a")]


def test_self_approval_denied_even_if_authorized(setup):
    request, approval = setup
    runner, audit, roles = service(request, replace(approval, approver_id="operator-1"))
    with pytest.raises(PrivilegedAccessDenied, match="SOD_VIOLATION"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert audit.events[0][0] == "SOD_VIOLATION"
    assert not roles.calls


@pytest.mark.parametrize("property_name, value", [
    ("tenant_id", "tenant-b"), ("login_role", "cc_runtime_b"),
    ("operation", "revoke"), ("approval_id", "unrelated"),
    ("expires_at", NOW), ("issued_at", NOW + timedelta(minutes=1)),
])
def test_approval_bound_to_exact_operation_and_unexpired(setup, property_name, value):
    request, approval = setup
    runner, audit, roles = service(request, replace(approval, **{property_name: value}))
    with pytest.raises(PrivilegedAccessDenied, match="APPROVAL_INVALID"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert audit.events[0][0] == "APPROVAL_INVALID"
    assert roles.calls == []


def test_policy_revocation_deny_prevents_mutation_and_is_audited(setup):
    request, approval = setup
    runner, audit, roles = service(request, approval, allowed=False)
    with pytest.raises(PrivilegedAccessDenied, match="PERMISSION_DENIED"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert audit.events[0][0] == "PERMISSION_DENIED"
    assert roles.calls == []


def test_mismatched_operator_tenant_audits_authenticated_tenant_only(setup):
    request, approval = setup
    runner, audit, roles = service(request, approval, actor=VerifiedOperator("op", "tenant-b"))
    with pytest.raises(PrivilegedAccessDenied, match="TENANT_MISMATCH"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert audit.events[0] == ("TENANT_MISMATCH", "tenant-b", "op")
    assert not roles.calls


def test_intent_audit_unavailable_fails_closed(setup):
    request, approval = setup
    runner, _, roles = service(request, approval, audit=Audit(fail_on="intent"))
    with pytest.raises(OSError, match="audit unavailable"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert roles.calls == []


def test_denial_audit_unavailable_does_not_allow_unauthorized_action(setup):
    request, approval = setup
    runner, _, roles = service(request, approval, allowed=False,
                               audit=Audit(fail_on="denial"))
    with pytest.raises(OSError, match="denial audit unavailable"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert roles.calls == []


def test_operator_failure_records_failed_outcome(setup):
    request, approval = setup
    runner, audit, roles = service(request, approval, roles=Roles(failing=True))
    with pytest.raises(OSError, match="operator failed"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert [x[0] for x in audit.events] == ["INTENT", "FAILED"]
    assert roles.calls


def test_outcome_audit_failure_never_claims_success(setup):
    request, approval = setup
    runner, _, roles = service(request, approval, audit=Audit(fail_on="outcome"))
    with pytest.raises(PrivilegedAuditIncomplete, match="may have completed"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="new-password-123456789")
    assert roles.calls


def test_duplicate_request_id_fails_before_operator_second_call(setup):
    request, approval = setup
    runner, _, roles = service(request, approval)
    runner.execute(request, auth_context="verified-transport-context",
                   new_password="new-password-123456789")
    with pytest.raises(ValueError, match="request replay"):
        runner.execute(request, auth_context="verified-transport-context",
                       new_password="different-password-123456789")
    assert len(roles.calls) == 1


def test_revoke_rejects_password_and_can_execute_without_secret(setup):
    req, approval = setup
    req = replace(req, operation="revoke")
    approval = replace(approval, operation="revoke")
    runner, audit, roles = service(req, approval)
    with pytest.raises(PrivilegedAccessDenied, match="UNEXPECTED_CREDENTIAL"):
        runner.execute(req, auth_context="verified-transport-context",
                       new_password="should-not-pass-123456")
    assert runner.execute(req, auth_context="verified-transport-context") == "revoked"
    assert [e[0] for e in audit.events] == ["UNEXPECTED_CREDENTIAL", "INTENT", "SUCCEEDED"]


def test_unverified_transport_cannot_mutate_role(setup):
    request, approval = setup
    runner, _, roles = service(request, approval)
    with pytest.raises(PrivilegedAccessDenied, match="Unverified transport"):
        runner.execute(request, auth_context="anonymous", new_password="secure-long-secret-123")
    assert roles.calls == []
