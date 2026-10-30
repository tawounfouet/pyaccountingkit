"""G3-C02a trusted-issuer gateway boundary for L03 organization commands.

Never accept a caller-made TrustedPrincipal. An independent verifier attests a
signed command request, then a live IAM grant port and durable nonce port must
accept it before any SQL issuer service is invoked. This module owns NO DSNs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from .organization_commands import AssignOrganizationMembership, EndOrganizationMembership
from .organization_lifecycle import TransitionCompany, TransitionEstablishment
from .organization_registration import (
    RegisterCompany,
    RegisterEstablishment,
    RegisterLegalIdentifier,
)
from .ports import TrustedPrincipal
from .service import PermissionDenied

# The command identity is derived from validated typed domain commands, not
# from any purported actor, tenant or target in the signed token alone.
ACTIONS = {
    RegisterCompany: "organization.company.register",
    RegisterEstablishment: "organization.establishment.register",
    RegisterLegalIdentifier: "organization.legal_identifier.register",
    TransitionCompany: "organization.company.transition",
    TransitionEstablishment: "organization.establishment.transition",
    AssignOrganizationMembership: "organization.membership.assign",
    EndOrganizationMembership: "organization.membership.end",
}


def _json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    if isinstance(value, (tuple, list)):
        return [_json_value(part) for part in value]
    raise TypeError("Unserializable organization command value")


def command_digest(command: object) -> str:
    """Canonical digest over the *entire* strongly typed command payload."""
    if type(command) not in ACTIONS:
        raise PermissionDenied("Unsupported organization command")
    canonical = json.dumps(
        _json_value(command), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CommandIdentity:
    action: str
    tenant_id: str
    target_id: UUID
    request_id: str
    correlation_id: str
    digest: str


def command_identity(command: object) -> CommandIdentity:
    action = ACTIONS.get(type(command))
    if action is None:
        raise PermissionDenied("Unsupported organization command")
    match command:
        case RegisterCompany(company=company):
            tenant, target = company.tenant_id, company.id.value
        case RegisterEstablishment(establishment=site):
            tenant, target = site.tenant_id, site.id.value
        case RegisterLegalIdentifier(identifier_id=identifier_id, identifier=item):
            tenant, target = item.tenant_id, identifier_id
        case TransitionCompany(tenant_id=tenant, company_id=company_id):
            target = company_id.value
        case TransitionEstablishment(tenant_id=tenant, establishment_id=site_id):
            target = site_id.value
        case AssignOrganizationMembership(scope=scope, membership_id=membership_id):
            tenant, target = scope.tenant_id, membership_id.value
        case EndOrganizationMembership(scope=scope, membership_id=membership_id):
            tenant, target = scope.tenant_id, membership_id.value
        case _:
            raise PermissionDenied("Unexpected command variant")
    return CommandIdentity(
        action, tenant, target, command.request_id, command.correlation_id,
        command_digest(command),
    )


@dataclass(frozen=True, slots=True)
class VerifiedCommandEnvelope:
    """Result ONLY of an independently injected cryptographic verifier.

    Creating this dataclass manually is NOT authentication. Gateway production
    composition must wire the pinned-key verifier, never a caller-made instance.
    """

    issuer: str
    actor_id: str
    identity: CommandIdentity
    nonce: UUID
    expires_at: datetime


class SignedCommandVerifierPort(Protocol):
    def verify(self, token: str, *, at: datetime) -> VerifiedCommandEnvelope: ...


class LiveIssuerAuthorizationPort(Protocol):
    def require(
        self, *, issuer: str, principal: TrustedPrincipal,
        action: str, target_id: UUID,
    ) -> None: ...


class DurableNoncePort(Protocol):
    def consume(self, *, issuer: str, nonce: UUID, expires_at: datetime) -> bool:
        """Atomic cluster-wide consume; False on duplicate or backend failure."""
        ...


class OrganizationCommandExecutorPort(Protocol):
    def execute(
        self, *, action: str, command: object, principal: TrustedPrincipal,
    ) -> object: ...


class OrganizationTrustedIssuerGateway:
    """Gate verified actor/action and nonce before any issuer SQL transaction.

    The gateway is a separate *deployment trust boundary*: deploy it outside
    the ordinary application process with private issuer credentials. Reusing
    it inside an API process that has those secrets is NOT secure isolation.
    """

    def __init__(
        self, *, verifier: SignedCommandVerifierPort,
        authorization: LiveIssuerAuthorizationPort,
        nonce_store: DurableNoncePort, executor: OrganizationCommandExecutorPort,
        clock: Any,
    ) -> None:
        if any(obj is None for obj in (
            verifier, authorization, nonce_store, executor, clock,
        )):
            raise ValueError("Independent gateway verification ports are mandatory")
        self._verifier = verifier
        self._authorization = authorization
        self._nonce_store = nonce_store
        self._executor = executor
        self._clock = clock

    def execute(self, command: object, *, signed_evidence: str) -> object:
        identity = command_identity(command)
        if not isinstance(signed_evidence, str) or not signed_evidence:
            raise PermissionDenied("Signed command evidence is mandatory")
        now = self._clock.now()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise PermissionDenied("Gateway needs a trusted aware clock")
        now = now.astimezone(UTC)
        # All failures must be denied BEFORE calling an issuer SQL executor.
        try:
            envelope = self._verifier.verify(signed_evidence, at=now)
            if not isinstance(envelope, VerifiedCommandEnvelope):
                raise PermissionDenied("Unverified command envelope")
            if envelope.identity != identity:
                raise PermissionDenied("Signed command fields do not match typed payload")
            principal = TrustedPrincipal(envelope.actor_id, identity.tenant_id)
            self._authorization.require(
                issuer=envelope.issuer, principal=principal,
                action=identity.action, target_id=identity.target_id,
            )
            # Do not use a process-local set in a deployed gateway. Consume is
            # durable/atomic; service-level idempotency still handles fresh
            # signed attestations sharing the same request_id.
            if not self._nonce_store.consume(
                issuer=envelope.issuer, nonce=envelope.nonce,
                expires_at=envelope.expires_at,
            ):
                raise PermissionDenied("Command attestation nonce already used")
        except Exception as exc:
            raise PermissionDenied("Trusted issuer attestation/authorization denied") from exc
        return self._executor.execute(
            action=identity.action, command=command, principal=principal,
        )


class OrganizationServiceExecutor:
    """Adapter for the three DDD service interfaces, without holding SQL DSNs."""

    def __init__(
        self, *, registration: Any, lifecycle: Any, membership: Any,
    ) -> None:
        self._registration = registration
        self._lifecycle = lifecycle
        self._membership = membership

    def execute(
        self, *, action: str, command: object, principal: TrustedPrincipal,
    ) -> object:
        cases = {
            "organization.company.register": self._registration.register_company,
            "organization.establishment.register": self._registration.register_establishment,
            "organization.legal_identifier.register": self._registration.register_legal_identifier,
            "organization.company.transition": self._lifecycle.transition_company,
            "organization.establishment.transition": self._lifecycle.transition_establishment,
            "organization.membership.assign": self._membership.assign,
            "organization.membership.end": self._membership.end,
        }
        if action != ACTIONS.get(type(command)) or action not in cases:
            raise PermissionDenied("Unsupported or mismatched organization operation")
        return cases[action](command, principal=principal)
