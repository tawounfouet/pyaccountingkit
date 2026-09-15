"""Unit tests for AccountingPeriod and its closing-status transitions."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.errors import DateOutsidePeriodError
from pyaccountingkit.core.identifiers import EntityId, FiscalYearId, PeriodId
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus


def _period(status: ClosingStatus = ClosingStatus.OPEN) -> AccountingPeriod:
    return AccountingPeriod(
        id=PeriodId("p1"),
        entity_id=EntityId("ent_1"),
        fiscal_year_id=FiscalYearId("fy_2024"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        status=status,
    )


def test_period_carries_entity_scope() -> None:
    period = _period()
    assert period.entity_id == EntityId("ent_1")
    assert period.fiscal_year_id == FiscalYearId("fy_2024")


def test_period_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError):
        AccountingPeriod(
            id=PeriodId("p1"),
            entity_id=EntityId("ent_1"),
            fiscal_year_id=FiscalYearId("fy_2024"),
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),
        )


def test_open_period_accepts_internal_dates() -> None:
    period = _period()
    assert period.contains(date(2024, 6, 15))
    assert period.is_open_for_posting()
    period.assert_date_within(date(2024, 6, 15))


def test_period_rejects_outside_dates() -> None:
    period = _period()
    assert not period.contains(date(2025, 1, 1))
    with pytest.raises(DateOutsidePeriodError):
        period.assert_date_within(date(2025, 1, 1))


@pytest.mark.parametrize("status", [ClosingStatus.LOCKED, ClosingStatus.CLOSED])
def test_non_open_periods_block_posting(status: ClosingStatus) -> None:
    assert not _period(status).is_open_for_posting()


def test_closing_status_is_closed() -> None:
    assert ClosingStatus.CLOSED.is_closed()
    assert not ClosingStatus.OPEN.is_closed()


@pytest.mark.parametrize(
    ("source", "target", "allowed"),
    [
        (ClosingStatus.OPEN, ClosingStatus.REVIEW, True),
        (ClosingStatus.OPEN, ClosingStatus.LOCKED, True),
        (ClosingStatus.OPEN, ClosingStatus.CLOSED, False),
        (ClosingStatus.REVIEW, ClosingStatus.OPEN, True),
        (ClosingStatus.REVIEW, ClosingStatus.CLOSING, True),
        (ClosingStatus.LOCKED, ClosingStatus.OPEN, True),
        (ClosingStatus.LOCKED, ClosingStatus.CLOSED, False),
        (ClosingStatus.CLOSING, ClosingStatus.CLOSED, True),
        (ClosingStatus.CLOSED, ClosingStatus.OPEN, False),
    ],
)
def test_period_status_transitions(
    source: ClosingStatus, target: ClosingStatus, allowed: bool
) -> None:
    assert source.can_transition_to(target) is allowed
    if not allowed:
        with pytest.raises(ValueError):
            _period(source).with_status(target)


def test_with_status_returns_new_period() -> None:
    period = _period()
    locked = period.with_status(ClosingStatus.LOCKED)
    assert locked.status is ClosingStatus.LOCKED
    assert period.status is ClosingStatus.OPEN
