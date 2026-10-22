"""Property qualification for conservative reporting monetary allocations."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.core.currency import EUR, XAF, Currency
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.allocation import allocate_money_conservatively


_PARTITIONS = st.sampled_from(
    (
        (("a", Decimal("0.5")), ("b", Decimal("0.5"))),
        (
            ("a", Decimal("0.3333")),
            ("b", Decimal("0.3333")),
            ("c", Decimal("0.3334")),
        ),
        (
            ("a", Decimal("0.10")),
            ("b", Decimal("0.20")),
            ("c", Decimal("0.70")),
        ),
    )
)


@given(
    minor_units=st.integers(min_value=-10_000, max_value=10_000),
    currency=st.sampled_from((EUR, XAF)),
    partition=_PARTITIONS,
)
def test_reporting_allocation_conserves_every_minor_unit(
    minor_units: int,
    currency: Currency,
    partition: tuple[tuple[str, Decimal], ...],
) -> None:
    source = Money(Decimal(minor_units) * currency.subunit_exp, currency)

    allocated = allocate_money_conservatively(source, partition)

    total = Money.zero(currency)
    for contribution in allocated.values():
        total += contribution
    assert total == source


@given(
    minor_units=st.integers(min_value=-100, max_value=100),
    currency=st.sampled_from((EUR, XAF)),
    partition=_PARTITIONS,
)
def test_reporting_allocation_is_independent_from_mapping_input_order(
    minor_units: int,
    currency: Currency,
    partition: tuple[tuple[str, Decimal], ...],
) -> None:
    source = Money(Decimal(minor_units) * currency.subunit_exp, currency)

    forward = allocate_money_conservatively(source, partition)
    reversed_order = allocate_money_conservatively(source, tuple(reversed(partition)))

    assert forward == reversed_order


def test_one_cent_split_fifty_fifty_never_creates_a_second_cent() -> None:
    allocated = allocate_money_conservatively(
        Money.from_str("0.01", EUR),
        (("a", Decimal("0.5")), ("b", Decimal("0.5"))),
    )

    assert allocated == {
        "a": Money.from_str("0.01", EUR),
        "b": Money.zero(EUR),
    }


def test_negative_one_cent_split_is_conservative() -> None:
    allocated = allocate_money_conservatively(
        Money.from_str("-0.01", EUR),
        (("a", Decimal("0.5")), ("b", Decimal("0.5"))),
    )

    assert allocated == {
        "a": Money.from_str("-0.01", EUR),
        "b": Money.zero(EUR),
    }
