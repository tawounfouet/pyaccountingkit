"""LOT-21 unit qualification for the framework-neutral public API facade."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from pyaccountingkit import AccountingApplication, CommandContext, Money
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import AccountId, EntryId, JournalId, PeriodId
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.engine import FinancialStatementResult
from pyaccountingkit.domain.reporting.statement_definition import FinancialStatementType
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance, TrialBalanceSnapshot
from pyaccountingkit.public.dto import FinancialStatementDTO, JournalEntryDTO, TrialBalanceDTO
from pyaccountingkit.public.errors import (
    PublicBoundaryViolationError,
    PublicOperationUnavailableError,
    PublicValidationError,
)
from pyaccountingkit.public.pagination import Cursor, Page


class _EntriesService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(self, **parameters: object) -> str:
        self.calls.append(parameters)
        return "posted-entry"


class _NestedSubledgerService:
    def record(self, **parameters: object) -> str:
        return f"recorded:{parameters['settlement_id']}"


class _SubledgerService:
    def __init__(self) -> None:
        self.settlements = _NestedSubledgerService()

    def reconcile(self, **parameters: object) -> str:
        return f"reconciled:{parameters['entity_id']}"


class _FakeDjangoModel:
    __module__ = "django.db.models.base"


class _LeakyService:
    def get(self, **parameters: object) -> object:
        return {"row": _FakeDjangoModel()}


def _entry() -> JournalEntry:
    return JournalEntry(
        id=EntryId("entry-1"),
        journal_id=JournalId("journal-1"),
        period_id=PeriodId("period-1"),
        entry_date=date(2026, 9, 18),
        description="Public DTO",
        lines=(
            JournalLine(
                account_id=AccountId("411000"),
                debit=Money.from_str("100.00", EUR),
                credit=Money.zero(EUR),
                label="Customer",
            ),
            JournalLine(
                account_id=AccountId("707000"),
                debit=Money.zero(EUR),
                credit=Money.from_str("100.00", EUR),
                label="Sales",
            ),
        ),
    )


def _trial_balance() -> TrialBalance:
    return TrialBalance.build(
        "period-1",
        TrialBalanceSnapshot.ADJUSTED,
        (
            AccountBalanceLine(
                account_id=None,
                account_code="411000",
                label="Customer",
                sum_debit=Money.from_str("100.00", EUR),
                sum_credit=Money.zero(EUR),
            ),
            AccountBalanceLine(
                account_id=AccountId("707000"),
                account_code="707000",
                label="Sales",
                sum_debit=Money.zero(EUR),
                sum_credit=Money.from_str("100.00", EUR),
            ),
        ),
    )


def test_accounting_application_exposes_all_public_namespaces() -> None:
    app = AccountingApplication()
    assert tuple(
        name
        for name in (
            "references",
            "charts",
            "entries",
            "ledger",
            "closing",
            "controls",
            "imports",
            "statements",
            "reporting",
            "analysis",
            "subledgers",
        )
        if hasattr(app, name)
    ) == (
        "references",
        "charts",
        "entries",
        "ledger",
        "closing",
        "controls",
        "imports",
        "statements",
        "reporting",
        "analysis",
        "subledgers",
    )


def test_public_operation_delegates_explicit_parameters_and_context() -> None:
    service = _EntriesService()
    app = AccountingApplication(entries=service)
    context = CommandContext(actor="user:42", correlation_id="corr-1")

    result = app.entries.post(entry_id="entry-1", context=context)

    assert result == "posted-entry"
    assert service.calls == [{"entry_id": "entry-1", "context": context}]


def test_subledger_nested_facade_delegates_without_exposing_service() -> None:
    app = AccountingApplication(subledgers=_SubledgerService())
    assert app.subledgers.settlements.record(settlement_id="s-1") == "recorded:s-1"
    assert app.subledgers.reconcile(entity_id="entity-a") == "reconciled:entity-a"


def test_missing_operation_fails_closed_with_machine_readable_error() -> None:
    app = AccountingApplication()
    with pytest.raises(PublicOperationUnavailableError) as raised:
        app.entries.post(entry_id="entry-1")
    assert raised.value.code == "PUBLIC_OPERATION_UNAVAILABLE"
    assert raised.value.to_info().details["namespace"] == "entries"


def test_framework_specific_objects_are_rejected_recursively() -> None:
    app = AccountingApplication(entries=_LeakyService())
    with pytest.raises(PublicBoundaryViolationError) as raised:
        app.entries.get(entry_id="entry-1")
    assert raised.value.code == "PUBLIC_BOUNDARY_VIOLATION"
    assert raised.value.to_info().details["object_type"].startswith("django.")


def test_command_context_is_frozen_and_metadata_read_only() -> None:
    context = CommandContext(
        actor="user:42",
        correlation_id="corr-1",
        metadata={"source": "api"},
    )
    with pytest.raises(TypeError):
        context.metadata["source"] = "mutated"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        context.actor = "other"  # type: ignore[misc]


def test_page_is_frozen_cursor_first_and_validated() -> None:
    page = Page(items=("a", "b"), page_size=2, next_cursor=Cursor("cursor-2"))
    assert page.items == ("a", "b")
    assert page.next_cursor == "cursor-2"
    with pytest.raises(FrozenInstanceError):
        page.page_size = 3  # type: ignore[misc]
    with pytest.raises(PublicValidationError):
        Page(items=("a", "b"), page_size=1)


def test_journal_entry_dto_is_immutable_and_deterministic() -> None:
    dto = JournalEntryDTO.from_domain(_entry())
    assert dto.entry_id == "entry-1"
    assert dto.status == "DRAFT"
    assert dto.lines[0].account_id == "411000"
    with pytest.raises(FrozenInstanceError):
        dto.description = "mutated"  # type: ignore[misc]


def test_trial_balance_dto_preserves_optional_account_identity() -> None:
    dto = TrialBalanceDTO.from_domain(_trial_balance())
    assert dto.lines[0].account_id is None
    assert dto.lines[1].account_id == "707000"
    assert dto.total_debit == Money.from_str("100.00", EUR)


def test_financial_statement_dto_maps_framework_neutral_fields() -> None:
    result = FinancialStatementResult(
        accounting_entity_id="entity-a",  # type: ignore[arg-type]
        statement_type=FinancialStatementType.INCOME_STATEMENT,
        statement_definition_id="income",
        statement_definition_version="1",
        statement_definition_checksum="def-checksum",
        mapping_set_id="mapping",
        mapping_set_version="1",
        mapping_set_checksum="mapping-checksum",
        source_period_id="period-1",
        source_checksum="source-checksum",
        source_snapshot="ADJUSTED",
        as_of=date(2026, 12, 31),
        lines=(),
        controls=(),
        checksum="statement-checksum",
    )
    dto = FinancialStatementDTO.from_domain(result)
    assert dto.accounting_entity_id == "entity-a"
    assert dto.statement_type == FinancialStatementType.INCOME_STATEMENT.value
    assert dto.lines == ()


def test_public_validation_errors_are_machine_readable() -> None:
    error = PublicValidationError("bad input", context={"field": "page_size"})
    info = error.to_info()
    assert info.code == "PUBLIC_VALIDATION_ERROR"
    assert info.retryable is False
    assert info.details == {"field": "page_size"}
