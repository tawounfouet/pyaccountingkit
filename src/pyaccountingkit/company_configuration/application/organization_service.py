"""L03 ORG-4 membership application service: domain commands through UoW ports.

All domain mutation, audit, Outbox event, and idempotency receipt share ONE
transaction. Authorization is separate and must receive a verified principal;
these operations are not an HTTP authenticator or qualified external C10.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from ..domain.organization.model import OrganizationMembership
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.digest import ContentDigest
from ..domain.shared.effective_interval import EffectiveInterval
from ..domain.shared.errors import VersionConflict
from ..domain.shared.identifiers import MembershipId
from .organization_commands import AssignOrganizationMembership, EndOrganizationMembership
from .ports import (
    AuditRecord,
    AuthorizationPort,
    ChangeReceipt,
    ClockPort,
    PendingEvent,
    TrustedPrincipal,
    UnitOfWork,
)
from .service import IdempotencyConflict, PermissionDenied, SystemClock


class OrganizationMembershipPort(Protocol):
    def latest(
        self, *, scope: ConfigurationScope, membership_id: MembershipId
    ) -> OrganizationMembership | None: ...

    def append(
        self, *, scope: ConfigurationScope, membership: OrganizationMembership
    ) -> None: ...


class OrganizationMembershipUnitOfWork(UnitOfWork, Protocol):
    org_memberships: OrganizationMembershipPort


class OrganizationMembershipService:
    """Application transaction boundary for two revision-aware membership commands."""

    def __init__(
        self,
        uow_factory: Callable[[], OrganizationMembershipUnitOfWork],
        authorization: AuthorizationPort,
        clock: ClockPort | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._authorization = authorization
        self._clock = clock if clock is not None else SystemClock()

    def _authorize(
        self, *, principal: TrustedPrincipal, scope: ConfigurationScope, action: str
    ) -> None:
        if not isinstance(principal, TrustedPrincipal) or principal.tenant_id != scope.tenant_id:
            raise PermissionDenied("Verified same-tenant principal required")
        self._authorization.require(principal=principal, action=action, scope=scope)

    def _now(self) -> datetime:
        now = self._clock.now()
        if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Clock must supply a timezone-aware instant")
        return now.astimezone(UTC)

    @staticmethod
    def _scope_data(scope: ConfigurationScope) -> dict[str, str]:
        return {
            "tenant": scope.tenant_id, "company": str(scope.company_id),
            "entity": str(scope.legal_entity_id),
        }

    @staticmethod
    def _idempotent(
        uow: OrganizationMembershipUnitOfWork, *, principal: TrustedPrincipal,
        scope: ConfigurationScope, action: str, key: str, digest: str,
    ) -> ChangeReceipt | None:
        record = uow.lookup_request(
            actor_id=principal.actor_id, scope=scope, action=action, key=key
        )
        if record is None:
            return None
        prior_digest, receipt = record
        if prior_digest != digest:
            raise IdempotencyConflict("Request key already used with different content")
        return receipt

    def _commit(
        self, *, uow: OrganizationMembershipUnitOfWork, principal: TrustedPrincipal,
        scope: ConfigurationScope, action: str, key: str, digest: str,
        revision: int, previous_revision: int, correlation_id: str, reason: str,
        recorded_at: datetime,
    ) -> ChangeReceipt:
        receipt = ChangeReceipt(
            entity_id=scope.legal_entity_id, revision=revision,
            correlation_id=correlation_id, audit_id=str(uuid4()), event_id=str(uuid4()),
        )
        uow.append_audit(AuditRecord(
            record_id=receipt.audit_id, actor_id=principal.actor_id,
            action=action, scope=scope, entity_id=scope.legal_entity_id,
            before_revision=previous_revision, after_revision=revision,
            reason=reason, correlation_id=correlation_id, recorded_at=recorded_at,
        ))
        uow.append_outbox(PendingEvent(
            event_id=receipt.event_id, event_type=action, schema_version=1,
            scope=scope, entity_id=scope.legal_entity_id,
            revision=revision, correlation_id=correlation_id, recorded_at=recorded_at,
        ))
        uow.save_request(
            actor_id=principal.actor_id, scope=scope, action=action,
            key=key, digest=digest, receipt=receipt,
        )
        uow.commit()
        return receipt

    def assign(
        self, command: AssignOrganizationMembership, *, principal: TrustedPrincipal
    ) -> ChangeReceipt:
        if not isinstance(command, AssignOrganizationMembership):
            raise TypeError("Expected AssignOrganizationMembership command")
        scope, action = command.scope, "organization.membership.assign"
        self._authorize(principal=principal, scope=scope, action=action)
        digest = ContentDigest.from_canonical_json({
            "scope": self._scope_data(scope), "membership": str(command.membership_id),
            "kind": command.kind.value, "exclusive": command.exclusive,
            "valid_from": command.valid_from.isoformat(),
            "valid_to": command.valid_to.isoformat() if command.valid_to else None,
            "source_ref": command.source_ref, "reason": command.reason,
        }).hex_sha256
        with self._uow_factory() as uow:
            cached = self._idempotent(
                uow, principal=principal, scope=scope,
                action=action, key=command.request_id, digest=digest,
            )
            if cached is not None:
                return cached
            if uow.org_memberships.latest(
                scope=scope, membership_id=command.membership_id
            ) is not None:
                raise VersionConflict("Membership identity already exists")
            now = self._now()
            membership = OrganizationMembership(
                command.membership_id, scope.tenant_id, scope.company_id,
                scope.legal_entity_id, command.kind, command.exclusive,
                EffectiveInterval(command.valid_from, command.valid_to),
                now, command.source_ref,
            )
            uow.org_memberships.append(scope=scope, membership=membership)
            return self._commit(
                uow=uow, principal=principal, scope=scope, action=action,
                key=command.request_id, digest=digest, revision=1,
                previous_revision=0, correlation_id=command.correlation_id,
                reason=command.reason, recorded_at=now,
            )

    def end(
        self, command: EndOrganizationMembership, *, principal: TrustedPrincipal
    ) -> ChangeReceipt:
        if not isinstance(command, EndOrganizationMembership):
            raise TypeError("Expected EndOrganizationMembership command")
        scope, action = command.scope, "organization.membership.end"
        self._authorize(principal=principal, scope=scope, action=action)
        digest = ContentDigest.from_canonical_json({
            "scope": self._scope_data(scope), "membership": str(command.membership_id),
            "effective_end": command.effective_end.isoformat(),
            "expected_revision": command.expected_revision,
            "source_ref": command.source_ref, "reason": command.reason,
        }).hex_sha256
        with self._uow_factory() as uow:
            cached = self._idempotent(
                uow, principal=principal, scope=scope,
                action=action, key=command.request_id, digest=digest,
            )
            if cached is not None:
                return cached
            current = uow.org_memberships.latest(
                scope=scope, membership_id=command.membership_id,
            )
            if current is None:
                raise VersionConflict("Membership not found in authorized scope")
            now = self._now()
            revised = current.end(
                effective_end=command.effective_end, recorded_at=now,
                source_ref=command.source_ref, expected_revision=command.expected_revision,
            )
            uow.org_memberships.append(scope=scope, membership=revised)
            return self._commit(
                uow=uow, principal=principal, scope=scope, action=action,
                key=command.request_id, digest=digest, revision=revised.revision,
                previous_revision=current.revision,
                correlation_id=command.correlation_id, reason=command.reason,
                recorded_at=now,
            )
