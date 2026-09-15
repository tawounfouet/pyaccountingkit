"""Regulatory standards, node types and account natures (LOT-10).

Standards carry a canonical id used by the upstream datasets
(``fr-pcg``, ``syscohada``...) that must be preserved exactly.
"""

from __future__ import annotations

from enum import StrEnum

RegulatoryId = str


class StandardType(StrEnum):
    """Jurisdictional accounting standards exposed by reference providers."""

    PCG_FRANCE = "PCG_FRANCE"
    PCG_ASSOCIATIONS = "PCG_ASSOCIATIONS"
    SYSCOHADA = "SYSCOHADA"
    IFRS = "IFRS"

    @property
    def canonical_id(self) -> str:
        return _CANONICAL_IDS[self]

    @staticmethod
    def from_canonical_id(canonical_id: str) -> StandardType | None:
        for standard, canonical in _CANONICAL_IDS.items():
            if canonical == canonical_id:
                return standard
        return None


class AccountNature(StrEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    EXPENSE = "EXPENSE"
    REVENUE = "REVENUE"
    SPECIAL = "SPECIAL"


class ReferenceNodeType(StrEnum):
    """Node kinds found in the upstream structure datasets."""

    CLASS = "class"
    GROUP = "group"
    ACCOUNT = "account"
    ACCOUNT_RANGE = "account_range"
    GROUP_BUNDLE = "group_bundle"


_CANONICAL_IDS: dict[StandardType, str] = {
    StandardType.PCG_FRANCE: "fr-pcg",
    StandardType.PCG_ASSOCIATIONS: "fr-pcg-assoc",
    StandardType.SYSCOHADA: "syscohada",
    StandardType.IFRS: "ifrs",
}

__all__ = [
    "RegulatoryId",
    "StandardType",
    "AccountNature",
    "ReferenceNodeType",
]
