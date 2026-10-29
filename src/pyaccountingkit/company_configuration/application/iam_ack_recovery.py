"""Tenant-bound manual ACK DEAD-letter recovery with independent approval.

The identity, current permission and approval ports MUST be independently
verified implementations. Dataclasses are not credentials or signed evidence.
Re-drive does NOT undo an ALREADY_CONSUMED SQL role operation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from .privileged_operations import PrivilegedAccessDenied, VerifiedOperator


@dataclass(frozen=True, slots=True)
class DeadAckDelivery:
    event_id: UUID
    request_id: UUID
    tenant_id: str
    disposition: str
    attempts: int
    redrive_count: int
    error_code: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RedriveRequest:
    event_id: UUID
    request_id: UUID
    tenant_id: str
    approval_reference: str
    evidence_reference: str
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, UUID) or not isinstance(self.request_id, UUID):
            raise ValueError("Typed request and event UUIDs required")
        for field in (self.tenant_id, self.approval_reference, self.evidence_reference):
            if not isinstance(field, str) or not field or field.strip() != field:
                raise ValueError("Canonical scoped recovery evidence required")
        if self.reason_code not in (
            "PROVIDER_RECOVERED", "INCIDENT_REVIEWED", "DELIVERY_RESTORED"
        ):
            raise ValueError("Controlled incident reason required")


@dataclass(frozen=True, slots=True)
class VerifiedRedriveApproval:
    approval_reference: str
    approver_id: str
    event_id: UUID
    request_id: UUID
    tenant_id: str
    evidence_reference: str
    reason_code: str
    issued_at: datetime
    expires_at: datetime


class RecoveryIdentityPort(Protocol):
    def verify(self, context: object) -> VerifiedOperator: ...


class RecoveryPolicyPort(Protocol):
    def require(self, *, actor: VerifiedOperator, tenant_id: str, action: str) -> None: ...


class RecoveryApprovalPort(Protocol):
    def resolve(self, *, reference: str) -> VerifiedRedriveApproval: ...


class RecoveryRepositoryPort(Protocol):
    def list_dead(self, tenant_id: str, limit: int) -> tuple[DeadAckDelivery, ...]: ...

    def redrive(
        self, request: RedriveRequest, *, actor_id: str, approver_id: str
    ) -> int: ...


class RecoveryClockPort(Protocol):
    def now(self) -> datetime: ...


def _aware(t: datetime) -> bool:
    return isinstance(t, datetime) and t.tzinfo is not None and t.utcoffset() is not None


class IamAckRecoveryService:
    """Require current tenant grant and SoD before the atomic SQL redrive."""

    def __init__(
        self, *, identity: RecoveryIdentityPort, policy: RecoveryPolicyPort,
        approvals: RecoveryApprovalPort, repository: RecoveryRepositoryPort,
        clock: RecoveryClockPort,
    ) -> None:
        self._identity = identity
        self._policy = policy
        self._approvals = approvals
        self._repository = repository
        self._clock = clock

    def _actor(self, auth_context: object, tenant_id: str, action: str) -> VerifiedOperator:
        actor = self._identity.verify(auth_context)
        if (
            not isinstance(actor, VerifiedOperator) or not actor.actor_id
            or not actor.tenant_id or actor.tenant_id != tenant_id
        ):
            raise PrivilegedAccessDenied("Verified recovery actor and tenant required")
        self._policy.require(actor=actor, tenant_id=tenant_id, action=action)
        return actor

    def list_dead(
        self, *, tenant_id: str, auth_context: object, limit: int = 10
    ) -> tuple[DeadAckDelivery, ...]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise ValueError("Bounded DEAD-letter inspection required")
        self._actor(auth_context, tenant_id, "inspect_iam_ack_dead")
        return self._repository.list_dead(tenant_id, limit)

    def redrive(self, request: RedriveRequest, *, auth_context: object) -> int:
        if not isinstance(request, RedriveRequest):
            raise TypeError("Scoped recovery request required")
        actor = self._actor(auth_context, request.tenant_id, "redrive_iam_ack_dead")
        approval = self._approvals.resolve(reference=request.approval_reference)
        now = self._clock.now()
        if (
            not isinstance(approval, VerifiedRedriveApproval)
            or not approval.approver_id or approval.approver_id == actor.actor_id
            or approval.approval_reference != request.approval_reference
            or approval.event_id != request.event_id
            or approval.request_id != request.request_id
            or approval.tenant_id != request.tenant_id
            or approval.evidence_reference != request.evidence_reference
            or approval.reason_code != request.reason_code
            or not _aware(approval.issued_at) or not _aware(approval.expires_at)
            or not _aware(now)
            or not approval.issued_at <= now < approval.expires_at
        ):
            raise PrivilegedAccessDenied("Independent exact-scope recovery approval denied")
        # Immediately recheck authoritative permission and approval before SQL mutation.
        self._policy.require(
            actor=actor, tenant_id=request.tenant_id, action="redrive_iam_ack_dead"
        )
        if self._approvals.resolve(reference=request.approval_reference) != approval:
            raise PrivilegedAccessDenied("Recovery approval changed before re-drive")
        fresh = self._clock.now()
        if not _aware(fresh) or not approval.issued_at <= fresh < approval.expires_at:
            raise PrivilegedAccessDenied("Recovery approval expired")
        return self._repository.redrive(
            request, actor_id=actor.actor_id, approver_id=approval.approver_id
        )
