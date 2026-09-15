"""Strongly-typed identifiers, object references and an opaque ID factory.

Identifiers are opaque strings distinct from any business code (account
codes, journal codes, ...). They are natively JSON-serializable.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from typing import NewType

EntityId = NewType("EntityId", str)
FiscalYearId = NewType("FiscalYearId", str)
PeriodId = NewType("PeriodId", str)
JournalId = NewType("JournalId", str)
EntryId = NewType("EntryId", str)
AccountId = NewType("AccountId", str)

_ID_PREFIX_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


@dataclass(frozen=True, slots=True)
class ObjectRef:
    """Typed reference to any domain object, used by provenance and lineage."""

    object_type: str
    object_id: str

    def to_key(self) -> str:
        """Serialize as ``type:id``, the canonical storage key."""
        return f"{self.object_type}:{self.object_id}"

    @classmethod
    def from_key(cls, key: str) -> ObjectRef:
        """Parse a ``type:id`` canonical key (type must not contain a colon)."""
        object_type, _, object_id = key.partition(":")
        if not object_type or not object_id:
            raise ValueError(f"Malformed ObjectRef key: {key!r}")
        return cls(object_type=object_type, object_id=object_id)


class IdFactory:
    """Factory producing opaque, parseable, collision-safe identifiers.

    The default source is cryptographically strong.  Tests can inject a
    deterministic ``bit_source`` without weakening production defaults.
    """

    def __init__(self, bit_source: Callable[[int], int] | None = None) -> None:
        self._bit_source = bit_source if bit_source is not None else secrets.randbits

    def new(self, prefix: str) -> str:
        """Return a fresh identifier ``prefix_<96-bit hex>``."""
        if not _ID_PREFIX_PATTERN.match(prefix):
            raise ValueError(f"Invalid identifier prefix: {prefix!r}")
        return f"{prefix}_{self._bit_source(96):024x}"


__all__ = [
    "EntityId",
    "FiscalYearId",
    "PeriodId",
    "JournalId",
    "EntryId",
    "AccountId",
    "ObjectRef",
    "IdFactory",
]
