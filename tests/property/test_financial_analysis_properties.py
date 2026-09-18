"""Property qualification for LOT-20 mathematical invariants."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.analysis import (
    AnalysisDefinitionSet,
    AnalysisInputValue,
    DefinitionStatus,
    FinancialAnalysisEngine,
    FinancialAnalysisRequest,
    FinancialAnalysisSource,
    FinancialAnalysisSourceType,
    FinancialRatioCategory,
    FinancialRatioDefinition,
    FunctionalBalanceDefinition,
    FunctionalBalanceEngine,
    IndicatorValueStatus,
    WorkingCapitalAnalysis,
)

ENTITY = EntityId("analysis-property-entity")


def _source() -> FinancialAnalysisSource:
    return FinancialAnalysisSource(
        source_type=FinancialAnalysisSourceType.CUSTOM_ANALYTICAL_SOURCE,
        source_ref="source:property",
        accounting_entity_id=ENTITY,
        period_id="FY2026",
        as_of=date(2026, 12, 31),
        currency=EUR,
        checksum="source-property-checksum",
    )


@given(
    numerator=st.integers(min_value=-10_000_000, max_value=10_000_000),
    denominator=st.integers(min_value=-10_000_000, max_value=10_000_000),
)
def test_ratio_never_emits_nan_or_infinity(numerator: int, denominator: int) -> None:
    definition = FinancialRatioDefinition(
        definition_id="ratio:property",
        code="PROPERTY_RATIO",
        label="Property ratio",
        category=FinancialRatioCategory.CUSTOM,
        version="1",
        numerator_ref="NUMERATOR",
        denominator_ref="DENOMINATOR",
        status=DefinitionStatus.ACTIVE,
    )
    definition_set = AnalysisDefinitionSet(
        definition_set_id="set:property",
        version="1",
        indicator_definitions=(),
        ratio_definitions=(definition,),
        status=DefinitionStatus.ACTIVE,
    )
    result = FinancialAnalysisEngine().run(
        FinancialAnalysisRequest(
            source=_source(),
            definition_set=definition_set,
            inputs=(
                AnalysisInputValue(
                    "NUMERATOR",
                    Decimal(numerator),
                    "source:numerator",
                ),
                AnalysisInputValue(
                    "DENOMINATOR",
                    Decimal(denominator),
                    "source:denominator",
                ),
            ),
        )
    )
    ratio = result.ratio("PROPERTY_RATIO")

    if denominator == 0:
        assert ratio.status is IndicatorValueStatus.UNDEFINED
        assert ratio.value is None
    else:
        assert ratio.status is IndicatorValueStatus.CALCULATED
        assert ratio.value is not None
        assert ratio.value.is_finite()


@given(
    stable_resources=st.integers(min_value=-1_000_000, max_value=1_000_000),
    stable_uses=st.integers(min_value=-1_000_000, max_value=1_000_000),
    operating_assets=st.integers(min_value=-1_000_000, max_value=1_000_000),
    operating_liabilities=st.integers(min_value=-1_000_000, max_value=1_000_000),
    non_operating_assets=st.integers(min_value=-1_000_000, max_value=1_000_000),
    non_operating_liabilities=st.integers(min_value=-1_000_000, max_value=1_000_000),
)
def test_working_capital_identity_holds_for_generated_inputs(
    stable_resources: int,
    stable_uses: int,
    operating_assets: int,
    operating_liabilities: int,
    non_operating_assets: int,
    non_operating_liabilities: int,
) -> None:
    frng = Decimal(stable_resources - stable_uses)
    bfre = Decimal(operating_assets - operating_liabilities)
    bfrhe = Decimal(non_operating_assets - non_operating_liabilities)
    bfr = bfre + bfrhe
    net_treasury = frng - bfr
    definition = FunctionalBalanceDefinition(
        definition_id="functional:property",
        version="1",
        stable_resources_ref="SR",
        stable_uses_ref="SU",
        operating_current_assets_ref="OA",
        operating_current_liabilities_ref="OL",
        non_operating_current_assets_ref="NOA",
        non_operating_current_liabilities_ref="NOL",
        cash_assets_ref="CA",
        cash_liabilities_ref="CL",
        status=DefinitionStatus.ACTIVE,
    )
    inputs = (
        AnalysisInputValue("SR", Decimal(stable_resources), "source:sr"),
        AnalysisInputValue("SU", Decimal(stable_uses), "source:su"),
        AnalysisInputValue("OA", Decimal(operating_assets), "source:oa"),
        AnalysisInputValue("OL", Decimal(operating_liabilities), "source:ol"),
        AnalysisInputValue("NOA", Decimal(non_operating_assets), "source:noa"),
        AnalysisInputValue("NOL", Decimal(non_operating_liabilities), "source:nol"),
        AnalysisInputValue("CA", net_treasury, "source:ca"),
        AnalysisInputValue("CL", Decimal("0"), "source:cl"),
    )
    functional = FunctionalBalanceEngine().build(
        definition=definition,
        source=_source(),
        inputs=inputs,
    )
    result = WorkingCapitalAnalysis.from_functional_balance(functional)

    assert result.frng is not None
    assert result.bfre is not None
    assert result.bfrhe is not None
    assert result.bfr is not None
    assert result.net_treasury is not None
    assert result.frng.amount == frng
    assert result.bfre.amount == bfre
    assert result.bfrhe.amount == bfrhe
    assert result.bfr.amount == bfr
    assert result.net_treasury.amount == net_treasury
    assert result.reconciled is True
