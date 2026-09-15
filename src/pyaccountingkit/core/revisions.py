"""Optimistic-concurrency revision value objects."""

from __future__ import annotations

from dataclasses import dataclass

INITIAL_REVISION = 0


@dataclass(frozen=True, slots=True)
class Revision:
    """Monotonic version counter guarding optimistic mutations."""

    value: int = INITIAL_REVISION

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"Revision cannot be negative: {self.value}")

    def incremented(self) -> Revision:
        """Return the next revision without mutating this one."""
        return Revision(self.value + 1)

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


__all__ = ["Revision", "INITIAL_REVISION"]
