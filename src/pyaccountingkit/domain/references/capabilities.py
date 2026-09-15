"""Reference capabilities — declared provider features (LOT-10)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReferenceCapability(StrEnum):
    NODE_LOOKUP = "NODE_LOOKUP"
    HIERARCHY = "HIERARCHY"
    SNAPSHOTS = "SNAPSHOTS"
    CROSSWALKS = "CROSSWALKS"
    NEGATIVE_CONSTRAINTS = "NEGATIVE_CONSTRAINTS"
    CONCEPTS = "CONCEPTS"


@dataclass(frozen=True, slots=True)
class ReferenceCapabilitySet:
    """Declared set of capabilities of one provider (immutable)."""

    capabilities: frozenset[ReferenceCapability] = frozenset()

    def supports(self, capability: ReferenceCapability) -> bool:
        return capability in self.capabilities

    def requires_all(self, required: tuple[ReferenceCapability, ...]) -> bool:
        return all(self.supports(capability) for capability in required)

    def __and__(self, other: ReferenceCapabilitySet) -> ReferenceCapabilitySet:
        return ReferenceCapabilitySet(self.capabilities & other.capabilities)


DEFAULT_FULL_CAPABILITIES = ReferenceCapabilitySet(frozenset(ReferenceCapability))

__all__ = [
    "ReferenceCapability",
    "ReferenceCapabilitySet",
    "DEFAULT_FULL_CAPABILITIES",
]
