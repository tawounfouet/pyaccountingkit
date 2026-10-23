"""LOT-21 unit qualification for the framework-neutral public API facade."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from pyaccountingkit import AccountingApplication, CommandContext, Money
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import PeriodClosedError
from pyaccountingkit.core.identifiers import AccountId, EntryId, JournalId, PeriodId
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.engine import FinancialStatementResult
from pyaccountingkit.domain.reporting.statement_definition import FinancialStatementType
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance, TrialBalanceSnapshot
from pyaccountingkit.public.analysis import FinancialAnalysisAPI
from pyaccountingkit.public.charts import ChartsAPI
from pyaccountingkit.public.closing import ClosingAPI
from pyaccountingkit.public.contracts import (
    PUBLIC_OPERATION_CONTRACTS,
    PublicOperationKind,
    PublicOperationRequest,
)
from pyaccountingkit.public.controls import ControlsAPI
from pyaccountingkit.public.dto import FinancialStatementDTO, JournalEntryDTO, TrialBalanceDTO
from pyaccountingkit.public.entries import EntriesAPI
from pyaccountingkit.public.errors import (
    PublicBoundaryViolationError,
    PublicInfrastructureError,
    PublicOperationUnavailableError,
    PublicValidationError,
)
from pyaccountingkit.public.imports import ImportsAPI
from pyaccountingkit.public.ledger import LedgerAPI
from pyaccountingkit.public.references import ReferencesAPI
from pyaccountingkit.public.reporting import RegulatoryReportingAPI
from pyaccountingkit.public.statements import StatementsAPI
from pyaccountingkit.public.subledgers import (
    MatchingAPI,
    PartnersAPI,
    PayablesAPI,
    ReceivablesAPI,
    SettlementsAPI,
    SubledgersAPI,
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


class _FakeSQLAlchemyModel:
    __module__ = "sqlalchemy.orm.base"


class _ObjectWrapper:
    def __init__(self, value: object) -> None:
        self.value = value


class _SlotWrapper:
    __slots__ = ("value",)

    def __init__(self, value: object) -> None:
        self.value = value


class _WrappedLeakyService:
    def get(self, **parameters: object) -> object:
        return _ObjectWrapper(_SlotWrapper(_FakeSQLAlchemyModel()))


class _FrameworkClassService:
    def get(self, **parameters: object) -> object:
        return _FakeDjangoModel


class _CyclicWrapperService:
    def get(self, **parameters: object) -> object:
        wrapper = _ObjectWrapper(None)
        wrapper.value = wrapper
        return wrapper


class _InputProbeService:
    def __init__(self) -> None:
        self.called = False

    def create(self, **parameters: object) -> str:
        self.called = True
        return "created"


class _FakeDjangoDatabaseError(Exception):
    __module__ = "django.db.utils"


class _FrameworkFailureService:
    def get(self, **parameters: object) -> object:
        raise _FakeDjangoDatabaseError("duplicate key secret table detail")


class _DomainFailureService:
    def post(self, **parameters: object) -> object:
        raise PeriodClosedError("period is closed")


class _UnknownFailureService:
    def get(self, **parameters: object) -> object:
        raise RuntimeError("unexpected bug")


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


def test_framework_specific_objects_are_rejected_through_plain_wrappers() -> None:
    app = AccountingApplication(entries=_WrappedLeakyService())
    with pytest.raises(PublicBoundaryViolationError) as raised:
        app.entries.get(entry_id="entry-1")
    assert raised.value.to_info().details["object_type"].startswith("sqlalchemy.")


def test_framework_class_is_rejected_at_public_boundary() -> None:
    app = AccountingApplication(entries=_FrameworkClassService())
    with pytest.raises(PublicBoundaryViolationError) as raised:
        app.entries.get(entry_id="entry-1")
    assert raised.value.to_info().details["object_type"].startswith("django.")


def test_cyclic_neutral_wrapper_is_cycle_safe() -> None:
    app = AccountingApplication(entries=_CyclicWrapperService())
    result = app.entries.get(entry_id="entry-1")
    assert isinstance(result, _ObjectWrapper)
    assert result.value is result


def test_framework_specific_input_is_rejected_before_service_invocation() -> None:
    service = _InputProbeService()
    app = AccountingApplication(entries=service)

    with pytest.raises(PublicBoundaryViolationError):
        app.entries.create(payload=_ObjectWrapper(_FakeDjangoModel()))

    assert service.called is False


def test_framework_exception_is_translated_without_raw_database_message() -> None:
    app = AccountingApplication(entries=_FrameworkFailureService())
    with pytest.raises(PublicInfrastructureError) as raised:
        app.entries.get(entry_id="entry-1")

    info = raised.value.to_info()
    assert info.code == "PUBLIC_INFRASTRUCTURE_FAILURE"
    assert info.details["framework"] == "django"
    assert info.details["exception_type"].startswith("django.")
    assert "duplicate key" not in info.message
    assert "secret" not in info.message


def test_canonical_accounting_error_is_preserved_by_public_boundary() -> None:
    app = AccountingApplication(entries=_DomainFailureService())
    with pytest.raises(PeriodClosedError) as raised:
        app.entries.post(entry_id="entry-1")
    assert raised.value.code == "PERIOD_CLOSED"


def test_unknown_failure_is_not_hidden_by_public_translation() -> None:
    app = AccountingApplication(entries=_UnknownFailureService())
    with pytest.raises(RuntimeError, match="unexpected bug"):
        app.entries.get(entry_id="entry-1")


def test_public_operation_contract_catalog_is_exhaustive_for_every_facade_method() -> None:
    api_types = (
        ReferencesAPI,
        ChartsAPI,
        EntriesAPI,
        LedgerAPI,
        ClosingAPI,
        ControlsAPI,
        ImportsAPI,
        StatementsAPI,
        RegulatoryReportingAPI,
        FinancialAnalysisAPI,
        PartnersAPI,
        ReceivablesAPI,
        PayablesAPI,
        SettlementsAPI,
        MatchingAPI,
        SubledgersAPI,
    )
    discovered: set[str] = set()
    for api_type in api_types:
        api = api_type()
        namespace = api._namespace  # noqa: SLF001 - contract qualification
        for name, member in inspect.getmembers(api_type, predicate=inspect.isfunction):
            if name.startswith("_") or name == "__init__":
                continue
            if member.__qualname__.split(".", maxsplit=1)[0] != api_type.__name__:
                continue
            discovered.add(f"{namespace}.{name}")

    assert discovered == set(PUBLIC_OPERATION_CONTRACTS)
    assert all(
        contract.kind in {PublicOperationKind.COMMAND, PublicOperationKind.QUERY}
        for contract in PUBLIC_OPERATION_CONTRACTS.values()
    )


def test_public_operation_request_is_immutable_and_adapter_neutral() -> None:
    request = PublicOperationRequest(parameters={"entry_id": "entry-1"})
    with pytest.raises(TypeError):
        request.parameters["entry_id"] = "entry-2"  # type: ignore[index]
    assert request.parameters == {"entry_id": "entry-1"}


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
