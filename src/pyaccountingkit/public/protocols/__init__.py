"""Versioned public extension API for adapter authors."""

from pyaccountingkit.public.protocols.compatibility import (
    ADAPTER_CONTRACT_VERSION,
    SUPPORTED_ADAPTER_CONTRACT_VERSIONS,
    AdapterContractVersion,
    RuntimeCapabilities,
    require_adapter_contract,
    require_optional_dependency,
    runtime_capabilities,
)
from pyaccountingkit.public.protocols.references import AccountingReferenceProviderProtocol
from pyaccountingkit.public.protocols.reporting import (
    RegulatoryExporterProtocol,
    RegulatoryRendererProtocol,
)
from pyaccountingkit.public.protocols.unit_of_work import (
    UnitOfWorkFactoryProtocol,
    UnitOfWorkProtocol,
)

__all__ = [
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
]
