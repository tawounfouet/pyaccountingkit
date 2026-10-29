"""Dedicated, write-only privileged-operation audit adapter (L02-07h).

The configured PostgreSQL LOGIN has EXECUTE only on a schema-owner-controlled,
narrow audit routine. It cannot SELECT/UPDATE/DELETE audit tables, issue a fence
or mutate SQL roles. This port assumes a trusted independently authenticated
application service; caller-supplied actor identity is not a signed credential.
"""

from datetime import datetime
from uuid import uuid4

import psycopg

from ...application.privileged_operations import (
    PrivilegedRoleRequest,
    VerifiedApproval,
    VerifiedOperator,
)


class DelegatedPrivilegedAudit:
    """Append verified request facts through a restricted SQL entry point.

    The server records its own timestamp and refuses success without a consumed
    exact-scoped fence. Terminal audit is still separate from SQL role DDL.
    """

    def __init__(self, audit_writer_dsn: str) -> None:
        if not isinstance(audit_writer_dsn, str) or not audit_writer_dsn.strip():
            raise ValueError("A dedicated audit-writer SQL credential is required")
        self._dsn = audit_writer_dsn

    def __repr__(self) -> str:
        return "DelegatedPrivilegedAudit(dsn=<redacted>)"

    def _append(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        approval: VerifiedApproval | None, phase: str, reason: str,
    ) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute(
                "SELECT company_configuration.cp_append_privileged_audit("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(), request.request_id, actor.tenant_id,
                    request.login_role, actor.actor_id,
                    approval.approver_id if approval is not None else None,
                    approval.approval_id if approval is not None else None,
                    request.operation, phase, reason,
                ),
            )

    def record_intent(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        approval: VerifiedApproval, recorded_at: datetime,
    ) -> None:
        self._append(
            request=request, actor=actor, approval=approval,
            phase="INTENT", reason="APPROVED",
        )

    def record_outcome(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        outcome: str, recorded_at: datetime,
    ) -> None:
        if outcome not in ("SUCCEEDED", "FAILED", "CANCELLED"):
            raise ValueError("Unsupported terminal outcome")
        self._append(
            request=request, actor=actor, approval=None,
            phase=outcome, reason=outcome,
        )

    def record_denial(
        self, *, request: PrivilegedRoleRequest, actor: VerifiedOperator,
        code: str, recorded_at: datetime,
    ) -> None:
        if code not in (
            "TENANT_MISMATCH", "CREDENTIAL_REQUIRED", "UNEXPECTED_CREDENTIAL",
            "PERMISSION_DENIED", "APPROVAL_INVALID", "SOD_VIOLATION",
        ):
            raise ValueError("Unsupported denial code")
        self._append(
            request=request, actor=actor, approval=None,
            phase="DENIED", reason=code,
        )
