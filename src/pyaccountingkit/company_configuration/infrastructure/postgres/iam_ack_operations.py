"""Read-only metrics and scoped DEAD-letter recovery via restricted SQL grants."""

from dataclasses import dataclass
import psycopg

from ...application.iam_ack_recovery import DeadAckDelivery, RedriveRequest


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
