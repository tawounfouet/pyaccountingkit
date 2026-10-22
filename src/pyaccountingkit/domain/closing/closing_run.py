"""Closing runs — orchestration state, close gate and evidence bundle (LOT-09)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pyaccountingkit.core.errors import ControlFailureError, DomainError
from pyaccountingkit.domain.controls.control import ControlOutcome, ControlRun
from pyaccountingkit.domain.traceability.trace import CanonicalHasher


class ClosingEvidenceError(DomainError):
    """Closing evidence is missing, foreign, stale, or otherwise unusable."""

    code = "CLOSING_EVIDENCE_INVALID"


class ClosingPhase(StrEnum):
    RUNNING = "RUNNING"
    SEALED = "SEALED"


@dataclass(frozen=True, slots=True)
class ClosingEvidenceBundle:
    """Immutable evidence sealing a closed period (reopening preserves it)."""

    run_id: str
    period_id: str
    trial_balance_checksum: str
    control_runs_hash: str
    total_debit: str
    total_credit: str
    sealed_at: datetime


@dataclass(frozen=True, slots=True)
class ClosingRun:
    """One close of one period; each step returns a new immutable run."""

    id: str
    period_id: str
    phase: ClosingPhase = ClosingPhase.RUNNING
    evidence: ClosingEvidenceBundle | None = None

    @property
    def is_sealed(self) -> bool:
        return self.phase is ClosingPhase.SEALED

    def with_evidence(self, evidence: ClosingEvidenceBundle) -> ClosingRun:
        """Return a sealed copy carrying its immutable evidence."""
        return ClosingRun(
            id=self.id,
            period_id=self.period_id,
            phase=ClosingPhase.SEALED,
            evidence=evidence,
        )

    def evidence_digest(self) -> str:
        """Deterministic digest of the carried evidence, stable over time."""
        if self.evidence is None:
            return CanonicalHasher.digest(
                {"run_id": self.id, "period_id": self.period_id, "phase": "RUNNING"}
            )
        return self.evidence_digest_from(self.evidence)

    @staticmethod
    def evidence_digest_from(evidence: ClosingEvidenceBundle) -> str:
        return CanonicalHasher.digest(
            {
                "run_id": evidence.run_id,
                "period_id": evidence.period_id,
                "tb_checksum": evidence.trial_balance_checksum,
                "controls": evidence.control_runs_hash,
                "total_debit": evidence.total_debit,
                "total_credit": evidence.total_credit,
                "sealed_at": evidence.sealed_at,
            }
        )


class CloseGate:
    """Fail-closed gate for the blocking controls required by a close."""

    def __init__(self) -> None:
        self._blocking_codes: set[str] = set()

    def require(self, control_code: str) -> None:
        self._blocking_codes.add(control_code)

    @property
    def required_codes(self) -> frozenset[str]:
        return frozenset(self._blocking_codes)

    def assert_passes(
        self,
        control_runs: Sequence[ControlRun],
        *,
        period_id: str,
    ) -> None:
        by_code: dict[str, list[ControlRun]] = {}
        for run in control_runs:
            by_code.setdefault(run.definition_code, []).append(run)

        missing = sorted(code for code in self._blocking_codes if code not in by_code)
        if missing:
            raise ControlFailureError(f"Contrôles bloquants absents, clôture refusée: {missing}")

        invalid: list[str] = []
        for code in sorted(self._blocking_codes):
            runs = by_code[code]
            if len(runs) != 1:
                invalid.append(f"{code}:AMBIGUOUS")
                continue
            run = runs[0]
            if run.period_id != period_id:
                invalid.append(f"{code}:FOREIGN_PERIOD")
                continue
            if run.result.outcome is not ControlOutcome.PASS:
                invalid.append(f"{code}:{run.result.outcome.value}")

        if invalid:
            raise ControlFailureError(
                f"Contrôles bloquants non validés, clôture refusée: {invalid}"
            )


class ClosingRunBook:
    """Append-only store preserving every closing run's evidence."""

    def __init__(self) -> None:
        self._runs: dict[str, ClosingRun] = {}

    def record(self, run: ClosingRun) -> None:
        stored = self._runs.get(run.id)
        if stored is not None and stored != run:
            raise ValueError(f"Closing run {run.id} déjà enregistré : témoignage immuable")
        self._runs[run.id] = run

    def get(self, run_id: str) -> ClosingRun:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return self._runs[run_id]

    def runs_for_period(self, period_id: str) -> tuple[ClosingRun, ...]:
        return tuple(run for run in self._runs.values() if run.period_id == period_id)


__all__ = [
    "ClosingEvidenceError",
    "ClosingPhase",
    "ClosingRun",
    "ClosingEvidenceBundle",
    "CloseGate",
    "ClosingRunBook",
]
