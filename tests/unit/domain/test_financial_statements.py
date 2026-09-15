"""LOT-16 qualification for the pure financial-statements engine."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import EntityScopeMismatchError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.engine import (
    FinancialStatementBuildRequest,
    FinancialStatementEngine,
    StatementControlStatus,
)
from pyaccountingkit.domain.reporting.errors import (
    FormulaCycleError,
    NonExecutableStatementMappingError,
    StatementMappingError,
    StatementSourceError,
)
from pyaccountingkit.domain.reporting.formula import FormulaOperation, StatementFormula
from pyaccountingkit.domain.reporting.mappings import (
    MappingProvenance,
    StatementAccountMapping,
    StatementMappingSet,
    StatementMappingSetStatus,
    StatementMappingStatus,
)
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotFreshness,
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

ENTITY = EntityId("entity-a")
OTHER_ENTITY = EntityId("entity-b")
AS_OF = date(2026, 12, 31)


def _line(code: str, debit: str, credit: str) -> AccountBalanceLine:
    return AccountBalanceLine(
        account_code=code,
        label=f"Account {code}",
        sum_debit=Money.from_str(debit, EUR),
        sum_credit=Money.from_str(credit, EUR),
    )


def _trial_balance(
    *lines: AccountBalanceLine,
    entity: EntityId | None = ENTITY,
    period: str = "FY2026",
) -> TrialBalance:
    return TrialBalance.build(
        period,
        TrialBalanceSnapshot.ADJUSTED,
        tuple(lines),
        accounting_entity_id=entity,
    )


def _balance_sheet_definition() -> FinancialStatementDefinition:
    return FinancialStatementDefinition(
        definition_id="def-bs",
        code="BS",
        statement_type=FinancialStatementType.BALANCE_SHEET,
        version="1",
        effective_from=date(2026, 1, 1),
        lines=(
            StatementLineDefinition(
                line_id="assets-total",
                code="ASSETS_TOTAL",
                label="Total assets",
                line_type=StatementLineType.TOTAL,
                order=20,
                control_role=StatementControlRole.ASSETS_TOTAL,
            ),
            StatementLineDefinition(
                line_id="assets-cash",
                code="ASSET_CASH",
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
                line_id="liabilities",
                code="LIABILITY",
                label="Liabilities",
                line_type=StatementLineType.DETAIL,
                order=30,
                parent_line_id="le-total",
                sign_convention=StatementSignConvention.CREDIT_POSITIVE,
            ),
        ),
    )


def _mapping(
    mapping_id: str,
    account: str,
    line_code: str,
    *,
    allocation: str = "1",
    status: StatementMappingStatus = StatementMappingStatus.VALIDATED,
) -> StatementAccountMapping:
    return StatementAccountMapping(
        mapping_id=mapping_id,
        company_account_id=account,
        statement_line_code=line_code,
        allocation=Decimal(allocation),
        mapping_status=status,
        provenance=MappingProvenance.MANUAL,
        effective_from=date(2026, 1, 1),
    )


def _balance_sheet_mapping_set(
    *,
    entity: EntityId = ENTITY,
    status: StatementMappingSetStatus = StatementMappingSetStatus.ACTIVE,
    mapping_status: StatementMappingStatus = StatementMappingStatus.VALIDATED,
) -> StatementMappingSet:
    return StatementMappingSet(
        mapping_set_id="map-bs",
        accounting_entity_id=entity,
        statement_definition_id="def-bs",
        version="1",
        status=status,
        mappings=(
            _mapping("m1", "100", "ASSET_CASH", status=mapping_status),
            _mapping("m2", "200", "LIABILITY", status=mapping_status),
        ),
        effective_from=date(2026, 1, 1),
    )


def _balance_sheet_request(
    *,
    source: TrialBalance | None = None,
    mapping_set: StatementMappingSet | None = None,
) -> FinancialStatementBuildRequest:
    return FinancialStatementBuildRequest(
        accounting_entity_id=ENTITY,
        as_of=AS_OF,
        reporting_source=(
            source
            if source is not None
            else _trial_balance(_line("100", "100", "0"), _line("200", "0", "100"))
        ),
        statement_definition=_balance_sheet_definition(),
        mapping_set=mapping_set or _balance_sheet_mapping_set(),
    )


def test_balance_sheet_projection_and_control() -> None:
    result = FinancialStatementEngine().build(_balance_sheet_request())

    assert result.line("ASSET_CASH").amount == Money.from_str("100", EUR)
    assert result.line("LIABILITY").amount == Money.from_str("100", EUR)
    assert result.line("ASSETS_TOTAL").amount == Money.from_str("100", EUR)
    assert result.line("LE_TOTAL").amount == Money.from_str("100", EUR)
    assert result.controls[0].status is StatementControlStatus.PASS
    assert result.controls[0].difference.is_zero()
    assert result.drill_down("ASSET_CASH")[0].account_code == "100"


def test_balance_sheet_control_detects_difference_when_mapping_omits_value() -> None:
    mapping_set = StatementMappingSet(
        mapping_set_id="map-bs",
        accounting_entity_id=ENTITY,
        statement_definition_id="def-bs",
        version="1",
        status=StatementMappingSetStatus.ACTIVE,
        mappings=(
            _mapping("m1", "100", "ASSET_CASH"),
            _mapping("m2", "200", "LIABILITY", allocation="0.5"),
        ),
        effective_from=date(2026, 1, 1),
    )
    request = _balance_sheet_request(mapping_set=mapping_set)
    with pytest.raises(StatementMappingError, match="allocate exactly 1"):
        FinancialStatementEngine().build(request)


def test_cross_entity_mapping_set_fails_closed() -> None:
    with pytest.raises(EntityScopeMismatchError):
        FinancialStatementEngine().build(
            _balance_sheet_request(mapping_set=_balance_sheet_mapping_set(entity=OTHER_ENTITY))
        )


def test_unscoped_trial_balance_is_rejected() -> None:
    source = _trial_balance(
        _line("100", "100", "0"),
        _line("200", "0", "100"),
        entity=None,
    )
    with pytest.raises(StatementSourceError):
        FinancialStatementEngine().build(_balance_sheet_request(source=source))


def test_candidate_mapping_set_is_not_executable() -> None:
    mapping_set = _balance_sheet_mapping_set(
        status=StatementMappingSetStatus.ACTIVE,
        mapping_status=StatementMappingStatus.CANDIDATE,
    )
    with pytest.raises(NonExecutableStatementMappingError):
        FinancialStatementEngine().build(_balance_sheet_request(mapping_set=mapping_set))


def test_formula_cycle_is_rejected_at_definition_construction() -> None:
    with pytest.raises(FormulaCycleError):
        FinancialStatementDefinition(
            definition_id="formula-cycle",
            code="FC",
            statement_type=FinancialStatementType.CUSTOM,
            version="1",
            effective_from=date(2026, 1, 1),
            lines=(
                StatementLineDefinition(
                    line_id="a",
                    code="A",
                    label="A",
                    line_type=StatementLineType.FORMULA,
                    order=1,
                    formula=StatementFormula(FormulaOperation.SUM, ("B",)),
                ),
                StatementLineDefinition(
                    line_id="b",
                    code="B",
                    label="B",
                    line_type=StatementLineType.FORMULA,
                    order=2,
                    formula=StatementFormula(FormulaOperation.SUM, ("A",)),
                ),
            ),
        )


def test_formula_dsl_and_cash_flow_reconciliation() -> None:
    definition = FinancialStatementDefinition(
        definition_id="def-cf",
        code="CF",
        statement_type=FinancialStatementType.CASH_FLOW_STATEMENT,
        version="1",
        effective_from=date(2026, 1, 1),
        lines=(
            StatementLineDefinition(
                line_id="open",
                code="OPEN",
                label="Opening cash",
                line_type=StatementLineType.DETAIL,
                order=1,
                control_role=StatementControlRole.CASH_OPENING,
            ),
            StatementLineDefinition(
                line_id="net",
                code="NET",
                label="Net change",
                line_type=StatementLineType.DETAIL,
                order=2,
                control_role=StatementControlRole.CASH_NET_CHANGE,
            ),
            StatementLineDefinition(
                line_id="close",
                code="CLOSE",
                label="Closing cash",
                line_type=StatementLineType.FORMULA,
                order=3,
                formula=StatementFormula(FormulaOperation.ADD, ("OPEN", "NET")),
                control_role=StatementControlRole.CASH_CLOSING,
            ),
        ),
    )
    mapping_set = StatementMappingSet(
        mapping_set_id="map-cf",
        accounting_entity_id=ENTITY,
        statement_definition_id="def-cf",
        version="1",
        status=StatementMappingSetStatus.ACTIVE,
        mappings=(
            _mapping("open-map", "100", "OPEN"),
            _mapping("net-map", "110", "NET"),
        ),
        effective_from=date(2026, 1, 1),
    )
    source = _trial_balance(
        _line("100", "100", "0"),
        _line("110", "20", "0"),
        _line("200", "0", "120"),
    )
    result = FinancialStatementEngine().build(
        FinancialStatementBuildRequest(
            accounting_entity_id=ENTITY,
            as_of=AS_OF,
            reporting_source=source,
            statement_definition=definition,
            mapping_set=mapping_set,
            require_full_mapping=False,
        )
    )

    assert result.line("CLOSE").amount == Money.from_str("120", EUR)
    assert result.controls[0].status is StatementControlStatus.PASS


def test_one_to_many_allocation_and_comparative_are_deterministic() -> None:
    definition = FinancialStatementDefinition(
        definition_id="def-custom",
        code="CUSTOM",
        statement_type=FinancialStatementType.CUSTOM,
        version="1",
        effective_from=date(2026, 1, 1),
        lines=(
            StatementLineDefinition(
                line_id="a",
                code="A",
                label="A",
                line_type=StatementLineType.DETAIL,
                order=1,
            ),
            StatementLineDefinition(
                line_id="b",
                code="B",
                label="B",
                line_type=StatementLineType.DETAIL,
                order=2,
            ),
        ),
    )
    mapping_set = StatementMappingSet(
        mapping_set_id="map-custom",
        accounting_entity_id=ENTITY,
        statement_definition_id="def-custom",
        version="1",
        status=StatementMappingSetStatus.ACTIVE,
        mappings=(
            _mapping("a-map", "100", "A", allocation="0.6"),
            _mapping("b-map", "100", "B", allocation="0.4"),
        ),
        effective_from=date(2026, 1, 1),
    )
    current = _trial_balance(
        _line("100", "100", "0"),
        _line("200", "0", "100"),
    )
    prior = _trial_balance(
        _line("100", "80", "0"),
        _line("200", "0", "80"),
        period="FY2025",
    )
    result = FinancialStatementEngine().build(
        FinancialStatementBuildRequest(
            accounting_entity_id=ENTITY,
            as_of=AS_OF,
            reporting_source=current,
            comparative_source=prior,
            statement_definition=definition,
            mapping_set=mapping_set,
            require_full_mapping=False,
        )
    )

    assert result.line("A").amount == Money.from_str("60", EUR)
    assert result.line("B").amount == Money.from_str("40", EUR)
    assert result.line("A").comparative_amount == Money.from_str("48", EUR)
    assert result.line("B").comparative_amount == Money.from_str("32", EUR)


def test_report_snapshot_is_content_deterministic_immutable_and_stale_aware() -> None:
    result = FinancialStatementEngine().build(_balance_sheet_request())
    first = ReportSnapshot.from_result(
        snapshot_id="snap-1",
        result=result,
        created_at=datetime(2026, 12, 31, tzinfo=UTC),
    )
    second = ReportSnapshot.from_result(
        snapshot_id="snap-2",
        result=result,
        created_at=datetime(2027, 1, 1, tzinfo=UTC),
    )

    assert first.checksum == second.checksum
    assert first.freshness_against(result.source_checksum) is ReportSnapshotFreshness.CURRENT
    assert first.freshness_against("changed") is ReportSnapshotFreshness.STALE
    with pytest.raises(FrozenInstanceError):
        first.status = first.status  # type: ignore[misc]
