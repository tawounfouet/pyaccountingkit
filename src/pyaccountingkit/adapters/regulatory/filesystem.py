"""Local filesystem reference adapter — reads structured datasets (LOT-10)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyaccountingkit.adapters.regulatory._base import (
    STANDARD_FILENAMES,
    _ReferenceProviderBase,
    parse_structure,
)
from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy
from pyaccountingkit.domain.references.relations import NegativeConstraint
from pyaccountingkit.domain.references.standards import StandardType


class LocalFilesystemReferenceAdapter(_ReferenceProviderBase):
    """Provider reading ``*_v1_structure.json`` files from a base directory.

    The filesystem path lives only in the adapter (DoD ``provider paths
    absent from domain``); the domain only sees the provider port.
    """

    def __init__(
        self,
        base_path: Path,
        clock: ClockProtocol | None = None,
        resource_names: Mapping[StandardType, str] | None = None,
        extra_constraints: Mapping[StandardType, tuple[NegativeConstraint, ...]] | None = None,
    ) -> None:
        super().__init__(clock=clock, extra_constraints=extra_constraints)
        self._base = base_path
        self._resource_names = resource_names or STANDARD_FILENAMES

    def _load_hierarchy(self, standard: StandardType) -> ReferenceHierarchy:
        filename = self._resource_names.get(standard)
        if filename is None:
            raise KeyError(f"No dataset file configured for {standard.value}")
        raw = (self._base / filename).read_text(encoding="utf-8")
        doc: Any = json.loads(raw)
        return parse_structure(doc)


__all__ = ["LocalFilesystemReferenceAdapter"]
