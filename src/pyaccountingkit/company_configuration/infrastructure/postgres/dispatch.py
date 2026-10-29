"""Leased PostgreSQL outbox delivery; at-least-once, never exactly-once.

Producer events are immutable. Mutable delivery bookkeeping lives in a separate
RLS-guarded table, using the authenticated login-to-tenant binding from L02-05.
Application authorization and independent credential provisioning remain required.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from .tenant_boundary import require_tenant_connection


@dataclass(frozen=True, slots=True)
class OutboxEnvelope:
    event_id: UUID
    tenant_id: str
    company_id: UUID
    entity_id: UUID
    event_type: str
    schema_version: int
    revision: int
    correlation_id: str
    recorded_at: datetime


class EventPublisher(Protocol):
    """Publisher must accept at-least-once deliveries with stable event IDs."""

    def publish(self, event: OutboxEnvelope) -> None: ...


@dataclass(frozen=True, slots=True)
class DispatchResult:
    claimed: int
    delivered: int
    retryable_failures: int
    dead_lettered: int


@dataclass(frozen=True, slots=True)
class _Claim:
    event: OutboxEnvelope
    token: UUID
    attempts: int


class DeliveryLeaseLost(RuntimeError):
    """Another worker owns this event; this worker may not mutate its state."""


class PostgresOutboxDispatcher:
    """Dispatch events for one *externally authorized* tenant.

    A successful publisher call followed by a lost acknowledgement can cause a
    duplicate later. Consumers MUST de-duplicate event_id transactionally.
    """

    def __init__(
        self,
        dsn: str,
        *,
        tenant_id: str,
        worker_id: str,
        publisher: EventPublisher,
        clock: Callable[[], datetime] | None = None,
        lease_seconds: int = 60,
        max_attempts: int = 5,
        retry_seconds: int = 2,
        max_retry_seconds: int = 300,
    ) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("A dispatcher DSN is required")
        if any(not isinstance(s, str) or not s or s.strip() != s
               for s in (tenant_id, worker_id)):
            raise ValueError("An explicit canonical tenant and worker are required")
        if (not isinstance(lease_seconds, int) or lease_seconds < 1
                or not isinstance(max_attempts, int) or max_attempts < 1
                or not isinstance(retry_seconds, int) or retry_seconds < 1
                or not isinstance(max_retry_seconds, int)
                or max_retry_seconds < retry_seconds):
            raise ValueError("Invalid lease/retry configuration")
        self._dsn = dsn
        self._tenant = tenant_id
        self._worker = worker_id
        self._publisher = publisher
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lease_seconds = lease_seconds
        self._max_attempts = max_attempts
        self._retry_seconds = retry_seconds
        self._max_retry_seconds = max_retry_seconds

    def _now(self) -> datetime:
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Dispatcher clock must return a timezone-aware datetime")
        return now

    def _open(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _set_tenant(self, conn: psycopg.Connection) -> None:
        require_tenant_connection(conn, self._tenant)

    def _claim(self, limit: int) -> list[_Claim]:
        now = self._now()
        # Unique token per *batch*; the same event cannot have two active
        # claims. A later lease always gets a different fencing token.
        token = uuid4()
        with self._open() as conn:
            self._set_tenant(conn)
            conn.execute(
                "INSERT INTO company_configuration.outbox_delivery (tenant_id, event_id) "
                "SELECT tenant_id, event_id FROM company_configuration.outbox_events "
                "WHERE tenant_id=%s ON CONFLICT (tenant_id, event_id) DO NOTHING",
                (self._tenant,),
            )
            # A crashed worker can exhaust its budget WITHOUT ever calling
            # _complete(). Finalize its expired lease here, before reclaiming.
            # Keep the producer event immutable and avoid a sixth publication.
            conn.execute(
                "UPDATE company_configuration.outbox_delivery SET "
                "dead_letter_at=%s, last_error='LEASE_EXPIRED', "
                "lease_owner=NULL, lease_token=NULL, lease_until=NULL "
                "WHERE tenant_id=%s AND delivered_at IS NULL "
                "AND dead_letter_at IS NULL AND attempts>=%s "
                "AND (lease_until IS NULL OR lease_until<=%s)",
                (now, self._tenant, self._max_attempts, now),
            )
            rows = conn.execute(
                "WITH candidates AS ("
                " SELECT tenant_id, event_id FROM company_configuration.outbox_delivery "
                " WHERE tenant_id=%s AND delivered_at IS NULL AND dead_letter_at IS NULL "
                " AND attempts<%s AND available_at<=%s "
                " AND (lease_until IS NULL OR lease_until<=%s) "
                " ORDER BY available_at, event_id FOR UPDATE SKIP LOCKED LIMIT %s"
                ") UPDATE company_configuration.outbox_delivery AS delivery "
                "SET attempts=delivery.attempts+1, lease_owner=%s, lease_token=%s, "
                "lease_until=%s FROM candidates AS c "
                "WHERE delivery.tenant_id=c.tenant_id AND delivery.event_id=c.event_id "
                "RETURNING delivery.event_id, delivery.attempts",
                (
                    self._tenant, self._max_attempts, now, now, limit,
                    self._worker, token, now + timedelta(seconds=self._lease_seconds),
                ),
            ).fetchall()
            if not rows:
                return []
            attempt_by_id = {r["event_id"]: r["attempts"] for r in rows}
            found = conn.execute(
                "SELECT event_id, tenant_id, company_id, entity_id, event_type, "
                "schema_version, revision, correlation_id, recorded_at "
                "FROM company_configuration.outbox_events "
                "WHERE tenant_id=%s AND event_id=ANY(%s)",
                (self._tenant, list(attempt_by_id)),
            ).fetchall()
            claims = [
                _Claim(OutboxEnvelope(**dict(r)), token, attempt_by_id[r["event_id"]])
                for r in found
            ]
            if len(claims) != len(rows):
                raise RuntimeError("Outbox claim missing an immutable source event")
            return claims

    def _complete(self, claim: _Claim, *, failure: Exception | None) -> bool:
        now = self._now()
        terminal = failure is not None and claim.attempts >= self._max_attempts
        delay = min(
            self._retry_seconds * 2 ** min(claim.attempts - 1, 20),
            self._max_retry_seconds,
        )
        # Never persist arbitrary external exception messages (potential secrets).
        error_class = type(failure).__name__[:100] if failure is not None else None
        with self._open() as conn:
            self._set_tenant(conn)
            row = conn.execute(
                "UPDATE company_configuration.outbox_delivery "
                "SET delivered_at=CASE WHEN %s THEN %s ELSE delivered_at END, "
                "dead_letter_at=CASE WHEN %s THEN %s ELSE dead_letter_at END, "
                "available_at=%s, last_error=%s, "
                "lease_owner=NULL, lease_token=NULL, lease_until=NULL "
                "WHERE tenant_id=%s AND event_id=%s AND lease_token=%s "
                "AND lease_until>%s AND delivered_at IS NULL AND dead_letter_at IS NULL "
                "RETURNING event_id",
                (
                    failure is None, now, terminal, now,
                    now + timedelta(seconds=delay) if failure and not terminal else now,
                    error_class, self._tenant, claim.event.event_id, claim.token, now,
                ),
            ).fetchone()
            if row is None:
                raise DeliveryLeaseLost("Lost outbox lease before state transition")
        return terminal

    def dispatch_once(self, *, limit: int = 10) -> DispatchResult:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Batch limit must be between 1 and 100")
        claims = self._claim(limit)
        delivered = retryable = dead = 0
        for claim in claims:
            try:
                self._publisher.publish(claim.event)
            except Exception as exc:
                terminal = self._complete(claim, failure=exc)
                dead += int(terminal)
                retryable += int(not terminal)
            else:
                self._complete(claim, failure=None)
                delivered += 1
        return DispatchResult(len(claims), delivered, retryable, dead)
