"""Immutable cursor-first pagination primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, NewType, TypeVar

from pyaccountingkit.public.errors import PublicValidationError

Cursor = NewType("Cursor", str)
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """One immutable page of framework-neutral public results."""

    items: tuple[T, ...]
    page_size: int
    total: int | None = None
    next_cursor: Cursor | None = None
    previous_cursor: Cursor | None = None

    def __post_init__(self) -> None:
        if self.page_size <= 0:
            raise PublicValidationError(
                "page_size must be strictly positive",
                context={"page_size": self.page_size},
            )
        if len(self.items) > self.page_size:
            raise PublicValidationError(
                "items cannot exceed page_size",
                context={"items": len(self.items), "page_size": self.page_size},
            )
        if self.total is not None and self.total < 0:
            raise PublicValidationError(
                "total must be non-negative",
                context={"total": self.total},
            )


__all__ = ["Cursor", "Page"]
