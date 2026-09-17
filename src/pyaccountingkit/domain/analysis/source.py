"""Sealed inputs consumed by the Financial Analysis bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.analysis.errors import (
    InvalidAnalysisSourceError,
    StaleAnalysisSourceError,
)
from pyaccountingkit.domain.reporting.report_snapshot import ReportSnapshot
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance


class FinancialAnalysisSourceType(StrEnum):
    REPORT_SNAPSHOT = "REPORT_SNAPSHOT"
    TRIAL_BALANCE_SNAPSHOT = "TRIAL_BALANCE_SNAPSHOT"
    MULTI_REPORT_SNAPSHOT = "MULTI_REPORT_SNAPSHOT"
    CUSTOM_ANALYTICAL_SOURCE = "CUSTOM_ANALYTICAL_SOURCE"


class FinancialAnalysisSourceFreshness(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True, slots=True)
class FinancialAnalysisSource:
    source_type: FinancialAnalysisSourceType
    source_ref: str
    accounting_entity_id: EntityId
    period_id: str
    as_of: date
    currency: Currency
    checksum: str
    freshness: FinancialAnalysisSourceFreshness = FinancialAnalysisSourceFreshness.CURRENT
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise InvalidAnalysisSourceError("analysis source ref must not be empty")
        if not str(self.accounting_entity_id).strip():
            raise InvalidAnalysisSourceError("analysis source entity must not be empty")
        if not self.period_id.strip():
            raise InvalidAnalysisSourceError("analysis source period must not be empty")
        if not self.checksum.strip():
            raise InvalidAnalysisSourceError("analysis source checksum must not be empty")
        if any(not key.strip() for key, _ in self.metadata):
            raise InvalidAnalysisSourceError("analysis source metadata keys must not be empty")

    @classmethod
    def from_report_snapshot(
        cls,
        snapshot: ReportSnapshot,
        *,
        freshness: FinancialAnalysisSourceFreshness = FinancialAnalysisSourceFreshness.CURRENT,
    ) -> FinancialAnalysisSource:
        if not snapshot.lines:
            raise InvalidAnalysisSourceError(
                "report snapshot must expose at least one line to resolve analysis currency"
            )
        currency = snapshot.lines[0].amount.currency
        if any(line.amount.currency != currency for line in snapshot.lines):
            raise InvalidAnalysisSourceError("report snapshot mixes currencies")
        return cls(
            source_type=FinancialAnalysisSourceType.REPORT_SNAPSHOT,
            source_ref=snapshot.snapshot_id,
            accounting_entity_id=snapshot.accounting_entity_id,
            period_id=snapshot.source_period_id,
            as_of=snapshot.as_of,
            currency=currency,
            checksum=snapshot.checksum,
            freshness=freshness,
            metadata=(("report_type", snapshot.report_type.value),),
        )

    @classmethod
    def from_trial_balance(
        cls,
        trial_balance: TrialBalance,
        *,
        as_of: date,
        freshness: FinancialAnalysisSourceFreshness = FinancialAnalysisSourceFreshness.CURRENT,
    ) -> FinancialAnalysisSource:
        if trial_balance.accounting_entity_id is None:
            raise InvalidAnalysisSourceError(
                "trial balance must carry accounting_entity_id for financial analysis"
            )
        return cls(
            source_type=FinancialAnalysisSourceType.TRIAL_BALANCE_SNAPSHOT,
            source_ref=(
                f"trial_balance:{trial_balance.period_id}:{trial_balance.snapshot.value}"
            ),
            accounting_entity_id=trial_balance.accounting_entity_id,
            period_id=trial_balance.period_id,
            as_of=as_of,
            currency=trial_balance.currency,
            checksum=trial_balance.checksum,
            freshness=freshness,
            metadata=(("snapshot", trial_balance.snapshot.value),),
        )

    def assert_publishable(self, *, historical_replay: bool = False) -> None:
        if self.freshness is FinancialAnalysisSourceFreshness.CURRENT:
            return
        if historical_replay:
            return
        raise StaleAnalysisSourceError(
            f"analysis source {self.source_ref!r} is {self.freshness.value}"
        )


__all__ = [
    "FinancialAnalysisSource",
    "FinancialAnalysisSourceFreshness",
    "FinancialAnalysisSourceType",
]
