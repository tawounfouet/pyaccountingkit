"""LOT-29R / F21 qualification for single-application reporting sign semantics."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.analysis.values import inputs_from_report_snapshot
from pyaccountingkit.domain.reporting.errors import InvalidStatementDefinitionError
from pyaccountingkit.domain.reporting.formula import FormulaOperation, StatementFormula
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotLine,
    ReportSnapshotStatus,
)
from pyaccountingkit.domain.reporting.statement_definition import FinancialStatementType
from pyaccountingkit.domain.reporting.statement_line import (
    StatementLineDefinition,
    StatementLineType,
    StatementSignConvention,
)


@pytest.mark.parametrize(
    "line_type",
    (StatementLineType.SUBTOTAL, StatementLineType.TOTAL),
)
def test_aggregate_lines_reject_non_natural_sign_conventions(
    line_type: StatementLineType,
) -> None:
    with pytest.raises(
        InvalidStatementDefinitionError,
        match="non-natural sign convention is only valid on DETAIL lines",
    ):
        StatementLineDefinition(
            line_id="computed",
            code="COMPUTED",
            label="Computed",
            line_type=line_type,
            order=1,
            sign_convention=StatementSignConvention.CREDIT_POSITIVE,
        )


def test_formula_lines_reject_non_natural_sign_conventions() -> None:
    with pytest.raises(
        InvalidStatementDefinitionError,
        match="non-natural sign convention is only valid on DETAIL lines",
    ):
        StatementLineDefinition(
            line_id="formula",
            code="FORMULA",
            label="Formula",
            line_type=StatementLineType.FORMULA,
            order=1,
            formula=StatementFormula(FormulaOperation.SUM, ("SOURCE",)),
            sign_convention=StatementSignConvention.ABSOLUTE,
        )


def test_detail_credit_positive_presentation_is_applied_once() -> None:
    line = StatementLineDefinition(
        line_id="liability",
        code="LIABILITY",
        label="Liability",
        line_type=StatementLineType.DETAIL,
        order=1,
        sign_convention=StatementSignConvention.CREDIT_POSITIVE,
    )

    ledger_signed = Money.from_str("-100", EUR)

    assert line.present(ledger_signed) == Money.from_str("100", EUR)


def test_financial_analysis_consumes_presented_snapshot_amount_without_resigning() -> None:
    snapshot = ReportSnapshot(
        snapshot_id="snapshot-sign-semantics",
        accounting_entity_id=EntityId("entity-sign-semantics"),
        report_type=FinancialStatementType.BALANCE_SHEET,
        source_period_id="FY2026",
        source_checksum="source-checksum",
        statement_definition_id="definition",
        statement_definition_version="1",
        statement_definition_checksum="definition-checksum",
        mapping_set_id="mapping",
        mapping_set_version="1",
        mapping_set_checksum="mapping-checksum",
        result_checksum="result-checksum",
        as_of=date(2026, 12, 31),
        created_at=datetime(2026, 12, 31, tzinfo=UTC),
        status=ReportSnapshotStatus.PUBLISHED,
        lines=(
            ReportSnapshotLine(
                code="LIABILITY",
                label="Liability",
                amount=Money.from_str("100", EUR),
                comparative_amount=None,
            ),
        ),
        checksum="snapshot-checksum",
    )

    inputs = inputs_from_report_snapshot(snapshot)

    assert len(inputs) == 1
    assert inputs[0].key == "LIABILITY"
    assert inputs[0].value.as_tuple() == Money.from_str("100", EUR).amount.as_tuple()
