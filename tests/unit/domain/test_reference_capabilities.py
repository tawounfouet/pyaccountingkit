"""Unit tests for reference capabilities (LOT-10)."""

from __future__ import annotations

from pyaccountingkit.domain.references.capabilities import (
    DEFAULT_FULL_CAPABILITIES,
    ReferenceCapability,
    ReferenceCapabilitySet,
)


def test_supports_and_requires_all() -> None:
    full = DEFAULT_FULL_CAPABILITIES
    assert full.supports(ReferenceCapability.SNAPSHOTS)
    assert full.requires_all((ReferenceCapability.NODE_LOOKUP, ReferenceCapability.HIERARCHY))
    assert full.requires_all((ReferenceCapability.SNAPSHOTS,))
    assert not ReferenceCapabilitySet().requires_all((ReferenceCapability.NODE_LOOKUP,))
    partial = ReferenceCapabilitySet(frozenset({ReferenceCapability.NODE_LOOKUP}))
    assert not partial.requires_all(
        (ReferenceCapability.NODE_LOOKUP, ReferenceCapability.HIERARCHY)
    )


def test_intersection() -> None:
    a = ReferenceCapabilitySet(frozenset({ReferenceCapability.NODE_LOOKUP}))
    b = ReferenceCapabilitySet(
        frozenset({ReferenceCapability.NODE_LOOKUP, ReferenceCapability.CONCEPTS})
    )
    assert (a & b).capabilities == frozenset({ReferenceCapability.NODE_LOOKUP})
