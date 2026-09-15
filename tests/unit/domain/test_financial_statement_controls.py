"""Additional LOT-16 controls and account-identity qualification."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.engine import (
    FinancialStatementBuildRequest,
    FinancialStatementEngine,
    StatementControlStatus,
)
from pyaccountingkit.domain.reporting.errors import (
    NonExecutableStatementMappingError,
    StatementControlError,
)
from pyaccountingkit.domain.reporting.mappings import (
    MappingProvenance,
    StatementAccountMapping,
    StatementMappingSet,
    StatementMappingSetStatus,
    StatementMappingStatus,
)
from pyaccountingkit.domain.reporting.statement_definition import (
    FinancialStatementDefinition,
    FinancialStatementType,
)
from pyaccountingkit.domain.reporting.statement_line import (
    StatementControlRole,
    StatementLineDefinition,
    StatementLineType,
    StatementSignConvention,
)
from pyaccountingkit.domain.reporting.trial_balance import (
    TrialBalance,
    TrialBalanceSnapshot,
)

ENTITY = EntityId("entity-reporting")
AS_OF = date(2026, 12, 31)


def _source() -> TrialBalance:
    return TrialBalance.build(
        "FY2026",
        TrialBalanceSnapshot.ADJUSTED,
        (
            AccountBalanceLine(
                account_id=AccountId("acc-cash"),
                account_code="512000",
                label="Cash",
                sum_debit=Money.from_str("100", EUR),
                sum_credit=Money.zero(EUR),
            ),
            AccountBalanceLine(
                account_id=AccountId("acc-equity"),
                account_code="101000",
                label="Equity",
                sum_debit=Money.zero(EUR),
                sum_credit=Money.from_str("100", EUR),
            ),
        ),
        accounting_entity_id=ENTITY,
    )


def _definition(*, include_unattached: bool = False) -> FinancialStatementDefinition:
    lines = [
        StatementLineDefinition(
            line_id="assets-total",
            code="ASSETS_TOTAL",
            label="Total assets",
            line_type=StatementLineType.TOTAL,
            order=20,
            control_role=StatementControlRole.ASSETS_TOTAL,
        ),
        StatementLineDefinition(
            line_id="cash",
            code="CASH",
            label="Cash",
            line_type=StatementLineType.DETAIL,
            order=10,
            parent_line_id="assets-total",
        ),
        StatementLineDefinition(
            line_id="le-total",
            code="LE_TOTAL",
            label="Liabilities and equity",
            line_type=StatementLineType.TOTAL,
            order=40,
            control_role=StatementControlRole.LIABILITIES_EQUITY_TOTAL,
        ),
        StatementLineDefinition(
            line_id="equity",
            code="EQUITY",
            label="Equity",
            line_type=StatementLineType.DETAIL,
            order=30,
            parent_line_id="le-total",
            sign_convention=StatementSignConvention.CREDIT_POSITIVE,
        ),
    ]
    if include_unattached:
        lines.append(
            StatementLineDefinition(
                line_id="unattached",
                code="UNATTACHED",
                label="Unattached presentation line",
                line_type=StatementLineType.DETAIL,
                order=50,
                sign_convention=StatementSignConvention.CREDIT_POSITIVE,
            )
        )
    return FinancialStatementDefinition(
        definition_id="def-bs-identity",
        code="BS-IDENTITY",
        statement_type=FinancialStatementType.BALANCE_SHEET,
        version="1",
        effective_from=date(2026, 1, 1),
        lines=tuple(lines),
    )


def _mapping(
    mapping_id: str,
    account_id: str,
    line_code: str,
) -> StatementAccountMapping:
    return StatementAccountMapping(
        mapping_id=mapping_id,
        company_account_id=account_id,
        statement_line_code=line_code,
        allocation=Decimal("1"),
        mapping_status=StatementMappingStatus.VALIDATED,
        provenance=MappingProvenance.MANUAL,
        effective_from=date(2026, 1, 1),
    )


def _mapping_set(
    *,
    equity_target: str = "EQUITY",
    effective_to: date | None = None,
) -> StatementMappingSet:
    return StatementMappingSet(
        mapping_set_id="map-bs-identity",
        accounting_entity_id=ENTITY,
        statement_definition_id="def-bs-identity",
        version="1",
        status=StatementMappingSetStatus.ACTIVE,
        mappings=(
            _mapping("m-cash", "acc-cash", "CASH"),
            _mapping("m-equity", "acc-equity", equity_target),
        ),
        effective_from=date(2026, 1, 1),
        effective_to=effective_to,
    )


def test_mapping_uses_stable_company_account_id_not_display_code() -> None:
    result = FinancialStatementEngine().build(
        FinancialStatementBuildRequest(
            accounting_entity_id=ENTITY,
            as_of=AS_OF,
            reporting_source=_source(),
            statement_definition=_definition(),
            mapping_set=_mapping_set(),
        )
    )

    assert result.line("CASH").amount == Money.from_str("100", EUR)
    assert result.line("EQUITY").amount == Money.from_str("100", EUR)
    assert result.drill_down("CASH")[0].account_code == "512000"
    assert result.controls[0].status is StatementControlStatus.PASS


def test_balance_sheet_control_can_fail_without_invalidating_source_balance() -> None:
    request = FinancialStatementBuildRequest(
        accounting_entity_id=ENTITY,
        as_of=AS_OF,
        reporting_source=_source(),
        statement_definition=_definition(include_unattached=True),
        mapping_set=_mapping_set(equity_target="UNATTACHED"),
    )
    result = FinancialStatementEngine().build(request)

    assert result.controls[0].status is StatementControlStatus.FAIL
    assert result.controls[0].difference == Money.from_str("100", EUR)

    strict_request = FinancialStatementBuildRequest(
        accounting_entity_id=request.accounting_entity_id,
        as_of=request.as_of,
        reporting_source=request.reporting_source,
        statement_definition=request.statement_definition,
        mapping_set=request.mapping_set,
        fail_on_control_error=True,
    )
    with pytest.raises(StatementControlError):
        FinancialStatementEngine().build(strict_request)


def test_expired_mapping_set_is_not_executable() -> None:
    with pytest.raises(NonExecutableStatementMappingError):
        FinancialStatementEngine().build(
            FinancialStatementBuildRequest(
                accounting_entity_id=ENTITY,
                as_of=AS_OF,
                reporting_source=_source(),
                statement_definition=_definition(),
                mapping_set=_mapping_set(effective_to=date(2026, 6, 30)),
            )
        )
