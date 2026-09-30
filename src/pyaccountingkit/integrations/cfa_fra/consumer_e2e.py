"""Consumer-side E2E evidence contract for CFA FRA migration.

PyAccountingKit does not execute the external Django application's browser/UI
suite itself. Instead, LOT-26 defines the exact evidence that the consumer must
produce before the duplicate accounting engine can be retired.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


REQUIRED_CONSUMER_SCENARIOS = frozenset(
    {
        "login",
        "organization_context",
        "fec_import",
        "journal",
        "ledger",
        "balance",
        "financial_statements",
        "controls",
        "closing",
        "exports",
    }
)


class ConsumerScenarioStatus(StrEnum):
    """Outcome recorded by the migrated CFA FRA consumer suite."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class ConsumerScenarioEvidence:
    """Evidence for one externally executed consumer scenario."""

    scenario: str
    status: ConsumerScenarioStatus
    reference: str
    checksum: str

    def __post_init__(self) -> None:
        if not self.scenario.strip():
            raise ValueError("consumer scenario must not be empty")
        if not self.reference.strip():
            raise ValueError("consumer scenario reference must not be empty")
        if not self.checksum.strip():
            raise ValueError("consumer scenario checksum must not be empty")


@dataclass(frozen=True, slots=True)
class ConsumerE2EManifest:
    """Immutable evidence manifest produced by the migrated consumer application."""

    consumer: str
    release: str
    environment: str
    scenarios: tuple[ConsumerScenarioEvidence, ...]

    def __post_init__(self) -> None:
        for value in (self.consumer, self.release, self.environment):
            if not value.strip():
                raise ValueError("consumer E2E manifest identity fields must not be empty")
        names = [item.scenario for item in self.scenarios]
        if len(names) != len(set(names)):
            raise ValueError("consumer E2E manifest contains duplicate scenarios")

    @property
    def missing_scenarios(self) -> tuple[str, ...]:
        observed = {item.scenario for item in self.scenarios}
        return tuple(sorted(REQUIRED_CONSUMER_SCENARIOS - observed))

    @property
    def non_green_scenarios(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.scenario
                for item in self.scenarios
                if item.scenario in REQUIRED_CONSUMER_SCENARIOS
                and item.status is not ConsumerScenarioStatus.PASS
            )
        )

    @property
    def green(self) -> bool:
        return not self.missing_scenarios and not self.non_green_scenarios

    def require_green(self) -> None:
        if self.missing_scenarios:
            raise ValueError(
                f"consumer E2E evidence missing scenarios: {self.missing_scenarios!r}"
            )
        if self.non_green_scenarios:
            raise ValueError(
                f"consumer E2E evidence has non-green scenarios: "
                f"{self.non_green_scenarios!r}"
            )


__all__ = [
    "REQUIRED_CONSUMER_SCENARIOS",
    "ConsumerE2EManifest",
    "ConsumerScenarioEvidence",
    "ConsumerScenarioStatus",
]
