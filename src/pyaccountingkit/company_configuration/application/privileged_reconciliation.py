"""L02-07c: reviewed unresolved intent detection, NEVER inferred DDL outcomes.

This authorization boundary requires real IdP and policy adapters in production.
A Python VerifiedOperator is NOT proof of identity by itself.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from .privileged_operations import (
    OperatorIdentityPort,
    PrivilegedAccessDenied,
    TimePort,
    VerifiedOperator,
    _aware,
)


@dataclass(frozen=True, slots=True)
class PrivilegedReview:
    review_id: UUID
    request_id: UUID
    tenant_id: str
    login_role: str
    operation: str
    detected_at: datetime
    observed_outcome: str  # Always UNKNOWN. SQL state never proves past DDL outcome.


class ReconciliationPolicyPort(Protocol):
    def require_review(self, *, principal: VerifiedOperator, tenant_id: str) -> None: ...


class PrivilegedReviewRepository(Protocol):
    def mark_stale(
        self, *, tenant_id: str, reviewer_id: str, cutoff: datetime,
        detected_at: datetime, limit: int,
    ) -> tuple[PrivilegedReview, ...]: ...


class PrivilegedReconciliationService:
    """Explicit IAM-authorized security review of old orphan INTENT records.

    There is no automatic retry of rotation/revocation and no SUCCEEDED/FAILED
    inference. Each reviewer action records immutable REVIEW_REQUIRED evidence.
    """

    def __init__(
        self, *, identity: OperatorIdentityPort, policy: ReconciliationPolicyPort,
        repository: PrivilegedReviewRepository, clock: TimePort,
    ) -> None:
        self._identity = identity
        self._policy = policy
        self._repository = repository
        self._clock = clock

    def review_stale(
        self, *, auth_context: object, tenant_id: str, older_than_seconds: int = 300,
        limit: int = 50,
    ) -> tuple[PrivilegedReview, ...]:
        if (not isinstance(tenant_id, str) or not tenant_id
                or tenant_id.strip() != tenant_id):
            raise PrivilegedAccessDenied("Canonical tenant scope required")
        if type(older_than_seconds) is not int or older_than_seconds < 60:
            raise ValueError("Review delay must be at least 60 seconds")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Review batch limit must be between 1 and 100")
        actor = self._identity.verify(auth_context)
        if not isinstance(actor, VerifiedOperator) or not actor.actor_id:
            raise PrivilegedAccessDenied("Authenticated reviewer required")
        if actor.tenant_id != tenant_id:
            raise PrivilegedAccessDenied("Reviewer tenant differs from requested scope")
        self._policy.require_review(principal=actor, tenant_id=tenant_id)
        now = self._clock.now()
        if not _aware(now):
            raise ValueError("Trusted timezone-aware clock required")
        return self._repository.mark_stale(
            tenant_id=tenant_id, reviewer_id=actor.actor_id,
            cutoff=now - timedelta(seconds=older_than_seconds),
            detected_at=now, limit=limit,
        )
