"""CFA FRA consumer cutover qualification evidence for LOT-26."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CFAFRAConsumerQualificationError(RuntimeError):
    """Raised when consumer qualification evidence is invalid or incomplete."""


class ConsumerScenario(StrEnum):
    """Mandatory CFA FRA consumer scenarios from the migration Gate Consumer."""

    LOGIN = "login"
    ORGANIZATION_CONTEXT = "organization_context"
    FEC_IMPORT = "fec_import"
    JOURNAL = "journal"
    LEDGER = "ledger"
    BALANCE = "balance"
    FINANCIAL_STATEMENTS = "financial_statements"
    CONTROLS = "controls"
    CLOSING = "closing"
    EXPORTS = "exports"


class ConsumerScenarioStatus(StrEnum):
    """Observed qualification status for one consumer scenario."""

    PASS = "PASS"  # nosec B105 - qualification status label, not a credential
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


_REQUIRED_SCENARIOS = frozenset(ConsumerScenario)


@dataclass(frozen=True, slots=True)
class ConsumerScenarioEvidence:
    """One externally produced consumer smoke/E2E result."""

    scenario: ConsumerScenario
    status: ConsumerScenarioStatus
    source: str
    detail: str | None = None
    evidence_checksum: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("consumer evidence source must not be empty")
        if self.status is not ConsumerScenarioStatus.PASS:
            if self.detail is None or not self.detail.strip():
                raise ValueError("non-passing consumer evidence requires detail")
        if self.evidence_checksum is not None and not self.evidence_checksum.strip():
            raise ValueError("consumer evidence checksum must not be empty")


@dataclass(frozen=True, slots=True)
class ConsumerQualificationDecision:
    """Deterministic cutover decision derived from consumer evidence."""

    green: bool
    blockers: tuple[str, ...]
    passed: tuple[ConsumerScenario, ...]
    failed: tuple[ConsumerScenario, ...]
    blocked: tuple[ConsumerScenario, ...]
    missing: tuple[ConsumerScenario, ...]


class ConsumerQualification:
    """Collect complete consumer evidence without importing the Django application."""

    def __init__(self, evidence: tuple[ConsumerScenarioEvidence, ...]) -> None:
        by_scenario: dict[ConsumerScenario, ConsumerScenarioEvidence] = {}
        for item in evidence:
            if item.scenario in by_scenario:
                raise CFAFRAConsumerQualificationError(
                    f"duplicate consumer evidence for {item.scenario.value!r}"
                )
            by_scenario[item.scenario] = item
        self._evidence = by_scenario

    def evidence(self) -> tuple[ConsumerScenarioEvidence, ...]:
        ordered = sorted(self._evidence, key=lambda item: item.value)
        return tuple(self._evidence[key] for key in ordered)

    def evaluate(self) -> ConsumerQualificationDecision:
        present = set(self._evidence)
        missing = tuple(sorted(_REQUIRED_SCENARIOS - present, key=lambda item: item.value))
        passed = tuple(
            sorted(
                (
                    scenario
                    for scenario, item in self._evidence.items()
                    if item.status is ConsumerScenarioStatus.PASS
                ),
                key=lambda item: item.value,
            )
        )
        failed = tuple(
            sorted(
                (
                    scenario
                    for scenario, item in self._evidence.items()
                    if item.status is ConsumerScenarioStatus.FAIL
                ),
                key=lambda item: item.value,
            )
        )
        blocked = tuple(
            sorted(
                (
                    scenario
                    for scenario, item in self._evidence.items()
                    if item.status is ConsumerScenarioStatus.BLOCKED
                ),
                key=lambda item: item.value,
            )
        )

        blockers = tuple(
            sorted(
                (
                    *(f"missing:{scenario.value}" for scenario in missing),
                    *(f"failed:{scenario.value}" for scenario in failed),
                    *(f"blocked:{scenario.value}" for scenario in blocked),
                )
            )
        )
        return ConsumerQualificationDecision(
            green=not blockers and len(passed) == len(_REQUIRED_SCENARIOS),
            blockers=blockers,
            passed=passed,
            failed=failed,
            blocked=blocked,
            missing=missing,
        )

    def require_green(self) -> None:
        decision = self.evaluate()
        if not decision.green:
            raise CFAFRAConsumerQualificationError(
                "consumer qualification is not green: " + ", ".join(decision.blockers)
            )


__all__ = [
    "CFAFRAConsumerQualificationError",
    "ConsumerQualification",
    "ConsumerQualificationDecision",
    "ConsumerScenario",
    "ConsumerScenarioEvidence",
    "ConsumerScenarioStatus",
]
