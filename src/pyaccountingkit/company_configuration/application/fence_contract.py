"""Pure application contract for fenced privileged SQL operations.

Value objects are not authentication credentials or IAM approvals.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrivilegedFencePermit:
    request_id: UUID
    tenant_id: str
    login_role: str
    operation: str
    actor_id: str
    approver_id: str
    approval_id: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, UUID) or self.operation not in ("rotate", "revoke"):
            raise ValueError("Valid operation and UUID required")
        for value in (
            self.tenant_id, self.login_role, self.actor_id,
            self.approver_id, self.approval_id,
        ):
            if not isinstance(value, str) or not value or value.strip() != value:
                raise ValueError("Canonical nonblank fence identity required")
        if self.actor_id == self.approver_id or not (
            isinstance(self.expires_at, datetime)
            and self.expires_at.tzinfo is not None
            and self.expires_at.utcoffset() is not None
        ):
            raise ValueError("Independent approver and timezone-aware expiration required")


@dataclass(frozen=True, slots=True)
class FencedRoleOperation:
    request_id: UUID
    tenant_id: str
    login_role: str
    operation: str
    actor_id: str
    approval_id: str


class PrivilegedFencedExecutorPort(Protocol):
    def issue(self, permit: PrivilegedFencePermit) -> None: ...

    def execute(
        self, operation: FencedRoleOperation, *, new_password: str | None = None,
    ) -> object: ...
