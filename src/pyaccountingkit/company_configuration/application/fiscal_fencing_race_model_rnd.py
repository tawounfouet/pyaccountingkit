"""L06-06 — symbolic close-vs-post ordering model; NO real posting guard.

A trace is a user-constructed abstract interleaving, NOT observed SQL COMMIT
order. "MODEL_ORDERED_PRE_CLOSE" never means that posting is authorized.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum

from ..domain.fiscal_calendar.period_controls import (
    PeriodControlDiagnosticDisposition,
    PeriodStatusCandidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.errors import DomainError
from ..domain.shared.identifiers import (
    AccountingPeriodId,
    CalendarCandidateVersionId,
)
from .fiscal_c10_q04_simulation import (
    SimulatedPeriodStatusResponse,
    UntrustedPeriodStatusForPosting,
)

MODEL_SCHEMA = "l06-06-symbolic-fence-race-rnd-v1"


class InvalidSymbolicFenceTrace(DomainError):
    code = "INVALID_SYMBOLIC_FENCE_TRACE"


class SymbolicFenceTraceTampered(DomainError):
    code = "SYMBOLIC_FENCE_TRACE_TAMPERED"


class SymbolicRaceStep(Enum):
    MODEL_CLOSE = "MODEL_CLOSE"
    MODEL_POST_ATTEMPT = "MODEL_POST_ATTEMPT"
    MODEL_DELAYED_CLOSE_NOTIFICATION = "MODEL_DELAYED_CLOSE_NOTIFICATION"


class SymbolicRaceOutcome(Enum):
    MODEL_CLOSE_ORDERED = "MODEL_CLOSE_ORDERED"
    MODEL_CLOSE_ALREADY_PRESENT = "MODEL_CLOSE_ALREADY_PRESENT"
    MODEL_ORDERED_PRE_CLOSE_ONLY = "MODEL_ORDERED_PRE_CLOSE_ONLY"
    MODEL_REJECTED_STALE_STATE = "MODEL_REJECTED_STALE_STATE"
    MODEL_REJECTED_NON_OPEN = "MODEL_REJECTED_NON_OPEN"
    MODEL_REJECTED_UNVERIFIED_LOCKS = "MODEL_REJECTED_UNVERIFIED_LOCKS"
    MODEL_REJECTED_INCOMPLETE_EVIDENCE = "MODEL_REJECTED_INCOMPLETE_EVIDENCE"
    MODEL_EVENT_IGNORED_NOT_AUTHORITY = "MODEL_EVENT_IGNORED_NOT_AUTHORITY"


class UnverifiedPostingFenceGate(Enum):
    SIGNED_ISSUER_ACTOR_AT_COMMIT = "SIGNED_ISSUER_ACTOR_AT_COMMIT"
    VERIFIED_PUBLISHED_PERIOD_AND_BOOK = "VERIFIED_PUBLISHED_PERIOD_AND_BOOK"
    AUTHORITATIVE_LOCK_APPLICABILITY = "AUTHORITATIVE_LOCK_APPLICABILITY"
    ATOMIC_LEDGER_COMMIT_FENCE = "ATOMIC_LEDGER_COMMIT_FENCE"
    DURABLE_CLOSE_CAS_AND_AUDIT_OUTBOX = "DURABLE_CLOSE_CAS_AND_AUDIT_OUTBOX"
    REAL_CONCURRENT_LINEARIZABILITY_PROOF = "REAL_CONCURRENT_LINEARIZABILITY_PROOF"


def _digest(manifest: dict[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            manifest, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class SymbolicPeriodControl:
    """Unverified initial state of an *abstract* book/period control row."""

    book_scope: ConfigurationScope
    calendar_version_id: CalendarCandidateVersionId
    period_id: AccountingPeriodId
    revision: int
    fence_epoch: int
    status: PeriodStatusCandidate

    def __post_init__(self) -> None:
        if not isinstance(self.book_scope, ConfigurationScope) or (
            self.book_scope.book_id is None
        ):
            raise InvalidSymbolicFenceTrace("Typed claimed book scope required")
        if not isinstance(self.calendar_version_id, CalendarCandidateVersionId) or (
            not isinstance(self.period_id, AccountingPeriodId)
        ):
            raise InvalidSymbolicFenceTrace("Typed candidate version/period IDs required")
        if type(self.revision) is not int or self.revision <= 0:
            raise InvalidSymbolicFenceTrace("Positive abstract revision required")
        if type(self.fence_epoch) is not int or self.fence_epoch <= 0:
            raise InvalidSymbolicFenceTrace("Positive abstract fence epoch required")
        if not isinstance(self.status, PeriodStatusCandidate):
            raise InvalidSymbolicFenceTrace("Typed abstract period status required")


@dataclass(frozen=True, slots=True)
class SymbolicPreflightObservation:
    """Pinned but UNSIGNED observation; neither a fence nor a lease."""

    book_scope: ConfigurationScope
    calendar_version_id: CalendarCandidateVersionId
    period_id: AccountingPeriodId
    read_revision: int
    read_epoch: int
    source_receipt_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.book_scope, ConfigurationScope) or (
            self.book_scope.book_id is None
        ) or not isinstance(self.calendar_version_id, CalendarCandidateVersionId) or (
            not isinstance(self.period_id, AccountingPeriodId)
        ):
            raise InvalidSymbolicFenceTrace("Typed exact preflight scope/IDs required")
        if type(self.read_revision) is not int or self.read_revision <= 0 or (
            type(self.read_epoch) is not int or self.read_epoch <= 0
        ):
            raise InvalidSymbolicFenceTrace("Positive preflight revision and epoch required")
        if not isinstance(self.source_receipt_digest, str) or len(
            self.source_receipt_digest
        ) != 71 or not self.source_receipt_digest.startswith("sha256:"):
            raise InvalidSymbolicFenceTrace("Exact source receipt digest required")


@dataclass(frozen=True, slots=True)
class SymbolicRaceObservation:
    """One step of an abstract ordering; no real COMMIT or posted ledger row."""

    index: int
    step: SymbolicRaceStep
    outcome: SymbolicRaceOutcome
    before_revision: int
    after_revision: int
    before_epoch: int
    after_epoch: int
    after_status: PeriodStatusCandidate

    def manifest(self) -> dict[str, object]:
        return {
            "index": self.index, "step": self.step.value,
            "outcome": self.outcome.value,
            "before_revision": self.before_revision,
            "after_revision": self.after_revision,
            "before_epoch": self.before_epoch,
            "after_epoch": self.after_epoch,
            "after_status": self.after_status.value,
        }


def _state_manifest(state: SymbolicPeriodControl) -> dict[str, object]:
    scope = state.book_scope
    return {
        "tenant": scope.tenant_id,
        "company": str(scope.company_id),
        "entity": str(scope.legal_entity_id),
        "book": str(scope.book_id),
        "version_id": str(state.calendar_version_id),
        "period_id": str(state.period_id),
        "revision": state.revision, "epoch": state.fence_epoch,
        "status": state.status.value,
    }


@dataclass(frozen=True, slots=True, eq=False)
class SymbolicFenceRaceDiagnostic:
    """Abstract trace with permanently UNVERIFIED external gates."""

    initial: SymbolicPeriodControl
    preflight: SymbolicPreflightObservation
    source_response: SimulatedPeriodStatusResponse
    steps: tuple[SymbolicRaceStep, ...]
    observations: tuple[SymbolicRaceObservation, ...]
    final_state: SymbolicPeriodControl
    unverified_gates: tuple[UnverifiedPostingFenceGate, ...]
    content_digest: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_inputs(self.initial, self.source_response, self.preflight, self.steps)
        expected, current = _run(self.initial, self.source_response, self.preflight, self.steps)
        if self.observations != expected or self.final_state != current:
            raise InvalidSymbolicFenceTrace("Fabricated symbolic trace results")
        if self.unverified_gates != tuple(UnverifiedPostingFenceGate):
            raise InvalidSymbolicFenceTrace("External fence proof was falsely elevated")
        object.__setattr__(self, "content_digest", _digest(self.manifest()))

    @property
    def disposition(self) -> str:
        return "ABSTRACT_TRACE_ONLY_NO_LEDGER_AUTHORITY"

    def manifest(self) -> dict[str, object]:
        return {
            "schema": MODEL_SCHEMA,
            "disposition": self.disposition,
            "initial": _state_manifest(self.initial),
            "final": _state_manifest(self.final_state),
            "source_response_digest": self.source_response.content_digest,
            "preflight": {
                "book": str(self.preflight.book_scope.book_id),
                "version_id": str(self.preflight.calendar_version_id),
                "period_id": str(self.preflight.period_id),
                "read_revision": self.preflight.read_revision,
                "read_epoch": self.preflight.read_epoch,
                "source_receipt_digest": self.preflight.source_receipt_digest,
            },
            "steps": [step.value for step in self.steps],
            "observations": [item.manifest() for item in self.observations],
            "unverified_gates": [gate.value for gate in self.unverified_gates],
            "sql_committed": False, "journal_entry_created": False,
            "posting_authorized": False, "signed": False,
        }

    def verify_integrity(self) -> None:
        _validate_inputs(self.initial, self.source_response, self.preflight, self.steps)
        observations, final = _run(
            self.initial, self.source_response, self.preflight, self.steps
        )
        if self.observations != observations or self.final_state != final:
            raise SymbolicFenceTraceTampered("Symbolic observations were modified")
        if self.unverified_gates != tuple(UnverifiedPostingFenceGate) or (
            _digest(self.manifest()) != self.content_digest
        ):
            raise SymbolicFenceTraceTampered("Symbolic trace or safety gates changed")


def _validate_inputs(
    initial: SymbolicPeriodControl,
    source: SimulatedPeriodStatusResponse,
    preflight: SymbolicPreflightObservation,
    steps: tuple[SymbolicRaceStep, ...],
) -> None:
    if not isinstance(initial, SymbolicPeriodControl) or not isinstance(
        source, SimulatedPeriodStatusResponse
    ) or not isinstance(preflight, SymbolicPreflightObservation):
        raise InvalidSymbolicFenceTrace("Typed state/source/preflight required")
    source.verify_integrity()
    if (
        initial.book_scope != source.book_scope
        or initial.calendar_version_id != source.calendar_version_id
        or initial.period_id != source.period_id
        or initial.revision != source.state_revision
        or initial.status is not source.observed_status
        or preflight.book_scope != initial.book_scope
        or preflight.calendar_version_id != initial.calendar_version_id
        or preflight.period_id != initial.period_id
        or preflight.read_revision != initial.revision
        or preflight.read_epoch != initial.fence_epoch
        or preflight.source_receipt_digest != source.content_digest
    ):
        raise InvalidSymbolicFenceTrace("Unpinned/forged abstract fence observation")
    if not isinstance(steps, tuple) or not steps or any(
        not isinstance(item, SymbolicRaceStep) for item in steps
    ):
        raise InvalidSymbolicFenceTrace("Explicit immutable symbolic steps required")
    if sum(step is SymbolicRaceStep.MODEL_POST_ATTEMPT for step in steps) != 1:
        raise InvalidSymbolicFenceTrace("Exactly one symbolic post attempt required")
    if sum(step is SymbolicRaceStep.MODEL_CLOSE for step in steps) > 2:
        raise InvalidSymbolicFenceTrace("At most two competing closures modeled")


def _run(
    initial: SymbolicPeriodControl,
    source: SimulatedPeriodStatusResponse,
    preflight: SymbolicPreflightObservation,
    steps: tuple[SymbolicRaceStep, ...],
) -> tuple[tuple[SymbolicRaceObservation, ...], SymbolicPeriodControl]:
    control = initial
    observed: list[SymbolicRaceObservation] = []
    for index, step in enumerate(steps):
        before = control
        if step is SymbolicRaceStep.MODEL_CLOSE:
            if control.status in (
                PeriodStatusCandidate.CLOSED, PeriodStatusCandidate.ARCHIVED,
            ):
                outcome = SymbolicRaceOutcome.MODEL_CLOSE_ALREADY_PRESENT
            else:
                control = SymbolicPeriodControl(
                    control.book_scope, control.calendar_version_id, control.period_id,
                    control.revision + 1, control.fence_epoch + 1,
                    PeriodStatusCandidate.CLOSED,
                )
                outcome = SymbolicRaceOutcome.MODEL_CLOSE_ORDERED
        elif step is SymbolicRaceStep.MODEL_DELAYED_CLOSE_NOTIFICATION:
            outcome = SymbolicRaceOutcome.MODEL_EVENT_IGNORED_NOT_AUTHORITY
        elif (
            control.revision != preflight.read_revision
            or control.fence_epoch != preflight.read_epoch
        ):
            outcome = SymbolicRaceOutcome.MODEL_REJECTED_STALE_STATE
        elif control.status is not PeriodStatusCandidate.OPEN:
            outcome = SymbolicRaceOutcome.MODEL_REJECTED_NON_OPEN
        elif source.diagnostic_disposition is (
            PeriodControlDiagnosticDisposition.INCOMPLETE_CANDIDATE_EVIDENCE
        ):
            outcome = SymbolicRaceOutcome.MODEL_REJECTED_INCOMPLETE_EVIDENCE
        elif source.observed_locks:
            outcome = SymbolicRaceOutcome.MODEL_REJECTED_UNVERIFIED_LOCKS
        else:
            outcome = SymbolicRaceOutcome.MODEL_ORDERED_PRE_CLOSE_ONLY
        observed.append(SymbolicRaceObservation(
            index, step, outcome, before.revision, control.revision,
            before.fence_epoch, control.fence_epoch, control.status,
        ))
    return tuple(observed), control


def simulate_symbolic_close_post_race(
    *,
    initial: SymbolicPeriodControl,
    preflight: SymbolicPreflightObservation,
    source_response: SimulatedPeriodStatusResponse,
    steps: tuple[SymbolicRaceStep, ...],
) -> SymbolicFenceRaceDiagnostic:
    """Enumerate symbolic ordering, never execute or approve posting."""
    _validate_inputs(initial, source_response, preflight, steps)
    observations, final = _run(initial, source_response, preflight, steps)
    return SymbolicFenceRaceDiagnostic(
        initial, preflight, source_response, steps, observations, final,
        tuple(UnverifiedPostingFenceGate),
    )


def refuse_symbolic_fence_for_posting(proof: SymbolicFenceRaceDiagnostic) -> None:
    """Cannot turn an abstract ordering into a real execution capability."""
    if not isinstance(proof, SymbolicFenceRaceDiagnostic):
        raise InvalidSymbolicFenceTrace("Typed abstract trace required")
    proof.verify_integrity()
    raise UntrustedPeriodStatusForPosting(
        "Symbolic linearization is not an atomic SQL/ledger fence or signed permission"
    )
