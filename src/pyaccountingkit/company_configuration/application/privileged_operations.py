"""L02-07b candidate: two-person authorization for privileged SQL role operations.

Provider-supplied identities and approvals MUST be cryptographically or otherwise
independently verified by trusted adapters. These dataclasses are not credentials.
The operation is only approved when a durable INTENT audit has been committed.
The outcome is separately audited; this is NOT an atomic SQL change/audit proof.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from .fence_contract import (
    FencedRoleOperation,
    PrivilegedFencePermit,
    PrivilegedFencedExecutorPort,
)


class PrivilegedAccessDenied(PermissionError):
    """Critical privileged action is denied without attempting role mutation."""


class PrivilegedAuditIncomplete(RuntimeError):
    """A role operation may have happened but audit completion failed."""


@dataclass(frozen=True, slots=True)
class PrivilegedRoleRequest:
    request_id: UUID
    tenant_id: str
    login_role: str
    operation: str
    approval_reference: str
    justification: str

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, UUID):
            raise ValueError("A typed UUID request ID is required")
        if self.operation not in ("rotate", "revoke"):
            raise ValueError("Only tenant login rotation/revocation is supported")
        for value in (
            self.tenant_id, self.login_role, self.approval_reference, self.justification
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError("Canonical nonempty request fields required")


@dataclass(frozen=True, slots=True)
class VerifiedOperator:
    """The trusted AuthN adapter creates this; never deserialize it from API JSON."""

    actor_id: str
    tenant_id: str


@dataclass(frozen=True, slots=True)
class VerifiedApproval:
    """Returned by a trusted approval verifier, NEVER client-supplied claims."""

    approval_id: str
    approver_id: str
    request_id: UUID
    tenant_id: str
    login_role: str
    operation: str
    issued_at: datetime
    expires_at: datetime


class OperatorIdentityPort(Protocol):
    def verify(self, context: object) -> VerifiedOperator: ...


class ApprovalVerificationPort(Protocol):
    def resolve(self, *, reference: str) -> VerifiedApproval: ...


class PrivilegedPolicyPort(Protocol):
    def require(self, *, principal: VerifiedOperator, request: PrivilegedRoleRequest) -> None: ...


class PrivilegedAuditPort(Protocol):
    def record_intent(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        approval: VerifiedApproval, recorded_at: datetime,
    ) -> None: ...

    def record_outcome(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        outcome: str, recorded_at: datetime,
    ) -> None: ...

    def record_denial(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        code: str, recorded_at: datetime,
    ) -> None: ...


class TimePort(Protocol):
    def now(self) -> datetime: ...


def _aware(value: datetime) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


class PrivilegedRoleService:
    """A strict SoD gate requiring a scoped SQL fence before role DDL.

    The service assumes no external request can bypass it to access the admin DSN.
    The policy port must check the authoritative current grants on every call.
    Denial/intent audit storage failures prevent the privileged operation.
    A result audit failure is not falsely reported as success.
    """

    def __init__(
        self, *, identity: OperatorIdentityPort,
        approvals: ApprovalVerificationPort, policy: PrivilegedPolicyPort,
        audit: PrivilegedAuditPort, fence: PrivilegedFencedExecutorPort, clock: TimePort,
    ) -> None:
        self._identity = identity
        self._approvals = approvals
        self._policy = policy
        self._audit = audit
        if not callable(getattr(fence, 'issue', None)) or not callable(
            getattr(fence, 'execute', None)
        ):
            raise PrivilegedAccessDenied('Mandatory fenced executor required')
        self._fence = fence
        self._clock = clock

    def execute(
        self, request: PrivilegedRoleRequest, *, auth_context: object,
        new_password: str | None = None,
    ) -> object:
        """No request object contains a password; do not serialize password arguments."""
        if not isinstance(request, PrivilegedRoleRequest):
            raise TypeError("PrivilegedRoleRequest required")
        actor = self._identity.verify(auth_context)
        if not isinstance(actor, VerifiedOperator):
            raise PrivilegedAccessDenied("Verified operator required")
        now = self._clock.now()
        if not _aware(now):
            raise ValueError("Trusted aware clock required")

        def deny(code: str) -> None:
            # Use authenticated tenant as source of identity, not requested scope.
            self._audit.record_denial(request=request, actor=actor, code=code, recorded_at=now)
            raise PrivilegedAccessDenied(code)

        if not actor.actor_id or not actor.tenant_id or actor.tenant_id != request.tenant_id:
            deny("TENANT_MISMATCH")
        if request.operation == "rotate" and (
            not isinstance(new_password, str) or len(new_password) < 16
        ):
            deny("CREDENTIAL_REQUIRED")
        if request.operation == "revoke" and new_password is not None:
            deny("UNEXPECTED_CREDENTIAL")
        try:
            self._policy.require(principal=actor, request=request)
        except PrivilegedAccessDenied:
            deny("PERMISSION_DENIED")
        approval = self._approvals.resolve(reference=request.approval_reference)
        if not isinstance(approval, VerifiedApproval):
            deny("APPROVAL_INVALID")
        if (
            approval.approver_id == actor.actor_id
            or not approval.approver_id
        ):
            deny("SOD_VIOLATION")
        if (
            approval.request_id != request.request_id
            or approval.tenant_id != request.tenant_id
            or approval.login_role != request.login_role
            or approval.operation != request.operation
            or not approval.approval_id
            or approval.approval_id != request.approval_reference
            or not _aware(approval.issued_at)
            or not _aware(approval.expires_at)
            or not (approval.issued_at <= now < approval.expires_at)
        ):
            deny("APPROVAL_INVALID")
        # A committed append-only INTENT is mandatory before the role DDL.
        # A duplicated request id fails at the DB unique intent index.
        self._audit.record_intent(
            request=request, actor=actor, approval=approval, recorded_at=now
        )
        # Revalidate against *current* authorization state immediately before
        # execution. The IAM/approval provider must resolve revocations on every
        # call, not cache the initial positive decision. This is still not an
        # atomic authorization lease across external IAM and PostgreSQL DDL.
        try:
            self._policy.require(principal=actor, request=request)
            current = self._approvals.resolve(reference=request.approval_reference)
            fresh = self._clock.now()
            if (
                not isinstance(current, VerifiedApproval)
                or current != approval
                or not _aware(fresh)
                or not (current.issued_at <= fresh < current.expires_at)
            ):
                raise PrivilegedAccessDenied("APPROVAL_REVOKED_OR_CHANGED")
        except Exception as exc:
            try:
                self._audit.record_outcome(
                    request=request, actor=actor, outcome="CANCELLED",
                    recorded_at=self._clock.now(),
                )
            except Exception as audit_exc:
                raise PrivilegedAuditIncomplete(
                    "Pre-mutation revalidation failed and final audit is unavailable"
                ) from audit_exc
            raise PrivilegedAccessDenied("Privileged grant or approval changed before DDL") from exc
        try:
            # The service never calls direct owner-side role mutation.
            # Issue only after rechecking the authoritative approval.
            self._fence.issue(
                PrivilegedFencePermit(
                    request.request_id, request.tenant_id, request.login_role,
                    request.operation, actor.actor_id, approval.approver_id,
                    approval.approval_id, approval.expires_at,
                )
            )
            result = self._fence.execute(
                FencedRoleOperation(
                    request.request_id, request.tenant_id, request.login_role,
                    request.operation, actor.actor_id, approval.approval_id,
                ),
                new_password=new_password,
            )
        except Exception:
            try:
                self._audit.record_outcome(
                    request=request, actor=actor, outcome="FAILED", recorded_at=self._clock.now()
                )
            except Exception as exc:
                raise PrivilegedAuditIncomplete(
                    "Privileged operation failed; completion audit is unavailable"
                ) from exc
            raise
        try:
            self._audit.record_outcome(
                request=request, actor=actor, outcome="SUCCEEDED", recorded_at=self._clock.now()
            )
        except Exception as exc:
            raise PrivilegedAuditIncomplete(
                "Privileged operation may have completed; outcome audit unavailable"
            ) from exc
        return result
