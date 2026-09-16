"""Financial-statement line definitions and presentation conventions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.errors import InvalidStatementDefinitionError
from pyaccountingkit.domain.reporting.formula import StatementFormula


class StatementLineType(StrEnum):
    DETAIL = "DETAIL"
    SUBTOTAL = "SUBTOTAL"
    TOTAL = "TOTAL"
    FORMULA = "FORMULA"
    HEADER = "HEADER"
    SPACER = "SPACER"
    MEMO = "MEMO"
    DISCLOSURE = "DISCLOSURE"


class StatementSignConvention(StrEnum):
    NATURAL = "NATURAL"
    DEBIT_POSITIVE = "DEBIT_POSITIVE"
    CREDIT_POSITIVE = "CREDIT_POSITIVE"
    ABSOLUTE = "ABSOLUTE"


class StatementVisibility(StrEnum):
    ALWAYS = "ALWAYS"
    NON_ZERO = "NON_ZERO"
    NEVER = "NEVER"


class DrilldownPolicy(StrEnum):
    ALLOWED = "ALLOWED"
    DISABLED = "DISABLED"


class StatementControlRole(StrEnum):
    """Optional semantic anchors used by structural statement controls."""

    ASSETS_TOTAL = "ASSETS_TOTAL"
    LIABILITIES_EQUITY_TOTAL = "LIABILITIES_EQUITY_TOTAL"
    NET_INCOME = "NET_INCOME"
    CASH_OPENING = "CASH_OPENING"
    CASH_NET_CHANGE = "CASH_NET_CHANGE"
    CASH_CLOSING = "CASH_CLOSING"


@dataclass(frozen=True, slots=True)
class StatementLineDefinition:
    """One immutable line inside a versioned financial-statement definition."""

    line_id: str
    code: str
    label: str
    line_type: StatementLineType
    order: int
    parent_line_id: str | None = None
    sign_convention: StatementSignConvention = StatementSignConvention.NATURAL
    formula: StatementFormula | None = None
    visibility: StatementVisibility = StatementVisibility.ALWAYS
    drilldown_policy: DrilldownPolicy = DrilldownPolicy.ALLOWED
    control_role: StatementControlRole | None = None

    def __post_init__(self) -> None:
        if not self.line_id.strip():
            raise InvalidStatementDefinitionError("statement line id must not be empty")
        if not self.code.strip():
            raise InvalidStatementDefinitionError("statement line code must not be empty")
        if not self.label.strip() and self.line_type is not StatementLineType.SPACER:
            raise InvalidStatementDefinitionError(f"statement line {self.code!r} must have a label")
        if self.order < 0:
            raise InvalidStatementDefinitionError(
                f"statement line {self.code!r} order must be >= 0"
            )
        if self.line_type is StatementLineType.FORMULA and self.formula is None:
            raise InvalidStatementDefinitionError(
                f"formula line {self.code!r} requires a StatementFormula"
            )
        if self.line_type is not StatementLineType.FORMULA and self.formula is not None:
            raise InvalidStatementDefinitionError(
                f"only FORMULA lines may carry a StatementFormula ({self.code!r})"
            )
        if self.line_type in {StatementLineType.HEADER, StatementLineType.SPACER}:
            if self.control_role is not None:
                raise InvalidStatementDefinitionError(
                    f"presentation line {self.code!r} cannot be a control anchor"
                )

    def present(self, value: Money) -> Money:
        """Apply only presentation sign rules; never mutate ledger semantics."""
        if self.sign_convention in {
            StatementSignConvention.NATURAL,
            StatementSignConvention.DEBIT_POSITIVE,
        }:
            return value
        if self.sign_convention is StatementSignConvention.CREDIT_POSITIVE:
            return -value
        if self.sign_convention is StatementSignConvention.ABSOLUTE:
            return abs(value)
        raise InvalidStatementDefinitionError(
            f"unsupported sign convention {self.sign_convention!r}"
        )

    @property
    def has_account_value(self) -> bool:
        return self.line_type is StatementLineType.DETAIL


__all__ = [
    "DrilldownPolicy",
    "StatementControlRole",
    "StatementLineDefinition",
    "StatementLineType",
    "StatementSignConvention",
    "StatementVisibility",
]
