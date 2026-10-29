"""L02-07c secure manual review and second approval revocation check."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    PrivilegedRoleRequest,
    PrivilegedRoleService,
    VerifiedApproval,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.application.privileged_reconciliation import (
    PrivilegedReconciliationService,
)

NOW = datetime(2026, 10, 29, 14, 0, tzinfo=UTC)


class Clock:
    def __init__(self, times=None):
        self.times = list(times or [NOW])

    def now(self):
        return self.times.pop(0) if len(self.times) > 1 else self.times[0]


class Identity:
    def __init__(self, principal=None):
        self.principal = principal or VerifiedOperator("reviewer-1", "tenant-a")

    def verify(self, auth_context):
        if auth_context != "verified":
            raise PrivilegedAccessDenied("Unverified reviewer")
        return self.principal


class ReviewPolicy:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls = 0

    def require_review(self, *, principal, tenant_id):
        self.calls += 1
        if not self.allowed:
            raise PrivilegedAccessDenied("No review grant")


class Reviews:
    def __init__(self):
        self.calls = []

    def mark_stale(self, **kwargs):
        self.calls.append(kwargs)
        return ()


def reviewer(*, identity=None, policy=None, repository=None, clock=None):
    return PrivilegedReconciliationService(
        identity=identity or Identity(), policy=policy or ReviewPolicy(),
        repository=repository or Reviews(), clock=clock or Clock(),
    )


def test_manual_review_must_use_verified_identity_and_authoritative_tenant():
    repo = Reviews()
    service = reviewer(repository=repo)
    with pytest.raises(PrivilegedAccessDenied):
        service.review_stale(auth_context="unverified", tenant_id="tenant-a")
    with pytest.raises(PrivilegedAccessDenied, match="tenant"):
        service.review_stale(auth_context="verified", tenant_id="tenant-b")
    assert not repo.calls


def test_review_deny_by_policy_never_calls_repository():
    repo = Reviews()
    policy = ReviewPolicy(False)
    with pytest.raises(PrivilegedAccessDenied):
        reviewer(repository=repo, policy=policy).review_stale(
            auth_context="verified", tenant_id="tenant-a"
        )
    assert policy.calls == 1 and not repo.calls


def test_review_cutoff_is_bounded_and_scoped():
    repo = Reviews()
    result = reviewer(repository=repo).review_stale(
        auth_context="verified", tenant_id="tenant-a", older_than_seconds=600, limit=5,
    )
    assert result == ()
    assert repo.calls[0] == {
        "tenant_id": "tenant-a", "reviewer_id": "reviewer-1",
        "cutoff": NOW - timedelta(minutes=10), "detected_at": NOW, "limit": 5,
    }


@pytest.mark.parametrize("seconds,limit", [(0, 10), (59, 10), (300, 0), (300, 101)])
def test_invalid_review_delay_or_limit_is_rejected(seconds, limit):
    with pytest.raises(ValueError):
        reviewer().review_stale(
            auth_context="verified", tenant_id="tenant-a",
            older_than_seconds=seconds, limit=limit,
        )


class RoleAudit:
    def __init__(self):
        self.events = []

    def record_intent(self, **kwargs):
        self.events.append("INTENT")

    def record_outcome(self, **kwargs):
        self.events.append(kwargs["outcome"])

    def record_denial(self, **kwargs):
        self.events.append("DENIED")


class RolePolicy:
    def __init__(self, fail_on_second=False):
        self.calls = 0
        self.fail_on_second = fail_on_second

    def require(self, **kwargs):
        self.calls += 1
        if self.fail_on_second and self.calls == 2:
            raise PrivilegedAccessDenied("Grant revoked after INTENT")


class ApprovalProvider:
    def __init__(self, approval, *, revoked_on_second=False):
        self.approval = approval
        self.calls = 0
        self.revoked_on_second = revoked_on_second

    def resolve(self, **kwargs):
        self.calls += 1
        if self.revoked_on_second and self.calls == 2:
            return replace(self.approval, approver_id="revoked-reviewer")
        return self.approval


class Roles:
    def __init__(self):
        self.calls = 0
        self.permits = []

    def issue(self, permit):
        self.permits.append(permit)

    def execute(self, operation, *, new_password=None):
        assert self.permits[-1].request_id == operation.request_id
        self.calls += 1
        return "rotated" if operation.operation == "rotate" else "revoked"


def make_role_service(*, revoke_approval=False, revoke_grant=False, times=None):
    request = PrivilegedRoleRequest(
        uuid4(), "tenant-a", "cc_runtime_test", "rotate", "approval-1", "rotate key"
    )
    approval = VerifiedApproval(
        "approval-1", "checker-1", request.request_id, "tenant-a", request.login_role,
        "rotate", NOW - timedelta(minutes=2), NOW + timedelta(minutes=2),
    )
    audit, roles = RoleAudit(), Roles()
    provider = ApprovalProvider(approval, revoked_on_second=revoke_approval)
    policy = RolePolicy(fail_on_second=revoke_grant)
    service = PrivilegedRoleService(
        identity=Identity(VerifiedOperator("operator-1", "tenant-a")),
        approvals=provider, policy=policy, audit=audit, fence=roles,
        clock=Clock(times),
    )
    return request, service, audit, roles, provider, policy


@pytest.mark.parametrize("revoke_approval,revoke_grant", [(True, False), (False, True)])
def test_revalidation_cancels_privileged_ddl_after_durable_intent(
    revoke_approval, revoke_grant
):
    req, svc, audit, roles, _, _ = make_role_service(
        revoke_approval=revoke_approval, revoke_grant=revoke_grant
    )
    with pytest.raises(PrivilegedAccessDenied, match="changed before DDL"):
        svc.execute(req, auth_context="verified", new_password="longpassword-123456789")
    assert audit.events == ["INTENT", "CANCELLED"]
    assert roles.calls == 0


def test_expired_approval_at_second_check_cancels_before_sql():
    req, svc, audit, roles, _, _ = make_role_service(
        times=[NOW, NOW + timedelta(minutes=4)]
    )
    with pytest.raises(PrivilegedAccessDenied, match="changed before DDL"):
        svc.execute(req, auth_context="verified", new_password="longpassword-123456789")
    assert audit.events == ["INTENT", "CANCELLED"]
    assert roles.calls == 0


def test_valid_second_approval_check_allows_only_one_ddl_call():
    req, svc, audit, roles, provider, policy = make_role_service()
    assert svc.execute(
        req, auth_context="verified", new_password="longpassword-123456789"
    ) == "rotated"
    assert provider.calls == 2 and policy.calls == 2
    assert roles.calls == 1
    assert audit.events == ["INTENT", "SUCCEEDED"]
