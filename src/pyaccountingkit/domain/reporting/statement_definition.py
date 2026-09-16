"""Versioned definitions for financial statements."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.domain.reporting.errors import (
    FormulaCycleError,
    InvalidStatementDefinitionError,
)
from pyaccountingkit.domain.reporting.statement_line import (
    StatementLineDefinition,
    StatementLineType,
)


class FinancialStatementType(StrEnum):
    BALANCE_SHEET = "BALANCE_SHEET"
    INCOME_STATEMENT = "INCOME_STATEMENT"
    CASH_FLOW_STATEMENT = "CASH_FLOW_STATEMENT"
    CHANGES_IN_EQUITY = "CHANGES_IN_EQUITY"
    NOTES_INDEX = "NOTES_INDEX"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class FinancialStatementDefinition:
    """Immutable, effective-dated structure of one financial statement."""

    definition_id: str
    code: str
    statement_type: FinancialStatementType
    version: str
    effective_from: date
    lines: tuple[StatementLineDefinition, ...]
    effective_to: date | None = None
    standard_scope: str | None = None
    reporting_profile: str | None = None

    def __post_init__(self) -> None:
        if not self.definition_id.strip():
            raise InvalidStatementDefinitionError("statement definition id must not be empty")
        if not self.code.strip():
            raise InvalidStatementDefinitionError("statement definition code must not be empty")
        if not self.version.strip():
            raise InvalidStatementDefinitionError("statement definition version must not be empty")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise InvalidStatementDefinitionError(
                "statement definition effective_to cannot precede effective_from"
            )
        if not self.lines:
            raise InvalidStatementDefinitionError("statement definition requires at least one line")

        ids = [line.line_id for line in self.lines]
        codes = [line.code for line in self.lines]
        if len(ids) != len(set(ids)):
            raise InvalidStatementDefinitionError("statement line ids must be unique")
        if len(codes) != len(set(codes)):
            raise InvalidStatementDefinitionError("statement line codes must be unique")
        control_roles = [line.control_role for line in self.lines if line.control_role is not None]
        if len(control_roles) != len(set(control_roles)):
            raise InvalidStatementDefinitionError("statement control roles must be unique")

        known_ids = set(ids)
        known_codes = set(codes)
        for line in self.lines:
            if line.parent_line_id is not None and line.parent_line_id not in known_ids:
                raise InvalidStatementDefinitionError(
                    f"line {line.code!r} references unknown parent {line.parent_line_id!r}"
                )
            if line.formula is not None:
                missing = sorted(set(line.formula.dependencies) - known_codes)
                if missing:
                    raise InvalidStatementDefinitionError(
                        f"line {line.code!r} formula references unknown lines {missing!r}"
                    )

        self._assert_dependency_graph_acyclic()

    def effective_on(self, value: date) -> bool:
        if value < self.effective_from:
            return False
        return self.effective_to is None or value <= self.effective_to

    def line_by_code(self, code: str) -> StatementLineDefinition:
        for line in self.lines:
            if line.code == code:
                return line
        raise KeyError(code)

    def children_of(self, line_id: str) -> tuple[StatementLineDefinition, ...]:
        return tuple(
            sorted(
                (line for line in self.lines if line.parent_line_id == line_id),
                key=lambda line: (line.order, line.code),
            )
        )

    @property
    def ordered_lines(self) -> tuple[StatementLineDefinition, ...]:
        return tuple(sorted(self.lines, key=lambda line: (line.order, line.code)))

    @property
    def checksum(self) -> str:
        payload = {
            "definition_id": self.definition_id,
            "code": self.code,
            "statement_type": self.statement_type.value,
            "version": self.version,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "standard_scope": self.standard_scope,
            "reporting_profile": self.reporting_profile,
            "lines": [
                {
                    "line_id": line.line_id,
                    "code": line.code,
                    "label": line.label,
                    "line_type": line.line_type.value,
                    "parent_line_id": line.parent_line_id,
                    "order": line.order,
                    "sign_convention": line.sign_convention.value,
                    "visibility": line.visibility.value,
                    "drilldown_policy": line.drilldown_policy.value,
                    "control_role": line.control_role.value if line.control_role else None,
                    "formula": (
                        {
                            "operation": line.formula.operation.value,
                            "operands": list(line.formula.operands),
                            "version": line.formula.version,
                        }
                        if line.formula
                        else None
                    ),
                }
                for line in self.ordered_lines
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _dependency_graph(self) -> dict[str, tuple[str, ...]]:
        by_id = {line.line_id: line for line in self.lines}
        graph: dict[str, tuple[str, ...]] = {}
        for line in self.lines:
            dependencies: list[str] = []
            if line.line_type in {StatementLineType.SUBTOTAL, StatementLineType.TOTAL}:
                dependencies.extend(child.code for child in self.children_of(line.line_id))
            if line.formula is not None:
                dependencies.extend(line.formula.dependencies)
            graph[line.code] = tuple(dependencies)
        # Parent cycles can exist even when subtotal edges are absent.
        # Validate the hierarchy itself as well as formula dependencies.
        for line in self.lines:
            seen: set[str] = set()
            current = line
            while current.parent_line_id is not None:
                if current.line_id in seen:
                    raise FormulaCycleError(
                        f"statement hierarchy cycle detected at line {current.code!r}"
                    )
                seen.add(current.line_id)
                current = by_id[current.parent_line_id]
        return graph

    def _assert_dependency_graph_acyclic(self) -> None:
        graph = self._dependency_graph()
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(node: str) -> None:
            if node in permanent:
                return
            if node in temporary:
                raise FormulaCycleError(f"statement formula cycle detected at line {node!r}")
            temporary.add(node)
            for dependency in graph[node]:
                visit(dependency)
            temporary.remove(node)
            permanent.add(node)

        for code in sorted(graph):
            visit(code)


__all__ = ["FinancialStatementDefinition", "FinancialStatementType"]
