"""Versioned public compatibility contracts for adapter authors."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from sys import version_info

from pyaccountingkit.public.errors import (
    AdapterContractMismatchError,
    OptionalDependencyMissingError,
)


@dataclass(frozen=True, slots=True, order=True)
class AdapterContractVersion:
    """Opaque major version of the public adapter-author contract."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.isascii() or not self.value.isdigit() or not self.value:
            raise ValueError("adapter contract version must be a non-empty ASCII integer")
        if self.value.startswith("0") and self.value != "0":
            raise ValueError("adapter contract version must use canonical integer spelling")

    def __str__(self) -> str:
        return self.value


ADAPTER_CONTRACT_VERSION = AdapterContractVersion("1")
SUPPORTED_ADAPTER_CONTRACT_VERSIONS = (ADAPTER_CONTRACT_VERSION,)


@dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    """Capabilities visible without importing optional framework integrations."""

    adapter_contract_version: AdapterContractVersion
    python_version: str
    django_available: bool
    sqlalchemy_available: bool
    py_typed: bool


def runtime_capabilities() -> RuntimeCapabilities:
    """Detect optional integration availability without importing those frameworks."""

    package_root = Path(__file__).resolve().parents[1]
    return RuntimeCapabilities(
        adapter_contract_version=ADAPTER_CONTRACT_VERSION,
        python_version=f"{version_info.major}.{version_info.minor}.{version_info.micro}",
        django_available=importlib.util.find_spec("django") is not None,
        sqlalchemy_available=importlib.util.find_spec("sqlalchemy") is not None,
        py_typed=(package_root / "py.typed").is_file(),
    )


def require_adapter_contract(
    adapter_name: str,
    supported_versions: tuple[str, ...],
) -> AdapterContractVersion:
    """Return the active contract when the adapter explicitly supports it."""

    current = str(ADAPTER_CONTRACT_VERSION)
    if current not in supported_versions:
        raise AdapterContractMismatchError(
            adapter_name=adapter_name,
            required_version=current,
            supported_versions=supported_versions,
        )
    return ADAPTER_CONTRACT_VERSION


def require_optional_dependency(*, extra: str, module: str) -> None:
    """Fail with a stable public error when an explicitly requested extra is unavailable."""

    if importlib.util.find_spec(module) is None:
        raise OptionalDependencyMissingError(extra=extra, module=module)


__all__ = [
    "ADAPTER_CONTRACT_VERSION",
    "SUPPORTED_ADAPTER_CONTRACT_VERSIONS",
    "AdapterContractVersion",
    "RuntimeCapabilities",
    "require_adapter_contract",
    "require_optional_dependency",
    "runtime_capabilities",
]
