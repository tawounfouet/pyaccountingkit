"""Deep-immutability helpers for durable evidence and sealed snapshots."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Generic, TypeVar, cast, overload

K = TypeVar("K")
V = TypeVar("V")


class FrozenDict(Mapping[K, V], Generic[K, V]):
    """Detached immutable mapping."""

    __slots__ = ("_data",)

    def __init__(self, values: Mapping[K, V]) -> None:
        self._data = dict(values)

    def __getitem__(self, key: K) -> V:
        return self._data[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return repr(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other.items())
        return False


class FrozenList(Sequence[V], Generic[V]):
    """Detached immutable sequence preserving list-style equality/repr."""

    __slots__ = ("_items",)

    def __init__(self, values: Sequence[V]) -> None:
        self._items = tuple(values)

    @overload
    def __getitem__(self, index: int) -> V: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[V]: ...

    def __getitem__(self, index: int | slice) -> V | Sequence[V]:
        return self._items[index]

    def _immutable(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("FrozenList is immutable")

    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[V]:
        return iter(self._items)

    def __repr__(self) -> str:
        return repr(list(self._items))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence) and not isinstance(other, str | bytes | bytearray):
            return tuple(self._items) == tuple(other)
        return False


def deep_freeze(value: Any) -> Any:
    """Return a detached recursively immutable copy."""
    if isinstance(value, FrozenDict | FrozenList):
        return value
    if isinstance(value, Mapping):
        frozen = {deep_freeze(key): deep_freeze(item) for key, item in value.items()}
        return FrozenDict(frozen)
    if isinstance(value, list):
        return FrozenList([deep_freeze(item) for item in value])
    if isinstance(value, tuple):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(deep_freeze(item) for item in value)
    return value


def deep_thaw(value: Any) -> Any:
    """Convert immutable wrappers into ordinary JSON-compatible containers."""
    if isinstance(value, Mapping):
        return {deep_thaw(key): deep_thaw(item) for key, item in value.items()}
    if isinstance(value, FrozenList):
        return [deep_thaw(item) for item in value]
    if isinstance(value, tuple):
        return [deep_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return [deep_thaw(item) for item in sorted(value, key=repr)]
    return value


def freeze_mapping(mapping: Mapping[K, V]) -> Mapping[K, V]:
    """Detach and recursively freeze one mapping."""
    return cast(Mapping[K, V], deep_freeze(mapping))


__all__ = ["FrozenDict", "FrozenList", "deep_freeze", "deep_thaw", "freeze_mapping"]
