"""L06-02 — immutable calendar-version and book-assignment *candidates*.

This module has no published CalendarVersion, signed evidence, live Book,
C10-Q04 period-status authority, lock, transition or Ledger posting API.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval, KnowledgeInterval
from ..shared.errors import DomainError
from ..shared.identifiers import (
    AccountingPeriodId,
    BookCalendarAssignmentCandidateId,
    CalendarCandidateVersionId,
    FiscalCalendarId,
)
from .model import (
    AccountingPeriodDraft,
    CalendarCoveragePolicy,
    FiscalCalendarDraft,
    FiscalPeriodCandidatePreview,
    FiscalYearDraft,
    preview_adjustment_period_candidate,
    preview_ordinary_period_candidate,
    validate_fiscal_structure,
)


class InvalidCalendarCandidateVersion(DomainError):
    code = "INVALID_CALENDAR_CANDIDATE_VERSION"


class InvalidBookCalendarAssignment(DomainError):
    code = "INVALID_BOOK_CALENDAR_ASSIGNMENT_CANDIDATE"


class BookCalendarCandidateMissing(DomainError):
    code = "BOOK_CALENDAR_CANDIDATE_MISSING"


class BookCalendarCandidateAmbiguous(DomainError):
    code = "BOOK_CALENDAR_CANDIDATE_AMBIGUOUS"


class CalendarCandidateDigestMismatch(DomainError):
    code = "CALENDAR_CANDIDATE_DIGEST_MISMATCH"


SCHEMA = "l06-rnd-calendar-v1"


def _date_interval(value: EffectiveInterval) -> dict[str, str | None]:
    return {
        "start": value.start.isoformat(),
        "end": value.end.isoformat() if value.end is not None else None,
    }


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _knowledge_interval(value: KnowledgeInterval) -> dict[str, str | None]:
    return {
        "start": _utc(value.start),
        "end": _utc(value.end) if value.end is not None else None,
    }


def _scope(value: ConfigurationScope) -> dict[str, str | None]:
    return {
        "tenant": value.tenant_id,
        "company": str(value.company_id),
        "legal_entity": str(value.legal_entity_id),
        "book": str(value.book_id) if value.book_id is not None else None,
    }


def _covers(outer: EffectiveInterval, inner: EffectiveInterval) -> bool:
    return outer.start <= inner.start and (
        outer.end is None or (inner.end is not None and inner.end <= outer.end)
    )


def _hash(manifest: dict[str, object]) -> str:
    payload = json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _source(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _related_scope(book: ConfigurationScope, calendar: ConfigurationScope) -> bool:
    return (
        book.book_id is not None
        and calendar.book_id is None
        and book.tenant_id == calendar.tenant_id
        and book.company_id == calendar.company_id
        and book.legal_entity_id == calendar.legal_entity_id
    )


def _cutoff(day: date, instant: datetime) -> None:
    if type(day) is not date:
        raise InvalidBookCalendarAssignment("Explicit business date required")
    if (
        type(instant) is not datetime
        or instant.tzinfo is None
        or instant.utcoffset() is None
    ):
        raise InvalidBookCalendarAssignment("Timezone-aware known_at instant required")


@dataclass(frozen=True, slots=True, eq=False)
class CalendarVersionCandidate:
    """Sealed in-process structure and knowledge window; never published."""

    id: CalendarCandidateVersionId
    calendar: FiscalCalendarDraft
    years: tuple[FiscalYearDraft, ...]
    periods: tuple[AccountingPeriodDraft, ...]
    coverage_policy: CalendarCoveragePolicy
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, CalendarCandidateVersionId):
            raise InvalidCalendarCandidateVersion("Typed calendar candidate version ID required")
        if not isinstance(self.calendar, FiscalCalendarDraft):
            raise InvalidCalendarCandidateVersion("Typed calendar draft required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidCalendarCandidateVersion("Effective and knowledge windows required")
        if not _source(self.source_ref):
            raise InvalidCalendarCandidateVersion("Canonical source_ref required")
        if not _covers(self.calendar.effective, self.effective):
            raise InvalidCalendarCandidateVersion("Version validity exceeds its calendar")
        validate_fiscal_structure(
            calendar=self.calendar, years=self.years, periods=self.periods,
            coverage_policy=self.coverage_policy,
        )
        if any(not _covers(self.effective, y.effective) for y in self.years):
            raise InvalidCalendarCandidateVersion("Fiscal year outside candidate version validity")
        object.__setattr__(self, "content_digest", _hash(self.canonical_manifest()))

    def canonical_manifest(self) -> dict[str, object]:
        c = self.calendar
        return {
            "schema": SCHEMA,
            "status": "UNPUBLISHED_CALENDAR_RND_CANDIDATE",
            "version_id": str(self.id),
            "calendar": {
                "id": str(c.id),
                "scope": _scope(c.scope),
                "code": c.code.value,
                "label": c.label,
                "jurisdiction_ref": c.jurisdiction_ref,
                "source_ref": c.source_ref,
                "effective": _date_interval(c.effective),
            },
            "coverage_policy": self.coverage_policy.value,
            "effective": _date_interval(self.effective),
            "knowledge": _knowledge_interval(self.knowledge),
            "source_ref": self.source_ref,
            "years": [
                {
                    "id": str(y.id), "calendar_id": str(y.calendar_id),
                    "scope": _scope(y.scope), "code": y.code.value,
                    "effective": _date_interval(y.effective), "source_ref": y.source_ref,
                }
                for y in sorted(self.years, key=lambda y: str(y.id))
            ],
            "periods": [
                {
                    "id": str(p.id), "calendar_id": str(p.calendar_id),
                    "fiscal_year_id": str(p.fiscal_year_id), "scope": _scope(p.scope),
                    "code": p.code.value, "kind": p.kind.value,
                    "ordinal": p.ordinal,
                    "adjustment_target_id": (
                        str(p.adjustment_target_id)
                        if p.adjustment_target_id is not None else None
                    ),
                    "effective": _date_interval(p.effective),
                    "source_ref": p.source_ref,
                }
                for p in sorted(self.periods, key=lambda p: str(p.id))
            ],
        }

    def verify_integrity(self) -> None:
        validate_fiscal_structure(
            calendar=self.calendar, years=self.years, periods=self.periods,
            coverage_policy=self.coverage_policy,
        )
        if _hash(self.canonical_manifest()) != self.content_digest:
            raise CalendarCandidateDigestMismatch("Calendar candidate manifest changed")


@dataclass(frozen=True, slots=True)
class BookCalendarAssignmentCandidate:
    """Unapproved book -> ONE exact calendar candidate version and time window."""

    id: BookCalendarAssignmentCandidateId
    book_scope: ConfigurationScope
    calendar_id: FiscalCalendarId
    calendar_version_id: CalendarCandidateVersionId
    effective: EffectiveInterval
    knowledge: KnowledgeInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, BookCalendarAssignmentCandidateId):
            raise InvalidBookCalendarAssignment("Typed assignment candidate ID required")
        if (
            not isinstance(self.book_scope, ConfigurationScope)
            or self.book_scope.book_id is None
        ):
            raise InvalidBookCalendarAssignment("Explicit typed book scope required")
        if not isinstance(self.calendar_id, FiscalCalendarId):
            raise InvalidBookCalendarAssignment("Typed calendar ID required")
        if not isinstance(self.calendar_version_id, CalendarCandidateVersionId):
            raise InvalidBookCalendarAssignment("Exact typed calendar version ID required")
        if not isinstance(self.effective, EffectiveInterval) or not isinstance(
            self.knowledge, KnowledgeInterval
        ):
            raise InvalidBookCalendarAssignment("Business and knowledge windows required")
        if not _source(self.source_ref):
            raise InvalidBookCalendarAssignment("Canonical assignment source_ref required")


@dataclass(frozen=True, slots=True, eq=False)
class BookCalendarCandidateReadReceipt:
    """Reproducible unsigned *structural* preview, NOT GetPeriodStatus."""

    assignment: BookCalendarAssignmentCandidate
    calendar_version: CalendarVersionCandidate
    period: FiscalPeriodCandidatePreview
    as_of: date
    known_at: datetime
    adjustment_period_id: AccountingPeriodId | None = None
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.assignment, BookCalendarAssignmentCandidate) or not isinstance(
            self.calendar_version, CalendarVersionCandidate
        ):
            raise InvalidBookCalendarAssignment("Typed assignment and calendar version required")
        if not isinstance(self.period, FiscalPeriodCandidatePreview):
            raise InvalidBookCalendarAssignment("Typed structural period preview required")
        _cutoff(self.as_of, self.known_at)
        if self.adjustment_period_id is not None and not isinstance(
            self.adjustment_period_id, AccountingPeriodId
        ):
            raise InvalidBookCalendarAssignment("Typed special period selector required")
        self._verify_relation()
        object.__setattr__(self, "content_digest", _hash(self.canonical_manifest()))

    def _verify_relation(self) -> None:
        a, v = self.assignment, self.calendar_version
        v.verify_integrity()
        if (
            a.calendar_id != v.calendar.id
            or a.calendar_version_id != v.id
            or not _related_scope(a.book_scope, v.calendar.scope)
            or not _covers(v.effective, a.effective)
            or not a.effective.contains(self.as_of)
            or not v.effective.contains(self.as_of)
            or not a.knowledge.contains(self.known_at)
            or not v.knowledge.contains(self.known_at)
        ):
            raise InvalidBookCalendarAssignment(
                "Assignment/calendar version scope or time mismatch"
            )
        if self.adjustment_period_id is None:
            expected = preview_ordinary_period_candidate(
                calendar=v.calendar, years=v.years, periods=v.periods,
                coverage_policy=v.coverage_policy, as_of=self.as_of,
            )
        else:
            expected = preview_adjustment_period_candidate(
                calendar=v.calendar, years=v.years, periods=v.periods,
                coverage_policy=v.coverage_policy, as_of=self.as_of,
                adjustment_period_id=self.adjustment_period_id,
            )
        if self.period != expected:
            raise InvalidBookCalendarAssignment("Fabricated or stale period preview")

    def canonical_manifest(self) -> dict[str, object]:
        a = self.assignment
        return {
            "schema": SCHEMA,
            "status": "UNPUBLISHED_STRUCTURAL_PERIOD_PREVIEW",
            "assignment_id": str(a.id),
            "book_scope": _scope(a.book_scope),
            "calendar_id": str(a.calendar_id),
            "calendar_version_id": str(a.calendar_version_id),
            "calendar_version_digest": self.calendar_version.content_digest,
            "assignment_effective": _date_interval(a.effective),
            "assignment_knowledge": _knowledge_interval(a.knowledge),
            "assignment_source_ref": a.source_ref,
            "as_of": self.as_of.isoformat(), "known_at": _utc(self.known_at),
            "period_id": str(self.period.period_id),
            "fiscal_year_id": str(self.period.fiscal_year_id),
            "period_code": self.period.code.value,
            "period_kind": self.period.kind.value,
            "adjustment_period_id": (
                str(self.adjustment_period_id)
                if self.adjustment_period_id is not None else None
            ),
            "adjustment_target_id": (
                str(self.period.adjustment_target_id)
                if self.period.adjustment_target_id is not None else None
            ),
        }

    def verify_integrity(self) -> None:
        self._verify_relation()
        if _hash(self.canonical_manifest()) != self.content_digest:
            raise CalendarCandidateDigestMismatch("Book-calendar candidate receipt changed")


def preview_book_calendar_candidate(
    *,
    book_scope: ConfigurationScope,
    as_of: date,
    known_at: datetime,
    assignments: tuple[BookCalendarAssignmentCandidate, ...],
    calendar_versions: tuple[CalendarVersionCandidate, ...],
    adjustment_period_id: AccountingPeriodId | None = None,
) -> BookCalendarCandidateReadReceipt:
    """Fail closed on foreign scope, ambiguity and absent pinned historical version."""
    if not isinstance(book_scope, ConfigurationScope) or book_scope.book_id is None:
        raise InvalidBookCalendarAssignment("Book-level scope required")
    _cutoff(as_of, known_at)
    if adjustment_period_id is not None and not isinstance(
        adjustment_period_id, AccountingPeriodId
    ):
        raise InvalidBookCalendarAssignment("Typed adjustment ID required")
    if not isinstance(assignments, tuple) or not isinstance(calendar_versions, tuple):
        raise InvalidBookCalendarAssignment("Immutable catalog tuples required")
    seen_assignments: set[BookCalendarAssignmentCandidateId] = set()
    active: list[BookCalendarAssignmentCandidate] = []
    for item in assignments:
        if not isinstance(item, BookCalendarAssignmentCandidate):
            raise InvalidBookCalendarAssignment("Non-assignment in book catalog")
        if item.id in seen_assignments:
            raise BookCalendarCandidateAmbiguous("Duplicate assignment identity")
        seen_assignments.add(item.id)
        if item.book_scope != book_scope:
            raise InvalidBookCalendarAssignment("Foreign book scope in assignment catalog")
        if item.effective.contains(as_of) and item.knowledge.contains(known_at):
            active.append(item)
    if not active:
        raise BookCalendarCandidateMissing("No calendar assignment for book/date/known_at")
    if len(active) != 1:
        raise BookCalendarCandidateAmbiguous("Concurrent active book-calendar assignments")

    versions: dict[CalendarCandidateVersionId, CalendarVersionCandidate] = {}
    for value in calendar_versions:
        if not isinstance(value, CalendarVersionCandidate):
            raise InvalidCalendarCandidateVersion("Non-calendar version in catalog")
        if not _related_scope(book_scope, value.calendar.scope):
            raise InvalidCalendarCandidateVersion("Foreign entity calendar in candidate catalog")
        if value.id in versions:
            raise BookCalendarCandidateAmbiguous("Duplicate candidate calendar version identity")
        value.verify_integrity()
        versions[value.id] = value

    chosen = active[0]
    version = versions.get(chosen.calendar_version_id)
    if version is None:
        raise BookCalendarCandidateMissing("Exact assigned calendar version unavailable")
    if (
        chosen.calendar_id != version.calendar.id
        or not _covers(version.effective, chosen.effective)
        or not version.effective.contains(as_of)
        or not version.knowledge.contains(known_at)
    ):
        raise InvalidBookCalendarAssignment(
            "Assigned calendar version identity or business/knowledge time mismatch"
        )
    if adjustment_period_id is None:
        selected = preview_ordinary_period_candidate(
            calendar=version.calendar, years=version.years, periods=version.periods,
            coverage_policy=version.coverage_policy, as_of=as_of,
        )
    else:
        selected = preview_adjustment_period_candidate(
            calendar=version.calendar, years=version.years, periods=version.periods,
            coverage_policy=version.coverage_policy, as_of=as_of,
            adjustment_period_id=adjustment_period_id,
        )
    return BookCalendarCandidateReadReceipt(
        assignment=chosen, calendar_version=version, period=selected,
        as_of=as_of, known_at=known_at, adjustment_period_id=adjustment_period_id,
    )
