"""L02-07d: independently approved incident decisions, never inferred DDL results.

Only trusted adapters may issue verified identities and approvals. This module
never applies SQL role mutations, guesses outcomes or replays old operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from .privileged_operations import (
    OperatorIdentityPort,
    PrivilegedAccessDenied,
    TimePort,
    VerifiedOperator,
    _aware,
)


class IncidentDecisionConflict(RuntimeError):
    """The review is ineligible, already decided or has a terminal DDL record."""


_ALLOWED_DISPOSITIONS = frozenset({
    "ESCALATED", "REMEDIATION_REQUIRED", "INVESTIGATION_DOCUMENTED",
})


@dataclass(frozen=True, slots=True)
class IncidentDecisionRequest:
    review_id: UUID
    tenant_id: str
    disposition: str
    evidence_reference: str
    approval_reference: str
    justification: str

    def __post_init__(self) -> None:
        if not isinstance(self.review_id, UUID):
            raise ValueError("Review ID must be UUID")
        if self.disposition not in _ALLOWED_DISPOSITIONS:
            raise ValueError("Unsupported incident disposition")
        for value in (self.tenant_id, self.evidence_reference,
                      self.approval_reference, self.justification):
            if not isinstance(value, str) or not 1 <= len(value) <= 240:
                raise ValueError("Canonical bounded incident fields required")
            if value != value.strip() or "\n" in value or "\x00" in value:
                raise ValueError("Canonical bounded incident fields required")


@dataclass(frozen=True, slots=True)
class VerifiedIncidentApproval:
    approval_id: str
    approver_id: str
    review_id: UUID
    tenant_id: str
    disposition: str
    evidence_reference: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IncidentDecisionReceipt:
    decision_id: UUID
    review_id: UUID
    tenant_id: str
    disposition: str
    observed_outcome: str  # ALWAYS UNKNOWN; decision does not prove DDL outcome.


class IncidentPolicyPort(Protocol):
    def require_decision(
        self, *, principal: VerifiedOperator, tenant_id: str, disposition: str,
    ) -> None: ...


class IncidentApprovalPort(Protocol):
    def resolve(self, *, reference: str) -> VerifiedIncidentApproval: ...


class IncidentDecisionRepository(Protocol):
    def record_decision(
        self, *, request: IncidentDecisionRequest, actor: VerifiedOperator,
        approval: VerifiedIncidentApproval, recorded_at: datetime,
    ) -> IncidentDecisionReceipt: ...

    def record_denial(
        self, *, request: IncidentDecisionRequest, actor: VerifiedOperator,
        code: str, recorded_at: datetime,
    ) -> None: ...


class PrivilegedIncidentService:
    """Two-person approved decision about a manual UNKNOWN incident.

    A decision captures a response plan only, never retroactively modifies an
    INTENT, assigns a historical DDL result, or changes a PostgreSQL role.
    """

    def __init__(
        self, *, identity: OperatorIdentityPort, policy: IncidentPolicyPort,
        approvals: IncidentApprovalPort, repository: IncidentDecisionRepository,
        clock: TimePort,
    ) -> None:
        self._identity = identity
        self._policy = policy
        self._approvals = approvals
        self._repository = repository
        self._clock = clock

    def decide(
        self, request: IncidentDecisionRequest, *, auth_context: object,
    ) -> IncidentDecisionReceipt:
        if not isinstance(request, IncidentDecisionRequest):
            raise TypeError("Typed incident decision required")
        actor = self._identity.verify(auth_context)
        if not isinstance(actor, VerifiedOperator) or not actor.actor_id:
            raise PrivilegedAccessDenied("Verified incident operator required")
        now = self._clock.now()
        if not _aware(now):
            raise ValueError("Timezone-aware clock required")

        def deny(code: str) -> None:
            # A denied cross-tenant request records the ACTUAL authenticated tenant.
            self._repository.record_denial(
                request=request, actor=actor, code=code, recorded_at=now,
            )
            raise PrivilegedAccessDenied(code)

        if not actor.tenant_id or actor.tenant_id != request.tenant_id:
            deny("TENANT_MISMATCH")
        try:
            self._policy.require_decision(
                principal=actor, tenant_id=request.tenant_id,
                disposition=request.disposition,
            )
        except PrivilegedAccessDenied:
            deny("PERMISSION_DENIED")
        approval = self._approvals.resolve(reference=request.approval_reference)
        if not isinstance(approval, VerifiedIncidentApproval):
            deny("APPROVAL_INVALID")
        if not approval.approver_id or approval.approver_id == actor.actor_id:
            deny("SOD_VIOLATION")
        if (
            approval.approval_id != request.approval_reference
            or approval.review_id != request.review_id
            or approval.tenant_id != request.tenant_id
            or approval.disposition != request.disposition
            or approval.evidence_reference != request.evidence_reference
            or not _aware(approval.issued_at)
            or not _aware(approval.expires_at)
            or not approval.issued_at <= now < approval.expires_at
        ):
            deny("APPROVAL_INVALID")
        # Repository verifies current incident state AND original actor/reviewer
        # SoD within the same transaction as the immutable decision write.
        return self._repository.record_decision(
            request=request, actor=actor, approval=approval, recorded_at=now,
        )
