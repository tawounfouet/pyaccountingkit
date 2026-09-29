"""CFA FRA Sprint 6 financial-statement golden parity."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from pyaccountingkit.core.currency import XAF
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.engine import (
    FinancialStatementBuildRequest,
    FinancialStatementEngine,
)
from pyaccountingkit.domain.reporting.formula import FormulaOperation, StatementFormula
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
from pyaccountingkit.integrations.cfa_fra import load_golden_fixture

FIXTURE = Path(__file__).parent / "fixtures" / "financial_statements.json"
ENTITY = EntityId("cfa-ent")
AS_OF = date(2025, 12, 31)
EFFECTIVE_FROM = date(2025, 1, 1)


def _line(code: str, debit: str, credit: str) -> AccountBalanceLine:
    return AccountBalanceLine(
        account_code=code,
        label=code,
        sum_debit=Money.from_str(debit, XAF),
        sum_credit=Money.from_str(credit, XAF),
    )


def _trial_balance(*lines: AccountBalanceLine) -> TrialBalance:
    return TrialBalance.build(
        "FY2025",
        TrialBalanceSnapshot.ADJUSTED,
        tuple(lines),
        accounting_entity_id=ENTITY,
    )


def _mapping(mapping_id: str, account: str, target: str) -> StatementAccountMapping:
    return StatementAccountMapping(
        mapping_id=mapping_id,
        company_account_id=account,
        statement_line_code=target,
        allocation=Decimal("1"),
        mapping_status=StatementMappingStatus.VALIDATED,
        provenance=MappingProvenance.MIGRATION,
        effective_from=EFFECTIVE_FROM,
    )


def _mapping_set(
    definition: FinancialStatementDefinition,
    *mappings: StatementAccountMapping,
) -> StatementMappingSet:
    return StatementMappingSet(
        mapping_set_id=f"map:{definition.code}",
        accounting_entity_id=ENTITY,
        statement_definition_id=definition.definition_id,
        version="cfa-sprint-6",
        status=StatementMappingSetStatus.ACTIVE,
        mappings=tuple(mappings),
        effective_from=EFFECTIVE_FROM,
    )


def _detail(
    code: str,
    order: int,
    *,
    parent: str | None = None,
    credit_positive: bool = False,
    control_role: StatementControlRole | None = None,
) -> StatementLineDefinition:
    return StatementLineDefinition(
        line_id=code.lower(),
        code=code,
        label=code,
        line_type=StatementLineType.DETAIL,
        order=order,
        parent_line_id=parent,
        sign_convention=(
            StatementSignConvention.CREDIT_POSITIVE
            if credit_positive
            else StatementSignConvention.NATURAL
        ),
        control_role=control_role,
    )


def _formula(
    code: str,
    order: int,
    operation: FormulaOperation,
    operands: tuple[str, ...],
    *,
    parent: str | None = None,
    control_role: StatementControlRole | None = None,
) -> StatementLineDefinition:
    return StatementLineDefinition(
        line_id=code.lower(),
        code=code,
        label=code,
        line_type=StatementLineType.FORMULA,
        order=order,
        parent_line_id=parent,
        formula=StatementFormula(operation, operands),
        control_role=control_role,
    )


def _total(
    code: str,
    order: int,
    *,
    control_role: StatementControlRole | None = None,
) -> StatementLineDefinition:
    return StatementLineDefinition(
        line_id=code.lower(),
        code=code,
        label=code,
        line_type=StatementLineType.TOTAL,
        order=order,
        control_role=control_role,
    )


def _build(
    definition: FinancialStatementDefinition,
    mapping_set: StatementMappingSet,
    source: TrialBalance,
    *,
    require_full_mapping: bool = True,
):
    return FinancialStatementEngine().build(
        FinancialStatementBuildRequest(
            accounting_entity_id=ENTITY,
            as_of=AS_OF,
            reporting_source=source,
            statement_definition=definition,
            mapping_set=mapping_set,
            require_full_mapping=require_full_mapping,
        )
    )


def _income_observation(source: TrialBalance) -> dict[str, object]:
    definition = FinancialStatementDefinition(
        definition_id="cfa-is",
        code="CFA_FRA_IS",
        statement_type=FinancialStatementType.INCOME_STATEMENT,
        version="sprint-6",
        effective_from=EFFECTIVE_FROM,
        lines=(
            _detail("REVENUE", 10, credit_positive=True),
            _detail("EXTERNAL_SERVICES", 20),
            _formula(
                "NET_INCOME",
                30,
                FormulaOperation.SUBTRACT,
                ("REVENUE", "EXTERNAL_SERVICES"),
                control_role=StatementControlRole.NET_INCOME,
            ),
        ),
    )
    mappings = _mapping_set(
        definition,
        _mapping("is-revenue", "70100000", "REVENUE"),
        _mapping("is-services", "62200000", "EXTERNAL_SERVICES"),
    )
    result = _build(definition, mappings, source, require_full_mapping=False)
    return {
        "revenue": result.line("REVENUE").amount.amount,
        "external_services": result.line("EXTERNAL_SERVICES").amount.amount,
        "net_income": result.line("NET_INCOME").amount.amount,
    }


def _balance_sheet_observation(source: TrialBalance) -> dict[str, object]:
    definition = FinancialStatementDefinition(
        definition_id="cfa-bs",
        code="CFA_FRA_BS",
        statement_type=FinancialStatementType.BALANCE_SHEET,
        version="sprint-6",
        effective_from=EFFECTIVE_FROM,
        lines=(
            _total(
                "TOTAL_ASSETS",
                30,
                control_role=StatementControlRole.ASSETS_TOTAL,
            ),
            _detail("CURRENT_ASSETS", 10, parent="total_assets"),
            _detail("NONCURRENT_ASSETS", 20, parent="total_assets"),
            _total(
                "TOTAL_LIABILITIES_EQUITY",
                80,
                control_role=StatementControlRole.LIABILITIES_EQUITY_TOTAL,
            ),
            _detail(
                "CURRENT_LIABILITIES",
                40,
                parent="total_liabilities_equity",
                credit_positive=True,
            ),
            _detail(
                "NONCURRENT_LIABILITIES",
                50,
                parent="total_liabilities_equity",
                credit_positive=True,
            ),
            _detail(
                "EQUITY",
                60,
                parent="total_liabilities_equity",
                credit_positive=True,
            ),
            _formula(
                "CURRENT_RESULT",
                70,
                FormulaOperation.SUBTRACT,
                ("REVENUE_MEMO", "EXPENSE_MEMO"),
                parent="total_liabilities_equity",
            ),
            _detail("REVENUE_MEMO", 90, credit_positive=True),
            _detail("EXPENSE_MEMO", 100),
        ),
    )
    mappings = _mapping_set(
        definition,
        _mapping("bs-ca", "57110000", "CURRENT_ASSETS"),
        _mapping("bs-nca", "21500000", "NONCURRENT_ASSETS"),
        _mapping("bs-cl", "40810000", "CURRENT_LIABILITIES"),
        _mapping("bs-ncl", "16400000", "NONCURRENT_LIABILITIES"),
        _mapping("bs-equity", "10110000", "EQUITY"),
        _mapping("bs-revenue", "70100000", "REVENUE_MEMO"),
        _mapping("bs-expense", "62200000", "EXPENSE_MEMO"),
    )
    result = _build(definition, mappings, source)
    control = result.controls[0]
    return {
        "current_assets": result.line("CURRENT_ASSETS").amount.amount,
        "noncurrent_assets": result.line("NONCURRENT_ASSETS").amount.amount,
        "total_assets": result.line("TOTAL_ASSETS").amount.amount,
        "current_liabilities": result.line("CURRENT_LIABILITIES").amount.amount,
        "noncurrent_liabilities": result.line("NONCURRENT_LIABILITIES").amount.amount,
        "equity": result.line("EQUITY").amount.amount,
        "current_result": result.line("CURRENT_RESULT").amount.amount,
        "total_liabilities_equity": result.line("TOTAL_LIABILITIES_EQUITY").amount.amount,
        "balance_gap": control.difference.amount,
        "is_balanced": control.difference.is_zero(),
    }


def _cash_flow_observation() -> dict[str, object]:
    source = _trial_balance(
        _line("OPENING_CASH", "1000", "0"),
        _line("CFO", "300", "0"),
        _line("CFI", "0", "100"),
        _line("CFF", "300", "0"),
        _line("ENDING_CASH", "1500", "0"),
        _line("BALANCING", "0", "3000"),
    )
    definition = FinancialStatementDefinition(
        definition_id="cfa-cf",
        code="CFA_FRA_CF",
        statement_type=FinancialStatementType.CASH_FLOW_STATEMENT,
        version="sprint-6",
        effective_from=EFFECTIVE_FROM,
        lines=(
            _detail(
                "OPENING_CASH",
                10,
                control_role=StatementControlRole.CASH_OPENING,
            ),
            _detail("OPERATING", 20),
            _detail("INVESTING", 30),
            _detail("FINANCING", 40),
            _detail("UNCLASSIFIED", 50),
            _formula(
                "NET_CHANGE",
                60,
                FormulaOperation.SUM,
                ("OPERATING", "INVESTING", "FINANCING", "UNCLASSIFIED"),
                control_role=StatementControlRole.CASH_NET_CHANGE,
            ),
            _detail(
                "ENDING_CASH",
                70,
                control_role=StatementControlRole.CASH_CLOSING,
            ),
        ),
    )
    mappings = _mapping_set(
        definition,
        _mapping("cf-open", "OPENING_CASH", "OPENING_CASH"),
        _mapping("cf-cfo", "CFO", "OPERATING"),
        _mapping("cf-cfi", "CFI", "INVESTING"),
        _mapping("cf-cff", "CFF", "FINANCING"),
        _mapping("cf-end", "ENDING_CASH", "ENDING_CASH"),
    )
    result = _build(definition, mappings, source, require_full_mapping=False)
    control = result.controls[0]
    return {
        "opening_cash": result.line("OPENING_CASH").amount.amount,
        "operating": result.line("OPERATING").amount.amount,
        "investing": result.line("INVESTING").amount.amount,
        "financing": result.line("FINANCING").amount.amount,
        "unclassified": result.line("UNCLASSIFIED").amount.amount,
        "net_change": result.line("NET_CHANGE").amount.amount,
        "ending_cash": result.line("ENDING_CASH").amount.amount,
        "reconciliation_gap": control.difference.amount,
    }


def test_financial_statements_match_cfa_fra_sprint_6_golden() -> None:
    fixture = load_golden_fixture(FIXTURE)
    source = _trial_balance(
        _line("57110000", "1500", "0"),
        _line("21500000", "100", "0"),
        _line("40810000", "0", "50"),
        _line("16400000", "0", "300"),
        _line("10110000", "0", "1000"),
        _line("70100000", "0", "500"),
        _line("62200000", "250", "0"),
    )
    actual = {
        "income_statement": _income_observation(source),
        "balance_sheet": _balance_sheet_observation(source),
        "cash_flow": _cash_flow_observation(),
    }
    parity = fixture.compare(actual)
    assert parity.exact is True
    assert parity.qualified is True
