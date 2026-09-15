"""Neutral accounting concepts and their bindings to standard nodes (LOT-10)."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.domain.references.standards import RegulatoryId


@dataclass(frozen=True, slots=True)
class ReferenceConcept:
    """A standard-neutral accounting notion shared across jurisdictions."""

    code: str
    label: str
    definition: str = ""


@dataclass(frozen=True, slots=True)
class ConceptBinding:
    """Maps one neutral concept onto the nodes of a specific standard."""

    concept_code: str
    standard_id: str
    edition: str
    node_ids: tuple[RegulatoryId, ...]


class ConceptRegistry:
    """Registry of neutral concepts and standard bindings (append-only)."""

    def __init__(self) -> None:
        self._concepts: dict[str, ReferenceConcept] = {}
        self._bindings: dict[str, tuple[ConceptBinding, ...]] = {}

    def add_concept(self, concept: ReferenceConcept) -> None:
        self._concepts[concept.code] = concept

    def bind(
        self,
        concept_code: str,
        standard_id: str,
        edition: str,
        node_ids: tuple[RegulatoryId, ...],
    ) -> None:
        if concept_code not in self._concepts:
            raise KeyError(f"Unknown concept {concept_code}")
        binding = ConceptBinding(concept_code, standard_id, edition, node_ids)
        current = [b for b in self._bindings.get(concept_code, ())]
        current.append(binding)
        self._bindings[concept_code] = tuple(current)

    def get(self, concept_code: str) -> ReferenceConcept | None:
        return self._concepts.get(concept_code)

    def concepts(self) -> tuple[ReferenceConcept, ...]:
        return tuple(self._concepts[code] for code in sorted(self._concepts))

    def bindings_for(self, concept_code: str) -> tuple[ConceptBinding, ...]:
        return self._bindings.get(concept_code, ())

    def concepts_for(
        self,
        standard_id: str,
        node_id: RegulatoryId,
    ) -> tuple[ReferenceConcept, ...]:
        found: list[ReferenceConcept] = []
        for concept_code, bindings in self._bindings.items():
            if any(
                binding.standard_id == standard_id and node_id in binding.node_ids
                for binding in bindings
            ):
                concept = self._concepts[concept_code]
                found.append(concept)
        return tuple(sorted(found, key=lambda concept: concept.code))


def seed_neutral_concepts() -> ConceptRegistry:
    """Registry preloaded with the core neutral accounting concepts."""
    registry = ConceptRegistry()
    for code, label, definition in _CORE_CONCEPTS:
        registry.add_concept(
            ReferenceConcept(
                code=code,
                label=label,
                definition=definition,
            )
        )
    return registry


_CORE_CONCEPTS: tuple[tuple[str, str, str], ...] = (
    ("CASH", "Trésorerie", "Disponibilités et équivalents de trésorerie."),
    ("TRADE_RECEIVABLES", "Créances d'exploitation", "Droits à recevoir de l'activité."),
    ("TRADE_PAYABLES", "Dettes d'exploitation", "Obligations envers les fournisseurs."),
    ("SHARE_CAPITAL", "Capital / dotation", "Ressources stables issues des apports."),
    ("REVENUE", "Produits", "Augmentations d'avantages économiques."),
    ("EXPENSE", "Charges", "Diminutions d'avantages économiques."),
    ("FIXED_ASSETS", "Immobilisations", "Actifs servant durablement à l'activité."),
)

__all__ = [
    "ReferenceConcept",
    "ConceptBinding",
    "ConceptRegistry",
    "seed_neutral_concepts",
]
