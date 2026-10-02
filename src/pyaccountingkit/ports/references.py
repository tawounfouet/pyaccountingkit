"""Accounting reference provider ports."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pyaccountingkit.domain.references.capabilities import ReferenceCapabilitySet
from pyaccountingkit.domain.references.concepts import ConceptRegistry
from pyaccountingkit.domain.references.effective_plan import EffectiveAccountPlan
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy, ReferenceNode
from pyaccountingkit.domain.references.overlays import ReferenceOverlay
from pyaccountingkit.domain.references.relations import ConstraintRegister
from pyaccountingkit.domain.references.snapshots import EffectivePlanSnapshot, ReferenceSnapshot
from pyaccountingkit.domain.references.standard_relations import (
    StandardRelation,
    StandardRelationRegister,
    StandardRelationType,
)
from pyaccountingkit.domain.references.standards import StandardType


class AccountingReferenceProviderProtocol(Protocol):
    """Contract of structural regulatory chart-of-accounts providers."""

    def get_node(self, standard: StandardType, code: str) -> ReferenceNode | None: ...

    def list_nodes_by_standard(self, standard: StandardType) -> Sequence[ReferenceNode]: ...

    def get_hierarchy(self, standard: StandardType) -> ReferenceHierarchy: ...

    def get_snapshot(self, standard: StandardType, version: str) -> ReferenceSnapshot: ...

    def capabilities(self, standard: StandardType) -> ReferenceCapabilitySet: ...

    def constraints(self, standard: StandardType) -> ConstraintRegister: ...

    def concept_registry(self) -> ConceptRegistry: ...


class StandardRelationProviderProtocol(Protocol):
    """Provider contract for explicit standard relations and inference guards."""

    def relation_register(self) -> StandardRelationRegister: ...

    def relations_for(
        self,
        subject_ref: str,
        relation_type: StandardRelationType | None = None,
    ) -> tuple[StandardRelation, ...]: ...

    def require_not_forbidden(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> None: ...

    def require_auto_inference_allowed(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> None: ...

    def can_auto_infer(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> bool: ...


class EffectivePlanReferenceProviderProtocol(Protocol):
    """Capability-specific provider for already-resolved regulatory effective plans."""

    def get_effective_plan(self, standard_id: str, edition: str) -> EffectiveAccountPlan: ...

    def get_overlay(self, standard_id: str, edition: str) -> ReferenceOverlay: ...

    def get_effective_plan_snapshot(
        self,
        standard_id: str,
        edition: str,
        version: str,
    ) -> EffectivePlanSnapshot: ...

    def capabilities(self, standard_id: str, edition: str) -> ReferenceCapabilitySet: ...


__all__ = [
    "AccountingReferenceProviderProtocol",
    "EffectivePlanReferenceProviderProtocol",
    "StandardRelationProviderProtocol",
]
