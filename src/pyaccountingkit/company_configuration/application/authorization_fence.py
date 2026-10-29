"""L02-07e: issue a scoped PostgreSQL fence after trusted IAM port checks.

The external identity, approval and policy ports MUST be trusted implementations.
These Python dataclasses are never authentication or approval credentials.
"""
from typing import Protocol

from .fence_contract import PrivilegedFencePermit
from .privileged_operations import (
    ApprovalVerificationPort,
    OperatorIdentityPort,
    PrivilegedAccessDenied,
    PrivilegedPolicyPort,
    PrivilegedRoleRequest,
    TimePort,
    VerifiedApproval,
    VerifiedOperator,
    _aware,
)


class AuthorizationFenceIssuerPort(Protocol):
    def issue(self, permit: PrivilegedFencePermit) -> None: ...


class AuthorizationFenceGrantService:
    """Mint a SQL-local fence after current policy and independent approval.

    External IAM revocations must be propagated to the SQL fence. This service
    does not make a remote IAM and PostgreSQL authorization transaction atomic.
    """

    def __init__(
        self, *, identity: OperatorIdentityPort, approvals: ApprovalVerificationPort,
        policy: PrivilegedPolicyPort, issuer: AuthorizationFenceIssuerPort, clock: TimePort,
    ) -> None:
        self._identity = identity
        self._approvals = approvals
        self._policy = policy
        self._issuer = issuer
        self._clock = clock

    def issue(
        self, request: PrivilegedRoleRequest, *, auth_context: object
    ) -> PrivilegedFencePermit:
        if not isinstance(request, PrivilegedRoleRequest):
            raise TypeError("Privileged role request required")
        actor = self._identity.verify(auth_context)
        if not isinstance(actor, VerifiedOperator) or not actor.actor_id:
            raise PrivilegedAccessDenied("Verified operator required")
        if actor.tenant_id != request.tenant_id:
            raise PrivilegedAccessDenied("Operator tenant mismatch")
        self._policy.require(principal=actor, request=request)
        approval = self._approvals.resolve(reference=request.approval_reference)
        now = self._clock.now()
        if not _aware(now):
            raise ValueError("Trusted aware clock required")
        if not isinstance(approval, VerifiedApproval):
            raise PrivilegedAccessDenied("Independently verified approval required")
        if (
            not approval.approver_id or approval.approver_id == actor.actor_id
            or approval.approval_id != request.approval_reference
            or approval.request_id != request.request_id
            or approval.tenant_id != request.tenant_id
            or approval.login_role != request.login_role
            or approval.operation != request.operation
            or not _aware(approval.issued_at)
            or not _aware(approval.expires_at)
            or not (approval.issued_at <= now < approval.expires_at)
        ):
            raise PrivilegedAccessDenied("Approval denied, expired or self-approved")
        permit = PrivilegedFencePermit(
            request.request_id, request.tenant_id, request.login_role,
            request.operation, actor.actor_id, approval.approver_id,
            approval.approval_id, approval.expires_at,
        )
        self._issuer.issue(permit)
        return permit
