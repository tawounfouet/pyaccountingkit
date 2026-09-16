"""Deterministic, deliberately small formula DSL for financial statements."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.errors import InvalidStatementDefinitionError


class FormulaOperation(StrEnum):
    """Operations allowed by the statement formula DSL."""

    ADD = "ADD"
    SUBTRACT = "SUBTRACT"
    SUM = "SUM"
    NEGATE = "NEGATE"
    ABS = "ABS"
    MIN = "MIN"
    MAX = "MAX"


@dataclass(frozen=True, slots=True)
class StatementFormula:
    """Pure expression over other statement-line codes.

    The DSL is intentionally data-only: formulas cannot execute arbitrary
    Python, call external services or mutate accounting state.
    """

    operation: FormulaOperation
    operands: tuple[str, ...]
    version: str = "1"

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise InvalidStatementDefinitionError("formula version must not be empty")
        if not self.operands:
            raise InvalidStatementDefinitionError("formula requires at least one operand")
        if any(not operand.strip() for operand in self.operands):
            raise InvalidStatementDefinitionError("formula operands must be non-empty line codes")
        if self.operation in {FormulaOperation.NEGATE, FormulaOperation.ABS}:
            if len(self.operands) != 1:
                raise InvalidStatementDefinitionError(
                    f"{self.operation.value} requires exactly one operand"
                )
        elif self.operation is FormulaOperation.SUBTRACT:
            if len(self.operands) != 2:
                raise InvalidStatementDefinitionError("SUBTRACT requires exactly two operands")
        elif self.operation is FormulaOperation.ADD and len(self.operands) < 2:
            raise InvalidStatementDefinitionError("ADD requires at least two operands")

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self.operands

    def evaluate(self, values: Mapping[str, Money], *, currency: Currency) -> Money:
        """Evaluate against already-resolved line values."""
        try:
            resolved = tuple(values[operand] for operand in self.operands)
        except KeyError as exc:
            missing = str(exc.args[0])
            raise InvalidStatementDefinitionError(
                f"formula dependency {missing!r} has no resolved value"
            ) from exc

        if self.operation in {FormulaOperation.ADD, FormulaOperation.SUM}:
            result = Money.zero(currency)
            for value in resolved:
                result = result + value
            return result
        if self.operation is FormulaOperation.SUBTRACT:
            return resolved[0] - resolved[1]
        if self.operation is FormulaOperation.NEGATE:
            return -resolved[0]
        if self.operation is FormulaOperation.ABS:
            return abs(resolved[0])
        if self.operation is FormulaOperation.MIN:
            result = resolved[0]
            for value in resolved[1:]:
                if value.compare(result) < 0:
                    result = value
            return result
        if self.operation is FormulaOperation.MAX:
            result = resolved[0]
            for value in resolved[1:]:
                if value.compare(result) > 0:
                    result = value
            return result
        raise InvalidStatementDefinitionError(f"unsupported formula operation {self.operation!r}")


__all__ = ["FormulaOperation", "StatementFormula"]
