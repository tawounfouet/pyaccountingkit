"""L06-03 — unsigned read-only period state, locks and transition diagnostics.

Not a published status, signed audit, authoritative lock inventory, C10-Q04,
commit-time guard, close/reopen command or posting authorization.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import KnowledgeInterval
from ..shared.errors import DomainError
from ..shared.identifiers import (
    AccountingPeriodId,
    CalendarCandidateVersionId,
    PeriodLockCandidateId,
    PeriodStateCandidateId,
    PeriodTransitionCandidateId,
)
from .versions_assignments import BookCalendarCandidateReadReceipt


class InvalidPeriodControlCandidate(DomainError):
    code = "INVALID_PERIOD_CONTROL_CANDIDATE"


class PeriodControlCandidateMissing(DomainError):
    code = "PERIOD_CONTROL_CANDIDATE_MISSING"


class PeriodControlCandidateAmbiguous(DomainError):
    code = "PERIOD_CONTROL_CANDIDATE_AMBIGUOUS"


class PeriodControlCandidateDigestMismatch(DomainError):
    code = "PERIOD_CONTROL_CANDIDATE_DIGEST_MISMATCH"


class PeriodStatusCandidate(Enum):
    DRAFT = "DRAFT"
    FUTURE = "FUTURE"
    OPEN = "OPEN"
    SOFT_CLOSED = "SOFT_CLOSED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class PeriodLockScopeCandidate(Enum):
    GLOBAL_BOOK_LOCK = "GLOBAL_BOOK_LOCK"
    JOURNAL_LOCK = "JOURNAL_LOCK"
    SOURCE_LOCK = "SOURCE_LOCK"
    OPERATION_LOCK = "OPERATION_LOCK"


class ObservationCompleteness(Enum):
    """Unverified catalog declaration, NOT authoritative lock completeness."""

    DECLARED_COMPLETE_RND = "DECLARED_COMPLETE_RND"
    INCOMPLETE_RND = "INCOMPLETE_RND"


class PeriodControlDiagnosticDisposition(Enum):
    NON_OPEN_CANDIDATE_STATUS = "NON_OPEN_CANDIDATE_STATUS"
    LOCKS_OBSERVED_SCOPE_UNEVALUATED = "LOCKS_OBSERVED_SCOPE_UNEVALUATED"
    NO_OBSERVED_LOCKS_UNVERIFIED = "NO_OBSERVED_LOCKS_UNVERIFIED"
    INCOMPLETE_CANDIDATE_EVIDENCE = "INCOMPLETE_CANDIDATE_EVIDENCE"


def _source(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _aware(value: datetime) -> bool:
    return (
        type(value) is datetime
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _knowledge(value: KnowledgeInterval) -> dict[str, str | None]:
    return {
        "start": _utc(value.start),
        "end": _utc(value.end) if value.end is not None else None,
    }


def _scope(value: ConfigurationScope) -> dict[str, str]:
    return {
        "tenant": value.tenant_id,
        "company": str(value.company_id),
        "entity": str(value.legal_entity_id),
        "book": str(value.book_id),
    }


def _hash(manifest: dict[str, object]) -> str:
    raw = json.dumps(
        manifest, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _identity(
    scope: ConfigurationScope,
    version_id: CalendarCandidateVersionId,
    period_id: AccountingPeriodId,
    knowledge: KnowledgeInterval,
    source_ref: str,
) -> None:
    if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
        raise InvalidPeriodControlCandidate("Typed book-level scope required")
    if not isinstance(version_id, CalendarCandidateVersionId) or not isinstance(
        period_id, AccountingPeriodId
    ):
        raise InvalidPeriodControlCandidate("Typed calendar version and period IDs required")
    if not isinstance(knowledge, KnowledgeInterval) or not _source(source_ref):
        raise InvalidPeriodControlCandidate("Aware knowledge window and source required")


@dataclass(frozen=True, slots=True)
class PeriodStateObservationCandidate:
    """One unsigned state observation of a pinned period and book."""

    id: PeriodStateCandidateId
    book_scope: ConfigurationScope
    calendar_version_id: CalendarCandidateVersionId
    period_id: AccountingPeriodId
    status: PeriodStatusCandidate
    state_revision: int
    knowledge: KnowledgeInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, PeriodStateCandidateId):
            raise InvalidPeriodControlCandidate("Typed state observation ID required")
        _identity(
            self.book_scope, self.calendar_version_id, self.period_id,
            self.knowledge, self.source_ref,
        )
        if not isinstance(self.status, PeriodStatusCandidate):
            raise InvalidPeriodControlCandidate("Typed period status required")
        if type(self.state_revision) is not int or self.state_revision <= 0:
            raise InvalidPeriodControlCandidate("Positive state revision required")


@dataclass(frozen=True, slots=True)
class PeriodLockObservationCandidate:
    """One observed lock revision; absence of a lock is not evidence of permission."""

    id: PeriodLockCandidateId
    book_scope: ConfigurationScope
    calendar_version_id: CalendarCandidateVersionId
    period_id: AccountingPeriodId
    lock_scope: PeriodLockScopeCandidate
    target_code: str | None
    active: bool
    revision: int
    knowledge: KnowledgeInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, PeriodLockCandidateId):
            raise InvalidPeriodControlCandidate("Typed lock observation ID required")
        _identity(
            self.book_scope, self.calendar_version_id, self.period_id,
            self.knowledge, self.source_ref,
        )
        if not isinstance(self.lock_scope, PeriodLockScopeCandidate):
            raise InvalidPeriodControlCandidate("Typed lock scope required")
        if self.lock_scope is PeriodLockScopeCandidate.GLOBAL_BOOK_LOCK:
            if self.target_code is not None:
                raise InvalidPeriodControlCandidate("Global book lock must have no target")
        elif (
            not isinstance(self.target_code, str)
            or re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", self.target_code) is None
        ):
            raise InvalidPeriodControlCandidate("Scoped lock requires canonical target")
        if type(self.active) is not bool:
            raise InvalidPeriodControlCandidate("Explicit boolean lock state required")
        if type(self.revision) is not int or self.revision <= 0:
            raise InvalidPeriodControlCandidate("Positive lock revision required")


@dataclass(frozen=True, slots=True)
class PeriodTransitionDeclarationCandidate:
    """Proposed historical transition, NOT an executed or audited command."""

    id: PeriodTransitionCandidateId
    book_scope: ConfigurationScope
    calendar_version_id: CalendarCandidateVersionId
    period_id: AccountingPeriodId
    from_status: PeriodStatusCandidate
    to_status: PeriodStatusCandidate
    expected_revision: int
    proposed_revision: int
    declared_at: datetime
    actor_ref: str
    reason: str
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, PeriodTransitionCandidateId):
            raise InvalidPeriodControlCandidate("Typed transition declaration ID required")
        if not isinstance(self.book_scope, ConfigurationScope) or (
            self.book_scope.book_id is None
        ):
            raise InvalidPeriodControlCandidate("Book-level transition scope required")
        if not isinstance(self.calendar_version_id, CalendarCandidateVersionId) or (
            not isinstance(self.period_id, AccountingPeriodId)
        ):
            raise InvalidPeriodControlCandidate("Typed transition period/version IDs required")
        if not isinstance(self.from_status, PeriodStatusCandidate) or not isinstance(
            self.to_status, PeriodStatusCandidate
        ) or self.from_status is self.to_status:
            raise InvalidPeriodControlCandidate("Distinct typed transition states required")
        if (
            type(self.expected_revision) is not int
            or self.expected_revision < 0
            or type(self.proposed_revision) is not int
            or self.proposed_revision != self.expected_revision + 1
        ):
            raise InvalidPeriodControlCandidate("Monotonic declared transition revision")
        if not _aware(self.declared_at) or not all(
            _source(value) for value in (
                self.actor_ref, self.reason, self.source_ref
            )
        ):
            raise InvalidPeriodControlCandidate(
            "Aware declaration and source/reason/actor required"
        )


def _state_manifest(item: PeriodStateObservationCandidate) -> dict[str, object]:
    return {
        "id": str(item.id),
        "scope": _scope(item.book_scope),
        "version_id": str(item.calendar_version_id),
        "period_id": str(item.period_id),
        "status": item.status.value,
        "revision": item.state_revision,
        "knowledge": _knowledge(item.knowledge),
        "source_ref": item.source_ref,
    }


def _lock_manifest(item: PeriodLockObservationCandidate) -> dict[str, object]:
    return {
        "id": str(item.id),
        "scope": _scope(item.book_scope),
        "version_id": str(item.calendar_version_id),
        "period_id": str(item.period_id),
        "lock_scope": item.lock_scope.value,
        "target_code": item.target_code,
        "active": item.active,
        "revision": item.revision,
        "knowledge": _knowledge(item.knowledge),
        "source_ref": item.source_ref,
    }


def _transition_manifest(item: PeriodTransitionDeclarationCandidate) -> dict[str, object]:
    return {
        "id": str(item.id),
        "scope": _scope(item.book_scope),
        "version_id": str(item.calendar_version_id),
        "period_id": str(item.period_id),
        "from": item.from_status.value,
        "to": item.to_status.value,
        "expected_revision": item.expected_revision,
        "proposed_revision": item.proposed_revision,
        "declared_at": _utc(item.declared_at),
        "actor_ref": item.actor_ref,
        "reason": item.reason,
        "source_ref": item.source_ref,
    }


def _validate_catalog(
    *,
    book_receipt: BookCalendarCandidateReadReceipt,
    states: tuple[PeriodStateObservationCandidate, ...],
    locks: tuple[PeriodLockObservationCandidate, ...],
    transitions: tuple[PeriodTransitionDeclarationCandidate, ...],
) -> None:
    book_receipt.verify_integrity()
    if any(not isinstance(seq, tuple) for seq in (states, locks, transitions)):
        raise InvalidPeriodControlCandidate("Immutable typed catalogs required")
    scope = book_receipt.assignment.book_scope
    version_id = book_receipt.calendar_version.id
    period_id = book_receipt.period.period_id
    for collection, kind in (
        (states, PeriodStateObservationCandidate),
        (locks, PeriodLockObservationCandidate),
        (transitions, PeriodTransitionDeclarationCandidate),
    ):
        if any(not isinstance(item, kind) for item in collection):
            raise InvalidPeriodControlCandidate("Non-typed period control observation")
        for item in collection:
            if (
                item.book_scope != scope
                or item.calendar_version_id != version_id
                or item.period_id != period_id
            ):
                raise InvalidPeriodControlCandidate("Foreign period/book/version control data")

    seen_state: set[PeriodStateCandidateId] = set()
    seen_revisions: set[int] = set()
    for i, item in enumerate(states):
        if item.id in seen_state or item.state_revision in seen_revisions:
            raise PeriodControlCandidateAmbiguous("Duplicate state ID or revision")
        seen_state.add(item.id)
        seen_revisions.add(item.state_revision)
        if any(item.knowledge.overlaps(other.knowledge) for other in states[i + 1:]):
            raise PeriodControlCandidateAmbiguous("Concurrent state observations")
    ordered = sorted(states, key=lambda x: x.knowledge.start.astimezone(UTC))
    if any(
        left.state_revision >= right.state_revision
        for left, right in zip(ordered, ordered[1:], strict=False)
    ):
        raise InvalidPeriodControlCandidate("State revisions regress with knowledge time")

    by_lock: dict[PeriodLockCandidateId, list[PeriodLockObservationCandidate]] = {}
    for item in locks:
        by_lock.setdefault(item.id, []).append(item)
    for entries in by_lock.values():
        seen: set[int] = set()
        for i, item in enumerate(entries):
            if item.revision in seen:
                raise PeriodControlCandidateAmbiguous("Duplicate lock revision")
            seen.add(item.revision)
            if any(item.knowledge.overlaps(other.knowledge) for other in entries[i + 1:]):
                raise PeriodControlCandidateAmbiguous("Overlapping lock revisions")
            if any(
                (item.lock_scope, item.target_code) != (
                    other.lock_scope, other.target_code
                )
                for other in entries
            ):
                raise InvalidPeriodControlCandidate("Lock identity changed its target")
        ordered_lock = sorted(entries, key=lambda x: x.knowledge.start.astimezone(UTC))
        if any(
            left.revision >= right.revision
            for left, right in zip(ordered_lock, ordered_lock[1:], strict=False)
        ):
            raise InvalidPeriodControlCandidate("Lock revisions regress with knowledge time")

    seen_events: set[PeriodTransitionCandidateId] = set()
    for item in transitions:
        if item.id in seen_events:
            raise PeriodControlCandidateAmbiguous("Duplicate transition declaration ID")
        seen_events.add(item.id)


@dataclass(frozen=True, slots=True, eq=False)
class PeriodControlCandidateDiagnostic:
    """All observed context and source-bound checksums; never posting eligibility."""

    book_receipt: BookCalendarCandidateReadReceipt
    states: tuple[PeriodStateObservationCandidate, ...]
    locks: tuple[PeriodLockObservationCandidate, ...]
    transitions: tuple[PeriodTransitionDeclarationCandidate, ...]
    completeness: ObservationCompleteness
    state: PeriodStateObservationCandidate
    observed_active_locks: tuple[PeriodLockObservationCandidate, ...]
    visible_declarations: tuple[PeriodTransitionDeclarationCandidate, ...]
    disposition: PeriodControlDiagnosticDisposition
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        self._validate()
        object.__setattr__(self, "content_digest", _hash(self.canonical_manifest()))

    def _validate(self) -> None:
        _validate_catalog(
            book_receipt=self.book_receipt, states=self.states,
            locks=self.locks, transitions=self.transitions,
        )
        if not isinstance(self.completeness, ObservationCompleteness):
            raise InvalidPeriodControlCandidate("Typed completeness declaration required")
        known_at = self.book_receipt.known_at
        matching = [s for s in self.states if s.knowledge.contains(known_at)]
        if len(matching) != 1 or self.state is not matching[0]:
            raise InvalidPeriodControlCandidate("Fabricated/stale selected state")
        active = tuple(
            sorted(
                (
                    item for item in self.locks
                    if item.active and item.knowledge.contains(known_at)
                ),
                key=lambda item: str(item.id),
            )
        )
        declarations = tuple(
            sorted(
                (t for t in self.transitions if t.declared_at.astimezone(UTC)
                 <= known_at.astimezone(UTC)),
                key=lambda t: str(t.id),
            )
        )
        if self.observed_active_locks != active or self.visible_declarations != declarations:
            raise InvalidPeriodControlCandidate("Fabricated lock/transition evidence")
        expected = _disposition(self.state, active, self.completeness)
        if self.disposition is not expected:
            raise InvalidPeriodControlCandidate("Fabricated diagnostic disposition")

    def canonical_manifest(self) -> dict[str, object]:
        return {
            "schema": "l06-period-control-rnd-v1",
            "status": "UNPUBLISHED_NONAUTHORITATIVE_PERIOD_DIAGNOSTIC",
            "book_receipt_digest": self.book_receipt.content_digest,
            "known_at": _utc(self.book_receipt.known_at),
            "as_of": self.book_receipt.as_of.isoformat(),
            "completeness": self.completeness.value,
            "disposition": self.disposition.value,
            "selected_state_id": str(self.state.id),
            "all_states": [
                _state_manifest(x) for x in sorted(self.states, key=lambda x: str(x.id))
            ],
            "all_locks": [
                _lock_manifest(x) for x in sorted(
                    self.locks, key=lambda x: (str(x.id), x.revision)
                )
            ],
            "all_transition_declarations": [
                _transition_manifest(x) for x in sorted(
                    self.transitions, key=lambda x: str(x.id)
                )
            ],
            "active_lock_ids": [str(x.id) for x in self.observed_active_locks],
            "visible_transition_ids": [str(x.id) for x in self.visible_declarations],
        }

    def verify_integrity(self) -> None:
        self._validate()
        if _hash(self.canonical_manifest()) != self.content_digest:
            raise PeriodControlCandidateDigestMismatch("Period control diagnostic changed")


def _disposition(
    state: PeriodStateObservationCandidate,
    locks: tuple[PeriodLockObservationCandidate, ...],
    completeness: ObservationCompleteness,
) -> PeriodControlDiagnosticDisposition:
    if completeness is ObservationCompleteness.INCOMPLETE_RND:
        return PeriodControlDiagnosticDisposition.INCOMPLETE_CANDIDATE_EVIDENCE
    if state.status is not PeriodStatusCandidate.OPEN:
        return PeriodControlDiagnosticDisposition.NON_OPEN_CANDIDATE_STATUS
    if locks:
        return PeriodControlDiagnosticDisposition.LOCKS_OBSERVED_SCOPE_UNEVALUATED
    return PeriodControlDiagnosticDisposition.NO_OBSERVED_LOCKS_UNVERIFIED


def preview_period_controls_candidate(
    *,
    book_receipt: BookCalendarCandidateReadReceipt,
    states: tuple[PeriodStateObservationCandidate, ...],
    locks: tuple[PeriodLockObservationCandidate, ...],
    transitions: tuple[PeriodTransitionDeclarationCandidate, ...],
    completeness: ObservationCompleteness,
) -> PeriodControlCandidateDiagnostic:
    """Read historical candidate observations; NEVER decide posting eligibility."""
    if not isinstance(book_receipt, BookCalendarCandidateReadReceipt):
        raise InvalidPeriodControlCandidate("Typed book-calendar candidate receipt required")
    if not isinstance(completeness, ObservationCompleteness):
        raise InvalidPeriodControlCandidate("Explicit candidate completeness required")
    _validate_catalog(
        book_receipt=book_receipt, states=states, locks=locks, transitions=transitions,
    )
    known_at = book_receipt.known_at
    matches = [item for item in states if item.knowledge.contains(known_at)]
    if not matches:
        raise PeriodControlCandidateMissing("No state observation at knowledge cutoff")
    if len(matches) != 1:
        raise PeriodControlCandidateAmbiguous("Concurrent applicable state observations")
    active = tuple(sorted(
        (item for item in locks if item.active and item.knowledge.contains(known_at)),
        key=lambda item: str(item.id),
    ))
    declared = tuple(sorted(
        (
            item for item in transitions
            if item.declared_at.astimezone(UTC) <= known_at.astimezone(UTC)
        ),
        key=lambda item: str(item.id),
    ))
    return PeriodControlCandidateDiagnostic(
        book_receipt=book_receipt, states=states, locks=locks,
        transitions=transitions, completeness=completeness, state=matches[0],
        observed_active_locks=active, visible_declarations=declared,
        disposition=_disposition(matches[0], active, completeness),
    )
