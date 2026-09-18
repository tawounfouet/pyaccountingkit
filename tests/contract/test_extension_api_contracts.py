"""LOT-22 extension API and compatibility contract qualification."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import pyaccountingkit
from pyaccountingkit.public.errors import (
    AdapterContractMismatchError,
    OptionalDependencyMissingError,
)
from pyaccountingkit.public.protocols import (
    ADAPTER_CONTRACT_VERSION,
    SUPPORTED_ADAPTER_CONTRACT_VERSIONS,
    AccountingReferenceProviderProtocol,
    AdapterContractVersion,
    RegulatoryExporterProtocol,
    RegulatoryRendererProtocol,
    RuntimeCapabilities,
    UnitOfWorkFactoryProtocol,
    UnitOfWorkProtocol,
    require_adapter_contract,
    require_optional_dependency,
    runtime_capabilities,
)

ROOT = Path(__file__).resolve().parents[2]


def test_extension_api_is_separate_from_root_user_api() -> None:
    extension_symbols = {
        "AdapterContractVersion",
        "UnitOfWorkFactoryProtocol",
        "AccountingReferenceProviderProtocol",
        "RegulatoryRendererProtocol",
        "RegulatoryExporterProtocol",
    }
    assert extension_symbols.isdisjoint(pyaccountingkit.__all__)


def test_extension_api_symbol_list_is_explicit() -> None:
    from pyaccountingkit.public import protocols

    expected = {
        "ADAPTER_CONTRACT_VERSION",
        "SUPPORTED_ADAPTER_CONTRACT_VERSIONS",
        "AccountingReferenceProviderProtocol",
        "AdapterContractVersion",
        "RegulatoryExporterProtocol",
        "RegulatoryRendererProtocol",
        "RuntimeCapabilities",
        "UnitOfWorkFactoryProtocol",
        "UnitOfWorkProtocol",
        "require_adapter_contract",
        "require_optional_dependency",
        "runtime_capabilities",
    }
    assert set(protocols.__all__) == expected


def test_adapter_contract_version_one_is_canonical() -> None:
    assert str(ADAPTER_CONTRACT_VERSION) == "1"
    assert SUPPORTED_ADAPTER_CONTRACT_VERSIONS == (AdapterContractVersion("1"),)
    with pytest.raises(ValueError):
        AdapterContractVersion("01")
    with pytest.raises(ValueError):
        AdapterContractVersion("v1")


def test_adapter_contract_accepts_explicit_v1_support() -> None:
    assert require_adapter_contract("custom", ("1",)) == ADAPTER_CONTRACT_VERSION


def test_adapter_contract_mismatch_is_typed_and_machine_readable() -> None:
    with pytest.raises(AdapterContractMismatchError) as raised:
        require_adapter_contract("legacy", ("0",))
    assert raised.value.code == "ADAPTER_CONTRACT_MISMATCH"
    assert raised.value.to_info().details == {
        "adapter_name": "legacy",
        "required_version": "1",
        "supported_versions": ("0",),
    }


def test_runtime_capabilities_are_immutable_and_do_not_import_optional_orms() -> None:
    before = {name for name in ("django", "sqlalchemy") if name in sys.modules}
    capabilities = runtime_capabilities()
    after = {name for name in ("django", "sqlalchemy") if name in sys.modules}

    assert isinstance(capabilities, RuntimeCapabilities)
    assert capabilities.adapter_contract_version == ADAPTER_CONTRACT_VERSION
    assert capabilities.py_typed is True
    assert after == before
    with pytest.raises(FrozenInstanceError):
        capabilities.py_typed = False  # type: ignore[misc]


def test_missing_optional_dependency_raises_typed_error() -> None:
    with pytest.raises(OptionalDependencyMissingError) as raised:
        require_optional_dependency(
            extra="missing-test-extra",
            module="pyaccountingkit_dependency_that_does_not_exist",
        )
    assert raised.value.code == "OPTIONAL_DEPENDENCY_MISSING"
    assert raised.value.to_info().details == {
        "extra": "missing-test-extra",
        "module": "pyaccountingkit_dependency_that_does_not_exist",
    }


def test_public_protocols_are_framework_neutral_types() -> None:
    assert UnitOfWorkProtocol.__module__.startswith("pyaccountingkit.")
    assert UnitOfWorkFactoryProtocol.__module__ == "pyaccountingkit.public.protocols.unit_of_work"
    assert (
        AccountingReferenceProviderProtocol.__module__
        == "pyaccountingkit.public.protocols.references"
    )
    assert RegulatoryRendererProtocol.__module__ == "pyaccountingkit.public.protocols.reporting"
    assert RegulatoryExporterProtocol.__module__ == "pyaccountingkit.public.protocols.reporting"
