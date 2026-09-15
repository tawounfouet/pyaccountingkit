"""Company chart generation from a resolved reference plan (LOT-11).

Generation strategies are explicit: ``REFERENCE_ONLY`` is the prudent default,
``PAD_TO_LENGTH`` only applies when the explicit policy allows it, and
``TEMPLATE_EXPANSION`` uses an explicit template (ADR COA-012/013, spec
sections 46-52 of the chart architecture).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.numbering import (
    AccountCodeContext,
    AccountCodeGenerationRequest,
    AccountCodePolicy,
)
from pyaccountingkit.domain.charts.regulatory_binding import (
    BindingPurpose,
    ChartBindingRegistry,
    MappingCandidate,
    RegulatoryAccountBinding,
)
from pyaccountingkit.domain.references.hierarchy import ReferenceNode
from pyaccountingkit.domain.references.standards import ReferenceNodeType, StandardType
from pyaccountingkit.ports.references import AccountingReferenceProviderProtocol

_GENERATED_ACCOUNT = "GENERAL"


class GenerationMode(StrEnum):
    """How a reference code becomes a company account code."""

    REFERENCE_ONLY = "REFERENCE_ONLY"
    PAD_TO_LENGTH = "PAD_TO_LENGTH"
    TEMPLATE_EXPANSION = "TEMPLATE_EXPANSION"


class ReferenceNodeInclusionPolicy(StrEnum):
    """Which resolved reference nodes turn into company accounts."""

    MINIMUM_PLAN_ONLY = "MINIMUM_PLAN_ONLY"
    INCLUDE_ALL_ACCOUNTS = "INCLUDE_ALL_ACCOUNTS"


@dataclass(frozen=True, slots=True)
class CompanyChartGenerationRequest:
    """Declarative inputs for one deterministic chart generation run."""

    entity_id: EntityId
    standard: StandardType
    reference_snapshot_id: str
    edition: str
    mode: GenerationMode = GenerationMode.REFERENCE_ONLY
    code_policy: AccountCodePolicy | None = None
    inclusion: ReferenceNodeInclusionPolicy = ReferenceNodeInclusionPolicy.MINIMUM_PLAN_ONLY
    effective_date: date | None = None
    template: str | None = None
    auto_promote: bool = False


@dataclass(frozen=True, slots=True)
class CompanyChartGenerationResult:
    """Deterministic outcome of a generation run, ready to be persisted."""

    accounts: tuple[CompanyAccount, ...]
    registry: ChartBindingRegistry
    warnings: tuple[str, ...]
    skipped_reference_nodes: tuple[str, ...]

    @property
    def candidates(self) -> tuple[MappingCandidate, ...]:
        return self.registry.candidates()

    @property
    def bindings(self) -> tuple[RegulatoryAccountBinding, ...]:
        return self.registry.bindings()


class CompanyChartGenerator:
    """Generates company accounts + mapping candidates from a reference plan."""

    def __init__(self, provider: AccountingReferenceProviderProtocol) -> None:
        self._provider = provider

    def generate(
        self,
        request: CompanyChartGenerationRequest,
    ) -> CompanyChartGenerationResult:
        hierarchy = self._provider.get_hierarchy(request.standard)
        policy = request.code_policy
        accounts: list[CompanyAccount] = []
        candidates: list[MappingCandidate] = []
        warnings: list[str] = []
        skipped: list[str] = []
        seen_codes: set[str] = set()

        for node in hierarchy.all_nodes():
            if not self._is_materialized(node, request.inclusion):
                continue
            code = self._generate_code(node, request)
            if code is None:
                skipped.append(node.ref_code)
                continue
            if policy is not None:
                result = policy.validate(
                    code,
                    AccountCodeContext(
                        reference_code=node.ref_code,
                        account_kind=_GENERATED_ACCOUNT,
                    ),
                )
                if not result.ok:
                    warnings.append(f"{node.ref_code!r}: code {code!r} invalid")
                    skipped.append(node.ref_code)
                    continue
            if code in seen_codes:
                warnings.append(f"duplicate generated code {code!r} (from {node.ref_code!r})")
                skipped.append(node.ref_code)
                continue
            seen_codes.add(code)
            accounts.append(self._build_account(code, node, request))
            candidates.append(
                MappingCandidate(
                    id=f"candidate:{code}:{node.node_id}",
                    company_account_code=code,
                    reference_node_id=node.node_id,
                    reference_standard_id=request.standard.canonical_id,
                    reference_snapshot_id=request.reference_snapshot_id,
                    reason=f"generated from {node.ref_code}",
                )
            )

        registry = ChartBindingRegistry()
        for candidate in candidates:
            registry = registry.add_candidate(candidate)
        if request.auto_promote:
            for candidate in candidates:
                registry, _ = registry.promote_candidate(
                    candidate,
                    purpose=BindingPurpose.PRIMARY_STATUTORY,
                    effective_from=request.effective_date,
                    provenance="generation",
                )

        return CompanyChartGenerationResult(
            accounts=tuple(accounts),
            registry=registry,
            warnings=tuple(warnings),
            skipped_reference_nodes=tuple(dict.fromkeys(skipped)),
        )

    def _is_materialized(
        self,
        node: ReferenceNode,
        inclusion: ReferenceNodeInclusionPolicy,
    ) -> bool:
        if node.node_type is not ReferenceNodeType.ACCOUNT:
            return False
        if inclusion is ReferenceNodeInclusionPolicy.MINIMUM_PLAN_ONLY:
            return bool(node.attributes.get("is_minimum_plan_account", False))
        return True

    def _generate_code(
        self,
        node: ReferenceNode,
        request: CompanyChartGenerationRequest,
    ) -> str | None:
        if request.mode is GenerationMode.REFERENCE_ONLY:
            return node.ref_code
        if request.mode is GenerationMode.PAD_TO_LENGTH:
            if request.code_policy is None:
                return None
            return request.code_policy.generate(
                AccountCodeGenerationRequest(
                    reference_code=node.ref_code,
                    target_length=_target_length(request.code_policy),
                )
            )
        if request.mode is GenerationMode.TEMPLATE_EXPANSION:
            template = request.template
            if template is None:
                return None
            return template.format(reference=node.ref_code, edition=request.edition)
        return None

    def _build_account(
        self,
        code: str,
        node: ReferenceNode,
        request: CompanyChartGenerationRequest,
    ) -> CompanyAccount:
        return CompanyAccount(
            id=AccountId(f"account:{_account_id_key(code)}"),
            entity_id=request.entity_id,
            code=code,
            label=node.label,
            postable=True,
        )


def _account_id_key(code: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "_", code)


def _target_length(policy: AccountCodePolicy) -> int | None:
    return getattr(policy, "length", None)


__all__ = [
    "CompanyChartGenerationRequest",
    "CompanyChartGenerationResult",
    "CompanyChartGenerator",
    "GenerationMode",
    "ReferenceNodeInclusionPolicy",
]
