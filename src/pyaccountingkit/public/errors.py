"""Stable-shaped, machine-readable errors for the public facade."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class PublicErrorInfo:
    """Serializable public error description."""

    code: str
    message: str
    retryable: bool
    details: Mapping[str, object]


class PyAccountingKitError(Exception):
    """Root exception exposed by the public API."""

    code = "PYACCOUNTINGKIT_ERROR"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = MappingProxyType(dict(context or {}))

    def to_info(self) -> PublicErrorInfo:
        """Return a framework-neutral machine-readable view."""

        return PublicErrorInfo(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            details=self.context,
        )


class PublicAccountingError(PyAccountingKitError):
    """Base class for errors produced directly by the public boundary."""

    code = "PUBLIC_ERROR"


class PublicOperationUnavailableError(PublicAccountingError):
    """The selected composition root does not provide an advertised operation."""

    code = "PUBLIC_OPERATION_UNAVAILABLE"

    def __init__(self, namespace: str, operation: str) -> None:
        super().__init__(
            f"public operation {namespace}.{operation} is not configured",
            context={"namespace": namespace, "operation": operation},
        )


class PublicBoundaryViolationError(PublicAccountingError):
    """An infrastructure-specific object attempted to cross the public boundary."""

    code = "PUBLIC_BOUNDARY_VIOLATION"

    def __init__(self, object_type: str) -> None:
        super().__init__(
            "framework-specific object cannot cross the public API boundary",
            context={"object_type": object_type},
        )


class PublicValidationError(PublicAccountingError):
    """A public request or response shape is invalid before domain execution."""

    code = "PUBLIC_VALIDATION_ERROR"


class AdapterContractMismatchError(PublicAccountingError):
    """An adapter does not declare support for the active extension contract."""

    code = "ADAPTER_CONTRACT_MISMATCH"

    def __init__(
        self,
        *,
        adapter_name: str,
        required_version: str,
        supported_versions: tuple[str, ...],
    ) -> None:
        super().__init__(
            f"adapter {adapter_name!r} does not support contract version {required_version}",
            context={
                "adapter_name": adapter_name,
                "required_version": required_version,
                "supported_versions": supported_versions,
            },
        )


class OptionalDependencyMissingError(PublicAccountingError):
    """An explicitly requested optional integration dependency is unavailable."""

    code = "OPTIONAL_DEPENDENCY_MISSING"

    def __init__(self, *, extra: str, module: str) -> None:
        super().__init__(
            f"optional dependency {module!r} is required by extra {extra!r}",
            context={"extra": extra, "module": module},
        )


__all__ = [
    "AdapterContractMismatchError",
    "OptionalDependencyMissingError",
    "PublicAccountingError",
    "PublicBoundaryViolationError",
    "PublicErrorInfo",
    "PublicOperationUnavailableError",
    "PublicValidationError",
    "PyAccountingKitError",
]
