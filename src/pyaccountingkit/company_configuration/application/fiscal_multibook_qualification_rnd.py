"""L06-07 multi-book candidate replay inventory (R&D, never operational E2E).

Only pure L06-02/03/05 candidate functions are composed. No authorized Book,
published CalendarVersion, SQL migration, Ledger posting, or G6 qualification.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import Enum

from ..domain.fiscal_calendar.period_controls import (
    ObservationCompleteness,
    PeriodControlCandidateDiagnostic,
    PeriodLockObservationCandidate,
    PeriodStateObservationCandidate,
    PeriodTransitionDeclarationCandidate,
    preview_period_controls_candidate,
)
from ..domain.fiscal_calendar.versions_assignments import (
    BookCalendarAssignmentCandidate,
    BookCalendarCandidateReadReceipt,
    CalendarVersionCandidate,
    preview_book_calendar_candidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.errors import DomainError
from ..domain.shared.identifiers import CalendarCandidateVersionId
from .fiscal_c10_q04_simulation import (
    SimulatedPeriodStatusQuery,
    SimulatedPeriodStatusResponse,
    inspect_simulated_period_status_wire,
    simulate_period_status_contract,
)

SCHEMA = "l06-07-multibook-replay-qualification-rnd-v1"


class InvalidMultiBookCandidate(DomainError):
    code = "INVALID_MULTIBOOK_CANDIDATE"


class MultiBookCandidateAmbiguous(DomainError):
    code = "MULTIBOOK_CANDIDATE_AMBIGUOUS"


class MultiBookQualificationTampered(DomainError):
    code = "MULTIBOOK_QUALIFICATION_TAMPERED"


class UnprovenL06ProductionGate(Enum):
    VERIFIED_ACCOUNTING_BOOK_AND_NORMATIVE_FRAMEWORK = (
        "VERIFIED_ACCOUNTING_BOOK_AND_NORMATIVE_FRAMEWORK"
    )
    APPROVED_PUBLISHED_CALENDAR_AND_AUDIT = "APPROVED_PUBLISHED_CALENDAR_AND_AUDIT"
    AUTHORITATIVE_C10_Q04_AND_LOCKS = "AUTHORITATIVE_C10_Q04_AND_LOCKS"
    SIGNED_SQL_ACTOR_AND_ISSUER = "SIGNED_SQL_ACTOR_AND_ISSUER"
    REAL_CLOSE_POST_COMMIT_FENCING = "REAL_CLOSE_POST_COMMIT_FENCING"
    REAL_MULTIBOOK_E2E_AND_MIGRATION_RECOVERY = (
        "REAL_MULTIBOOK_E2E_AND_MIGRATION_RECOVERY"
    )


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _digest(obj: dict[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            obj, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class BookCandidateFixture:
    """Explicit book-level candidate catalogs, no verified Book membership."""

    book_scope: ConfigurationScope
    assignments: tuple[BookCalendarAssignmentCandidate, ...]
    versions: tuple[CalendarVersionCandidate, ...]
    states: tuple[PeriodStateObservationCandidate, ...]
    locks: tuple[PeriodLockObservationCandidate, ...] = ()
    declarations: tuple[PeriodTransitionDeclarationCandidate, ...] = ()

    def __post_init__(self) -> None:
        self.verify_catalog()

    def verify_catalog(self) -> None:
        scope = self.book_scope
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidMultiBookCandidate("Explicit typed book scope required")
        groups = (
            (self.assignments, BookCalendarAssignmentCandidate),
            (self.versions, CalendarVersionCandidate),
            (self.states, PeriodStateObservationCandidate),
            (self.locks, PeriodLockObservationCandidate),
            (self.declarations, PeriodTransitionDeclarationCandidate),
        )
        for entries, kind in groups:
            if not isinstance(entries, tuple) or any(
                not isinstance(value, kind) for value in entries
            ):
                raise InvalidMultiBookCandidate("Immutable typed candidate catalogs required")

        versions: dict[CalendarCandidateVersionId, CalendarVersionCandidate] = {}
        for version in self.versions:
            version.verify_integrity()
            calendar_scope = version.calendar.scope
            if (
                calendar_scope.book_id is not None
                or calendar_scope.tenant_id != scope.tenant_id
                or calendar_scope.company_id != scope.company_id
                or calendar_scope.legal_entity_id != scope.legal_entity_id
            ):
                raise InvalidMultiBookCandidate("Foreign candidate calendar in book catalog")
            if version.id in versions:
                raise MultiBookCandidateAmbiguous("Duplicate calendar version identity")
            versions[version.id] = version

        assignment_ids: set[object] = set()
        for assignment in self.assignments:
            if assignment.book_scope != scope:
                raise InvalidMultiBookCandidate("Foreign assignment in book catalog")
            if assignment.id in assignment_ids:
                raise MultiBookCandidateAmbiguous("Repeated book assignment identity")
            assignment_ids.add(assignment.id)
            version = versions.get(assignment.calendar_version_id)
            if version is None or assignment.calendar_id != version.calendar.id:
                raise InvalidMultiBookCandidate("Missing exact assignment version/calendar")

        for group in (self.states, self.locks, self.declarations):
            for item in group:
                if item.book_scope != scope:
                    raise InvalidMultiBookCandidate("Foreign control candidate in book catalog")
                version = versions.get(item.calendar_version_id)
                if version is None or not any(
                    period.id == item.period_id for period in version.periods
                ):
                    raise InvalidMultiBookCandidate("Orphan control candidate period/version")


@dataclass(frozen=True, slots=True)
class BookReplayQueryCandidate:
    book_scope: ConfigurationScope
    posting_date: date
    known_at: datetime

    def __post_init__(self) -> None:
        SimulatedPeriodStatusQuery(
            book_scope=self.book_scope,
            posting_date=self.posting_date,
            known_at=self.known_at,
        )


@dataclass(frozen=True, slots=True)
class BookReplayCandidateEvidence:
    """One pinned structural+control+wire snapshot, never a transaction."""

    query: BookReplayQueryCandidate
    calendar: BookCalendarCandidateReadReceipt
    controls: PeriodControlCandidateDiagnostic
    simulated_wire: SimulatedPeriodStatusResponse

    def verify_integrity(self) -> None:
        self.calendar.verify_integrity()
        self.controls.verify_integrity()
        self.simulated_wire.verify_integrity()
        if self.controls.book_receipt is not self.calendar:
            raise MultiBookQualificationTampered("Control evidence not pinned to book receipt")
        expected = simulate_period_status_contract(
            query=SimulatedPeriodStatusQuery(
                self.query.book_scope, self.query.posting_date, self.query.known_at,
            ),
            diagnostic=self.controls,
        )
        if expected.to_wire() != self.simulated_wire.to_wire():
            raise MultiBookQualificationTampered("Simulated consumer payload changed")
        inspected = inspect_simulated_period_status_wire(
            wire=self.simulated_wire.to_wire(),
            query=SimulatedPeriodStatusQuery(
                self.query.book_scope, self.query.posting_date, self.query.known_at,
            ),
        )
        if inspected.content_digest != self.simulated_wire.content_digest:
            raise MultiBookQualificationTampered("Consumer checksum mismatch")

    def manifest(self) -> dict[str, object]:
        return {
            "book_id": str(self.query.book_scope.book_id),
            "tenant_id": self.query.book_scope.tenant_id,
            "company_id": str(self.query.book_scope.company_id),
            "legal_entity_id": str(self.query.book_scope.legal_entity_id),
            "posting_date": self.query.posting_date.isoformat(),
            "known_at": _utc(self.query.known_at),
            "assignment_id": str(self.calendar.assignment.id),
            "calendar_candidate_id": str(self.calendar.calendar_version.id),
            "period_id": str(self.calendar.period.period_id),
            "period_code": self.calendar.period.code.value,
            "calendar_receipt_digest": self.calendar.content_digest,
            "control_diagnostic_digest": self.controls.content_digest,
            "wire_digest": self.simulated_wire.content_digest,
            "observed_status": self.controls.state.status.value,
            "authority": "UNTRUSTED_CANDIDATE_SIMULATION",
            "posting_authorized": False,
        }


def _replay(
    fixtures: tuple[BookCandidateFixture, ...],
    queries: tuple[BookReplayQueryCandidate, ...],
    completeness: ObservationCompleteness,
) -> tuple[BookReplayCandidateEvidence, ...]:
    if not isinstance(fixtures, tuple) or not isinstance(queries, tuple):
        raise InvalidMultiBookCandidate("Immutable multi-book scenario tuples required")
    if len(fixtures) < 2 or not queries:
        raise InvalidMultiBookCandidate("At least two book fixtures and one query required")
    if not isinstance(completeness, ObservationCompleteness):
        raise InvalidMultiBookCandidate("Explicit unverified observation completeness required")
    by_book: dict[object, BookCandidateFixture] = {}
    base_scope: ConfigurationScope | None = None
    assignment_ids: set[object] = set()
    for item in fixtures:
        if not isinstance(item, BookCandidateFixture):
            raise InvalidMultiBookCandidate("Typed book candidate fixture required")
        item.verify_catalog()
        scope = item.book_scope
        if base_scope is None:
            base_scope = scope
        if (
            scope.tenant_id != base_scope.tenant_id
            or scope.company_id != base_scope.company_id
            or scope.legal_entity_id != base_scope.legal_entity_id
        ):
            raise InvalidMultiBookCandidate("Cross-entity fixture in multi-book scenario")
        if scope.book_id in by_book:
            raise MultiBookCandidateAmbiguous("Duplicate book in scenario")
        by_book[scope.book_id] = item
        for assignment in item.assignments:
            if assignment.id in assignment_ids:
                raise MultiBookCandidateAmbiguous("Assignment ID reused across books")
            assignment_ids.add(assignment.id)

    seen_queries: set[tuple[object, date, str]] = set()
    selected: list[BookReplayCandidateEvidence] = []
    covered_books: set[object] = set()
    for query in queries:
        if not isinstance(query, BookReplayQueryCandidate):
            raise InvalidMultiBookCandidate("Typed historical query required")
        fixture = by_book.get(query.book_scope.book_id)
        if fixture is None or fixture.book_scope != query.book_scope:
            raise InvalidMultiBookCandidate("Foreign or unregistered book query")
        key = (query.book_scope.book_id, query.posting_date, _utc(query.known_at))
        if key in seen_queries:
            raise MultiBookCandidateAmbiguous("Repeated book/date/known-at query")
        seen_queries.add(key)
        covered_books.add(query.book_scope.book_id)
        receipt = preview_book_calendar_candidate(
            book_scope=fixture.book_scope, as_of=query.posting_date,
            known_at=query.known_at,
            assignments=fixture.assignments, calendar_versions=fixture.versions,
        )
        states = tuple(
            value for value in fixture.states
            if value.calendar_version_id == receipt.calendar_version.id
            and value.period_id == receipt.period.period_id
        )
        locks = tuple(
            value for value in fixture.locks
            if value.calendar_version_id == receipt.calendar_version.id
            and value.period_id == receipt.period.period_id
        )
        declarations = tuple(
            value for value in fixture.declarations
            if value.calendar_version_id == receipt.calendar_version.id
            and value.period_id == receipt.period.period_id
        )
        controls = preview_period_controls_candidate(
            book_receipt=receipt, states=states, locks=locks,
            transitions=declarations, completeness=completeness,
        )
        status_query = SimulatedPeriodStatusQuery(
            fixture.book_scope, query.posting_date, query.known_at,
        )
        wire = simulate_period_status_contract(query=status_query, diagnostic=controls)
        proof = BookReplayCandidateEvidence(query, receipt, controls, wire)
        proof.verify_integrity()
        selected.append(proof)
    if covered_books != set(by_book):
        raise InvalidMultiBookCandidate("Every supplied book must have replay evidence")
    return tuple(sorted(
        selected,
        key=lambda x: (
            str(x.query.book_scope.book_id),
            x.query.posting_date.isoformat(), _utc(x.query.known_at),
        ),
    ))


@dataclass(frozen=True, slots=True, eq=False)
class MultiBookReplayCandidateReport:
    """All real production acceptance gates remain UNPROVEN, no G6 GO."""

    fixtures: tuple[BookCandidateFixture, ...]
    queries: tuple[BookReplayQueryCandidate, ...]
    completeness: ObservationCompleteness
    evidence: tuple[BookReplayCandidateEvidence, ...]
    unproven_gates: tuple[UnprovenL06ProductionGate, ...]
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        self._validate()
        object.__setattr__(self, "content_digest", _digest(self.manifest()))

    def _validate(self) -> None:
        expected = _replay(self.fixtures, self.queries, self.completeness)
        if tuple(item.manifest() for item in self.evidence) != tuple(
            item.manifest() for item in expected
        ):
            raise MultiBookQualificationTampered("Fabricated multi-book replay evidence")
        for item in self.evidence:
            item.verify_integrity()
        if self.unproven_gates != tuple(UnprovenL06ProductionGate):
            raise MultiBookQualificationTampered("Production qualification falsely elevated")

    def manifest(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "disposition": "MULTIBOOK_CANDIDATE_REPLAY_ONLY_NO_G6_GO",
            "completeness": self.completeness.value,
            "evidence": [item.manifest() for item in self.evidence],
            "unproven_production_gates": [x.value for x in self.unproven_gates],
            "live_e2e_qualified": False,
            "posting_authorized": False,
            "published": False,
            "migration_to_production_qualified": False,
        }

    def verify_integrity(self) -> None:
        self._validate()
        if _digest(self.manifest()) != self.content_digest:
            raise MultiBookQualificationTampered("Multi-book replay digest changed")


def qualify_multibook_candidate_replay(
    *,
    fixtures: tuple[BookCandidateFixture, ...],
    queries: tuple[BookReplayQueryCandidate, ...],
    completeness: ObservationCompleteness,
) -> MultiBookReplayCandidateReport:
    """Pure fixture replay; NOT CAL-L7 live E2E/qualification sign-off."""
    evidence = _replay(fixtures, queries, completeness)
    return MultiBookReplayCandidateReport(
        fixtures=fixtures, queries=queries, completeness=completeness,
        evidence=evidence, unproven_gates=tuple(UnprovenL06ProductionGate),
    )
