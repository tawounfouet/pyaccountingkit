"""Package reference adapter — reads a Python-bundled dataset resource (LOT-10)."""

from __future__ import annotations

import importlib.resources
import json
from collections.abc import Mapping

from pyaccountingkit.adapters.regulatory._base import (
    STANDARD_FILENAMES,
    _ReferenceProviderBase,
    parse_structure,
)
from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy
from pyaccountingkit.domain.references.relations import NegativeConstraint
from pyaccountingkit.domain.references.standards import StandardType


class PackageReferenceAdapter(_ReferenceProviderBase):
    """Provider reading structural datasets bundled inside an importable package.

    ``package`` is a module or dotted package name; ``resource_names``
    overrides the default dataset filename per standard.
    """

    def __init__(
        self,
        package: str,
        clock: ClockProtocol | None = None,
        resource_names: Mapping[StandardType, str] | None = None,
        extra_constraints: Mapping[StandardType, tuple[NegativeConstraint, ...]] | None = None,
    ) -> None:
        super().__init__(clock=clock, extra_constraints=extra_constraints)
        self._package = package
        self._resource_names = resource_names or STANDARD_FILENAMES

    def _load_hierarchy(self, standard: StandardType) -> ReferenceHierarchy:
        filename = self._resource_names.get(standard)
        if filename is None:
            raise KeyError(f"No resource configured for {standard.value}")
        resource = importlib.resources.files(self._package).joinpath(filename)
        with resource.open("r", encoding="utf-8") as handle:
            doc: Mapping[str, object] = json.load(handle)
        return parse_structure(doc)


__all__ = ["PackageReferenceAdapter"]
