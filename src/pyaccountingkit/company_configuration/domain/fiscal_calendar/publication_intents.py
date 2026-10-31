"""L06-04 — non-executing calendar publication/audit/outbox INTENTS (R&D).

No signed approval, COMMIT, publisher, emitted event, durable audit, SQL, C10,
Ledger or eligibility can be created from these immutable draft proposals.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import NAMESPACE_URL, uuid5

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError
from ..shared.identifiers import (
    CalendarAuditIntentId,
    CalendarCandidateVersionId,
    CalendarOutboxIntentId,
    CalendarPublicationIntentId,
)
from .versions_assignments import CalendarVersionCandidate


class InvalidCalendarPublicationIntent(DomainError):
    code = "INVALID_CALENDAR_PUBLICATION_INTENT"


class CalendarPublicationIntentConflict(DomainError):
    code = "CALENDAR_PUBLICATION_INTENT_CONFLICT"


class CalendarPublicationIntentTampered(DomainError):
    code = "CALENDAR_PUBLICATION_INTENT_TAMPERED"


class DeclaredRoleCandidate(Enum):
    PREPARER = "PREPARER"
    REVIEWER = "REVIEWER"
    APPROVER = "APPROVER"
    PUBLISHER = "PUBLISHER"


class UnverifiedPublicationGate(Enum):
    SIGNED_ACTOR_AND_ISSUER = "SIGNED_ACTOR_AND_ISSUER"
    INDEPENDENT_APPROVAL_AND_SOD = "INDEPENDENT_APPROVAL_AND_SOD"
    NORMATIVE_AND_DEPENDENCY_VALIDATION = "NORMATIVE_AND_DEPENDENCY_VALIDATION"
    AUTHORITATIVE_CURRENT_HEAD_AND_IDEMPOTENCY = (
        "AUTHORITATIVE_CURRENT_HEAD_AND_IDEMPOTENCY"
    )
    ATOMIC_VERSION_AUDIT_OUTBOX_COMMIT = "ATOMIC_VERSION_AUDIT_OUTBOX_COMMIT"
    PUBLISHED_SCOPE_AND_TEMPORAL_EXCLUSION = "PUBLISHED_SCOPE_AND_TEMPORAL_EXCLUSION"


def _aware(value: datetime) -> bool:
    return type(value) is datetime and value.tzinfo is not None and (
        value.utcoffset() is not None
    )


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _text(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip() == value


def _key(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", value
    ) is not None


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


def _digest(payload: dict[str, object]) -> str:
    data = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _scope(scope: ConfigurationScope) -> dict[str, str]:
    return {
        "tenant": scope.tenant_id,
        "company": str(scope.company_id),
        "legal_entity": str(scope.legal_entity_id),
    }


@dataclass(frozen=True, slots=True)
class PublicationRoleClaimCandidate:
    """Unverified, non-signing role metadata; NOT ApprovalEvidence."""

    role: DeclaredRoleCandidate
    actor_ref: str
    claimed_at: datetime
    expires_at: datetime
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, DeclaredRoleCandidate) or not all(
            _text(value) for value in (self.actor_ref, self.source_ref)
        ):
            raise InvalidCalendarPublicationIntent("Typed role and unverified actor/source")
        if (
            not _aware(self.claimed_at)
            or not _aware(self.expires_at)
            or self.expires_at.astimezone(UTC) <= self.claimed_at.astimezone(UTC)
        ):
            raise InvalidCalendarPublicationIntent("Aware bounded role claim required")


def _claim_manifest(claim: PublicationRoleClaimCandidate) -> dict[str, str]:
    return {
        "role": claim.role.value,
        "actor_ref": claim.actor_ref,
        "claimed_at": _utc(claim.claimed_at),
        "expires_at": _utc(claim.expires_at),
        "source_ref": claim.source_ref,
        "signature_status": "UNVERIFIED_UNTRUSTED_CLAIM",
    }


@dataclass(frozen=True, slots=True, eq=False)
class CalendarPublicationRequestCandidate:
    """Proposed intent to publish an exact candidate; DOES NOT perform publishing."""

    id: CalendarPublicationIntentId
    calendar_version: CalendarVersionCandidate
    scope: ConfigurationScope
    effective: EffectiveInterval
    requested_at: datetime
    expected_content_digest: str
    idempotency_key: str
    correlation_id: str
    reason: str
    source_ref: str
    role_claims: tuple[PublicationRoleClaimCandidate, ...] = ()
    expected_prior_version_id: CalendarCandidateVersionId | None = None
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, CalendarPublicationIntentId):
            raise InvalidCalendarPublicationIntent("Typed intent ID required")
        if not isinstance(self.calendar_version, CalendarVersionCandidate):
            raise InvalidCalendarPublicationIntent("Typed candidate calendar version required")
        self.calendar_version.verify_integrity()
        if not isinstance(self.scope, ConfigurationScope) or (
            self.scope.book_id is not None
            or self.scope != self.calendar_version.calendar.scope
        ):
            raise InvalidCalendarPublicationIntent("Exact entity scope required")
        if not isinstance(self.effective, EffectiveInterval) or not _covers(
            self.calendar_version.effective, self.effective
        ):
            raise InvalidCalendarPublicationIntent(
                "Publication intent exceeds version validity"
            )
        if not _aware(self.requested_at) or not self.calendar_version.knowledge.contains(
            self.requested_at
        ):
            raise InvalidCalendarPublicationIntent("Request outside version knowledge window")
        if self.expected_content_digest != self.calendar_version.content_digest:
            raise InvalidCalendarPublicationIntent("Candidate version digest precondition failed")
        if not _key(self.idempotency_key) or not _key(self.correlation_id):
            raise InvalidCalendarPublicationIntent("Canonical idempotency/correlation keys required")
        if not _text(self.reason) or not _text(self.source_ref):
            raise InvalidCalendarPublicationIntent("Nonempty canonical reason/source required")
        if self.expected_prior_version_id is not None and not isinstance(
            self.expected_prior_version_id, CalendarCandidateVersionId
        ):
            raise InvalidCalendarPublicationIntent("Typed expected prior version ID required")
        if self.expected_prior_version_id == self.calendar_version.id:
            raise InvalidCalendarPublicationIntent("Cannot supersede same version candidate")
        if not isinstance(self.role_claims, tuple) or any(
            not isinstance(claim, PublicationRoleClaimCandidate)
            for claim in self.role_claims
        ):
            raise InvalidCalendarPublicationIntent("Immutable typed role claims required")
        roles = [claim.role for claim in self.role_claims]
        actors = [claim.actor_ref for claim in self.role_claims]
        if len(roles) != len(set(roles)) or len(actors) != len(set(actors)):
            raise InvalidCalendarPublicationIntent("Duplicate roles or violated claimed SoD")
        if any(
            claim.claimed_at.astimezone(UTC) > self.requested_at.astimezone(UTC)
            or claim.expires_at.astimezone(UTC) <= self.requested_at.astimezone(UTC)
            for claim in self.role_claims
        ):
            raise InvalidCalendarPublicationIntent("Future or expired role claim")
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": "l06-publication-intent-rnd-v1",
            "status": "UNAPPROVED_UNCOMMITTED_PUBLICATION_REQUEST",
            "intent_id": str(self.id),
            "version_id": str(self.calendar_version.id),
            "calendar_id": str(self.calendar_version.calendar.id),
            "version_digest": self.calendar_version.content_digest,
            "scope": _scope(self.scope),
            "effective": {
                "start": self.effective.start.isoformat(),
                "end": self.effective.end.isoformat() if self.effective.end else None,
            },
            "requested_at": _utc(self.requested_at),
            "expected_prior_version_id": (
                str(self.expected_prior_version_id)
                if self.expected_prior_version_id is not None else None
            ),
            "expected_content_digest": self.expected_content_digest,
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "reason": self.reason,
            "source_ref": self.source_ref,
            "unverified_role_claims": [
                _claim_manifest(claim)
                for claim in sorted(self.role_claims, key=lambda item: item.role.value)
            ],
        }

    def verify_integrity(self) -> None:
        self.calendar_version.verify_integrity()
        if self.expected_content_digest != self.calendar_version.content_digest:
            raise CalendarPublicationIntentTampered("Pinned calendar digest altered")
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise CalendarPublicationIntentTampered("Publication request content altered")


@dataclass(frozen=True, slots=True)
class CalendarAuditIntentCandidate:
    """Audit *intent* only: neither durable record nor signed actor authority."""

    id: CalendarAuditIntentId
    publication_intent_id: CalendarPublicationIntentId
    correlation_id: str
    version_digest: str
    intent_action: str = "CALENDAR_PUBLICATION_REQUESTED"


@dataclass(frozen=True, slots=True)
class CalendarOutboxIntentCandidate:
    """Unsent event intent; NEVER CalendarVersionPublished."""

    id: CalendarOutboxIntentId
    publication_intent_id: CalendarPublicationIntentId
    correlation_id: str
    version_digest: str
    event_type: str = "CALENDAR_VERSION_PUBLICATION_PROPOSED"


@dataclass(frozen=True, slots=True, eq=False)
class CalendarPublicationContractDiagnostic:
    """No APPROVED/READY/COMMITTED disposition by construction."""

    request: CalendarPublicationRequestCandidate
    audit_intent: CalendarAuditIntentCandidate
    outbox_intent: CalendarOutboxIntentCandidate
    missing_role_claims: tuple[DeclaredRoleCandidate, ...]
    unverified_external_gates: tuple[UnverifiedPublicationGate, ...]
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        self._verify_fields()
        object.__setattr__(self, "content_digest", _digest(self.canonical_manifest()))

    @property
    def disposition(self) -> str:
        return "EXTERNAL_GOVERNANCE_AND_COMMIT_GATES_UNVERIFIED"

    def _verify_fields(self) -> None:
        self.request.verify_integrity()
        expected_audit, expected_outbox, missing = _intents(self.request)
        if (
            self.audit_intent != expected_audit
            or self.outbox_intent != expected_outbox
            or self.missing_role_claims != missing
            or self.unverified_external_gates != tuple(UnverifiedPublicationGate)
        ):
            raise InvalidCalendarPublicationIntent("Fabricated audit/outbox/gate claim")

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": "l06-publication-contract-rnd-v1",
            "disposition": self.disposition,
            "publication_intent_id": str(self.request.id),
            "request_digest": self.request.content_digest,
            "audit_intent_id": str(self.audit_intent.id),
            "audit_action": self.audit_intent.intent_action,
            "outbox_intent_id": str(self.outbox_intent.id),
            "outbox_event_type": self.outbox_intent.event_type,
            "correlation_id": self.request.correlation_id,
            "missing_role_claims": [role.value for role in self.missing_role_claims],
            "unverified_external_gates": [
                gate.value for gate in self.unverified_external_gates
            ],
            "committed": False,
            "event_emitted": False,
            "signed": False,
        }

    def verify_integrity(self) -> None:
        self._verify_fields()
        if _digest(self.canonical_manifest()) != self.content_digest:
            raise CalendarPublicationIntentTampered("Publication contract receipt altered")


def _intents(
    request: CalendarPublicationRequestCandidate,
) -> tuple[
    CalendarAuditIntentCandidate,
    CalendarOutboxIntentCandidate,
    tuple[DeclaredRoleCandidate, ...],
]:
    def stable_id(suffix: str):
        return uuid5(NAMESPACE_URL, f"pyaccountingkit:rnd:{request.id}:{suffix}")

    audit = CalendarAuditIntentCandidate(
        CalendarAuditIntentId(stable_id("audit")),
        request.id, request.correlation_id, request.expected_content_digest,
    )
    outbox = CalendarOutboxIntentCandidate(
        CalendarOutboxIntentId(stable_id("outbox")),
        request.id, request.correlation_id, request.expected_content_digest,
    )
    claimed = {claim.role for claim in request.role_claims}
    missing = tuple(role for role in DeclaredRoleCandidate if role not in claimed)
    return audit, outbox, missing


def preview_calendar_publication_contract(
    *, request: CalendarPublicationRequestCandidate,
    competing_intents: tuple[CalendarPublicationRequestCandidate, ...] = (),
) -> CalendarPublicationContractDiagnostic:
    """Pure negative-proof inventory; NO issue of audit/outbox nor authorization."""
    if not isinstance(request, CalendarPublicationRequestCandidate):
        raise InvalidCalendarPublicationIntent("Typed publication request required")
    if not isinstance(competing_intents, tuple):
        raise InvalidCalendarPublicationIntent("Immutable competing candidate catalog required")
    request.verify_integrity()
    seen_ids: set[CalendarPublicationIntentId] = {request.id}
    for item in competing_intents:
        if not isinstance(item, CalendarPublicationRequestCandidate):
            raise InvalidCalendarPublicationIntent("Non-typed competing publication intent")
        item.verify_integrity()
        if item.id in seen_ids:
            raise CalendarPublicationIntentConflict("Duplicate publication request identity")
        seen_ids.add(item.id)
        if item.scope != request.scope:
            raise InvalidCalendarPublicationIntent("Foreign scope in publication intent catalog")
        if item.idempotency_key == request.idempotency_key:
            raise CalendarPublicationIntentConflict(
                "Idempotency key collision needs commit authority"
            )
        if (
            item.calendar_version.calendar.id == request.calendar_version.calendar.id
            and item.effective.overlaps(request.effective)
        ):
            raise CalendarPublicationIntentConflict(
                "Overlapping publication candidates need authoritative exclusion"
            )
    audit, outbox, missing = _intents(request)
    return CalendarPublicationContractDiagnostic(
        request=request, audit_intent=audit, outbox_intent=outbox,
        missing_role_claims=missing,
        unverified_external_gates=tuple(UnverifiedPublicationGate),
    )
