"""Application service for standard-level regulatory relations (LOT-27)."""

from __future__ import annotations

from pyaccountingkit.domain.references.standard_relations import (
    StandardRelation,
    StandardRelationType,
)
from pyaccountingkit.ports.references import StandardRelationProviderProtocol


class StandardRelationService:
    """Framework-neutral relation query and fail-closed inference guard."""

    def __init__(self, provider: StandardRelationProviderProtocol) -> None:
        self._provider = provider

    def relations_for(
        self,
        *,
        subject_ref: str,
        relation_type: StandardRelationType | None = None,
        context: object | None = None,
    ) -> tuple[StandardRelation, ...]:
        del context
        return self._provider.relations_for(subject_ref, relation_type)

    def require_not_forbidden(
        self,
        *,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
        context: object | None = None,
    ) -> None:
        del context
        self._provider.require_not_forbidden(subject_ref, relation_type, target_ref)

    def require_auto_inference_allowed(
        self,
        *,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
        context: object | None = None,
    ) -> None:
        del context
        self._provider.require_auto_inference_allowed(
            subject_ref,
            relation_type,
            target_ref,
        )

    def can_auto_infer(
        self,
        *,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
        context: object | None = None,
    ) -> bool:
        del context
        return self._provider.can_auto_infer(subject_ref, relation_type, target_ref)


__all__ = ["StandardRelationService"]
