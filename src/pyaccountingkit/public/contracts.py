"""Typed, adapter-neutral operational contracts for the public facade."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from pyaccountingkit.public.context import CommandContext


class PublicOperationKind(StrEnum):
    """Stable public operation classification."""

    COMMAND = "COMMAND"
    QUERY = "QUERY"


class PublicContextPolicy(StrEnum):
    """Whether caller context is accepted or mandatory."""

    OPTIONAL = "OPTIONAL"
    REQUIRED = "REQUIRED"


@dataclass(frozen=True, slots=True)
class PublicOperationRequest:
    """Immutable adapter-neutral request envelope used by the public boundary."""

    parameters: Mapping[str, object] = field(default_factory=dict)
    context: CommandContext | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class PublicOperationContract:
    """Executable contract metadata for one public facade operation."""

    namespace: str
    operation: str
    kind: PublicOperationKind
    request_type: type[PublicOperationRequest] = PublicOperationRequest
    response_contract: str = "framework-neutral-object"
    context_policy: PublicContextPolicy = PublicContextPolicy.OPTIONAL
    boundary_error_codes: tuple[str, ...] = (
        "PUBLIC_OPERATION_UNAVAILABLE",
        "PUBLIC_BOUNDARY_VIOLATION",
        "PUBLIC_INFRASTRUCTURE_FAILURE",
    )

    @property
    def key(self) -> str:
        return f"{self.namespace}.{self.operation}"


def _contract(
    namespace: str,
    operation: str,
    kind: PublicOperationKind,
) -> PublicOperationContract:
    return PublicOperationContract(namespace=namespace, operation=operation, kind=kind)


_COMMANDS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "references": (
            "create_snapshot",
            "require_not_forbidden",
            "require_auto_inference_allowed",
        ),
        "charts": (
            "create",
            "generate_from_reference",
            "add_account",
            "activate_account",
            "deactivate_account",
            "bind_reference",
            "validate",
            "activate",
            "migrate",
        ),
        "entries": (
            "create",
            "add_line",
            "remove_line",
            "validate",
            "post",
            "reverse",
        ),
        "closing": (
            "start_review",
            "generate_adjustments",
            "validate",
            "close",
            "reopen",
            "create_snapshot",
        ),
        "controls": ("run", "evaluate", "gate"),
        "imports": (
            "create",
            "preflight",
            "discover",
            "map_account",
            "map_journal",
            "validate",
            "build_plan",
            "approve",
            "execute",
            "reprocess",
        ),
        "statements": ("build", "preview", "snapshot", "publish"),
        "reporting": (
            "create_profile",
            "activate_profile",
            "build_report",
            "validate_report",
            "export",
            "plan_upgrade",
        ),
        "analysis": (
            "define_indicator",
            "define_ratio",
            "create_definition_set",
            "activate_definition_set",
            "run",
            "snapshot",
        ),
        "subledgers.partners": ("create",),
        "subledgers.receivables": ("recognize",),
        "subledgers.payables": ("recognize",),
        "subledgers.settlements": ("record", "allocate", "reverse"),
        "subledgers.matching": ("suggest", "validate"),
        "subledgers": ("reconcile",),
    }
)

_QUERIES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "references": (
            "get_standard",
            "list_standards",
            "get_structure",
            "get_effective_plan",
            "get_reporting_model",
            "relations_for",
            "can_auto_infer",
        ),
        "charts": ("get", "search_accounts"),
        "entries": ("get", "list"),
        "ledger": (
            "journal",
            "general_ledger",
            "trial_balance",
            "account_balance",
            "entry_history",
            "snapshot_trial_balance",
        ),
        "closing": ("status",),
        "controls": ("get_run", "list_findings"),
        "imports": ("trace",),
        "statements": ("drilldown", "compare"),
        "reporting": (),
        "analysis": ("drilldown", "trend", "diagnostic"),
        "subledgers.partners": ("get", "list"),
        "subledgers.receivables": ("get", "list_open"),
        "subledgers.payables": ("get", "list_open"),
        "subledgers.settlements": (),
        "subledgers.matching": (),
        "subledgers": ("aging",),
    }
)


def _build_contracts() -> Mapping[str, PublicOperationContract]:
    contracts: dict[str, PublicOperationContract] = {}
    for namespace, operations in _COMMANDS.items():
        for operation in operations:
            contract = _contract(namespace, operation, PublicOperationKind.COMMAND)
            contracts[contract.key] = contract
    for namespace, operations in _QUERIES.items():
        for operation in operations:
            contract = _contract(namespace, operation, PublicOperationKind.QUERY)
            if contract.key in contracts:
                raise RuntimeError(f"duplicate public operation contract: {contract.key}")
            contracts[contract.key] = contract
    return MappingProxyType(dict(sorted(contracts.items())))


PUBLIC_OPERATION_CONTRACTS = _build_contracts()


def public_operation_contract(namespace: str, operation: str) -> PublicOperationContract:
    """Resolve one required public operation contract, failing closed if absent."""

    key = f"{namespace}.{operation}"
    try:
        return PUBLIC_OPERATION_CONTRACTS[key]
    except KeyError as exc:
        raise RuntimeError(f"public operation contract is missing: {key}") from exc


__all__ = [
    "PUBLIC_OPERATION_CONTRACTS",
    "PublicContextPolicy",
    "PublicOperationContract",
    "PublicOperationKind",
    "PublicOperationRequest",
    "public_operation_contract",
]
