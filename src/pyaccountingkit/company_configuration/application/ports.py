"""Narrow hexagonal ports for the L02 proof slice.

Transport authentication MUST construct TrustedPrincipal via a trusted adapter.
These ports are not a production IAM, DB or C10 implementation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Self

from ..domain.organization.entities import LegalEntity
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import LegalEntityId


@dataclass(frozen=True, slots=True)
class TrustedPrincipal:
    """Identity already verified at an external authentication boundary.

    No caller-supplied roles are trusted. This value is *not* itself an
    authentication mechanism, and must never be constructed from raw API JSON.
    """

    actor_id: str
    tenant_id: str

    def __post_init__(self) -> None:
        for value in (self.actor_id, self.tenant_id):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError("Trusted principal requires nonblank canonical identity")


@dataclass(frozen=True, slots=True)
class ChangeReceipt:
    entity_id: LegalEntityId
    revision: int
    correlation_id: str
    audit_id: str
    event_id: str


@dataclass(frozen=True, slots=True)
class AuditRecord:
    record_id: str
    actor_id: str
    action: str
    scope: ConfigurationScope
    entity_id: LegalEntityId
    before_revision: int
    after_revision: int
    reason: str
    correlation_id: str
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class PendingEvent:
    """Internal outbox candidate, NOT a qualified C10 event contract."""

    event_id: str
    event_type: str
    schema_version: int
    scope: ConfigurationScope
    entity_id: LegalEntityId
    revision: int
    correlation_id: str
    recorded_at: datetime


class LegalEntityRepository(Protocol):
    def get(self, *, scope: ConfigurationScope, entity_id: LegalEntityId) -> LegalEntity | None: ...

    def save(self, entity: LegalEntity, *, expected_revision: int) -> None: ...


class UnitOfWork(Protocol):
    entities: LegalEntityRepository

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...

    def lookup_request(
        self, *, actor_id: str, scope: ConfigurationScope, action: str, key: str
    ) -> tuple[str, ChangeReceipt] | None: ...

    def save_request(
        self, *, actor_id: str, scope: ConfigurationScope, action: str,
        key: str, digest: str, receipt: ChangeReceipt,
    ) -> None: ...

    def append_audit(self, record: AuditRecord) -> None: ...

    def append_outbox(self, event: PendingEvent) -> None: ...

    def commit(self) -> None: ...


class AuthorizationPort(Protocol):
    def require(
        self, *, principal: TrustedPrincipal, action: str, scope: ConfigurationScope
    ) -> None: ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class DenialAuditPort(Protocol):
    """Record denied *verified* principals in a separate durable transaction.

    Authentication failures have no verified principal and are the transport
    authenticator's responsibility. Failure to record raises and must never
    turn a denied operation into an allowed operation.
    """

    def record_denial(
        self, *, principal: TrustedPrincipal, action: str,
        reason_code: str, correlation_id: str | None,
    ) -> None: ...
