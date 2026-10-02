"""Unit tests for reference standards and node types (LOT-10)."""

from __future__ import annotations

from pyaccountingkit.domain.references.standards import (
    AccountNature,
    ReferenceNodeType,
    StandardType,
)


def test_canonical_ids_roundtrip() -> None:
    assert StandardType.PCG_FRANCE.canonical_id == "fr-pcg"
    assert StandardType.SYSCOHADA.canonical_id == "syscohada"
    assert StandardType.OHADA_EBNL.canonical_id == "ohada-ebnl"
    assert StandardType.from_canonical_id("fr-pcg") is StandardType.PCG_FRANCE
    assert StandardType.from_canonical_id("syscohada") is StandardType.SYSCOHADA
    assert StandardType.from_canonical_id("ohada-ebnl") is StandardType.OHADA_EBNL
    assert StandardType.from_canonical_id("unknown") is None


def test_standard_enum_values() -> None:
    assert set(StandardType) == {
        StandardType.PCG_FRANCE,
        StandardType.PCG_ASSOCIATIONS,
        StandardType.SYSCOHADA,
        StandardType.OHADA_EBNL,
        StandardType.IFRS,
    }


def test_natures_and_node_types() -> None:
    assert AccountNature.ASSET.value == "ASSET"
    assert ReferenceNodeType.CLASS.value == "class"
    assert ReferenceNodeType.GROUP.value == "group"
    assert ReferenceNodeType.CLASS_SCOPE.value == "class_scope"
    assert ReferenceNodeType.ACCOUNT.value == "account"
