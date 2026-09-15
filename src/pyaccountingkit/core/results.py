"""Monadic error-handling primitive for pure domain flows.

``Result[T, E]`` transports either a success value or a typed error without
relying on exceptions for expected control flow.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar, final

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@final
class Result(Generic[T, E]):
    """Immutable success-or-error container.

    Exactly one of the success value or the error may be set.
    """

    __slots__ = ("_ok", "_value", "_error")

    def __init__(self, value: T | None = None, error: E | None = None) -> None:
        if value is not None and error is not None:
            raise ValueError("Result cannot carry both a value and an error")
        self._ok = error is None
        self._value = value
        self._error = error

    @classmethod
    def ok(cls, value: T) -> Result[T, E]:
        """Build a success result."""
        return cls(value)

    @classmethod
    def err(cls, error: E) -> Result[T, E]:
        """Build an error result."""
        return cls(error=error)

    @property
    def is_ok(self) -> bool:
        return self._ok

    @property
    def is_err(self) -> bool:
        return not self._ok

    def value(self) -> T | None:
        """Return the contained success value (``None`` on an error result)."""
        return self._value

    def error(self) -> E | None:
        """Return the contained error (``None`` on a success result)."""
        return self._error

    def _required_value(self) -> T:
        if self._value is None:
            raise RuntimeError("Result success invariant violated: missing value")
        return self._value

    def _required_error(self) -> E:
        if self._error is None:
            raise RuntimeError("Result error invariant violated: missing error")
        return self._error

    def unwrap(self) -> T:
        """Return the success value or raise ``RuntimeError``."""
        if not self._ok:
            message = self._error if self._error is not None else "unknown error"
            raise RuntimeError(f"Called unwrap() on an error Result: {message}")
        return self._required_value()

    def unwrap_or(self, default: T) -> T:
        """Return the success value or ``default`` on an error result."""
        if self._ok:
            return self._required_value()
        return default

    def map(self, transform: Callable[[T], U]) -> Result[U, E]:
        """Apply ``transform`` to the success value, keeping the error path intact."""
        if self._ok:
            return Result.ok(transform(self._required_value()))
        return Result.err(self._required_error())

    def map_err(self, transform: Callable[[E], U]) -> Result[T, U]:
        """Apply ``transform`` to the error, keeping the success path intact."""
        if self._ok:
            return Result.ok(self._required_value())
        return Result.err(transform(self._required_error()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return self._ok == other._ok and self._value == other._value and self._error == other._error

    def __hash__(self) -> int:
        return hash((self._ok, self._value, self._error))

    def __repr__(self) -> str:
        if self._ok:
            return f"Result.ok({self._value!r})"
        return f"Result.err({self._error!r})"


__all__ = ["Result"]
