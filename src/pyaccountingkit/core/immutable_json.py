"""Deeply immutable JSON-like evidence payload helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import cast


_JSON_SCALARS = (str, int, float, bool, type(None))


def freeze_json_value(value: object) -> object:
    """Return a detached deeply immutable representation of one JSON-like value."""
    if isinstance(value, _JSON_SCALARS):
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON evidence mapping keys must be strings")
            frozen[key] = freeze_json_value(item)
        return MappingProxyType(frozen)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(freeze_json_value(item) for item in value)
    raise TypeError(f"Unsupported JSON evidence value: {type(value).__name__}")


def freeze_json_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    """Detach and deeply freeze a JSON-like mapping."""
    frozen = freeze_json_value(value)
    return cast(Mapping[str, object], frozen)


def thaw_json_value(value: object) -> object:
    """Return a JSON-serializable mutable representation of frozen evidence."""
    if isinstance(value, Mapping):
        return {str(key): thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_json_value(item) for item in value]
    if isinstance(value, _JSON_SCALARS):
        return value
    raise TypeError(f"Unsupported frozen JSON evidence value: {type(value).__name__}")


def thaw_json_mapping(value: Mapping[str, object]) -> dict[str, object]:
    """Materialize deeply frozen evidence for a JSON persistence adapter."""
    thawed = thaw_json_value(value)
    if not isinstance(thawed, dict):
        raise TypeError("Frozen JSON evidence root must be a mapping")
    return thawed


__all__ = [
    "freeze_json_mapping",
    "freeze_json_value",
    "thaw_json_mapping",
    "thaw_json_value",
]
