"""Company chart migration plans (LOT-11).

A major coding change produces a new chart version through an explicit plan
(ADR COA-018); historical chart versions are never rewritten (ADR COA-020,
spec sections 93-96 of the chart architecture).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.domain.charts.company_chart import CompanyChart


class MigrationChangeKind(StrEnum):
    """Nature of one account change inside a migration plan."""

    REMAPPED = "REMAPPED"
    ADDED = "ADDED"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class AccountMigration:
    """One source-to-target account change within a migration."""

    source_code: str
    target_code: str | None
    kind: MigrationChangeKind
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.source_code:
            raise ValueError("source_code must be non-empty")
        if self.kind is MigrationChangeKind.RETIRED and self.target_code is not None:
            raise ValueError("a retired account must not carry a target code")


@dataclass(frozen=True, slots=True)
class CompanyChartMigrationPlan:
    """Versioned description of a chart transition.

    The plan targets a **new** chart version; it never rewrites the source
    version, so historical charts remain replayable.
    """

    source_chart_code: str
    source_version: str
    target_version: str
    effective_date: date
    reason: str
    account_migrations: tuple[AccountMigration, ...] = ()
    added_codes: tuple[str, ...] = ()
    retired_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not (self.source_chart_code and self.source_version and self.target_version):
            raise ValueError("chart code and both versions must be non-empty")
        if self.source_version == self.target_version:
            raise ValueError("source and target versions must differ")
        non_retired_sources = {
            migration.source_code
            for migration in self.account_migrations
            if migration.kind is not MigrationChangeKind.RETIRED
        }
        overlap = non_retired_sources & set(self.retired_codes)
        if overlap:
            raise ValueError(f"codes both migrated and retired: {sorted(overlap)}")

    def apply_to(self, chart: CompanyChart) -> CompanyChart:
        """Return the target chart version; the source version is preserved.

        The resulting chart retains every historical version (the previous
        ACTIVE becomes SUPERSEDED once the target version is activated).
        """
        if chart.code != self.source_chart_code:
            raise ValueError(f"plan targets chart {self.source_chart_code!r}, got {chart.code!r}")
        return chart.plan_version(
            label=self.target_version,
            effective_from=self.effective_date,
            reason=self.reason,
        )


__all__ = [
    "AccountMigration",
    "CompanyChartMigrationPlan",
    "MigrationChangeKind",
]
