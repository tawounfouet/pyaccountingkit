"""Data-only deterministic formula DSL for financial analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.domain.analysis.errors import InvalidIndicatorDefinitionError


class AnalysisFormulaOperation(StrEnum):
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    SUM = "SUM"
    NEGATE = "NEGATE"
    ABS = "ABS"
    MIN = "MIN"
    MAX = "MAX"
    COALESCE = "COALESCE"
    IF_DEFINED = "IF_DEFINED"


@dataclass(frozen=True, slots=True)
class AnalysisFormula:
    """Pure expression over named analytical dependencies.

    Evaluation is intentionally delegated to the analysis engine so undefined
    mathematics and missing inputs can be represented as analytical statuses
    rather than exceptions.
    """

    operation: AnalysisFormulaOperation
    operands: tuple[str, ...]
    version: str = "1"

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise InvalidIndicatorDefinitionError("formula version must not be empty")
        if not self.operands or any(not operand.strip() for operand in self.operands):
            raise InvalidIndicatorDefinitionError(
                "formula operands must contain non-empty dependency references"
            )
        if self.operation in {AnalysisFormulaOperation.NEGATE, AnalysisFormulaOperation.ABS}:
            if len(self.operands) != 1:
                raise InvalidIndicatorDefinitionError(
                    f"{self.operation.value} requires exactly one operand"
                )
        elif self.operation in {
            AnalysisFormulaOperation.SUBTRACT,
            AnalysisFormulaOperation.MULTIPLY,
            AnalysisFormulaOperation.DIVIDE,
            AnalysisFormulaOperation.IF_DEFINED,
        }:
            if len(self.operands) != 2:
                raise InvalidIndicatorDefinitionError(
                    f"{self.operation.value} requires exactly two operands"
                )
        elif self.operation is AnalysisFormulaOperation.ADD and len(self.operands) < 2:
            raise InvalidIndicatorDefinitionError("ADD requires at least two operands")

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self.operands


__all__ = ["AnalysisFormula", "AnalysisFormulaOperation"]
