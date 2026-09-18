"""Unit qualification for LOT-20 financial analysis."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.analysis import (
    AnalysisDefinitionSet,
    AnalysisFormula,
    AnalysisFormulaOperation,
    AnalysisInputValue,
    DefinitionStatus,
    DiagnosticEngine,
    DiagnosticOperator,
    DiagnosticRule,
    DiagnosticStatus,
    FinancialAnalysisEngine,
    FinancialAnalysisRequest,
    FinancialAnalysisSource,
    FinancialAnalysisSourceFreshness,
    FinancialAnalysisSourceType,
    FinancialIndicatorCategory,
    FinancialIndicatorDefinition,
    FinancialRatioCategory,
    FinancialRatioDefinition,
    IndicatorDependency,
    IndicatorDependencyType,
    IndicatorUnit,
    IndicatorValueStatus,
    MetricTrend,
    PeriodObservation,
    StaleAnalysisSourceError,
)
from tests.support.financial_analysis import run_golden_analysis

ENTITY = EntityId("analysis-unit-entity")


def _source() -> FinancialAnalysisSource:
    return FinancialAnalysisSource(
        source_type=FinancialAnalysisSourceType.CUSTOM_ANALYTICAL_SOURCE,
        source_ref="source:unit",
        accounting_entity_id=ENTITY,
        period_id="FY2026",
        as_of=date(2026, 12, 31),
        currency=EUR,
        checksum="source-unit-checksum",
    )


def _definition(
    *,
    code: str,
    operation: AnalysisFormulaOperation,
    operands: tuple[str, ...],
) -> FinancialIndicatorDefinition:
    return FinancialIndicatorDefinition(
        definition_id=f"indicator:{code.lower()}",
        code=code,
        label=code,
        category=FinancialIndicatorCategory.CUSTOM,
        version="1",
        formula=AnalysisFormula(operation, operands),
        dependencies=tuple(
            IndicatorDependency(
                dependency_type=IndicatorDependencyType.EXTERNAL_ANALYTICAL_INPUT,
                dependency_id=operand,
            )
            for operand in operands
        ),
        unit=IndicatorUnit.RATIO,
        status=DefinitionStatus.ACTIVE,
        effective_from=date(2026, 1, 1),
    )


def test_missing_required_input_is_indeterminate() -> None:
    definition = _definition(
        code="MISSING",
        operation=AnalysisFormulaOperation.ADD,
        operands=("A", "B"),
    )
    definition_set = AnalysisDefinitionSet(
        definition_set_id="set:missing",
        version="1",
        indicator_definitions=(definition,),
        status=DefinitionStatus.ACTIVE,
    )
    result = FinancialAnalysisEngine().run(
        FinancialAnalysisRequest(
            source=_source(),
            definition_set=definition_set,
            inputs=(AnalysisInputValue("A", Decimal("10"), "source:A"),),
        )
    )

    assert result.indicator("MISSING").status is IndicatorValueStatus.INDETERMINATE
    assert result.indicator("MISSING").value is None


def test_division_by_zero_is_undefined_not_zero_nan_or_infinity() -> None:
    definition = _definition(
        code="DIVISION",
        operation=AnalysisFormulaOperation.DIVIDE,
        operands=("A", "B"),
    )
    definition_set = AnalysisDefinitionSet(
        definition_set_id="set:division",
        version="1",
        indicator_definitions=(definition,),
        status=DefinitionStatus.ACTIVE,
    )
    result = FinancialAnalysisEngine().run(
        FinancialAnalysisRequest(
            source=_source(),
            definition_set=definition_set,
            inputs=(
                AnalysisInputValue("A", Decimal("10"), "source:A"),
                AnalysisInputValue("B", Decimal("0"), "source:B"),
            ),
        )
    )

    value = result.indicator("DIVISION")
    assert value.status is IndicatorValueStatus.UNDEFINED
    assert value.value is None


def test_ratio_zero_denominator_defaults_to_undefined() -> None:
    ratio = FinancialRatioDefinition(
        definition_id="ratio:test",
        code="TEST_RATIO",
        label="Test ratio",
        category=FinancialRatioCategory.CUSTOM,
        version="1",
        numerator_ref="A",
        denominator_ref="B",
        status=DefinitionStatus.ACTIVE,
    )
    definition_set = AnalysisDefinitionSet(
        definition_set_id="set:ratio",
        version="1",
        indicator_definitions=(),
        ratio_definitions=(ratio,),
        status=DefinitionStatus.ACTIVE,
    )
    result = FinancialAnalysisEngine().run(
        FinancialAnalysisRequest(
            source=_source(),
            definition_set=definition_set,
            inputs=(
                AnalysisInputValue("A", Decimal("10"), "source:A"),
                AnalysisInputValue("B", Decimal("0"), "source:B"),
            ),
        )
    )

    assert result.ratio("TEST_RATIO").status is IndicatorValueStatus.UNDEFINED
    assert result.ratio("TEST_RATIO").value is None


def test_stale_source_is_rejected_unless_historical_replay_is_explicit() -> None:
    definition = _definition(
        code="TOTAL",
        operation=AnalysisFormulaOperation.ADD,
        operands=("A", "B"),
    )
    definition_set = AnalysisDefinitionSet(
        definition_set_id="set:stale",
        version="1",
        indicator_definitions=(definition,),
        status=DefinitionStatus.ACTIVE,
    )
    request = FinancialAnalysisRequest(
        source=replace(
            _source(),
            freshness=FinancialAnalysisSourceFreshness.STALE,
        ),
        definition_set=definition_set,
        inputs=(
            AnalysisInputValue("A", Decimal("1"), "source:A"),
            AnalysisInputValue("B", Decimal("2"), "source:B"),
        ),
    )

    with pytest.raises(StaleAnalysisSourceError):
        FinancialAnalysisEngine().run(request)

    replay = FinancialAnalysisEngine().run(replace(request, historical_replay=True))
    assert replay.indicator("TOTAL").value == Decimal("3")


def test_ebe_and_ebitda_are_distinct_definition_driven_metrics() -> None:
    run = run_golden_analysis(
        analysis_snapshot_id="analysis:unit",
        generated_at=datetime(2027, 1, 2, tzinfo=UTC),
    )
    values = dict(run.indicator_values)

    assert values["EBE"] == Decimal("350.00")
    assert values["EBITDA"] == Decimal("360.00")
    assert values["EBE"] != values["EBITDA"]


def test_working_capital_golden_identities_reconcile() -> None:
    run = run_golden_analysis(
        analysis_snapshot_id="analysis:working-capital",
        generated_at=datetime(2027, 1, 2, tzinfo=UTC),
    )

    assert run.frng.amount == Decimal("400.00")
    assert run.bfr.amount == Decimal("250.00")
    assert run.net_treasury.amount == Decimal("150.00")
    assert run.reconciled is True


def test_trend_and_diagnostic_are_explicit_and_deterministic() -> None:
    trend = MetricTrend.build(
        metric_code="NET_MARGIN",
        observations=(
            PeriodObservation(
                period_id="2025",
                as_of=date(2025, 12, 31),
                value=Decimal("15"),
                status=IndicatorValueStatus.CALCULATED,
                source_checksum="source-2025",
            ),
            PeriodObservation(
                period_id="2026",
                as_of=date(2026, 12, 31),
                value=Decimal("20"),
                status=IndicatorValueStatus.CALCULATED,
                source_checksum="source-2026",
            ),
        ),
    )
    rule = DiagnosticRule(
        rule_id="diagnostic:net-margin-target",
        version="1",
        metric_code="NET_MARGIN",
        operator=DiagnosticOperator.GTE,
        threshold=Decimal("18"),
        label="TARGET_REACHED",
        message="Configured net-margin target reached.",
        status=DefinitionStatus.ACTIVE,
    )
    diagnostic = DiagnosticEngine().evaluate(
        rule=rule,
        metric_value=Decimal("20"),
        metric_status=IndicatorValueStatus.CALCULATED,
    )

    assert trend.absolute_change == Decimal("5")
    assert trend.percentage_change == Decimal("33.33333333333333333333333333")
    assert diagnostic.status is DiagnosticStatus.MATCHED
    assert diagnostic.label == "TARGET_REACHED"
