"""Shared LOT-20 financial-analysis golden coordinates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.analysis import (
    AnalysisDefinitionSet,
    AnalysisFormula,
    AnalysisFormulaOperation,
    AnalysisInputValue,
    AnalysisSnapshot,
    DefinitionStatus,
    FinancialAnalysisEngine,
    FinancialAnalysisRequest,
    FinancialAnalysisSource,
    FinancialIndicatorCategory,
    FinancialIndicatorDefinition,
    FinancialRatioCategory,
    FinancialRatioDefinition,
    FunctionalBalanceDefinition,
    FunctionalBalanceEngine,
    IndicatorDependency,
    IndicatorDependencyType,
    IndicatorUnit,
    WorkingCapitalAnalysis,
    inputs_from_report_snapshot,
)
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotLine,
    ReportSnapshotStatus,
)
from pyaccountingkit.domain.reporting.statement_definition import FinancialStatementType

ENTITY = EntityId("analysis-golden-entity")
AS_OF = date(2026, 12, 31)


@dataclass(frozen=True, slots=True)
class GoldenAnalysisRun:
    source_snapshot: ReportSnapshot
    result_checksum: str
    analysis_snapshot: AnalysisSnapshot
    indicator_values: tuple[tuple[str, Decimal | None], ...]
    ratio_values: tuple[tuple[str, Decimal | None], ...]
    frng: Money
    bfr: Money
    net_treasury: Money
    reconciled: bool


def _line(code: str, value: str) -> ReportSnapshotLine:
    return ReportSnapshotLine(
        code=code,
        label=code.replace("_", " ").title(),
        amount=Money.from_str(value, EUR),
    )


def build_report_snapshot() -> ReportSnapshot:
    return ReportSnapshot(
        snapshot_id="report:analysis:2026",
        accounting_entity_id=ENTITY,
        report_type=FinancialStatementType.CUSTOM,
        source_period_id="FY2026",
        source_checksum="trial-balance-analysis-2026",
        statement_definition_id="analysis-source-definition",
        statement_definition_version="1",
        statement_definition_checksum="analysis-source-definition-checksum",
        mapping_set_id="analysis-source-mapping",
        mapping_set_version="1",
        mapping_set_checksum="analysis-source-mapping-checksum",
        result_checksum="analysis-source-result-checksum",
        as_of=AS_OF,
        created_at=datetime(2027, 1, 1, tzinfo=UTC),
        status=ReportSnapshotStatus.PUBLISHED,
        lines=(
            _line("REVENUE", "1000.00"),
            _line("COGS", "400.00"),
            _line("OPERATING_EXPENSES", "250.00"),
            _line("EBITDA_ADJUSTMENT", "10.00"),
            _line("NET_RESULT", "200.00"),
            _line("NON_CASH_CHARGES", "30.00"),
            _line("STABLE_RESOURCES", "1200.00"),
            _line("STABLE_USES", "800.00"),
            _line("OPERATING_CURRENT_ASSETS", "500.00"),
            _line("OPERATING_CURRENT_LIABILITIES", "300.00"),
            _line("NON_OPERATING_CURRENT_ASSETS", "100.00"),
            _line("NON_OPERATING_CURRENT_LIABILITIES", "50.00"),
            _line("CASH_ASSETS", "250.00"),
            _line("CASH_LIABILITIES", "100.00"),
            _line("CURRENT_ASSETS", "850.00"),
            _line("CURRENT_LIABILITIES", "450.00"),
            _line("TOTAL_ASSETS", "1800.00"),
            _line("TOTAL_DEBT", "600.00"),
            _line("EQUITY", "1200.00"),
            _line("CFO", "280.00"),
        ),
        checksum="sealed-analysis-report-2026",
    )


def _source_dependency(ref: str) -> IndicatorDependency:
    return IndicatorDependency(
        dependency_type=IndicatorDependencyType.STATEMENT_LINE,
        dependency_id=ref,
    )


def _indicator_dependency(ref: str) -> IndicatorDependency:
    return IndicatorDependency(
        dependency_type=IndicatorDependencyType.INDICATOR,
        dependency_id=ref,
    )


def build_definition_set() -> AnalysisDefinitionSet:
    indicators = (
        FinancialIndicatorDefinition(
            definition_id="indicator:gross-margin",
            code="GROSS_MARGIN",
            label="Gross margin",
            category=FinancialIndicatorCategory.PERFORMANCE,
            version="1",
            formula=AnalysisFormula(
                AnalysisFormulaOperation.SUBTRACT,
                ("REVENUE", "COGS"),
            ),
            dependencies=(
                _source_dependency("REVENUE"),
                _source_dependency("COGS"),
            ),
            unit=IndicatorUnit.CURRENCY,
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialIndicatorDefinition(
            definition_id="indicator:ebe",
            code="EBE",
            label="EBE",
            category=FinancialIndicatorCategory.PERFORMANCE,
            version="1",
            formula=AnalysisFormula(
                AnalysisFormulaOperation.SUBTRACT,
                ("GROSS_MARGIN", "OPERATING_EXPENSES"),
            ),
            dependencies=(
                _indicator_dependency("GROSS_MARGIN"),
                _source_dependency("OPERATING_EXPENSES"),
            ),
            unit=IndicatorUnit.CURRENCY,
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialIndicatorDefinition(
            definition_id="indicator:ebitda",
            code="EBITDA",
            label="EBITDA",
            category=FinancialIndicatorCategory.PERFORMANCE,
            version="1",
            formula=AnalysisFormula(
                AnalysisFormulaOperation.ADD,
                ("EBE", "EBITDA_ADJUSTMENT"),
            ),
            dependencies=(
                _indicator_dependency("EBE"),
                _source_dependency("EBITDA_ADJUSTMENT"),
            ),
            unit=IndicatorUnit.CURRENCY,
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialIndicatorDefinition(
            definition_id="indicator:caf",
            code="CAF",
            label="CAF",
            category=FinancialIndicatorCategory.CASH_GENERATION,
            version="1",
            formula=AnalysisFormula(
                AnalysisFormulaOperation.ADD,
                ("NET_RESULT", "NON_CASH_CHARGES"),
            ),
            dependencies=(
                _source_dependency("NET_RESULT"),
                _source_dependency("NON_CASH_CHARGES"),
            ),
            unit=IndicatorUnit.CURRENCY,
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
    )
    ratios = (
        FinancialRatioDefinition(
            definition_id="ratio:net-margin",
            code="NET_MARGIN",
            label="Net margin",
            category=FinancialRatioCategory.PROFITABILITY,
            version="1",
            numerator_ref="NET_RESULT",
            denominator_ref="REVENUE",
            scale=Decimal("100"),
            unit=IndicatorUnit.PERCENTAGE,
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialRatioDefinition(
            definition_id="ratio:roa",
            code="ROA",
            label="Return on assets",
            category=FinancialRatioCategory.PROFITABILITY,
            version="1",
            numerator_ref="NET_RESULT",
            denominator_ref="TOTAL_ASSETS",
            scale=Decimal("100"),
            unit=IndicatorUnit.PERCENTAGE,
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialRatioDefinition(
            definition_id="ratio:current-ratio",
            code="CURRENT_RATIO",
            label="Current ratio",
            category=FinancialRatioCategory.LIQUIDITY,
            version="1",
            numerator_ref="CURRENT_ASSETS",
            denominator_ref="CURRENT_LIABILITIES",
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialRatioDefinition(
            definition_id="ratio:debt-to-assets",
            code="DEBT_TO_ASSETS",
            label="Debt to assets",
            category=FinancialRatioCategory.SOLVENCY,
            version="1",
            numerator_ref="TOTAL_DEBT",
            denominator_ref="TOTAL_ASSETS",
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialRatioDefinition(
            definition_id="ratio:equity",
            code="EQUITY_RATIO",
            label="Equity ratio",
            category=FinancialRatioCategory.CAPITAL_STRUCTURE,
            version="1",
            numerator_ref="EQUITY",
            denominator_ref="TOTAL_ASSETS",
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialRatioDefinition(
            definition_id="ratio:cfo-revenue",
            code="CFO_TO_REVENUE",
            label="CFO to revenue",
            category=FinancialRatioCategory.CASH_GENERATION,
            version="1",
            numerator_ref="CFO",
            denominator_ref="REVENUE",
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
        FinancialRatioDefinition(
            definition_id="ratio:asset-turnover",
            code="ASSET_TURNOVER",
            label="Asset turnover",
            category=FinancialRatioCategory.EFFICIENCY,
            version="1",
            numerator_ref="REVENUE",
            denominator_ref="TOTAL_ASSETS",
            status=DefinitionStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
        ),
    )
    return AnalysisDefinitionSet(
        definition_set_id="analysis:golden",
        version="1",
        indicator_definitions=indicators,
        ratio_definitions=ratios,
        status=DefinitionStatus.ACTIVE,
        effective_from=date(2026, 1, 1),
    )


def build_functional_balance_definition() -> FunctionalBalanceDefinition:
    return FunctionalBalanceDefinition(
        definition_id="functional-balance:golden",
        version="1",
        stable_resources_ref="STABLE_RESOURCES",
        stable_uses_ref="STABLE_USES",
        operating_current_assets_ref="OPERATING_CURRENT_ASSETS",
        operating_current_liabilities_ref="OPERATING_CURRENT_LIABILITIES",
        non_operating_current_assets_ref="NON_OPERATING_CURRENT_ASSETS",
        non_operating_current_liabilities_ref="NON_OPERATING_CURRENT_LIABILITIES",
        cash_assets_ref="CASH_ASSETS",
        cash_liabilities_ref="CASH_LIABILITIES",
        status=DefinitionStatus.ACTIVE,
        effective_from=date(2026, 1, 1),
    )


def run_golden_analysis(
    *,
    analysis_snapshot_id: str,
    generated_at: datetime,
) -> GoldenAnalysisRun:
    source_snapshot = build_report_snapshot()
    source = FinancialAnalysisSource.from_report_snapshot(source_snapshot)
    inputs: tuple[AnalysisInputValue, ...] = inputs_from_report_snapshot(source_snapshot)
    definition_set = build_definition_set()
    result = FinancialAnalysisEngine().run(
        FinancialAnalysisRequest(
            source=source,
            definition_set=definition_set,
            inputs=inputs,
        )
    )
    functional = FunctionalBalanceEngine().build(
        definition=build_functional_balance_definition(),
        source=source,
        inputs=inputs,
    )
    working_capital = WorkingCapitalAnalysis.from_functional_balance(functional)
    if (
        working_capital.frng is None
        or working_capital.bfr is None
        or working_capital.net_treasury is None
        or working_capital.reconciled is None
    ):
        raise AssertionError("golden working-capital analysis must be calculated")
    snapshot = AnalysisSnapshot.from_result(
        snapshot_id=analysis_snapshot_id,
        result=result,
        generated_at=generated_at,
        functional_balance=functional,
        working_capital=working_capital,
    )
    return GoldenAnalysisRun(
        source_snapshot=source_snapshot,
        result_checksum=result.checksum,
        analysis_snapshot=snapshot,
        indicator_values=tuple(
            (value.code, value.value) for value in result.indicator_values
        ),
        ratio_values=tuple((value.code, value.value) for value in result.ratio_values),
        frng=working_capital.frng,
        bfr=working_capital.bfr,
        net_treasury=working_capital.net_treasury,
        reconciled=working_capital.reconciled,
    )


__all__ = [
    "AS_OF",
    "ENTITY",
    "GoldenAnalysisRun",
    "build_definition_set",
    "build_functional_balance_definition",
    "build_report_snapshot",
    "run_golden_analysis",
]
