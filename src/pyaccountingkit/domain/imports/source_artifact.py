"""Immutable source evidence for generic accounting imports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    """Immutable description of bytes acquired from an external source.

    The generic domain deliberately knows nothing about FEC/CSV/ERP columns.
    ``checksum`` is always a lowercase SHA-256 digest.
    """

    artifact_ref: str
    source_type: str
    checksum: str
    acquired_at: datetime
    filename: str | None = None
    media_type: str | None = None
    size: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.artifact_ref.strip():
            raise ValueError("artifact_ref must not be empty")
        if not self.source_type.strip():
            raise ValueError("source_type must not be empty")
        digest = self.checksum.lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("checksum must be a SHA-256 hexadecimal digest")
        if self.size is not None and self.size < 0:
            raise ValueError("size must be non-negative")
        object.__setattr__(self, "checksum", digest)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def from_bytes(
        cls,
        *,
        artifact_ref: str,
        source_type: str,
        payload: bytes,
        acquired_at: datetime,
        filename: str | None = None,
        media_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> SourceArtifact:
        """Build source evidence while computing the canonical checksum."""
        return cls(
            artifact_ref=artifact_ref,
            source_type=source_type,
            checksum=hashlib.sha256(payload).hexdigest(),
            acquired_at=acquired_at,
            filename=filename,
            media_type=media_type,
            size=len(payload),
            metadata=metadata or {},
        )


@dataclass(frozen=True, slots=True)
class ImportSourceFingerprint:
    """Scoped import identity; a source checksum alone is never sufficient."""

    checksum: str
    entity_id: str
    adapter_id: str
    adapter_version: str
    fiscal_year_id: str | None = None
    source_business_key: str | None = None

    def canonical_key(self) -> str:
        return "|".join(
            (
                self.entity_id,
                self.checksum,
                self.adapter_id,
                self.adapter_version,
                self.fiscal_year_id or "",
                self.source_business_key or "",
            )
        )


__all__ = ["ImportSourceFingerprint", "SourceArtifact"]
