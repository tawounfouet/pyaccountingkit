from datetime import date
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.analysis import (
    AnalysisDefinitionSet,
    AnalysisFormula,
    AnalysisFormulaOperation,
    DefinitionStatus,
    FinancialAnalysisSource,
    FinancialAnalysisSourceFreshness,
    FinancialAnalysisSourceType,
    FinancialIndicatorCategory,
    FinancialIndicatorDefinition,
    FinancialRatioCategory,
    FinancialRatioDefinition,
    IndicatorDependency,
    IndicatorDependencyCycleError,
    IndicatorDependencyType,
    IndicatorUnit,
    InvalidIndicatorDefinitionError,
    InvalidRatioDefinitionError,
    StaleAnalysisSourceError,
)


def _indicator(
    code: str,
    dependency_id: str,
    dependency_type: IndicatorDependencyType = IndicatorDependencyType.STATEMENT_LINE,
) -> FinancialIndicatorDefinition:
    dependency = IndicatorDependency(dependency_type, dependency_id)
    return FinancialIndicatorDefinition(
        definition_id=f"indicator:{code.lower()}",
        code=code,
        label=code,
        category=FinancialIndicatorCategory.PERFORMANCE,
        version="1",
        formula=AnalysisFormula(AnalysisFormulaOperation.SUM, (dependency_id,)),
        dependencies=(dependency,),
        unit=IndicatorUnit.CURRENCY,
        status=DefinitionStatus.ACTIVE,
    )


def test_stale_source_is_rejected_for_current_publication() -> None:
    source = FinancialAnalysisSource(
        source_type=FinancialAnalysisSourceType.CUSTOM_ANALYTICAL_SOURCE,
        source_ref="source-1",
        accounting_entity_id=EntityId("entity-1"),
        period_id="FY2026",
        as_of=date(2026, 12, 31),
        currency=EUR,
        checksum="checksum-1",
        freshness=FinancialAnalysisSourceFreshness.STALE,
    )

    with pytest.raises(StaleAnalysisSourceError):
        source.assert_publishable()

    source.assert_publishable(historical_replay=True)


def test_indicator_formula_cannot_reference_undeclared_dependency() -> None:
    with pytest.raises(InvalidIndicatorDefinitionError):
        FinancialIndicatorDefinition(
            definition_id="indicator:ebe",
            code="EBE",
            label="EBE",
            category=FinancialIndicatorCategory.PERFORMANCE,
            version="1",
            formula=AnalysisFormula(AnalysisFormulaOperation.SUM, ("VA",)),
            dependencies=(
                IndicatorDependency(
                    IndicatorDependencyType.STATEMENT_LINE,
                    "REVENUE",
                ),
            ),
            unit=IndicatorUnit.CURRENCY,
        )


def test_definition_set_rejects_indicator_dependency_cycle() -> None:
    a = _indicator("A", "B", IndicatorDependencyType.INDICATOR)
    b = _indicator("B", "A", IndicatorDependencyType.INDICATOR)

    with pytest.raises(IndicatorDependencyCycleError):
        AnalysisDefinitionSet(
            definition_set_id="set-1",
            version="1",
            indicator_definitions=(a, b),
        )


def test_ebe_and_ebitda_remain_distinct_definitions() -> None:
    ebe = _indicator("EBE", "EBE_SOURCE")
    ebitda = _indicator("EBITDA", "EBITDA_SOURCE")
    definitions = AnalysisDefinitionSet(
        definition_set_id="set-performance",
        version="1",
        indicator_definitions=(ebe, ebitda),
        status=DefinitionStatus.ACTIVE,
    )

    assert ebe.definition_id != ebitda.definition_id
    assert {item.code for item in definitions.indicator_definitions} == {"EBE", "EBITDA"}
    assert len(definitions.checksum) == 64


def test_ratio_scale_must_be_positive_finite_decimal() -> None:
    with pytest.raises(InvalidRatioDefinitionError):
        FinancialRatioDefinition(
            definition_id="ratio:margin",
            code="NET_MARGIN",
            label="Net margin",
            category=FinancialRatioCategory.PROFITABILITY,
            version="1",
            numerator_ref="NET_RESULT",
            denominator_ref="REVENUE",
            scale=Decimal("0"),
        )


def test_definition_set_checksum_is_deterministic() -> None:
    indicator = _indicator("REVENUE_ANALYSIS", "REVENUE")
    ratio = FinancialRatioDefinition(
        definition_id="ratio:revenue-share",
        code="REVENUE_SHARE",
        label="Revenue share",
        category=FinancialRatioCategory.CUSTOM,
        version="1",
        numerator_ref="REVENUE_ANALYSIS",
        denominator_ref="REVENUE_ANALYSIS",
        scale=Decimal("100"),
        unit=IndicatorUnit.PERCENTAGE,
        status=DefinitionStatus.ACTIVE,
    )

    left = AnalysisDefinitionSet(
        definition_set_id="set-1",
        version="1",
        indicator_definitions=(indicator,),
        ratio_definitions=(ratio,),
    )
    right = AnalysisDefinitionSet(
        definition_set_id="set-1",
        version="1",
        indicator_definitions=(indicator,),
        ratio_definitions=(ratio,),
    )

    assert left.checksum == right.checksum
