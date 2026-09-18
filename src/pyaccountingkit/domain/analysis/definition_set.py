"""Versioned collection of financial-analysis definitions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date

from pyaccountingkit.domain.analysis.errors import (
    IndicatorDependencyCycleError,
    InvalidAnalysisDefinitionSetError,
)
from pyaccountingkit.domain.analysis.indicators import (
    DefinitionStatus,
    FinancialIndicatorDefinition,
    IndicatorDependencyType,
)
from pyaccountingkit.domain.analysis.ratios import FinancialRatioDefinition


@dataclass(frozen=True, slots=True)
class AnalysisDefinitionSet:
    definition_set_id: str
    version: str
    indicator_definitions: tuple[FinancialIndicatorDefinition, ...]
    ratio_definitions: tuple[FinancialRatioDefinition, ...] = ()
    status: DefinitionStatus = DefinitionStatus.DRAFT
    effective_from: date | None = None
    effective_to: date | None = None
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.definition_set_id.strip() or not self.version.strip():
            raise InvalidAnalysisDefinitionSetError(
                "definition set id and version must not be empty"
            )
        if self.effective_to is not None and self.effective_from is None:
            raise InvalidAnalysisDefinitionSetError(
                "effective_to requires effective_from on an analysis definition set"
            )
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise InvalidAnalysisDefinitionSetError("definition-set dates are inverted")

        indicator_ids = [item.definition_id for item in self.indicator_definitions]
        indicator_codes = [item.code for item in self.indicator_definitions]
        ratio_ids = [item.definition_id for item in self.ratio_definitions]
        ratio_codes = [item.code for item in self.ratio_definitions]
        if len(indicator_ids) != len(set(indicator_ids)):
            raise InvalidAnalysisDefinitionSetError("indicator definition ids must be unique")
        if len(ratio_ids) != len(set(ratio_ids)):
            raise InvalidAnalysisDefinitionSetError("ratio definition ids must be unique")
        all_codes = indicator_codes + ratio_codes
        if len(all_codes) != len(set(all_codes)):
            raise InvalidAnalysisDefinitionSetError("analysis metric codes must be unique")

        by_code = {item.code: item for item in self.indicator_definitions}
        graph: dict[str, tuple[str, ...]] = {}
        for definition in self.indicator_definitions:
            indicator_dependencies = tuple(
                dependency.dependency_id
                for dependency in definition.dependencies
                if dependency.dependency_type is IndicatorDependencyType.INDICATOR
            )
            missing = sorted(set(indicator_dependencies) - set(by_code))
            if missing:
                raise InvalidAnalysisDefinitionSetError(
                    f"indicator {definition.code!r} references missing indicators: "
                    + ", ".join(missing)
                )
            graph[definition.code] = indicator_dependencies

        self._assert_acyclic(graph)
        object.__setattr__(self, "checksum", self._compute_checksum())

    @staticmethod
    def _assert_acyclic(graph: dict[str, tuple[str, ...]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str, path: tuple[str, ...]) -> None:
            if node in visiting:
                cycle = " -> ".join((*path, node))
                raise IndicatorDependencyCycleError(f"analysis dependency cycle: {cycle}")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph.get(node, ()):
                visit(dependency, (*path, node))
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node, ())

    def _compute_checksum(self) -> str:
        payload = {
            "definition_set_id": self.definition_set_id,
            "version": self.version,
            "status": self.status.value,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "indicators": [
                {
                    "id": item.definition_id,
                    "code": item.code,
                    "version": item.version,
                    "category": item.category.value,
                    "unit": item.unit.value,
                    "status": item.status.value,
                    "operation": item.formula.operation.value,
                    "formula_version": item.formula.version,
                    "operands": list(item.formula.operands),
                    "dependencies": [
                        {
                            "type": dependency.dependency_type.value,
                            "id": dependency.dependency_id,
                            "required": dependency.required,
                        }
                        for dependency in item.dependencies
                    ],
                }
                for item in self.indicator_definitions
            ],
            "ratios": [
                {
                    "id": item.definition_id,
                    "code": item.code,
                    "version": item.version,
                    "category": item.category.value,
                    "numerator": item.numerator_ref,
                    "denominator": item.denominator_ref,
                    "scale": str(item.scale),
                    "unit": item.unit.value,
                    "status": item.status.value,
                    "zero_denominator_policy": item.zero_denominator_policy.value,
                    "day_count_policy": (
                        item.day_count_policy.value if item.day_count_policy else None
                    ),
                }
                for item in self.ratio_definitions
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def is_effective_on(self, on_date: date) -> bool:
        if self.effective_from is not None and on_date < self.effective_from:
            return False
        if self.effective_to is not None and on_date > self.effective_to:
            return False
        return True

    @property
    def executable(self) -> bool:
        return self.status is DefinitionStatus.ACTIVE


__all__ = ["AnalysisDefinitionSet"]
