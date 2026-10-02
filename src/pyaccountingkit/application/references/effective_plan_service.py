"""Application service for effective regulatory account plans (LOT-27)."""

from __future__ import annotations

from pyaccountingkit.domain.references.effective_plan import EffectiveAccountPlan
from pyaccountingkit.domain.references.snapshots import EffectivePlanSnapshot
from pyaccountingkit.ports.references import EffectivePlanReferenceProviderProtocol


class EffectivePlanReferenceService:
    """Framework-neutral query service for the public references namespace."""

    def __init__(self, provider: EffectivePlanReferenceProviderProtocol) -> None:
        self._provider = provider

    def get_effective_plan(
        self,
        *,
        standard_id: str,
        edition: str,
        context: object | None = None,
    ) -> EffectiveAccountPlan:
        del context
        return self._provider.get_effective_plan(standard_id, edition)

    def create_snapshot(
        self,
        *,
        standard_id: str,
        edition: str,
        version: str,
        context: object | None = None,
    ) -> EffectivePlanSnapshot:
        del context
        return self._provider.get_effective_plan_snapshot(standard_id, edition, version)


__all__ = ["EffectivePlanReferenceService"]
