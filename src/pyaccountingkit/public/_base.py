"""Internal delegation machinery for the framework-neutral public facade."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence, Set
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import cast

from pyaccountingkit.public.context import CommandContext
from pyaccountingkit.public.contracts import (
    PublicOperationRequest,
    public_operation_contract,
)
from pyaccountingkit.public.errors import (
    PublicBoundaryViolationError,
    PublicOperationUnavailableError,
    translate_public_exception,
)

_FORBIDDEN_FRAMEWORK_PREFIXES = ("django", "sqlalchemy")


def _has_forbidden_framework_ancestry(value: object) -> bool:
    value_type = type(value)
    return any(
        cls.__module__.split(".", maxsplit=1)[0] in _FORBIDDEN_FRAMEWORK_PREFIXES
        for cls in value_type.__mro__
    )


def ensure_framework_neutral(value: object, *, _seen: set[int] | None = None) -> None:
    """Reject ORM/framework objects anywhere in a public object graph."""

    if value is None or isinstance(value, (str, bytes, int, float, bool, Enum)):
        return
    if _has_forbidden_framework_ancestry(value):
        qualified = f"{type(value).__module__}.{type(value).__qualname__}"
        raise PublicBoundaryViolationError(qualified)

    seen = _seen if _seen is not None else set()
    identity = id(value)
    if identity in seen:
        return
    seen.add(identity)

    if isinstance(value, Iterator):
        qualified = f"{type(value).__module__}.{type(value).__qualname__}"
        raise PublicBoundaryViolationError(qualified)

    if isinstance(value, Mapping):
        for key, item in value.items():
            ensure_framework_neutral(key, _seen=seen)
            ensure_framework_neutral(item, _seen=seen)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            ensure_framework_neutral(item, _seen=seen)
        return
    if isinstance(value, Set):
        for item in value:
            ensure_framework_neutral(item, _seen=seen)
        return
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            ensure_framework_neutral(getattr(value, field.name), _seen=seen)
        return

    try:
        attributes = vars(value)
    except TypeError:
        attributes = {}
    for item in attributes.values():
        ensure_framework_neutral(item, _seen=seen)

    for value_type in type(value).__mro__:
        slots = value_type.__dict__.get("__slots__", ())
        if isinstance(slots, str):
            slot_names = (slots,)
        else:
            slot_names = slots
        for slot_name in slot_names:
            if slot_name in {"__dict__", "__weakref__"}:
                continue
            try:
                item = object.__getattribute__(value, slot_name)
            except AttributeError:
                continue
            ensure_framework_neutral(item, _seen=seen)


class PublicNamespace:
    """Explicit public namespace delegating into an application-layer service."""

    __slots__ = ("_namespace", "_service")

    def __init__(self, namespace: str, service: object | None) -> None:
        self._namespace = namespace
        self._service = service

    def _invoke(
        self,
        operation: str,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        public_operation_contract(self._namespace, operation)
        request = PublicOperationRequest(parameters=parameters, context=context)
        ensure_framework_neutral(request)

        if self._service is None:
            raise PublicOperationUnavailableError(self._namespace, operation)
        candidate = getattr(self._service, operation, None)
        if not callable(candidate):
            raise PublicOperationUnavailableError(self._namespace, operation)

        call = cast(Callable[..., object], candidate)
        call_parameters = dict(request.parameters)
        if request.context is not None:
            call_parameters["context"] = request.context
        try:
            result = call(**call_parameters)
        except Exception as exc:
            translated = translate_public_exception(exc)
            if translated is None or translated is exc:
                raise
            raise translated from exc
        ensure_framework_neutral(result)
        return result

    def _child_service(self, name: str) -> object | None:
        if self._service is None:
            return None
        return getattr(self._service, name, None)


__all__ = ["PublicNamespace", "ensure_framework_neutral"]
