"""Company chart configuration and versioning aggregate (LOT-11).

The chart aggregate carries configuration and versions; it does not hold every
account as a child (ADR COA-007/008). Historical versions are preserved and
resolved explicitly by accounting date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.errors import AmbiguousChartVersionError, ChartVersionNotFoundError
from pyaccountingkit.core.identifiers import EntityId


class ChartStatus(StrEnum):
    """Lifecycle of a company chart version."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True, slots=True)
class CompanyChartVersion:
    """One version of a company chart, with effective bounds.

    Effective intervals are interpreted as ``[effective_from, effective_to)``.
    This makes a superseded version stop exactly when its successor starts.
    """

    label: str
    status: ChartStatus
    effective_from: date | None = None
    effective_to: date | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("version label must be non-empty")
        if self.effective_to is not None and self.effective_from is not None:
            if self.effective_to < self.effective_from:
                raise ValueError("effective_to precedes effective_from")

    def applies_on(self, accounting_date: date) -> bool:
        """Return whether this non-DRAFT version applies on *accounting_date*."""
        if self.status is ChartStatus.DRAFT:
            return False
        if self.effective_from is None or accounting_date < self.effective_from:
            return False
        return self.effective_to is None or accounting_date < self.effective_to


@dataclass(frozen=True, slots=True)
class CompanyChart:
    """Configuration / version aggregate root for a company chart."""

    chart_id: str
    entity_id: EntityId
    code: str
    label: str
    primary_standard: str
    code_policy_id: str
    reference_snapshot_id: str
    versions: tuple[CompanyChartVersion, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("chart_id", "code", "label", "primary_standard", "code_policy_id"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must be non-empty")
        labels = [version.label for version in self.versions]
        if len(labels) != len(set(labels)):
            raise ValueError("duplicate chart version labels")
        active = [version for version in self.versions if version.status is ChartStatus.ACTIVE]
        if len(active) > 1:
            raise ValueError("at most one ACTIVE chart version")

    @property
    def current_version(self) -> CompanyChartVersion | None:
        return self.versions[-1] if self.versions else None

    @property
    def current_active_version(self) -> CompanyChartVersion | None:
        return next(
            (
                version
                for version in reversed(self.versions)
                if version.status is ChartStatus.ACTIVE
            ),
            None,
        )

    def version_at(self, accounting_date: date) -> CompanyChartVersion:
        """Resolve exactly one effective historical/current version for a date."""
        applicable = tuple(
            version for version in self.versions if version.applies_on(accounting_date)
        )
        if not applicable:
            raise ChartVersionNotFoundError(
                f"no chart version of {self.chart_id!r} applies on {accounting_date}"
            )
        if len(applicable) > 1:
            raise AmbiguousChartVersionError(
                f"{len(applicable)} chart versions of {self.chart_id!r} "
                f"apply on {accounting_date}: "
                + ", ".join(version.label for version in applicable)
            )
        return applicable[0]

    def activate(self, label: str, effective_from: date) -> CompanyChart:
        """Activate a DRAFT version, superseding the previous ACTIVE version."""
        if any(
            version.label == label
            for version in self.versions
            if version.status is ChartStatus.DRAFT
        ) is False:
            raise ValueError(f"no DRAFT version {label!r} in chart")
        previous = self.current_active_version
        versions: list[CompanyChartVersion] = []
        for version in self.versions:
            if version.label == label:
                versions.append(
                    CompanyChartVersion(
                        label=version.label,
                        status=ChartStatus.ACTIVE,
                        effective_from=effective_from,
                        effective_to=None,
                        reason=version.reason,
                    )
                )
            elif previous is not None and version.label == previous.label:
                versions.append(
                    CompanyChartVersion(
                        label=version.label,
                        status=ChartStatus.SUPERSEDED,
                        effective_from=version.effective_from,
                        effective_to=effective_from,
                        reason=version.reason,
                    )
                )
            else:
                versions.append(version)
        return CompanyChart(
            chart_id=self.chart_id,
            entity_id=self.entity_id,
            code=self.code,
            label=self.label,
            primary_standard=self.primary_standard,
            code_policy_id=self.code_policy_id,
            reference_snapshot_id=self.reference_snapshot_id,
            versions=tuple(versions),
        )

    def plan_version(
        self,
        label: str,
        effective_from: date,
        reason: str = "",
    ) -> CompanyChart:
        """Plan a new DRAFT version without mutating any historical version."""
        if any(version.label == label for version in self.versions):
            raise ValueError(f"version {label!r} already exists")
        last = self.current_version
        if last is not None and last.effective_from is not None:
            if effective_from < last.effective_from:
                raise ValueError("new version cannot start before a previous version")
            if last.status is ChartStatus.ACTIVE and effective_from == last.effective_from:
                raise ValueError("new version overlaps the active version")
        return CompanyChart(
            chart_id=self.chart_id,
            entity_id=self.entity_id,
            code=self.code,
            label=self.label,
            primary_standard=self.primary_standard,
            code_policy_id=self.code_policy_id,
            reference_snapshot_id=self.reference_snapshot_id,
            versions=(
                *self.versions,
                CompanyChartVersion(
                    label=label,
                    status=ChartStatus.DRAFT,
                    effective_from=effective_from,
                    reason=reason,
                ),
            ),
        )


__all__ = ["ChartStatus", "CompanyChart", "CompanyChartVersion"]
