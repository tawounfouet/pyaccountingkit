"""Property qualification for LOT-28R conservative monetary allocation."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.monetary_allocation import (
    allocate_money_conservatively,
)


@given(
    cents=st.integers(min_value=-1_000_000, max_value=1_000_000),
    left_basis_points=st.integers(min_value=1, max_value=9_999),
)
def test_two_way_allocation_preserves_source_and_is_order_stable(
    cents: int,
    left_basis_points: int,
) -> None:
    source = Money(Decimal(cents) / Decimal("100"), EUR)
    left = Decimal(left_basis_points) / Decimal("10000")
    right = Decimal("1") - left
    forward = (("left", left), ("right", right))
    reverse = tuple(reversed(forward))

    first = allocate_money_conservatively(source, forward)
    second = allocate_money_conservatively(source, reverse)

    assert first == second
    assert sum(first.values(), Money.zero(EUR)) == source
