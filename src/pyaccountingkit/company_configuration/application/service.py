"""L02 application proof slice: secured, scoped, staged mutation + evidence.

An in-memory adapter exercises the ports. It does not substitute for durable
storage, DB-enforced scope or audit immutability, migrations or C10 qualification.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from ..domain.organization.entities import LegalEntity
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.digest import ContentDigest
from ..domain.shared.errors import DomainError
from .commands import CreateLegalEntity, RenameLegalEntity
from .ports import (
    AuditRecord,
    AuthorizationPort,
    ChangeReceipt,
    ClockPort,
    DenialAuditPort,
    PendingEvent,
    TrustedPrincipal,
    UnitOfWork,
)


class PermissionDenied(DomainError):
    code = "PERMISSION_DENIED"


class EntityNotFound(DomainError):
    code = "ENTITY_NOT_FOUND"


class IdempotencyConflict(DomainError):
    code = "IDEMPOTENCY_CONFLICT"


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class LegalEntityService:
    """Authorization precedes access, then the UoW stages all changes together."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        authorization: AuthorizationPort,
        clock: ClockPort | None = None,
        denial_audit: DenialAuditPort | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._authorization = authorization
        self._clock = clock if clock is not None else SystemClock()
        self._denial_audit = denial_audit

    def _authorize(
        self, *, principal: TrustedPrincipal, action: str,
        scope: ConfigurationScope, correlation_id: str | None = None,
    ) -> None:
        if not isinstance(principal, TrustedPrincipal):
            # Unauthenticated calls must be audited by the authentication
            # boundary; never trust a payload-supplied actor or tenant ID.
            raise PermissionDenied("Authenticated principal required")
        reason_code = "TENANT_MISMATCH" if principal.tenant_id != scope.tenant_id else None
        if reason_code is None:
            try:
                self._authorization.require(principal=principal, action=action, scope=scope)
            except PermissionDenied:
                reason_code = "PERMISSION_DENIED"
        if reason_code is not None:
            if self._denial_audit is not None:
                self._denial_audit.record_denial(
                    principal=principal, action=action, reason_code=reason_code,
                    correlation_id=correlation_id,
                )
            raise PermissionDenied("Operation not authorized")

    def create(self, command: CreateLegalEntity, *, principal: TrustedPrincipal) -> ChangeReceipt:
        if not isinstance(command, CreateLegalEntity):
            raise TypeError("Expected CreateLegalEntity command")
        scope = command.scope
        self._authorize(
            principal=principal, action="legal_entity.create", scope=scope,
            correlation_id=command.correlation_id,
        )
        digest = ContentDigest.from_canonical_json({
            "scope": self._scope_payload(scope), "name": command.legal_name,
            "jurisdiction": command.jurisdiction.value,
            "currency": command.functional_currency.value,
            "reason": command.reason,
        }).hex_sha256
        with self._uow_factory() as uow:
            cached = self._replay(
                uow, principal, scope, "legal_entity.create", command.request_id, digest
            )
            if cached:
                return cached
            entity = LegalEntity(
                id=scope.legal_entity_id, scope=scope, legal_name=command.legal_name,
                jurisdiction=command.jurisdiction,
                functional_currency=command.functional_currency,
            )
            uow.entities.save(entity, expected_revision=0)
            receipt = self._record(
                uow, principal=principal, scope=scope, action="legal_entity.create",
                entity=entity, prior_revision=0, reason=command.reason,
                correlation_id=command.correlation_id,
            )
            uow.save_request(
                actor_id=principal.actor_id, scope=scope, action="legal_entity.create",
                key=command.request_id, digest=digest, receipt=receipt,
            )
            uow.commit()
            return receipt

    def rename(self, command: RenameLegalEntity, *, principal: TrustedPrincipal) -> ChangeReceipt:
        if not isinstance(command, RenameLegalEntity):
            raise TypeError("Expected RenameLegalEntity command")
        scope = command.scope
        self._authorize(
            principal=principal, action="legal_entity.rename", scope=scope,
            correlation_id=command.correlation_id,
        )
        digest = ContentDigest.from_canonical_json({
            "scope": self._scope_payload(scope), "entity_id": str(command.entity_id),
            "expected_revision": command.expected_revision,
            "new_name": command.new_name, "reason": command.reason,
        }).hex_sha256
        with self._uow_factory() as uow:
            cached = self._replay(
                uow, principal, scope, "legal_entity.rename", command.request_id, digest
            )
            if cached:
                return cached
            existing = uow.entities.get(scope=scope, entity_id=command.entity_id)
            if existing is None:
                raise EntityNotFound("Legal entity not found within authorized scope")
            changed = existing.with_legal_name(
                command.new_name, expected_revision=command.expected_revision,
                reason=command.reason,
            )
            uow.entities.save(changed, expected_revision=command.expected_revision)
            receipt = self._record(
                uow, principal=principal, scope=scope, action="legal_entity.rename",
                entity=changed, prior_revision=existing.revision, reason=command.reason,
                correlation_id=command.correlation_id,
            )
            uow.save_request(
                actor_id=principal.actor_id, scope=scope, action="legal_entity.rename",
                key=command.request_id, digest=digest, receipt=receipt,
            )
            uow.commit()
            return receipt

    def read(self, *, principal: TrustedPrincipal, scope: ConfigurationScope) -> LegalEntity:
        self._authorize(principal=principal, action="legal_entity.read", scope=scope)
        with self._uow_factory() as uow:
            entity = uow.entities.get(scope=scope, entity_id=scope.legal_entity_id)
            if entity is None:
                raise EntityNotFound("Legal entity not found within authorized scope")
            return entity

    @staticmethod
    def _scope_payload(scope: ConfigurationScope) -> dict[str, str]:
        return {
            "tenant_id": scope.tenant_id,
            "company_id": str(scope.company_id),
            "legal_entity_id": str(scope.legal_entity_id),
        }

    @staticmethod
    def _replay(
        uow: UnitOfWork, principal: TrustedPrincipal, scope: ConfigurationScope,
        action: str, key: str, digest: str,
    ) -> ChangeReceipt | None:
        record = uow.lookup_request(
            actor_id=principal.actor_id, scope=scope, action=action, key=key
        )
        if record is None:
            return None
        old_digest, receipt = record
        if old_digest != digest:
            raise IdempotencyConflict("Request key was previously used for another payload")
        return receipt

    def _record(
        self, uow: UnitOfWork, *, principal: TrustedPrincipal,
        scope: ConfigurationScope, action: str, entity: LegalEntity,
        prior_revision: int, reason: str, correlation_id: str,
    ) -> ChangeReceipt:
        now = self._clock.now()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Clock must return a timezone-aware instant")
        receipt = ChangeReceipt(
            entity_id=entity.id, revision=entity.revision,
            correlation_id=correlation_id, audit_id=str(uuid4()), event_id=str(uuid4()),
        )
        uow.append_audit(AuditRecord(
            record_id=receipt.audit_id, actor_id=principal.actor_id, action=action,
            scope=scope, entity_id=entity.id, before_revision=prior_revision,
            after_revision=entity.revision, reason=reason,
            correlation_id=correlation_id, recorded_at=now,
        ))
        uow.append_outbox(PendingEvent(
            event_id=receipt.event_id, event_type=action,
            schema_version=1, scope=scope, entity_id=entity.id,
            revision=entity.revision, correlation_id=correlation_id, recorded_at=now,
        ))
        return receipt
