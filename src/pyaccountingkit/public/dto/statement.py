"""Immutable public DTOs for financial statements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.engine import FinancialStatementResult


@dataclass(frozen=True, slots=True)
class FinancialStatementLineDTO:
    code: str
    label: str
    amount: Money
    comparative_amount: Money | None
    visible: bool


@dataclass(frozen=True, slots=True)
class FinancialStatementDTO:
    accounting_entity_id: str
    statement_type: str
    source_period_id: str
    source_checksum: str
    as_of: date
    checksum: str
    lines: tuple[FinancialStatementLineDTO, ...]

    @classmethod
    def from_domain(cls, statement: FinancialStatementResult) -> FinancialStatementDTO:
        return cls(
            accounting_entity_id=str(statement.accounting_entity_id),
            statement_type=statement.statement_type.value,
            source_period_id=statement.source_period_id,
            source_checksum=statement.source_checksum,
            as_of=statement.as_of,
            checksum=statement.checksum,
            lines=tuple(
                FinancialStatementLineDTO(
                    code=line.code,
                    label=line.label,
                    amount=line.amount,
                    comparative_amount=line.comparative_amount,
                    visible=line.visible,
                )
                for line in statement.lines
            ),
        )


__all__ = ["FinancialStatementDTO", "FinancialStatementLineDTO"]
