"""Strict in-memory proof adapter; neither durable nor production-safe.

Atomicity holds within *one process* and one store instance. No SQL guarantees,
no real persistence, no distributed transactions and no externally delivered C10.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import RLock

from ..application.ports import (
    AuditRecord,
    ChangeReceipt,
    PendingEvent,
    TrustedPrincipal,
)
from ..application.service import PermissionDenied
from ..domain.organization.entities import LegalEntity
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.errors import VersionConflict
from ..domain.shared.identifiers import LegalEntityId


class MemoryAuthorization:
    """Explicit allowlist test adapter. No implicit admin or default allow."""

    def __init__(self) -> None:
        self._grants: set[tuple[str, str, ConfigurationScope]] = set()

    def grant(self, *, actor_id: str, action: str, scope: ConfigurationScope) -> None:
        self._grants.add((actor_id, action, scope))

    def revoke(self, *, actor_id: str, action: str, scope: ConfigurationScope) -> None:
        self._grants.discard((actor_id, action, scope))

    def require(
        self, *, principal: TrustedPrincipal, action: str, scope: ConfigurationScope
    ) -> None:
        if (
            not isinstance(principal, TrustedPrincipal)
            or principal.tenant_id != scope.tenant_id
            or (principal.actor_id, action, scope) not in self._grants
        ):
            raise PermissionDenied("Operation not authorized")


@dataclass
class MemoryStore:
    """Staged local state; callers must not mutate its internals in production."""

    entities: dict[tuple[str, LegalEntityId], LegalEntity] = field(default_factory=dict)
    requests: dict[
        tuple[str, str, ConfigurationScope, str, str], tuple[str, ChangeReceipt]
    ] = field(default_factory=dict)
    audit: list[AuditRecord] = field(default_factory=list)
    outbox: list[PendingEvent] = field(default_factory=list)
    lock: RLock = field(default_factory=RLock)


class MemoryLegalEntityRepository:
    def __init__(self, entities: dict[tuple[str, LegalEntityId], LegalEntity]) -> None:
        self._entities = entities

    def get(self, *, scope: ConfigurationScope, entity_id: LegalEntityId) -> LegalEntity | None:
        entity = self._entities.get((scope.tenant_id, entity_id))
        if entity is None or entity.scope != scope:
            return None
        return entity

    def save(self, entity: LegalEntity, *, expected_revision: int) -> None:
        key = (entity.scope.tenant_id, entity.id)
        current = self._entities.get(key)
        if current is None:
            if expected_revision != 0 or entity.revision != 1:
                raise VersionConflict("New entity must have revision 1 and expected 0")
        else:
            if current.scope != entity.scope:
                raise VersionConflict("Changing an entity's accounting perimeter is forbidden")
            if current.revision != expected_revision or entity.revision != expected_revision + 1:
                raise VersionConflict("Conflicting entity revision")
        self._entities[key] = entity


class MemoryUnitOfWork:
    """Serializable local fake with commit-or-rollback and failure injection.

    The lock prevents concurrent in-process writers from both accepting a stale
    expected_revision. The store's mutable fields are test-only inspection hooks.
    """

    def __init__(
        self, store: MemoryStore, *, before_commit: Callable[[], None] | None = None
    ) -> None:
        self._store = store
        self._before_commit = before_commit
        self._active = False
        self._committed = False

    def __enter__(self) -> "MemoryUnitOfWork":
        self._store.lock.acquire()
        try:
            self._entities = self._store.entities.copy()
            self._requests = self._store.requests.copy()
            self._audit = self._store.audit.copy()
            self._outbox = self._store.outbox.copy()
            self.entities = MemoryLegalEntityRepository(self._entities)
            self._active = True
            return self
        except BaseException:
            self._store.lock.release()
            raise

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._active:
            self._active = False
            self._store.lock.release()

    def _ensure_open(self) -> None:
        if not self._active or self._committed:
            raise RuntimeError("Unit of Work is closed or already committed")

    def lookup_request(
        self, *, actor_id: str, scope: ConfigurationScope, action: str, key: str
    ) -> tuple[str, ChangeReceipt] | None:
        self._ensure_open()
        return self._requests.get((scope.tenant_id, actor_id, scope, action, key))

    def save_request(
        self, *, actor_id: str, scope: ConfigurationScope, action: str,
        key: str, digest: str, receipt: ChangeReceipt,
    ) -> None:
        self._ensure_open()
        request_key = (scope.tenant_id, actor_id, scope, action, key)
        if request_key in self._requests:
            raise RuntimeError("Idempotency slot already staged")
        self._requests[request_key] = (digest, receipt)

    def append_audit(self, record: AuditRecord) -> None:
        self._ensure_open()
        self._audit.append(record)

    def append_outbox(self, event: PendingEvent) -> None:
        self._ensure_open()
        self._outbox.append(event)

    def commit(self) -> None:
        self._ensure_open()
        if self._before_commit is not None:
            self._before_commit()  # can raise before any store mutation
        # The four assignments are guarded by an in-process lock; no other
        # application thread can observe a partial commit through this adapter.
        self._store.entities = self._entities
        self._store.requests = self._requests
        self._store.audit = self._audit
        self._store.outbox = self._outbox
        self._committed = True
