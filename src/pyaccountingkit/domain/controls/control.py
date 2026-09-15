"""Controls — versioned definitions, runs, results and gates (LOT-08).

Control runs are append-only: the history of a failed control is
immutable once recorded (DoD `failed control history immutable`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pyaccountingkit.core.errors import ControlFailureError


class ControlOutcome(StrEnum):
    PASS = "PASS"  # nosec B105 - accounting control outcome, not a credential
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class ControlDefinition:
    """A versioned control contract."""

    code: str
    label: str
    version: int = 1

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError(f"Control version must be >= 1, got {self.version}")


@dataclass(frozen=True, slots=True)
class ControlResult:
    """Outcome plus human-readable detail of one evaluation."""

    outcome: ControlOutcome
    detail: str = ""

    @classmethod
    def passed(cls, detail: str = "") -> ControlResult:
        return cls(ControlOutcome.PASS, detail)

    @classmethod
    def failed(cls, detail: str = "") -> ControlResult:
        return cls(ControlOutcome.FAIL, detail)


@dataclass(frozen=True, slots=True)
class ControlRun:
    """An immutable evaluation of a control over a period."""

    id: str
    definition_code: str
    version: int
    period_id: str
    result: ControlResult
    executed_at: datetime

    @property
    def failed(self) -> bool:
        return self.result.outcome is ControlOutcome.FAIL


class ControlGate:
    """Blocks processing when a control run fails; sketches a typed decision."""

    def __init__(self, definition: ControlDefinition) -> None:
        self.definition = definition

    def evaluate(self, run: ControlRun) -> bool:
        """Return ``True`` when the run passes against this gate."""
        if run.definition_code != self.definition.code:
            raise ValueError(f"Gate {self.definition.code} vs run {run.definition_code} mismatch")
        if run.failed:
            raise ControlFailureError(
                f"Contrôle {run.definition_code} v{run.version} échoué: {run.result.detail}"
            )
        return True


class ControlRunBook:
    """Append-only ledger of control runs enforcing immutable history."""

    def __init__(self) -> None:
        self._runs: dict[str, ControlRun] = {}

    def record(self, run: ControlRun) -> None:
        """Append a run; refusing any overwrite once recorded."""
        stored = self._runs.get(run.id)
        if stored is not None and stored != run:
            raise ValueError(f"Run {run.id} déjà enregistré : historique immuable")
        self._runs[run.id] = run

    def get(self, run_id: str) -> ControlRun:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return self._runs[run_id]

    def history(self) -> tuple[ControlRun, ...]:
        return tuple(self._runs[run_id] for run_id in sorted(self._runs))


__all__ = [
    "ControlDefinition",
    "ControlResult",
    "ControlRun",
    "ControlGate",
    "ControlRunBook",
    "ControlOutcome",
]
