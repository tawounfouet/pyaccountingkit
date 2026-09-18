"""Immutable replayable financial-analysis snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.analysis.diagnostics import FinancialDiagnostic
from pyaccountingkit.domain.analysis.engine import FinancialAnalysisResult
from pyaccountingkit.domain.analysis.errors import InvalidAnalysisSnapshotError
from pyaccountingkit.domain.analysis.functional_balance import FunctionalBalanceResult
from pyaccountingkit.domain.analysis.trends import MetricTrend
from pyaccountingkit.domain.analysis.working_capital import WorkingCapitalAnalysis


@dataclass(frozen=True, slots=True)
class AnalysisSnapshot:
    snapshot_id: str
    accounting_entity_id: EntityId
    period_id: str
    as_of: date
    source_type: str
    source_ref: str
    source_checksum: str
    source_freshness: str
    definition_set_id: str
    definition_set_version: str
    definition_set_checksum: str
    analysis_result_checksum: str
    indicator_checksums: tuple[str, ...]
    ratio_checksums: tuple[str, ...]
    trace_checksums: tuple[str, ...]
    functional_balance_checksum: str | None
    working_capital_checksum: str | None
    trend_checksums: tuple[str, ...]
    diagnostic_checksums: tuple[str, ...]
    generated_at: datetime
    checksum: str

    @classmethod
    def from_result(
        cls,
        *,
        snapshot_id: str,
        result: FinancialAnalysisResult,
        generated_at: datetime,
        functional_balance: FunctionalBalanceResult | None = None,
        working_capital: WorkingCapitalAnalysis | None = None,
        trends: tuple[MetricTrend, ...] = (),
        diagnostics: tuple[FinancialDiagnostic, ...] = (),
    ) -> AnalysisSnapshot:
        if not snapshot_id.strip():
            raise InvalidAnalysisSnapshotError("analysis snapshot id must not be empty")
        indicator_checksums = tuple(value.checksum for value in result.indicator_values)
        ratio_checksums = tuple(value.checksum for value in result.ratio_values)
        trace_checksums = tuple(trace.checksum for trace in result.traces)
        trend_checksums = tuple(sorted(item.checksum for item in trends))
        diagnostic_checksums = tuple(sorted(item.checksum for item in diagnostics))
        checksum = cls._semantic_checksum(
            result=result,
            functional_balance=functional_balance,
            working_capital=working_capital,
            trend_checksums=trend_checksums,
            diagnostic_checksums=diagnostic_checksums,
        )
        return cls(
            snapshot_id=snapshot_id,
            accounting_entity_id=result.source.accounting_entity_id,
            period_id=result.source.period_id,
            as_of=result.source.as_of,
            source_type=result.source.source_type.value,
            source_ref=result.source.source_ref,
            source_checksum=result.source.checksum,
            source_freshness=result.source.freshness.value,
            definition_set_id=result.definition_set_id,
            definition_set_version=result.definition_set_version,
            definition_set_checksum=result.definition_set_checksum,
            analysis_result_checksum=result.checksum,
            indicator_checksums=indicator_checksums,
            ratio_checksums=ratio_checksums,
            trace_checksums=trace_checksums,
            functional_balance_checksum=(
                functional_balance.checksum if functional_balance is not None else None
            ),
            working_capital_checksum=(
                working_capital.checksum if working_capital is not None else None
            ),
            trend_checksums=trend_checksums,
            diagnostic_checksums=diagnostic_checksums,
            generated_at=generated_at,
            checksum=checksum,
        )

    @staticmethod
    def _semantic_checksum(
        *,
        result: FinancialAnalysisResult,
        functional_balance: FunctionalBalanceResult | None,
        working_capital: WorkingCapitalAnalysis | None,
        trend_checksums: tuple[str, ...],
        diagnostic_checksums: tuple[str, ...],
    ) -> str:
        payload = {
            "entity_id": str(result.source.accounting_entity_id),
            "period_id": result.source.period_id,
            "as_of": result.source.as_of.isoformat(),
            "source_type": result.source.source_type.value,
            "source_ref": result.source.source_ref,
            "source_checksum": result.source.checksum,
            "source_freshness": result.source.freshness.value,
            "definition_set_id": result.definition_set_id,
            "definition_set_version": result.definition_set_version,
            "definition_set_checksum": result.definition_set_checksum,
            "analysis_result_checksum": result.checksum,
            "functional_balance_checksum": (
                functional_balance.checksum if functional_balance is not None else None
            ),
            "working_capital_checksum": (
                working_capital.checksum if working_capital is not None else None
            ),
            "trend_checksums": list(trend_checksums),
            "diagnostic_checksums": list(diagnostic_checksums),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


__all__ = ["AnalysisSnapshot"]
