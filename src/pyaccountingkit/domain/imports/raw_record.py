"""Lossless raw records produced by source-format adapters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class RawImportRecord:
    """Immutable raw source record preserving adapter-level provenance."""

    batch_id: str
    record_index: int
    raw_fields: Mapping[str, str | None]
    source_line_number: int | None = None
    source_record_id: str | None = None
    row_checksum: str | None = None
    provenance: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.batch_id.strip():
            raise ValueError("batch_id must not be empty")
        if self.record_index < 0:
            raise ValueError("record_index must be non-negative")
        if self.source_line_number is not None and self.source_line_number <= 0:
            raise ValueError("source_line_number must be positive")
        fields = MappingProxyType(dict(self.raw_fields))
        provenance = MappingProxyType(dict(self.provenance))
        object.__setattr__(self, "raw_fields", fields)
        object.__setattr__(self, "provenance", provenance)
        if self.row_checksum is None:
            canonical = json.dumps(dict(fields), sort_keys=True, separators=(",", ":"))
            object.__setattr__(self, "row_checksum", hashlib.sha256(canonical.encode()).hexdigest())

    @property
    def source_ref(self) -> str:
        suffix = self.source_record_id or str(self.record_index)
        return f"{self.batch_id}:{suffix}"


__all__ = ["RawImportRecord"]
