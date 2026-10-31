"""L06-05 — C10-Q04 *shape* and consumer simulation; NEVER the live C10 port.

This is an UNTRUSTED R&D wire fixture, not an authenticated authoritative
GetPeriodStatus response or a Ledger COMMIT guard. Even OPEN/zero locks must
always be rejected when the consumer asks for posting authority.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import ClassVar

from ..domain.fiscal_calendar.period_controls import (
    PeriodControlCandidateDiagnostic,
    PeriodControlDiagnosticDisposition,
    PeriodLockScopeCandidate,
    PeriodStatusCandidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.errors import DomainError
from ..domain.shared.identifiers import (
    AccountingBookId,
    AccountingPeriodId,
    CalendarCandidateVersionId,
    CompanyId,
    LegalEntityId,
)

SCHEMA_VERSION = "l06-05-c10-q04-simulation-v0"
AUTHORITY = "UNTRUSTED_CANDIDATE_SIMULATION"
DIGEST = re.compile(r"sha256:[a-f0-9]{64}\Z")
UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z"
)


class InvalidPeriodStatusSimulation(DomainError):
    code = "INVALID_PERIOD_STATUS_SIMULATION"


class UntrustedPeriodStatusForPosting(DomainError):
    code = "UNTRUSTED_PERIOD_STATUS_FOR_POSTING"


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _digest(value: dict[str, object]) -> str:
    data = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _check_time(value: datetime) -> None:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidPeriodStatusSimulation("Timezone-aware known_at required")


def _check_digest(value: str) -> None:
    if not isinstance(value, str) or DIGEST.fullmatch(value) is None:
        raise InvalidPeriodStatusSimulation("Canonical sha256 evidence digest required")


@dataclass(frozen=True, slots=True)
class SimulatedPeriodStatusQuery:
    """Exact business posting date and as-known cutoff, scoped to a claimed book."""

    book_scope: ConfigurationScope
    posting_date: date
    known_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.book_scope, ConfigurationScope) or (
            self.book_scope.book_id is None
        ):
            raise InvalidPeriodStatusSimulation("Book-level query scope required")
        if type(self.posting_date) is not date:
            raise InvalidPeriodStatusSimulation("Explicit posting_date required")
        _check_time(self.known_at)


@dataclass(frozen=True, slots=True)
class ObservedLockWireCandidate:
    """Observed lock, not a computed applicable/blocking lock."""

    lock_id: str
    scope: str
    target_code: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.lock_id, str) or UUID_PATTERN.fullmatch(
            self.lock_id
        ) is None:
            raise InvalidPeriodStatusSimulation("Canonical observed lock ID required")
        if self.scope not in {item.value for item in PeriodLockScopeCandidate}:
            raise InvalidPeriodStatusSimulation("Unknown candidate lock scope")
        if self.scope == PeriodLockScopeCandidate.GLOBAL_BOOK_LOCK.value:
            if self.target_code is not None:
                raise InvalidPeriodStatusSimulation("Global lock must not have target")
        elif (
            not isinstance(self.target_code, str)
            or re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", self.target_code) is None
        ):
            raise InvalidPeriodStatusSimulation("Typed scoped lock target required")

    def manifest(self) -> dict[str, str | None]:
        return {
            "lock_id": self.lock_id, "scope": self.scope,
            "target_code": self.target_code,
        }


@dataclass(frozen=True, slots=True)
class SimulatedPeriodStatusResponse:
    """Wire contract. No status authority, signed version, or can_post accessor."""

    book_scope: ConfigurationScope
    posting_date: date
    known_at: datetime
    calendar_version_id: CalendarCandidateVersionId
    period_id: AccountingPeriodId
    period_code: str
    observed_status: PeriodStatusCandidate
    state_revision: int
    diagnostic_disposition: PeriodControlDiagnosticDisposition
    observed_locks: tuple[ObservedLockWireCandidate, ...]
    calendar_candidate_digest: str
    period_control_candidate_digest: str
    content_digest: str = field(init=False)

    schema_version: ClassVar[str] = SCHEMA_VERSION
    authority: ClassVar[str] = AUTHORITY

    def __post_init__(self) -> None:
        SimulatedPeriodStatusQuery(
            self.book_scope, self.posting_date, self.known_at
        )
        if not isinstance(self.calendar_version_id, CalendarCandidateVersionId):
            raise InvalidPeriodStatusSimulation("Typed calendar candidate version ID")
        if not isinstance(self.period_id, AccountingPeriodId):
            raise InvalidPeriodStatusSimulation("Typed period ID required")
        if not isinstance(self.period_code, str) or re.fullmatch(
            r"[A-Z0-9][A-Z0-9_-]{0,47}", self.period_code
        ) is None:
            raise InvalidPeriodStatusSimulation("Canonical period code required")
        if not isinstance(self.observed_status, PeriodStatusCandidate):
            raise InvalidPeriodStatusSimulation("Typed observed status required")
        if type(self.state_revision) is not int or self.state_revision <= 0:
            raise InvalidPeriodStatusSimulation("Positive candidate revision required")
        if not isinstance(
            self.diagnostic_disposition, PeriodControlDiagnosticDisposition
        ):
            raise InvalidPeriodStatusSimulation("Typed diagnostic disposition required")
        if not isinstance(self.observed_locks, tuple) or any(
            not isinstance(item, ObservedLockWireCandidate)
            for item in self.observed_locks
        ):
            raise InvalidPeriodStatusSimulation("Immutable observed locks required")
        if (
            tuple(sorted(self.observed_locks, key=lambda x: x.lock_id))
            != self.observed_locks
            or len({item.lock_id for item in self.observed_locks})
            != len(self.observed_locks)
        ):
            raise InvalidPeriodStatusSimulation("Locks must be sorted and unique")
        _check_digest(self.calendar_candidate_digest)
        _check_digest(self.period_control_candidate_digest)
        self._validate_consistency()
        object.__setattr__(self, "content_digest", _digest(self.manifest()))

    def _validate_consistency(self) -> None:
        disposition = self.diagnostic_disposition
        if disposition is PeriodControlDiagnosticDisposition.NO_OBSERVED_LOCKS_UNVERIFIED:
            if self.observed_status is not PeriodStatusCandidate.OPEN or self.observed_locks:
                raise InvalidPeriodStatusSimulation("Contradictory no-lock diagnostic")
        if disposition is PeriodControlDiagnosticDisposition.LOCKS_OBSERVED_SCOPE_UNEVALUATED:
            if self.observed_status is not PeriodStatusCandidate.OPEN or not self.observed_locks:
                raise InvalidPeriodStatusSimulation("Contradictory lock diagnostic")
        if disposition is PeriodControlDiagnosticDisposition.NON_OPEN_CANDIDATE_STATUS:
            if self.observed_status is PeriodStatusCandidate.OPEN:
                raise InvalidPeriodStatusSimulation("Contradictory non-open diagnostic")

    def manifest(self) -> dict[str, object]:
        scope = self.book_scope
        return {
            "schema_version": SCHEMA_VERSION,
            "authority": AUTHORITY,
            "eligible_for_posting": False,
            "book_id": str(scope.book_id),
            "tenant_id": scope.tenant_id,
            "company_id": str(scope.company_id),
            "legal_entity_id": str(scope.legal_entity_id),
            "posting_date": self.posting_date.isoformat(),
            "known_at": _utc(self.known_at),
            "calendar_candidate_version_id": str(self.calendar_version_id),
            "period_id": str(self.period_id),
            "period_code": self.period_code,
            "observed_status": self.observed_status.value,
            "state_revision": self.state_revision,
            "diagnostic_disposition": self.diagnostic_disposition.value,
            "observed_lock_observations": [
                lock.manifest() for lock in self.observed_locks
            ],
            "calendar_candidate_digest": self.calendar_candidate_digest,
            "period_control_candidate_digest": self.period_control_candidate_digest,
        }

    def to_wire(self) -> str:
        """Canonical wire JSON with local checksum; never a verified signature."""
        result = {**self.manifest(), "content_digest": self.content_digest}
        return json.dumps(
            result, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )

    def verify_integrity(self) -> None:
        self._validate_consistency()
        if _digest(self.manifest()) != self.content_digest:
            raise InvalidPeriodStatusSimulation("Simulated period status tampered")

    def matches_query(self, query: SimulatedPeriodStatusQuery) -> None:
        if not isinstance(query, SimulatedPeriodStatusQuery):
            raise InvalidPeriodStatusSimulation("Typed consumer query required")
        if (
            self.book_scope != query.book_scope
            or self.posting_date != query.posting_date
            or _utc(self.known_at) != _utc(query.known_at)
        ):
            raise InvalidPeriodStatusSimulation("Query and candidate response mismatch")


def simulate_period_status_contract(
    *, query: SimulatedPeriodStatusQuery,
    diagnostic: PeriodControlCandidateDiagnostic,
) -> SimulatedPeriodStatusResponse:
    """Producer *simulation* from an untrusted L06-03 diagnostic only."""
    if not isinstance(query, SimulatedPeriodStatusQuery):
        raise InvalidPeriodStatusSimulation("Typed query required")
    if not isinstance(diagnostic, PeriodControlCandidateDiagnostic):
        raise InvalidPeriodStatusSimulation("Typed candidate diagnostic required")
    diagnostic.verify_integrity()
    receipt = diagnostic.book_receipt
    if (
        query.book_scope != receipt.assignment.book_scope
        or query.posting_date != receipt.as_of
        or _utc(query.known_at) != _utc(receipt.known_at)
    ):
        raise InvalidPeriodStatusSimulation("Producer query/date/book mismatch")
    return SimulatedPeriodStatusResponse(
        book_scope=query.book_scope,
        posting_date=query.posting_date,
        known_at=query.known_at,
        calendar_version_id=receipt.calendar_version.id,
        period_id=receipt.period.period_id,
        period_code=receipt.period.code.value,
        observed_status=diagnostic.state.status,
        state_revision=diagnostic.state.state_revision,
        diagnostic_disposition=diagnostic.disposition,
        observed_locks=tuple(
            ObservedLockWireCandidate(
                str(item.id), item.lock_scope.value, item.target_code
            ) for item in diagnostic.observed_active_locks
        ),
        calendar_candidate_digest=receipt.calendar_version.content_digest,
        period_control_candidate_digest=diagnostic.content_digest,
    )


def inspect_simulated_period_status_wire(
    *, wire: str, query: SimulatedPeriodStatusQuery,
) -> SimulatedPeriodStatusResponse:
    """Strict consumer compatibility: no unknown/extra fields or authority upgrade."""
    if not isinstance(wire, str):
        raise InvalidPeriodStatusSimulation("JSON text required")
    try:
        parsed = json.loads(wire)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise InvalidPeriodStatusSimulation("Malformed candidate wire JSON") from exc
    if not isinstance(parsed, dict):
        raise InvalidPeriodStatusSimulation("Object wire payload required")
    if (
        parsed.get("schema_version") != SCHEMA_VERSION
        or parsed.get("authority") != AUTHORITY
        or type(parsed.get("eligible_for_posting")) is not bool
        or parsed["eligible_for_posting"] is not False
    ):
        raise InvalidPeriodStatusSimulation("Unsupported or elevated wire authority")
    expected_keys = set(
        SimulatedPeriodStatusResponse(
            book_scope=query.book_scope, posting_date=query.posting_date,
            known_at=query.known_at,
            calendar_version_id=CalendarCandidateVersionId.new(),
            period_id=AccountingPeriodId.new(),
            period_code="P00", observed_status=PeriodStatusCandidate.DRAFT,
            state_revision=1,
            diagnostic_disposition=(
                PeriodControlDiagnosticDisposition.NON_OPEN_CANDIDATE_STATUS
            ),
            observed_locks=(),
            calendar_candidate_digest="sha256:" + "0" * 64,
            period_control_candidate_digest="sha256:" + "0" * 64,
        ).manifest()
    ) | {"content_digest"}
    if set(parsed) != expected_keys:
        raise InvalidPeriodStatusSimulation("Unexpected/missing wire fields")
    locks = parsed["observed_lock_observations"]
    if not isinstance(locks, list) or any(
        not isinstance(item, dict) or set(item)
        != {"lock_id", "scope", "target_code"} for item in locks
    ):
        raise InvalidPeriodStatusSimulation("Invalid lock wire shape")
    try:
        book_scope = ConfigurationScope(
            parsed["tenant_id"],
            CompanyId.parse(parsed["company_id"]),
            LegalEntityId.parse(parsed["legal_entity_id"]),
            AccountingBookId.parse(parsed["book_id"]),
        )
        known_at = datetime.fromisoformat(parsed["known_at"].replace("Z", "+00:00"))
        candidate = SimulatedPeriodStatusResponse(
            book_scope=book_scope,
            posting_date=date.fromisoformat(parsed["posting_date"]),
            known_at=known_at,
            calendar_version_id=CalendarCandidateVersionId.parse(
                parsed["calendar_candidate_version_id"]
            ),
            period_id=AccountingPeriodId.parse(parsed["period_id"]),
            period_code=parsed["period_code"],
            observed_status=PeriodStatusCandidate(parsed["observed_status"]),
            state_revision=parsed["state_revision"],
            diagnostic_disposition=PeriodControlDiagnosticDisposition(
                parsed["diagnostic_disposition"]
            ),
            observed_locks=tuple(ObservedLockWireCandidate(
                item["lock_id"], item["scope"], item["target_code"]
            ) for item in locks),
            calendar_candidate_digest=parsed["calendar_candidate_digest"],
            period_control_candidate_digest=parsed["period_control_candidate_digest"],
        )
    except (ValueError, TypeError, KeyError, DomainError) as exc:
        raise InvalidPeriodStatusSimulation("Invalid typed candidate wire fields") from exc
    _check_digest(parsed["content_digest"])
    if candidate.content_digest != parsed["content_digest"]:
        raise InvalidPeriodStatusSimulation("Candidate wire checksum mismatch")
    candidate.matches_query(query)
    if wire != candidate.to_wire():
        raise InvalidPeriodStatusSimulation("Noncanonical or duplicated wire keys")
    return candidate


def reject_simulated_status_for_posting(
    response: SimulatedPeriodStatusResponse,
) -> None:
    """Negative contract: ALWAYS refuses, including OPEN with zero observed locks."""
    if not isinstance(response, SimulatedPeriodStatusResponse):
        raise InvalidPeriodStatusSimulation("Typed simulated response required")
    response.verify_integrity()
    raise UntrustedPeriodStatusForPosting(
        "R&D candidate is never authoritative at Ledger COMMIT; C10-Q04 required"
    )
