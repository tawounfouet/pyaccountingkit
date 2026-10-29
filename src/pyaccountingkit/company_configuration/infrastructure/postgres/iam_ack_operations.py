"""Read-only metrics and scoped DEAD-letter recovery via restricted SQL grants."""

from dataclasses import dataclass
from datetime import datetime

import psycopg

from ...application.iam_ack_recovery import (
    DeadAckDelivery,
    RedriveRequest,
    VerifiedRedriveApproval,
)
from ...application.privileged_operations import PrivilegedAccessDenied, VerifiedOperator


@dataclass(frozen=True, slots=True)
class IamAckMetrics:
    pending: int
    in_flight: int
    retry: int
    delivered: int
    dead: int
    stale_leases: int
    due_count: int
    oldest_open_seconds: int


class PostgresIamAckMetrics:
    """Only aggregated metrics via the delivery role, no row-level inspection."""

    def __init__(self, delivery_dsn: str) -> None:
        if not isinstance(delivery_dsn, str) or not delivery_dsn.strip():
            raise ValueError("Dedicated IAM delivery DSN required")
        self._dsn = delivery_dsn

    def __repr__(self) -> str:
        return "PostgresIamAckMetrics(dsn=<redacted>)"

    def snapshot(self) -> IamAckMetrics:
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "SELECT * FROM company_configuration.cp_iam_ack_metrics()"
            ).fetchone()
        if row is None or len(row) != 8:
            raise RuntimeError("No verified IAM delivery metrics")
        return IamAckMetrics(*row)


class PostgresIamDeadAckRecovery:
    """Uses only the cc_iam_recovery role, never the schema owner."""

    def __init__(self, recovery_dsn: str) -> None:
        if not isinstance(recovery_dsn, str) or not recovery_dsn.strip():
            raise ValueError("Dedicated IAM recovery DSN required")
        self._dsn = recovery_dsn

    def __repr__(self) -> str:
        return "PostgresIamDeadAckRecovery(dsn=<redacted>)"

    def list_dead(self, tenant_id: str, limit: int) -> tuple[DeadAckDelivery, ...]:
        with psycopg.connect(self._dsn) as conn:
            rows = conn.execute(
                "SELECT * FROM company_configuration.cp_list_dead_iam_acks(%s,%s)",
                (tenant_id, limit),
            ).fetchall()
        return tuple(DeadAckDelivery(*row) for row in rows)

    def redrive(
        self, request: RedriveRequest, *, actor_id: str, approver_id: str
    ) -> int:
        if not isinstance(request, RedriveRequest):
            raise TypeError("Typed recovery request required")
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "SELECT company_configuration.cp_redrive_dead_iam_ack("
                "%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    request.event_id, request.request_id, request.tenant_id,
                    actor_id, approver_id, request.approval_reference,
                    request.reason_code, request.evidence_reference,
                ),
            ).fetchone()
        if row is None or row[0] not in (1, 2):
            raise RuntimeError("Unverified recovery decision, no success")
        return row[0]


class PostgresIamAckApprovalGrants:
    """Writer-side SQL authorization, isolated from cc_iam_recovery.

    This low-level adapter must be deployed behind an independently trusted
    signed-approval verifier, current policy and actor identity. The Python
    value objects alone are NOT signature verification or live IAM authority.
    Granting and re-driving must use different workload/SQL credentials.
    """

    def __init__(self, approval_writer_dsn: str) -> None:
        if not isinstance(approval_writer_dsn, str) or not approval_writer_dsn.strip():
            raise ValueError("Independent approval-writer DSN required")
        self._dsn = approval_writer_dsn

    def __repr__(self) -> str:
        return "PostgresIamAckApprovalGrants(dsn=<redacted>)"

    def issue(
        self,
        request: RedriveRequest,
        *,
        actor: VerifiedOperator,
        approval: VerifiedRedriveApproval,
        now: datetime,
    ) -> int:
        """Mint a one-use SQL grant after caller's independent IAM verification."""
        if (
            not isinstance(request, RedriveRequest)
            or not isinstance(actor, VerifiedOperator)
            or not isinstance(approval, VerifiedRedriveApproval)
            or not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() is None
            or not isinstance(approval.issued_at, datetime)
            or approval.issued_at.tzinfo is None
            or approval.issued_at.utcoffset() is None
            or not isinstance(approval.expires_at, datetime)
            or approval.expires_at.tzinfo is None
            or approval.expires_at.utcoffset() is None
            or actor.tenant_id != request.tenant_id
            or not actor.actor_id or actor.actor_id == approval.approver_id
            or not approval.approver_id
            or approval.approval_reference != request.approval_reference
            or approval.event_id != request.event_id
            or approval.request_id != request.request_id
            or approval.tenant_id != request.tenant_id
            or approval.evidence_reference != request.evidence_reference
            or approval.reason_code != request.reason_code
            or not approval.issued_at <= now < approval.expires_at
        ):
            raise PrivilegedAccessDenied("Independent exact-scope recovery grant denied")
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "SELECT company_configuration.cp_grant_iam_ack_redrive("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    request.event_id, request.request_id, request.tenant_id,
                    actor.actor_id, approval.approver_id, request.approval_reference,
                    request.reason_code, request.evidence_reference, approval.expires_at,
                ),
            ).fetchone()
        if row is None or row[0] not in (1, 2):
            raise RuntimeError("Independent recovery grant was not persisted")
        return row[0]
