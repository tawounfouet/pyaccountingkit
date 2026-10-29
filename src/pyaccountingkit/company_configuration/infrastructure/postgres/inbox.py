"""L02-04 candidate: transactional inbox and illustrative SQL projection.

This transport-facing adapter does not implement the published C10 contract.
The producer identity and database credentials must be supplied by a trusted
composition root. RLS here is *not* an independently secure tenant boundary.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .dispatch import OutboxEnvelope


class InboxPayloadConflict(ValueError):
    """The same producer/event id was replayed with different content."""


class InboxTenantMismatch(PermissionError):
    """Inbound event does not belong to the configured tenant."""


class UnsupportedInboxSchema(ValueError):
    """The consumer cannot interpret the incoming event schema."""


class TransactionalEventHandler(Protocol):
    """A trusted handler uses this exact SQL transaction, never its own commit."""

    def apply(
        self,
        connection: psycopg.Connection,
        event: OutboxEnvelope,
        *,
        consumer_id: str,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class InboxResult:
    applied: bool
    duplicate: bool


def _required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{label} must be a non-empty canonical string")
    return value


def _validated_digest(event: OutboxEnvelope) -> str:
    """Hash complete stable metadata, not correlation-dependent delivery state."""
    if not isinstance(event, OutboxEnvelope):
        raise TypeError("Expected a typed OutboxEnvelope from a trusted transport")
    if any(
        not isinstance(value, UUID)
        for value in (event.event_id, event.company_id, event.entity_id)
    ):
        raise ValueError("Event identifiers must be UUIDs")
    for label in ("tenant_id", "event_type", "correlation_id"):
        _required(getattr(event, label), label)
    if type(event.schema_version) is not int or event.schema_version < 1:
        raise UnsupportedInboxSchema("Positive schema version is required")
    if type(event.revision) is not int or event.revision < 1:
        raise ValueError("Positive event revision is required")
    instant = event.recorded_at
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("An event must carry a timezone-aware recorded_at instant")
    canonical = {
        "event_id": str(event.event_id),
        "tenant_id": event.tenant_id,
        "company_id": str(event.company_id),
        "entity_id": str(event.entity_id),
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "revision": event.revision,
        "correlation_id": event.correlation_id,
        "recorded_at": instant.astimezone(UTC).isoformat(),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PostgresInboxConsumer:
    """Atomically persist dedup receipt and a trusted handler's SQL side effect.

    At-least-once delivery can trigger duplicate calls; within *this* DB and
    handler transaction the side effect executes once per
    (tenant, consumer_id, producer_id, event_id). The handler MUST use the
    supplied connection and MUST NOT independently commit or change its scope.
    """

    def __init__(
        self,
        dsn: str,
        *,
        tenant_id: str,
        consumer_id: str,
        producer_id: str,
        handler: TransactionalEventHandler,
        supported_versions: frozenset[int] = frozenset({1}),
    ) -> None:
        self._dsn = _required(dsn, "dsn")
        self._tenant_id = _required(tenant_id, "tenant_id")
        self._consumer_id = _required(consumer_id, "consumer_id")
        self._producer_id = _required(producer_id, "producer_id")
        if not callable(getattr(handler, "apply", None)):
            raise TypeError("A transactional SQL handler is required")
        if (
            not isinstance(supported_versions, frozenset)
            or not supported_versions
            or any(type(v) is not int or v < 1 for v in supported_versions)
        ):
            raise ValueError("Supported schema versions must be a nonempty frozenset")
        self._handler = handler
        self._versions = supported_versions

    def process(self, event: OutboxEnvelope) -> InboxResult:
        digest = _validated_digest(event)
        if event.tenant_id != self._tenant_id:
            raise InboxTenantMismatch("Inbound tenant is not authorized for this consumer")
        if event.schema_version not in self._versions:
            raise UnsupportedInboxSchema("Unsupported inbound event schema")
        # Unique constraint on the inbox key arbitrates concurrent duplicates.
        # A conflicting uncommitted insert blocks until commit/rollback.
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (self._tenant_id,))
            inserted = conn.execute(
                "INSERT INTO company_configuration.inbox_receipts "
                "(tenant_id, consumer_id, producer_id, event_id, payload_sha256, "
                "event_type, schema_version) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, consumer_id, producer_id, event_id) "
                "DO NOTHING RETURNING event_id",
                (
                    self._tenant_id, self._consumer_id, self._producer_id,
                    event.event_id, digest, event.event_type, event.schema_version,
                ),
            ).fetchone()
            if inserted is None:
                old = conn.execute(
                    "SELECT payload_sha256 FROM company_configuration.inbox_receipts "
                    "WHERE tenant_id=%s AND consumer_id=%s AND producer_id=%s "
                    "AND event_id=%s",
                    (self._tenant_id, self._consumer_id, self._producer_id, event.event_id),
                ).fetchone()
                if old is None:
                    raise RuntimeError("Inbox conflict without visible receipt")
                if old["payload_sha256"] != digest:
                    raise InboxPayloadConflict("Same event identity, different event content")
                return InboxResult(applied=False, duplicate=True)
            self._handler.apply(conn, event, consumer_id=self._consumer_id)
        return InboxResult(applied=True, duplicate=False)

    def publish(self, event: OutboxEnvelope) -> None:
        """Test-only adapter to plug this inbox into the existing dispatcher."""
        self.process(event)


class CountingProjectionHandler:
    """Illustrative read-model side effect. NEVER writes into Ledger or books."""

    def apply(
        self, connection: psycopg.Connection, event: OutboxEnvelope, *, consumer_id: str
    ) -> None:
        connection.execute(
            "INSERT INTO company_configuration.inbox_projection_counts "
            "(tenant_id, consumer_id, event_type, applied_count) "
            "VALUES (%s, %s, %s, 1) "
            "ON CONFLICT (tenant_id, consumer_id, event_type) DO UPDATE "
            "SET applied_count = company_configuration.inbox_projection_counts.applied_count + 1",
            (event.tenant_id, consumer_id, event.event_type),
        )
