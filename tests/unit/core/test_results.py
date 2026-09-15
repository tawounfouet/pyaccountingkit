"""Unit tests for the Result monadic container."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.results import Result


def test_ok_result() -> None:
    result: Result[int, str] = Result.ok(42)
    assert result.is_ok
    assert not result.is_err
    assert result.value() == 42
    assert result.unwrap() == 42


def test_err_result() -> None:
    result: Result[int, str] = Result.err("boom")
    assert result.is_err
    assert result.error() == "boom"


def test_unwrap_raises_on_error_result() -> None:
    result: Result[int, str] = Result.err("boom")
    with pytest.raises(RuntimeError, match="boom"):
        result.unwrap()


def test_unwrap_or_returns_default_on_error() -> None:
    result: Result[int, str] = Result.err("boom")
    assert result.unwrap_or(0) == 0
    assert Result.ok(9).unwrap_or(0) == 9


def test_map_transforms_success_path() -> None:
    result: Result[int, str] = Result.ok(21)
    doubled = result.map(lambda value: value * 2)
    assert doubled == Result.ok(42)


def test_map_keeps_error_path() -> None:
    result: Result[int, str] = Result.err("boom")
    mapped = result.map(lambda value: value * 2)
    assert mapped.is_err
    assert mapped.error() == "boom"


def test_map_err_transforms_error_path() -> None:
    result: Result[int, str] = Result.err("boom")
    assert result.map_err(lambda error: len(error)) == Result.err(4)


def test_constructor_rejects_value_and_error_together() -> None:
    with pytest.raises(ValueError):
        Result(42, error="boom")  # type: ignore[arg-type]


def test_repr() -> None:
    assert repr(Result.ok(1)) == "Result.ok(1)"
    assert repr(Result.err("e")) == "Result.err('e')"
