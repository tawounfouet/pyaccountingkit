"""Unit tests for the canonical error-code contract."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.errors import (
    AccountingError,
    CoreError,
    DomainError,
    EmptyEntryError,
    EntryRuleError,
    IncompatibleCurrenciesError,
    InvalidAmountError,
    PeriodClosedError,
    UnbalancedEntryError,
)


@pytest.mark.parametrize(
    ("exception", "expected_code"),
    [
        (InvalidAmountError, "CORE_INVALID_AMOUNT"),
        (IncompatibleCurrenciesError, "CORE_INCOMPATIBLE_CURRENCIES"),
        (UnbalancedEntryError, "ENTRY_UNBALANCED"),
        (EmptyEntryError, "ENTRY_EMPTY"),
        (PeriodClosedError, "PERIOD_CLOSED"),
    ],
)
def test_error_codes_are_stable(exception: type[AccountingError], expected_code: str) -> None:
    assert exception().code == expected_code


def test_error_hierarchy_is_subtype_of_base() -> None:
    assert issubclass(UnbalancedEntryError, EntryRuleError)
    assert issubclass(UnbalancedEntryError, DomainError)
    assert issubclass(InvalidAmountError, CoreError)
    assert issubclass(CoreError, AccountingError)


def test_error_carry_message() -> None:
    error = UnbalancedEntryError("déséquilibrée")
    assert str(error) == "déséquilibrée"
    assert error.message == "déséquilibrée"


def test_accounting_errors_are_importable_for_handlers() -> None:
    from pyaccountingkit.core import errors as core_errors

    public_names = {name for name in dir(core_errors) if name.endswith("Error")}
    assert "PeriodClosedError" in public_names
    assert "RevisionConflictError" in public_names
