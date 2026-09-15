"""Unit tests for the injectable clocks."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pyaccountingkit.core.clock import ClockProtocol, FrozenClock, SystemClock


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(None)


def test_frozen_clock_is_deterministic() -> None:
    clock = FrozenClock()
    assert clock.now() == clock.now() == datetime(2024, 1, 1, tzinfo=UTC)


def test_frozen_clock_accepts_explicit_fixed_time() -> None:
    fixed = datetime(2025, 6, 15, 10, 30, tzinfo=UTC)
    assert FrozenClock(fixed).now() == fixed


def test_frozen_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        FrozenClock(datetime(2024, 1, 1))


def test_clock_protocol_is_satisfied_by_both_implementations() -> None:
    providers: list[ClockProtocol] = [SystemClock(), FrozenClock()]
    for provider in providers:
        assert provider.now().tzinfo is not None
