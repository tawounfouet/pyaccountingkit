"""Deep-immutability helpers for durable evidence and sealed snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

K = TypeVar("K")
V = TypeVar("V")


class FrozenDict(dict[K, V]):
    """A JSON-compatible dict that rejects every mutating operation."""

    def _immutable(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("FrozenDict is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


class FrozenList(list[V]):
    """A JSON-compatible list that rejects every mutating operation."""

    def _immutable(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("FrozenList is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable


def deep_freeze(value: Any) -> Any:
    """Return a detached recursively immutable copy preserving JSON shapes."""
    if isinstance(value, FrozenDict | FrozenList):
        return value
    if isinstance(value, Mapping):
        return FrozenDict(
            (deep_freeze(key), deep_freeze(item))
            for key, item in value.items()
        )
    if isinstance(value, list):
        return FrozenList(deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(deep_freeze(item) for item in value)
    if isinstance(value, frozenset):
        return frozenset(deep_freeze(item) for item in value)
    return value


def freeze_mapping(mapping: Mapping[K, V]) -> Mapping[K, V]:
    """Detach and recursively freeze one mapping."""
    return cast(Mapping[K, V], deep_freeze(mapping))


__all__ = ["FrozenDict", "FrozenList", "deep_freeze", "freeze_mapping"]
