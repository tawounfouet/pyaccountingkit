"""OHADA EBNL 2023 structural reference provider (LOT-27)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyaccountingkit.adapters.regulatory._base import _ReferenceProviderBase, parse_structure
from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.domain.references.capabilities import (
    EBNL_STRUCTURE_CAPABILITIES,
    ReferenceCapabilitySet,
)
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy
from pyaccountingkit.domain.references.standards import StandardType

EBNL_STRUCTURE_FILENAME = "ebnl_2023_v1_structure.json"


class EBNLFilesystemReferenceAdapter(_ReferenceProviderBase):
    """Read the reviewed EBNL graph while preserving source occurrence identities."""

    def __init__(
        self,
        base_path: Path,
        *,
        clock: ClockProtocol | None = None,
        filename: str = EBNL_STRUCTURE_FILENAME,
    ) -> None:
        super().__init__(clock=clock)
        self._base_path = base_path
        self._filename = filename

    def capabilities(self, standard: StandardType) -> ReferenceCapabilitySet:
        if standard is not StandardType.OHADA_EBNL:
            return ReferenceCapabilitySet()
        self.get_hierarchy(standard)
        return EBNL_STRUCTURE_CAPABILITIES

    def _load_hierarchy(self, standard: StandardType) -> ReferenceHierarchy:
        if standard is not StandardType.OHADA_EBNL:
            raise KeyError(f"unsupported EBNL structure {standard.value}")
        raw = (self._base_path / self._filename).read_text(encoding="utf-8")
        document: Any = json.loads(raw)
        if not isinstance(document, dict):
            raise ValueError("EBNL structure must contain a JSON object")
        hierarchy = parse_structure(document)
        if hierarchy.standard_id != standard.canonical_id or hierarchy.edition != "2023":
            raise ValueError("EBNL structure coordinates do not match ohada-ebnl:2023")
        return hierarchy


__all__ = ["EBNL_STRUCTURE_FILENAME", "EBNLFilesystemReferenceAdapter"]
