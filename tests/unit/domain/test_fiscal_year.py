"""Unit tests for FiscalYear and its deterministic period decomposition."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

import pytest

from pyaccountingkit.core.identifiers import EntityId, FiscalYearId
from pyaccountingkit.domain.identity.fiscal_year import FiscalYear


def _fiscal_year() -> FiscalYear:
    return FiscalYear(
        id=FiscalYearId("fy_2024"),
        entity_id=EntityId("ent_1"),
        label="Exercice 2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )


def test_fiscal_year_bounds_and_scope() -> None:
    year = _fiscal_year()
    assert year.entity_id == EntityId("ent_1")
    assert year.contains(date(2024, 6, 15))
    assert not year.contains(date(2025, 1, 1))


def test_fiscal_year_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError):
        FiscalYear(
            id=FiscalYearId("fy_bad"),
            entity_id=EntityId("ent_1"),
            label="bad",
            start_date=date(2025, 1, 1),
            end_date=date(2024, 1, 1),
        )


def test_default_period_covers_whole_year() -> None:
    year = _fiscal_year()
    period = year.default_period()
    assert period.start_date == year.start_date
    assert period.end_date == year.end_date
    assert period.fiscal_year_id == year.id


def test_monthly_periods_are_deterministic_and_cover_the_year() -> None:
    year = _fiscal_year()
    periods = year.monthly_periods()
    assert len(periods) == 12
    assert periods[0].start_date == date(2024, 1, 1)
    assert periods[0].end_date == date(2024, 1, 31)
    assert periods[-1].end_date == date(2024, 12, 31)
    for current, following in pairwise(periods):
        assert current.end_date + timedelta(days=1) == following.start_date


def test_monthly_periods_trim_edges_of_a_partial_year() -> None:
    year = FiscalYear(
        id=FiscalYearId("fy_2024"),
        entity_id=EntityId("ent_1"),
        label="2024 partiel",
        start_date=date(2024, 6, 5),
        end_date=date(2024, 9, 20),
    )
    periods = year.monthly_periods()
    assert [period.start_date for period in periods] == [
        date(2024, 6, 5),
        date(2024, 7, 1),
        date(2024, 8, 1),
        date(2024, 9, 1),
    ]
    assert [period.end_date for period in periods] == [
        date(2024, 6, 30),
        date(2024, 7, 31),
        date(2024, 8, 31),
        date(2024, 9, 20),
    ]
