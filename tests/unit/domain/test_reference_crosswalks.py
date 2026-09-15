"""Unit tests for standards crosswalks (LOT-10)."""

from __future__ import annotations

from pyaccountingkit.domain.references.crosswalks import CrosswalkEntry, StandardCrosswalk


def _entry() -> CrosswalkEntry:
    return CrosswalkEntry(
        concept_code="TRADE_RECEIVABLES",
        source_standard_id="fr-pcg",
        source_node_id="account:fr-pcg:2026:411",
        target_standard_id="syscohada",
        target_node_id="account:syscohada:2017:411",
    )


def test_map_and_reverse() -> None:
    crosswalk = StandardCrosswalk((_entry(),))
    mapped = crosswalk.map("fr-pcg", "account:fr-pcg:2026:411")
    assert len(mapped) == 1
    assert mapped[0].target_standard_id == "syscohada"
    reversed_entries = crosswalk.reverse("syscohada", "account:syscohada:2017:411")
    assert reversed_entries[0].source_standard_id == "fr-pcg"
    assert crosswalk.reverse("fr-pcg", "account:fr-pcg:2026:411") == ()


def test_entries_for_concept() -> None:
    crosswalk = StandardCrosswalk((_entry(),))
    assert len(crosswalk.entries_for_concept("TRADE_RECEIVABLES")) == 1
    assert crosswalk.entries_for_concept("CASH") == ()


def test_add_is_immutable() -> None:
    first = StandardCrosswalk()
    second = first.add(_entry())
    assert first.entries() == ()
    assert len(second.entries()) == 1
