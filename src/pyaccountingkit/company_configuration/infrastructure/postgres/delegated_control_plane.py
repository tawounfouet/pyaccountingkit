"""Restricted PostgreSQL delegated control plane, without schema-owner DSN.

Only a dedicated login granted EXECUTE on narrowly scoped SECURITY DEFINER
functions can issue, revoke and consume a role fence. This is not remote IAM.
"""
from uuid import UUID

import psycopg

from ...application.fence_contract import FencedRoleOperation, PrivilegedFencePermit
from .authorization_fence import PrivilegedFenceDenied
from .role_lifecycle import RoleLifecycleDenied, RoleLifecycleReceipt


class DelegatedPrivilegedControlPlane:
    """Database privilege boundary; SQL role grants must be provisioned out of band."""

    def __init__(self, dsn: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("Dedicated control-plane DSN required")
        self._dsn = dsn

    def __repr__(self) -> str:
        return "DelegatedPrivilegedControlPlane(dsn=<redacted>)"

    def issue(self, permit: PrivilegedFencePermit) -> None:
        if not isinstance(permit, PrivilegedFencePermit):
            raise TypeError("Trusted scoped fence permit required")
        with psycopg.connect(self._dsn) as conn:
            conn.execute(
                "SELECT company_configuration.cp_issue_fence("
                "%s,%s,%s,%s,%s,%s,%s,%s)",
                (permit.request_id, permit.tenant_id, permit.login_role,
                 permit.operation, permit.actor_id, permit.approver_id,
                 permit.approval_id, permit.expires_at),
            )

    def revoke(self, *, request_id: UUID, tenant_id: str, revoked_by: str) -> bool:
        if not isinstance(request_id, UUID) or not tenant_id or not revoked_by:
            raise PrivilegedFenceDenied("Scoped revocation required")
        with psycopg.connect(self._dsn) as conn:
            return conn.execute(
                "SELECT company_configuration.cp_revoke_fence(%s,%s,%s)",
                (request_id, tenant_id, revoked_by),
            ).fetchone()[0]

    def execute(
        self, operation: FencedRoleOperation, *, new_password: str | None = None,
    ) -> RoleLifecycleReceipt:
        if not isinstance(operation, FencedRoleOperation):
            raise TypeError("Typed fenced operation required")
        if operation.operation not in ("rotate", "revoke"):
            raise PrivilegedFenceDenied("Unsupported role operation")
        if operation.operation == "rotate":
            if (not isinstance(new_password, str)
                    or len(new_password) < 16 or "\x00" in new_password):
                raise RoleLifecycleDenied("Invalid credential input")
        elif new_password is not None:
            raise RoleLifecycleDenied("Revoke cannot carry a password")
        with psycopg.connect(self._dsn) as conn:
            terminated = conn.execute(
                "SELECT company_configuration.cp_execute_fence("
                "%s,%s,%s,%s,%s,%s,%s)",
                (operation.request_id, operation.tenant_id, operation.login_role,
                 operation.operation, operation.actor_id, operation.approval_id,
                 new_password),
            ).fetchone()[0]
        return RoleLifecycleReceipt(
            operation.login_role, operation.tenant_id, operation.operation, terminated,
        )
