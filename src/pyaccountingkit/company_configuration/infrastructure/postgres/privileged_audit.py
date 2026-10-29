"""Owner-only durable, append-only audit for candidate privileged role operations.

Uses an independently trusted administrator DSN. These short transactions are
NOT atomic with PostgreSQL ALTER ROLE and session drain; failed outcome audit
must be escalated as an incident. No credentials are persisted here.
"""

from datetime import datetime
from uuid import uuid4

import psycopg

from ...application.privileged_operations import (
    PrivilegedRoleRequest,
    VerifiedApproval,
    VerifiedOperator,
)


class PostgresPrivilegedAudit:
    """Durable intent before DDL, separate outcome or denial after evaluation."""

    def __init__(self, admin_dsn: str) -> None:
        if not isinstance(admin_dsn, str) or not admin_dsn.strip():
            raise ValueError("Explicit owner DSN required")
        self._dsn = admin_dsn

    def _append(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        approval: VerifiedApproval | None, phase: str, code: str, recorded_at: datetime,
    ) -> None:
        with psycopg.connect(self._dsn) as conn:
            if phase in ("SUCCEEDED", "FAILED"):
                row = conn.execute(
                    "SELECT approver_id, approval_id FROM "
                    "company_configuration.privileged_operation_audit "
                    "WHERE request_id=%s AND tenant_id=%s AND actor_id=%s "
                    "AND operation=%s AND phase='INTENT' FOR SHARE",
                    (request.request_id, actor.tenant_id, actor.actor_id, request.operation),
                ).fetchone()
                if row is None:
                    raise RuntimeError("Cannot complete privileged operation without intent")
                approver_id, approval_id = row
            else:
                approver_id = approval.approver_id if approval is not None else None
                approval_id = approval.approval_id if approval is not None else None
            conn.execute(
                "INSERT INTO company_configuration.privileged_operation_audit "
                "(record_id, request_id, tenant_id, login_role, actor_id, "
                "approver_id, approval_id, operation, phase, reason_code, recorded_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    uuid4(), request.request_id, actor.tenant_id, request.login_role,
                    actor.actor_id, approver_id, approval_id, request.operation,
                    phase, code, recorded_at,
                ),
            )

    def record_intent(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        approval: VerifiedApproval, recorded_at: datetime,
    ) -> None:
        self._append(
            request=request, actor=actor, approval=approval,
            phase="INTENT", code="APPROVED", recorded_at=recorded_at,
        )

    def record_outcome(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        outcome: str, recorded_at: datetime,
    ) -> None:
        if outcome not in ("SUCCEEDED", "FAILED"):
            raise ValueError("Invalid privileged operation outcome")
        self._append(
            request=request, actor=actor, approval=None,
            phase=outcome, code=outcome, recorded_at=recorded_at,
        )

    def record_denial(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        code: str, recorded_at: datetime,
    ) -> None:
        if code not in (
            "TENANT_MISMATCH", "CREDENTIAL_REQUIRED", "UNEXPECTED_CREDENTIAL",
            "PERMISSION_DENIED", "APPROVAL_INVALID", "SOD_VIOLATION",
        ):
            raise ValueError("Unexpected denial reason")
        self._append(
            request=request, actor=actor, approval=None,
            phase="DENIED", code=code, recorded_at=recorded_at,
        )
