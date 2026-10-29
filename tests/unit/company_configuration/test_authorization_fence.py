"""Pure application proof of scoped, independently approved SQL fence issuance."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.authorization_fence import (
    AuthorizationFenceGrantService,
    PrivilegedFencePermit,
)
from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    PrivilegedRoleRequest,
    VerifiedApproval,
    VerifiedOperator,
)

NOW = datetime(2026, 10, 29, 17, 0, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class Identity:
    def verify(self, context):
        if context != "trusted":
            raise PrivilegedAccessDenied("Unverified identity")
        return VerifiedOperator("operator-a", "tenant-a")


class Policy:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def require(self, *, principal, request):
        if not self.allowed:
            raise PrivilegedAccessDenied("Grant absent")


class Approval:
    def __init__(self, result):
        self.result = result

    def resolve(self, *, reference):
        return self.result


class Issuer:
    def __init__(self):
        self.permits = []

    def issue(self, permit):
        self.permits.append(permit)


@pytest.fixture
def context():
    request = PrivilegedRoleRequest(
        uuid4(), "tenant-a", "cc_runtime_fence_target", "rotate",
        "approval-123", "test SQL-side revocation",
    )
    approval = VerifiedApproval(
        request.approval_reference, "checker-b", request.request_id, "tenant-a",
        request.login_role, "rotate",
        NOW - timedelta(minutes=1), NOW + timedelta(minutes=2),
    )
    return request, approval


def runner(approval, *, allowed=True):
    issuer = Issuer()
    service = AuthorizationFenceGrantService(
        identity=Identity(), approvals=Approval(approval), policy=Policy(allowed),
        issuer=issuer, clock=Clock(),
    )
    return service, issuer


def test_trusted_scoped_grant_is_issued_once(context):
    request, approval = context
    svc, out = runner(approval)
    permit = svc.issue(request, auth_context="trusted")
    assert out.permits == [permit]
    assert permit.request_id == request.request_id
    assert permit.actor_id == "operator-a" and permit.approver_id == "checker-b"


@pytest.mark.parametrize("field,value", [
    ("approver_id", "operator-a"),
    ("tenant_id", "tenant-b"),
    ("login_role", "cc_runtime_different"),
    ("operation", "revoke"),
    ("approval_id", "wrong"),
    ("expires_at", NOW),
    ("issued_at", NOW + timedelta(minutes=1)),
    ("request_id", uuid4()),
])
def test_self_approval_expired_or_foreign_grant_denied(context, field, value):
    request, approval = context
    svc, issuer = runner(replace(approval, **{field: value}))
    with pytest.raises(PrivilegedAccessDenied):
        svc.issue(request, auth_context="trusted")
    assert issuer.permits == []


def test_unverified_identity_denied_before_mint(context):
    request, approval = context
    svc, issuer = runner(approval)
    with pytest.raises(PrivilegedAccessDenied):
        svc.issue(request, auth_context="not-trusted")
    assert issuer.permits == []


def test_revoked_policy_denied_before_mint(context):
    request, approval = context
    svc, issuer = runner(approval, allowed=False)
    with pytest.raises(PrivilegedAccessDenied):
        svc.issue(request, auth_context="trusted")
    assert issuer.permits == []


def test_foreign_tenant_denied_before_mint(context):
    request, approval = context
    svc, issuer = runner(approval)
    with pytest.raises(PrivilegedAccessDenied):
        svc.issue(replace(request, tenant_id="tenant-b"), auth_context="trusted")
    assert issuer.permits == []


def test_permit_rejects_naive_expiry_and_same_actor(context):
    request, approval = context
    with pytest.raises(ValueError):
        PrivilegedFencePermit(
            request.request_id, "tenant-a", request.login_role, "rotate",
            "same", "same", "approval-123", approval.expires_at,
        )
    with pytest.raises(ValueError):
        PrivilegedFencePermit(
            request.request_id, "tenant-a", request.login_role, "rotate",
            "actor", "checker", "approval-123", approval.expires_at.replace(tzinfo=None),
        )
