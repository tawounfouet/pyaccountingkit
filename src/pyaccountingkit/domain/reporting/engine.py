"""Pure financial-statement projection engine built from trial-balance snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.errors import (
    InvalidStatementDefinitionError,
    NonExecutableStatementMappingError,
    StatementControlError,
    StatementMappingError,
    StatementSourceError,
)
from pyaccountingkit.domain.reporting.mappings import StatementMappingSet
from pyaccountingkit.domain.reporting.statement_definition import (
    FinancialStatementDefinition,
    FinancialStatementType,
)
from pyaccountingkit.domain.reporting.statement_line import (
    DrilldownPolicy,
    StatementControlRole,
    StatementLineDefinition,
    StatementLineType,
    StatementVisibility,
)
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance


class StatementControlStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class StatementDrilldownItem:
    account_code: str
    account_label: str
    source_balance: Money
    allocation: Decimal
    contribution: Money


@dataclass(frozen=True, slots=True)
class StatementLineValue:
    line_id: str
    code: str
    label: str
    line_type: StatementLineType
    amount: Money
    comparative_amount: Money | None
    visible: bool
    drilldown: tuple[StatementDrilldownItem, ...] = ()


@dataclass(frozen=True, slots=True)
class StatementControlResult:
    control_code: str
    status: StatementControlStatus
    difference: Money
    message: str


@dataclass(frozen=True, slots=True)
class FinancialStatementBuildRequest:
    accounting_entity_id: EntityId
    as_of: date
    reporting_source: TrialBalance
    statement_definition: FinancialStatementDefinition
    mapping_set: StatementMappingSet
    comparative_source: TrialBalance | None = None
    require_full_mapping: bool = True
    fail_on_control_error: bool = False


@dataclass(frozen=True, slots=True)
class FinancialStatementResult:
    accounting_entity_id: EntityId
    statement_type: FinancialStatementType
    statement_definition_id: str
    statement_definition_version: str
    statement_definition_checksum: str
    mapping_set_id: str
    mapping_set_version: str
    mapping_set_checksum: str
    source_period_id: str
    source_checksum: str
    source_snapshot: str
    as_of: date
    lines: tuple[StatementLineValue, ...]
    controls: tuple[StatementControlResult, ...]
    checksum: str

    def line(self, code: str) -> StatementLineValue:
        for line in self.lines:
            if line.code == code:
                return line
        raise KeyError(code)

    def drill_down(self, code: str) -> tuple[StatementDrilldownItem, ...]:
        return self.line(code).drilldown


class FinancialStatementEngine:
    """Build deterministic statement projections without mutating accounting data."""

    def build(self, request: FinancialStatementBuildRequest) -> FinancialStatementResult:
        self._validate_request(request)
        current_values, current_drilldown = self._project_source(
            request.reporting_source,
            request=request,
        )
        comparative_values: dict[str, Money] | None = None
        if request.comparative_source is not None:
            comparative_values, _ = self._project_source(
                request.comparative_source,
                request=request,
                require_full_mapping=request.require_full_mapping,
            )

        rendered_lines: list[StatementLineValue] = []
        for line in request.statement_definition.ordered_lines:
            amount = current_values[line.code]
            comparative = (
                comparative_values[line.code] if comparative_values is not None else None
            )
            visible = self._is_visible(line, amount, comparative)
            rendered_lines.append(
                StatementLineValue(
                    line_id=line.line_id,
                    code=line.code,
                    label=line.label,
                    line_type=line.line_type,
                    amount=amount,
                    comparative_amount=comparative,
                    visible=visible,
                    drilldown=(
                        current_drilldown.get(line.code, ())
                        if line.drilldown_policy is DrilldownPolicy.ALLOWED
                        else ()
                    ),
                )
            )

        controls = self._run_controls(request.statement_definition, current_values)
        if request.fail_on_control_error:
            failed = [
                control
                for control in controls
                if control.status is StatementControlStatus.FAIL
            ]
            if failed:
                codes = ", ".join(control.control_code for control in failed)
                raise StatementControlError(f"financial statement controls failed: {codes}")

        checksum = self._result_checksum(request, tuple(rendered_lines), controls)
        return FinancialStatementResult(
            accounting_entity_id=request.accounting_entity_id,
            statement_type=request.statement_definition.statement_type,
            statement_definition_id=request.statement_definition.definition_id,
            statement_definition_version=request.statement_definition.version,
            statement_definition_checksum=request.statement_definition.checksum,
            mapping_set_id=request.mapping_set.mapping_set_id,
            mapping_set_version=request.mapping_set.version,
            mapping_set_checksum=request.mapping_set.checksum,
            source_period_id=request.reporting_source.period_id,
            source_checksum=request.reporting_source.checksum,
            source_snapshot=request.reporting_source.snapshot.value,
            as_of=request.as_of,
            lines=tuple(rendered_lines),
            controls=controls,
            checksum=checksum,
        )

    def _validate_request(self, request: FinancialStatementBuildRequest) -> None:
        source_entity = request.reporting_source.accounting_entity_id
        if source_entity is None:
            raise StatementSourceError(
                "financial statement source must pin an accounting_entity_id"
            )
        require_same_entity(
            request.accounting_entity_id,
            source_entity,
            resource="financial statement reporting source",
        )
        require_same_entity(
            request.accounting_entity_id,
            request.mapping_set.accounting_entity_id,
            resource="statement mapping set",
        )
        if request.comparative_source is not None:
            comparative_entity = request.comparative_source.accounting_entity_id
            if comparative_entity is None:
                raise StatementSourceError(
                    "comparative reporting source must pin an accounting_entity_id"
                )
            require_same_entity(
                request.accounting_entity_id,
                comparative_entity,
                resource="comparative reporting source",
            )
        if (
            request.mapping_set.statement_definition_id
            != request.statement_definition.definition_id
        ):
            raise StatementMappingError(
                "statement mapping set targets a different statement definition"
            )
        if not request.statement_definition.effective_on(request.as_of):
            raise InvalidStatementDefinitionError(
                f"statement definition {request.statement_definition.code!r} is not effective "
                f"on {request.as_of.isoformat()}"
            )
        if not request.mapping_set.effective_on(request.as_of):
            raise NonExecutableStatementMappingError(
                f"statement mapping set {request.mapping_set.mapping_set_id!r} is not effective "
                f"on {request.as_of.isoformat()}"
            )
        if not request.mapping_set.is_executable:
            raise NonExecutableStatementMappingError(
                f"statement mapping set {request.mapping_set.mapping_set_id!r} is not executable"
            )

    def _project_source(
        self,
        source: TrialBalance,
        *,
        request: FinancialStatementBuildRequest,
        require_full_mapping: bool | None = None,
    ) -> tuple[dict[str, Money], dict[str, tuple[StatementDrilldownItem, ...]]]:
        require_mapping = (
            request.require_full_mapping
            if require_full_mapping is None
            else require_full_mapping
        )
        currency = source.currency
        definition = request.statement_definition
        line_by_code = {line.code: line for line in definition.lines}
        detail_values: dict[str, Money] = {
            line.code: Money.zero(currency)
            for line in definition.lines
            if line.line_type is StatementLineType.DETAIL
        }
        drilldown: dict[str, list[StatementDrilldownItem]] = {
            code: [] for code in detail_values
        }

        for source_line in source.lines:
            applicable = tuple(
                mapping
                for mapping in request.mapping_set.mappings
                if mapping.applies_to(source_line, as_of=request.as_of)
            )
            if not applicable:
                if require_mapping and not source_line.is_zero:
                    raise StatementMappingError(
                        f"non-zero account {source_line.account_code!r} has no executable "
                        "statement mapping"
                    )
                continue
            allocation_total = sum(
                (mapping.allocation for mapping in applicable),
                Decimal("0"),
            )
            if allocation_total != Decimal("1"):
                raise StatementMappingError(
                    f"applicable mappings for account {source_line.account_code!r} must "
                    f"allocate exactly 1, got {allocation_total}"
                )
            for mapping in applicable:
                try:
                    target = line_by_code[mapping.statement_line_code]
                except KeyError as exc:
                    raise StatementMappingError(
                        f"mapping {mapping.mapping_id!r} targets unknown statement line "
                        f"{mapping.statement_line_code!r}"
                    ) from exc
                if target.line_type is not StatementLineType.DETAIL:
                    raise StatementMappingError(
                        f"mapping {mapping.mapping_id!r} must target a DETAIL line, got "
                        f"{target.line_type.value}"
                    )
                contribution = source_line.balance * mapping.allocation
                detail_values[target.code] = detail_values[target.code] + contribution
                drilldown[target.code].append(
                    StatementDrilldownItem(
                        account_code=source_line.account_code,
                        account_label=source_line.label,
                        source_balance=source_line.balance,
                        allocation=mapping.allocation,
                        contribution=contribution,
                    )
                )

        resolved: dict[str, Money] = {}
        resolving: set[str] = set()

        def evaluate(code: str) -> Money:
            if code in resolved:
                return resolved[code]
            if code in resolving:
                raise InvalidStatementDefinitionError(
                    f"cyclic statement evaluation detected at line {code!r}"
                )
            resolving.add(code)
            line = line_by_code[code]
            if line.line_type is StatementLineType.DETAIL:
                raw = detail_values[code]
            elif line.line_type in {StatementLineType.SUBTOTAL, StatementLineType.TOTAL}:
                raw = Money.zero(currency)
                for child in definition.children_of(line.line_id):
                    raw = raw + evaluate(child.code)
            elif line.line_type is StatementLineType.FORMULA:
                if line.formula is None:
                    raise InvalidStatementDefinitionError(
                        f"formula line {line.code!r} has no formula"
                    )
                dependencies = {
                    dependency: evaluate(dependency)
                    for dependency in line.formula.dependencies
                }
                raw = line.formula.evaluate(dependencies, currency=currency)
            else:
                raw = Money.zero(currency)
            value = line.present(raw)
            resolving.remove(code)
            resolved[code] = value
            return value

        for line in definition.ordered_lines:
            evaluate(line.code)

        frozen_drilldown = {code: tuple(items) for code, items in drilldown.items()}
        return resolved, frozen_drilldown

    @staticmethod
    def _is_visible(
        line: StatementLineDefinition,
        current: Money,
        comparative: Money | None,
    ) -> bool:
        if line.visibility is StatementVisibility.NEVER:
            return False
        if line.visibility is StatementVisibility.ALWAYS:
            return True
        if not current.is_zero():
            return True
        return comparative is not None and not comparative.is_zero()

    @staticmethod
    def _control_anchor(
        definition: FinancialStatementDefinition,
        role: StatementControlRole,
    ) -> StatementLineDefinition | None:
        matches = [line for line in definition.lines if line.control_role is role]
        if len(matches) > 1:
            raise InvalidStatementDefinitionError(
                f"statement definition has multiple {role.value} control anchors"
            )
        return matches[0] if matches else None

    def _run_controls(
        self,
        definition: FinancialStatementDefinition,
        values: dict[str, Money],
    ) -> tuple[StatementControlResult, ...]:
        currency = next(iter(values.values())).currency
        controls: list[StatementControlResult] = []

        if definition.statement_type is FinancialStatementType.BALANCE_SHEET:
            assets = self._control_anchor(definition, StatementControlRole.ASSETS_TOTAL)
            liabilities = self._control_anchor(
                definition,
                StatementControlRole.LIABILITIES_EQUITY_TOTAL,
            )
            if assets is None or liabilities is None:
                controls.append(
                    StatementControlResult(
                        control_code="BALANCE_SHEET_EQUATION",
                        status=StatementControlStatus.NOT_APPLICABLE,
                        difference=Money.zero(currency),
                        message="balance-sheet control anchors are not fully defined",
                    )
                )
            else:
                difference = values[assets.code] - values[liabilities.code]
                controls.append(
                    StatementControlResult(
                        control_code="BALANCE_SHEET_EQUATION",
                        status=(
                            StatementControlStatus.PASS
                            if difference.is_zero()
                            else StatementControlStatus.FAIL
                        ),
                        difference=difference,
                        message="assets must equal liabilities plus equity",
                    )
                )

        if definition.statement_type is FinancialStatementType.CASH_FLOW_STATEMENT:
            opening = self._control_anchor(definition, StatementControlRole.CASH_OPENING)
            net_change = self._control_anchor(
                definition,
                StatementControlRole.CASH_NET_CHANGE,
            )
            closing = self._control_anchor(definition, StatementControlRole.CASH_CLOSING)
            if opening is None or net_change is None or closing is None:
                controls.append(
                    StatementControlResult(
                        control_code="CASH_FLOW_RECONCILIATION",
                        status=StatementControlStatus.NOT_APPLICABLE,
                        difference=Money.zero(currency),
                        message="cash-flow reconciliation anchors are not fully defined",
                    )
                )
            else:
                difference = values[opening.code] + values[net_change.code] - values[closing.code]
                controls.append(
                    StatementControlResult(
                        control_code="CASH_FLOW_RECONCILIATION",
                        status=(
                            StatementControlStatus.PASS
                            if difference.is_zero()
                            else StatementControlStatus.FAIL
                        ),
                        difference=difference,
                        message="opening cash plus net change must equal closing cash",
                    )
                )

        return tuple(controls)

    @staticmethod
    def _result_checksum(
        request: FinancialStatementBuildRequest,
        lines: tuple[StatementLineValue, ...],
        controls: tuple[StatementControlResult, ...],
    ) -> str:
        payload = {
            "accounting_entity_id": str(request.accounting_entity_id),
            "as_of": request.as_of.isoformat(),
            "source_checksum": request.reporting_source.checksum,
            "definition_checksum": request.statement_definition.checksum,
            "mapping_checksum": request.mapping_set.checksum,
            "lines": [
                {
                    "code": line.code,
                    "amount": str(line.amount.amount),
                    "currency": str(line.amount.currency.code),
                    "comparative": (
                        str(line.comparative_amount.amount)
                        if line.comparative_amount is not None
                        else None
                    ),
                    "visible": line.visible,
                    "drilldown": [
                        {
                            "account_code": item.account_code,
                            "allocation": str(item.allocation),
                            "contribution": str(item.contribution.amount),
                        }
                        for item in line.drilldown
                    ],
                }
                for line in lines
            ],
            "controls": [
                {
                    "control_code": control.control_code,
                    "status": control.status.value,
                    "difference": str(control.difference.amount),
                }
                for control in controls
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "FinancialStatementBuildRequest",
    "FinancialStatementEngine",
    "FinancialStatementResult",
    "StatementControlResult",
    "StatementControlStatus",
    "StatementDrilldownItem",
    "StatementLineValue",
]
