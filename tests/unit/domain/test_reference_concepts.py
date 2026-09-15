"""Unit tests for neutral concepts and bindings (LOT-10)."""

from __future__ import annotations

import pytest

from pyaccountingkit.domain.references.concepts import (
    ReferenceConcept,
    seed_neutral_concepts,
)


def test_neutral_seed_contains_core_concepts() -> None:
    registry = seed_neutral_concepts()
    assert registry.get("CASH") is not None
    assert registry.get("TRADE_RECEIVABLES") is not None


def test_binding_roundtrip() -> None:
    registry = seed_neutral_concepts()
    registry.bind(
        "TRADE_RECEIVABLES",
        "fr-pcg",
        "2026",
        ("account:fr-pcg:2026:411",),
    )
    registry.bind(
        "TRADE_PAYABLES",
        "fr-pcg",
        "2026",
        ("account:fr-pcg:2026:401",),
    )
    concepts = registry.concepts_for("fr-pcg", "account:fr-pcg:2026:411")
    assert [concept.code for concept in concepts] == ["TRADE_RECEIVABLES"]
    assert registry.bindings_for("TRADE_RECEIVABLES")[0].standard_id == "fr-pcg"


def test_binding_unknown_concept_rejected() -> None:
    registry = seed_neutral_concepts()
    with pytest.raises(KeyError):
        registry.bind("NOT_A_CONCEPT", "fr-pcg", "2026", ("x",))


def test_concepts_sorted_exposition() -> None:
    registry = seed_neutral_concepts()
    codes = [concept.code for concept in registry.concepts()]
    assert codes == sorted(codes)
    assert ReferenceConcept("X", "x").definition == ""
