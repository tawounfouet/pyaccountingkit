"""Pure deterministic financial-analysis engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from pyaccountingkit.domain.analysis.definition_set import AnalysisDefinitionSet
from pyaccountingkit.domain.analysis.errors import (
    InvalidAnalysisDefinitionSetError,
    UnsupportedAnalysisOperationError,
)
from pyaccountingkit.domain.analysis.formula import AnalysisFormula, AnalysisFormulaOperation
from pyaccountingkit.domain.analysis.indicators import (
    FinancialIndicatorDefinition,
    IndicatorDependencyType,
    IndicatorValueStatus,
)
from pyaccountingkit.domain.analysis.ratios import (
    FinancialRatioDefinition,
    ZeroDenominatorPolicy,
)
from pyaccountingkit.domain.analysis.source import FinancialAnalysisSource
from pyaccountingkit.domain.analysis.values import (
    AnalysisInputValue,
    AnalysisMetricKind,
    CalculationTrace,
    DependencyObservation,
    FinancialIndicatorValue,
    FinancialRatioValue,
)

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class FinancialAnalysisRequest:
    source: FinancialAnalysisSource
    definition_set: AnalysisDefinitionSet
    inputs: tuple[AnalysisInputValue, ...]
    historical_replay: bool = False

    def __post_init__(self) -> None:
        keys = tuple(item.key for item in self.inputs)
        if len(keys) != len(set(keys)):
            raise InvalidAnalysisDefinitionSetError("analysis input keys must be unique")


@dataclass(frozen=True, slots=True)
class FinancialAnalysisResult:
    source: FinancialAnalysisSource
    definition_set_id: str
    definition_set_version: str
    definition_set_checksum: str
    indicator_values: tuple[FinancialIndicatorValue, ...]
    ratio_values: tuple[FinancialRatioValue, ...]
    traces: tuple[CalculationTrace, ...]
    checksum: str

    def indicator(self, code: str) -> FinancialIndicatorValue:
        for value in self.indicator_values:
            if value.code == code:
                return value
        raise KeyError(code)

    def ratio(self, code: str) -> FinancialRatioValue:
        for value in self.ratio_values:
            if value.code == code:
                return value
        raise KeyError(code)


class FinancialAnalysisEngine:
    """Evaluate versioned analytical definitions without mutating accounting truth."""

    def run(self, request: FinancialAnalysisRequest) -> FinancialAnalysisResult:
        request.source.assert_publishable(historical_replay=request.historical_replay)
        if not request.definition_set.executable:
            raise InvalidAnalysisDefinitionSetError("analysis definition set must be ACTIVE")
        if not request.definition_set.is_effective_on(request.source.as_of):
            raise InvalidAnalysisDefinitionSetError(
                "analysis definition set is not effective on source as_of date"
            )

        input_map = {item.key: item for item in request.inputs}
        definitions = {item.code: item for item in request.definition_set.indicator_definitions}
        resolved: dict[str, FinancialIndicatorValue] = {}
        traces: dict[tuple[AnalysisMetricKind, str], CalculationTrace] = {}

        def evaluate_indicator(code: str) -> FinancialIndicatorValue:
            if code in resolved:
                return resolved[code]
            definition = definitions[code]
            value, trace = self._evaluate_indicator(
                definition,
                source=request.source,
                input_map=input_map,
                evaluate_indicator=evaluate_indicator,
            )
            resolved[code] = value
            traces[(AnalysisMetricKind.INDICATOR, code)] = trace
            return value

        for code in sorted(definitions):
            evaluate_indicator(code)

        ratio_values: list[FinancialRatioValue] = []
        for definition in sorted(
            request.definition_set.ratio_definitions,
            key=lambda item: item.code,
        ):
            value, trace = self._evaluate_ratio(
                definition,
                source=request.source,
                input_map=input_map,
                indicators=resolved,
            )
            ratio_values.append(value)
            traces[(AnalysisMetricKind.RATIO, definition.code)] = trace

        indicator_values = tuple(resolved[code] for code in sorted(resolved))
        frozen_ratios = tuple(ratio_values)
        frozen_traces = tuple(
            traces[key]
            for key in sorted(
                traces,
                key=lambda item: (item[0].value, item[1]),
            )
        )
        checksum = self._result_checksum(
            request=request,
            indicators=indicator_values,
            ratios=frozen_ratios,
            traces=frozen_traces,
        )
        return FinancialAnalysisResult(
            source=request.source,
            definition_set_id=request.definition_set.definition_set_id,
            definition_set_version=request.definition_set.version,
            definition_set_checksum=request.definition_set.checksum,
            indicator_values=indicator_values,
            ratio_values=frozen_ratios,
            traces=frozen_traces,
            checksum=checksum,
        )

    def _evaluate_indicator(
        self,
        definition: FinancialIndicatorDefinition,
        *,
        source: FinancialAnalysisSource,
        input_map: dict[str, AnalysisInputValue],
        evaluate_indicator: Callable[[str], FinancialIndicatorValue],
    ) -> tuple[FinancialIndicatorValue, CalculationTrace]:
        if not definition.executable or not definition.is_effective_on(source.as_of):
            value = FinancialIndicatorValue(
                definition_id=definition.definition_id,
                definition_version=definition.version,
                code=definition.code,
                value=None,
                unit=definition.unit,
                status=IndicatorValueStatus.NOT_APPLICABLE,
                source_refs=(source.source_ref,),
                dependencies=(),
                message="indicator definition is not executable/effective",
            )
            return value, self._trace_for_indicator(definition, value)

        observations: list[DependencyObservation] = []
        source_refs = {source.source_ref}
        for dependency in definition.dependencies:
            if dependency.dependency_type is IndicatorDependencyType.INDICATOR:
                indicator_value = evaluate_indicator(dependency.dependency_id)
                observation = DependencyObservation(
                    ref=dependency.dependency_id,
                    status=indicator_value.status,
                    value=indicator_value.value,
                )
                source_refs.update(indicator_value.source_refs)
            else:
                source_input = input_map.get(dependency.dependency_id)
                if source_input is None:
                    observation = DependencyObservation(
                        ref=dependency.dependency_id,
                        status=(
                            IndicatorValueStatus.INDETERMINATE
                            if dependency.required
                            else IndicatorValueStatus.NOT_APPLICABLE
                        ),
                        value=None,
                    )
                else:
                    observation = DependencyObservation(
                        ref=dependency.dependency_id,
                        status=IndicatorValueStatus.CALCULATED,
                        value=source_input.value,
                    )
                    source_refs.add(source_input.source_ref)
            observations.append(observation)

        required_missing = any(
            dependency.required
            and observation.status
            in {
                IndicatorValueStatus.INDETERMINATE,
                IndicatorValueStatus.NOT_APPLICABLE,
            }
            for dependency, observation in zip(
                definition.dependencies,
                observations,
                strict=True,
            )
        )
        message: str | None
        if required_missing:
            status = IndicatorValueStatus.INDETERMINATE
            result_value = None
            message = "required analytical dependency is missing"
        else:
            status, result_value, message = self._evaluate_formula(
                definition.formula,
                tuple(observations),
            )

        value = FinancialIndicatorValue(
            definition_id=definition.definition_id,
            definition_version=definition.version,
            code=definition.code,
            value=result_value,
            unit=definition.unit,
            status=status,
            source_refs=tuple(sorted(source_refs)),
            dependencies=tuple(observations),
            message=message,
        )
        return value, self._trace_for_indicator(definition, value)

    @staticmethod
    def _trace_for_indicator(
        definition: FinancialIndicatorDefinition,
        value: FinancialIndicatorValue,
    ) -> CalculationTrace:
        return CalculationTrace(
            metric_kind=AnalysisMetricKind.INDICATOR,
            metric_code=definition.code,
            definition_id=definition.definition_id,
            definition_version=definition.version,
            operation=definition.formula.operation.value,
            dependencies=value.dependencies,
            status=value.status,
            result_value=value.value,
        )

    def _evaluate_formula(
        self,
        formula: AnalysisFormula,
        observations: tuple[DependencyObservation, ...],
    ) -> tuple[IndicatorValueStatus, Decimal | None, str | None]:
        by_ref = {item.ref: item for item in observations}
        ordered = tuple(by_ref[ref] for ref in formula.operands)

        if formula.operation in {
            AnalysisFormulaOperation.COALESCE,
            AnalysisFormulaOperation.IF_DEFINED,
        }:
            for observation in ordered:
                if observation.status is IndicatorValueStatus.CALCULATED:
                    return (
                        IndicatorValueStatus.CALCULATED,
                        observation.value,
                        None,
                    )
            if any(
                observation.status is IndicatorValueStatus.INDETERMINATE for observation in ordered
            ):
                return (
                    IndicatorValueStatus.INDETERMINATE,
                    None,
                    ("no defined operand; at least one dependency is indeterminate"),
                )
            return (
                IndicatorValueStatus.UNDEFINED,
                None,
                "no operand is mathematically defined",
            )

        propagated = self._propagated_status(ordered)
        if propagated is not None:
            return (
                propagated,
                None,
                "dependency status prevents calculation",
            )

        values = tuple(item.value for item in ordered)
        if any(value is None for value in values):
            return (
                IndicatorValueStatus.INDETERMINATE,
                None,
                "formula operand is unavailable",
            )
        resolved = tuple(value for value in values if value is not None)

        try:
            if formula.operation in {
                AnalysisFormulaOperation.ADD,
                AnalysisFormulaOperation.SUM,
            }:
                result = sum(resolved, _ZERO)
            elif formula.operation is AnalysisFormulaOperation.SUBTRACT:
                result = resolved[0] - resolved[1]
            elif formula.operation is AnalysisFormulaOperation.MULTIPLY:
                result = resolved[0] * resolved[1]
            elif formula.operation is AnalysisFormulaOperation.DIVIDE:
                if resolved[1].is_zero():
                    return (
                        IndicatorValueStatus.UNDEFINED,
                        None,
                        "division denominator is zero",
                    )
                result = resolved[0] / resolved[1]
            elif formula.operation is AnalysisFormulaOperation.NEGATE:
                result = -resolved[0]
            elif formula.operation is AnalysisFormulaOperation.ABS:
                result = abs(resolved[0])
            elif formula.operation is AnalysisFormulaOperation.MIN:
                result = min(resolved)
            elif formula.operation is AnalysisFormulaOperation.MAX:
                result = max(resolved)
            else:
                raise UnsupportedAnalysisOperationError(
                    f"unsupported analysis operation {formula.operation.value!r}"
                )
        except (ArithmeticError, IndexError) as exc:
            return (
                IndicatorValueStatus.ERROR,
                None,
                f"analytical calculation failed: {exc}",
            )

        if not result.is_finite():
            return (
                IndicatorValueStatus.ERROR,
                None,
                "analytical calculation produced non-finite value",
            )
        return IndicatorValueStatus.CALCULATED, result, None

    @staticmethod
    def _propagated_status(
        observations: tuple[DependencyObservation, ...],
    ) -> IndicatorValueStatus | None:
        statuses = {item.status for item in observations}
        if IndicatorValueStatus.ERROR in statuses:
            return IndicatorValueStatus.ERROR
        if IndicatorValueStatus.INDETERMINATE in statuses:
            return IndicatorValueStatus.INDETERMINATE
        if IndicatorValueStatus.UNDEFINED in statuses:
            return IndicatorValueStatus.UNDEFINED
        if IndicatorValueStatus.NOT_APPLICABLE in statuses:
            return IndicatorValueStatus.INDETERMINATE
        return None

    def _evaluate_ratio(
        self,
        definition: FinancialRatioDefinition,
        *,
        source: FinancialAnalysisSource,
        input_map: dict[str, AnalysisInputValue],
        indicators: dict[str, FinancialIndicatorValue],
    ) -> tuple[FinancialRatioValue, CalculationTrace]:
        if not definition.executable or not definition.is_effective_on(source.as_of):
            value = FinancialRatioValue(
                definition_id=definition.definition_id,
                definition_version=definition.version,
                code=definition.code,
                value=None,
                unit=definition.unit,
                status=IndicatorValueStatus.NOT_APPLICABLE,
                numerator_value=None,
                denominator_value=None,
                source_refs=(source.source_ref,),
                message="ratio definition is not executable/effective",
            )
            return value, self._trace_for_ratio(definition, value)

        numerator = self._resolve_ratio_ref(
            definition.numerator_ref,
            input_map,
            indicators,
        )
        denominator = self._resolve_ratio_ref(
            definition.denominator_ref,
            input_map,
            indicators,
        )
        source_refs = {source.source_ref}
        for ref in (
            definition.numerator_ref,
            definition.denominator_ref,
        ):
            source_input = input_map.get(ref)
            if source_input is not None:
                source_refs.add(source_input.source_ref)
            indicator = indicators.get(ref)
            if indicator is not None:
                source_refs.update(indicator.source_refs)

        if numerator.status is not IndicatorValueStatus.CALCULATED:
            status = self._ratio_dependency_status(numerator.status)
            result = None
            message = f"ratio numerator {definition.numerator_ref!r} is not calculated"
        elif denominator.status is not IndicatorValueStatus.CALCULATED:
            status = self._ratio_dependency_status(denominator.status)
            result = None
            message = f"ratio denominator {definition.denominator_ref!r} is not calculated"
        elif denominator.value is None or numerator.value is None:
            status = IndicatorValueStatus.INDETERMINATE
            result = None
            message = "ratio dependency value is unavailable"
        elif denominator.value.is_zero():
            status, result, message = self._zero_denominator(definition)
        else:
            result = numerator.value / denominator.value * definition.scale
            if not result.is_finite():
                status = IndicatorValueStatus.ERROR
                result = None
                message = "ratio produced non-finite value"
            else:
                status = IndicatorValueStatus.CALCULATED
                message = None

        value = FinancialRatioValue(
            definition_id=definition.definition_id,
            definition_version=definition.version,
            code=definition.code,
            value=result,
            unit=definition.unit,
            status=status,
            numerator_value=numerator.value,
            denominator_value=denominator.value,
            source_refs=tuple(sorted(source_refs)),
            message=message,
        )
        return value, self._trace_for_ratio(
            definition,
            value,
            dependencies=(numerator, denominator),
        )

    @staticmethod
    def _resolve_ratio_ref(
        ref: str,
        input_map: dict[str, AnalysisInputValue],
        indicators: dict[str, FinancialIndicatorValue],
    ) -> DependencyObservation:
        if ref in indicators:
            indicator = indicators[ref]
            return DependencyObservation(
                ref=ref,
                status=indicator.status,
                value=indicator.value,
            )
        source_input = input_map.get(ref)
        if source_input is not None:
            return DependencyObservation(
                ref=ref,
                status=IndicatorValueStatus.CALCULATED,
                value=source_input.value,
            )
        return DependencyObservation(
            ref=ref,
            status=IndicatorValueStatus.INDETERMINATE,
            value=None,
        )

    @staticmethod
    def _ratio_dependency_status(
        status: IndicatorValueStatus,
    ) -> IndicatorValueStatus:
        if status is IndicatorValueStatus.UNDEFINED:
            return IndicatorValueStatus.UNDEFINED
        if status is IndicatorValueStatus.ERROR:
            return IndicatorValueStatus.ERROR
        return IndicatorValueStatus.INDETERMINATE

    @staticmethod
    def _zero_denominator(
        definition: FinancialRatioDefinition,
    ) -> tuple[IndicatorValueStatus, Decimal | None, str]:
        if definition.zero_denominator_policy is ZeroDenominatorPolicy.NOT_APPLICABLE:
            return (
                IndicatorValueStatus.NOT_APPLICABLE,
                None,
                "ratio denominator is zero",
            )
        if definition.zero_denominator_policy is ZeroDenominatorPolicy.ZERO_IF_CONFIGURED:
            return (
                IndicatorValueStatus.CALCULATED,
                _ZERO,
                "zero denominator policy returned zero",
            )
        if definition.zero_denominator_policy is ZeroDenominatorPolicy.ERROR:
            return (
                IndicatorValueStatus.ERROR,
                None,
                "ratio denominator is zero",
            )
        return (
            IndicatorValueStatus.UNDEFINED,
            None,
            "ratio denominator is zero",
        )

    @staticmethod
    def _trace_for_ratio(
        definition: FinancialRatioDefinition,
        value: FinancialRatioValue,
        *,
        dependencies: (tuple[DependencyObservation, DependencyObservation] | None) = None,
    ) -> CalculationTrace:
        observations = dependencies or (
            DependencyObservation(
                ref=definition.numerator_ref,
                status=IndicatorValueStatus.NOT_APPLICABLE,
                value=None,
            ),
            DependencyObservation(
                ref=definition.denominator_ref,
                status=IndicatorValueStatus.NOT_APPLICABLE,
                value=None,
            ),
        )
        return CalculationTrace(
            metric_kind=AnalysisMetricKind.RATIO,
            metric_code=definition.code,
            definition_id=definition.definition_id,
            definition_version=definition.version,
            operation="RATIO_DIVIDE_SCALE",
            dependencies=observations,
            status=value.status,
            result_value=value.value,
        )

    @staticmethod
    def _result_checksum(
        *,
        request: FinancialAnalysisRequest,
        indicators: tuple[FinancialIndicatorValue, ...],
        ratios: tuple[FinancialRatioValue, ...],
        traces: tuple[CalculationTrace, ...],
    ) -> str:
        payload = {
            "source_checksum": request.source.checksum,
            "source_ref": request.source.source_ref,
            "entity_id": str(request.source.accounting_entity_id),
            "period_id": request.source.period_id,
            "as_of": request.source.as_of.isoformat(),
            "definition_set_checksum": request.definition_set.checksum,
            "indicators": [value.checksum for value in indicators],
            "ratios": [value.checksum for value in ratios],
            "traces": [trace.checksum for trace in traces],
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


__all__ = [
    "FinancialAnalysisEngine",
    "FinancialAnalysisRequest",
    "FinancialAnalysisResult",
]
