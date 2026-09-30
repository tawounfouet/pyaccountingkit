"""Fail-closed legacy-retirement qualification for CFA FRA LOT-26."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.integrations.cfa_fra.compatibility import MigrationRouting


class LegacyRetirementBlockedError(RuntimeError):
    """Raised when the CFA FRA legacy accounting engine is not safe to retire."""

    def __init__(self, blockers: tuple[str, ...]) -> None:
        self.blockers = blockers
        super().__init__("legacy retirement blocked: " + ", ".join(blockers))


@dataclass(frozen=True, slots=True)
class LegacyRetirementEvidence:
    """Release evidence required before the duplicate accounting engine can disappear."""

    golden_parity_green: bool
    production_adapters_green: bool
    consumer_e2e_green: bool
    identities_traceable: bool


@dataclass(frozen=True, slots=True)
class LegacyRetirementDecision:
    """Deterministic decision describing whether retirement is allowed."""

    ready: bool
    blockers: tuple[str, ...]


class LegacyRetirementGate:
    """Require routes and evidence to be fully migrated before retirement."""

    def evaluate(
        self,
        routing: MigrationRouting,
        evidence: LegacyRetirementEvidence,
    ) -> LegacyRetirementDecision:
        blockers: list[str] = []

        for operation in routing.remaining_legacy_mutations():
            blockers.append(f"mutation:{operation}:legacy")
        for operation in routing.remaining_legacy_reads():
            blockers.append(f"read:{operation}:legacy")
        for operation in sorted(routing.dual_run_reads):
            blockers.append(f"read:{operation}:dual-run-active")

        if not evidence.golden_parity_green:
            blockers.append("evidence:golden-parity")
        if not evidence.production_adapters_green:
            blockers.append("evidence:production-adapters")
        if not evidence.consumer_e2e_green:
            blockers.append("evidence:consumer-e2e")
        if not evidence.identities_traceable:
            blockers.append("evidence:legacy-identities")

        normalized = tuple(sorted(blockers))
        return LegacyRetirementDecision(ready=not normalized, blockers=normalized)

    def require_ready(
        self,
        routing: MigrationRouting,
        evidence: LegacyRetirementEvidence,
    ) -> None:
        decision = self.evaluate(routing, evidence)
        if not decision.ready:
            raise LegacyRetirementBlockedError(decision.blockers)


__all__ = [
    "LegacyRetirementBlockedError",
    "LegacyRetirementDecision",
    "LegacyRetirementEvidence",
    "LegacyRetirementGate",
]
