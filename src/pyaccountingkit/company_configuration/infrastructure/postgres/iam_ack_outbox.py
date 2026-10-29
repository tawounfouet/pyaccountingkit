"""Least-privileged PostgreSQL claim/complete/retry capability for IAM ACKs."""

from dataclasses import dataclass
from uuid import UUID

import psycopg

from ..iam.revocation import IamRevocationReceipt


@dataclass(frozen=True, slots=True)
class IamAckLease:
    receipt: IamRevocationReceipt
    lease_token: UUID


class PostgresIamAckOutbox:
    """Requires dedicated cc_iam_delivery credential, never the schema owner."""

    def __init__(self, dsn: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError('Dedicated IAM ACK delivery DSN required')
        self._dsn = dsn

    def __repr__(self) -> str:
        return 'PostgresIamAckOutbox(dsn=<redacted>)'

    def claim(self, limit: int) -> tuple[IamAckLease, ...]:
        if not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError('Batch limit must be 1..20')
        with psycopg.connect(self._dsn) as conn:
            rows = conn.execute(
                'SELECT * FROM company_configuration.cp_claim_iam_ack(%s)', (limit,)
            ).fetchall()
        return tuple(
            IamAckLease(IamRevocationReceipt(event, request, tenant, outcome), token)
            for event, request, tenant, outcome, token in rows
        )

    def delivered(self, lease: IamAckLease) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute(
                'SELECT company_configuration.cp_complete_iam_ack(%s,%s)',
                (lease.receipt.event_id, lease.lease_token),
            )

    def failed(self, lease: IamAckLease, error_code: str) -> str:
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                'SELECT company_configuration.cp_fail_iam_ack(%s,%s,%s)',
                (lease.receipt.event_id, lease.lease_token, error_code),
            ).fetchone()
        if row is None or row[0] not in ('RETRY', 'DEAD'):
            raise RuntimeError('Invalid IAM ACK failure outcome')
        return row[0]
