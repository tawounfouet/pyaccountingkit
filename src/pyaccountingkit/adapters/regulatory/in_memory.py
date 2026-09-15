"""In-memory reference adapter — deterministic, for tests and contracts (LOT-10)."""

from __future__ import annotations

from collections.abc import Mapping

from pyaccountingkit.adapters.regulatory._base import _ReferenceProviderBase
from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy
from pyaccountingkit.domain.references.relations import NegativeConstraint
from pyaccountingkit.domain.references.standards import StandardType


class InMemoryReferenceAdapter(_ReferenceProviderBase):
    """Provider over pre-built hierarchies (no filesystem involved)."""

    def __init__(
        self,
        hierarchies: Mapping[StandardType, ReferenceHierarchy],
        clock: ClockProtocol | None = None,
        extra_constraints: Mapping[StandardType, tuple[NegativeConstraint, ...]] | None = None,
    ) -> None:
        super().__init__(clock=clock, extra_constraints=extra_constraints)
        self._provided = dict(hierarchies)

    def _load_hierarchy(self, standard: StandardType) -> ReferenceHierarchy:
        if standard not in self._provided:
            raise KeyError(f"Standard {standard.value} not provided to the in-memory adapter")
        return self._provided[standard]


__all__ = ["InMemoryReferenceAdapter"]
